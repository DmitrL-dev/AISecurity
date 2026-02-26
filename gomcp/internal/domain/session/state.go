// Package session defines domain entities for cognitive state persistence.
package session

import (
	"context"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"strings"
	"time"
)

// HypothesisStatus represents the lifecycle state of a hypothesis.
type HypothesisStatus string

const (
	HypothesisProposed  HypothesisStatus = "PROPOSED"
	HypothesisTesting   HypothesisStatus = "TESTING"
	HypothesisConfirmed HypothesisStatus = "CONFIRMED"
	HypothesisRejected  HypothesisStatus = "REJECTED"
)

// IsValid checks if the status is a known value.
func (s HypothesisStatus) IsValid() bool {
	switch s {
	case HypothesisProposed, HypothesisTesting, HypothesisConfirmed, HypothesisRejected:
		return true
	}
	return false
}

// Goal represents the primary objective of a session.
type Goal struct {
	ID          string  `json:"id"`
	Description string  `json:"description"`
	Progress    float64 `json:"progress"` // 0.0-1.0
}

// Validate checks goal fields.
func (g *Goal) Validate() error {
	if g.Description == "" {
		return fmt.Errorf("goal description is required")
	}
	if g.Progress < 0.0 || g.Progress > 1.0 {
		return fmt.Errorf("goal progress must be between 0.0 and 1.0, got %f", g.Progress)
	}
	return nil
}

// Hypothesis represents a testable hypothesis.
type Hypothesis struct {
	ID        string           `json:"id"`
	Statement string           `json:"statement"`
	Status    HypothesisStatus `json:"status"`
}

// Decision represents a recorded decision with rationale.
type Decision struct {
	ID           string    `json:"id"`
	Description  string    `json:"description"`
	Rationale    string    `json:"rationale"`
	Alternatives []string  `json:"alternatives,omitempty"`
	Timestamp    time.Time `json:"timestamp"`
}

// SessionFact represents a fact within a session's cognitive state.
type SessionFact struct {
	ID         string  `json:"id"`
	Content    string  `json:"content"`
	EntityType string  `json:"entity_type"`
	Confidence float64 `json:"confidence"`
	ValidAt    string  `json:"valid_at,omitempty"`
}

// CognitiveStateVector represents the full cognitive state of a session.
type CognitiveStateVector struct {
	SessionID     string             `json:"session_id"`
	Version       int                `json:"version"`
	Timestamp     time.Time          `json:"timestamp"`
	PrimaryGoal   *Goal              `json:"primary_goal,omitempty"`
	Hypotheses    []Hypothesis       `json:"hypotheses"`
	Decisions     []Decision         `json:"decisions"`
	Facts         []SessionFact      `json:"facts"`
	OpenQuestions []string           `json:"open_questions"`
	ConfidenceMap map[string]float64 `json:"confidence_map"`
}

// NewCognitiveStateVector creates a new empty state vector.
func NewCognitiveStateVector(sessionID string) *CognitiveStateVector {
	return &CognitiveStateVector{
		SessionID:     sessionID,
		Version:       1,
		Timestamp:     time.Now(),
		Hypotheses:    []Hypothesis{},
		Decisions:     []Decision{},
		Facts:         []SessionFact{},
		OpenQuestions: []string{},
		ConfidenceMap: make(map[string]float64),
	}
}

// SetGoal sets or replaces the primary goal. Progress is clamped to [0, 1].
func (csv *CognitiveStateVector) SetGoal(description string, progress float64) {
	if progress < 0 {
		progress = 0
	}
	if progress > 1 {
		progress = 1
	}
	csv.PrimaryGoal = &Goal{
		ID:          generateID(),
		Description: description,
		Progress:    progress,
	}
}

// AddHypothesis adds a new hypothesis in PROPOSED status.
func (csv *CognitiveStateVector) AddHypothesis(statement string) *Hypothesis {
	h := Hypothesis{
		ID:        generateID(),
		Statement: statement,
		Status:    HypothesisProposed,
	}
	csv.Hypotheses = append(csv.Hypotheses, h)
	return &csv.Hypotheses[len(csv.Hypotheses)-1]
}

