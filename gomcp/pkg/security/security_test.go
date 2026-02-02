package security

import (
	"encoding/json"
	"strings"
	"testing"
	"time"
)

func TestValidator_ValidatesValidJSON(t *testing.T) {
	v := DefaultValidator()

	validInputs := []string{
		`{"name": "test", "value": 123}`,
		`{"nested": {"deep": {"value": true}}}`,
		`{"array": [1, 2, 3, 4, 5]}`,
		`{"mixed": {"items": [{"a": 1}, {"b": 2}]}}`,
		`{}`,
		`null`,
	}

	for _, input := range validInputs {
		result := v.ValidateJSON(json.RawMessage(input))
		if !result.Valid {
			t.Errorf("expected valid for input %s, got errors: %v", input, result.Errors)
		}
	}
}

func TestValidator_RejectsXSSPatterns(t *testing.T) {
	v := DefaultValidator()

	xssInputs := []string{
		`{"msg": "<script>alert('xss')</script>"}`,
		`{"url": "javascript:evil()"}`,
		`{"inject": "; drop table users"}`,
	}

	for _, input := range xssInputs {
		result := v.ValidateJSON(json.RawMessage(input))
		if result.Valid {
			t.Errorf("expected rejection for XSS pattern: %s", input)
		}
		if len(result.Errors) == 0 {
			t.Errorf("expected errors for XSS pattern: %s", input)
		}
	}
}

func TestValidator_RejectsTemplateInjection(t *testing.T) {
	v := DefaultValidator()

	templateInputs := []string{
		`{"tpl": "${process.env.SECRET}"}`,
		`{"jinja": "{{ config.password }}"}`,
	}

	for _, input := range templateInputs {
		result := v.ValidateJSON(json.RawMessage(input))
		if result.Valid {
			t.Errorf("expected rejection for template injection: %s", input)
		}
	}
}

func TestValidator_RejectsExcessiveNesting(t *testing.T) {
	v := &Validator{MaxDepth: 3, MaxStringLength: 1000, MaxArrayLength: 100}

	// Create deeply nested JSON
	deepJSON := `{"a": {"b": {"c": {"d": {"e": "too deep"}}}}}`
	result := v.ValidateJSON(json.RawMessage(deepJSON))

	if result.Valid {
		t.Error("expected rejection for excessive nesting")
	}

	foundDepthError := false
	for _, err := range result.Errors {
		if strings.Contains(err.Message, "nesting depth") {
			foundDepthError = true
			break
		}
	}
	if !foundDepthError {
		t.Error("expected nesting depth error")
	}
}

func TestValidator_RejectsOversizedStrings(t *testing.T) {
	v := &Validator{MaxStringLength: 100, MaxArrayLength: 100, MaxDepth: 10}

	longString := strings.Repeat("x", 200)
	input := `{"data": "` + longString + `"}`

	result := v.ValidateJSON(json.RawMessage(input))
	if result.Valid {
		t.Error("expected rejection for oversized string")
	}
}

func TestValidator_RejectsOversizedArrays(t *testing.T) {
	v := &Validator{MaxStringLength: 1000, MaxArrayLength: 5, MaxDepth: 10}

	input := `{"items": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]}`
	result := v.ValidateJSON(json.RawMessage(input))

	if result.Valid {
		t.Error("expected rejection for oversized array")
	}
}

func TestAuditLogger_LogsEvents(t *testing.T) {
	logger := NewInMemoryAuditLogger(100)

	event := &AuditEvent{
		ID:        "test-1",
		Timestamp: time.Now(),
		EventType: AuditToolCall,
		ToolName:  "test_tool",
		ClientID:  "client-1",
		Success:   true,
	}

	logger.Log(event)
	events := logger.Events()

	if len(events) != 1 {
		t.Errorf("expected 1 event, got %d", len(events))
	}
	if events[0].ToolName != "test_tool" {
		t.Errorf("expected tool_name 'test_tool', got '%s'", events[0].ToolName)
	}
}

func TestAuditLogger_RingBufferBehavior(t *testing.T) {
	logger := NewInMemoryAuditLogger(3)

	for i := 0; i < 5; i++ {
		logger.Log(&AuditEvent{
			ID:        string(rune('A' + i)),
			Timestamp: time.Now(),
			EventType: AuditToolCall,
		})
	}

	events := logger.Events()
	if len(events) != 3 {
		t.Errorf("expected 3 events (ring buffer), got %d", len(events))
	}

	// Should have events C, D, E (first two dropped)
	if events[0].ID != "C" {
		t.Errorf("expected first event ID 'C', got '%s'", events[0].ID)
	}
}

func TestRateLimiter_AllowsWithinLimit(t *testing.T) {
	rl := NewRateLimiter(5, time.Second)
	defer rl.Stop()

	clientID := "test-client"

	for i := 0; i < 5; i++ {
		if !rl.Allow(clientID) {
			t.Errorf("request %d should be allowed within limit", i+1)
		}
	}
}

func TestRateLimiter_BlocksOverLimit(t *testing.T) {
	rl := NewRateLimiter(3, time.Second)
	defer rl.Stop()

	clientID := "test-client"

	// Use up the limit
	for i := 0; i < 3; i++ {
		rl.Allow(clientID)
	}

	// This should be blocked
	if rl.Allow(clientID) {
		t.Error("request over limit should be blocked")
	}
}

func TestRateLimiter_ResetsAfterWindow(t *testing.T) {
	rl := NewRateLimiter(2, 50*time.Millisecond)
	defer rl.Stop()

	clientID := "test-client"

	// Use up the limit
	rl.Allow(clientID)
	rl.Allow(clientID)

	if rl.Allow(clientID) {
		t.Error("should be blocked before window resets")
	}

	// Wait for window to reset
	time.Sleep(60 * time.Millisecond)

	if !rl.Allow(clientID) {
		t.Error("should be allowed after window reset")
	}
}

func TestRateLimiter_SeparatesClients(t *testing.T) {
	rl := NewRateLimiter(2, time.Second)
	defer rl.Stop()

	// Client 1 uses up limit
	rl.Allow("client1")
	rl.Allow("client1")

	// Client 2 should still be allowed
	if !rl.Allow("client2") {
		t.Error("client2 should be allowed independently")
	}
}

func TestRateLimiter_RemainingCount(t *testing.T) {
	rl := NewRateLimiter(5, time.Second)
	defer rl.Stop()

	clientID := "test-client"

	if rl.Remaining(clientID) != 5 {
		t.Errorf("expected 5 remaining for new client")
	}

	rl.Allow(clientID)
	rl.Allow(clientID)

	if rl.Remaining(clientID) != 3 {
		t.Errorf("expected 3 remaining after 2 requests, got %d", rl.Remaining(clientID))
	}
}

// Benchmark tests
func BenchmarkValidator_ValidateJSON(b *testing.B) {
	v := DefaultValidator()
	input := json.RawMessage(`{"name": "test", "nested": {"deep": {"value": 123}}, "array": [1, 2, 3]}`)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		v.ValidateJSON(input)
	}
}

func BenchmarkRateLimiter_Allow(b *testing.B) {
	rl := NewRateLimiter(1000000, time.Second)
	defer rl.Stop()

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		rl.Allow("client-1")
	}
}

func BenchmarkAuditLogger_Log(b *testing.B) {
	logger := NewInMemoryAuditLogger(10000)
	event := &AuditEvent{
		ID:        "bench",
		Timestamp: time.Now(),
		EventType: AuditToolCall,
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		logger.Log(event)
	}
}
