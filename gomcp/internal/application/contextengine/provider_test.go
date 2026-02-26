package contextengine

import (
	"context"
	"fmt"
	"sync"
	"testing"

	"github.com/sentinel-community/gomcp/internal/domain/memory"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// --- Mock FactStore for provider tests ---

type mockFactStore struct {
	mu          sync.Mutex
	facts       map[string]*memory.Fact
	searchFacts []*memory.Fact
	searchErr   error
	levelFacts  map[memory.HierLevel][]*memory.Fact
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

func (m *mockFactStore) GetExpired(_ context.Context) ([]*memory.Fact, error) {
	return nil, nil
}

func (m *mockFactStore) RefreshTTL(_ context.Context, _ string) error {
	return nil
}

func (m *mockFactStore) Stats(_ context.Context) (*memory.FactStoreStats, error) {
	return nil, nil
}

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

func TestStoreFactProvider_GetL0Facts_FromCache(t *testing.T) {
	store := newMockFactStore()
	cacheFact := memory.NewFact("Cached L0", memory.LevelProject, "arch", "")
	cache := &mockHotCache{l0Facts: []*memory.Fact{cacheFact}}

	provider := NewStoreFactProvider(store, cache)

	facts, err := provider.GetL0Facts()
	require.NoError(t, err)
	assert.Len(t, facts, 1)
	assert.Equal(t, "Cached L0", facts[0].Content)
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
