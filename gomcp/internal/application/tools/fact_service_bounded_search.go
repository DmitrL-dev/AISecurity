package tools

import (
	"context"
	"errors"
	"fmt"

	"github.com/syntrex/gomcp/internal/domain/memory"
)

// ErrBoundedSearchUnavailable prevents the additive bounded-search protocol
// from falling back to a store that can materialize unbounded rows.
var ErrBoundedSearchUnavailable = errors.New("bounded search snapshot unavailable")

// SearchFactsBoundedSnapshot preserves keyword/vector base ranking while all
// fact reads run after a bounded preflight in the same store snapshot. It does
// not invoke legacy synapse expansion because that store has no bounded read
// protocol.
func (s *FactService) SearchFactsBoundedSnapshot(
	ctx context.Context,
	query string,
	limit int,
	mode SearchMode,
) ([]*memory.Fact, *memory.BoundedSearchStoredOversize, error) {
	store, ok := s.store.(memory.ExactBoundedSearchStore)
	if !ok {
		return nil, nil, ErrBoundedSearchUnavailable
	}
	if limit <= 0 {
		limit = 20
	}

	switch mode {
	case ModeKeyword:
		return runBoundedSearchSnapshot(ctx, store, nil, func(snapshot memory.BoundedSearchSnapshot) ([]*memory.Fact, error) {
			return snapshot.Search(ctx, query, limit)
		})
	case ModeSemantic:
		if s.embedder == nil {
			return nil, nil, fmt.Errorf("semantic search unavailable: no embedder configured")
		}
		queryVec, err := s.embedder.Embed(ctx, query)
		if err != nil {
			return nil, nil, fmt.Errorf("embed query: %w", err)
		}
		return runBoundedSearchSnapshot(ctx, store, nil, func(snapshot memory.BoundedSearchSnapshot) ([]*memory.Fact, error) {
			return snapshot.SearchByVector(ctx, queryVec, limit)
		})
	default:
		return s.searchFactsHybridBoundedSnapshot(ctx, store, query, limit)
	}
}

// ReloadFactsBoundedSnapshot reloads only the signed frozen IDs. Later inserts
// elsewhere in the scope are deliberately outside both preflight and snapshot.
func (s *FactService) ReloadFactsBoundedSnapshot(
	ctx context.Context,
	factIDs []string,
) ([]*memory.Fact, *memory.BoundedSearchStoredOversize, error) {
	store, ok := s.store.(memory.ExactBoundedSearchStore)
	if !ok {
		return nil, nil, ErrBoundedSearchUnavailable
	}
	ids := append([]string(nil), factIDs...)
	return runBoundedSearchSnapshot(ctx, store, ids, func(snapshot memory.BoundedSearchSnapshot) ([]*memory.Fact, error) {
		facts := make([]*memory.Fact, 0, len(ids))
		for _, id := range ids {
			fact, err := snapshot.Get(ctx, id)
			if err != nil {
				return nil, err
			}
			facts = append(facts, fact)
		}
		return facts, nil
	})
}

func runBoundedSearchSnapshot(
	ctx context.Context,
	store memory.ExactBoundedSearchStore,
	factIDs []string,
	run func(memory.BoundedSearchSnapshot) ([]*memory.Fact, error),
) ([]*memory.Fact, *memory.BoundedSearchStoredOversize, error) {
	facts, oversize, err := store.WithBoundedSearchSnapshot(ctx, factIDs, run)
	if err != nil {
		return nil, nil, fmt.Errorf("bounded search snapshot: %w", err)
	}
	return facts, oversize, nil
}

func (s *FactService) searchFactsHybridBoundedSnapshot(
	ctx context.Context,
	store memory.ExactBoundedSearchStore,
	query string,
	limit int,
) ([]*memory.Fact, *memory.BoundedSearchStoredOversize, error) {
	if s.embedder == nil {
		return runBoundedSearchSnapshot(ctx, store, nil, func(snapshot memory.BoundedSearchSnapshot) ([]*memory.Fact, error) {
			return snapshot.Search(ctx, query, limit)
		})
	}

	queryVec, err := s.embedder.Embed(ctx, query)
	if err != nil {
		// Match legacy hybrid behavior: embedder failure degrades to keyword
		// without verified-synapse expansion.
		return runBoundedSearchSnapshot(ctx, store, nil, func(snapshot memory.BoundedSearchSnapshot) ([]*memory.Fact, error) {
			return snapshot.Search(ctx, query, limit)
		})
	}
	return runBoundedSearchSnapshot(ctx, store, nil, func(snapshot memory.BoundedSearchSnapshot) ([]*memory.Fact, error) {
		semantic, err := snapshot.SearchByVector(ctx, queryVec, limit)
		if err != nil {
			// Match legacy hybrid behavior: any semantic-store failure also
			// degrades to keyword without verified-synapse expansion.
			return snapshot.Search(ctx, query, limit)
		}
		keyword, err := snapshot.Search(ctx, query, limit)
		if err != nil {
			return semantic, nil
		}
		return mergeBoundedSearchFacts(semantic, keyword, limit), nil
	})
}

func mergeBoundedSearchFacts(semantic, keyword []*memory.Fact, limit int) []*memory.Fact {
	seen := make(map[string]struct{}, len(semantic)+len(keyword))
	merged := make([]*memory.Fact, 0, limit)
	for _, facts := range [][]*memory.Fact{semantic, keyword} {
		for _, fact := range facts {
			if _, present := seen[fact.ID]; present {
				continue
			}
			seen[fact.ID] = struct{}{}
			merged = append(merged, fact)
			if len(merged) >= limit {
				return merged
			}
		}
	}
	return merged
}
