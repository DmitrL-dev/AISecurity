// Package vectorstore — QJL (Quantized Johnson-Lindenstrauss) 1-bit quantization.
//
// Based on Google's TurboQuant research (ICLR 2026, AAAI 2025).
// Projects high-dimensional float64 vectors to compact bit signatures via
// random projection + sign quantization. Enables O(d/64) approximate similarity
// using POPCNT-accelerated Hamming distance.
//
// Properties:
//   - Data-oblivious: no training, no codebook, no dataset-specific tuning
//   - Deterministic: seeded PRNG → reproducible projections
//   - Zero accuracy loss on ordering for well-separated vectors
//   - 32x memory reduction (256-bit signature vs 128-dim float64 vector)
package vectorstore

import (
	"math"
	"math/bits"
	"math/rand"
)

// QJLSignature is a bit-packed sign vector produced by QJL quantization.
// Each uint64 holds 64 sign bits from random projections.
type QJLSignature []uint64

// QJLProjection holds the random projection matrix for QJL quantization.
// Thread-safe after construction (read-only).
type QJLProjection struct {
	numProjections int         // Total number of random projections (bits)
	vectorDim      int         // Expected input vector dimensionality
	matrix         [][]float64 // [numProjections][vectorDim] random Gaussian
}

// NewQJLProjection creates a random projection matrix for QJL quantization.
//
// Parameters:
//   - numProjections: number of random projections (bits in output signature).
//     Higher = more accurate but more memory. Recommended: 256.
//   - vectorDim: dimensionality of input vectors (must match embedder output).
//   - seed: PRNG seed for reproducibility. Same seed → same projections.
func NewQJLProjection(numProjections, vectorDim int, seed int64) *QJLProjection {
	rng := rand.New(rand.NewSource(seed))

	// Generate random Gaussian projection matrix.
	// Each row is a random direction in the input space.
	// By JL lemma, sign(projection) preserves angular distances.
	matrix := make([][]float64, numProjections)
	for i := range matrix {
		row := make([]float64, vectorDim)
		for j := range row {
			row[j] = rng.NormFloat64()
		}
		// L2-normalize each projection row for numerical stability.
		var norm float64
		for _, v := range row {
			norm += v * v
		}
		norm = math.Sqrt(norm)
		if norm > 0 {
			for j := range row {
				row[j] /= norm
			}
		}
		matrix[i] = row
	}

	return &QJLProjection{
		numProjections: numProjections,
		vectorDim:      vectorDim,
		matrix:         matrix,
	}
}

// Quantize projects a float64 vector through the random matrix and returns
// a compact bit-packed QJLSignature. Each bit is the sign of one projection.
//
// Memory: numProjections/64 uint64s (e.g., 256 bits = 4 uint64s = 32 bytes).
// Compare: 128-dim float64 vector = 1024 bytes → 32x reduction.
func (p *QJLProjection) Quantize(vector []float64) QJLSignature {
	numWords := (p.numProjections + 63) / 64
	sig := make(QJLSignature, numWords)

	dim := p.vectorDim
	if len(vector) < dim {
		dim = len(vector)
	}

	for i := 0; i < p.numProjections; i++ {
		// Dot product: projection[i] · vector
		var dot float64
		row := p.matrix[i]
		for j := 0; j < dim; j++ {
			dot += row[j] * vector[j]
		}

		// Sign bit: positive → 1, negative/zero → 0
		if dot > 0 {
			word := i / 64
			bit := uint(i % 64)
			sig[word] |= 1 << bit
		}
	}

	return sig
}

// NumProjections returns the total number of projection bits.
func (p *QJLProjection) NumProjections() int {
	return p.numProjections
}

// VectorDim returns the expected input dimensionality.
func (p *QJLProjection) VectorDim() int {
	return p.vectorDim
}

// HammingSimilarity computes normalized Hamming similarity between two QJL signatures.
// Returns a value in [0, 1] where 1 = all bits match (identical direction),
// 0.5 = uncorrelated (orthogonal), 0 = all bits differ (opposite direction).
//
// Uses math/bits.OnesCount64 which maps to hardware POPCNT on x86.
func HammingSimilarity(a, b QJLSignature, numBits int) float64 {
	if len(a) != len(b) || numBits == 0 {
		return 0
	}

	// Count matching bits = total bits - differing bits.
	var xorCount int
	for i := range a {
		xorCount += bits.OnesCount64(a[i] ^ b[i])
	}

	// Similarity = 1 - (hamming_distance / total_bits)
	return 1.0 - float64(xorCount)/float64(numBits)
}

// EstimatedCosineSimilarity converts Hamming similarity to an estimated
// cosine similarity using the relationship from the JL sign-random-projection
// theorem: cos(θ) ≈ cos(π * (1 - hamming_similarity)).
//
// This gives a more accurate similarity estimate than raw Hamming for ranking.
func EstimatedCosineSimilarity(hammingSim float64) float64 {
	// θ ≈ π * (1 - hammingSim)
	// cos(θ) = cos(π * (1 - hammingSim))
	return math.Cos(math.Pi * (1.0 - hammingSim))
}
