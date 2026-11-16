//go:build onnx

package onnx

import (
	"log"

	"github.com/syntrex/gomcp/internal/domain/vectorstore"
)

// NewEmbedderWithFallback attempts to create an ONNX embedder.
// If ONNX Runtime or model is not available, falls back to FTS5Embedder.
// Always returns a working Embedder — never nil.
func NewEmbedderWithFallback(rlmDir string) vectorstore.Embedder {
	// Try ONNX first.
	onnxEmb, err := NewEmbedder(Config{RlmDir: rlmDir})
	if err == nil {
		log.Printf("Oracle: ONNX embedder active (%s, dim=%d) [ORACLE: FULL]",
			onnxEmb.Name(), onnxEmb.Dimension())
		return onnxEmb
	}

	// ONNX unavailable — degrade gracefully.
	log.Printf("Oracle: ONNX unavailable (%v) — falling back to FTS5 [ORACLE: DEGRADED]", err)
	return vectorstore.NewFTS5Embedder()
}
