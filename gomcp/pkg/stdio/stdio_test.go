package stdio

import (
	"bytes"
	"context"
	"encoding/json"
	"strings"
	"testing"
	"time"
)

func TestNewAdapter(t *testing.T) {
	a := NewAdapter(Config{})

	if a == nil {
		t.Fatal("adapter should not be nil")
	}
	if a.serverName != "gomcp" {
		t.Errorf("expected default name gomcp, got %s", a.serverName)
	}
	if a.serverVersion != "1.0.0" {
		t.Errorf("expected default version 1.0.0, got %s", a.serverVersion)
	}
}

func TestNewAdapter_CustomConfig(t *testing.T) {
	a := NewAdapter(Config{
		ServerName:    "custom",
		ServerVersion: "2.0.0",
	})

	if a.serverName != "custom" {
		t.Errorf("expected custom name, got %s", a.serverName)
	}
	if a.serverVersion != "2.0.0" {
		t.Errorf("expected 2.0.0, got %s", a.serverVersion)
	}
}

func TestAdapter_Initialize(t *testing.T) {
	input := `{"jsonrpc":"2.0","id":"1","method":"initialize","params":{}}` + "\n"
	reader := strings.NewReader(input)
	var output bytes.Buffer

	a := NewAdapter(Config{
		Reader: reader,
		Writer: &output,
	})

	ctx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
	defer cancel()

	a.Run(ctx)

	var resp Response
	json.NewDecoder(&output).Decode(&resp)

	if string(resp.ID) != "\"1\"" {
		t.Errorf("expected id \"1\", got %s", string(resp.ID))
	}

	if resp.Error != nil {
		t.Errorf("unexpected error: %v", resp.Error)
	}
	if resp.Result == nil {
		t.Error("expected result")
	}
}

func TestAdapter_Ping(t *testing.T) {
	input := `{"jsonrpc":"2.0","id":"2","method":"ping"}` + "\n"
	reader := strings.NewReader(input)
	var output bytes.Buffer

	a := NewAdapter(Config{
		Reader: reader,
		Writer: &output,
	})

	ctx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
	defer cancel()

	a.Run(ctx)

	var resp Response
	json.NewDecoder(&output).Decode(&resp)

	if resp.Error != nil {
		t.Errorf("unexpected error: %v", resp.Error)
	}

	var result map[string]string
	json.Unmarshal(resp.Result, &result)
	if result["status"] != "pong" {
		t.Errorf("expected pong, got %s", result["status"])
	}
}

func TestAdapter_ToolsList_Empty(t *testing.T) {
	input := `{"jsonrpc":"2.0","id":"3","method":"tools/list"}` + "\n"
	reader := strings.NewReader(input)
	var output bytes.Buffer

	a := NewAdapter(Config{
		Reader: reader,
		Writer: &output,
	})

	ctx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
	defer cancel()

	a.Run(ctx)

	var resp Response
	json.NewDecoder(&output).Decode(&resp)

	if resp.Error != nil {
		t.Errorf("unexpected error: %v", resp.Error)
	}

	var result ToolsListResult
	json.Unmarshal(resp.Result, &result)
	if len(result.Tools) != 0 {
		t.Errorf("expected 0 tools, got %d", len(result.Tools))
	}
}

func TestAdapter_MethodNotFound(t *testing.T) {
	input := `{"jsonrpc":"2.0","id":"4","method":"unknown/method"}` + "\n"
	reader := strings.NewReader(input)
	var output bytes.Buffer

	a := NewAdapter(Config{
		Reader: reader,
		Writer: &output,
	})

	ctx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
	defer cancel()

	a.Run(ctx)

	var resp Response
	json.NewDecoder(&output).Decode(&resp)

	if resp.Error == nil {
		t.Error("expected error")
	}
	if resp.Error.Code != CodeMethodNotFound {
		t.Errorf("expected code %d, got %d", CodeMethodNotFound, resp.Error.Code)
	}
}

func TestAdapter_InvalidJSON(t *testing.T) {
	input := `{invalid json}` + "\n"
	reader := strings.NewReader(input)
	var output bytes.Buffer

	a := NewAdapter(Config{
		Reader: reader,
		Writer: &output,
	})

	ctx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
	defer cancel()

	a.Run(ctx)

	var resp Response
	json.NewDecoder(&output).Decode(&resp)

	if resp.Error == nil {
		t.Error("expected error")
	}
	if resp.Error.Code != CodeParseError {
		t.Errorf("expected code %d, got %d", CodeParseError, resp.Error.Code)
	}
}

func TestAdapter_InvalidJSONRPCVersion(t *testing.T) {
	input := `{"jsonrpc":"1.0","id":"5","method":"ping"}` + "\n"
	reader := strings.NewReader(input)
	var output bytes.Buffer

	a := NewAdapter(Config{
		Reader: reader,
		Writer: &output,
	})

	ctx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
	defer cancel()

	a.Run(ctx)

	var resp Response
	json.NewDecoder(&output).Decode(&resp)

	if resp.Error == nil {
		t.Error("expected error")
	}
	if resp.Error.Code != CodeInvalidRequest {
		t.Errorf("expected code %d, got %d", CodeInvalidRequest, resp.Error.Code)
	}
}

