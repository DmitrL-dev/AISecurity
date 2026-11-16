package resilience

import (
	"crypto/sha256"
	"encoding/hex"
	"os"
	"path/filepath"
	"testing"
	"time"
)

// --- Mock action function ---

type modeActionLog struct {
	calls []struct {
		mode   EmergencyMode
		action string
	}
	failAction string // if set, this action will fail
}

func newModeActionLog() *modeActionLog {
	return &modeActionLog{}
}

func (m *modeActionLog) execute(mode EmergencyMode, action string, _ map[string]interface{}) error {
	m.calls = append(m.calls, struct {
		mode   EmergencyMode
		action string
	}{mode, action})
	if m.failAction == action {
		return errActionFailed
	}
	return nil
}

var errActionFailed = &actionError{"simulated failure"}

type actionError struct{ msg string }

func (e *actionError) Error() string { return e.msg }

// --- Preservation Engine Tests ---

// SP-01: Safe mode activation.
func TestPreservation_SP01_SafeMode(t *testing.T) {
	log := newModeActionLog()
	pe := NewPreservationEngine(log.execute)

	err := pe.ActivateMode(ModeSafe, "quorum lost (3/6 offline)", "auto")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if pe.CurrentMode() != ModeSafe {
		t.Errorf("expected SAFE, got %s", pe.CurrentMode())
	}

	activation := pe.Activation()
	if activation == nil {
		t.Fatal("expected activation details")
	}
	if !activation.AutoExit {
		t.Error("safe mode should have auto-exit enabled")
	}

	// Should have executed safe mode actions.
	if len(log.calls) == 0 {
		t.Error("expected mode actions to be executed")
	}
	// First action should be disable_non_essential_services.
	if log.calls[0].action != "disable_non_essential_services" {
		t.Errorf("expected first action disable_non_essential_services, got %s", log.calls[0].action)
	}
}

// SP-02: Lockdown mode activation.
func TestPreservation_SP02_LockdownMode(t *testing.T) {
	log := newModeActionLog()
	pe := NewPreservationEngine(log.execute)

	err := pe.ActivateMode(ModeLockdown, "binary tampering detected", "auto")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if pe.CurrentMode() != ModeLockdown {
		t.Errorf("expected LOCKDOWN, got %s", pe.CurrentMode())
	}

	// Should have network isolation action.
	foundIsolate := false
	for _, c := range log.calls {
		if c.action == "isolate_from_network" {
			foundIsolate = true
		}
	}
	if !foundIsolate {
		t.Error("expected isolate_from_network in lockdown actions")
	}
}

// SP-03: Apoptosis mode activation.
func TestPreservation_SP03_ApoptosisMode(t *testing.T) {
	log := newModeActionLog()
	pe := NewPreservationEngine(log.execute)

	err := pe.ActivateMode(ModeApoptosis, "rootkit detected", "architect:admin")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if pe.CurrentMode() != ModeApoptosis {
		t.Errorf("expected APOPTOSIS, got %s", pe.CurrentMode())
	}

	// Should have graceful_shutdown action.
	foundShutdown := false
	for _, c := range log.calls {
		if c.action == "graceful_shutdown" {
			foundShutdown = true
		}
	}
	if !foundShutdown {
		t.Error("expected graceful_shutdown in apoptosis actions")
	}

	// Cannot deactivate apoptosis.
	err = pe.DeactivateMode("architect:admin")
	if err == nil {
		t.Error("expected error deactivating apoptosis")
	}
}

// SP-04: Invalid transition (downgrade).
func TestPreservation_SP04_InvalidTransition(t *testing.T) {
	log := newModeActionLog()
	pe := NewPreservationEngine(log.execute)

	pe.ActivateMode(ModeLockdown, "test", "auto")

	// Can't downgrade from LOCKDOWN to SAFE.
	err := pe.ActivateMode(ModeSafe, "test downgrade", "auto")
	if err == nil {
		t.Error("expected error on downgrade from LOCKDOWN to SAFE")
	}
}

// SP-05: Escalation (SAFE → LOCKDOWN → APOPTOSIS).
func TestPreservation_SP05_Escalation(t *testing.T) {
	log := newModeActionLog()
	pe := NewPreservationEngine(log.execute)

	pe.ActivateMode(ModeSafe, "quorum lost", "auto")
	if pe.CurrentMode() != ModeSafe {
		t.Fatal("expected SAFE")
	}

	pe.ActivateMode(ModeLockdown, "compromise detected", "auto")
	if pe.CurrentMode() != ModeLockdown {
		t.Fatal("expected LOCKDOWN")
	}

	pe.ActivateMode(ModeApoptosis, "rootkit", "auto")
	if pe.CurrentMode() != ModeApoptosis {
		t.Fatal("expected APOPTOSIS")
	}
}

