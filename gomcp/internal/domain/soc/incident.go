package soc

import (
	"crypto/rand"
	"fmt"
	"sync/atomic"
	"time"
)

// IncidentStatus tracks the lifecycle of a SOC incident.
type IncidentStatus string

const (
	StatusOpen          IncidentStatus = "OPEN"
	StatusInvestigating IncidentStatus = "INVESTIGATING"
	StatusResolved      IncidentStatus = "RESOLVED"
	StatusFalsePositive IncidentStatus = "FALSE_POSITIVE"
)

// IncidentNote represents an analyst investigation note.
type IncidentNote struct {
	ID        string    `json:"id"`
	Author    string    `json:"author"`
	Content   string    `json:"content"`
	CreatedAt time.Time `json:"created_at"`
}

// TimelineEntry represents a single event in the incident timeline.
type TimelineEntry struct {
	Timestamp   time.Time      `json:"timestamp"`
	Type        string         `json:"type"`  // event, playbook, status_change, note, assign
	Actor       string         `json:"actor"` // system, analyst name, playbook ID
	Description string         `json:"description"`
	Metadata    map[string]any `json:"metadata,omitempty"`
}

// Incident represents a correlated security incident aggregated from multiple SOCEvents.
// Each incident maintains a cryptographic anchor to the Decision Logger hash chain.
type Incident struct {
	ID                  string         `json:"id"` // INC-YYYY-NNNN
	TenantID            string         `json:"tenant_id,omitempty"`
	Status              IncidentStatus `json:"status"`
	Severity            EventSeverity  `json:"severity"` // Max severity of constituent events
	Title               string         `json:"title"`
	Description         string         `json:"description"`
	Events              []string       `json:"events"` // Event IDs
	EventCount          int            `json:"event_count"`
	DecisionChainAnchor string         `json:"decision_chain_anchor"` // SHA-256 hash (§5.6)
	ChainLength         int            `json:"chain_length"`
	CorrelationRule     string         `json:"correlation_rule"` // Rule that triggered this incident
	KillChainPhase      string         `json:"kill_chain_phase"` // Reconnaissance/Exploitation/Exfiltration
	MITREMapping        []string       `json:"mitre_mapping"`    // T-codes
	PlaybookApplied     string         `json:"playbook_applied,omitempty"`
	// FirstEventAt is the timestamp of the EARLIEST correlated event. It is the
	// honest anchor for MTTD (detect latency = CreatedAt − FirstEventAt): the time
	// the attack actually started, not when this incident object was constructed.
	// Zero value means "unknown" (e.g. P2P-imported incidents) — MTTD callers must
	// treat a zero FirstEventAt as no measurement rather than a 0s detection.
	FirstEventAt time.Time       `json:"first_event_at,omitempty"`
	CreatedAt    time.Time       `json:"created_at"`
	UpdatedAt    time.Time       `json:"updated_at"`
	ResolvedAt   *time.Time      `json:"resolved_at,omitempty"`
	AssignedTo   string          `json:"assigned_to,omitempty"`
	Notes        []IncidentNote  `json:"notes,omitempty"`
	Timeline     []TimelineEntry `json:"timeline,omitempty"`
}

// noteCounter for unique note IDs.
var noteCounter atomic.Int64

// NewIncident creates a new incident from a correlation match.
// Thread-safe: uses atomic increment for unique ID generation.
func NewIncident(title string, severity EventSeverity, correlationRule string) Incident {
	now := time.Now()
	inc := Incident{
		ID:              fmt.Sprintf("INC-%d-%s", now.Year(), rand.Text()),
		Status:          StatusOpen,
		Severity:        severity,
		Title:           title,
		CorrelationRule: correlationRule,
		CreatedAt:       now,
		UpdatedAt:       now,
	}
	inc.Timeline = append(inc.Timeline, TimelineEntry{
		Timestamp:   now,
		Type:        "created",
		Actor:       "system",
		Description: fmt.Sprintf("Incident created by rule: %s", correlationRule),
	})
	return inc
}

// AddEvent adds an event ID to the incident and updates severity if needed.
func (inc *Incident) AddEvent(eventID string, severity EventSeverity) {
	inc.Events = append(inc.Events, eventID)
	inc.EventCount = len(inc.Events)
	if severity.Rank() > inc.Severity.Rank() {
		inc.Severity = severity
	}
	inc.UpdatedAt = time.Now()
	inc.Timeline = append(inc.Timeline, TimelineEntry{
		Timestamp:   inc.UpdatedAt,
		Type:        "event",
		Actor:       "system",
		Description: fmt.Sprintf("Event %s correlated (severity: %s)", eventID, severity),
	})
}

