package tools

import (
	"context"
	"math"
	"testing"

	"github.com/syntrex/gomcp/internal/domain/memory"
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func newTestCentroidService(t *testing.T) (*CentroidService, *sqlite.FactRepo) {
	t.Helper()
	db, err := sqlite.OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { db.Close() })
	factRepo, err := sqlite.NewFactRepo(db)
	require.NoError(t, err)
	centroidRepo, err := sqlite.NewCentroidRepo(db)
	require.NoError(t, err)
	return NewCentroidService(factRepo, centroidRepo), factRepo
}

func addEmbedded(t *testing.T, repo *sqlite.FactRepo, content, domain string, vec []float64) *memory.Fact {
	t.Helper()
	f := memory.NewFact(content, memory.LevelDomain, domain, "")
	f.Embedding = vec
	require.NoError(t, repo.Add(context.Background(), f))
	return f
}

func TestMeanEmbedding_PicksDominantDimensionAndNormalises(t *testing.T) {
	facts := []*memory.Fact{
		{Embedding: []float64{1, 0}},
		{Embedding: []float64{0, 1}},
		{Embedding: []float64{1, 1}},
		// Mismatched-dim fact must be skipped, not crash the call.
		{Embedding: []float64{1, 0, 0}},
	}
	mean, count, err := MeanEmbedding(facts)
	require.NoError(t, err)
	assert.Equal(t, 3, count)
	require.Len(t, mean, 2)

	// Mean before normalisation: ((1+0+1)/3, (0+1+1)/3) = (2/3, 2/3)
	// Normalised: each / sqrt(8/9) = (sqrt(2)/2, sqrt(2)/2)
	expected := math.Sqrt(2) / 2
	assert.InDelta(t, expected, mean[0], 1e-6)
	assert.InDelta(t, expected, mean[1], 1e-6)

	// Unit vector check.
	var n float64
	for _, v := range mean {
		n += v * v
	}
	assert.InDelta(t, 1.0, math.Sqrt(n), 1e-6)
}

func TestMeanEmbedding_EmptyOrAllSkipped(t *testing.T) {
	mean, count, err := MeanEmbedding(nil)
	require.NoError(t, err)
	assert.Nil(t, mean)
	assert.Equal(t, 0, count)

	skipped := []*memory.Fact{
		{Embedding: nil},
		{Embedding: []float64{1, 0}, IsArchived: true},
		{Embedding: []float64{1, 0}, IsStale: true},
	}
	mean, count, err = MeanEmbedding(skipped)
	require.NoError(t, err)
	assert.Nil(t, mean)
	assert.Equal(t, 0, count)
}

func TestCentroidService_Recompute_StoresCentroid(t *testing.T) {
	svc, repo := newTestCentroidService(t)
	ctx := context.Background()

	addEmbedded(t, repo, "f1", "alpha", []float64{1, 0})
	addEmbedded(t, repo, "f2", "alpha", []float64{0, 1})
	addEmbedded(t, repo, "f3", "alpha", []float64{1, 1})

	c, err := svc.Recompute(ctx, "alpha")
	require.NoError(t, err)
	require.NotNil(t, c)
	assert.Equal(t, "alpha", c.Domain)
	assert.Equal(t, 3, c.FactCount)
	require.Len(t, c.Vector, 2)

	// Stored persistently.
	all, err := svc.List(ctx)
	require.NoError(t, err)
	require.Len(t, all, 1)
	assert.Equal(t, "alpha", all[0].Domain)
}

func TestCentroidService_Recompute_NoEmbeddings_DeletesExisting(t *testing.T) {
	svc, repo := newTestCentroidService(t)
	ctx := context.Background()

	// Seed: 1 fact with embedding → centroid present.
	addEmbedded(t, repo, "f1", "transient", []float64{1, 0})
	_, err := svc.Recompute(ctx, "transient")
	require.NoError(t, err)
	all, _ := svc.List(ctx)
	require.Len(t, all, 1)

	// Now mark it archived (stops contributing). Recompute must drop centroid.
	facts, err := repo.ListByDomain(ctx, "transient", false)
	require.NoError(t, err)
	require.Len(t, facts, 1)
	facts[0].Archive()
	require.NoError(t, repo.Update(ctx, facts[0]))

	c, err := svc.Recompute(ctx, "transient")
	require.NoError(t, err)
	assert.Nil(t, c)

	all, err = svc.List(ctx)
	require.NoError(t, err)
	assert.Empty(t, all)
}

func TestCentroidService_RecomputeAll_PrunesStaleDomains(t *testing.T) {
	svc, repo := newTestCentroidService(t)
	ctx := context.Background()

	// Pre-seed a centroid for a domain that will have no live facts.
	require.NoError(t, repo.Add(ctx, embFact("f0", "ghost", []float64{1, 0})))
	_, err := svc.Recompute(ctx, "ghost")
	require.NoError(t, err)

	// Archive the only fact in "ghost" so it has no live embeddings.
	ghostFacts, _ := repo.ListByDomain(ctx, "ghost", false)
	for _, f := range ghostFacts {
		f.Archive()
		_ = repo.Update(ctx, f)
	}

	// Add fresh embeddings for two new domains.
	addEmbedded(t, repo, "f1", "alpha", []float64{1, 0})
	addEmbedded(t, repo, "f2", "beta", []float64{0, 1})

	written, err := svc.RecomputeAll(ctx)
	require.NoError(t, err)
	assert.Equal(t, 2, written, "only alpha and beta should produce centroids")

	all, err := svc.List(ctx)
	require.NoError(t, err)
	domains := []string{}
	for _, c := range all {
		domains = append(domains, c.Domain)
	}
	assert.ElementsMatch(t, []string{"alpha", "beta"}, domains)
}

func embFact(content, domain string, vec []float64) *memory.Fact {
	f := memory.NewFact(content, memory.LevelDomain, domain, "")
	f.Embedding = vec
	return f
}

func TestCentroidService_SearchDomainsByVector_RanksByCosine(t *testing.T) {
	svc, repo := newTestCentroidService(t)
	ctx := context.Background()

	addEmbedded(t, repo, "ax", "alignedDomain", []float64{1, 0})
	addEmbedded(t, repo, "bx", "perpendicularDomain", []float64{0, 1})
	addEmbedded(t, repo, "cx", "oppositeDomain", []float64{-1, 0})

	_, err := svc.RecomputeAll(ctx)
	require.NoError(t, err)

	results, err := svc.SearchDomainsByVector(ctx, []float64{1, 0}, 10)
	require.NoError(t, err)
	require.Len(t, results, 3)
	assert.Equal(t, "alignedDomain", results[0].Centroid.Domain)
	assert.Equal(t, "oppositeDomain", results[2].Centroid.Domain)
}

func TestCentroidService_SearchDomainsByVector_EmptyQueryReturnsNil(t *testing.T) {
	svc, _ := newTestCentroidService(t)
	results, err := svc.SearchDomainsByVector(context.Background(), nil, 10)
	require.NoError(t, err)
	assert.Nil(t, results)
}

func TestCentroidService_Recompute_RequiresDomain(t *testing.T) {
	svc, _ := newTestCentroidService(t)
	_, err := svc.Recompute(context.Background(), "")
	assert.Error(t, err)
}
