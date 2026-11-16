// Package soc defines domain entities for the SENTINEL AI SOC subsystem.
// SOC extends gomcp's alert/oracle layer with multi-source event ingestion,
// incident management, sensor lifecycle, and compliance reporting.
package soc

import (
	"crypto/sha256"
	"fmt"
	"time"
)

// EventSeverity represents SOC-specific severity levels (extended from alert.Severity).
type EventSeverity string

const (
	SeverityInfo     EventSeverity = "INFO"
	SeverityLow      EventSeverity = "LOW"
	SeverityMedium   EventSeverity = "MEDIUM"
	SeverityHigh     EventSeverity = "HIGH"
	SeverityCritical EventSeverity = "CRITICAL"
)

// SeverityRank returns numeric rank for comparison (higher = more severe).
func (s EventSeverity) Rank() int {
	switch s {
	case SeverityCritical:
		return 5
	case SeverityHigh:
		return 4
	case SeverityMedium:
		return 3
	case SeverityLow:
		return 2
	case SeverityInfo:
		return 1
	default:
		return 0
	}
}

// Verdict represents a SOC decision outcome.
type Verdict string

const (
	VerdictAllow    Verdict = "ALLOW"
	VerdictDeny     Verdict = "DENY"
	VerdictReview   Verdict = "REVIEW"
	VerdictEscalate Verdict = "ESCALATE"
)

// EventSource identifies the sensor or subsystem that generated the event.
type EventSource string

const (
	SourceSentinelCore EventSource = "sentinel-core"
	SourceShield       EventSource = "shield"
	SourceImmune       EventSource = "immune"
	SourceMicroSwarm   EventSource = "micro-swarm"
	SourceGoMCP        EventSource = "gomcp"
	SourceShadowAI     EventSource = "shadow-ai"
	SourceExternal     EventSource = "external"
)

// SOCEvent represents a security event ingested into the AI SOC Event Bus.
// This is the core entity flowing through the pipeline:
// Sensor → Secret Scanner (Step 0) → DIP → Decision Logger → Queue → Correlation.
type SOCEvent struct {
	ID           string            `json:"id"`
	TenantID     string            `json:"tenant_id,omitempty"`
	Source       EventSource       `json:"source"`
	SensorID     string            `json:"sensor_id"`
	SensorKey    string            `json:"-"` // §17.3 T-01: pre-shared key (never serialized)
	Severity     EventSeverity     `json:"severity"`
	Category     string            `json:"category"`    // e.g., "jailbreak", "injection", "exfiltration"
	Subcategory  string            `json:"subcategory"` // e.g., "sql_injection", "tool_abuse"
	Confidence   float64           `json:"confidence"`  // 0.0 - 1.0
	Description  string            `json:"description"`
	Payload      string            `json:"payload,omitempty"` // Raw input for Secret Scanner Step 0
	SessionID    string            `json:"session_id,omitempty"`
	ContentHash  string            `json:"content_hash,omitempty"` // SHA-256 dedup key (§5.2)
	DecisionHash string            `json:"decision_hash,omitempty"` // SHA-256 chain link
	Verdict      Verdict           `json:"verdict"`
	ZeroGMode    bool              `json:"zero_g_mode,omitempty"` // §13.4: Strike Force operation tag
	Timestamp    time.Time         `json:"timestamp"`
	Metadata     map[string]string `json:"metadata,omitempty"` // Extensible key-value pairs
}

// ComputeContentHash generates a SHA-256 hash from tenant+sensor+source+category+description+payload
// for content-based deduplication (§5.2 step 2).
func (e *SOCEvent) ComputeContentHash() string {
	h := sha256.New()
	fmt.Fprintf(h, "%s|%s|%s|%s|%s|%s", e.TenantID, e.SensorID, e.Source, e.Category, e.Description, e.Payload)
	e.ContentHash = fmt.Sprintf("%x", h.Sum(nil))
	return e.ContentHash
}

// KnownCategories is the set of recognized event categories.
// Events with unknown categories are still accepted but logged as warnings.
var KnownCategories = map[string]bool{
	"jailbreak":        true,
	"prompt_injection":  true,
	"tool_abuse":       true,
	"exfiltration":     true,
	"pii_leak":         true,
	"auth_bypass":      true,
	"encoding":         true,
	"persistence":      true,
	"sensor_anomaly":   true,
	"dos":              true,
	"model_theft":      true,
	"supply_chain":     true,
	"data_poisoning":   true,
	"evasion":          true,
	"shadow_ai_usage":  true,
	"integration_health": true,
	"other":            true,
	// GenAI EDR categories (SDD-001)
	"genai_child_process":       true,
	"genai_sensitive_file_access": true,
	"genai_unusual_domain":      true,
	"genai_credential_access":   true,
	"genai_persistence":         true,
	"genai_config_modification": true,
}

// ValidSeverity returns true if the severity is a known value.
func ValidSeverity(s EventSeverity) bool {
	switch s {
	case SeverityInfo, SeverityLow, SeverityMedium, SeverityHigh, SeverityCritical:
		return true
	}
	return false
}

// ValidSource returns true if the source is a known value.
func ValidSource(s EventSource) bool {
	switch s {
	case SourceSentinelCore, SourceShield, SourceImmune, SourceMicroSwarm, SourceGoMCP, SourceShadowAI, SourceExternal:
		return true
	}
	return false
}

