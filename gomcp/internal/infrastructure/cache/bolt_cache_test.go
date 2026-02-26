package cache

import (
	"context"
	"os"
	"path/filepath"
	"testing"

	"github.com/sentinel-community/gomcp/internal/domain/memory"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func newTestCache(t *testing.T) *BoltCache {
	t.Helper()
	dir := t.TempDir()
	path := filepath.Join(dir, "test_cache.db")

	cache, err := NewBoltCache(path)
	require.NoError(t, err)
	t.Cleanup(func() { cache.Close() })
	return cache
}

func TestBoltCache_WarmUp_GetL0Facts(t *testing.T) {
	cache := newTestCache(t)
	ctx := context.Background()

	facts := []*memory.Fact{
		memory.NewFact("Iron Law 1: TDD always", memory.LevelProject, "core", ""),
		memory.NewFact("Iron Law 2: No any types", memory.LevelProject, "core", ""),
		memory.NewFact("Architecture: Clean Architecture", memory.LevelProject, "arch", ""),
	}

	err := cache.WarmUp(ctx, facts)
	require.NoError(t, err)

	got, err := cache.GetL0Facts(ctx)
	require.NoError(t, err)
	assert.Len(t, got, 3)
}

func TestBoltCache_InvalidateFact(t *testing.T) {
	cache := newTestCache(t)
	ctx := context.Background()

	f := memory.NewFact("to invalidate", memory.LevelProject, "", "")
	require.NoError(t, cache.WarmUp(ctx, []*memory.Fact{f}))

	got, err := cache.GetL0Facts(ctx)
	require.NoError(t, err)
	assert.Len(t, got, 1)

	require.NoError(t, cache.InvalidateFact(ctx, f.ID))

	got, err = cache.GetL0Facts(ctx)
	require.NoError(t, err)
	assert.Len(t, got, 0)
}

func TestBoltCache_EmptyCache(t *testing.T) {
	cache := newTestCache(t)
	ctx := context.Background()

	got, err := cache.GetL0Facts(ctx)
	require.NoError(t, err)
	assert.Len(t, got, 0)
}

func TestBoltCache_RoundTrip_Preserves_Fields(t *testing.T) {
	cache := newTestCache(t)
	ctx := context.Background()

	f := memory.NewFact("test content", memory.LevelProject, "domain1", "module1")
	f.Confidence = 0.95
	f.Source = "consolidation"
	f.Embedding = []float64{0.1, 0.2, 0.3}

	require.NoError(t, cache.WarmUp(ctx, []*memory.Fact{f}))

	got, err := cache.GetL0Facts(ctx)
	require.NoError(t, err)
	require.Len(t, got, 1)

	assert.Equal(t, f.ID, got[0].ID)
	assert.Equal(t, f.Content, got[0].Content)
	assert.Equal(t, f.Domain, got[0].Domain)
	assert.Equal(t, f.Module, got[0].Module)
	assert.InDelta(t, f.Confidence, got[0].Confidence, 0.001)
	assert.Equal(t, f.Source, got[0].Source)
	assert.Len(t, got[0].Embedding, 3)
}

func TestBoltCache_Close_Reopen(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "persist.db")
	ctx := context.Background()

	// Create and populate cache.
	cache, err := NewBoltCache(path)
	require.NoError(t, err)

	f := memory.NewFact("persistent fact", memory.LevelProject, "", "")
	require.NoError(t, cache.WarmUp(ctx, []*memory.Fact{f}))
	require.NoError(t, cache.Close())

	// Reopen and verify data persists.
	cache2, err := NewBoltCache(path)
	require.NoError(t, err)
	defer cache2.Close()

	got, err := cache2.GetL0Facts(ctx)
	require.NoError(t, err)
	require.Len(t, got, 1)
	assert.Equal(t, "persistent fact", got[0].Content)
}

func TestBoltCache_InvalidateFact_NonExistent(t *testing.T) {
	cache := newTestCache(t)
	ctx := context.Background()

	// Should not error on non-existent ID.
	err := cache.InvalidateFact(ctx, "nonexistent-id")
	assert.NoError(t, err)
}

func TestBoltCache_FileCreated(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "subdir", "cache.db")

	cache, err := NewBoltCache(path)
	require.NoError(t, err)
	defer cache.Close()

	_, err = os.Stat(path)
	assert.NoError(t, err)
}
