package wasmsandbox

import (
	"context"
	"testing"
	"time"
)

func TestNewSandbox(t *testing.T) {
	s := NewSandbox()
	stats := s.Stats()
	if stats.TotalExecutions != 0 {
		t.Errorf("total = %d, want 0", stats.TotalExecutions)
	}
}

func TestExecute_Log(t *testing.T) {
	s := NewSandbox()
	result := s.Execute(ActionRequest{
		PlaybookID: "pb-001",
		ActionType: "log",
		Params:     map[string]string{"message": "test event"},
	})
	if !result.Success {
		t.Errorf("expected success, got error: %s", result.Error)
	}
	if !result.Sandboxed {
		t.Error("should be sandboxed")
	}
}

func TestExecute_BlockIP(t *testing.T) {
	s := NewSandbox()
	result := s.Execute(ActionRequest{
		PlaybookID: "pb-002",
		ActionType: "block_ip",
		Params:     map[string]string{"ip": "10.0.0.1"},
	})
	if !result.Success {
		t.Errorf("expected success: %s", result.Error)
	}
}

func TestExecute_MissingParam(t *testing.T) {
	s := NewSandbox()
	result := s.Execute(ActionRequest{
		PlaybookID: "pb-003",
		ActionType: "block_ip",
		Params:     map[string]string{}, // Missing 'ip'.
	})
	if result.Success {
		t.Error("expected failure for missing param")
	}
}

func TestExecute_UnknownAction(t *testing.T) {
	s := NewSandbox()
	result := s.Execute(ActionRequest{
		PlaybookID: "pb-004",
		ActionType: "delete_everything",
		Params:     map[string]string{},
	})
	if result.Success {
		t.Error("expected failure for unknown action")
	}
}

func TestExecute_Timeout(t *testing.T) {
	s := NewSandbox()
	s.RegisterHandler("slow", func(ctx context.Context, params map[string]string) (string, error) {
		select {
		case <-time.After(5 * time.Second):
			return "done", nil
		case <-ctx.Done():
			return "", ctx.Err()
		}
	})

	result := s.Execute(ActionRequest{
		PlaybookID: "pb-005",
		ActionType: "slow",
		Timeout:    50 * time.Millisecond,
	})
	if result.Success {
		t.Error("expected timeout failure")
	}
}

func TestExecute_CustomHandler(t *testing.T) {
	s := NewSandbox()
	s.RegisterHandler("custom", func(_ context.Context, params map[string]string) (string, error) {
		return "custom result: " + params["key"], nil
	})

	result := s.Execute(ActionRequest{
		ActionType: "custom",
		Params:     map[string]string{"key": "value"},
	})
	if !result.Success {
		t.Errorf("expected success: %s", result.Error)
	}
	if result.Output != "custom result: value" {
		t.Errorf("output = %s", result.Output)
	}
}

func TestStats(t *testing.T) {
	s := NewSandbox()
	s.Execute(ActionRequest{ActionType: "log", Params: map[string]string{}})
	s.Execute(ActionRequest{ActionType: "block_ip", Params: map[string]string{"ip": "1.2.3.4"}})
	s.Execute(ActionRequest{ActionType: "unknown"})

	stats := s.Stats()
	if stats.TotalExecutions != 3 {
		t.Errorf("total = %d, want 3", stats.TotalExecutions)
	}
	if stats.Succeeded != 2 {
		t.Errorf("succeeded = %d, want 2", stats.Succeeded)
	}
	if stats.Failed != 1 {
		t.Errorf("failed = %d, want 1", stats.Failed)
	}
}
