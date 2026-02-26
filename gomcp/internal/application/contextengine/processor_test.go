package contextengine

import (
	"context"
	"testing"
	"time"

	"github.com/sentinel-community/gomcp/internal/domain/memory"
	"github.com/sentinel-community/gomcp/internal/infrastructure/sqlite"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// --- mock FactStore for processor tests ---

type procMockFactStore struct {
	facts []*memory.Fact
}

func (m *procMockFactStore) Add(_ context.Context, f *memory.Fact) error {
	m.facts = append(m.facts, f)
	return nil
}
func (m *procMockFactStore) Get(_ context.Context, id string) (*memory.Fact, error) {
	for _, f := range m.facts {
		if f.ID == id {
			return f, nil
		}
	}
	return nil, nil
}
func (m *procMockFactStore) Update(_ context.Context, _ *memory.Fact) error { return nil }
func (m *procMockFactStore) Delete(_ context.Context, _ string) error       { return nil }
func (m *procMockFactStore) ListByDomain(_ context.Context, _ string, _ bool) ([]*memory.Fact, error) {
	return nil, nil
}
func (m *procMockFactStore) ListByLevel(_ context.Context, _ memory.HierLevel) ([]*memory.Fact, error) {
	return nil, nil
}
func (m *procMockFactStore) ListDomains(_ context.Context) ([]string, error) { return nil, nil }
func (m *procMockFactStore) GetStale(_ context.Context, _ bool) ([]*memory.Fact, error) {
	return nil, nil
}
func (m *procMockFactStore) Search(_ context.Context, query string, limit int) ([]*memory.Fact, error) {
	var results []*memory.Fact
	for _, f := range m.facts {
		if len(results) >= limit {
			break
		}
		if contains(f.Content, query) {
			results = append(results, f)
		}
	}
	return results, nil
}
func (m *procMockFactStore) GetExpired(_ context.Context) ([]*memory.Fact, error) { return nil, nil }
func (m *procMockFactStore) RefreshTTL(_ context.Context, _ string) error         { return nil }
func (m *procMockFactStore) Stats(_ context.Context) (*memory.FactStoreStats, error) {
	return &memory.FactStoreStats{}, nil
}

func contains(s, sub string) bool {
	return len(s) >= len(sub) && (s == sub || len(sub) == 0 ||
		(len(s) > 0 && len(sub) > 0 && containsStr(s, sub)))
}
func containsStr(s, sub string) bool {
	for i := 0; i <= len(s)-len(sub); i++ {
		if s[i:i+len(sub)] == sub {
			return true
		}
	}
	return false
}

// --- Tests ---

func TestInteractionProcessor_ProcessStartup_NoEntries(t *testing.T) {
	db, err := sqlite.OpenMemory()
	require.NoError(t, err)
	defer db.Close()

	repo, err := sqlite.NewInteractionLogRepo(db)
	require.NoError(t, err)

	store := &procMockFactStore{}
	proc := NewInteractionProcessor(repo, store)

	summary, err := proc.ProcessStartup(context.Background())
	require.NoError(t, err)
	assert.Empty(t, summary)
	assert.Empty(t, store.facts, "no facts should be created")
}

func TestInteractionProcessor_ProcessStartup_CreatesFactAndMarksProcessed(t *testing.T) {
	db, err := sqlite.OpenMemory()
	require.NoError(t, err)
	defer db.Close()

	repo, err := sqlite.NewInteractionLogRepo(db)
	require.NoError(t, err)

	ctx := context.Background()

	// Insert some tool calls
	require.NoError(t, repo.Record(ctx, "add_fact", map[string]interface{}{"content": "test fact about architecture"}))
	require.NoError(t, repo.Record(ctx, "search_facts", map[string]interface{}{"query": "security"}))
	require.NoError(t, repo.Record(ctx, "health", nil))
	require.NoError(t, repo.Record(ctx, "add_fact", map[string]interface{}{"content": "another fact"}))
	require.NoError(t, repo.Record(ctx, "dashboard", nil))

	store := &procMockFactStore{}
	proc := NewInteractionProcessor(repo, store)

	summary, err := proc.ProcessStartup(ctx)
	require.NoError(t, err)
	assert.NotEmpty(t, summary)
	assert.Contains(t, summary, "Session summary")
	assert.Contains(t, summary, "5 tool calls")
	assert.Contains(t, summary, "add_fact(2)")

	// Fact should be saved
	require.Len(t, store.facts, 1)
	assert.Equal(t, memory.LevelDomain, store.facts[0].Level)
	assert.Equal(t, "session-history", store.facts[0].Domain)
	assert.Equal(t, "auto:interaction-processor", store.facts[0].Source)

	// All entries should be marked processed
	_, unprocessed, err := repo.Count(ctx)
	require.NoError(t, err)
	assert.Equal(t, 0, unprocessed)
}

func TestInteractionProcessor_ProcessShutdown(t *testing.T) {
	db, err := sqlite.OpenMemory()
	require.NoError(t, err)
	defer db.Close()

	repo, err := sqlite.NewInteractionLogRepo(db)
	require.NoError(t, err)

	ctx := context.Background()
	require.NoError(t, repo.Record(ctx, "version", nil))
	require.NoError(t, repo.Record(ctx, "search_facts", map[string]interface{}{"query": "gomcp"}))

	store := &procMockFactStore{}
	proc := NewInteractionProcessor(repo, store)

	summary, err := proc.ProcessShutdown(ctx)
	require.NoError(t, err)
	assert.Contains(t, summary, "session ending")
	assert.Contains(t, summary, "2 tool calls")

	require.Len(t, store.facts, 1)
	assert.Equal(t, "auto:session-shutdown", store.facts[0].Source)
}

func TestBuildSessionSummary_ToolCounts(t *testing.T) {
	now := time.Now()
	entries := []sqlite.InteractionEntry{
		{ID: 1, ToolName: "add_fact", Timestamp: now},
		{ID: 2, ToolName: "add_fact", Timestamp: now},
		{ID: 3, ToolName: "add_fact", Timestamp: now},
		{ID: 4, ToolName: "search_facts", Timestamp: now},
		{ID: 5, ToolName: "health", Timestamp: now},
	}

	summary := buildSessionSummary(entries, "test")
	assert.Contains(t, summary, "5 tool calls")
	assert.Contains(t, summary, "add_fact(3)")
	assert.Contains(t, summary, "search_facts(1)")
	assert.Contains(t, summary, "health(1)")
}

func TestBuildSessionSummary_Duration(t *testing.T) {
	now := time.Now()
	entries := []sqlite.InteractionEntry{
		{ID: 1, ToolName: "a", Timestamp: now.Add(-30 * time.Minute)},
		{ID: 2, ToolName: "b", Timestamp: now},
	}

	summary := buildSessionSummary(entries, "test")
	assert.Contains(t, summary, "30m")
}

func TestBuildSessionSummary_Empty(t *testing.T) {
	summary := buildSessionSummary(nil, "test")
	assert.Empty(t, summary)
}

func TestBuildSessionSummary_Topics(t *testing.T) {
	now := time.Now()
	entries := []sqlite.InteractionEntry{
		{ID: 1, ToolName: "search_facts", ArgsJSON: `{"query":"architecture"}`, Timestamp: now},
		{ID: 2, ToolName: "add_fact", ArgsJSON: `{"content":"security review"}`, Timestamp: now},
	}

	summary := buildSessionSummary(entries, "test")
	assert.Contains(t, summary, "Topics:")
	assert.Contains(t, summary, "architecture")
}

func TestGetLastSessionSummary_Found(t *testing.T) {
	store := &procMockFactStore{}
	f := memory.NewFact("Session summary (test): 5 tool calls", memory.LevelDomain, "session-history", "")
	f.Source = "auto:session-shutdown"
	store.facts = append(store.facts, f)

	result := GetLastSessionSummary(context.Background(), store)
	assert.Contains(t, result, "Session summary")
}

func TestGetLastSessionSummary_NotFound(t *testing.T) {
	store := &procMockFactStore{}
	result := GetLastSessionSummary(context.Background(), store)
	assert.Empty(t, result)
}

func TestGetLastSessionSummary_SkipsStale(t *testing.T) {
	store := &procMockFactStore{}
	f := memory.NewFact("Session summary (test): old", memory.LevelDomain, "session-history", "")
	f.IsStale = true
	store.facts = append(store.facts, f)

	result := GetLastSessionSummary(context.Background(), store)
	assert.Empty(t, result)
}

func TestFormatDuration(t *testing.T) {
	assert.Equal(t, "30s", formatDuration(30*time.Second))
	assert.Equal(t, "5m", formatDuration(5*time.Minute))
	assert.Equal(t, "2h15m", formatDuration(2*time.Hour+15*time.Minute))
}

func TestExtractTopicsFromEntries(t *testing.T) {
	entries := []sqlite.InteractionEntry{
		{ArgsJSON: `{"query":"architecture"}`},
		{ArgsJSON: `{"content":"security review"}`},
		{ArgsJSON: ``}, // empty
	}

	topics := extractTopicsFromEntries(entries)
	assert.NotEmpty(t, topics)
}
