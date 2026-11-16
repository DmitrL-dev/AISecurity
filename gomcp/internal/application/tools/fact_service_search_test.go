package tools

import (
	"context"
	"testing"

	"github.com/syntrex/gomcp/internal/domain/memory"
	"github.com/syntrex/gomcp/internal/domain/vectorstore"
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// stubEmbedder returns a deterministic embedding controlled by the test.
type stubEmbedder struct {
	dim   int
	embed func(text string) []float64
}

func (e *stubEmbedder) Embed(_ context.Context, text string) ([]float64, error) {
	return e.embed(text), nil
}
func (e *stubEmbedder) Dimension() int               { return e.dim }
func (e *stubEmbedder) Name() string                 { return "stub" }
func (e *stubEmbedder) Mode() vectorstore.OracleMode { return vectorstore.OracleModeFull }

// addFactWithEmbedding seeds a fact directly via the underlying repo so the
// embedding survives the round trip (FactService.AddFact does not accept one).
func addFactWithEmbedding(t *testing.T, svc *FactService, content string, vec []float64) *memory.Fact {
	t.Helper()
	f := memory.NewFact(content, memory.LevelProject, "", "")
	f.Embedding = vec
	require.NoError(t, svc.Store().Add(context.Background(), f))
	return f
}

func newTestFactServiceWithSynapses(t *testing.T) (*FactService, *sqlite.SynapseRepo) {
	t.Helper()
	db, err := sqlite.OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { db.Close() })

	factRepo, err := sqlite.NewFactRepo(db)
	require.NoError(t, err)
	synapseRepo := sqlite.NewSynapseRepo(db)
	return NewFactService(factRepo, nil).WithSynapseStore(synapseRepo), synapseRepo
}

func TestFactService_HasEmbedder(t *testing.T) {
	svc := newTestFactService(t)
	assert.False(t, svc.HasEmbedder())

	svc.SetEmbedder(&stubEmbedder{dim: 2, embed: func(string) []float64 { return []float64{1, 0} }})
	assert.True(t, svc.HasEmbedder())

	svc.SetEmbedder(nil)
	assert.False(t, svc.HasEmbedder())
}

func TestFactService_SearchFactsSemantic_RequiresEmbedder(t *testing.T) {
	svc := newTestFactService(t)
	ctx := context.Background()

	_, err := svc.SearchFactsSemantic(ctx, "anything", 10)
	assert.Error(t, err, "semantic search must error when no embedder configured")
}

func TestFactService_SearchFactsSemantic_RanksByCosine(t *testing.T) {
	svc := newTestFactService(t)
	ctx := context.Background()

	// Embedder that maps any query to direction (1, 0).
	svc.SetEmbedder(&stubEmbedder{
		dim:   2,
		embed: func(string) []float64 { return []float64{1, 0} },
	})

	aligned := addFactWithEmbedding(t, svc, "aligned", []float64{1, 0})
	orthogonal := addFactWithEmbedding(t, svc, "orthogonal", []float64{0, 1})
	_ = orthogonal

	results, err := svc.SearchFactsSemantic(ctx, "ignored by stub", 10)
	require.NoError(t, err)
	require.NotEmpty(t, results)
	assert.Equal(t, aligned.ID, results[0].ID)
}

func TestFactService_SearchFactsHybrid_FallsBackOnNoEmbedder(t *testing.T) {
	svc := newTestFactService(t)
	ctx := context.Background()

	_, err := svc.AddFact(ctx, AddFactParams{Content: "hello world", Level: 0})
	require.NoError(t, err)
	_, err = svc.AddFact(ctx, AddFactParams{Content: "goodbye", Level: 0})
	require.NoError(t, err)

	// No embedder set — hybrid must degrade to pure keyword.
	results, err := svc.SearchFactsHybrid(ctx, "hello", 10)
	require.NoError(t, err)
	require.Len(t, results, 1)
	assert.Equal(t, "hello world", results[0].Content)
}

