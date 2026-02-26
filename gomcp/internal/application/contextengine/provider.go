package contextengine

import (
	"context"
	"sync"

	"github.com/sentinel-community/gomcp/internal/domain/memory"

	ctxdomain "github.com/sentinel-community/gomcp/internal/domain/context"
)

// StoreFactProvider adapts FactStore + HotCache to the FactProvider interface,
// bridging infrastructure storage with the context engine domain.
type StoreFactProvider struct {
	store memory.FactStore
	cache memory.HotCache

	mu           sync.Mutex
	accessCounts map[string]int
}

// NewStoreFactProvider creates a FactProvider backed by FactStore and optional HotCache.
func NewStoreFactProvider(store memory.FactStore, cache memory.HotCache) *StoreFactProvider {
	return &StoreFactProvider{
		store:        store,
		cache:        cache,
		accessCounts: make(map[string]int),
	}
}

// Verify interface compliance at compile time.
var _ ctxdomain.FactProvider = (*StoreFactProvider)(nil)

// GetRelevantFacts returns candidate facts for context injection.
// Uses keyword search from tool arguments + L0 facts as candidates.
func (p *StoreFactProvider) GetRelevantFacts(args map[string]interface{}) ([]*memory.Fact, error) {
	ctx := context.Background()

	// Always include L0 facts
	l0Facts, err := p.GetL0Facts()
	if err != nil {
		return nil, err
	}

	// Extract query text from arguments for search
	query := extractQueryFromArgs(args)
	if query == "" {
		return l0Facts, nil
	}

	// Search for additional relevant facts
	searchResults, err := p.store.Search(ctx, query, 30)
	if err != nil {
		// Degrade gracefully — just return L0 facts
		return l0Facts, nil
	}

	// Merge L0 + search results, deduplicating by ID
	seen := make(map[string]bool, len(l0Facts))
	merged := make([]*memory.Fact, 0, len(l0Facts)+len(searchResults))

	for _, f := range l0Facts {
		seen[f.ID] = true
		merged = append(merged, f)
	}
	for _, f := range searchResults {
		if !seen[f.ID] {
			seen[f.ID] = true
			merged = append(merged, f)
		}
	}

	return merged, nil
}

// GetL0Facts returns all L0 (project-level) facts.
// Uses HotCache if available, falls back to store.
func (p *StoreFactProvider) GetL0Facts() ([]*memory.Fact, error) {
	ctx := context.Background()

	if p.cache != nil {
		facts, err := p.cache.GetL0Facts(ctx)
		if err == nil && len(facts) > 0 {
			return facts, nil
		}
	}

	return p.store.ListByLevel(ctx, memory.LevelProject)
}

// RecordAccess increments the access counter for a fact.
func (p *StoreFactProvider) RecordAccess(factID string) {
	p.mu.Lock()
	p.accessCounts[factID]++
	p.mu.Unlock()
}

// extractQueryFromArgs builds a search query string from argument values.
func extractQueryFromArgs(args map[string]interface{}) string {
	var parts []string
	for _, v := range args {
		if s, ok := v.(string); ok && s != "" {
			parts = append(parts, s)
		}
	}
	if len(parts) == 0 {
		return ""
	}
	result := ""
	for i, p := range parts {
		if i > 0 {
			result += " "
		}
		result += p
	}
	return result
}
