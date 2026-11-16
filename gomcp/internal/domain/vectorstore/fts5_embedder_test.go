package vectorstore_test

import (
	"context"
	"math"
	"testing"

	"github.com/syntrex/gomcp/internal/domain/vectorstore"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestFTS5Embedder_Interface(t *testing.T) {
	// Verify FTS5Embedder satisfies the Embedder interface.
	var _ vectorstore.Embedder = (*vectorstore.FTS5Embedder)(nil)
}

func TestFTS5Embedder_Dimension(t *testing.T) {
	e := vectorstore.NewFTS5Embedder()
	assert.Equal(t, 128, e.Dimension())
}

func TestFTS5Embedder_Name(t *testing.T) {
	e := vectorstore.NewFTS5Embedder()
	assert.Equal(t, "fts5:trigram-128d", e.Name())
}

func TestFTS5Embedder_Mode(t *testing.T) {
	e := vectorstore.NewFTS5Embedder()
	assert.Equal(t, vectorstore.OracleModeDegraded, e.Mode())
	assert.Equal(t, "DEGRADED", e.Mode().String())
}

func TestFTS5Embedder_EmptyText(t *testing.T) {
	e := vectorstore.NewFTS5Embedder()
	vec, err := e.Embed(context.Background(), "")
	require.NoError(t, err)
	assert.Len(t, vec, 128)
	// All zeros for empty text.
	for _, v := range vec {
		assert.Equal(t, 0.0, v)
	}
}

func TestFTS5Embedder_NormalizedOutput(t *testing.T) {
	e := vectorstore.NewFTS5Embedder()
	vec, err := e.Embed(context.Background(), "Hello, this is a test sentence.")
	require.NoError(t, err)
	assert.Len(t, vec, 128)

	// Verify L2 normalization: ||vec|| should be ~1.0.
	var norm float64
	for _, v := range vec {
		norm += v * v
	}
	norm = math.Sqrt(norm)
	assert.InDelta(t, 1.0, norm, 0.01, "vector should be L2-normalized")
}

func TestFTS5Embedder_SimilarTextsSimilarVectors(t *testing.T) {
	e := vectorstore.NewFTS5Embedder()

	v1, err := e.Embed(context.Background(), "authentication using JWT tokens")
	require.NoError(t, err)

	v2, err := e.Embed(context.Background(), "auth with JWT token verification")
	require.NoError(t, err)

	v3, err := e.Embed(context.Background(), "raspberry pi gpio led control")
	require.NoError(t, err)

	// Similar texts should have higher similarity than dissimilar.
	simSimilar := vectorstore.CosineSimilarity(v1, v2)
	simDissimilar := vectorstore.CosineSimilarity(v1, v3)

	assert.Greater(t, simSimilar, simDissimilar,
		"similar texts should have higher cosine similarity (%.4f > %.4f)",
		simSimilar, simDissimilar)
}

func TestFTS5Embedder_RussianText(t *testing.T) {
	e := vectorstore.NewFTS5Embedder()

	vec, err := e.Embed(context.Background(), "Аутентификация через JWT токены")
	require.NoError(t, err)
	assert.Len(t, vec, 128)

	// Verify normalization for Cyrillic text.
	var norm float64
	for _, v := range vec {
		norm += v * v
	}
	norm = math.Sqrt(norm)
	assert.InDelta(t, 1.0, norm, 0.01)
}

func TestFTS5Embedder_Deterministic(t *testing.T) {
	e := vectorstore.NewFTS5Embedder()

	v1, _ := e.Embed(context.Background(), "test input")
	v2, _ := e.Embed(context.Background(), "test input")

	assert.Equal(t, v1, v2, "same input should produce identical vectors")
}

func TestOracleMode_String(t *testing.T) {
	assert.Equal(t, "FULL", vectorstore.OracleModeFull.String())
	assert.Equal(t, "DEGRADED", vectorstore.OracleModeDegraded.String())
	assert.Equal(t, "UNKNOWN", vectorstore.OracleMode(99).String())
}