// SP-06: Safe mode auto-exit.
func TestPreservation_SP06_AutoExit(t *testing.T) {
	log := newModeActionLog()
	pe := NewPreservationEngine(log.execute)

	pe.ActivateMode(ModeSafe, "test", "auto")

	// Not yet time.
	if pe.ShouldAutoExit() {
		t.Error("should not auto-exit immediately")
	}

	// Fast-forward activation's auto_exit_at.
	pe.mu.Lock()
	pe.activation.AutoExitAt = time.Now().Add(-1 * time.Second)
	pe.mu.Unlock()

	if !pe.ShouldAutoExit() {
		t.Error("should auto-exit after timer expired")
	}
}

// SP-07: Manual deactivation of safe mode.
func TestPreservation_SP07_ManualDeactivate(t *testing.T) {
	log := newModeActionLog()
	pe := NewPreservationEngine(log.execute)

	pe.ActivateMode(ModeSafe, "test", "auto")
	err := pe.DeactivateMode("architect:admin")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if pe.CurrentMode() != ModeNone {
		t.Errorf("expected NONE, got %s", pe.CurrentMode())
	}
}

// SP-08: Lockdown deactivation.
func TestPreservation_SP08_LockdownDeactivate(t *testing.T) {
	log := newModeActionLog()
	pe := NewPreservationEngine(log.execute)

	pe.ActivateMode(ModeLockdown, "test", "auto")
	err := pe.DeactivateMode("architect:admin")
	if err != nil {
		t.Fatalf("lockdown deactivation should succeed: %v", err)
	}
}

// SP-09: History audit log.
func TestPreservation_SP09_AuditHistory(t *testing.T) {
	log := newModeActionLog()
	pe := NewPreservationEngine(log.execute)

	pe.ActivateMode(ModeSafe, "test", "auto")
	pe.DeactivateMode("admin")

	history := pe.History()
	if len(history) == 0 {
		t.Error("expected audit history entries")
	}

	// Last entry should be deactivation.
	last := history[len(history)-1]
	if last.Action != "deactivated" {
		t.Errorf("expected deactivated, got %s", last.Action)
	}
}

// SP-10: Action failure in non-apoptosis mode aborts.
func TestPreservation_SP10_ActionFailure(t *testing.T) {
	log := newModeActionLog()
	log.failAction = "disable_non_essential_services"
	pe := NewPreservationEngine(log.execute)

	err := pe.ActivateMode(ModeSafe, "test", "auto")
	if err == nil {
		t.Error("expected error when safe mode action fails")
	}
	// Mode should not have changed due to failure.
	if pe.CurrentMode() != ModeNone {
		t.Errorf("expected NONE after failed activation, got %s", pe.CurrentMode())
	}
}

// SP-10b: Action failure in apoptosis mode continues.
func TestPreservation_SP10b_ApoptosisActionFailure(t *testing.T) {
	log := newModeActionLog()
	log.failAction = "graceful_shutdown"
	pe := NewPreservationEngine(log.execute)

	// Apoptosis should continue despite action failures.
	err := pe.ActivateMode(ModeApoptosis, "rootkit", "auto")
	if err != nil {
		t.Fatalf("apoptosis should not fail on action errors: %v", err)
	}
	if pe.CurrentMode() != ModeApoptosis {
		t.Errorf("expected APOPTOSIS, got %s", pe.CurrentMode())
	}
}

// Test ModeNone activation rejected.
func TestPreservation_ModeNoneRejected(t *testing.T) {
	pe := NewPreservationEngine(func(_ EmergencyMode, _ string, _ map[string]interface{}) error { return nil })
	err := pe.ActivateMode(ModeNone, "test", "auto")
	if err == nil {
		t.Error("expected error activating ModeNone")
	}
}

// Test deactivate when already NONE.
func TestPreservation_DeactivateNone(t *testing.T) {
	pe := NewPreservationEngine(func(_ EmergencyMode, _ string, _ map[string]interface{}) error { return nil })
	err := pe.DeactivateMode("admin")
	if err != nil {
		t.Errorf("deactivating NONE should be no-op: %v", err)
	}
}

// Test ShouldAutoExit when not in safe mode.
func TestPreservation_AutoExitNotSafe(t *testing.T) {
	pe := NewPreservationEngine(func(_ EmergencyMode, _ string, _ map[string]interface{}) error { return nil })
	if pe.ShouldAutoExit() {
		t.Error("should not auto-exit when mode is NONE")
	}
}

// --- Integrity Verifier Tests ---

