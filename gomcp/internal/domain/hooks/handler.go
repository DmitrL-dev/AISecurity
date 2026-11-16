// Package hooks implements the Syntrex Hook Provider domain logic (SDD-004).
//
// The hook provider intercepts IDE agent tool calls (Claude Code, Gemini CLI,
// Cursor) and runs them through sentinel-core's 67 engines + DIP Oracle
// before allowing execution.
package hooks

import (
	"encoding/json"
	"fmt"
	"time"
)

// IDE represents a supported IDE agent.
type IDE string

const (
	IDEClaude  IDE = "claude"
	IDEGemini  IDE = "gemini"
	IDECursor  IDE = "cursor"
)

// EventType represents the type of hook event from the IDE.
type EventType string

const (
	EventPreToolUse  EventType = "pre_tool_use"
	EventPostToolUse EventType = "post_tool_use"
	EventBeforeModel EventType = "before_model"
	EventCommand     EventType = "command"
	EventPrompt      EventType = "prompt"
)

// HookEvent represents an incoming hook event from an IDE agent.
type HookEvent struct {
	IDE       IDE               `json:"ide"`
	EventType EventType         `json:"event_type"`
	ToolName  string            `json:"tool_name,omitempty"`
	ToolInput json.RawMessage   `json:"tool_input,omitempty"`
	Content   string            `json:"content,omitempty"` // For prompt/command events
	SessionID string            `json:"session_id,omitempty"`
	Timestamp time.Time         `json:"timestamp"`
	Metadata  map[string]string `json:"metadata,omitempty"`
}

// Decision types for hook responses.
type DecisionType string

const (
	DecisionAllow  DecisionType = "allow"
	DecisionDeny   DecisionType = "deny"
	DecisionModify DecisionType = "modify"
)

// HookDecision is the response sent back to the IDE hook system.
type HookDecision struct {
	Decision  DecisionType `json:"decision"`
	Reason    string       `json:"reason"`
	Severity  string       `json:"severity,omitempty"`
	Matches   []Match      `json:"matches,omitempty"`
	AgentID   string       `json:"agent_id,omitempty"`
	Timestamp time.Time    `json:"timestamp"`
}

// Match represents a single detection engine match.
type Match struct {
	Engine     string  `json:"engine"`
	Pattern    string  `json:"pattern"`
	Confidence float64 `json:"confidence"`
}

// ScanResult represents the output from sentinel-core analysis.
type ScanResult struct {
	Detected   bool    `json:"detected"`
	RiskScore  float64 `json:"risk_score"`
	Matches    []Match `json:"matches"`
	EngineTime int64   `json:"engine_time_us"`
}

// Scanner interface for scanning tool call content.
// In production, this wraps sentinel-core via FFI or HTTP.
type Scanner interface {
	Scan(text string) (*ScanResult, error)
}

// PolicyChecker interface for DIP Oracle rule evaluation.
type PolicyChecker interface {
	Check(toolName string) (allowed bool, reason string)
}

// Handler processes hook events and returns decisions.
type Handler struct {
	scanner      Scanner
	policy       PolicyChecker
	learningMode bool // If true, log but never deny
}

// NewHandler creates a new hook handler.
func NewHandler(scanner Scanner, policy PolicyChecker, learningMode bool) *Handler {
	return &Handler{
		scanner:      scanner,
		policy:       policy,
		learningMode: learningMode,
	}
}

// ProcessEvent evaluates a hook event and returns a decision.
func (h *Handler) ProcessEvent(event *HookEvent) (*HookDecision, error) {
	if event == nil {
		return nil, fmt.Errorf("nil event")
	}

	// 1. Check DIP Oracle policy for the tool
	if event.ToolName != "" && h.policy != nil {
		allowed, reason := h.policy.Check(event.ToolName)
		if !allowed {
			decision := &HookDecision{
				Decision:  DecisionDeny,
				Reason:    reason,
				Severity:  "HIGH",
				Timestamp: time.Now(),
			}
			if h.learningMode {
				decision.Decision = DecisionAllow
				decision.Reason = fmt.Sprintf("[LEARNING MODE] would deny: %s", reason)
			}
			return decision, nil
		}
	}

	// 2. Extract content to scan
	content := h.extractContent(event)
	if content == "" {
		return &HookDecision{
			Decision:  DecisionAllow,
			Reason:    "no content to scan",
			Timestamp: time.Now(),
		}, nil
	}

	// 3. Run sentinel-core scan
	if h.scanner != nil {
		result, err := h.scanner.Scan(content)
		if err != nil {
			// On scan error, fail-open in learning mode, fail-closed otherwise
			if h.learningMode {
				return &HookDecision{
					Decision:  DecisionAllow,
					Reason:    fmt.Sprintf("[LEARNING MODE] scan error: %v", err),
					Timestamp: time.Now(),
				}, nil
			}
			return nil, fmt.Errorf("scan error: %w", err)
		}

		if result.Detected {
			severity := "MEDIUM"
			if result.RiskScore >= 0.9 {
				severity = "CRITICAL"
			} else if result.RiskScore >= 0.7 {
				severity = "HIGH"
			}

			decision := &HookDecision{
				Decision:  DecisionDeny,
				Reason:    "injection_detected",
				Severity:  severity,
				Matches:   result.Matches,
				Timestamp: time.Now(),
			}

			if h.learningMode {
				decision.Decision = DecisionAllow
				decision.Reason = fmt.Sprintf("[LEARNING MODE] would deny: injection_detected (score=%.2f)", result.RiskScore)
			}
			return decision, nil
		}
	}

	return &HookDecision{
		Decision:  DecisionAllow,
		Reason:    "clean",
		Timestamp: time.Now(),
	}, nil
}

// extractContent pulls the scannable text from a hook event.
func (h *Handler) extractContent(event *HookEvent) string {
	if event.Content != "" {
		return event.Content
	}
	if len(event.ToolInput) > 0 {
		return string(event.ToolInput)
	}
	return ""
}
