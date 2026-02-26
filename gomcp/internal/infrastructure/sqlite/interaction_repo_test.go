package sqlite

import (
	"context"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func setupInteractionRepo(t *testing.T) *InteractionLogRepo {
	t.Helper()
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { db.Close() })
	repo, err := NewInteractionLogRepo(db)
	require.NoError(t, err)
	return repo
}

func TestNewInteractionLogRepo(t *testing.T) {
	repo := setupInteractionRepo(t)
	require.NotNil(t, repo)
}

func TestInteractionLogRepo_Record(t *testing.T) {
	repo := setupInteractionRepo(t)
	ctx := context.Background()

	err := repo.Record(ctx, "add_fact", map[string]interface{}{
		"content": "test fact",
		"level":   0,
	})
	require.NoError(t, err)

	total, unproc, err := repo.Count(ctx)
	require.NoError(t, err)
	assert.Equal(t, 1, total)
	assert.Equal(t, 1, unproc)
}

func TestInteractionLogRepo_Record_EmptyArgs(t *testing.T) {
	repo := setupInteractionRepo(t)
	ctx := context.Background()

	err := repo.Record(ctx, "health", nil)
	require.NoError(t, err)

	entries, err := repo.GetUnprocessed(ctx)
	require.NoError(t, err)
	require.Len(t, entries, 1)
	assert.Equal(t, "health", entries[0].ToolName)
	assert.Empty(t, entries[0].ArgsJSON)
}

func TestInteractionLogRepo_Record_TruncatesLongValues(t *testing.T) {
	repo := setupInteractionRepo(t)
	ctx := context.Background()

	longContent := make([]byte, 500)
	for i := range longContent {
		longContent[i] = 'x'
	}

	err := repo.Record(ctx, "add_fact", map[string]interface{}{
		"content": string(longContent),
	})
	require.NoError(t, err)

	entries, err := repo.GetUnprocessed(ctx)
	require.NoError(t, err)
	require.Len(t, entries, 1)
	// args_json should contain truncated value (200 chars + "...")
	assert.Contains(t, entries[0].ArgsJSON, "...")
	assert.Less(t, len(entries[0].ArgsJSON), 300)
}

func TestInteractionLogRepo_GetUnprocessed(t *testing.T) {
	repo := setupInteractionRepo(t)
	ctx := context.Background()

	_ = repo.Record(ctx, "add_fact", map[string]interface{}{"content": "a"})
	_ = repo.Record(ctx, "search_facts", map[string]interface{}{"query": "b"})
	_ = repo.Record(ctx, "health", nil)

	entries, err := repo.GetUnprocessed(ctx)
	require.NoError(t, err)
	assert.Len(t, entries, 3)
	// Ordered by id ASC
	assert.Equal(t, "add_fact", entries[0].ToolName)
	assert.Equal(t, "search_facts", entries[1].ToolName)
	assert.Equal(t, "health", entries[2].ToolName)
}

func TestInteractionLogRepo_MarkProcessed(t *testing.T) {
	repo := setupInteractionRepo(t)
	ctx := context.Background()

	_ = repo.Record(ctx, "tool_a", nil)
	_ = repo.Record(ctx, "tool_b", nil)

	entries, _ := repo.GetUnprocessed(ctx)
	require.Len(t, entries, 2)

	// Mark first as processed
	err := repo.MarkProcessed(ctx, []int64{entries[0].ID})
	require.NoError(t, err)

	remaining, _ := repo.GetUnprocessed(ctx)
	assert.Len(t, remaining, 1)
	assert.Equal(t, "tool_b", remaining[0].ToolName)

	total, unproc, _ := repo.Count(ctx)
	assert.Equal(t, 2, total)
	assert.Equal(t, 1, unproc)
}

func TestInteractionLogRepo_MarkProcessed_Empty(t *testing.T) {
	repo := setupInteractionRepo(t)
	err := repo.MarkProcessed(context.Background(), nil)
	require.NoError(t, err)
}

func TestInteractionLogRepo_Prune(t *testing.T) {
	repo := setupInteractionRepo(t)
	ctx := context.Background()

	// Insert and mark as processed
	_ = repo.Record(ctx, "old_tool", nil)
	entries, _ := repo.GetUnprocessed(ctx)
	_ = repo.MarkProcessed(ctx, []int64{entries[0].ID})

	// Prune with 0 duration should delete all processed
	deleted, err := repo.Prune(ctx, 0)
	require.NoError(t, err)
	assert.Equal(t, int64(1), deleted)

	total, _, _ := repo.Count(ctx)
	assert.Equal(t, 0, total)
}

func TestInteractionLogRepo_Prune_KeepsUnprocessed(t *testing.T) {
	repo := setupInteractionRepo(t)
	ctx := context.Background()

	_ = repo.Record(ctx, "unprocessed_tool", nil)

	// Prune should not delete unprocessed entries
	deleted, err := repo.Prune(ctx, 0)
	require.NoError(t, err)
	assert.Equal(t, int64(0), deleted)

	total, _, _ := repo.Count(ctx)
	assert.Equal(t, 1, total)
}

func TestInteractionLogRepo_Timestamps(t *testing.T) {
	repo := setupInteractionRepo(t)
	ctx := context.Background()

	before := time.Now().UTC()
	_ = repo.Record(ctx, "timed_tool", nil)
	after := time.Now().UTC()

	entries, _ := repo.GetUnprocessed(ctx)
	require.Len(t, entries, 1)

	ts := entries[0].Timestamp
	assert.False(t, ts.Before(before.Add(-time.Second)))
	assert.False(t, ts.After(after.Add(time.Second)))
}

func TestInteractionLogRepo_MultipleRecords_Count(t *testing.T) {
	repo := setupInteractionRepo(t)
	ctx := context.Background()

	for i := 0; i < 10; i++ {
		_ = repo.Record(ctx, "tool", nil)
	}

	total, unproc, err := repo.Count(ctx)
	require.NoError(t, err)
	assert.Equal(t, 10, total)
	assert.Equal(t, 10, unproc)
}
