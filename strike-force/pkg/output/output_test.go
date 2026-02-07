package output

import (
	"strings"
	"testing"
	"time"

	"github.com/sentinel-community/strike-force/pkg/vectors"
)

// ============================================================================
// TDD: Output Reporter Tests
// ============================================================================

func TestReporter_TextMode(t *testing.T) {
	r := NewReporter("text")
	result := &vectors.Result{
		Vector:   "mcp",
		Strategy: "stealth_probe",
		Target:   "wss://target.dev",
		Success:  true,
		Response: "test_response",
	}

	output := r.Format(result)
	if output == "" {
		t.Fatal("text reporter returned empty output")
	}
	if !strings.Contains(output, "mcp") {
		t.Error("text output missing vector name")
	}
}

func TestReporter_JSONMode(t *testing.T) {
	r := NewReporter("json")
	result := &vectors.Result{
		Vector:    "mcp",
		Strategy:  "stealth_probe",
		Target:    "wss://target.dev",
		Success:   true,
		Response:  "test_response",
		Timestamp: time.Now(),
	}

	output := r.Format(result)
	if output == "" {
		t.Fatal("json reporter returned empty output")
	}
	// Must be valid JSON (starts with { or [)
	trimmed := strings.TrimSpace(output)
	if trimmed[0] != '{' {
		t.Errorf("JSON output doesn't start with '{': %s", trimmed[:20])
	}
}

func TestReporter_DefaultIsText(t *testing.T) {
	r := NewReporter("")
	if r.Mode() != "text" {
		t.Errorf("expected default mode 'text', got '%s'", r.Mode())
	}
}
