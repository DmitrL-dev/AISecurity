// Package vectorstore implements persistent storage for intent vectors (DIP H2.1).
//
// Intent vectors are the output of the Intent Distiller (H0.2). Storing them
// enables neuroplastic routing — matching new intents against known patterns
// to determine optimal processing paths.
//
// Features:
//   - In-memory store with capacity management (LRU eviction)
//   - Cosine similarity search for nearest-neighbor matching
//   - Route labels for categorized intent patterns
//   - Pluggable Embedder interface (ONNX, FTS5 fallback)
//   - Thread-safe for concurrent access
package vectorstore

import "context"

// Embedder generates vector embeddings from text.
// Implementations: ONNXEmbedder (full), FTS5Embedder (fallback, pure Go).
type Embedder interface {
	// Embed computes a vector embedding for the given text.
	// Returns a float64 slice of length Dimension().
	Embed(ctx context.Context, text string) ([]float64, error)

	// Dimension returns the embedding vector dimensionality.
	// MiniLM-L12-v2: 384. FTS5 fallback: len(vocabulary).
	Dimension() int

	// Name returns the embedder identifier (e.g. "onnx:MiniLM-L12-v2", "fts5:fallback").
	Name() string

	// Mode returns the current oracle mode.
	// FULL = neural embeddings, DEGRADED = text-based fallback.
	Mode() OracleMode
}

// OracleMode indicates the operational mode of the embedding engine.
type OracleMode int

const (
	// OracleModeFull indicates neural ONNX embeddings are active.
	OracleModeFull OracleMode = iota
	// OracleModeDegraded indicates fallback text-based search (FTS5/Levenshtein).
	OracleModeDegraded
)

// String returns human-readable oracle mode.
func (m OracleMode) String() string {
	switch m {
	case OracleModeFull:
		return "FULL"
	case OracleModeDegraded:
		return "DEGRADED"
	default:
		return "UNKNOWN"
	}
}
