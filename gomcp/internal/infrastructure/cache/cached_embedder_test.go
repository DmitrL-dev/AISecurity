package cache

import (
	"context"
	"os"
	"testing"

	"github.com/syntrex/gomcp/internal/domain/vectorstore"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	bolt "go.etcd.io/bbolt"
)

// mockEmbedder is a simple test embedder.
type mockEmbedder struct {
	calls int
}

func (m *mockEmbedder) Embed(_ context.Context, text string) ([]float64, error) {
	m.calls++
	// Simple deterministic embedding: sum of bytes.
	vec := make([]float64, 4)
	for i, b := range []byte(text) {
		vec[i%4] += float64(b)
	}
	return vec, nil
}

func (m *mockEmbedder) Dimension() int               { return 4 }
func (m *mockEmbedder) Name() string                 { return "mock" }
func (m *mockEmbedder) Mode() vectorstore.OracleMode { return vectorstore.OracleModeFull }

func TestCachedEmbedder_HitMiss(t *testing.T) {
	tmp, err := os.CreateTemp("", "embed_cache_*.db")
	require.NoError(t, err)
	tmp.Close()
	defer os.Remove(tmp.Name())

	db, err := bolt.Open(tmp.Name(), 0o600, nil)
	require.NoError(t, err)
	defer db.Close()

	inner := &mockEmbedder{}
	cached, err := NewCachedEmbedder(inner, db)
	require.NoError(t, err)

	ctx := context.Background()

	// First call — cache miss.
	v1, err := cached.Embed(ctx, "hello world")
	require.NoError(t, err)
	assert.Equal(t, 1, inner.calls)

	// Second call — cache hit.
	v2, err := cached.Embed(ctx, "hello world")
	require.NoError(t, err)
	assert.Equal(t, 1, inner.calls) // No extra call.
	assert.Equal(t, v1, v2)

	// Different text — cache miss.
	_, err = cached.Embed(ctx, "different text")
	require.NoError(t, err)
	assert.Equal(t, 2, inner.calls)

	hits, misses := cached.Stats()
	assert.Equal(t, 1, hits)
	assert.Equal(t, 2, misses)
}

func TestCachedEmbedder_Name(t *testing.T) {
	inner := &mockEmbedder{}
	db, err := bolt.Open(t.TempDir()+"/test.db", 0o600, nil)
	require.NoError(t, err)
	defer db.Close()

	cached, err := NewCachedEmbedder(inner, db)
	require.NoError(t, err)

	assert.Equal(t, "cached:mock", cached.Name())
	assert.Equal(t, 4, cached.Dimension())
}