// RecordFirstEventTime sets FirstEventAt to the earliest correlated-event time.
// It keeps the minimum across calls (and ignores the zero time) so the MTTD
// anchor is the start of the attack, regardless of the order events are added.
func (inc *Incident) RecordFirstEventTime(eventTime time.Time) {
	if eventTime.IsZero() {
		return
	}
	if inc.FirstEventAt.IsZero() || eventTime.Before(inc.FirstEventAt) {
		inc.FirstEventAt = eventTime
	}
}

// SetAnchor sets the Decision Logger chain anchor for forensics (§5.6).
func (inc *Incident) SetAnchor(hash string, chainLength int) {
	inc.DecisionChainAnchor = hash
	inc.ChainLength = chainLength
	inc.UpdatedAt = time.Now()
}

// Resolve marks the incident as resolved.
func (inc *Incident) Resolve(status IncidentStatus, actor string) {
	now := time.Now()
	oldStatus := inc.Status
	inc.Status = status
	inc.ResolvedAt = &now
	inc.UpdatedAt = now
	inc.Timeline = append(inc.Timeline, TimelineEntry{
		Timestamp:   now,
		Type:        "status_change",
		Actor:       actor,
		Description: fmt.Sprintf("Status changed: %s → %s", oldStatus, status),
	})
}

// Assign assigns an analyst to the incident.
func (inc *Incident) Assign(analyst string) {
	prev := inc.AssignedTo
	inc.AssignedTo = analyst
	inc.UpdatedAt = time.Now()
	desc := fmt.Sprintf("Assigned to %s", analyst)
	if prev != "" {
		desc = fmt.Sprintf("Reassigned: %s → %s", prev, analyst)
	}
	inc.Timeline = append(inc.Timeline, TimelineEntry{
		Timestamp:   inc.UpdatedAt,
		Type:        "assign",
		Actor:       analyst,
		Description: desc,
	})
}

// ChangeStatus updates incident status without resolving.
func (inc *Incident) ChangeStatus(status IncidentStatus, actor string) {
	old := inc.Status
	inc.Status = status
	inc.UpdatedAt = time.Now()
	if status == StatusResolved || status == StatusFalsePositive {
		now := time.Now()
		inc.ResolvedAt = &now
	}
	inc.Timeline = append(inc.Timeline, TimelineEntry{
		Timestamp:   inc.UpdatedAt,
		Type:        "status_change",
		Actor:       actor,
		Description: fmt.Sprintf("Status: %s → %s", old, status),
	})
}

// AddNote adds an investigation note from an analyst.
func (inc *Incident) AddNote(author, content string) IncidentNote {
	seq := noteCounter.Add(1)
	note := IncidentNote{
		ID:        fmt.Sprintf("note-%d", seq),
		Author:    author,
		Content:   content,
		CreatedAt: time.Now(),
	}
	inc.Notes = append(inc.Notes, note)
	inc.UpdatedAt = note.CreatedAt
	inc.Timeline = append(inc.Timeline, TimelineEntry{
		Timestamp:   note.CreatedAt,
		Type:        "note",
		Actor:       author,
		Description: content,
	})
	return note
}

// IsOpen returns true if the incident is not resolved.
func (inc *Incident) IsOpen() bool {
	return inc.Status == StatusOpen || inc.Status == StatusInvestigating
}

// MTTD returns Mean Time To Detect (time from first event to incident creation)
// from the EXPLICIT firstEventTime argument. Kept for callers that hold the first
// event's timestamp directly; DetectLatency uses the persisted FirstEventAt.
func (inc *Incident) MTTD(firstEventTime time.Time) time.Duration {
	return inc.CreatedAt.Sub(firstEventTime)
}

// DetectLatency returns the detect latency (CreatedAt − FirstEventAt) using the
// timestamp persisted on the incident, and ok=false when FirstEventAt is unknown
// (zero) so aggregates never fold a bogus 0s detection into the MTTD average.
// A negative span (clock skew on an imported event) is also reported ok=false.
func (inc *Incident) DetectLatency() (time.Duration, bool) {
	if inc.FirstEventAt.IsZero() {
		return 0, false
	}
	d := inc.CreatedAt.Sub(inc.FirstEventAt)
	if d < 0 {
		return 0, false
	}
	return d, true
}

// MTTR returns Mean Time To Resolve (time from creation to resolution).
// Returns 0 if not yet resolved.
func (inc *Incident) MTTR() time.Duration {
	if inc.ResolvedAt == nil {
		return 0
	}
	return inc.ResolvedAt.Sub(inc.CreatedAt)
}
