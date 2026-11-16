// Package vectorstore — PolarQuant multi-bit vector compression.
//
// Based on Google's TurboQuant research (ICLR 2026, §3.2).
// Exploits the key insight: after random orthogonal rotation, vector
// coordinates become approximately uniformly distributed regardless of
// the original data distribution. This makes uniform scalar quantization
// near-optimal without any calibration data.
//
// Pipeline:
//  1. Random orthogonal rotation R (data-oblivious, seeded)
//  2. y = R · x (rotate)
//  3. Uniform quantization: each y_i ∈ [-1, 1] → [0, 2^b - 1]
//  4. Compact byte packing (2 values per byte at 4-bit)
//
// Combined with QJL (1-bit approximate search):
//   - QJL signatures: fast approximate filtering (Phase 1)
//   - PolarQuant codes: compressed exact reranking (Phase 2)
//   - Together: TurboQuant = PolarQuant(main bits) + QJL(1-bit residual)
//
// Memory at 4-bit, 128-dim: 64 bytes + 4 bytes radius = 68 bytes
// vs float64 original: 1024 bytes → 15x compression
package vectorstore

import (
	"math"
	"math/rand"
)

// CompressedVector holds a PolarQuant-compressed representation of a vector.
type CompressedVector struct {
	Data   []byte  // Packed quantized values (2 per byte at 4-bit)
	Radius float32 // Original L2 norm for denormalization
}

// PolarQuantCodec encodes/decodes vectors using rotation + uniform quantization.
// Thread-safe after construction (read-only rotation matrix).
type PolarQuantCodec struct {
	dim        int         // Vector dimensionality
	bitsPerDim int         // Quantization bits per dimension (1-8)
	levels     int         // 2^bitsPerDim - 1 (quantization levels)
	rotation   [][]float64 // dim × dim orthogonal rotation matrix
}

// NewPolarQuantCodec creates a PolarQuant codec with random orthogonal rotation.
//
// Parameters:
//   - dim: expected vector dimensionality (must match embedder output)
//   - bitsPerDim: quantization bits per dimension (1-8). Default: 4.
//     4-bit → 16x compression, 8-bit → 8x compression.
//   - seed: PRNG seed for reproducible rotation. Same seed → same codec.
func NewPolarQuantCodec(dim, bitsPerDim int, seed int64) *PolarQuantCodec {
	if bitsPerDim < 1 {
		bitsPerDim = 1
	}
	if bitsPerDim > 8 {
		bitsPerDim = 8
	}

	rng := rand.New(rand.NewSource(seed))
	rotation := randomOrthogonalMatrix(dim, rng)

	return &PolarQuantCodec{
		dim:        dim,
		bitsPerDim: bitsPerDim,
		levels:     (1 << bitsPerDim) - 1,
		rotation:   rotation,
	}
}

// Encode compresses a float64 vector to a compact PolarQuant representation.
//
// Steps:
//  1. Compute and store L2 norm (radius)
//  2. L2-normalize the vector
//  3. Rotate through random orthogonal matrix
//  4. Uniform quantization of each coordinate
//  5. Pack into bytes
func (c *PolarQuantCodec) Encode(vector []float64) CompressedVector {
	dim := c.dim
	if len(vector) < dim {
		dim = len(vector)
	}

	// Step 1: Compute radius (L2 norm).
	var radius float64
	for i := 0; i < dim; i++ {
		radius += vector[i] * vector[i]
	}
	radius = math.Sqrt(radius)

	// Step 2: Normalize.
	normalized := make([]float64, c.dim)
	if radius > 0 {
		for i := 0; i < dim; i++ {
			normalized[i] = vector[i] / radius
		}
	}

	// Step 3: Rotate — y = R · x.
	rotated := make([]float64, c.dim)
	for i := 0; i < c.dim; i++ {
		var dot float64
		row := c.rotation[i]
		for j := 0; j < c.dim; j++ {
			dot += row[j] * normalized[j]
		}
		rotated[i] = dot
	}

	// Step 4-5: Quantize and pack.
	data := c.packQuantized(rotated)

	return CompressedVector{
		Data:   data,
		Radius: float32(radius),
	}
}

