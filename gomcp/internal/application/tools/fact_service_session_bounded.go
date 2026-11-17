package tools

import (
	"context"
	"fmt"

	"github.com/syntrex/gomcp/internal/domain/memory"
)

// SearchSessionFactsBoundedSnapshot preserves the exact session keyword,
// vector, and hybrid ranking contracts while requiring a stored-row preflight
// in the same snapshot as every variable-width read. It never falls back to
// SearchSessionFactsWithMode or the legacy SessionFactStore search methods.
func (s *FactService) SearchSessionFactsBoundedSnapshot(
	ctx context.Context,
	sessionID, query string,
	limit int,
	mode SearchMode,
) ([]*memory.Fact, *memory.BoundedSearchStoredOversize, error) {
	if _, err := s.sessionStore(ctx, sessionID); err != nil {
		return nil, nil, err
	}
	store, ok := s.store.(memory.ExactBoundedSessionSearchStore)
	if !ok {
		return nil, nil, ErrBoundedSearchUnavailable
	}
	if limit <= 0 {
		limit = 20
	}

	var (
		facts    []*memory.Fact
		oversize *memory.BoundedSearchStoredOversize
		err      error
	)
	switch mode {
	case ModeKeyword:
		facts, oversize, err = runBoundedSessionSearchSnapshot(
			ctx, store, sessionID, nil,
			func(snapshot memory.BoundedSearchSnapshot) ([]*memory.Fact, error) {
				return snapshot.Search(ctx, query, limit)
			},
		)
	case ModeSemantic:
		if s.embedder == nil {
			return nil, nil, fmt.Errorf("semantic search unavailable: no embedder configured")
		}
		var queryVec []float64
		queryVec, err = s.embedder.Embed(ctx, query)
		if err != nil {
			return nil, nil, fmt.Errorf("embed query: %w", err)
		}
		facts, oversize, err = runBoundedSessionSearchSnapshot(
			ctx, store, sessionID, nil,
			func(snapshot memory.BoundedSearchSnapshot) ([]*memory.Fact, error) {
				return snapshot.SearchByVector(ctx, queryVec, limit)
			},
		)
	default:
		facts, oversize, err = s.searchSessionFactsHybridBoundedSnapshot(
			ctx, store, sessionID, query, limit,
		)
	}
	if err != nil || oversize != nil {
		return nil, oversize, err
	}
	if err := validateSessionFacts(ctx, sessionID, facts...); err != nil {
		return nil, nil, err
	}
	return facts, nil, nil
}

// ReloadSessionFactsBoundedSnapshot revalidates only the cursor's frozen IDs
// under the same exact-session preflight and read snapshot. Later inserts are
// outside the signed page and deliberately ignored.
func (s *FactService) ReloadSessionFactsBoundedSnapshot(
	ctx context.Context,
	sessionID string,
	factIDs []string,
) ([]*memory.Fact, *memory.BoundedSearchStoredOversize, error) {
	if _, err := s.sessionStore(ctx, sessionID); err != nil {
		return nil, nil, err
	}
	store, ok := s.store.(memory.ExactBoundedSessionSearchStore)
	if !ok {
		return nil, nil, ErrBoundedSearchUnavailable
	}
	ids := append([]string(nil), factIDs...)
	facts, oversize, err := runBoundedSessionSearchSnapshot(
		ctx, store, sessionID, ids,
		func(snapshot memory.BoundedSearchSnapshot) ([]*memory.Fact, error) {
			facts := make([]*memory.Fact, 0, len(ids))
			for _, id := range ids {
				fact, err := snapshot.Get(ctx, id)
				if err != nil {
					return nil, err
				}
				facts = append(facts, fact)
			}
			return facts, nil
		},
	)
	if err != nil || oversize != nil {
		return nil, oversize, err
	}
	if err := validateSessionFacts(ctx, sessionID, facts...); err != nil {
		return nil, nil, err
	}
	return facts, nil, nil
}

func runBoundedSessionSearchSnapshot(
	ctx context.Context,
	store memory.ExactBoundedSessionSearchStore,
	sessionID string,
	factIDs []string,
	run func(memory.BoundedSearchSnapshot) ([]*memory.Fact, error),
) ([]*memory.Fact, *memory.BoundedSearchStoredOversize, error) {
	facts, oversize, err := store.WithBoundedSessionSearchSnapshot(ctx, sessionID, factIDs, run)
	if err != nil {
		return nil, nil, fmt.Errorf("bounded session search snapshot: %w", err)
	}
	return facts, oversize, nil
}

func (s *FactService) searchSessionFactsHybridBoundedSnapshot(
	ctx context.Context,
	store memory.ExactBoundedSessionSearchStore,
	sessionID, query string,
	limit int,
) ([]*memory.Fact, *memory.BoundedSearchStoredOversize, error) {
	keyword := func(snapshot memory.BoundedSearchSnapshot) ([]*memory.Fact, error) {
		return snapshot.Search(ctx, query, limit)
	}
	if s.embedder == nil {
		return runBoundedSessionSearchSnapshot(ctx, store, sessionID, nil, keyword)
	}
	queryVec, err := s.embedder.Embed(ctx, query)
	if err != nil {
		return runBoundedSessionSearchSnapshot(ctx, store, sessionID, nil, keyword)
	}
	depth := hybridDepth(limit)
	weight := s.semanticFusionWeight()
	return runBoundedSessionSearchSnapshot(
		ctx, store, sessionID, nil,
		func(snapshot memory.BoundedSearchSnapshot) ([]*memory.Fact, error) {
			semantic, err := snapshot.SearchByVector(ctx, queryVec, depth)
			if err != nil {
				return keyword(snapshot)
			}
			keywordFacts, err := snapshot.Search(ctx, query, depth)
			if err != nil {
				return truncateFacts(semantic, limit), nil
			}
			return fuseHybridResults(semantic, keywordFacts, limit, weight), nil
		},
	)
}

// GetExactSessionFact reloads one frozen session-search result through a store
// that proves the full tenant/project/session boundary in its query.
func (s *FactService) GetExactSessionFact(
	ctx context.Context,
	sessionID, factID string,
) (*memory.Fact, error) {
	if _, err := s.sessionStore(ctx, sessionID); err != nil {
		return nil, err
	}
	reader, ok := s.store.(memory.ExactSessionFactReader)
	if !ok {
		return nil, fmt.Errorf("bounded session memory is unavailable")
	}
	fact, err := reader.GetForSession(ctx, sessionID, factID)
	if err != nil {
		return nil, err
	}
	if err := validateSessionFacts(ctx, sessionID, fact); err != nil {
		return nil, err
	}
	return fact, nil
}
