package vectorstore

import (
	"fmt"
	"math"
	"math/rand"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// --- QJL Core Algorithm Tests ---

func TestQJL_Quantize_Deterministic(t *testing.T) {
	proj := NewQJLProjection(256, 128, 42)
	vec := randomVector(128, 1)

	sig1 := proj.Quantize(vec)
	sig2 := proj.Quantize(vec)

	assert.Equal(t, sig1, sig2, "identical input must produce identical signature")
}

func TestQJL_Quantize_DifferentSeeds(t *testing.T) {
	vec := randomVector(128, 1)

	proj1 := NewQJLProjection(256, 128, 42)
	proj2 := NewQJLProjection(256, 128, 99)

	sig1 := proj1.Quantize(vec)
	sig2 := proj2.Quantize(vec)

	// Different seeds should produce different projections → different signatures.
	assert.NotEqual(t, sig1, sig2, "different seeds must produce different signatures")
}

func TestQJL_HammingSimilarity_Identical(t *testing.T) {
	proj := NewQJLProjection(256, 128, 42)
	vec := randomVector(128, 1)

	sig := proj.Quantize(vec)
	sim := HammingSimilarity(sig, sig, 256)

	assert.InDelta(t, 1.0, sim, 0.001, "identical signatures → similarity = 1.0")
}

func TestQJL_HammingSimilarity_Orthogonal(t *testing.T) {
	proj := NewQJLProjection(512, 128, 42) // More bits for better approximation.
	v1 := make([]float64, 128)
	v2 := make([]float64, 128)
	v1[0] = 1.0
	v2[1] = 1.0

	sig1 := proj.Quantize(v1)
	sig2 := proj.Quantize(v2)

	sim := HammingSimilarity(sig1, sig2, 512)
	// Orthogonal vectors → ~0.5 Hamming similarity (random coin-flip).
	assert.InDelta(t, 0.5, sim, 0.1, "orthogonal vectors → similarity ≈ 0.5, got %.4f", sim)
}

func TestQJL_HammingSimilarity_Opposite(t *testing.T) {
	proj := NewQJLProjection(512, 128, 42)
	v1 := randomVector(128, 1)
	v2 := make([]float64, 128)
	for i := range v1 {
		v2[i] = -v1[i]
	}

	sig1 := proj.Quantize(v1)
	sig2 := proj.Quantize(v2)

	sim := HammingSimilarity(sig1, sig2, 512)
	// Opposite vectors → ~0.0 Hamming similarity.
	assert.InDelta(t, 0.0, sim, 0.1, "opposite vectors → similarity ≈ 0.0, got %.4f", sim)
}

func TestQJL_PreservesOrdering(t *testing.T) {
	// For well-separated vectors, QJL Hamming ordering should match cosine ordering.
	proj := NewQJLProjection(512, 128, 42)

	query := randomVector(128, 1)
	close := perturbVector(query, 0.1, 2)  // ~10% perturbation = close
	far := perturbVector(query, 0.9, 3)     // ~90% perturbation = far

	cosClose := CosineSimilarity(query, close)
	cosFar := CosineSimilarity(query, far)
	require.Greater(t, cosClose, cosFar, "sanity: cosine(query, close) > cosine(query, far)")

	sigQ := proj.Quantize(query)
	sigClose := proj.Quantize(close)
	sigFar := proj.Quantize(far)

	hamClose := HammingSimilarity(sigQ, sigClose, 512)
	hamFar := HammingSimilarity(sigQ, sigFar, 512)

	assert.Greater(t, hamClose, hamFar,
		"QJL must preserve ordering: hamming(query,close)=%.4f > hamming(query,far)=%.4f",
		hamClose, hamFar)
}

func TestQJL_EstimatedCosineSimilarity(t *testing.T) {
	// Hamming sim = 1.0 → estimated cosine = cos(0) = 1.0
	assert.InDelta(t, 1.0, EstimatedCosineSimilarity(1.0), 0.001)
	// Hamming sim = 0.5 → estimated cosine = cos(π/2) = 0.0
	assert.InDelta(t, 0.0, EstimatedCosineSimilarity(0.5), 0.001)
	// Hamming sim = 0.0 → estimated cosine = cos(π) = -1.0
	assert.InDelta(t, -1.0, EstimatedCosineSimilarity(0.0), 0.001)
}

func TestQJL_MemoryReduction(t *testing.T) {
	proj := NewQJLProjection(256, 128, 42)
	vec := randomVector(128, 1)
	sig := proj.Quantize(vec)

	float64Bytes := 128 * 8           // 1024 bytes
	qjlBytes := len(sig) * 8          // 4 * 8 = 32 bytes
	reduction := float64(float64Bytes) / float64(qjlBytes)

	assert.Equal(t, 4, len(sig), "256 bits → 4 uint64 words")
	assert.Equal(t, 32, qjlBytes, "256-bit signature = 32 bytes")
	assert.InDelta(t, 32.0, reduction, 0.5, "expected 32x memory reduction")
}

func TestQJL_HammingSimilarity_LengthMismatch(t *testing.T) {
	a := QJLSignature{0xFF}
	b := QJLSignature{0xFF, 0x00}
	assert.Equal(t, 0.0, HammingSimilarity(a, b, 128))
}

func TestQJL_HammingSimilarity_ZeroBits(t *testing.T) {
	a := QJLSignature{0xFF}
	b := QJLSignature{0xFF}
	assert.Equal(t, 0.0, HammingSimilarity(a, b, 0))
}

// --- Store QJL Integration Tests ---

func TestStore_QJLEnabled_Default(t *testing.T) {
	s := New(nil)
	assert.True(t, s.QJLEnabled(), "QJL should be enabled by default")
}

func TestStore_QJLDisabled_Explicit(t *testing.T) {
	s := New(&Config{QJLProjections: -1})
	assert.False(t, s.QJLEnabled(), "QJL should be disabled with -1")
}

func TestStore_SearchQJL_MatchesExact(t *testing.T) {
	s := New(&Config{QJLProjections: 512, QJLVectorDim: 3, QJLSeed: 42})

	s.Add(&IntentRecord{ID: "r1", Text: "read data", Vector: []float64{1.0, 0.0, 0.0}})
	s.Add(&IntentRecord{ID: "w1", Text: "write data", Vector: []float64{0.0, 1.0, 0.0}})
	s.Add(&IntentRecord{ID: "e1", Text: "exec code", Vector: []float64{0.0, 0.0, 1.0}})

	// SearchQJL should return the same top-1 as Search for well-separated vectors.
	exact := s.Search([]float64{1.0, 0.0, 0.0}, 1)
	qjl := s.SearchQJL([]float64{1.0, 0.0, 0.0}, 1)

	require.Len(t, exact, 1)
	require.Len(t, qjl, 1)
	assert.Equal(t, exact[0].Record.ID, qjl[0].Record.ID, "QJL top-1 should match exact top-1")
	assert.InDelta(t, exact[0].Similarity, qjl[0].Similarity, 0.001)
}

func TestStore_SearchQJL_Fallback_NoQJL(t *testing.T) {
	s := New(&Config{QJLProjections: -1})

	s.Add(&IntentRecord{ID: "r1", Vector: []float64{1.0, 0.0, 0.0}})
	s.Add(&IntentRecord{ID: "w1", Vector: []float64{0.0, 1.0, 0.0}})

	results := s.SearchQJL([]float64{1.0, 0.0, 0.0}, 1)
	require.Len(t, results, 1)
	assert.Equal(t, "r1", results[0].Record.ID, "fallback should still work")
}

func TestStore_SearchQJL_Stats(t *testing.T) {
	s := New(&Config{QJLProjections: 256, QJLVectorDim: 128})
	s.Add(&IntentRecord{Route: "read", Verdict: "ALLOW", Entropy: 3.0, Vector: randomVector(128, 1)})

	stats := s.GetStats()
	assert.True(t, stats.QJLEnabled)
	assert.Equal(t, 256, stats.QJLProjections)
	assert.Equal(t, 256, stats.QJLBitsPerVec)
	assert.Equal(t, 32, stats.QJLBytesPerVec)
}

func TestStore_QJL_LRU_Eviction(t *testing.T) {
	s := New(&Config{Capacity: 3, QJLProjections: 64, QJLVectorDim: 3})

	s.Add(&IntentRecord{ID: "a", Vector: []float64{1.0, 0.0, 0.0}})
	s.Add(&IntentRecord{ID: "b", Vector: []float64{0.0, 1.0, 0.0}})
	s.Add(&IntentRecord{ID: "c", Vector: []float64{0.0, 0.0, 1.0}})
	s.Add(&IntentRecord{ID: "d", Vector: []float64{0.5, 0.5, 0.0}}) // Evicts "a"

	assert.Equal(t, 3, s.Count())
	assert.Nil(t, s.Get("a"))

	// SearchQJL should still work after eviction.
	results := s.SearchQJL([]float64{0.5, 0.5, 0.0}, 1)
	require.Len(t, results, 1)
	assert.Equal(t, "d", results[0].Record.ID)
}

func TestStore_SearchQJL_EmptyStore(t *testing.T) {
	s := New(nil)
	assert.Nil(t, s.SearchQJL([]float64{1.0}, 5))
}

func TestStore_SearchQJL_EmptyQuery(t *testing.T) {
	s := New(nil)
	s.Add(&IntentRecord{ID: "r1", Vector: []float64{1.0, 0.0}})
	assert.Nil(t, s.SearchQJL(nil, 5))
}

// --- PolarQuant Store Integration Tests ---

func TestStore_PQEnabled(t *testing.T) {
	// PQ disabled by default.
	s1 := New(nil)
	assert.False(t, s1.PQEnabled(), "PQ should be disabled by default")

	// PQ enabled with 4-bit.
	s2 := New(&Config{PQBitsPerDim: 4})
	assert.True(t, s2.PQEnabled(), "PQ should be enabled with 4-bit")
}

func TestStore_PQ_Stats(t *testing.T) {
	s := New(&Config{QJLProjections: 256, QJLVectorDim: 128, PQBitsPerDim: 4, PQSeed: 7})
	s.Add(&IntentRecord{Route: "read", Vector: randomVector(128, 1)})

	stats := s.GetStats()
	assert.True(t, stats.PQEnabled)
	assert.Equal(t, 4, stats.PQBitsPerDim)
	assert.Equal(t, 68, stats.PQBytesPerVec) // 64 data + 4 radius
	assert.Greater(t, stats.PQCompressionRate, 14.0)
}

func TestStore_SearchQJL_WithPQ_MatchesExact(t *testing.T) {
	// Full TurboQuant pipeline: QJL filter → PQ compressed rerank.
	s := New(&Config{QJLProjections: 512, QJLVectorDim: 3, PQBitsPerDim: 8, PQSeed: 7})

	s.Add(&IntentRecord{ID: "r1", Vector: []float64{1.0, 0.0, 0.0}})
	s.Add(&IntentRecord{ID: "w1", Vector: []float64{0.0, 1.0, 0.0}})
	s.Add(&IntentRecord{ID: "e1", Vector: []float64{0.0, 0.0, 1.0}})

	results := s.SearchQJL([]float64{0.9, 0.1, 0.0}, 1)
	require.Len(t, results, 1)
	assert.Equal(t, "r1", results[0].Record.ID, "PQ rerank should still pick the closest vector")
}

func TestStore_PQ_LRU_Eviction(t *testing.T) {
	s := New(&Config{Capacity: 3, QJLProjections: 64, QJLVectorDim: 3, PQBitsPerDim: 4, PQSeed: 7})

	s.Add(&IntentRecord{ID: "a", Vector: []float64{1.0, 0.0, 0.0}})
	s.Add(&IntentRecord{ID: "b", Vector: []float64{0.0, 1.0, 0.0}})
	s.Add(&IntentRecord{ID: "c", Vector: []float64{0.0, 0.0, 1.0}})
	s.Add(&IntentRecord{ID: "d", Vector: []float64{0.5, 0.5, 0.0}}) // Evicts "a"

	assert.Equal(t, 3, s.Count())
	assert.Nil(t, s.Get("a"))

	// SearchQJL with PQ should still work after eviction.
	results := s.SearchQJL([]float64{0.5, 0.5, 0.0}, 1)
	require.Len(t, results, 1)
	assert.Equal(t, "d", results[0].Record.ID)
}

func TestStore_SearchQJL_PQOnly_NoBrokenFallback(t *testing.T) {
	// PQ enabled, QJL disabled → should fallback to brute-force (no PQ rerank without QJL)
	s := New(&Config{QJLProjections: -1, PQBitsPerDim: 4, QJLVectorDim: 3, PQSeed: 7})

	s.Add(&IntentRecord{ID: "r1", Vector: []float64{1.0, 0.0, 0.0}})
	s.Add(&IntentRecord{ID: "w1", Vector: []float64{0.0, 1.0, 0.0}})

	results := s.SearchQJL([]float64{1.0, 0.0, 0.0}, 1)
	require.Len(t, results, 1)
	assert.Equal(t, "r1", results[0].Record.ID, "fallback should work with PQ but no QJL")
}

func TestStore_PQ_DropFloat64(t *testing.T) {
	s := New(&Config{PQBitsPerDim: 4, PQDropFloat64: true})
	s.Add(&IntentRecord{ID: "r1", Vector: []float64{1.0, 0.0, 0.0}})
	s.Add(&IntentRecord{ID: "r2", Vector: []float64{0.0, 1.0, 0.0}})

	// Original float64 vector should be nil'd out.
	assert.Nil(t, s.Get("r1").Vector, "Vector should be dropped to save memory")
	
	stats := s.GetStats()
	assert.True(t, stats.PQDropFloat64, "Stats should reflect drop float64 true")

	// Search should still work via compressed similarity fallback in brute-force searchLocked.
	results := s.Search([]float64{1.0, 0.0, 0.0}, 1)
	require.Len(t, results, 1)
	assert.Equal(t, "r1", results[0].Record.ID, "Search should work via PQ fallback when vector is dropped")
}

// --- Benchmarks ---

func BenchmarkSearch_BruteForce(b *testing.B) {
	s := New(&Config{Capacity: 10000, QJLProjections: -1, QJLVectorDim: 128})
	populateStore(s, 1000, 128)
	query := randomVector(128, 999)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		s.Search(query, 10)
	}
}

