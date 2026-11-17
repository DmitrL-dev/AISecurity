package tools

import (
	"context"
	"fmt"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/syntrex/gomcp/internal/domain/memory"
	"github.com/syntrex/gomcp/internal/domain/vectorstore"
)

type degradedStubEmbedder struct{ stubEmbedder }

func (e *degradedStubEmbedder) Mode() vectorstore.OracleMode { return vectorstore.OracleModeDegraded }

func factsNamed(names ...string) []*memory.Fact {
	out := make([]*memory.Fact, len(names))
	for i, n := range names {
		out[i] = &memory.Fact{ID: n, Content: n}
	}
	return out
}

func ids(facts []*memory.Fact) []string {
	out := make([]string, len(facts))
	for i, f := range facts {
		out[i] = f.ID
	}
	return out
}

// The defect this replaces: the semantic list was emitted first and filled the
// page, so a keyword match never appeared. A full page of semantic results must
// not push out the only fact the keyword list found.
func TestHybrid_KeywordMatchSurvivesAFullSemanticPage(t *testing.T) {
	for _, mode := range []vectorstore.OracleMode{vectorstore.OracleModeFull, vectorstore.OracleModeDegraded} {
		t.Run(mode.String(), func(t *testing.T) {
			svc := newTestFactService(t)
			ctx := context.Background()
			stub := stubEmbedder{dim: 2, embed: func(string) []float64 { return []float64{1, 0} }}
			if mode == vectorstore.OracleModeDegraded {
				svc.SetEmbedder(&degradedStubEmbedder{stub})
			} else {
				svc.SetEmbedder(&stub)
			}
			for i := 0; i < 12; i++ {
				addFactWithEmbedding(t, svc, fmt.Sprintf("noise %02d", i), []float64{1, 0.01 * float64(i)})
			}
			target := addFactWithEmbedding(t, svc, "the PYO3_PYTHON variable", []float64{0, 1})

			results, err := svc.SearchFactsHybrid(ctx, "PYO3_PYTHON", 5)
			require.NoError(t, err)
			require.NotEmpty(t, results)
			assert.Contains(t, ids(results), target.ID)
			if mode == vectorstore.OracleModeDegraded {
				assert.Equal(t, target.ID, results[0].ID, "degraded mode puts keyword matches first")
			}
		})
	}
}

func TestFuse_FactInBothListsOutranksEitherAlone(t *testing.T) {
	semantic := factsNamed("s1", "both", "s3")
	keyword := factsNamed("k1", "both", "k3")
	got := fuseHybridResults(semantic, keyword, 3, 1)
	assert.Equal(t, "both", got[0].ID)
}

func TestFuse_ZeroWeightKeepsKeywordOrderThenSemanticOrder(t *testing.T) {
	semantic := factsNamed("s1", "k2", "s2", "s3")
	keyword := factsNamed("k1", "k2", "k3")
	got := fuseHybridResults(semantic, keyword, 6, 0)
	assert.Equal(t, []string{"k1", "k2", "k3", "s1", "s2", "s3"}, ids(got))
}

func TestFuse_ListRepeatingAFactCountsItOnce(t *testing.T) {
	keyword := factsNamed("a", "b", "a")
	got := fuseHybridResults(nil, keyword, 5, 1)
	assert.Equal(t, []string{"a", "b"}, ids(got))
}

func TestFuse_DegradedEmbedderGetsTheDegradedWeight(t *testing.T) {
	svc := newTestFactService(t)
	assert.Equal(t, 1.0, svc.semanticFusionWeight(), "no embedder")
	svc.SetEmbedder(&stubEmbedder{dim: 2, embed: func(string) []float64 { return []float64{1, 0} }})
	assert.Equal(t, 1.0, svc.semanticFusionWeight(), "full embedder")
	svc.SetEmbedder(&degradedStubEmbedder{stubEmbedder{dim: 2, embed: func(string) []float64 { return []float64{1, 0} }}})
	assert.Equal(t, degradedSemanticWeight, svc.semanticFusionWeight(), "degraded embedder")
}
