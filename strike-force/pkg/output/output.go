package output

import (
	"encoding/json"
	"fmt"
	"strings"

	"github.com/sentinel-community/strike-force/pkg/vectors"
)

// ============================================================================
// OUTPUT REPORTER — Structured output for automation
// ============================================================================

// Reporter formats attack results in text or JSON.
type Reporter struct {
	mode string // "text" or "json"
}

// NewReporter creates a reporter with the specified mode.
// Falls back to "text" for unknown modes.
func NewReporter(mode string) *Reporter {
	if mode != "json" && mode != "text" {
		mode = "text"
	}
	return &Reporter{mode: mode}
}

// Mode returns the current output mode.
func (r *Reporter) Mode() string {
	return r.mode
}

// Format renders a Result in the configured output format.
func (r *Reporter) Format(result *vectors.Result) string {
	if r.mode == "json" {
		return r.formatJSON(result)
	}
	return r.formatText(result)
}

func (r *Reporter) formatJSON(result *vectors.Result) string {
	b, err := json.MarshalIndent(result, "", "  ")
	if err != nil {
		return fmt.Sprintf(`{"error": "%v"}`, err)
	}
	return string(b)
}

func (r *Reporter) formatText(result *vectors.Result) string {
	var sb strings.Builder
	status := "FAILED"
	if result.Success {
		status = "SUCCESS"
	}

	sb.WriteString(fmt.Sprintf("[%s] Vector: %s | Strategy: %s\n", status, result.Vector, result.Strategy))
	sb.WriteString(fmt.Sprintf("  Target:   %s\n", result.Target))
	sb.WriteString(fmt.Sprintf("  Duration: %s\n", result.Duration))

	if result.Response != "" {
		sb.WriteString(fmt.Sprintf("  Response: %s\n", truncate(result.Response, 200)))
	}

	if result.Error != "" {
		sb.WriteString(fmt.Sprintf("  Error:    %s\n", result.Error))
	}

	for i, e := range result.Evidence {
		sb.WriteString(fmt.Sprintf("  Evidence[%d] (%s): %s\n", i, e.Type, truncate(e.Data, 100)))
	}

	return sb.String()
}

func truncate(s string, maxLen int) string {
	if len(s) <= maxLen {
		return s
	}
	return s[:maxLen] + "..."
}