func BenchmarkSearchQJL_TwoPhase(b *testing.B) {
	s := New(&Config{Capacity: 10000, QJLProjections: 256, QJLVectorDim: 128, QJLSeed: 42})
	populateStore(s, 1000, 128)
	query := randomVector(128, 999)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		s.SearchQJL(query, 10)
	}
}

func BenchmarkSearchTurboQuant_Full(b *testing.B) {
	// Full TurboQuant: QJL filter + PolarQuant compressed rerank.
	s := New(&Config{
		Capacity:       10000,
		QJLProjections: 256,
		QJLVectorDim:   128,
		QJLSeed:        42,
		PQBitsPerDim:   4,
		PQSeed:         7,
	})
	populateStore(s, 1000, 128)
	query := randomVector(128, 999)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		s.SearchQJL(query, 10)
	}
}

func BenchmarkQJL_Quantize(b *testing.B) {
	proj := NewQJLProjection(256, 128, 42)
	vec := randomVector(128, 1)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		proj.Quantize(vec)
	}
}

func BenchmarkHammingSimilarity_256bit(b *testing.B) {
	proj := NewQJLProjection(256, 128, 42)
	v1 := randomVector(128, 1)
	v2 := randomVector(128, 2)
	sig1 := proj.Quantize(v1)
	sig2 := proj.Quantize(v2)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		HammingSimilarity(sig1, sig2, 256)
	}
}