// AddDecision records a decision with rationale and alternatives.
func (csv *CognitiveStateVector) AddDecision(description, rationale string, alternatives []string) *Decision {
	d := Decision{
		ID:           generateID(),
		Description:  description,
		Rationale:    rationale,
		Alternatives: alternatives,
		Timestamp:    time.Now(),
	}
	csv.Decisions = append(csv.Decisions, d)
	return &csv.Decisions[len(csv.Decisions)-1]
}

// AddFact adds a fact to the session state.
func (csv *CognitiveStateVector) AddFact(content, entityType string, confidence float64) *SessionFact {
	f := SessionFact{
		ID:         generateID(),
		Content:    content,
		EntityType: entityType,
		Confidence: confidence,
		ValidAt:    time.Now().UTC().Format(time.RFC3339),
	}
	csv.Facts = append(csv.Facts, f)
	return &csv.Facts[len(csv.Facts)-1]
}

// BumpVersion increments the version counter.
func (csv *CognitiveStateVector) BumpVersion() {
	csv.Version++
	csv.Timestamp = time.Now()
}

// Checksum computes a SHA-256 hex digest of the serialized state.
func (csv *CognitiveStateVector) Checksum() string {
	data, _ := json.Marshal(csv)
	h := sha256.Sum256(data)
	return hex.EncodeToString(h[:])
}

// ToCompactString renders the state as a compact text block for prompt injection.
// maxTokens controls approximate truncation (1 token ≈ 4 chars).
func (csv *CognitiveStateVector) ToCompactString(maxTokens int) string {
	maxChars := maxTokens * 4
	var sb strings.Builder

	if csv.PrimaryGoal != nil {
		fmt.Fprintf(&sb, "GOAL: %s (%.0f%%)\n", csv.PrimaryGoal.Description, csv.PrimaryGoal.Progress*100)
	}

	if len(csv.Hypotheses) > 0 {
		sb.WriteString("HYPOTHESES:\n")
		for _, h := range csv.Hypotheses {
			fmt.Fprintf(&sb, "  - [%s] %s\n", strings.ToLower(string(h.Status)), h.Statement)
			if sb.Len() > maxChars {
				break
			}
		}
	}

	if len(csv.Facts) > 0 {
		sb.WriteString("FACTS:\n")
		for _, f := range csv.Facts {
			fmt.Fprintf(&sb, "  - [%s] %s\n", f.EntityType, f.Content)
			if sb.Len() > maxChars {
				break
			}
		}
	}

	if len(csv.Decisions) > 0 {
		sb.WriteString("DECISIONS:\n")
		for _, d := range csv.Decisions {
			fmt.Fprintf(&sb, "  - %s\n", d.Description)
			if sb.Len() > maxChars {
				break
			}
		}
	}

	if len(csv.OpenQuestions) > 0 {
		sb.WriteString("OPEN QUESTIONS:\n")
		for _, q := range csv.OpenQuestions {
			fmt.Fprintf(&sb, "  - %s\n", q)
			if sb.Len() > maxChars {
				break
			}
		}
	}

	result := sb.String()
	if len(result) > maxChars {
		result = result[:maxChars]
	}
	return result
}

// SessionInfo holds metadata about a persisted session.
type SessionInfo struct {
	SessionID string    `json:"session_id"`
	Version   int       `json:"version"`
	UpdatedAt time.Time `json:"updated_at"`
}

// AuditEntry records a state change operation.
type AuditEntry struct {
	SessionID string `json:"session_id"`
	Action    string `json:"action"`
	Version   int    `json:"version"`
	Timestamp string `json:"timestamp"`
	Details   string `json:"details"`
}

// StateStore defines the interface for session state persistence.
type StateStore interface {
	Save(ctx context.Context, state *CognitiveStateVector, checksum string) error
	Load(ctx context.Context, sessionID string, version *int) (*CognitiveStateVector, string, error)
	ListSessions(ctx context.Context) ([]SessionInfo, error)
	DeleteSession(ctx context.Context, sessionID string) (int, error)
	GetAuditLog(ctx context.Context, sessionID string, limit int) ([]AuditEntry, error)
}

func generateID() string {
	b := make([]byte, 16)
	_, _ = rand.Read(b)
	return hex.EncodeToString(b)
}
