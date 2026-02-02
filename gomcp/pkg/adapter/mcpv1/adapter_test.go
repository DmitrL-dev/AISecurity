package mcpv1

import (
	"bytes"
	"context"
	"encoding/json"
	"strings"
	"testing"
	"time"

	"github.com/sentinel-community/gomcp/pkg/supervisor"
)

func TestNewAdapter(t *testing.T) {
	sup := supervisor.New(supervisor.Config{})
	defer sup.Shutdown()

	adapter := NewAdapter(sup)
	if adapter == nil {
		t.Fatal("NewAdapter() returned nil")
	}

	if adapter.supervisor == nil {
		t.Error("adapter.supervisor is nil")
	}
}

func TestJSONRPCRequest(t *testing.T) {
	req := JSONRPCRequest{
		JSONRPC: "2.0",
		ID:      1,
		Method:  "ping",
	}

	data, err := json.Marshal(req)
	if err != nil {
		t.Fatalf("Marshal error: %v", err)
	}

	var parsed JSONRPCRequest
	if err := json.Unmarshal(data, &parsed); err != nil {
		t.Fatalf("Unmarshal error: %v", err)
	}

	if parsed.Method != "ping" {
		t.Errorf("Method = %q, want %q", parsed.Method, "ping")
	}
}

func TestJSONRPCResponse(t *testing.T) {
	resp := JSONRPCResponse{
		JSONRPC: "2.0",
		ID:      1,
		Result:  map[string]interface{}{"status": "ok"},
	}

	data, err := json.Marshal(resp)
	if err != nil {
		t.Fatalf("Marshal error: %v", err)
	}

	if !bytes.Contains(data, []byte(`"status":"ok"`)) {
		t.Errorf("Response should contain status:ok, got %s", data)
	}
}

func TestJSONRPCErrorResponse(t *testing.T) {
	resp := JSONRPCResponse{
		JSONRPC: "2.0",
		ID:      1,
		Error: &JSONRPCError{
			Code:    -32601,
			Message: "Method not found",
		},
	}

	data, err := json.Marshal(resp)
	if err != nil {
		t.Fatalf("Marshal error: %v", err)
	}

	if !bytes.Contains(data, []byte(`"code":-32601`)) {
		t.Errorf("Response should contain error code, got %s", data)
	}
}

func TestAdapterSendResult(t *testing.T) {
	sup := supervisor.New(supervisor.Config{})
	defer sup.Shutdown()

	var output bytes.Buffer
	adapter := &Adapter{
		supervisor: sup,
		stdout:     &output,
	}

	adapter.sendResult(1, map[string]interface{}{"ok": true})

	if output.Len() == 0 {
		t.Error("sendResult() produced no output")
	}

	var resp JSONRPCResponse
	if err := json.Unmarshal(bytes.TrimSpace(output.Bytes()), &resp); err != nil {
		t.Fatalf("Output is not valid JSON: %v", err)
	}

	if resp.ID != float64(1) {
		t.Errorf("ID = %v, want 1", resp.ID)
	}
}

func TestAdapterSendError(t *testing.T) {
	sup := supervisor.New(supervisor.Config{})
	defer sup.Shutdown()

	var output bytes.Buffer
	adapter := &Adapter{
		supervisor: sup,
		stdout:     &output,
	}

	adapter.sendError(2, -32600, "Invalid Request", "details here")

	var resp JSONRPCResponse
	if err := json.Unmarshal(bytes.TrimSpace(output.Bytes()), &resp); err != nil {
		t.Fatalf("Output is not valid JSON: %v", err)
	}

	if resp.Error == nil {
		t.Fatal("Error should not be nil")
	}

	if resp.Error.Code != -32600 {
		t.Errorf("Error.Code = %d, want -32600", resp.Error.Code)
	}
}

func TestAdapterHandleInitialize(t *testing.T) {
	sup := supervisor.New(supervisor.Config{})
	defer sup.Shutdown()

	var output bytes.Buffer
	adapter := &Adapter{
		supervisor: sup,
		stdout:     &output,
	}

	req := &JSONRPCRequest{
		JSONRPC: "2.0",
		ID:      1,
		Method:  "initialize",
	}

	adapter.handleRequest(req)
	time.Sleep(10 * time.Millisecond)

	var resp JSONRPCResponse
	if err := json.Unmarshal(bytes.TrimSpace(output.Bytes()), &resp); err != nil {
		t.Fatalf("Output is not valid JSON: %v, output: %s", err, output.String())
	}

	result, ok := resp.Result.(map[string]interface{})
	if !ok {
		t.Fatal("Result should be a map")
	}

	if result["protocolVersion"] != "2025-11-25" {
		t.Errorf("protocolVersion = %v, want 2025-11-25", result["protocolVersion"])
	}
}