func BenchmarkCosineSimilarity_128dim(b *testing.B) {
	v1 := randomVector(128, 1)
	v2 := randomVector(128, 2)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		CosineSimilarity(v1, v2)
	}
}

// --- Helpers ---

func randomVector(dim int, seed int64) []float64 {
	rng := rand.New(rand.NewSource(seed))
	vec := make([]float64, dim)
	for i := range vec {
		vec[i] = rng.NormFloat64()
	}
	// L2-normalize.
	var norm float64
	for _, v := range vec {
		norm += v * v
	}
	norm = math.Sqrt(norm)
	for i := range vec {
		vec[i] /= norm
	}
	return vec
}

func perturbVector(v []float64, noise float64, seed int64) []float64 {
	rng := rand.New(rand.NewSource(seed))
	perturbed := make([]float64, len(v))
	for i := range v {
		perturbed[i] = v[i] + noise*rng.NormFloat64()
	}
	// L2-normalize.
	var norm float64
	for _, val := range perturbed {
		norm += val * val
	}
	norm = math.Sqrt(norm)
	for i := range perturbed {
		perturbed[i] /= norm
	}
	return perturbed
}

func populateStore(s *Store, n, dim int) {
	for i := 0; i < n; i++ {
		s.Add(&IntentRecord{
			ID:     fmt.Sprintf("vec-%d", i),
			Vector: randomVector(dim, int64(i)),
			Route:  "test",
		})
	}
}
