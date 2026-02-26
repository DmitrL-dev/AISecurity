package pybridge

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestNewBridge_Defaults(t *testing.T) {
	b := NewBridge(Config{})
	require.NotNil(t, b)
	assert.Equal(t, "python", b.pythonPath)
	assert.Equal(t, "", b.scriptPath)
	assert.Equal(t, 30_000_000_000, int(b.timeout)) // 30s in nanoseconds
}

func TestNewBridge_Custom(t *testing.T) {
	b := NewBridge(Config{
		PythonPath: "/usr/bin/python3",
		ScriptPath: "/path/to/bridge.py",
		Timeout:    60_000_000_000,
	})
	assert.Equal(t, "/usr/bin/python3", b.pythonPath)
	assert.Equal(t, "/path/to/bridge.py", b.scriptPath)
}

func TestBridge_IsAvailable(t *testing.T) {
	b := NewBridge(Config{PythonPath: "python"})
	// This test checks if python is on PATH — may be true or false.
	// We just verify it doesn't panic.
	_ = b.IsAvailable()
}

func TestRequest_Marshal(t *testing.T) {
	req := Request{
		Method: "compute_embedding",
		Params: map[string]string{"text": "hello"},
	}
	assert.Equal(t, "compute_embedding", req.Method)
}

func TestResponse_Fields(t *testing.T) {
	resp := Response{Error: "test error"}
	assert.Equal(t, "test error", resp.Error)
	assert.Nil(t, resp.Result)
}

func TestEmbeddingResult_Fields(t *testing.T) {
	r := EmbeddingResult{
		Embedding: []float64{0.1, 0.2, 0.3},
		Model:     "all-MiniLM-L6-v2",
	}
	assert.Len(t, r.Embedding, 3)
	assert.Equal(t, "all-MiniLM-L6-v2", r.Model)
}

func TestSemanticSearchResult_Fields(t *testing.T) {
	r := SemanticSearchResult{
		FactID:     "fact-123",
		Content:    "Go is fast",
		Similarity: 0.95,
	}
	assert.Equal(t, "fact-123", r.FactID)
	assert.InDelta(t, 0.95, r.Similarity, 0.001)
}