func TestAdapterHandleListTools(t *testing.T) {
	sup := supervisor.New(supervisor.Config{})
	defer sup.Shutdown()

	sup.RegisterWorker(&supervisor.Worker{
		ID: "test",
		Tools: []supervisor.ToolDef{
			{Name: "my_tool", Description: "My test tool"},
		},
	})

	var output bytes.Buffer
	adapter := &Adapter{
		supervisor: sup,
		stdout:     &output,
	}

	req := &JSONRPCRequest{
		JSONRPC: "2.0",
		ID:      2,
		Method:  "tools/list",
	}

	adapter.handleRequest(req)
	time.Sleep(10 * time.Millisecond)

	var resp JSONRPCResponse
	if err := json.Unmarshal(bytes.TrimSpace(output.Bytes()), &resp); err != nil {
		t.Fatalf("Output is not valid JSON: %v", err)
	}

	result, ok := resp.Result.(map[string]interface{})
	if !ok {
		t.Fatal("Result should be a map")
	}

	tools, ok := result["tools"].([]interface{})
	if !ok {
		t.Fatal("tools should be an array")
	}

	if len(tools) != 1 {
		t.Errorf("len(tools) = %d, want 1", len(tools))
	}
}

func TestAdapterHandlePing(t *testing.T) {
	sup := supervisor.New(supervisor.Config{})
	defer sup.Shutdown()

	var output bytes.Buffer
	adapter := &Adapter{
		supervisor: sup,
		stdout:     &output,
	}

	req := &JSONRPCRequest{
		JSONRPC: "2.0",
		ID:      3,
		Method:  "ping",
	}

	adapter.handleRequest(req)
	time.Sleep(10 * time.Millisecond)

	var resp JSONRPCResponse
	if err := json.Unmarshal(bytes.TrimSpace(output.Bytes()), &resp); err != nil {
		t.Fatalf("Output is not valid JSON: %v", err)
	}

	if resp.Error != nil {
		t.Errorf("ping should not return error: %v", resp.Error)
	}
}

func TestAdapterHandleUnknownMethod(t *testing.T) {
	sup := supervisor.New(supervisor.Config{})
	defer sup.Shutdown()

	var output bytes.Buffer
	adapter := &Adapter{
		supervisor: sup,
		stdout:     &output,
	}

	req := &JSONRPCRequest{
		JSONRPC: "2.0",
		ID:      4,
		Method:  "unknown_method",
	}

	adapter.handleRequest(req)
	time.Sleep(10 * time.Millisecond)

	var resp JSONRPCResponse
	if err := json.Unmarshal(bytes.TrimSpace(output.Bytes()), &resp); err != nil {
		t.Fatalf("Output is not valid JSON: %v", err)
	}

	if resp.Error == nil {
		t.Fatal("Unknown method should return error")
	}

	if resp.Error.Code != -32601 {
		t.Errorf("Error.Code = %d, want -32601", resp.Error.Code)
	}
}

func TestAdapterHandleCallTool(t *testing.T) {
	sup := supervisor.New(supervisor.Config{})
	defer sup.Shutdown()

	sup.RegisterWorker(&supervisor.Worker{
		ID: "worker",
		Tools: []supervisor.ToolDef{
			{Name: "echo_tool", Description: "Echoes input"},
		},
	})

	var output bytes.Buffer
	adapter := &Adapter{
		supervisor: sup,
		stdout:     &output,
	}

	params, _ := json.Marshal(map[string]interface{}{
		"name":      "echo_tool",
		"arguments": map[string]interface{}{"message": "hello"},
	})

	req := &JSONRPCRequest{
		JSONRPC: "2.0",
		ID:      5,
		Method:  "tools/call",
		Params:  params,
	}

	adapter.handleRequest(req)
	time.Sleep(10 * time.Millisecond)

	var resp JSONRPCResponse
	if err := json.Unmarshal(bytes.TrimSpace(output.Bytes()), &resp); err != nil {
		t.Fatalf("Output is not valid JSON: %v", err)
	}

	if resp.Error != nil {
		t.Errorf("tools/call should not return error: %v", resp.Error)
	}

	if resp.Result == nil {
		t.Error("Result should not be nil")
	}
}

