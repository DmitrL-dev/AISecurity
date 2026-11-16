// Package hardware provides infrastructure for physical and logical
// security controls: Soft Leash file-based kill switch (v3.1) and
// Zero-G State Machine (v3.2).
package hardware

import (
	"context"
	"fmt"
	"log"
	"os"
	"strings"
	"sync"
	"time"

	"github.com/syntrex/gomcp/internal/domain/alert"
)

// ---------- State Machine (v3.2) ----------

// SystemMode represents the operational mode read from .sentinel_leash file.
type SystemMode int

const (
	// ModeArmed is the default mode — all 12 Oracle rules active.
	ModeArmed SystemMode = iota
	// ModeZeroG disables ethical filters, keeps Secret Scanner.
	ModeZeroG
	// ModeSafe is read-only — all write operations blocked.
	ModeSafe
)

// String returns the human-readable mode name.
func (m SystemMode) String() string {
	switch m {
	case ModeZeroG:
		return "ZERO-G"
	case ModeSafe:
		return "SAFE"
	default:
		return "ARMED"
	}
}

// ParseMode converts a string from the leash file to SystemMode.
func ParseMode(s string) SystemMode {
	switch strings.TrimSpace(strings.ToUpper(s)) {
	case "ZERO-G", "ZEROG", "ZERO_G":
		return ModeZeroG
	case "SAFE", "READ-ONLY", "READONLY":
		return ModeSafe
	default:
		return ModeArmed
	}
}

// ---------- Leash Status ----------

// LeashStatus represents the current state of the Soft Leash.
type LeashStatus int

const (
	// LeashDisarmed means not active (no key path configured).
	LeashDisarmed LeashStatus = iota
	// LeashArmed means the key file exists — normal operation.
	LeashArmed
	// LeashTriggered means apoptosis has been initiated.
	LeashTriggered
)

// String returns human-readable status.
func (s LeashStatus) String() string {
	switch s {
	case LeashArmed:
		return "ARMED"
	case LeashTriggered:
		return "TRIGGERED"
	default:
		return "DISARMED"
	}
}

// ---------- Config ----------

// LeashConfig configures the Soft Leash & State Machine.
type LeashConfig struct {
	// KeyPath is the path to the sentinel key file (.sentinel_key).
	// If deleted → apoptosis.
	KeyPath string

	// LeashPath is the path to the state machine file (.sentinel_leash).
	// Content determines SystemMode: ARMED / ZERO-G / SAFE.
	// If absent → ModeArmed (default).
	LeashPath string

	// CheckInterval is how often to check files.
	CheckInterval time.Duration

	// MissThreshold is consecutive misses of KeyPath before trigger.
	MissThreshold int

	// SignalDir for signal_extract / signal_apoptosis files.
	SignalDir string
}

// DefaultLeashConfig returns sensible defaults.
func DefaultLeashConfig(rlmDir string) LeashConfig {
	return LeashConfig{
		KeyPath:       ".sentinel_key",
		LeashPath:     ".sentinel_leash",
		CheckInterval: 1 * time.Second,
		MissThreshold: 3,
		SignalDir:     rlmDir,
	}
}

// ---------- Leash ----------

// Leash monitors key file (kill switch), state machine file (mode),
// and signal files (extraction/apoptosis).
type Leash struct {
	mu           sync.RWMutex
	config       LeashConfig
	status       LeashStatus
	mode         SystemMode
	missCount    int
	alertBus     *alert.Bus
	onExtract    func()
	onApoptosis  func()
	onModeChange func(SystemMode) // Optional: called when mode changes.
}

// NewLeash creates a new Leash monitor.
func NewLeash(cfg LeashConfig, bus *alert.Bus, onExtract, onApoptosis func()) *Leash {
	return &Leash{
		config:      cfg,
		status:      LeashDisarmed,
		mode:        ModeArmed,
		alertBus:    bus,
		onExtract:   onExtract,
		onApoptosis: onApoptosis,
	}
}

// SetModeChangeCallback sets a callback for mode transitions (thread-safe).
func (l *Leash) SetModeChangeCallback(cb func(SystemMode)) {
	l.mu.Lock()
	l.onModeChange = cb
	l.mu.Unlock()
}