// Decode reconstructs a float64 vector from its compressed representation.
//
// Steps:
//  1. Unpack quantized values
//  2. Dequantize to [-1, 1] midpoints
//  3. Inverse rotation: x = R^T · y
//  4. Denormalize by radius
func (c *PolarQuantCodec) Decode(cv CompressedVector) []float64 {
	// Step 1-2: Unpack and dequantize.
	rotated := c.unpackDequantized(cv.Data)

	// Step 3: Inverse rotation — x = R^T · y (transpose of orthogonal = inverse).
	normalized := make([]float64, c.dim)
	for i := 0; i < c.dim; i++ {
		var dot float64
		for j := 0; j < c.dim; j++ {
			dot += c.rotation[j][i] * rotated[j] // R^T[i][j] = R[j][i]
		}
		normalized[i] = dot
	}

	// Step 4: Denormalize.
	radius := float64(cv.Radius)
	result := make([]float64, c.dim)
	for i := range normalized {
		result[i] = normalized[i] * radius
	}

	return result
}

// CompressedSimilarity computes approximate cosine similarity between two
// compressed vectors WITHOUT full decompression. Decompresses to the rotated
// domain and computes dot product there (rotation preserves inner products).
func (c *PolarQuantCodec) CompressedSimilarity(a, b CompressedVector) float64 {
	ra := c.unpackDequantized(a.Data)
	rb := c.unpackDequantized(b.Data)

	// Cosine similarity in rotated space = cosine similarity in original space
	// (orthogonal rotation preserves inner products).
	var dot, normA, normB float64
	for i := 0; i < c.dim; i++ {
		dot += ra[i] * rb[i]
		normA += ra[i] * ra[i]
		normB += rb[i] * rb[i]
	}

	denom := math.Sqrt(normA) * math.Sqrt(normB)
	if denom == 0 {
		return 0
	}
	return dot / denom
}

// Dim returns the expected vector dimensionality.
func (c *PolarQuantCodec) Dim() int {
	return c.dim
}

// BitsPerDim returns the quantization precision.
func (c *PolarQuantCodec) BitsPerDim() int {
	return c.bitsPerDim
}

// CompressedBytes returns bytes per compressed vector (excluding radius).
func (c *PolarQuantCodec) CompressedBytes() int {
	return (c.dim*c.bitsPerDim + 7) / 8
}

// CompressionRatio returns the ratio of original to compressed size.
func (c *PolarQuantCodec) CompressionRatio() float64 {
	origBytes := c.dim * 8 // float64
	compBytes := c.CompressedBytes() + 4 // + float32 radius
	return float64(origBytes) / float64(compBytes)
}

// --- Internal: Quantization and packing ---

// packQuantized quantizes and packs rotated coordinates into bytes.
// For 4-bit: 2 values packed per byte (high nibble, low nibble).
// For 8-bit: 1 value per byte.
// For other bit widths: generic bit packing.
func (c *PolarQuantCodec) packQuantized(rotated []float64) []byte {
	numBytes := (c.dim*c.bitsPerDim + 7) / 8
	data := make([]byte, numBytes)

	if c.bitsPerDim == 4 {
		// Fast path: 4-bit packing (2 per byte).
		for i := 0; i < c.dim; i++ {
			q := quantizeUniform(rotated[i], c.levels)
			byteIdx := i / 2
			if i%2 == 0 {
				data[byteIdx] |= q << 4 // High nibble
			} else {
				data[byteIdx] |= q // Low nibble
			}
		}
	} else if c.bitsPerDim == 8 {
		// Fast path: 8-bit packing (1 per byte).
		for i := 0; i < c.dim; i++ {
			data[i] = quantizeUniform(rotated[i], c.levels)
		}
	} else {
		// Generic bit packing.
		bitPos := 0
		for i := 0; i < c.dim; i++ {
			q := quantizeUniform(rotated[i], c.levels)
			for b := c.bitsPerDim - 1; b >= 0; b-- {
				if q&(1<<uint(b)) != 0 {
					data[bitPos/8] |= 1 << uint(7-bitPos%8)
				}
				bitPos++
			}
		}
	}

	return data
}

