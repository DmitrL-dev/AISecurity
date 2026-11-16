//go:build onnx

package onnx

import (
	"context"
	"fmt"
	"log"
	"math"
	"sync"

	ort "github.com/yalue/onnxruntime_go"

	"github.com/syntrex/gomcp/internal/domain/vectorstore"
)

// Embedder implements vectorstore.Embedder using ONNX Runtime.
// Runs paraphrase-multilingual-MiniLM-L12-v2 inference locally.
type Embedder struct {
	mu        sync.Mutex
	session   *ort.DynamicAdvancedSession
	tokenizer *Tokenizer
	dimension int
	modelName string
}

// Config holds ONNX embedder configuration.
type Config struct {
	RlmDir    string // Path to .rlm directory (for model discovery)
	ModelPath string // Override: direct path to .onnx model
	VocabPath string // Override: direct path to vocab.txt
	MaxSeqLen int    // Max sequence length (default: 128)
}

// NewEmbedder creates an ONNX-based embedder.
// Returns an error if the model or runtime cannot be loaded.
// Caller should fall back to FTS5Embedder on error.
func NewEmbedder(cfg Config) (*Embedder, error) {
	// Discover model paths if not explicitly provided.
	paths := &ModelPaths{
		ModelPath: cfg.ModelPath,
		VocabPath: cfg.VocabPath,
	}

	if paths.ModelPath == "" || paths.VocabPath == "" {
		discovered, err := DiscoverModel(cfg.RlmDir)
		if err != nil {
			return nil, fmt.Errorf("onnx discovery: %w", err)
		}
		if paths.ModelPath == "" {
			paths.ModelPath = discovered.ModelPath
		}
		if paths.VocabPath == "" {
			paths.VocabPath = discovered.VocabPath
		}
		// Set runtime path for ONNX Runtime initialization.
		if discovered.RuntimePath != "" {
			ort.SetSharedLibraryPath(discovered.RuntimePath)
		}
	}

	// Initialize ONNX Runtime.
	if err := ort.InitializeEnvironment(); err != nil {
		return nil, fmt.Errorf("onnx init: %w", err)
	}

	// Load tokenizer.
	maxSeqLen := cfg.MaxSeqLen
	if maxSeqLen <= 0 {
		maxSeqLen = 128
	}

	tokenizer, err := NewTokenizer(TokenizerConfig{
		VocabPath: paths.VocabPath,
		MaxLength: maxSeqLen,
	})
	if err != nil {
		return nil, fmt.Errorf("onnx tokenizer: %w", err)
	}

	log.Printf("ONNX tokenizer loaded: %d tokens from %s", tokenizer.VocabSize(), paths.VocabPath)

	// Create ONNX session.
	// MiniLM inputs: input_ids [1, seq_len], attention_mask [1, seq_len], token_type_ids [1, seq_len]
	// MiniLM output: last_hidden_state [1, seq_len, 384] → mean pool → [384]
	inputNames := []string{"input_ids", "attention_mask", "token_type_ids"}
	outputNames := []string{"last_hidden_state"}

	session, err := ort.NewDynamicAdvancedSession(
		paths.ModelPath,
		inputNames,
		outputNames,
		nil, // default session options
	)
	if err != nil {
		return nil, fmt.Errorf("onnx session: %w", err)
	}

	log.Printf("ONNX model loaded: %s (seq_len=%d)", paths.ModelPath, maxSeqLen)

	return &Embedder{
		session:   session,
		tokenizer: tokenizer,
		dimension: 384, // MiniLM-L12-v2.
		modelName: "MiniLM-L12-v2",
	}, nil
}

// Embed computes a 384-dim embedding via ONNX inference.
func (e *Embedder) Embed(ctx context.Context, text string) ([]float64, error) {
	e.mu.Lock()
	defer e.mu.Unlock()

	// Tokenize.
	encoded := e.tokenizer.Encode(text)

	seqLen := int64(len(encoded.InputIDs))
	shape := ort.Shape{1, seqLen}

	// Create input tensors.
	inputIDsTensor, err := ort.NewTensor(shape, encoded.InputIDs)
	if err != nil {
		return nil, fmt.Errorf("create input_ids tensor: %w", err)
	}
	defer inputIDsTensor.Destroy()

	attMaskTensor, err := ort.NewTensor(shape, encoded.AttentionMask)
	if err != nil {
		return nil, fmt.Errorf("create attention_mask tensor: %w", err)
	}
	defer attMaskTensor.Destroy()

	tokenTypeTensor, err := ort.NewTensor(shape, encoded.TokenTypeIDs)
	if err != nil {
		return nil, fmt.Errorf("create token_type_ids tensor: %w", err)
	}
	defer tokenTypeTensor.Destroy()

	// Create output tensor placeholder.
	outputShape := ort.Shape{1, seqLen, int64(e.dimension)}
	outputTensor, err := ort.NewEmptyTensor[float32](outputShape)
	if err != nil {
		return nil, fmt.Errorf("create output tensor: %w", err)
	}
	defer outputTensor.Destroy()

	// Run inference.
	err = e.session.Run(
		[]ort.ArbitraryTensor{inputIDsTensor, attMaskTensor, tokenTypeTensor},
		[]ort.ArbitraryTensor{outputTensor},
	)
	if err != nil {
		return nil, fmt.Errorf("onnx inference: %w", err)
	}

	// Mean pooling over non-padded tokens.
	rawOutput := outputTensor.GetData()
	embedding := meanPool(rawOutput, encoded.AttentionMask, int(seqLen), e.dimension)

	// L2 normalize.
	l2Normalize(embedding)

	return embedding, nil
}

// Dimension returns 384 (MiniLM-L12-v2).
func (e *Embedder) Dimension() int {
	return e.dimension
}

// Name returns the embedder identifier.
func (e *Embedder) Name() string {
	return fmt.Sprintf("onnx:%s", e.modelName)
}

// Mode returns FULL — ONNX provides neural embeddings.
func (e *Embedder) Mode() vectorstore.OracleMode {
	return vectorstore.OracleModeFull
}

// Close releases ONNX resources.
func (e *Embedder) Close() error {
	e.mu.Lock()
	defer e.mu.Unlock()
	if e.session != nil {
		e.session.Destroy()
	}
	return ort.DestroyEnvironment()
}

// meanPool computes mean pooling over the hidden states,
// considering only non-padded positions (attention_mask=1).
func meanPool(hiddenStates []float32, attentionMask []int64, seqLen, dim int) []float64 {
	result := make([]float64, dim)
	var count float64

	for i := 0; i < seqLen; i++ {
		if attentionMask[i] == 0 {
			continue
		}
		count++
		offset := i * dim
		for d := 0; d < dim; d++ {
			result[d] += float64(hiddenStates[offset+d])
		}
	}

	if count > 0 {
		for d := range result {
			result[d] /= count
		}
	}
	return result
}

// l2Normalize normalizes a vector in-place to unit length.
func l2Normalize(vec []float64) {
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