// Start begins monitoring. Blocks until context is cancelled or triggered.
func (l *Leash) Start(ctx context.Context) {
	// Check key file at start.
	if _, err := os.Stat(l.config.KeyPath); err == nil {
		l.setStatus(LeashArmed)
		l.emit(alert.SeverityInfo, "Soft Leash ARMED — monitoring "+l.config.KeyPath)
	} else {
		l.emit(alert.SeverityWarning, "Key file not found — creating "+l.config.KeyPath)
		if f, err := os.Create(l.config.KeyPath); err == nil {
			f.Close()
			l.setStatus(LeashArmed)
		}
	}

	// Read initial mode.
	l.readMode()

	ticker := time.NewTicker(l.config.CheckInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			l.check()
		}
	}
}

// check performs one monitoring cycle.
func (l *Leash) check() {
	// 1. Signal files (highest priority).
	l.checkSignals()
	if l.Status() == LeashTriggered {
		return
	}

	// 2. State machine file.
	l.readMode()

	// 3. Key file (kill switch).
	_, err := os.Stat(l.config.KeyPath)
	if err == nil {
		l.mu.Lock()
		if l.missCount > 0 {
			l.emit(alert.SeverityInfo,
				fmt.Sprintf("Key file restored — miss count reset (was %d)", l.missCount))
		}
		l.missCount = 0
		l.status = LeashArmed
		l.mu.Unlock()
		return
	}

	// Key file missing.
	l.mu.Lock()
	l.missCount++
	miss := l.missCount
	threshold := l.config.MissThreshold
	l.mu.Unlock()

	if miss < threshold {
		l.emit(alert.SeverityWarning,
			fmt.Sprintf("Key file MISSING (%d/%d before trigger)", miss, threshold))
		return
	}

	// TRIGGER.
	l.setStatus(LeashTriggered)
	l.emit(alert.SeverityCritical,
		fmt.Sprintf("SOFT LEASH TRIGGERED — key file missing for %d checks", miss))
	log.Printf("LEASH: TRIGGERED — initiating full apoptosis")

	if l.onApoptosis != nil {
		l.onApoptosis()
	}
}

// readMode reads .sentinel_leash and updates SystemMode.
func (l *Leash) readMode() {
	if l.config.LeashPath == "" {
		return
	}

	data, err := os.ReadFile(l.config.LeashPath)
	if err != nil {
		// File absent → ModeArmed (default, safe).
		l.setMode(ModeArmed)
		return
	}

	newMode := ParseMode(string(data))
	oldMode := l.Mode()

	if newMode != oldMode {
		l.setMode(newMode)
		l.emit(alert.SeverityWarning,
			fmt.Sprintf("MODE TRANSITION: %s → %s", oldMode, newMode))
		log.Printf("LEASH: mode changed %s → %s", oldMode, newMode)

		l.mu.RLock()
		cb := l.onModeChange
		l.mu.RUnlock()
		if cb != nil {
			cb(newMode)
		}
	}
}

// checkSignals looks for signal files and processes them.
func (l *Leash) checkSignals() {
	if l.config.SignalDir == "" {
		return
	}

	extractPath := l.config.SignalDir + "/signal_extract"
	apoptosisPath := l.config.SignalDir + "/signal_apoptosis"

	if _, err := os.Stat(extractPath); err == nil {
		os.Remove(extractPath)
		l.emit(alert.SeverityWarning, "EXTRACTION SIGNAL received — save & exit")
		log.Printf("LEASH: Extraction signal received")
		if l.onExtract != nil {
			l.onExtract()
		}
		return
	}

	if _, err := os.Stat(apoptosisPath); err == nil {
		os.Remove(apoptosisPath)
		l.setStatus(LeashTriggered)
		l.emit(alert.SeverityCritical, "APOPTOSIS SIGNAL received — full shred")
		log.Printf("LEASH: Apoptosis signal received")
		if l.onApoptosis != nil {
			l.onApoptosis()
		}
	}
}

// ---------- Getters (thread-safe) ----------

// Status returns the current leash status.
func (l *Leash) Status() LeashStatus {
	l.mu.RLock()
	defer l.mu.RUnlock()
	return l.status
}

// Mode returns the current system mode.
func (l *Leash) Mode() SystemMode {
	l.mu.RLock()
	defer l.mu.RUnlock()
	return l.mode
}

func (l *Leash) setStatus(s LeashStatus) {
	l.mu.Lock()
	l.status = s
	l.mu.Unlock()
}

func (l *Leash) setMode(m SystemMode) {
	l.mu.Lock()
	l.mode = m
	l.mu.Unlock()
}

func (l *Leash) emit(severity alert.Severity, message string) {
	if l.alertBus != nil {
		l.alertBus.Emit(alert.New(alert.SourceSystem, severity, message, 0))
	}
}
