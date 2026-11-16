// Package antitamper implements SEC-005 Anti-Tamper Protection.
//
// Provides runtime protection against:
//   - ptrace/debugger attachment to SOC processes
//   - memory dump (process_vm_readv)
//   - binary modification detection via SHA-256 integrity checks
//   - environment variable tampering
//
// On Linux: uses prctl(PR_SET_DUMPABLE, 0) and self-ptrace detection.
// On Windows: uses IsDebuggerPresent() and NtQueryInformationProcess.
// Cross-platform: binary hash verification and env integrity checks.
package antitamper

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"io"
	"log/slog"
	"os"
	"sync"
	"time"
)

// TamperType classifies the tampering attempt.
type TamperType string

const (
	TamperDebugger    TamperType = "debugger_attached"
	TamperPtrace      TamperType = "ptrace_attempt"
	TamperBinaryMod   TamperType = "binary_modified"
	TamperEnvTamper   TamperType = "env_tampering"
	TamperMemoryDump  TamperType = "memory_dump"

	// CheckInterval for periodic integrity verification.
	DefaultCheckInterval = 5 * time.Minute
)

// TamperEvent records a detected tampering attempt.
type TamperEvent struct {
	Timestamp time.Time  `json:"timestamp"`
	Type      TamperType `json:"type"`
	Detail    string     `json:"detail"`
	Severity  string     `json:"severity"`
	PID       int        `json:"pid"`
	Binary    string     `json:"binary,omitempty"`
}

// TamperHandler is called when tampering is detected.
type TamperHandler func(event TamperEvent)

// Shield provides anti-tamper protection for SOC processes.
type Shield struct {
	mu             sync.RWMutex
	binaryPath     string
	binaryHash     string // SHA-256 at startup
	envSnapshot    map[string]string
	handlers       []TamperHandler
	logger         *slog.Logger
	stats          ShieldStats
}

// ShieldStats tracks anti-tamper metrics.
type ShieldStats struct {
	mu               sync.Mutex
	TotalChecks      int64 `json:"total_checks"`
	TamperDetected   int64 `json:"tamper_detected"`
	DebuggerBlocked  int64 `json:"debugger_blocked"`
	BinaryIntegrity  bool  `json:"binary_integrity"`
	LastCheck        time.Time `json:"last_check"`
	StartedAt        time.Time `json:"started_at"`
}

// NewShield creates a new anti-tamper shield.
// Takes a snapshot of the binary hash and critical env vars at startup.
func NewShield() (*Shield, error) {
	binaryPath, err := os.Executable()
	if err != nil {
		return nil, fmt.Errorf("antitamper: get executable: %w", err)
	}

	hash, err := hashFile(binaryPath)
	if err != nil {
		return nil, fmt.Errorf("antitamper: hash binary: %w", err)
	}

	// Snapshot critical environment variables.
	criticalEnvs := []string{
		"SOC_DB_PATH", "SOC_JWT_SECRET", "SOC_GUARD_POLICY",
		"GOMEMLIMIT", "SOC_AUDIT_DIR", "SOC_PORT",
	}
	envSnap := make(map[string]string)
	for _, key := range criticalEnvs {
		envSnap[key] = os.Getenv(key)
	}

	shield := &Shield{
		binaryPath:  binaryPath,
		binaryHash:  hash,
		envSnapshot: envSnap,
		logger:      slog.Default().With("component", "sec-005-antitamper"),
		stats: ShieldStats{
			BinaryIntegrity: true,
			StartedAt:       time.Now(),
		},
	}

	// Platform-specific initialization (disable core dumps, set non-dumpable).
	shield.platformInit()

	shield.logger.Info("anti-tamper shield initialized",
		"binary", binaryPath,
		"hash", hash[:16]+"...",
		"env_keys", len(envSnap),
	)

	return shield, nil
}

// OnTamper registers a handler for tampering events.
func (s *Shield) OnTamper(h TamperHandler) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.handlers = append(s.handlers, h)
}

