package sqlite

import (
	"context"
	"testing"
	"time"

	"github.com/sentinel-community/gomcp/internal/domain/memory"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func newTestFactRepo(t *testing.T) *FactRepo {
	t.Helper()
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { db.Close() })

	repo, err := NewFactRepo(db)
	require.NoError(t, err)
	return repo
}

func TestFactRepo_Add_Get(t *testing.T) {
	repo := newTestFactRepo(t)
	ctx := context.Background()

	fact := memory.NewFact("Go is fast", memory.LevelProject, "core", "engine")
	fact.Confidence = 0.95
	fact.Source = "manual"
	fact.CodeRef = "main.go:42"

	err := repo.Add(ctx, fact)
	require.NoError(t, err)

	got, err := repo.Get(ctx, fact.ID)
	require.NoError(t, err)
	require.NotNil(t, got)

	assert.Equal(t, fact.ID, got.ID)
	assert.Equal(t, fact.Content, got.Content)
	assert.Equal(t, fact.Level, got.Level)
	assert.Equal(t, fact.Domain, got.Domain)
	assert.Equal(t, fact.Module, got.Module)
	assert.Equal(t, fact.CodeRef, got.CodeRef)
	assert.InDelta(t, fact.Confidence, got.Confidence, 0.001)
	assert.Equal(t, fact.Source, got.Source)
	assert.False(t, got.IsStale)
	assert.False(t, got.IsArchived)
}

func TestFactRepo_Get_NotFound(t *testing.T) {
	repo := newTestFactRepo(t)
	ctx := context.Background()

	got, err := repo.Get(ctx, "nonexistent")
	assert.Error(t, err)
	assert.Nil(t, got)
}

func TestFactRepo_Update(t *testing.T) {
	repo := newTestFactRepo(t)
	ctx := context.Background()

	fact := memory.NewFact("original", memory.LevelProject, "core", "")
	require.NoError(t, repo.Add(ctx, fact))

	fact.Content = "updated"
	fact.IsStale = true
	require.NoError(t, repo.Update(ctx, fact))

	got, err := repo.Get(ctx, fact.ID)
	require.NoError(t, err)
	assert.Equal(t, "updated", got.Content)
	assert.True(t, got.IsStale)
}

func TestFactRepo_Delete(t *testing.T) {
	repo := newTestFactRepo(t)
	ctx := context.Background()

	fact := memory.NewFact("to delete", memory.LevelProject, "", "")
	require.NoError(t, repo.Add(ctx, fact))

	err := repo.Delete(ctx, fact.ID)
	require.NoError(t, err)

	got, err := repo.Get(ctx, fact.ID)
	assert.Error(t, err)
	assert.Nil(t, got)
}

func TestFactRepo_ListByDomain(t *testing.T) {
	repo := newTestFactRepo(t)
	ctx := context.Background()

	f1 := memory.NewFact("fact1", memory.LevelProject, "backend", "")
	f2 := memory.NewFact("fact2", memory.LevelDomain, "backend", "")
	f3 := memory.NewFact("fact3", memory.LevelProject, "frontend", "")
	f4 := memory.NewFact("stale", memory.LevelProject, "backend", "")
	f4.IsStale = true

	for _, f := range []*memory.Fact{f1, f2, f3, f4} {
		require.NoError(t, repo.Add(ctx, f))
	}

	// Without stale
	facts, err := repo.ListByDomain(ctx, "backend", false)
	require.NoError(t, err)
	assert.Len(t, facts, 2)

	// With stale
	facts, err = repo.ListByDomain(ctx, "backend", true)
	require.NoError(t, err)
	assert.Len(t, facts, 3)
}

func TestFactRepo_ListByLevel(t *testing.T) {
	repo := newTestFactRepo(t)
	ctx := context.Background()

	f1 := memory.NewFact("f1", memory.LevelProject, "", "")
	f2 := memory.NewFact("f2", memory.LevelProject, "", "")
	f3 := memory.NewFact("f3", memory.LevelDomain, "", "")

	for _, f := range []*memory.Fact{f1, f2, f3} {
		require.NoError(t, repo.Add(ctx, f))
	}

	facts, err := repo.ListByLevel(ctx, memory.LevelProject)
	require.NoError(t, err)
	assert.Len(t, facts, 2)
}

func TestFactRepo_ListDomains(t *testing.T) {
	repo := newTestFactRepo(t)
	ctx := context.Background()

	f1 := memory.NewFact("f1", memory.LevelProject, "backend", "")
	f2 := memory.NewFact("f2", memory.LevelProject, "frontend", "")
	f3 := memory.NewFact("f3", memory.LevelProject, "backend", "")

	for _, f := range []*memory.Fact{f1, f2, f3} {
		require.NoError(t, repo.Add(ctx, f))
	}

	domains, err := repo.ListDomains(ctx)
	require.NoError(t, err)
	assert.Len(t, domains, 2)
	assert.Contains(t, domains, "backend")
	assert.Contains(t, domains, "frontend")
}