func TestAdapter_ToolsCall_NoSupervisor(t *testing.T) {
	input := `{"jsonrpc":"2.0","id":"6","method":"tools/call","params":{"name":"test"}}` + "\n"
	reader := strings.NewReader(input)
	var output bytes.Buffer

	a := NewAdapter(Config{
		Reader: reader,
		Writer: &output,
	})

	ctx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
	defer cancel()

	a.Run(ctx)

	var resp Response
	json.NewDecoder(&output).Decode(&resp)

	if resp.Error == nil {
		t.Error("expected error for no supervisor")
	}
}

func TestAdapter_ToolsCall_InvalidParams(t *testing.T) {
	input := `{"jsonrpc":"2.0","id":"7","method":"tools/call","params":"invalid"}` + "\n"
	reader := strings.NewReader(input)
	var output bytes.Buffer

	a := NewAdapter(Config{
		Reader: reader,
		Writer: &output,
	})

	ctx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
	defer cancel()

	a.Run(ctx)

	var resp Response
	json.NewDecoder(&output).Decode(&resp)

	if resp.Error == nil {
		t.Error("expected error")
	}
	if resp.Error.Code != CodeInvalidParams {
		t.Errorf("expected code %d, got %d", CodeInvalidParams, resp.Error.Code)
	}
}

func TestAdapter_Shutdown(t *testing.T) {
	input := `{"jsonrpc":"2.0","id":"8","method":"shutdown"}` + "\n"
	reader := strings.NewReader(input)
	var output bytes.Buffer

	a := NewAdapter(Config{
		Reader: reader,
		Writer: &output,
	})

	go func() {
		time.Sleep(50 * time.Millisecond)
		a.Stop()
	}()

	ctx, cancel := context.WithTimeout(context.Background(), 500*time.Millisecond)
	defer cancel()

	a.Run(ctx)

	var resp Response
	json.NewDecoder(&output).Decode(&resp)

	if resp.Error != nil {
		t.Errorf("unexpected error: %v", resp.Error)
	}
}

func TestAdapter_IsRunning(t *testing.T) {
	a := NewAdapter(Config{})

	if a.IsRunning() {
		t.Error("should not be running before start")
	}
}

func TestAdapter_Stop(t *testing.T) {
	a := NewAdapter(Config{
		Reader: strings.NewReader(""),
		Writer: &bytes.Buffer{},
	})

	// Stop should not panic on non-running adapter
	a.Stop()
}

func TestAdapter_MultipleRequests(t *testing.T) {
	input := `{"jsonrpc":"2.0","id":"1","method":"ping"}
{"jsonrpc":"2.0","id":"2","method":"ping"}
`
	reader := strings.NewReader(input)
	var output bytes.Buffer

	a := NewAdapter(Config{
		Reader: reader,
		Writer: &output,
	})

	ctx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
	defer cancel()

	a.Run(ctx)

	lines := strings.Split(strings.TrimSpace(output.String()), "\n")
	if len(lines) != 2 {
		t.Errorf("expected 2 responses, got %d", len(lines))
	}
}

func TestResponse_MarshalJSON(t *testing.T) {
	resp := Response{
		ID:      "test",
		JSONRPC: "2.0",
		Result:  json.RawMessage(`{"ok":true}`),
	}

	data, err := json.Marshal(resp)
	if err != nil {
		t.Fatalf("marshal error: %v", err)
	}

	if !strings.Contains(string(data), `"id":"test"`) {
		t.Error("missing id")
	}
	if !strings.Contains(string(data), `"jsonrpc":"2.0"`) {
		t.Error("missing jsonrpc")
	}
}

func TestRequest_UnmarshalJSON(t *testing.T) {
	data := `{"jsonrpc":"2.0","id":"123","method":"test","params":{"key":"value"}}`

	var req Request
	if err := json.Unmarshal([]byte(data), &req); err != nil {
		t.Fatalf("unmarshal error: %v", err)
	}

	if string(req.ID) != "\"123\"" {
		t.Errorf("expected id \"123\", got %s", req.ID)
	}
	if req.Method != "test" {
		t.Errorf("expected method test, got %s", req.Method)
	}
}

// Benchmark
func BenchmarkAdapter_Ping(b *testing.B) {
	for i := 0; i < b.N; i++ {
		input := `{"jsonrpc":"2.0","id":"1","method":"ping"}` + "\n"
		reader := strings.NewReader(input)
		var output bytes.Buffer

		a := NewAdapter(Config{
			Reader: reader,
			Writer: &output,
		})

		ctx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
		a.Run(ctx)
		cancel()
	}
}
