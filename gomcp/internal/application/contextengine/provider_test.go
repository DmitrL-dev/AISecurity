package contextengine

import (
	"context"
	"fmt"
	"sync"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"
)

// --- Mock FactStore for provider tests ---

type mockFactStore struct {
	mu            sync.Mutex
	touched       []string
	touchedScopes []rlmscope.Scope
	facts         map[string]*memory.Fact
	searchFacts   []*memory.Fact
	searchErr     error
	levelFacts    map[memory.HierLevel][]*memory.Fact
}

func newMockFactStore() *mockFactStore {
	return &mockFactStore{
		facts:      make(map[string]*memory.Fact),
		levelFacts: make(map[memory.HierLevel][]*memory.Fact),
	}
}

func (m *mockFactStore) Add(_ context.Context, fact *memory.Fact) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.facts[fact.ID] = fact
	m.levelFacts[fact.Level] = append(m.levelFacts[fact.Level], fact)
	return nil
}

func (m *mockFactStore) Get(_ context.Context, id string) (*memory.Fact, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	f, ok := m.facts[id]
	if !ok {
		return nil, fmt.Errorf("not found")
	}
	return f, nil
}

func (m *mockFactStore) Update(_ context.Context, fact *memory.Fact) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.facts[fact.ID] = fact
	return nil
}

func (m *mockFactStore) Delete(_ context.Context, id string) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	delete(m.facts, id)
	return nil
}

func (m *mockFactStore) ListByDomain(_ context.Context, _ string, _ bool) ([]*memory.Fact, error) {
	return nil, nil
}

func (m *mockFactStore) ListByLevel(_ context.Context, level memory.HierLevel) ([]*memory.Fact, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	return m.levelFacts[level], nil
}

func (m *mockFactStore) ListDomains(_ context.Context) ([]string, error) {
	return nil, nil
}

func (m *mockFactStore) GetStale(_ context.Context, _ bool) ([]*memory.Fact, error) {
	return nil, nil
}

func (m *mockFactStore) Search(_ context.Context, _ string, _ int) ([]*memory.Fact, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	return m.searchFacts, m.searchErr
}

func (m *mockFactStore) SearchByVector(_ context.Context, _ []float64, _ int) ([]*memory.Fact, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	return m.searchFacts, m.searchErr
}

func (m *mockFactStore) GetExpired(_ context.Context) ([]*memory.Fact, error) {
	return nil, nil
}

func (m *mockFactStore) RefreshTTL(_ context.Context, _ string) error {
	return nil
}

// TouchFact records what it was asked to do. A mock that silently returned nil is precisely what
// let this go unnoticed: the interface was satisfied, every test passed, and hit_count in the real
// database stayed at 0 for every fact in every tenant.
func (m *mockFactStore) TouchFact(ctx context.Context, id string) error {
	// Under the mock's own mutex: RecordAccess is called from a context build, and this package
	// already has tests that drive builds from twenty goroutines.
	m.mu.Lock()
	defer m.mu.Unlock()
	m.touched = append(m.touched, id)
	m.touchedScopes = append(m.touchedScopes, rlmscope.FromContext(ctx))
	return nil
}

func (m *mockFactStore) GetColdFacts(_ context.Context, _ int) ([]*memory.Fact, error) {
	return nil, nil
}
func (m *mockFactStore) CompressFacts(_ context.Context, _ []string, _ string) (string, error) {
	return "", nil
}

func (m *mockFactStore) Stats(_ context.Context) (*memory.FactStoreStats, error) {
	return nil, nil
}

func (m *mockFactStore) ListGenes(_ context.Context) ([]*memory.Fact, error) { return nil, nil }

// --- Mock HotCache ---

type mockHotCache struct {
	l0Facts []*memory.Fact
	l0Err   error
}

func (m *mockHotCache) GetL0Facts(_ context.Context) ([]*memory.Fact, error) {
	return m.l0Facts, m.l0Err
}

func (m *mockHotCache) InvalidateFact(_ context.Context, _ string) error { return nil }
func (m *mockHotCache) WarmUp(_ context.Context, _ []*memory.Fact) error { return nil }
func (m *mockHotCache) Close() error                                     { return nil }

// --- StoreFactProvider tests ---

func TestNewStoreFactProvider(t *testing.T) {
	store := newMockFactStore()
	provider := NewStoreFactProvider(store, nil)
	require.NotNil(t, provider)
}

func TestStoreFactProvider_GetL0Facts_FromStore(t *testing.T) {
	store := newMockFactStore()
	f1 := memory.NewFact("L0 fact A", memory.LevelProject, "arch", "")
	f2 := memory.NewFact("L0 fact B", memory.LevelProject, "process", "")
	_ = store.Add(context.Background(), f1)
	_ = store.Add(context.Background(), f2)

	provider := NewStoreFactProvider(store, nil) // no cache

	facts, err := provider.GetL0Facts()
	require.NoError(t, err)
	assert.Len(t, facts, 2)
}