func TestAdapterHandleCallToolNotFound(t *testing.T) {
	sup := supervisor.New(supervisor.Config{})
	defer sup.Shutdown()

	var output bytes.Buffer
	adapter := &Adapter{
		supervisor: sup,
		stdout:     &output,
	}

	params, _ := json.Marshal(map[string]interface{}{
		"name":      "nonexistent_tool",
		"arguments": map[string]interface{}{},
	})

	req := &JSONRPCRequest{
		JSONRPC: "2.0",
		ID:      6,
		Method:  "tools/call",
		Params:  params,
	}

	adapter.handleRequest(req)
	time.Sleep(10 * time.Millisecond)

	var resp JSONRPCResponse
	if err := json.Unmarshal(bytes.TrimSpace(output.Bytes()), &resp); err != nil {
		t.Fatalf("Output is not valid JSON: %v", err)
	}

	if resp.Error == nil {
		t.Fatal("Calling nonexistent tool should return error")
	}
}

func TestAdapterHandleCallToolInvalidParams(t *testing.T) {
	sup := supervisor.New(supervisor.Config{})
	defer sup.Shutdown()

	var output bytes.Buffer
	adapter := &Adapter{
		supervisor: sup,
		stdout:     &output,
	}

	req := &JSONRPCRequest{
		JSONRPC: "2.0",
		ID:      7,
		Method:  "tools/call",
		Params:  json.RawMessage(`"invalid"`),
	}

	adapter.handleRequest(req)
	time.Sleep(10 * time.Millisecond)

	var resp JSONRPCResponse
	if err := json.Unmarshal(bytes.TrimSpace(output.Bytes()), &resp); err != nil {
		t.Fatalf("Output is not valid JSON: %v", err)
	}

	if resp.Error == nil {
		t.Fatal("Invalid params should return error")
	}

	if resp.Error.Code != -32602 {
		t.Errorf("Error.Code = %d, want -32602 (Invalid params)", resp.Error.Code)
	}
}

func TestAdapterRun(t *testing.T) {
	sup := supervisor.New(supervisor.Config{})
	defer sup.Shutdown()

	input := `{"jsonrpc":"2.0","id":1,"method":"ping"}` + "\n"
	var output bytes.Buffer

	adapter := &Adapter{
		supervisor: sup,
		stdin:      strings.NewReader(input),
		stdout:     &output,
	}

	ctx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
	defer cancel()

	go adapter.Run(ctx)
	time.Sleep(50 * time.Millisecond)

	if output.Len() == 0 {
		t.Error("Run() should have produced output")
	}
}

func TestAdapterRunEmptyLine(t *testing.T) {
	sup := supervisor.New(supervisor.Config{})
	defer sup.Shutdown()

	// Empty line followed by valid request
	input := "\n" + `{"jsonrpc":"2.0","id":1,"method":"ping"}` + "\n"
	var output bytes.Buffer

	adapter := &Adapter{
		supervisor: sup,
		stdin:      strings.NewReader(input),
		stdout:     &output,
	}

	ctx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
	defer cancel()

	go adapter.Run(ctx)
	time.Sleep(50 * time.Millisecond)

	// Should still process the ping
	if output.Len() == 0 {
		t.Error("Run() should skip empty lines and process valid requests")
	}
}

func TestAdapterRunInvalidJSON(t *testing.T) {
	sup := supervisor.New(supervisor.Config{})
	defer sup.Shutdown()

	input := `not valid json` + "\n"
	var output bytes.Buffer

	adapter := &Adapter{
		supervisor: sup,
		stdin:      strings.NewReader(input),
		stdout:     &output,
	}

	ctx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
	defer cancel()

	go adapter.Run(ctx)
	time.Sleep(50 * time.Millisecond)

	// Should send parse error
	if output.Len() == 0 {
		t.Error("Run() should send parse error for invalid JSON")
	}

	var resp JSONRPCResponse
	if err := json.Unmarshal(bytes.TrimSpace(output.Bytes()), &resp); err != nil {
		t.Fatalf("Output is not valid JSON: %v", err)
	}

	if resp.Error == nil {
		t.Error("Should have error for invalid JSON")
	}

	if resp.Error.Code != -32700 {
		t.Errorf("Error.Code = %d, want -32700 (Parse error)", resp.Error.Code)
	}
}