func TestFactService_SearchFactsHybrid_UnionsKeywordAndSemantic(t *testing.T) {
	svc := newTestFactService(t)
	ctx := context.Background()

	// Embedder maps query → direction (1,0); only semantic-only fact has matching embedding.
	svc.SetEmbedder(&stubEmbedder{
		dim:   2,
		embed: func(string) []float64 { return []float64{1, 0} },
	})

	// Fact A: matches by keyword "alpha", no embedding (keyword-only hit).
	keywordOnly := memory.NewFact("alpha keyword payload", memory.LevelProject, "", "")
	require.NoError(t, svc.Store().Add(ctx, keywordOnly))

	// Fact B: no keyword match, but embedding aligns with the query (semantic-only hit).
	semanticOnly := memory.NewFact("zeta only", memory.LevelProject, "", "")
	semanticOnly.Embedding = []float64{1, 0}
	require.NoError(t, svc.Store().Add(ctx, semanticOnly))

	// Fact C: matches both — same keyword and aligned embedding.
	both := memory.NewFact("alpha resonance", memory.LevelProject, "", "")
	both.Embedding = []float64{0.95, 0.05}
	require.NoError(t, svc.Store().Add(ctx, both))

	results, err := svc.SearchFactsHybrid(ctx, "alpha", 10)
	require.NoError(t, err)

	ids := map[string]bool{}
	for _, f := range results {
		ids[f.ID] = true
	}
	assert.True(t, ids[keywordOnly.ID], "keyword-only fact must be in hybrid result")
	assert.True(t, ids[semanticOnly.ID], "semantic-only fact must be in hybrid result")
	assert.True(t, ids[both.ID], "fact matching both must be in hybrid result, deduped to single entry")
	assert.Len(t, results, 3, "no fact should appear twice")
}

func TestFactService_SearchFactsHybrid_ExpandsVerifiedSynapses(t *testing.T) {
	svc, synapseRepo := newTestFactServiceWithSynapses(t)
	ctx := context.Background()

	direct := memory.NewFact("alpha gateway", memory.LevelProject, "", "")
	linked := memory.NewFact("rollout checklist", memory.LevelProject, "", "")
	unlinked := memory.NewFact("unrelated checklist", memory.LevelProject, "", "")
	require.NoError(t, svc.Store().Add(ctx, direct))
	require.NoError(t, svc.Store().Add(ctx, linked))
	require.NoError(t, svc.Store().Add(ctx, unlinked))

	id, err := synapseRepo.Create(ctx, direct.ID, linked.ID, 0.94)
	require.NoError(t, err)
	require.NoError(t, synapseRepo.Accept(ctx, id))

	results, err := svc.SearchFactsHybrid(ctx, "alpha", 10)
	require.NoError(t, err)

	ids := map[string]bool{}
	for _, f := range results {
		ids[f.ID] = true
	}
	assert.True(t, ids[direct.ID], "direct keyword hit must be present")
	assert.True(t, ids[linked.ID], "accepted synapse neighbor must be present")
	assert.False(t, ids[unlinked.ID], "unlinked fact must not be pulled in")
}

func TestFactService_SearchFactsWithMode_DispatchesCorrectly(t *testing.T) {
	svc := newTestFactService(t)
	ctx := context.Background()

	// Seed BOTH facts via the direct store path so AddFact's auto-embed
	// doesn't muddy the dispatch test — this test isolates the dispatch
	// logic, not the embed-on-add behaviour (which has its own tests).
	keywordOnly := memory.NewFact("rare-keyword-token", memory.LevelProject, "", "")
	require.NoError(t, svc.Store().Add(ctx, keywordOnly))

	semanticOnly := memory.NewFact("unrelated content", memory.LevelProject, "", "")
	semanticOnly.Embedding = []float64{1, 0}
	require.NoError(t, svc.Store().Add(ctx, semanticOnly))

	// Embedder mapping query → (1, 0) so semanticOnly aligns and
	// keywordOnly (no embedding) falls through.
	svc.SetEmbedder(&stubEmbedder{
		dim:   2,
		embed: func(string) []float64 { return []float64{1, 0} },
	})

	t.Run("keyword mode returns only LIKE matches", func(t *testing.T) {
		r, err := svc.SearchFactsWithMode(ctx, "rare-keyword-token", 10, ModeKeyword)
		require.NoError(t, err)
		require.Len(t, r, 1)
		assert.Equal(t, keywordOnly.ID, r[0].ID)
	})

	t.Run("semantic mode returns only embedding matches", func(t *testing.T) {
		r, err := svc.SearchFactsWithMode(ctx, "rare-keyword-token", 10, ModeSemantic)
		require.NoError(t, err)
		// Only semanticOnly carries an embedding — must rank first and alone.
		require.Len(t, r, 1)
		assert.Equal(t, semanticOnly.ID, r[0].ID)
	})

	t.Run("hybrid is the default for unknown mode", func(t *testing.T) {
		r, err := svc.SearchFactsWithMode(ctx, "rare-keyword-token", 10, SearchMode("garbage"))
		require.NoError(t, err)
		ids := map[string]bool{}
		for _, f := range r {
			ids[f.ID] = true
		}
		assert.True(t, ids[keywordOnly.ID])
		assert.True(t, ids[semanticOnly.ID])
	})
}

