package vectorstore

import (
	"fmt"
	"math"
	"math/rand"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// --- PolarQuant Core Tests ---

func TestPolarQuant_EncodeDecode_Deterministic(t *testing.T) {
	codec := NewPolarQuantCodec(128, 4, 42)
	vec := pqRandomVector(128, 1)

	cv1 := codec.Encode(vec)
	cv2 := codec.Encode(vec)

	assert.Equal(t, cv1.Data, cv2.Data, "same input → same compressed data")
	assert.Equal(t, cv1.Radius, cv2.Radius, "same input → same radius")
}

func TestPolarQuant_RoundTrip_4bit(t *testing.T) {
	codec := NewPolarQuantCodec(128, 4, 42)
	vec := pqRandomVector(128, 1)

	cv := codec.Encode(vec)
	reconstructed := codec.Decode(cv)

	// 4-bit quantization on 128-dim: ~91% avg cosine (empirically measured).
	// Quantization noise is higher at d=128 vs d=3 due to more dimensions.
	l2err := l2Error(vec, reconstructed)
	assert.Less(t, l2err, 0.50, "4-bit roundtrip L2 error should be < 50%%, got %.4f", l2err)

	cosSim := CosineSimilarity(vec, reconstructed)
	assert.Greater(t, cosSim, 0.90, "4-bit roundtrip cosine similarity should be > 0.90, got %.4f", cosSim)
}

func TestPolarQuant_RoundTrip_8bit(t *testing.T) {
	codec := NewPolarQuantCodec(128, 8, 42)
	vec := pqRandomVector(128, 1)

	cv := codec.Encode(vec)
	reconstructed := codec.Decode(cv)

	// 8-bit quantization: expect << 1% reconstruction error.
	l2err := l2Error(vec, reconstructed)
	assert.Less(t, l2err, 0.05, "8-bit roundtrip L2 error should be < 5%%, got %.4f", l2err)

	cosSim := CosineSimilarity(vec, reconstructed)
	assert.Greater(t, cosSim, 0.999, "8-bit roundtrip cosine similarity should be > 0.999, got %.4f", cosSim)
}

func TestPolarQuant_RoundTrip_2bit(t *testing.T) {
	codec := NewPolarQuantCodec(128, 2, 42)
	vec := pqRandomVector(128, 1)

	cv := codec.Encode(vec)
	reconstructed := codec.Decode(cv)

	// 2-bit: coarse but should preserve general direction.
	cosSim := CosineSimilarity(vec, reconstructed)
	assert.Greater(t, cosSim, 0.70, "2-bit roundtrip cosine should be > 0.70, got %.4f", cosSim)
}

func TestPolarQuant_PreservesRadius(t *testing.T) {
	codec := NewPolarQuantCodec(128, 4, 42)
	vec := pqRandomVector(128, 1)

	// Scale vector to non-unit length.
	scaled := make([]float64, len(vec))
	for i, v := range vec {
		scaled[i] = v * 3.7
	}

	cv := codec.Encode(scaled)
	assert.InDelta(t, 3.7, float64(cv.Radius), 0.01, "radius should be ≈ 3.7")

	reconstructed := codec.Decode(cv)
	// Check that the scale is preserved.
	var recNorm float64
	for _, v := range reconstructed {
		recNorm += v * v
	}
	recNorm = math.Sqrt(recNorm)
	assert.InDelta(t, 3.7, recNorm, 0.5, "reconstructed norm should be ≈ 3.7")
}

func TestPolarQuant_PreservesOrdering(t *testing.T) {
	codec := NewPolarQuantCodec(128, 4, 42)

	query := pqRandomVector(128, 1)
	close := pqPerturbVector(query, 0.1, 2)
	far := pqPerturbVector(query, 0.9, 3)

	cosClose := CosineSimilarity(query, close)
	cosFar := CosineSimilarity(query, far)
	require.Greater(t, cosClose, cosFar, "sanity: close > far in original space")

	// Encode all.
	cvQ := codec.Encode(query)
	cvClose := codec.Encode(close)
	cvFar := codec.Encode(far)

	// Compressed similarity should preserve ordering.
	compClose := codec.CompressedSimilarity(cvQ, cvClose)
	compFar := codec.CompressedSimilarity(cvQ, cvFar)

	assert.Greater(t, compClose, compFar,
		"PolarQuant must preserve ordering: comp(query,close)=%.4f > comp(query,far)=%.4f",
		compClose, compFar)
}

func TestPolarQuant_CompressedSimilarity_AccuracyVsExact(t *testing.T) {
	codec := NewPolarQuantCodec(128, 4, 42)

	v1 := pqRandomVector(128, 10)
	v2 := pqRandomVector(128, 20)

	exactSim := CosineSimilarity(v1, v2)

	cv1 := codec.Encode(v1)
	cv2 := codec.Encode(v2)
	compSim := codec.CompressedSimilarity(cv1, cv2)

	// 4-bit compressed similarity should be within ±0.1 of exact.
	assert.InDelta(t, exactSim, compSim, 0.1,
		"compressed similarity (%.4f) should be close to exact (%.4f)", compSim, exactSim)
}

func TestPolarQuant_MemoryReduction_4bit(t *testing.T) {
	codec := NewPolarQuantCodec(128, 4, 42)

	compBytes := codec.CompressedBytes() + 4 // +4 for float32 radius
	origBytes := 128 * 8                     // float64
	ratio := codec.CompressionRatio()

	assert.Equal(t, 64, codec.CompressedBytes(), "128×4bit = 512 bits = 64 bytes")
	assert.Equal(t, 68, compBytes, "total = 64 data + 4 radius = 68 bytes")
	assert.InDelta(t, float64(origBytes)/float64(compBytes), ratio, 0.1)
	assert.Greater(t, ratio, 14.0, "should be >14x compression, got %.1fx", ratio)
}

func TestPolarQuant_MemoryReduction_8bit(t *testing.T) {
	codec := NewPolarQuantCodec(128, 8, 42)

	compBytes := codec.CompressedBytes() + 4
	ratio := codec.CompressionRatio()

	assert.Equal(t, 128, codec.CompressedBytes(), "128×8bit = 1024 bits = 128 bytes")
	assert.Equal(t, 132, compBytes)
	assert.Greater(t, ratio, 7.0, "should be >7x compression, got %.1fx", ratio)
}

func TestPolarQuant_ZeroVector(t *testing.T) {
	codec := NewPolarQuantCodec(128, 4, 42)
	zero := make([]float64, 128)

	cv := codec.Encode(zero)
	assert.InDelta(t, 0.0, float64(cv.Radius), 0.001)

	reconstructed := codec.Decode(cv)
	for i, v := range reconstructed {
		assert.InDelta(t, 0.0, v, 0.001, "zero vector dimension %d should stay zero", i)
	}
}

func TestPolarQuant_SmallDim(t *testing.T) {
	// Ensure PolarQuant works for small dimensions too.
	codec := NewPolarQuantCodec(3, 4, 42)
	vec := []float64{0.6, 0.8, 0.0}

	cv := codec.Encode(vec)
	reconstructed := codec.Decode(cv)

	cosSim := CosineSimilarity(vec, reconstructed)
	assert.Greater(t, cosSim, 0.90, "3-dim 4-bit cosine should be > 0.90, got %.4f", cosSim)
}

// TestPolarQuant_ShortDataBuffer guards Decode/CompressedSimilarity against an
// index-out-of-range panic when a CompressedVector carries a Data buffer that is
// shorter than the codec's dimensionality requires (e.g. corrupt, truncated, or
// foreign-constructed). The exported Data field makes such inputs reachable.
func TestPolarQuant_ShortDataBuffer(t *testing.T) {
	for _, bits := range []int{2, 4, 8} {
		codec := NewPolarQuantCodec(128, bits, 7)

		short := CompressedVector{Data: []byte{0x12}, Radius: 1.0}
		empty := CompressedVector{Data: nil, Radius: 1.0}

		assert.NotPanics(t, func() {
			out := codec.Decode(short)
			assert.Len(t, out, 128, "Decode must still return a dim-length vector (bits=%d)", bits)
			codec.Decode(empty)
		}, "Decode must not panic on a short/empty buffer (bits=%d)", bits)

		// A correctly-sized vector compared against a short one must not panic.
		good := codec.Encode(pqRandomVector(128, 1))
		assert.NotPanics(t, func() {
			codec.CompressedSimilarity(good, short)
			codec.CompressedSimilarity(short, good)
		}, "CompressedSimilarity must not panic on a short buffer (bits=%d)", bits)
	}
}

func TestPolarQuant_DifferentSeeds(t *testing.T) {
	vec := pqRandomVector(128, 1)

	codec1 := NewPolarQuantCodec(128, 4, 42)
	codec2 := NewPolarQuantCodec(128, 4, 99)

	cv1 := codec1.Encode(vec)
	cv2 := codec2.Encode(vec)

	assert.NotEqual(t, cv1.Data, cv2.Data, "different seeds → different compressed data")
}

func TestPolarQuant_BitWidthClamping(t *testing.T) {
	// bitsPerDim < 1 → clamp to 1.
	codec1 := NewPolarQuantCodec(128, 0, 42)
	assert.Equal(t, 1, codec1.BitsPerDim())

	// bitsPerDim > 8 → clamp to 8.
	codec2 := NewPolarQuantCodec(128, 16, 42)
	assert.Equal(t, 8, codec2.BitsPerDim())
}

func TestPolarQuant_OrthogonalRotation_PreservesNorm(t *testing.T) {
	// Orthogonal matrix should preserve vector norms.
	codec := NewPolarQuantCodec(64, 8, 42)
	vec := pqRandomVector(64, 5)

	// Manually rotate.
	rotated := make([]float64, 64)
	for i := 0; i < 64; i++ {
		var dot float64
		for j := 0; j < 64; j++ {
			dot += codec.rotation[i][j] * vec[j]
		}
		rotated[i] = dot
	}

	origNorm := vecNorm(vec, 64)
	rotNorm := vecNorm(rotated, 64)
	assert.InDelta(t, origNorm, rotNorm, 0.001, "rotation should preserve L2 norm")
}

func TestPolarQuant_OrthogonalRotation_Deterministic(t *testing.T) {
	c1 := NewPolarQuantCodec(32, 4, 42)
	c2 := NewPolarQuantCodec(32, 4, 42)

	for i := 0; i < 32; i++ {
		for j := 0; j < 32; j++ {
			assert.Equal(t, c1.rotation[i][j], c2.rotation[i][j],
				"same seed → same rotation at [%d][%d]", i, j)
		}
	}
}

// --- Batch Quality Tests ---

func TestPolarQuant_BatchQuality_4bit(t *testing.T) {
	codec := NewPolarQuantCodec(128, 4, 42)
	n := 100

	var totalCosSim float64
	for i := 0; i < n; i++ {
		vec := pqRandomVector(128, int64(i))
		cv := codec.Encode(vec)
		rec := codec.Decode(cv)
		totalCosSim += CosineSimilarity(vec, rec)
	}

	avgCos := totalCosSim / float64(n)
	assert.Greater(t, avgCos, 0.90,
		"avg cosine similarity over %d vectors should be > 0.90, got %.4f", n, avgCos)
}

func TestPolarQuant_BatchOrderingPreservation(t *testing.T) {
	codec := NewPolarQuantCodec(128, 4, 42)
	n := 50

	// For each query, verify that the top-1 nearest neighbor is preserved.
	preserved := 0
	for i := 0; i < n; i++ {
		query := pqRandomVector(128, int64(i*100))
		vectors := make([][]float64, 10)
		for j := 0; j < 10; j++ {
			vectors[j] = pqRandomVector(128, int64(i*100+j+1))
		}

		// Find exact top-1.
		bestExact := -1
		bestExactSim := -2.0
		for j, v := range vectors {
			sim := CosineSimilarity(query, v)
			if sim > bestExactSim {
				bestExactSim = sim
				bestExact = j
			}
		}

		// Find compressed top-1.
		cvQ := codec.Encode(query)
		bestComp := -1
		bestCompSim := -2.0
		for j, v := range vectors {
			cv := codec.Encode(v)
			sim := codec.CompressedSimilarity(cvQ, cv)
			if sim > bestCompSim {
				bestCompSim = sim
				bestComp = j
			}
		}

		if bestExact == bestComp {
			preserved++
		}
	}

	rate := float64(preserved) / float64(n)
	assert.Greater(t, rate, 0.55,
		"top-1 preservation rate should be > 55%%, got %.0f%% (%d/%d)", rate*100, preserved, n)
}

// --- Benchmarks ---

func BenchmarkPolarQuant_Encode_4bit(b *testing.B) {
	codec := NewPolarQuantCodec(128, 4, 42)
	vec := pqRandomVector(128, 1)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		codec.Encode(vec)
	}
}

