package supervisor

import (
	"context"
	"encoding/json"
	"testing"
	"time"

	"github.com/sentinel-community/gomcp/pkg/security"
)

func TestSecureSupervisor_RateLimiting(t *testing.T) {
	cfg := SecureConfig{
		Config: Config{
			DefaultTimeout: time.Second,
		},
		RateLimitPerClient: 3,
		RateLimitWindow:    time.Second,
	}
	s := NewSecure(cfg)
	defer s.ShutdownSecure()

	// Register a dummy worker with a tool
	worker := &Worker{
		ID:    "test-worker",
		Tools: []ToolDef{{Name: "test_tool"}},
	}
	s.RegisterWorker(worker)

	clientID := "test-client"

	// First 3 calls should succeed
	for i := 0; i < 3; i++ {
		call := &ToolCall{
			RequestID: "req-" + string(rune('A'+i)),
			ToolName:  "test_tool",
			Arguments: json.RawMessage(`{}`),
		}
		result := s.CallToolSecure(context.Background(), clientID, call)
		if result.Error != nil && result.Error.Code == ErrPermissionDenied {
			t.Errorf("call %d should not be rate limited", i+1)
		}
	}

	// 4th call should be rate limited
	call := &ToolCall{
		RequestID: "req-D",
		ToolName:  "test_tool",
		Arguments: json.RawMessage(`{}`),
	}
	result := s.CallToolSecure(context.Background(), clientID, call)
	if result.Error == nil || result.Error.Code != ErrPermissionDenied {
		t.Error("4th call should be rate limited")
	}
}

func TestSecureSupervisor_InputValidation(t *testing.T) {
	cfg := SecureConfig{
		Config: Config{
			DefaultTimeout: time.Second,
		},
		RateLimitPerClient: 100,
		RateLimitWindow:    time.Minute,
	}
	s := NewSecure(cfg)
	defer s.ShutdownSecure()

	worker := &Worker{
		ID:    "test-worker",
		Tools: []ToolDef{{Name: "test_tool"}},
	}
	s.RegisterWorker(worker)

	// Test XSS rejection
	call := &ToolCall{
		RequestID: "req-xss",
		ToolName:  "test_tool",
		Arguments: json.RawMessage(`{"msg": "<script>evil()</script>"}`),
	}
	result := s.CallToolSecure(context.Background(), "client1", call)
	if result.Error == nil || result.Error.Code != ErrInvalidArguments {
		t.Error("XSS payload should be rejected")
	}

	// Test valid input passes
	call = &ToolCall{
		RequestID: "req-valid",
		ToolName:  "test_tool",
		Arguments: json.RawMessage(`{"name": "safe value"}`),
	}
	result = s.CallToolSecure(context.Background(), "client2", call)
	if result.Error != nil && result.Error.Code == ErrInvalidArguments {
		t.Error("valid input should not be rejected")
	}
}

func TestSecureSupervisor_AuditLogging(t *testing.T) {
	cfg := SecureConfig{
		Config: Config{
			DefaultTimeout: time.Second,
		},
		RateLimitPerClient: 100,
		RateLimitWindow:    time.Minute,
		MaxAuditEvents:     100,
	}
	s := NewSecure(cfg)
	defer s.ShutdownSecure()

	worker := &Worker{
		ID:    "test-worker",
		Tools: []ToolDef{{Name: "audit_tool"}},
	}
	s.RegisterWorker(worker)

	// Make a call
	call := &ToolCall{
		RequestID: "audit-req-1",
		ToolName:  "audit_tool",
		Arguments: json.RawMessage(`{}`),
	}
	s.CallToolSecure(context.Background(), "audit-client", call)

	// Check audit log
	events := s.AuditEvents()
	if len(events) < 2 {
		t.Errorf("expected at least 2 audit events (call + result), got %d", len(events))
	}

	// Verify event types
	foundToolCall := false
	foundToolResult := false
	for _, e := range events {
		if e.EventType == security.AuditToolCall {
			foundToolCall = true
		}
		if e.EventType == security.AuditToolResult {
			foundToolResult = true
		}
	}
	if !foundToolCall {
		t.Error("missing AuditToolCall event")
	}
	if !foundToolResult {
		t.Error("missing AuditToolResult event")
	}
}

func TestSecureSupervisor_TemplateInjectionBlocked(t *testing.T) {
	cfg := SecureConfig{
		Config: Config{
			DefaultTimeout: time.Second,
		},
	}
	s := NewSecure(cfg)
	defer s.ShutdownSecure()

	worker := &Worker{
		ID:    "test-worker",
		Tools: []ToolDef{{Name: "test_tool"}},
	}
	s.RegisterWorker(worker)

	testCases := []struct {
		name    string
		payload string
	}{
		{"jinja", `{"tpl": "{{ config.secret }}"}`},
		{"shell_env", `{"cmd": "${HOME}/evil"}`},
		{"javascript", `{"url": "javascript:alert(1)"}`},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			call := &ToolCall{
				RequestID: "req-" + tc.name,
				ToolName:  "test_tool",
				Arguments: json.RawMessage(tc.payload),
			}
			result := s.CallToolSecure(context.Background(), "client", call)
			if result.Error == nil || result.Error.Code != ErrInvalidArguments {
				t.Errorf("%s injection should be blocked", tc.name)
			}
		})
	}
}

func TestSecureSupervisor_RemainingRequests(t *testing.T) {
	cfg := SecureConfig{
		Config: Config{
			DefaultTimeout: time.Second,
		},
		RateLimitPerClient: 10,
		RateLimitWindow:    time.Minute,
	}
	s := NewSecure(cfg)
	defer s.ShutdownSecure()

	worker := &Worker{
		ID:    "test-worker",
		Tools: []ToolDef{{Name: "test_tool"}},
	}
	s.RegisterWorker(worker)

	clientID := "remaining-client"

	// Initial should be full
	if s.RemainingRequests(clientID) != 10 {
		t.Errorf("expected 10 remaining, got %d", s.RemainingRequests(clientID))
	}

	// After 3 calls
	for i := 0; i < 3; i++ {
		call := &ToolCall{
			RequestID: "req-rem-" + string(rune('A'+i)),
			ToolName:  "test_tool",
			Arguments: json.RawMessage(`{}`),
		}
		s.CallToolSecure(context.Background(), clientID, call)
	}

	if s.RemainingRequests(clientID) != 7 {
		t.Errorf("expected 7 remaining after 3 calls, got %d", s.RemainingRequests(clientID))
	}
}

// Benchmark tests
func BenchmarkSecureSupervisor_CallToolSecure(b *testing.B) {
	cfg := SecureConfig{
		Config: Config{
			DefaultTimeout: time.Second,
		},
		RateLimitPerClient: 1000000,
		RateLimitWindow:    time.Hour,
	}
	s := NewSecure(cfg)
	defer s.ShutdownSecure()

	worker := &Worker{
		ID:    "bench-worker",
		Tools: []ToolDef{{Name: "bench_tool"}},
	}
	s.RegisterWorker(worker)

	ctx := context.Background()
	call := &ToolCall{
		RequestID: "bench-req",
		ToolName:  "bench_tool",
		Arguments: json.RawMessage(`{"key": "value", "nested": {"data": [1,2,3]}}`),
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		s.CallToolSecure(ctx, "bench-client", call)
	}
}