func TestStoreFactProvider_GetL0Facts_UsesStoreDespiteCache(t *testing.T) {
	store := newMockFactStore()
	storeFact := memory.NewFact("Durable L0", memory.LevelProject, "arch", "")
	_ = store.Add(context.Background(), storeFact)
	cacheFact := memory.NewFact("Stale cached L0", memory.LevelProject, "arch", "")
	provider := NewStoreFactProvider(store, &mockHotCache{l0Facts: []*memory.Fact{cacheFact}})
	facts, err := provider.GetL0Facts()
	require.NoError(t, err)
	assert.Len(t, facts, 1)
	assert.Equal(t, "Durable L0", facts[0].Content)
}

func TestStoreFactProvider_GetL0Facts_CacheFallbackToStore(t *testing.T) {
	store := newMockFactStore()
	storeFact := memory.NewFact("Store L0", memory.LevelProject, "arch", "")
	_ = store.Add(context.Background(), storeFact)

	cache := &mockHotCache{l0Facts: nil, l0Err: fmt.Errorf("cache miss")}
	provider := NewStoreFactProvider(store, cache)

	facts, err := provider.GetL0Facts()
	require.NoError(t, err)
	assert.Len(t, facts, 1)
	assert.Equal(t, "Store L0", facts[0].Content)
}

func TestStoreFactProvider_GetRelevantFacts_NoQuery(t *testing.T) {
	store := newMockFactStore()
	l0 := memory.NewFact("L0 always included", memory.LevelProject, "arch", "")
	_ = store.Add(context.Background(), l0)

	provider := NewStoreFactProvider(store, nil)

	// No string args → no query → only L0
	facts, err := provider.GetRelevantFacts(map[string]interface{}{
		"level": 0,
	})
	require.NoError(t, err)
	assert.Len(t, facts, 1)
}

func TestStoreFactProvider_GetRelevantFacts_WithSearch(t *testing.T) {
	store := newMockFactStore()
	l0 := memory.NewFact("L0 architecture", memory.LevelProject, "arch", "")
	searchResult := memory.NewFact("Found by search", memory.LevelDomain, "auth", "")
	_ = store.Add(context.Background(), l0)
	store.searchFacts = []*memory.Fact{searchResult}

	provider := NewStoreFactProvider(store, nil)

	facts, err := provider.GetRelevantFacts(map[string]interface{}{
		"content": "authentication module",
	})
	require.NoError(t, err)
	assert.Len(t, facts, 2) // L0 + search result
}

func TestStoreFactProvider_GetRelevantFacts_Deduplication(t *testing.T) {
	store := newMockFactStore()
	l0 := memory.NewFact("L0 architecture", memory.LevelProject, "arch", "")
	_ = store.Add(context.Background(), l0)
	// Search returns the same fact that's also L0
	store.searchFacts = []*memory.Fact{l0}

	provider := NewStoreFactProvider(store, nil)

	facts, err := provider.GetRelevantFacts(map[string]interface{}{
		"content": "architecture",
	})
	require.NoError(t, err)
	assert.Len(t, facts, 1, "duplicate should be removed")
}

func TestStoreFactProvider_GetRelevantFacts_SearchError_GracefulDegradation(t *testing.T) {
	store := newMockFactStore()
	l0 := memory.NewFact("L0 fact", memory.LevelProject, "arch", "")
	_ = store.Add(context.Background(), l0)
	store.searchErr = fmt.Errorf("search broken")

	provider := NewStoreFactProvider(store, nil)

	facts, err := provider.GetRelevantFacts(map[string]interface{}{
		"content": "test query",
	})
	require.NoError(t, err, "should degrade gracefully, not error")
	assert.Len(t, facts, 1, "should still return L0 facts")
}

