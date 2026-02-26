// Package pybridge provides a bridge to the Python RLM toolkit for NLP operations
// that require embeddings, semantic search, and other ML capabilities.
package pybridge

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"os/exec"
	"sync"
	"time"
)

// Bridge communicates with the Python RLM toolkit via subprocess JSON-RPC.
type Bridge struct {
	pythonPath string
	scriptPath string
	timeout    time.Duration
	mu         sync.Mutex
}

// Config holds Python bridge configuration.
type Config struct {
	PythonPath string        // Path to python executable (default: "python")
	ScriptPath string        // Path to bridge script
	Timeout    time.Duration // Command timeout (default: 30s)
}

// NewBridge creates a new Python bridge.
func NewBridge(cfg Config) *Bridge {
	if cfg.PythonPath == "" {
		cfg.PythonPath = "python"
	}
	if cfg.Timeout == 0 {
		cfg.Timeout = 30 * time.Second
	}
	return &Bridge{
		pythonPath: cfg.PythonPath,
		scriptPath: cfg.ScriptPath,
		timeout:    cfg.Timeout,
	}
}

// Request represents a JSON-RPC request to the Python bridge.
type Request struct {
	Method string      `json:"method"`
	Params interface{} `json:"params"`
}

// Response represents a JSON-RPC response from the Python bridge.
type Response struct {
	Result json.RawMessage `json:"result,omitempty"`
	Error  string          `json:"error,omitempty"`
}

// Call invokes a method on the Python bridge and returns the raw JSON result.
func (b *Bridge) Call(ctx context.Context, method string, params interface{}) (json.RawMessage, error) {
	b.mu.Lock()
	defer b.mu.Unlock()

	req := Request{Method: method, Params: params}
	reqData, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("marshal request: %w", err)
	}

	ctx, cancel := context.WithTimeout(ctx, b.timeout)
	defer cancel()

	cmd := exec.CommandContext(ctx, b.pythonPath, b.scriptPath)
	cmd.Stdin = bytes.NewReader(reqData)

	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	if err := cmd.Run(); err != nil {
		return nil, fmt.Errorf("python bridge error: %w (stderr: %s)", err, stderr.String())
	}

	var resp Response
	if err := json.Unmarshal(stdout.Bytes(), &resp); err != nil {
		return nil, fmt.Errorf("unmarshal response: %w (raw: %s)", err, stdout.String())
	}

	if resp.Error != "" {
		return nil, fmt.Errorf("python error: %s", resp.Error)
	}

	return resp.Result, nil
}

// IsAvailable checks if the Python interpreter and bridge script are accessible.
func (b *Bridge) IsAvailable() bool {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	cmd := exec.CommandContext(ctx, b.pythonPath, "--version")
	return cmd.Run() == nil
}

// EmbeddingResult holds the result of an embedding computation.
type EmbeddingResult struct {
	Embedding []float64 `json:"embedding"`
	Model     string    `json:"model"`
}

// ComputeEmbedding computes an embedding vector for the given text.
func (b *Bridge) ComputeEmbedding(ctx context.Context, text string) (*EmbeddingResult, error) {
	result, err := b.Call(ctx, "compute_embedding", map[string]string{"text": text})
	if err != nil {
		return nil, err
	}
	var emb EmbeddingResult
	if err := json.Unmarshal(result, &emb); err != nil {
		return nil, fmt.Errorf("unmarshal embedding: %w", err)
	}
	return &emb, nil
}

// SemanticSearchResult holds a search result with similarity score.
type SemanticSearchResult struct {
	FactID     string  `json:"fact_id"`
	Content    string  `json:"content"`
	Similarity float64 `json:"similarity"`
}

// SemanticSearch performs vector similarity search.
func (b *Bridge) SemanticSearch(ctx context.Context, query string, limit int) ([]SemanticSearchResult, error) {
	result, err := b.Call(ctx, "semantic_search", map[string]interface{}{
		"query": query,
		"limit": limit,
	})
	if err != nil {
		return nil, err
	}
	var results []SemanticSearchResult
	if err := json.Unmarshal(result, &results); err != nil {
		return nil, fmt.Errorf("unmarshal search results: %w", err)
	}
	return results, nil
}