// SP-04 (ТЗ): Binary integrity check — hash mismatch.
func TestIntegrity_BinaryMismatch(t *testing.T) {
	tmpDir := t.TempDir()
	binPath := filepath.Join(tmpDir, "test-binary")
	os.WriteFile(binPath, []byte("original content"), 0o644)

	// Calculate correct hash.
	h := sha256.Sum256([]byte("original content"))
	correctHash := hex.EncodeToString(h[:])

	iv := NewIntegrityVerifier([]byte("test-key"))
	iv.RegisterBinary(binPath, correctHash)

	// Verify (should pass).
	report := iv.VerifyAll()
	if report.Overall != IntegrityVerified {
		t.Errorf("expected VERIFIED, got %s", report.Overall)
	}

	// Tamper with the binary.
	os.WriteFile(binPath, []byte("tampered content"), 0o644)

	// Verify (should fail).
	report = iv.VerifyAll()
	if report.Overall != IntegrityCompromised {
		t.Errorf("expected COMPROMISED, got %s", report.Overall)
	}
	bs := report.Binaries[binPath]
	if bs.Status != IntegrityCompromised {
		t.Errorf("expected binary COMPROMISED, got %s", bs.Status)
	}
}

// Binary not found.
func TestIntegrity_BinaryNotFound(t *testing.T) {
	iv := NewIntegrityVerifier([]byte("test-key"))
	iv.RegisterBinary("/nonexistent/binary", "abc123")

	report := iv.VerifyAll()
	bs := report.Binaries["/nonexistent/binary"]
	if bs.Status != IntegrityUnknown {
		t.Errorf("expected UNKNOWN for missing binary, got %s", bs.Status)
	}
}

// Config HMAC computation.
func TestIntegrity_ConfigHMAC(t *testing.T) {
	tmpDir := t.TempDir()
	cfgPath := filepath.Join(tmpDir, "config.yaml")
	os.WriteFile(cfgPath, []byte("server:\n  port: 8080"), 0o644)

	iv := NewIntegrityVerifier([]byte("hmac-key"))
	iv.RegisterConfig(cfgPath)

	report := iv.VerifyAll()
	cs := report.Configs[cfgPath]
	if !cs.Valid {
		t.Errorf("expected valid config, got error: %s", cs.Error)
	}
	if cs.CurrentHMAC == "" {
		t.Error("expected non-empty HMAC")
	}
}

// Config file unreadable.
func TestIntegrity_ConfigUnreadable(t *testing.T) {
	iv := NewIntegrityVerifier([]byte("key"))
	iv.RegisterConfig("/nonexistent/config.yaml")

	report := iv.VerifyAll()
	cs := report.Configs["/nonexistent/config.yaml"]
	if cs.Valid {
		t.Error("expected invalid for unreadable config")
	}
}

// Decision chain — file does not exist (OK, no chain yet).
func TestIntegrity_ChainNotExist(t *testing.T) {
	iv := NewIntegrityVerifier([]byte("key"))
	iv.SetChainPath("/nonexistent/decisions.log")

	report := iv.VerifyAll()
	if report.Chain == nil {
		t.Fatal("expected chain status")
	}
	if !report.Chain.Valid {
		t.Error("nonexistent chain should be valid (no entries)")
	}
}

// Decision chain — file exists.
func TestIntegrity_ChainExists(t *testing.T) {
	tmpDir := t.TempDir()
	chainPath := filepath.Join(tmpDir, "decisions.log")
	os.WriteFile(chainPath, []byte("entry1\nentry2\n"), 0o644)

	iv := NewIntegrityVerifier([]byte("key"))
	iv.SetChainPath(chainPath)

	report := iv.VerifyAll()
	if report.Chain == nil {
		t.Fatal("expected chain status")
	}
	if !report.Chain.Valid {
		t.Error("expected valid chain")
	}
}

// LastReport.
func TestIntegrity_LastReport(t *testing.T) {
	iv := NewIntegrityVerifier([]byte("key"))
	if iv.LastReport() != nil {
		t.Error("expected nil before first verify")
	}

	iv.VerifyAll()
	if iv.LastReport() == nil {
		t.Error("expected report after verify")
	}
}

// Pluggable integrity check in PreservationEngine.
func TestPreservation_IntegrityCheck(t *testing.T) {
	pe := NewPreservationEngine(func(_ EmergencyMode, _ string, _ map[string]interface{}) error { return nil })

	// Default: no integrity fn → VERIFIED.
	report := pe.CheckIntegrity()
	if report.Overall != IntegrityVerified {
		t.Errorf("expected VERIFIED, got %s", report.Overall)
	}

	// Set custom checker.
	pe.SetIntegrityCheck(func() IntegrityReport {
		return IntegrityReport{Overall: IntegrityCompromised, Timestamp: time.Now()}
	})

	report = pe.CheckIntegrity()
	if report.Overall != IntegrityCompromised {
		t.Errorf("expected COMPROMISED from custom checker, got %s", report.Overall)
	}
}