// Validate checks all required fields and enum values.
// Returns nil if valid, or a *ValidationErrors with field-level details.
func (e SOCEvent) Validate() error {
	ve := &ValidationErrors{}

	if e.Source == "" {
		ve.Add("source", "source is required")
	} else if !ValidSource(e.Source) {
		ve.Add("source", fmt.Sprintf("unknown source: %q (valid: sentinel-core, shield, immune, micro-swarm, gomcp, external)", e.Source))
	}

	if e.Severity == "" {
		ve.Add("severity", "severity is required")
	} else if !ValidSeverity(e.Severity) {
		ve.Add("severity", fmt.Sprintf("unknown severity: %q (valid: INFO, LOW, MEDIUM, HIGH, CRITICAL)", e.Severity))
	}

	if e.Category == "" {
		ve.Add("category", "category is required")
	}

	if e.Description == "" {
		ve.Add("description", "description is required")
	}

	if e.Confidence < 0 || e.Confidence > 1 {
		ve.Add("confidence", "confidence must be between 0.0 and 1.0")
	}

	// Bound SensorID (Review 14.06 round-5): it is an attacker-controlled string
	// used as a rate-limit key AND a map key (s.sensors / s.sensorRates) AND a
	// persisted column. Without a bound, a flood of unique SensorIDs grows those
	// maps + SQLite rows without limit (memory/disk DoS). Restrict to a
	// conservative id charset and length; empty is allowed (falls back to Source).
	if e.SensorID != "" {
		if len(e.SensorID) > MaxSensorIDLen {
			ve.Add("sensor_id", fmt.Sprintf("sensor_id too long (max %d)", MaxSensorIDLen))
		} else if !validSensorID(e.SensorID) {
			ve.Add("sensor_id", "sensor_id has invalid characters (allowed: A-Z a-z 0-9 . _ : -)")
		}
	}

	// Bound the free-text fields (pre-launch audit 18.06): only the 1 MiB body cap
	// otherwise limits them, so a single event could bloat storage + dashboards/
	// exports. Caps are generous — they reject abuse, not legitimate events.
	if len(e.Description) > MaxDescriptionLen {
		ve.Add("description", fmt.Sprintf("description too long (max %d bytes)", MaxDescriptionLen))
	}
	if len(e.Payload) > MaxPayloadLen {
		ve.Add("payload", fmt.Sprintf("payload too long (max %d bytes)", MaxPayloadLen))
	}
	if len(e.Category) > MaxFieldLen {
		ve.Add("category", fmt.Sprintf("category too long (max %d bytes)", MaxFieldLen))
	}
	if len(e.Subcategory) > MaxFieldLen {
		ve.Add("subcategory", fmt.Sprintf("subcategory too long (max %d bytes)", MaxFieldLen))
	}
	if len(e.Metadata) > MaxMetadataPairs {
		ve.Add("metadata", fmt.Sprintf("too many metadata keys (max %d)", MaxMetadataPairs))
	} else {
		for k, v := range e.Metadata {
			if len(k) > MaxFieldLen || len(v) > MaxMetadataValueLen {
				ve.Add("metadata", "metadata key/value too long")
				break
			}
		}
	}

	if ve.HasErrors() {
		return ve
	}
	return nil
}

// MaxSensorIDLen bounds an auto-discovered sensor identifier.
const MaxSensorIDLen = 128

// Per-field caps on ingested SOC events (pre-launch audit 18.06) — generous
// bounds that reject abuse without affecting legitimate events.
const (
	MaxDescriptionLen   = 8 * 1024  // 8 KiB
	MaxPayloadLen       = 64 * 1024 // 64 KiB
	MaxFieldLen         = 256       // category / subcategory / metadata key
	MaxMetadataPairs    = 64
	MaxMetadataValueLen = 4 * 1024 // 4 KiB
)

// validSensorID allows only a conservative identifier charset — enough for
// hostnames and the "gateway:<tenant>" form, but not arbitrary attacker text.
func validSensorID(s string) bool {
	for _, r := range s {
		switch {
		case r >= 'a' && r <= 'z', r >= 'A' && r <= 'Z', r >= '0' && r <= '9':
		case r == '.' || r == '_' || r == ':' || r == '-':
		default:
			return false
		}
	}
	return true
}

// NewSOCEvent creates a new SOC event with auto-generated ID.
func NewSOCEvent(source EventSource, severity EventSeverity, category, description string) SOCEvent {
	return SOCEvent{
		ID:          genID("evt"),
		Source:      source,
		Severity:    severity,
		Category:    category,
		Description: description,
		Verdict:     VerdictReview, // Default: needs review
		Timestamp:   time.Now(),
	}
}

// WithSensor sets the sensor ID.
func (e SOCEvent) WithSensor(sensorID string) SOCEvent {
	e.SensorID = sensorID
	return e
}

// WithConfidence sets the confidence score.
func (e SOCEvent) WithConfidence(c float64) SOCEvent {
	if c < 0 {
		c = 0
	}
	if c > 1 {
		c = 1
	}
	e.Confidence = c
	return e
}

// WithVerdict sets the verdict.
func (e SOCEvent) WithVerdict(v Verdict) SOCEvent {
	e.Verdict = v
	return e
}

// IsCritical returns true if severity is HIGH or CRITICAL.
func (e SOCEvent) IsCritical() bool {
	return e.Severity == SeverityHigh || e.Severity == SeverityCritical
}