func TestFactRepo_GetStale(t *testing.T) {
	repo := newTestFactRepo(t)
	ctx := context.Background()

	f1 := memory.NewFact("fresh", memory.LevelProject, "", "")
	f2 := memory.NewFact("stale", memory.LevelProject, "", "")
	f2.IsStale = true
	f3 := memory.NewFact("archived", memory.LevelProject, "", "")
	f3.IsStale = true
	f3.IsArchived = true

	for _, f := range []*memory.Fact{f1, f2, f3} {
		require.NoError(t, repo.Add(ctx, f))
	}

	// Without archived
	stale, err := repo.GetStale(ctx, false)
	require.NoError(t, err)
	assert.Len(t, stale, 1)

	// With archived
	stale, err = repo.GetStale(ctx, true)
	require.NoError(t, err)
	assert.Len(t, stale, 2)
}

func TestFactRepo_Search(t *testing.T) {
	repo := newTestFactRepo(t)
	ctx := context.Background()

	f1 := memory.NewFact("Go concurrency patterns", memory.LevelProject, "", "")
	f2 := memory.NewFact("Python is slow", memory.LevelProject, "", "")
	f3 := memory.NewFact("Go channels are great", memory.LevelDomain, "", "")

	for _, f := range []*memory.Fact{f1, f2, f3} {
		require.NoError(t, repo.Add(ctx, f))
	}

	results, err := repo.Search(ctx, "Go", 10)
	require.NoError(t, err)
	assert.Len(t, results, 2)
}

func TestFactRepo_GetExpired(t *testing.T) {
	repo := newTestFactRepo(t)
	ctx := context.Background()

	f1 := memory.NewFact("no ttl", memory.LevelProject, "", "")

	f2 := memory.NewFact("expired", memory.LevelProject, "", "")
	f2.TTL = &memory.TTLConfig{TTLSeconds: 1, OnExpire: memory.OnExpireMarkStale}
	f2.CreatedAt = time.Now().Add(-2 * time.Hour)
	f2.ValidFrom = f2.CreatedAt

	for _, f := range []*memory.Fact{f1, f2} {
		require.NoError(t, repo.Add(ctx, f))
	}

	expired, err := repo.GetExpired(ctx)
	require.NoError(t, err)
	assert.Len(t, expired, 1)
	assert.Equal(t, f2.ID, expired[0].ID)
}

func TestFactRepo_RefreshTTL(t *testing.T) {
	repo := newTestFactRepo(t)
	ctx := context.Background()

	f := memory.NewFact("refreshable", memory.LevelProject, "", "")
	f.TTL = &memory.TTLConfig{TTLSeconds: 3600, OnExpire: memory.OnExpireMarkStale}
	f.CreatedAt = time.Now().Add(-2 * time.Hour)
	f.ValidFrom = f.CreatedAt
	require.NoError(t, repo.Add(ctx, f))

	require.NoError(t, repo.RefreshTTL(ctx, f.ID))

	got, err := repo.Get(ctx, f.ID)
	require.NoError(t, err)
	assert.True(t, got.CreatedAt.After(f.CreatedAt))
}

func TestFactRepo_Stats(t *testing.T) {
	repo := newTestFactRepo(t)
	ctx := context.Background()

	f1 := memory.NewFact("f1", memory.LevelProject, "backend", "")
	f2 := memory.NewFact("f2", memory.LevelDomain, "backend", "")
	f2.IsStale = true
	f3 := memory.NewFact("f3", memory.LevelProject, "frontend", "")
	f3.Embedding = []float64{0.1, 0.2}

	for _, f := range []*memory.Fact{f1, f2, f3} {
		require.NoError(t, repo.Add(ctx, f))
	}

	stats, err := repo.Stats(ctx)
	require.NoError(t, err)
	assert.Equal(t, 3, stats.TotalFacts)
	assert.Equal(t, 2, stats.ByLevel[memory.LevelProject])
	assert.Equal(t, 1, stats.ByLevel[memory.LevelDomain])
	assert.Equal(t, 2, stats.ByDomain["backend"])
	assert.Equal(t, 1, stats.ByDomain["frontend"])
	assert.Equal(t, 1, stats.StaleCount)
	assert.Equal(t, 1, stats.WithEmbeddings)
}

func TestFactRepo_EmbeddingRoundTrip(t *testing.T) {
	repo := newTestFactRepo(t)
	ctx := context.Background()

	f := memory.NewFact("with embedding", memory.LevelProject, "", "")
	f.Embedding = []float64{0.1, 0.2, 0.3, -0.5}
	require.NoError(t, repo.Add(ctx, f))

	got, err := repo.Get(ctx, f.ID)
	require.NoError(t, err)
	require.Len(t, got.Embedding, 4)
	assert.InDelta(t, 0.1, got.Embedding[0], 0.0001)
	assert.InDelta(t, -0.5, got.Embedding[3], 0.0001)
}

func TestFactRepo_TTLConfigRoundTrip(t *testing.T) {
	repo := newTestFactRepo(t)
	ctx := context.Background()

	f := memory.NewFact("with ttl", memory.LevelProject, "", "")
	f.TTL = &memory.TTLConfig{
		TTLSeconds:     3600,
		RefreshTrigger: "main.go",
		OnExpire:       memory.OnExpireArchive,
	}
	require.NoError(t, repo.Add(ctx, f))

	got, err := repo.Get(ctx, f.ID)
	require.NoError(t, err)
	require.NotNil(t, got.TTL)
	assert.Equal(t, 3600, got.TTL.TTLSeconds)
	assert.Equal(t, "main.go", got.TTL.RefreshTrigger)
	assert.Equal(t, memory.OnExpireArchive, got.TTL.OnExpire)
}
