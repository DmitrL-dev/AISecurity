package grpcserver

import (
	"context"
	"encoding/json"
	"net"
	"testing"
	"time"
)

// MockHandler for testing
type mockHandler struct {
	tools   []ToolDefinition
	results map[string]json.RawMessage
	errors  map[string]error
}

func (m *mockHandler) ListTools() []ToolDefinition {
	return m.tools
}

func (m *mockHandler) CallTool(ctx context.Context, name string, args json.RawMessage) (json.RawMessage, error) {
	if err, ok := m.errors[name]; ok {
		return nil, err
	}
	if result, ok := m.results[name]; ok {
		return result, nil
	}
	return json.RawMessage(`{}`), nil
}

func TestNewServer(t *testing.T) {
	srv := NewServer(Config{})
	if srv == nil {
		t.Fatal("server should not be nil")
	}
}

func TestNewServer_CustomConfig(t *testing.T) {
	srv := NewServer(Config{
		Addr:          ":9999",
		MaxConcurrent: 50,
	})
	if srv.config.Addr != ":9999" {
		t.Errorf("expected :9999, got %s", srv.config.Addr)
	}
}

func TestServer_StartStop(t *testing.T) {
	srv := NewServer(Config{Addr: ":0"})

	if err := srv.Start(); err != nil {
		t.Fatalf("start error: %v", err)
	}

	if !srv.IsRunning() {
		t.Error("server should be running")
	}

	if err := srv.Stop(); err != nil {
		t.Errorf("stop error: %v", err)
	}

	if srv.IsRunning() {
		t.Error("server should not be running")
	}
}

func TestServer_Addr(t *testing.T) {
	srv := NewServer(Config{Addr: ":0"})
	srv.Start()
	defer srv.Stop()

	addr := srv.Addr()
	if addr == "" {
		t.Error("addr should not be empty")
	}
}

func TestServer_HandleListTools(t *testing.T) {
	handler := &mockHandler{
		tools: []ToolDefinition{
			{Name: "tool1", Description: "desc1"},
			{Name: "tool2", Description: "desc2"},
		},
	}

	srv := NewServer(Config{Handler: handler})

	req := &RPCRequest{ID: "1", Method: "gomcp.ListTools"}
	resp := srv.handleRequest(context.Background(), req)

	if resp.Error != nil {
		t.Errorf("unexpected error: %v", resp.Error)
	}

	var result map[string][]ToolDefinition
	json.Unmarshal(resp.Result, &result)
	if len(result["tools"]) != 2 {
		t.Errorf("expected 2 tools, got %d", len(result["tools"]))
	}
}

func TestServer_HandleListTools_Empty(t *testing.T) {
	srv := NewServer(Config{})

	req := &RPCRequest{ID: "1", Method: "gomcp.ListTools"}
	resp := srv.handleRequest(context.Background(), req)

	if resp.Error != nil {
		t.Errorf("unexpected error: %v", resp.Error)
	}

	var result map[string][]ToolDefinition
	json.Unmarshal(resp.Result, &result)
	if len(result["tools"]) != 0 {
		t.Errorf("expected 0 tools, got %d", len(result["tools"]))
	}
}

func TestServer_HandleCallTool(t *testing.T) {
	handler := &mockHandler{
		results: map[string]json.RawMessage{
			"mytool": json.RawMessage(`{"result":"ok"}`),
		},
	}

	srv := NewServer(Config{Handler: handler})

	params, _ := json.Marshal(CallToolParams{Name: "mytool"})
	req := &RPCRequest{ID: "1", Method: "gomcp.CallTool", Params: params}
	resp := srv.handleRequest(context.Background(), req)

	if resp.Error != nil {
		t.Errorf("unexpected error: %v", resp.Error)
	}
}

func TestServer_HandleCallTool_NoHandler(t *testing.T) {
	srv := NewServer(Config{})

	params, _ := json.Marshal(CallToolParams{Name: "test"})
	req := &RPCRequest{ID: "1", Method: "gomcp.CallTool", Params: params}
	resp := srv.handleRequest(context.Background(), req)

	if resp.Error == nil {
		t.Error("expected error for no handler")
	}
	if resp.Error.Code != ErrInternal {
		t.Errorf("expected ErrInternal, got %d", resp.Error.Code)
	}
}

func TestServer_HandleCallTool_InvalidParams(t *testing.T) {
	srv := NewServer(Config{Handler: &mockHandler{}})

	req := &RPCRequest{ID: "1", Method: "gomcp.CallTool", Params: json.RawMessage(`invalid`)}
	resp := srv.handleRequest(context.Background(), req)

	if resp.Error == nil {
		t.Error("expected error for invalid params")
	}
	if resp.Error.Code != ErrInvalidParams {
		t.Errorf("expected ErrInvalidParams, got %d", resp.Error.Code)
	}
}