// unpackDequantized unpacks and dequantizes bytes back to float64 coordinates.
//
// A short or empty Data buffer (e.g. from a corrupt, truncated, or
// foreign-constructed CompressedVector) would otherwise index past the slice
// and panic. Guard against that by returning a zero-filled vector when the
// buffer is smaller than the codec requires.
func (c *PolarQuantCodec) unpackDequantized(data []byte) []float64 {
	rotated := make([]float64, c.dim)

	if len(data) < (c.dim*c.bitsPerDim+7)/8 {
		return rotated
	}

	if c.bitsPerDim == 4 {
		// Fast path: 4-bit.
		for i := 0; i < c.dim; i++ {
			byteIdx := i / 2
			var q uint8
			if i%2 == 0 {
				q = data[byteIdx] >> 4
			} else {
				q = data[byteIdx] & 0x0F
			}
			rotated[i] = dequantizeUniform(q, c.levels)
		}
	} else if c.bitsPerDim == 8 {
		// Fast path: 8-bit.
		for i := 0; i < c.dim; i++ {
			rotated[i] = dequantizeUniform(data[i], c.levels)
		}
	} else {
		// Generic bit unpacking.
		bitPos := 0
		for i := 0; i < c.dim; i++ {
			var q uint8
			for b := c.bitsPerDim - 1; b >= 0; b-- {
				if data[bitPos/8]&(1<<uint(7-bitPos%8)) != 0 {
					q |= 1 << uint(b)
				}
				bitPos++
			}
			rotated[i] = dequantizeUniform(q, c.levels)
		}
	}

	return rotated
}

// quantizeUniform maps a value in [-1, 1] to [0, levels] as uint8.
func quantizeUniform(val float64, levels int) uint8 {
	// Clamp to [-1, 1].
	if val < -1 {
		val = -1
	}
	if val > 1 {
		val = 1
	}
	// Map [-1, 1] → [0, 1] → [0, levels].
	normalized := (val + 1.0) / 2.0
	return uint8(math.Round(normalized * float64(levels)))
}

// dequantizeUniform maps a quantized uint8 in [0, levels] back to [-1, 1].
func dequantizeUniform(q uint8, levels int) float64 {
	// Map [0, levels] → [0, 1] → [-1, 1].
	normalized := float64(q) / float64(levels)
	return normalized*2.0 - 1.0
}

// --- Internal: Random orthogonal matrix generation ---

// randomOrthogonalMatrix generates a dim×dim random orthogonal matrix
// using Gram-Schmidt orthogonalization of a random Gaussian matrix.
//
// Properties:
//   - Uniformly distributed over the orthogonal group O(d)
//   - Deterministic given the PRNG
//   - O(d³) construction, done once at initialization
func randomOrthogonalMatrix(dim int, rng *rand.Rand) [][]float64 {
	// Generate random Gaussian matrix.
	Q := make([][]float64, dim)
	for i := range Q {
		Q[i] = make([]float64, dim)
		for j := range Q[i] {
			Q[i][j] = rng.NormFloat64()
		}
	}

	// Modified Gram-Schmidt orthogonalization (numerically stable).
	for i := 0; i < dim; i++ {
		// Subtract projections onto all previous basis vectors.
		for j := 0; j < i; j++ {
			dot := vecDot(Q[i], Q[j], dim)
			for k := 0; k < dim; k++ {
				Q[i][k] -= dot * Q[j][k]
			}
		}

		// Normalize to unit length.
		norm := vecNorm(Q[i], dim)
		if norm > 0 {
			for k := 0; k < dim; k++ {
				Q[i][k] /= norm
			}
		}
	}

	return Q
}

// vecDot computes dot product of two vectors up to length n.
func vecDot(a, b []float64, n int) float64 {
	var sum float64
	for i := 0; i < n; i++ {
		sum += a[i] * b[i]
	}
	return sum
}

// vecNorm computes L2 norm of a vector up to length n.
func vecNorm(v []float64, n int) float64 {
	var sum float64
	for i := 0; i < n; i++ {
		sum += v[i] * v[i]
	}
	return math.Sqrt(sum)
}