func TestFactService_SearchFacts_KeywordRegression(t *testing.T) {
	// Existing API must keep working unchanged after extension.
	svc := newTestFactService(t)
	ctx := context.Background()

	_, err := svc.AddFact(ctx, AddFactParams{Content: "Go concurrency patterns", Level: 0})
	require.NoError(t, err)
	_, err = svc.AddFact(ctx, AddFactParams{Content: "Python is slow", Level: 0})
	require.NoError(t, err)

	results, err := svc.SearchFacts(ctx, "Go", 10)
	require.NoError(t, err)
	assert.Len(t, results, 1)
}

func TestFactService_AddFact_WithEmbedder_AttachesEmbedding(t *testing.T) {
	svc := newTestFactService(t)
	ctx := context.Background()

	expected := []float64{0.7, 0.1, 0.0, -0.4}
	svc.SetEmbedder(&stubEmbedder{
		dim:   4,
		embed: func(string) []float64 { return expected },
	})

	fact, err := svc.AddFact(ctx, AddFactParams{Content: "embed-me", Level: 0})
	require.NoError(t, err)
	assert.Equal(t, expected, fact.Embedding,
		"AddFact must populate fact.Embedding when an embedder is configured")

	// Round-trip through the store: embedding must persist.
	got, err := svc.GetFact(ctx, fact.ID)
	require.NoError(t, err)
	assert.Equal(t, expected, got.Embedding)
}

func TestFactService_AddFact_NoEmbedder_NoEmbedding(t *testing.T) {
	// Regression: behaviour without an embedder is unchanged — embedding
	// stays empty, AddFact still succeeds.
	svc := newTestFactService(t)
	ctx := context.Background()

	fact, err := svc.AddFact(ctx, AddFactParams{Content: "no-embedder", Level: 0})
	require.NoError(t, err)
	assert.Empty(t, fact.Embedding)
}

func TestFactService_AddFact_EmbedderError_DoesNotBlockAdd(t *testing.T) {
	// Embedder failure must never cause AddFact to fail — memory persistence
	// is more important than embedding availability.
	svc := newTestFactService(t)
	ctx := context.Background()
	svc.SetEmbedder(&stubEmbedder{
		dim:   4,
		embed: func(string) []float64 { return nil }, // simulate empty result
	})

	fact, err := svc.AddFact(ctx, AddFactParams{Content: "anything", Level: 0})
	require.NoError(t, err)
	assert.Empty(t, fact.Embedding, "graceful degradation — fact stored without vector")
}

func TestFactService_AddGene_WithEmbedder_AttachesEmbedding(t *testing.T) {
	svc := newTestFactService(t)
	ctx := context.Background()

	expected := []float64{0.0, 1.0, 0.0, 0.0}
	svc.SetEmbedder(&stubEmbedder{
		dim:   4,
		embed: func(string) []float64 { return expected },
	})

	gene, err := svc.AddGene(ctx, AddGeneParams{Content: "survival invariant", Domain: "core"})
	require.NoError(t, err)
	assert.Equal(t, expected, gene.Embedding)
	assert.True(t, gene.IsGene, "gene flag must still hold")
}