func TestServer_HandleHealth(t *testing.T) {
	srv := NewServer(Config{})
	srv.startTime = time.Now()

	req := &RPCRequest{ID: "1", Method: "gomcp.Health"}
	resp := srv.handleRequest(context.Background(), req)

	if resp.Error != nil {
		t.Errorf("unexpected error: %v", resp.Error)
	}

	var result map[string]string
	json.Unmarshal(resp.Result, &result)
	if result["status"] != "healthy" {
		t.Errorf("expected healthy, got %s", result["status"])
	}
}

func TestServer_HandleStats(t *testing.T) {
	srv := NewServer(Config{})
	srv.startTime = time.Now()
	srv.callCount = 42

	req := &RPCRequest{ID: "1", Method: "gomcp.Stats"}
	resp := srv.handleRequest(context.Background(), req)

	if resp.Error != nil {
		t.Errorf("unexpected error: %v", resp.Error)
	}

	var result map[string]interface{}
	json.Unmarshal(resp.Result, &result)
	if int64(result["calls"].(float64)) != 42 {
		t.Errorf("expected 42 calls, got %v", result["calls"])
	}
}

func TestServer_HandleMethodNotFound(t *testing.T) {
	srv := NewServer(Config{})

	req := &RPCRequest{ID: "1", Method: "unknown.Method"}
	resp := srv.handleRequest(context.Background(), req)

	if resp.Error == nil {
		t.Error("expected error for unknown method")
	}
	if resp.Error.Code != ErrMethodNotFound {
		t.Errorf("expected ErrMethodNotFound, got %d", resp.Error.Code)
	}
}

func TestServer_Stats(t *testing.T) {
	srv := NewServer(Config{})
	srv.startTime = time.Now()
	srv.callCount = 100

	calls, uptime := srv.Stats()
	if calls != 100 {
		t.Errorf("expected 100 calls, got %d", calls)
	}
	if uptime < 0 {
		t.Error("uptime should be non-negative")
	}
}

func TestServer_StopIdempotent(t *testing.T) {
	srv := NewServer(Config{Addr: ":0"})
	srv.Start()

	// Should not panic on multiple stops
	srv.Stop()
	srv.Stop()
}

func TestServer_IsRunning_NotStarted(t *testing.T) {
	srv := NewServer(Config{})
	if srv.IsRunning() {
		t.Error("should not be running before start")
	}
}

func TestServer_Connection(t *testing.T) {
	handler := &mockHandler{
		tools: []ToolDefinition{{Name: "test", Description: "test"}},
	}

	srv := NewServer(Config{Addr: ":0", Handler: handler})
	if err := srv.Start(); err != nil {
		t.Fatalf("start error: %v", err)
	}
	defer srv.Stop()

	// Connect to server
	conn, err := net.Dial("tcp", srv.Addr())
	if err != nil {
		t.Fatalf("dial error: %v", err)
	}
	defer conn.Close()

	// Send request
	encoder := json.NewEncoder(conn)
	decoder := json.NewDecoder(conn)

	req := RPCRequest{ID: "1", Method: "gomcp.ListTools"}
	encoder.Encode(req)

	var resp RPCResponse
	decoder.Decode(&resp)

	if resp.Error != nil {
		t.Errorf("unexpected error: %v", resp.Error)
	}
}

func TestRPCResponse_Marshal(t *testing.T) {
	resp := RPCResponse{
		ID:     "test",
		Result: json.RawMessage(`{"ok":true}`),
	}

	data, err := json.Marshal(resp)
	if err != nil {
		t.Fatalf("marshal error: %v", err)
	}

	if len(data) == 0 {
		t.Error("data should not be empty")
	}
}

func TestRPCError_Marshal(t *testing.T) {
	err := RPCError{Code: 1, Message: "test error"}
	data, marshalErr := json.Marshal(err)
	if marshalErr != nil {
		t.Fatalf("marshal error: %v", marshalErr)
	}

	var decoded RPCError
	json.Unmarshal(data, &decoded)
	if decoded.Code != 1 {
		t.Errorf("expected code 1, got %d", decoded.Code)
	}
}

// Benchmark
func BenchmarkServer_HandleListTools(b *testing.B) {
	handler := &mockHandler{
		tools: []ToolDefinition{
			{Name: "tool1", Description: "desc1"},
		},
	}
	srv := NewServer(Config{Handler: handler})

	req := &RPCRequest{ID: "1", Method: "gomcp.ListTools"}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		srv.handleRequest(context.Background(), req)
	}
}
