package vectorstore

import (
	"context"
	"math"
	"strings"
	"unicode/utf8"
)

// FTS5Embedder is a pure-Go fallback embedder that uses character n-gram
// frequency vectors instead of neural embeddings. No external deps required.
//
// Quality is lower than MiniLM but sufficient for basic intent matching.
// Used when ONNX runtime is not available → [ORACLE: DEGRADED].
type FTS5Embedder struct {
	ngramSize int
	dimension int
}

// NewFTS5Embedder creates a fallback embedder with character n-grams.
// Uses tri-grams (n=3) projected to a fixed dimension via hashing.
func NewFTS5Embedder() *FTS5Embedder {
	return &FTS5Embedder{
		ngramSize: 3,
		dimension: 128, // Hash-projected dimension.
	}
}

// Embed generates a character n-gram frequency vector.
// Text is lowercased, split into n-grams, each hashed to a bucket.
func (e *FTS5Embedder) Embed(_ context.Context, text string) ([]float64, error) {
	text = strings.ToLower(strings.TrimSpace(text))
	if text == "" {
		return make([]float64, e.dimension), nil
	}

	vec := make([]float64, e.dimension)
	runes := []rune(text)

	// Generate character n-grams and hash into buckets.
	count := 0
	for i := 0; i <= len(runes)-e.ngramSize; i++ {
		ngram := string(runes[i : i+e.ngramSize])
		bucket := fnvHash(ngram) % uint32(e.dimension)
		vec[bucket]++
		count++
	}

	// Also add word-level features for better discrimination.
	words := strings.Fields(text)
	for _, w := range words {
		if utf8.RuneCountInString(w) >= 2 {
			bucket := fnvHash("w:"+w) % uint32(e.dimension)
			vec[bucket]++
			count++
		}
	}

	// L2-normalize the vector.
	if count > 0 {
		var norm float64
		for _, v := range vec {
			norm += v * v
		}
		norm = math.Sqrt(norm)
		if norm > 0 {
			for i := range vec {
				vec[i] /= norm
			}
		}
	}

	return vec, nil
}

// Dimension returns the fixed output dimension (128).
func (e *FTS5Embedder) Dimension() int {
	return e.dimension
}

// Name returns the embedder identifier.
func (e *FTS5Embedder) Name() string {
	return "fts5:trigram-128d"
}

// Mode returns DEGRADED — this is a fallback embedder.
func (e *FTS5Embedder) Mode() OracleMode {
	return OracleModeDegraded
}

// fnvHash computes FNV-1a hash of a string.
func fnvHash(s string) uint32 {
	const (
		offset32 = uint32(2166136261)
		prime32  = uint32(16777619)
	)
	h := offset32
	for i := 0; i < len(s); i++ {
		h ^= uint32(s[i])
		h *= prime32
	}
	return h
}