// CheckBinaryIntegrity verifies the running binary hasn't been modified.
func (s *Shield) CheckBinaryIntegrity() *TamperEvent {
	s.stats.mu.Lock()
	s.stats.TotalChecks++
	s.stats.LastCheck = time.Now()
	s.stats.mu.Unlock()

	currentHash, err := hashFile(s.binaryPath)
	if err != nil {
		event := TamperEvent{
			Timestamp: time.Now(),
			Type:      TamperBinaryMod,
			Detail:    fmt.Sprintf("cannot read binary for hash check: %v", err),
			Severity:  "HIGH",
			PID:       os.Getpid(),
			Binary:    s.binaryPath,
		}
		s.recordTamper(event)
		return &event
	}

	if currentHash != s.binaryHash {
		s.stats.mu.Lock()
		s.stats.BinaryIntegrity = false
		s.stats.mu.Unlock()

		event := TamperEvent{
			Timestamp: time.Now(),
			Type:      TamperBinaryMod,
			Detail: fmt.Sprintf("binary modified! expected=%s got=%s",
				truncHash(s.binaryHash), truncHash(currentHash)),
			Severity: "CRITICAL",
			PID:      os.Getpid(),
			Binary:   s.binaryPath,
		}
		s.recordTamper(event)
		return &event
	}

	return nil
}

// CheckEnvIntegrity verifies critical environment variables haven't changed.
func (s *Shield) CheckEnvIntegrity() *TamperEvent {
	s.stats.mu.Lock()
	s.stats.TotalChecks++
	s.stats.mu.Unlock()

	for key, originalValue := range s.envSnapshot {
		current := os.Getenv(key)
		if current != originalValue {
			event := TamperEvent{
				Timestamp: time.Now(),
				Type:      TamperEnvTamper,
				Detail: fmt.Sprintf("env %s changed: original=%q current=%q",
					key, originalValue, current),
				Severity: "HIGH",
				PID:      os.Getpid(),
			}
			s.recordTamper(event)
			return &event
		}
	}
	return nil
}

// CheckDebugger checks if a debugger is attached.
// Platform-specific implementation in antitamper_*.go.
func (s *Shield) CheckDebugger() *TamperEvent {
	s.stats.mu.Lock()
	s.stats.TotalChecks++
	s.stats.mu.Unlock()

	if s.isDebuggerAttached() {
		s.stats.mu.Lock()
		s.stats.DebuggerBlocked++
		s.stats.mu.Unlock()

		event := TamperEvent{
			Timestamp: time.Now(),
			Type:      TamperDebugger,
			Detail:    "debugger detected attached to SOC process",
			Severity:  "CRITICAL",
			PID:       os.Getpid(),
			Binary:    s.binaryPath,
		}
		s.recordTamper(event)
		return &event
	}
	return nil
}

// RunAllChecks performs all anti-tamper checks at once.
func (s *Shield) RunAllChecks() []TamperEvent {
	var events []TamperEvent

	if e := s.CheckDebugger(); e != nil {
		events = append(events, *e)
	}
	if e := s.CheckBinaryIntegrity(); e != nil {
		events = append(events, *e)
	}
	if e := s.CheckEnvIntegrity(); e != nil {
		events = append(events, *e)
	}

	return events
}

// BinaryHash returns the expected binary hash (taken at startup).
func (s *Shield) BinaryHash() string {
	return s.binaryHash
}

// Stats returns current shield metrics.
func (s *Shield) Stats() ShieldStats {
	s.stats.mu.Lock()
	defer s.stats.mu.Unlock()
	return ShieldStats{
		TotalChecks:     s.stats.TotalChecks,
		TamperDetected:  s.stats.TamperDetected,
		DebuggerBlocked: s.stats.DebuggerBlocked,
		BinaryIntegrity: s.stats.BinaryIntegrity,
		LastCheck:       s.stats.LastCheck,
		StartedAt:       s.stats.StartedAt,
	}
}

// recordTamper updates stats and notifies handlers.
func (s *Shield) recordTamper(event TamperEvent) {
	s.stats.mu.Lock()
	s.stats.TamperDetected++
	s.stats.mu.Unlock()

	s.logger.Error("TAMPER DETECTED",
		"type", event.Type,
		"detail", event.Detail,
		"severity", event.Severity,
		"pid", event.PID,
	)

	s.mu.RLock()
	handlers := s.handlers
	s.mu.RUnlock()

	for _, h := range handlers {
		h(event)
	}
}

// --- Helpers ---

func hashFile(path string) (string, error) {
	f, err := os.Open(path)
	if err != nil {
		return "", err
	}
	defer f.Close()

	h := sha256.New()
	if _, err := io.Copy(h, f); err != nil {
		return "", err
	}

	return hex.EncodeToString(h.Sum(nil)), nil
}

func truncHash(h string) string {
	if len(h) > 16 {
		return h[:16]
	}
	return h
}
