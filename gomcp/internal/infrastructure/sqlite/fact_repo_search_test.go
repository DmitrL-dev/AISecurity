package sqlite

import (
	"context"
	"fmt"
	"testing"

	"github.com/syntrex/gomcp/internal/domain/memory"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestFactRepo_SearchByVector_RanksByCosine(t *testing.T) {
	repo := newTestFactRepo(t)
	ctx := context.Background()

	// Query at 45°. f2 is exactly aligned (cos=1.0); f1 is 45° off (cos≈0.707);
	// f3 points opposite (cos=-1.0). Ranking must be f2 > f1 > f3.
	f1 := memory.NewFact("at zero", memory.LevelProject, "", "")
	f1.Embedding = []float64{1, 0}
	f2 := memory.NewFact("at fortyfive", memory.LevelProject, "", "")
	f2.Embedding = []float64{1, 1}
	f3 := memory.NewFact("opposite", memory.LevelProject, "", "")
	f3.Embedding = []float64{-1, -1}

	for _, f := range []*memory.Fact{f1, f2, f3} {
		require.NoError(t, repo.Add(ctx, f))
	}

	queryVec := []float64{1, 1}
	results, err := repo.SearchByVector(ctx, queryVec, 10)
	require.NoError(t, err)
	require.Len(t, results, 3)

	assert.Equal(t, f2.ID, results[0].ID, "expected f2 (perfect alignment) ranked first")
	assert.Equal(t, f1.ID, results[1].ID, "expected f1 (45° off) ranked second")
	assert.Equal(t, f3.ID, results[2].ID, "expected f3 (opposite direction) ranked last")
}

func TestFactRepo_SearchByVector_EmptyQueryReturnsNil(t *testing.T) {
	repo := newTestFactRepo(t)
	ctx := context.Background()

	f := memory.NewFact("any", memory.LevelProject, "", "")
	f.Embedding = []float64{1, 2, 3}
	require.NoError(t, repo.Add(ctx, f))

	results, err := repo.SearchByVector(ctx, []float64{}, 10)
	require.NoError(t, err)
	assert.Nil(t, results)

	results, err = repo.SearchByVector(ctx, nil, 10)
	require.NoError(t, err)
	assert.Nil(t, results)
}

func TestFactRepo_SearchByVector_SkipsFactsWithoutEmbedding(t *testing.T) {
	repo := newTestFactRepo(t)
	ctx := context.Background()

	withEmb := memory.NewFact("has embedding", memory.LevelProject, "", "")
	withEmb.Embedding = []float64{0.5, 0.5}
	noEmb := memory.NewFact("no embedding", memory.LevelProject, "", "")

	require.NoError(t, repo.Add(ctx, withEmb))
	require.NoError(t, repo.Add(ctx, noEmb))

	results, err := repo.SearchByVector(ctx, []float64{1, 1}, 10)
	require.NoError(t, err)
	require.Len(t, results, 1)
	assert.Equal(t, withEmb.ID, results[0].ID)
}

func TestFactRepo_SearchByVector_SkipsArchived(t *testing.T) {
	repo := newTestFactRepo(t)
	ctx := context.Background()

	live := memory.NewFact("live", memory.LevelProject, "", "")
	live.Embedding = []float64{1, 0}
	archived := memory.NewFact("archived", memory.LevelProject, "", "")
	archived.Embedding = []float64{1, 0}
	archived.IsArchived = true

	require.NoError(t, repo.Add(ctx, live))
	require.NoError(t, repo.Add(ctx, archived))

	results, err := repo.SearchByVector(ctx, []float64{1, 0}, 10)
	require.NoError(t, err)
	require.Len(t, results, 1)
	assert.Equal(t, live.ID, results[0].ID)
}

func TestFactRepo_SearchByVector_SkipsDimensionMismatch(t *testing.T) {
	repo := newTestFactRepo(t)
	ctx := context.Background()

	dim2 := memory.NewFact("dim2", memory.LevelProject, "", "")
	dim2.Embedding = []float64{1, 0}
	dim3 := memory.NewFact("dim3", memory.LevelProject, "", "")
	dim3.Embedding = []float64{1, 0, 0}

	require.NoError(t, repo.Add(ctx, dim2))
	require.NoError(t, repo.Add(ctx, dim3))

	// Query in 2D — only dim2 fact must match.
	results, err := repo.SearchByVector(ctx, []float64{1, 0}, 10)
	require.NoError(t, err)
	require.Len(t, results, 1)
	assert.Equal(t, dim2.ID, results[0].ID)
}

func TestFactRepo_SearchByVector_RespectsLimit(t *testing.T) {
	repo := newTestFactRepo(t)
	ctx := context.Background()

	// Distinct content per fact. This loop used to store five facts all named "f", which relied on
	// the store accepting duplicate content — it no longer does, and it never meant to: an embedding
	// is a function of the text, so identical text with five different vectors is a situation real
	// data cannot produce. The limit is what this test is about, and five distinct facts exercise it
	// the same way.
	for i := 0; i < 5; i++ {
		f := memory.NewFact(fmt.Sprintf("fact %d", i), memory.LevelProject, "", "")
		f.Embedding = []float64{float64(i), 0}
		require.NoError(t, repo.Add(ctx, f))
	}

	results, err := repo.SearchByVector(ctx, []float64{1, 0}, 2)
	require.NoError(t, err)
	assert.Len(t, results, 2)
}
