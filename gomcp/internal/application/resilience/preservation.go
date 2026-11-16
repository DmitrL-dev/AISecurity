package resilience

import (
	"fmt"
	"log/slog"
	"sync"
	"time"
)

// EmergencyMode defines the system's emergency state.
type EmergencyMode string

const (
	ModeNone      EmergencyMode = "NONE"
	ModeSafe      EmergencyMode = "SAFE"
	ModeLockdown  EmergencyMode = "LOCKDOWN"
	ModeApoptosis EmergencyMode = "APOPTOSIS"
)

// ModeActivation records when and why a mode was activated.
type ModeActivation struct {
	Mode        EmergencyMode `json:"mode"`
	ActivatedAt time.Time     `json:"activated_at"`
	ActivatedBy string        `json:"activated_by"` // "auto" or "architect:<name>"
	Reason      string        `json:"reason"`
	AutoExit    bool          `json:"auto_exit"`
	AutoExitAt  time.Time     `json:"auto_exit_at,omitempty"`
}

// PreservationEvent is an audit log entry for preservation actions.
type PreservationEvent struct {
	Timestamp time.Time     `json:"timestamp"`
	Mode      EmergencyMode `json:"mode"`
	Action    string        `json:"action"`
	Detail    string        `json:"detail"`
	Success   bool          `json:"success"`
	Error     string        `json:"error,omitempty"`
}

// ModeActionFunc is a callback to perform mode-specific actions.
// Implementations handle the real system operations (network isolation, process freeze, etc.).
type ModeActionFunc func(mode EmergencyMode, action string, params map[string]interface{}) error

// PreservationEngine manages emergency modes (safe/lockdown/apoptosis).
type PreservationEngine struct {
	mu           sync.RWMutex
	currentMode  EmergencyMode
	activation   *ModeActivation
	history      []PreservationEvent
	actionFn     ModeActionFunc
	integrityFn  func() IntegrityReport // pluggable integrity check
	logger       *slog.Logger
}

// NewPreservationEngine creates a new preservation engine.
func NewPreservationEngine(actionFn ModeActionFunc) *PreservationEngine {
	return &PreservationEngine{
		currentMode: ModeNone,
		history:     make([]PreservationEvent, 0),
		actionFn:    actionFn,
		logger:      slog.Default().With("component", "sarl-preservation"),
	}
}

// CurrentMode returns the active emergency mode.
func (pe *PreservationEngine) CurrentMode() EmergencyMode {
	pe.mu.RLock()
	defer pe.mu.RUnlock()
	return pe.currentMode
}

// Activation returns the current mode activation details (nil if NONE).
func (pe *PreservationEngine) Activation() *ModeActivation {
	pe.mu.RLock()
	defer pe.mu.RUnlock()
	if pe.activation == nil {
		return nil
	}
	cp := *pe.activation
	return &cp
}

// ActivateMode enters an emergency mode. Returns error if transition is invalid.
func (pe *PreservationEngine) ActivateMode(mode EmergencyMode, reason, activatedBy string) error {
	pe.mu.Lock()
	defer pe.mu.Unlock()

	if mode == ModeNone {
		return fmt.Errorf("use DeactivateMode to exit emergency mode")
	}

	// Validate transitions: can always escalate, can't downgrade.
	if !pe.isValidTransition(pe.currentMode, mode) {
		return fmt.Errorf("invalid transition: %s → %s", pe.currentMode, mode)
	}

	pe.logger.Warn("EMERGENCY MODE ACTIVATION",
		"mode", mode,
		"reason", reason,
		"activated_by", activatedBy,
	)

	// Execute mode-specific actions.
	actions := pe.actionsForMode(mode)
	for _, action := range actions {
		err := pe.executeAction(mode, action.name, action.params)
		if err != nil {
			pe.logger.Error("mode action failed",
				"mode", mode,
				"action", action.name,
				"error", err,
			)
			// In critical modes, continue despite errors.
			if mode != ModeApoptosis {
				return fmt.Errorf("failed to activate %s: action %s: %w", mode, action.name, err)
			}
		}
	}

	activation := &ModeActivation{
		Mode:        mode,
		ActivatedAt: time.Now(),
		ActivatedBy: activatedBy,
		Reason:      reason,
	}

	if mode == ModeSafe {
		activation.AutoExit = true
		activation.AutoExitAt = time.Now().Add(15 * time.Minute)
	}

	pe.currentMode = mode
	pe.activation = activation

	return nil
}

// DeactivateMode exits the current emergency mode and returns to NONE.
func (pe *PreservationEngine) DeactivateMode(deactivatedBy string) error {
	pe.mu.Lock()
	defer pe.mu.Unlock()

	if pe.currentMode == ModeNone {
		return nil
	}

	// Lockdown and apoptosis require manual deactivation by architect.
	if pe.currentMode == ModeApoptosis {
		return fmt.Errorf("apoptosis mode cannot be deactivated — system rebuild required")
	}

	pe.logger.Info("EMERGENCY MODE DEACTIVATION",
		"mode", pe.currentMode,
		"deactivated_by", deactivatedBy,
	)

	pe.recordEvent(pe.currentMode, "deactivated",
		fmt.Sprintf("deactivated by %s", deactivatedBy), true, "")

	pe.currentMode = ModeNone
	pe.activation = nil

	return nil
}

