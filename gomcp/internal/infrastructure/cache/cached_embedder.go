package cache

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"

	"github.com/syntrex/gomcp/internal/domain/vectorstore"
	bolt "go.etcd.io/bbolt"
)

var embeddingBucket = []byte("embedding_cache")

// CachedEmbedder wraps an Embedder and caches results in BoltDB (v3.4).
// Avoids recomputing embeddings for the same text, especially useful
// for ONNX mode where inference is expensive.
type CachedEmbedder struct {
	inner vectorstore.Embedder
	db    *bolt.DB
	hits  int
	miss  int
}

// NewCachedEmbedder creates a caching wrapper around any Embedder.
func NewCachedEmbedder(inner vectorstore.Embedder, db *bolt.DB) (*CachedEmbedder, error) {
	err := db.Update(func(tx *bolt.Tx) error {
		_, err := tx.CreateBucketIfNotExists(embeddingBucket)
		return err
	})
	if err != nil {
		return nil, fmt.Errorf("create embedding_cache bucket: %w", err)
	}
	return &CachedEmbedder{inner: inner, db: db}, nil
}

// Embed returns cached embedding or computes and caches a new one.
func (c *CachedEmbedder) Embed(ctx context.Context, text string) ([]float64, error) {
	key := hashText(text)

	// Try cache first.
	var cached []float64
	err := c.db.View(func(tx *bolt.Tx) error {
		b := tx.Bucket(embeddingBucket)
		if b == nil {
			return nil
		}
		data := b.Get([]byte(key))
		if data != nil {
			return json.Unmarshal(data, &cached)
		}
		return nil
	})
	if err == nil && cached != nil {
		c.hits++
		return cached, nil
	}

	// Cache miss — compute.
	embedding, err := c.inner.Embed(ctx, text)
	if err != nil {
		return nil, err
	}
	c.miss++

	// Store in cache (fire-and-forget, don't fail on cache write error).
	_ = c.db.Update(func(tx *bolt.Tx) error {
		b := tx.Bucket(embeddingBucket)
		if b == nil {
			return nil
		}
		data, err := json.Marshal(embedding)
		if err != nil {
			return err
		}
		return b.Put([]byte(key), data)
	})

	return embedding, nil
}

// Dimension delegates to inner embedder.
func (c *CachedEmbedder) Dimension() int { return c.inner.Dimension() }

// Name returns the inner embedder name with cache prefix.
func (c *CachedEmbedder) Name() string { return "cached:" + c.inner.Name() }

// Mode delegates to inner embedder.
func (c *CachedEmbedder) Mode() vectorstore.OracleMode { return c.inner.Mode() }

// Stats returns cache hit/miss statistics.
func (c *CachedEmbedder) Stats() (hits, misses int) { return c.hits, c.miss }

// Ensure CachedEmbedder implements Embedder.
var _ vectorstore.Embedder = (*CachedEmbedder)(nil)

func hashText(text string) string {
	h := sha256.Sum256([]byte(text))
	return hex.EncodeToString(h[:16]) // 128-bit key
}