func TestStoreFactProvider_GetRelevantFactsWithBoost_SynapseExpansionScoped(t *testing.T) {
	db, err := sqlite.OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { db.Close() })

	factRepo, err := sqlite.NewFactRepo(db)
	require.NoError(t, err)
	synapseRepo := sqlite.NewSynapseRepo(db)

	ctxA := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-alpha"))
	ctxB := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-b", "project-alpha"))

	directA := memory.NewFact("alpha direct lookup", memory.LevelDomain, "ops", "")
	linkedA := memory.NewFact("linked operational runbook", memory.LevelDomain, "ops", "")
	directB := memory.NewFact("alpha direct lookup", memory.LevelDomain, "ops", "")
	linkedB := memory.NewFact("bravo linked runbook", memory.LevelDomain, "ops", "")
	require.NoError(t, factRepo.Add(ctxA, directA))
	require.NoError(t, factRepo.Add(ctxA, linkedA))
	require.NoError(t, factRepo.Add(ctxB, directB))
	require.NoError(t, factRepo.Add(ctxB, linkedB))

	idA, err := synapseRepo.Create(ctxA, directA.ID, linkedA.ID, 0.93)
	require.NoError(t, err)
	require.NoError(t, synapseRepo.Accept(ctxA, idA))
	idB, err := synapseRepo.Create(ctxB, directB.ID, linkedB.ID, 0.91)
	require.NoError(t, err)
	require.NoError(t, synapseRepo.Accept(ctxB, idB))

	provider := NewStoreFactProvider(factRepo, nil).
		WithScope(rlmscope.New("tenant-a", "project-alpha")).
		WithSynapseStore(synapseRepo)

	facts, boosts, err := provider.GetRelevantFactsWithBoost(context.Background(), map[string]interface{}{
		"content": "alpha direct",
	})
	require.NoError(t, err)

	ids := map[string]bool{}
	for _, f := range facts {
		ids[f.ID] = true
	}
	assert.True(t, ids[directA.ID], "direct search hit must be present")
	assert.True(t, ids[linkedA.ID], "verified synapse neighbor must be present")
	assert.False(t, ids[linkedB.ID], "synapse expansion must stay scoped")
	assert.Greater(t, boosts[linkedA.ID], 0, "linked fact must receive a ranking boost")
}

func TestStoreFactProvider_RecordAccess(t *testing.T) {
	store := newMockFactStore()
	provider := NewStoreFactProvider(store, nil)

	provider.RecordAccess("fact-1")
	provider.RecordAccess("fact-1")
	provider.RecordAccess("fact-2")

	provider.mu.Lock()
	assert.Equal(t, 2, provider.accessCounts["fact-1"])
	assert.Equal(t, 1, provider.accessCounts["fact-2"])
	provider.mu.Unlock()
}

func TestExtractQueryFromArgs(t *testing.T) {
	tests := []struct {
		name string
		args map[string]interface{}
		want string
	}{
		{"nil", nil, ""},
		{"empty", map[string]interface{}{}, ""},
		{"no strings", map[string]interface{}{"level": 0, "flag": true}, ""},
		{"single string", map[string]interface{}{"content": "hello"}, "hello"},
		{"empty string", map[string]interface{}{"content": ""}, ""},
		{"mixed", map[string]interface{}{"content": "hello", "level": 0, "domain": "arch"}, ""},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := extractQueryFromArgs(tt.args)
			if tt.name == "mixed" {
				// Map iteration order is non-deterministic, just check non-empty
				assert.NotEmpty(t, got)
			} else {
				if tt.want == "" {
					assert.Empty(t, got)
				} else {
					assert.Contains(t, got, tt.want)
				}
			}
		})
	}
}

func TestRecordAccessPersistsTheAccess(t *testing.T) {
	// The counter existed, looked maintained, and was never incremented in production: TouchFact was
	// implemented and called by nothing. Measured on Global 2026-08-06 — hit_count = 0 for every fact
	// in all three tenant databases, maximum 0.
	//
	// It matters beyond the scorer. GetColdFacts selects on `hit_count = 0 AND created_at < 30 days`,
	// so a counter that never rises marks every older fact as unused, and gomcp-decay archives what
	// that query returns.
	store := newMockFactStore()
	provider := NewStoreFactProvider(store, nil)

	provider.RecordAccess("fact-1")
	provider.RecordAccess("fact-1")
	provider.RecordAccess("fact-2")

	require.Equal(t, []string{"fact-1", "fact-1", "fact-2"}, store.touched,
		"the access was counted in memory and never reached the store")
	// The in-memory count is still kept: the scorer reads it within one process, and dropping it
	// would trade one defect for another.
	require.Equal(t, 2, provider.accessCounts["fact-1"])
}

func TestRecordAccessUsesTheProviderScope(t *testing.T) {
	// The trap this fix could have fallen into. TouchFact filters on tenant_id and project_id, and an
	// UPDATE matching no rows is not an error — so persisting with rlmscope.Default() would run,
	// report success, and change nothing, which is the same defect wearing a fix's clothes.
	store := newMockFactStore()
	provider := NewStoreFactProvider(store, nil).WithScope(rlmscope.New("tenant-a", "proj-a"))

	provider.RecordAccess("fact-1")

	require.Len(t, store.touchedScopes, 1)
	require.Equal(t, "tenant-a", store.touchedScopes[0].TenantID)
	require.Equal(t, "proj-a", store.touchedScopes[0].ProjectID)
}

func TestRecordAccessSurvivesAProviderWithNoStore(t *testing.T) {
	// The provider is constructed with a nil store in places; a counter bump must not panic there.
	provider := &StoreFactProvider{accessCounts: map[string]int{}, scope: rlmscope.Default()}
	provider.RecordAccess("fact-1")
	require.Equal(t, 1, provider.accessCounts["fact-1"])
}