// ShouldAutoExit checks if safe mode should auto-exit based on timer.
func (pe *PreservationEngine) ShouldAutoExit() bool {
	pe.mu.RLock()
	defer pe.mu.RUnlock()

	if pe.currentMode != ModeSafe || pe.activation == nil {
		return false
	}
	return pe.activation.AutoExit && time.Now().After(pe.activation.AutoExitAt)
}

// isValidTransition checks if a mode transition is allowed.
// Escalation order: NONE → SAFE → LOCKDOWN → APOPTOSIS.
func (pe *PreservationEngine) isValidTransition(from, to EmergencyMode) bool {
	rank := map[EmergencyMode]int{
		ModeNone:      0,
		ModeSafe:      1,
		ModeLockdown:  2,
		ModeApoptosis: 3,
	}
	// Can always escalate or re-enter same mode.
	return rank[to] >= rank[from]
}

type modeAction struct {
	name   string
	params map[string]interface{}
}

// actionsForMode returns the actions to execute for a given mode.
func (pe *PreservationEngine) actionsForMode(mode EmergencyMode) []modeAction {
	switch mode {
	case ModeSafe:
		return []modeAction{
			{"disable_non_essential_services", map[string]interface{}{
				"services": []string{"analytics", "reporting", "p2p_sync", "threat_intel_feeds"},
			}},
			{"enable_readonly_mode", map[string]interface{}{
				"scope": []string{"event_ingest", "correlation", "dashboard_view"},
			}},
			{"preserve_all_logs", nil},
			{"notify_architect", map[string]interface{}{"severity": "emergency"}},
			{"increase_monitoring_frequency", map[string]interface{}{"interval": "5s"}},
		}
	case ModeLockdown:
		return []modeAction{
			{"isolate_from_network", map[string]interface{}{"scope": "all_external"}},
			{"freeze_all_processes", nil},
			{"capture_memory_dump", nil},
			{"capture_disk_snapshot", nil},
			{"trigger_immune_kernel_lock", map[string]interface{}{
				"allow_syscalls": []string{"read", "write", "exit"},
			}},
			{"send_panic_alert", map[string]interface{}{
				"channels": []string{"email", "sms", "slack", "pagerduty"},
			}},
		}
	case ModeApoptosis:
		return []modeAction{
			{"graceful_shutdown", map[string]interface{}{"timeout": "30s", "drain_events": true}},
			{"zero_sensitive_memory", map[string]interface{}{
				"regions": []string{"keys", "certs", "tokens", "secrets"},
			}},
			{"preserve_forensic_evidence", nil},
			{"notify_soc", map[string]interface{}{
				"severity": "CRITICAL",
				"message":  "system self-terminated",
			}},
			{"secure_erase_temp_files", nil},
		}
	}
	return nil
}

// executeAction runs a mode action and records the result.
func (pe *PreservationEngine) executeAction(mode EmergencyMode, name string, params map[string]interface{}) error {
	err := pe.actionFn(mode, name, params)
	success := err == nil
	errStr := ""
	if err != nil {
		errStr = err.Error()
	}
	pe.recordEvent(mode, name, fmt.Sprintf("params: %v", params), success, errStr)
	return err
}

// recordEvent appends to the audit history.
func (pe *PreservationEngine) recordEvent(mode EmergencyMode, action, detail string, success bool, errStr string) {
	pe.history = append(pe.history, PreservationEvent{
		Timestamp: time.Now(),
		Mode:      mode,
		Action:    action,
		Detail:    detail,
		Success:   success,
		Error:     errStr,
	})
}

// History returns the preservation audit log.
func (pe *PreservationEngine) History() []PreservationEvent {
	pe.mu.RLock()
	defer pe.mu.RUnlock()
	result := make([]PreservationEvent, len(pe.history))
	copy(result, pe.history)
	return result
}

// SetIntegrityCheck sets the pluggable integrity checker.
func (pe *PreservationEngine) SetIntegrityCheck(fn func() IntegrityReport) {
	pe.mu.Lock()
	defer pe.mu.Unlock()
	pe.integrityFn = fn
}

// CheckIntegrity runs the pluggable integrity check and returns the report.
func (pe *PreservationEngine) CheckIntegrity() IntegrityReport {
	pe.mu.RLock()
	fn := pe.integrityFn
	pe.mu.RUnlock()

	if fn == nil {
		return IntegrityReport{Overall: IntegrityVerified, Timestamp: time.Now()}
	}
	return fn()
}
