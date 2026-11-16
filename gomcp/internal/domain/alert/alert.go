// Package alert defines the Alert domain entity and severity levels
// for the DIP-Watcher proactive monitoring system.
package alert

import (
	"fmt"
	"time"
)

// Severity represents the urgency level of an alert.
type Severity int

const (
	// SeverityInfo is for routine status updates.
	SeverityInfo Severity = iota
	// SeverityWarning indicates a potential issue requiring attention.
	SeverityWarning
	// SeverityCritical indicates an active threat or system instability.
	SeverityCritical
)

// String returns human-readable severity.
func (s Severity) String() string {
	switch s {
	case SeverityInfo:
		return "INFO"
	case SeverityWarning:
		return "WARNING"
	case SeverityCritical:
		return "CRITICAL"
	default:
		return "UNKNOWN"
	}
}

// Icon returns the emoji indicator for the severity.
func (s Severity) Icon() string {
	switch s {
	case SeverityInfo:
		return "🟢"
	case SeverityWarning:
		return "⚠️"
	case SeverityCritical:
		return "🔴"
	default:
		return "❓"
	}
}

// Source identifies the subsystem that generated the alert.
type Source string

const (
	SourceWatcher Source = "dip-watcher"
	SourceGenome  Source = "genome"
	SourceEntropy Source = "entropy"
	SourceMemory  Source = "memory"
	SourceOracle  Source = "oracle"
	SourcePeer    Source = "peer"
	SourceSystem  Source = "system"
)

// Alert represents a single monitoring event from the DIP-Watcher.
type Alert struct {
	ID        string    `json:"id"`
	Source    Source    `json:"source"`
	Severity  Severity  `json:"severity"`
	Message   string    `json:"message"`
	Cycle     int       `json:"cycle"` // Heartbeat cycle that generated this alert
	Value     float64   `json:"value"` // Numeric value (entropy, count, etc.)
	Timestamp time.Time `json:"timestamp"`
	Resolved  bool      `json:"resolved"`
}

// New creates a new Alert with auto-generated ID.
func New(source Source, severity Severity, message string, cycle int) Alert {
	return Alert{
		ID:        fmt.Sprintf("alert-%d-%s", time.Now().UnixMicro(), source),
		Source:    source,
		Severity:  severity,
		Message:   message,
		Cycle:     cycle,
		Timestamp: time.Now(),
	}
}

// WithValue sets a numeric value on the alert (for entropy levels, counts, etc.).
func (a Alert) WithValue(v float64) Alert {
	a.Value = v
	return a
}
