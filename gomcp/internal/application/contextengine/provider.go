package contextengine

import (
	"context"
	"sync"

	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
	"github.com/syntrex/gomcp/internal/domain/synapse"

	ctxdomain "github.com/syntrex/gomcp/internal/domain/context"
)

const synapseBoostAccessCount = 30

// StoreFactProvider adapts FactStore + HotCache to the FactProvider interface,
// bridging infrastructure storage with the context engine domain.
type StoreFactProvider struct {
	store    memory.FactStore
	cache    memory.HotCache
	synapses synapse.SynapseStore
	scope    rlmscope.Scope

	mu           sync.Mutex
	accessCounts map[string]int
}

// NewStoreFactProvider creates a FactProvider backed by FactStore and optional HotCache.
func NewStoreFactProvider(store memory.FactStore, cache memory.HotCache) *StoreFactProvider {
	return &StoreFactProvider{
		store:        store,
		cache:        cache,
		scope:        rlmscope.Default(),
		accessCounts: make(map[string]int),
	}
}

// WithScope binds the provider to a tenant/project memory boundary.
func (p *StoreFactProvider) WithScope(sc rlmscope.Scope) *StoreFactProvider {
	p.scope = sc.Normalize()
	return p
}

// WithSynapseStore enables verified synapse expansion for proactive context.
func (p *StoreFactProvider) WithSynapseStore(store synapse.SynapseStore) *StoreFactProvider {
	p.synapses = store
	return p
}

// Verify interface compliance at compile time.
var _ ctxdomain.FactProvider = (*StoreFactProvider)(nil)

// GetRelevantFacts returns candidate facts for context injection.
// Uses keyword search from tool arguments + L0 facts as candidates.
func (p *StoreFactProvider) GetRelevantFacts(args map[string]interface{}) ([]*memory.Fact, error) {
	facts, _, err := p.GetRelevantFactsWithBoost(rlmscope.WithScope(context.Background(), p.scope), args)
	return facts, err
}

// scopedCtx returns ctx when it already carries a scope (the per-request scope
// set by the scope middleware), otherwise binds the provider's pinned scope.
// This lets proactive context injection honor a client's project switch in
// unlocked mode while still defaulting to the pinned scope for direct callers.
func (p *StoreFactProvider) scopedCtx(ctx context.Context) context.Context {
	if _, ok := rlmscope.Lookup(ctx); ok {
		return ctx
	}
	return rlmscope.WithScope(context.Background(), p.scope)
}

// GetRelevantFactsWithBoost returns candidate facts plus access-count boosts for
// facts reached through verified synapses from direct query hits. The scope is
// taken from ctx (the per-request tenant/project resolved by the scope
// middleware), falling back to the provider's pinned scope.
func (p *StoreFactProvider) GetRelevantFactsWithBoost(ctx context.Context, args map[string]interface{}) ([]*memory.Fact, map[string]int, error) {
	ctx = p.scopedCtx(ctx)

	// Always include L0 facts
	l0Facts, err := p.getL0Facts(ctx)
	if err != nil {
		return nil, nil, err
	}

	// Extract query text from arguments for search
	query := extractQueryFromArgs(args)
	if query == "" {
		return l0Facts, nil, nil
	}

	// Search for additional relevant facts
	searchResults, err := p.store.Search(ctx, query, 30)
	if err != nil {
		// Degrade gracefully — just return L0 facts
		return l0Facts, nil, nil
	}

	// Merge L0 + search results, deduplicating by ID
	seen := make(map[string]bool, len(l0Facts))
	seedIDs := make(map[string]bool, len(searchResults))
	merged := make([]*memory.Fact, 0, len(l0Facts)+len(searchResults))

	for _, f := range l0Facts {
		seen[f.ID] = true
		merged = append(merged, f)
	}
	for _, f := range searchResults {
		// Review 13.06 (audit D3): session-scoped facts must NOT be proactively
		// injected across sessions (cross-session memory bleed). Until a
		// session_id is threaded through the FactStore query API, only
		// L0/shared (no-session) facts are eligible for proactive injection.
		if f.SessionID != "" {
			continue
		}
		seedIDs[f.ID] = true
		if !seen[f.ID] {
			seen[f.ID] = true
			merged = append(merged, f)
		}
	}

	boosts := p.expandSynapseNeighbors(ctx, seedIDs, seen, &merged)
	return merged, boosts, nil
}

