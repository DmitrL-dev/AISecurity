package pybridge

import (
	"context"
	"fmt"

	"github.com/syntrex/gomcp/internal/domain/vectorstore"
)

// PyBridgeEmbedder wraps the Python bridge as an Embedder.
// This is a transitional adapter — will be replaced by ONNXEmbedder in Phase 3.2.
type PyBridgeEmbedder struct {
	bridge    *Bridge
	dimension int
}

// NewPyBridgeEmbedder creates an Embedder backed by the Python bridge.
func NewPyBridgeEmbedder(bridge *Bridge) *PyBridgeEmbedder {
	return &PyBridgeEmbedder{
		bridge:    bridge,
		dimension: 384, // MiniLM-L12-v2 default.
	}
}

// Embed computes an embedding via the Python subprocess.
func (e *PyBridgeEmbedder) Embed(ctx context.Context, text string) ([]float64, error) {
	result, err := e.bridge.ComputeEmbedding(ctx, text)
	if err != nil {
		return nil, fmt.Errorf("pybridge embed: %w", err)
	}
	if len(result.Embedding) > 0 {
		e.dimension = len(result.Embedding) // Auto-detect from first result.
	}
	return result.Embedding, nil
}

// Dimension returns the embedding vector dimensionality.
func (e *PyBridgeEmbedder) Dimension() int {
	return e.dimension
}

// Name returns the embedder identifier.
func (e *PyBridgeEmbedder) Name() string {
	return "pybridge:sentence-transformers"
}

// Mode returns FULL — Python bridge uses neural embeddings.
func (e *PyBridgeEmbedder) Mode() vectorstore.OracleMode {
	return vectorstore.OracleModeFull
}
