package httpmode

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/sentinel-community/gomcp/pkg/security"
	"github.com/sentinel-community/gomcp/pkg/tenant"
)

// Mock handler for testing
type mockHandler struct {
	tools   []ToolInfo
	results map[string]json.RawMessage
	err     error
}

func (m *mockHandler) Execute(ctx context.Context, tool string, args json.RawMessage) (json.RawMessage, error) {
	if m.err != nil {
		return nil, m.err
	}
	if result, ok := m.results[tool]; ok {
		return result, nil
	}
	return nil, errors.New("tool not found: " + tool)
}

func (m *mockHandler) ListTools() []ToolInfo {
	return m.tools
}

func TestServer_ListTools(t *testing.T) {
	handler := &mockHandler{
		tools: []ToolInfo{
			{Name: "tool1", Description: "First tool"},
			{Name: "tool2", Description: "Second tool"},
		},
	}

	s := NewServer(Config{Handler: handler})
	req := httptest.NewRequest("GET", "/v1/tools", nil)
	rec := httptest.NewRecorder()

	s.handleListTools(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", rec.Code)
	}

	var tools []ToolInfo
	json.NewDecoder(rec.Body).Decode(&tools)

	if len(tools) != 2 {
		t.Errorf("expected 2 tools, got %d", len(tools))
	}
}

func TestServer_ListTools_Empty(t *testing.T) {
	s := NewServer(Config{})
	req := httptest.NewRequest("GET", "/v1/tools", nil)
	rec := httptest.NewRecorder()

	s.handleListTools(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", rec.Code)
	}
}

func TestServer_ToolCall_Success(t *testing.T) {
	handler := &mockHandler{
		results: map[string]json.RawMessage{
			"echo": json.RawMessage(`{"result": "hello"}`),
		},
	}

	s := NewServer(Config{Handler: handler})

	body := bytes.NewBufferString(`{"tool": "echo", "arguments": {"msg": "hello"}}`)
	req := httptest.NewRequest("POST", "/v1/tools/call", body)
	rec := httptest.NewRecorder()

	s.handleToolCall(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", rec.Code)
	}

	var resp ToolResponse
	json.NewDecoder(rec.Body).Decode(&resp)

	if !resp.Success {
		t.Error("expected success")
	}
}

func TestServer_ToolCall_Error(t *testing.T) {
	handler := &mockHandler{
		err: errors.New("tool failed"),
	}

	s := NewServer(Config{Handler: handler})

	body := bytes.NewBufferString(`{"tool": "fail", "arguments": {}}`)
	req := httptest.NewRequest("POST", "/v1/tools/call", body)
	rec := httptest.NewRecorder()

	s.handleToolCall(rec, req)

	var resp ToolResponse
	json.NewDecoder(rec.Body).Decode(&resp)

	if resp.Success {
		t.Error("expected failure")
	}
	if resp.Error == "" {
		t.Error("expected error message")
	}
}

func TestServer_ToolCall_InvalidJSON(t *testing.T) {
	s := NewServer(Config{})

	body := bytes.NewBufferString(`{invalid json}`)
	req := httptest.NewRequest("POST", "/v1/tools/call", body)
	rec := httptest.NewRecorder()

	s.handleToolCall(rec, req)

	if rec.Code != http.StatusBadRequest {
		t.Errorf("expected 400, got %d", rec.Code)
	}
}

func TestServer_ToolCall_MethodNotAllowed(t *testing.T) {
	s := NewServer(Config{})

	req := httptest.NewRequest("GET", "/v1/tools/call", nil)
	rec := httptest.NewRecorder()

	s.handleToolCall(rec, req)

	if rec.Code != http.StatusMethodNotAllowed {
		t.Errorf("expected 405, got %d", rec.Code)
	}
}

func TestServer_ToolCall_WithValidation(t *testing.T) {
	s := NewServer(Config{
		Handler:   &mockHandler{results: map[string]json.RawMessage{"t": json.RawMessage(`{}`)}},
		Validator: security.DefaultValidator(),
	})

	// XSS attack should be blocked
	body := bytes.NewBufferString(`{"tool": "t", "arguments": "<script>alert('xss')</script>"}`)
	req := httptest.NewRequest("POST", "/v1/tools/call", body)
	rec := httptest.NewRecorder()

	s.handleToolCall(rec, req)

	var resp ToolResponse
	json.NewDecoder(rec.Body).Decode(&resp)

	if resp.Success {
		t.Error("XSS should be blocked")
	}
}

func TestServer_ToolCall_WithTenant(t *testing.T) {
	tm := tenant.NewManager()
	tm.CreateTenant("t1", "Tenant 1", tenant.Quotas{})

	tenant1, _ := tm.GetTenant("t1")
	tenant1.SetAllowedTools([]string{"allowed_tool"})

	handler := &mockHandler{
		results: map[string]json.RawMessage{
			"allowed_tool": json.RawMessage(`{}`),
			"blocked_tool": json.RawMessage(`{}`),
		},
	}

	s := NewServer(Config{
		Handler:       handler,
		TenantManager: tm,
	})

	// Allowed tool
	body := bytes.NewBufferString(`{"tool": "allowed_tool", "arguments": {}, "tenant_id": "t1"}`)
	req := httptest.NewRequest("POST", "/v1/tools/call", body)
	rec := httptest.NewRecorder()
	s.handleToolCall(rec, req)

	var resp ToolResponse
	json.NewDecoder(rec.Body).Decode(&resp)
	if !resp.Success {
		t.Error("allowed tool should succeed")
	}

	// Blocked tool
	body = bytes.NewBufferString(`{"tool": "blocked_tool", "arguments": {}, "tenant_id": "t1"}`)
	req = httptest.NewRequest("POST", "/v1/tools/call", body)
	rec = httptest.NewRecorder()
	s.handleToolCall(rec, req)

	json.NewDecoder(rec.Body).Decode(&resp)
	if rec.Code != http.StatusForbidden {
		t.Error("blocked tool should be forbidden")
	}
}