// GetL0Facts returns all L0 (project-level) facts under the provider's pinned
// scope (domain interface). The middleware path uses getL0Facts(ctx).
func (p *StoreFactProvider) GetL0Facts() ([]*memory.Fact, error) {
	return p.getL0Facts(rlmscope.WithScope(context.Background(), p.scope))
}

// getL0Facts returns scoped L0 facts from the durable store. A nonempty
// hot cache does not prove completeness or freshness.
func (p *StoreFactProvider) getL0Facts(ctx context.Context) ([]*memory.Fact, error) {
	return p.store.ListByLevel(ctx, memory.LevelProject)
}

// RecordAccess increments the access counter for a fact, in memory and in the store.
//
// The in-memory half was all there was, and it made two things wrong at once.
//
// Measured on Global 2026-08-06: `hit_count` is 0 for every fact in all three tenant databases,
// maximum 0. `TouchFact` — the method that writes it — is declared in the FactStore interface,
// implemented in FactRepo, and called by nothing outside test mocks. So the counter existed,
// looked maintained, and was never once incremented in production.
//
// Consequence one: the frequency term in the scorer only counts accesses within the lifetime of
// this process. The gomcp subprocess is per-tenant and spawned on demand, so in practice it scores
// almost everything at zero.
//
// Consequence two, and the expensive one: `GetColdFacts` selects on `COALESCE(hit_count,0) = 0 AND
// created_at < 30 days`. With a counter that never rises, that is every fact older than a month
// regardless of how heavily it is used. `gomcp-decay` archives what that query returns — so the
// fact that nothing schedules the decay pass is currently the only thing protecting the store from
// a criterion that would eventually classify all of it as unused.
//
// The scope comes from p.scope, not from a background default. TouchFact filters on tenant_id and
// project_id, and an UPDATE that matches no rows is not an error — a fix written with
// rlmscope.Default() would run, report success, and change nothing. That is the same shape as the
// defect it is fixing.
func (p *StoreFactProvider) RecordAccess(factID string) {
	p.mu.Lock()
	p.accessCounts[factID]++
	p.mu.Unlock()

	if p.store == nil {
		return
	}
	// Fire-and-forget, matching this method's signature: a counter bump must never fail a context
	// build. The error is dropped deliberately rather than by omission — there is no caller that
	// could act on it, and returning one would change the FactProvider interface for every
	// implementation to carry news nobody reads.
	ctx := rlmscope.WithScope(context.Background(), p.scope)
	_ = p.store.TouchFact(ctx, factID)
}

func (p *StoreFactProvider) expandSynapseNeighbors(ctx context.Context, seedIDs, seen map[string]bool, merged *[]*memory.Fact) map[string]int {
	if p.synapses == nil || len(seedIDs) == 0 {
		return nil
	}
	verified, err := p.synapses.ListVerified(ctx)
	if err != nil {
		return nil
	}
	boosts := make(map[string]int)
	for _, link := range verified {
		neighborID := ""
		switch {
		case seedIDs[link.FactIDA]:
			neighborID = link.FactIDB
		case seedIDs[link.FactIDB]:
			neighborID = link.FactIDA
		default:
			continue
		}
		if neighborID == "" || seen[neighborID] {
			continue
		}
		fact, err := p.store.Get(ctx, neighborID)
		if err != nil || fact == nil || fact.SessionID != "" || fact.IsArchived {
			continue
		}
		seen[neighborID] = true
		*merged = append(*merged, fact)
		boosts[neighborID] += synapseBoostAccessCount
	}
	if len(boosts) == 0 {
		return nil
	}
	return boosts
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
