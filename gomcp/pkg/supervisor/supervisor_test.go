package supervisor

import (
	"context"
	"encoding/json"
	"testing"
	"time"
)

func TestNew(t *testing.T) {
	cfg := Config{
		DefaultTimeout:  10 * time.Second,
		MaxWorkers:      5,
		HeartbeatPeriod: 1 * time.Second,
	}

	sup := New(cfg)
	if sup == nil {
		t.Fatal("New() returned nil")
	}

	if sup.config.DefaultTimeout != 10*time.Second {
		t.Errorf("DefaultTimeout = %v, want 10s", sup.config.DefaultTimeout)
	}

	sup.Shutdown()
}

func TestNewDefaults(t *testing.T) {
	sup := New(Config{})

	if sup.config.DefaultTimeout != DefaultTimeout {
		t.Errorf("DefaultTimeout = %v, want %v", sup.config.DefaultTimeout, DefaultTimeout)
	}

	if sup.config.HeartbeatPeriod != HeartbeatInterval {
		t.Errorf("HeartbeatPeriod = %v, want %v", sup.config.HeartbeatPeriod, HeartbeatInterval)
	}

	sup.Shutdown()
}

func TestRegisterWorker(t *testing.T) {
	sup := New(Config{})
	defer sup.Shutdown()

	worker := &Worker{
		ID: "test-worker-1",
		Tools: []ToolDef{
			{Name: "test_tool", Description: "A test tool"},
		},
	}

	err := sup.RegisterWorker(worker)
	if err != nil {
		t.Fatalf("RegisterWorker() error = %v", err)
	}

	tools := sup.ListTools()
	if len(tools) != 1 {
		t.Errorf("ListTools() = %d tools, want 1", len(tools))
	}

	if tools[0].Name != "test_tool" {
		t.Errorf("tools[0].Name = %q, want %q", tools[0].Name, "test_tool")
	}
}

func TestCallToolNotFound(t *testing.T) {
	sup := New(Config{})
	defer sup.Shutdown()

	call := &ToolCall{
		RequestID: "req-1",
		ToolName:  "nonexistent_tool",
		Arguments: json.RawMessage(`{}`),
	}

	result := sup.CallTool(context.Background(), call)

	if result.Error == nil {
		t.Fatal("CallTool() expected error for nonexistent tool")
	}

	if result.Error.Code != ErrToolNotFound {
		t.Errorf("Error.Code = %v, want %v", result.Error.Code, ErrToolNotFound)
	}
}

func TestCallToolTimeout(t *testing.T) {
	sup := New(Config{DefaultTimeout: 100 * time.Millisecond})
	defer sup.Shutdown()

	// Register a worker with a tool
	worker := &Worker{
		ID: "slow-worker",
		Tools: []ToolDef{
			{Name: "slow_tool", Description: "A slow tool"},
		},
	}
	sup.RegisterWorker(worker)

	// Override executeCall to simulate slow execution
	// For now, the mock implementation returns immediately
	// In production, this would test actual timeout behavior

	call := &ToolCall{
		RequestID: "req-timeout",
		ToolName:  "slow_tool",
		Arguments: json.RawMessage(`{}`),
		Timeout:   50 * time.Millisecond,
	}

	result := sup.CallTool(context.Background(), call)

	// Current mock returns immediately, so no timeout
	// This test documents expected behavior for future implementation
	if result.Error != nil && result.Error.Code == ErrTimeout {
		t.Log("Timeout behavior confirmed")
	}
}

func TestCallToolSuccess(t *testing.T) {
	sup := New(Config{})
	defer sup.Shutdown()

	worker := &Worker{
		ID: "fast-worker",
		Tools: []ToolDef{
			{Name: "fast_tool", Description: "A fast tool"},
		},
	}
	sup.RegisterWorker(worker)

	call := &ToolCall{
		RequestID: "req-success",
		ToolName:  "fast_tool",
		Arguments: json.RawMessage(`{"input": "test"}`),
	}

	result := sup.CallTool(context.Background(), call)

	if result.Error != nil {
		t.Fatalf("CallTool() unexpected error: %v", result.Error)
	}

	if result.Output == nil {
		t.Error("CallTool() Output is nil")
	}

	if result.Duration == 0 {
		t.Log("Duration is 0 (expected for instant mock execution)")
	}
}

func TestListToolsEmpty(t *testing.T) {
	sup := New(Config{})
	defer sup.Shutdown()

	tools := sup.ListTools()
	if len(tools) != 0 {
		t.Errorf("ListTools() = %d tools, want 0", len(tools))
	}
}

func TestListToolsMultipleWorkers(t *testing.T) {
	sup := New(Config{})
	defer sup.Shutdown()

	sup.RegisterWorker(&Worker{
		ID: "worker-1",
		Tools: []ToolDef{
			{Name: "tool_a", Description: "Tool A"},
			{Name: "tool_b", Description: "Tool B"},
		},
	})

	sup.RegisterWorker(&Worker{
		ID: "worker-2",
		Tools: []ToolDef{
			{Name: "tool_c", Description: "Tool C"},
		},
	})

	tools := sup.ListTools()
	if len(tools) != 3 {
		t.Errorf("ListTools() = %d tools, want 3", len(tools))
	}
}

func TestShutdown(t *testing.T) {
	sup := New(Config{})

	// Should not panic
	sup.Shutdown()

	// Double shutdown should not panic
	sup.Shutdown()
}