func TestServer_ToolCall_TenantNotFound(t *testing.T) {
	tm := tenant.NewManager()
	s := NewServer(Config{
		Handler:       &mockHandler{results: map[string]json.RawMessage{"t": json.RawMessage(`{}`)}},
		TenantManager: tm,
	})

	body := bytes.NewBufferString(`{"tool": "t", "arguments": {}, "tenant_id": "nonexistent"}`)
	req := httptest.NewRequest("POST", "/v1/tools/call", body)
	rec := httptest.NewRecorder()

	s.handleToolCall(rec, req)

	if rec.Code != http.StatusForbidden {
		t.Errorf("expected 403, got %d", rec.Code)
	}
}

func TestServer_BatchCall(t *testing.T) {
	handler := &mockHandler{
		results: map[string]json.RawMessage{
			"t1": json.RawMessage(`{"r": 1}`),
			"t2": json.RawMessage(`{"r": 2}`),
		},
	}

	s := NewServer(Config{Handler: handler})

	body := bytes.NewBufferString(`{
		"requests": [
			{"tool": "t1", "arguments": {}},
			{"tool": "t2", "arguments": {}}
		],
		"parallel": true
	}`)
	req := httptest.NewRequest("POST", "/v1/tools/batch", body)
	rec := httptest.NewRecorder()

	s.handleBatchCall(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", rec.Code)
	}

	var resp BatchToolResponse
	json.NewDecoder(rec.Body).Decode(&resp)

	if resp.SuccessCount != 2 {
		t.Errorf("expected 2 successes, got %d", resp.SuccessCount)
	}
}

func TestServer_BatchCall_NoHandler(t *testing.T) {
	s := NewServer(Config{})

	body := bytes.NewBufferString(`{"requests": [{"tool": "t"}]}`)
	req := httptest.NewRequest("POST", "/v1/tools/batch", body)
	rec := httptest.NewRecorder()

	s.handleBatchCall(rec, req)

	if rec.Code != http.StatusServiceUnavailable {
		t.Errorf("expected 503, got %d", rec.Code)
	}
}

func TestServer_BasicHealth(t *testing.T) {
	s := NewServer(Config{})

	req := httptest.NewRequest("GET", "/health", nil)
	rec := httptest.NewRecorder()

	s.handleBasicHealth(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", rec.Code)
	}
}

func TestServer_IsRunning(t *testing.T) {
	s := NewServer(Config{Addr: ":0"})

	if s.IsRunning() {
		t.Error("should not be running before start")
	}
}

func TestServer_Addr(t *testing.T) {
	s := NewServer(Config{Addr: ":9090"})

	if s.Addr() != ":9090" {
		t.Errorf("expected :9090, got %s", s.Addr())
	}
}

func TestServer_DefaultAddr(t *testing.T) {
	s := NewServer(Config{})

	if s.Addr() != ":8080" {
		t.Errorf("expected default :8080, got %s", s.Addr())
	}
}

func TestServer_Stop_NotRunning(t *testing.T) {
	s := NewServer(Config{})

	err := s.Stop(context.Background())
	if err != nil {
		t.Errorf("stop on non-running server should not error: %v", err)
	}
}

func TestServer_ToolCall_NoHandler(t *testing.T) {
	s := NewServer(Config{})

	body := bytes.NewBufferString(`{"tool": "t", "arguments": {}}`)
	req := httptest.NewRequest("POST", "/v1/tools/call", body)
	rec := httptest.NewRecorder()

	s.handleToolCall(rec, req)

	if rec.Code != http.StatusServiceUnavailable {
		t.Errorf("expected 503, got %d", rec.Code)
	}
}

func TestServer_ToolCall_Latency(t *testing.T) {
	handler := &mockHandler{
		results: map[string]json.RawMessage{"t": json.RawMessage(`{}`)},
	}

	s := NewServer(Config{Handler: handler})

	body := bytes.NewBufferString(`{"tool": "t", "arguments": {}}`)
	req := httptest.NewRequest("POST", "/v1/tools/call", body)
	rec := httptest.NewRecorder()

	s.handleToolCall(rec, req)

	var resp ToolResponse
	json.NewDecoder(rec.Body).Decode(&resp)

	if resp.Latency == "" {
		t.Error("latency should be set")
	}
}

// Benchmark
func BenchmarkServer_ToolCall(b *testing.B) {
	handler := &mockHandler{
		results: map[string]json.RawMessage{"t": json.RawMessage(`{}`)},
	}
	s := NewServer(Config{Handler: handler})

	body := []byte(`{"tool": "t", "arguments": {}}`)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		req := httptest.NewRequest("POST", "/v1/tools/call", bytes.NewReader(body))
		rec := httptest.NewRecorder()
		s.handleToolCall(rec, req)
	}
}