func BenchmarkPolarQuant_Decode_4bit(b *testing.B) {
	codec := NewPolarQuantCodec(128, 4, 42)
	vec := pqRandomVector(128, 1)
	cv := codec.Encode(vec)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		codec.Decode(cv)
	}
}

func BenchmarkPolarQuant_CompressedSimilarity_4bit(b *testing.B) {
	codec := NewPolarQuantCodec(128, 4, 42)
	v1 := pqRandomVector(128, 1)
	v2 := pqRandomVector(128, 2)
	cv1 := codec.Encode(v1)
	cv2 := codec.Encode(v2)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		codec.CompressedSimilarity(cv1, cv2)
	}
}

func BenchmarkPolarQuant_Encode_8bit(b *testing.B) {
	codec := NewPolarQuantCodec(128, 8, 42)
	vec := pqRandomVector(128, 1)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		codec.Encode(vec)
	}
}

// --- Helpers (scoped to polarquant tests to avoid collision with qjl_test) ---

func pqRandomVector(dim int, seed int64) []float64 {
	rng := rand.New(rand.NewSource(seed))
	vec := make([]float64, dim)
	for i := range vec {
		vec[i] = rng.NormFloat64()
	}
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
	return vec
}

func pqPerturbVector(v []float64, noise float64, seed int64) []float64 {
	rng := rand.New(rand.NewSource(seed))
	perturbed := make([]float64, len(v))
	for i := range v {
		perturbed[i] = v[i] + noise*rng.NormFloat64()
	}
	var norm float64
	for _, val := range perturbed {
		norm += val * val
	}
	norm = math.Sqrt(norm)
	if norm > 0 {
		for i := range perturbed {
			perturbed[i] /= norm
		}
	}
	return perturbed
}

func l2Error(a, b []float64) float64 {
	if len(a) != len(b) {
		return math.Inf(1)
	}
	var sumSq float64
	for i := range a {
		d := a[i] - b[i]
		sumSq += d * d
	}
	return math.Sqrt(sumSq)
}

func init() {
	// Silence unused import warnings by referencing fmt.
	_ = fmt.Sprint
}
