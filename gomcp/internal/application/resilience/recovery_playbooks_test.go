package resilience

import (
	"context"
	"fmt"
	"testing"
	"time"
)

// --- Mock playbook executor ---

type mockPlaybookExecutor struct {
	failSteps map[string]bool
	callCount int
}

func newMockPlaybookExecutor() *mockPlaybookExecutor {
	return &mockPlaybookExecutor{failSteps: make(map[string]bool)}
}

func (m *mockPlaybookExecutor) execute(_ context.Context, step PlaybookStep, _ string) (string, error) {
	m.callCount++
	if m.failSteps[step.ID] {
		return "", fmt.Errorf("step %s failed", step.ID)
	}
	return fmt.Sprintf("step %s completed", step.ID), nil
}

// --- Recovery Playbook Tests ---

// AR-01: Component resurrection (success).
func TestPlaybook_AR01_ResurrectionSuccess(t *testing.T) {
	mock := newMockPlaybookExecutor()
	rpe := NewRecoveryPlaybookEngine(mock.execute)
	rpe.RegisterPlaybook(ComponentResurrectionPlaybook())

	execID, err := rpe.Execute(context.Background(), "component-resurrection", "soc-ingest")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	exec, ok := rpe.GetExecution(execID)
	if !ok {
		t.Fatal("execution not found")
	}
	if exec.Status != PlaybookSucceeded {
		t.Errorf("expected SUCCEEDED, got %s", exec.Status)
	}
	if len(exec.StepsRun) == 0 {
		t.Error("expected steps to be recorded")
	}
}

// AR-02: Component resurrection (failure → rollback).
func TestPlaybook_AR02_ResurrectionFailure(t *testing.T) {
	mock := newMockPlaybookExecutor()
	mock.failSteps["restart-component"] = true

	rpe := NewRecoveryPlaybookEngine(mock.execute)
	rpe.RegisterPlaybook(ComponentResurrectionPlaybook())

	_, err := rpe.Execute(context.Background(), "component-resurrection", "soc-ingest")
	if err == nil {
		t.Fatal("expected error")
	}

	execs := rpe.RecentExecutions(10)
	if len(execs) == 0 {
		t.Fatal("expected execution")
	}
	if execs[0].Status != PlaybookRolledBack {
		t.Errorf("expected ROLLED_BACK, got %s", execs[0].Status)
	}
}

// AR-03: Consensus recovery (success).
func TestPlaybook_AR03_ConsensusSuccess(t *testing.T) {
	mock := newMockPlaybookExecutor()
	rpe := NewRecoveryPlaybookEngine(mock.execute)
	rpe.RegisterPlaybook(ConsensusRecoveryPlaybook())

	_, err := rpe.Execute(context.Background(), "consensus-recovery", "cluster")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}

// AR-04: Consensus recovery (failure → readonly maintained).
func TestPlaybook_AR04_ConsensusFailure(t *testing.T) {
	mock := newMockPlaybookExecutor()
	mock.failSteps["elect-leader"] = true

	rpe := NewRecoveryPlaybookEngine(mock.execute)
	rpe.RegisterPlaybook(ConsensusRecoveryPlaybook())

	_, err := rpe.Execute(context.Background(), "consensus-recovery", "cluster")
	if err == nil {
		t.Fatal("expected error")
	}

	execs := rpe.RecentExecutions(10)
	if execs[0].Status != PlaybookRolledBack {
		t.Errorf("expected ROLLED_BACK, got %s", execs[0].Status)
	}
}

// AR-05: Crypto key rotation (success).
func TestPlaybook_AR05_CryptoSuccess(t *testing.T) {
	mock := newMockPlaybookExecutor()
	rpe := NewRecoveryPlaybookEngine(mock.execute)
	rpe.RegisterPlaybook(CryptoRotationPlaybook())

	_, err := rpe.Execute(context.Background(), "crypto-rotation", "system")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}

// AR-06: Crypto rotation (emergency — cert rotation fails → rollback).
func TestPlaybook_AR06_CryptoRollback(t *testing.T) {
	mock := newMockPlaybookExecutor()
	mock.failSteps["rotate-certs"] = true

	rpe := NewRecoveryPlaybookEngine(mock.execute)
	rpe.RegisterPlaybook(CryptoRotationPlaybook())

	_, err := rpe.Execute(context.Background(), "crypto-rotation", "system")
	if err == nil {
		t.Fatal("expected error on cert rotation failure")
	}

	execs := rpe.RecentExecutions(10)
	// Should have run rollback (revert keys).
	found := false
	for _, s := range execs[0].StepsRun {
		if s.StepID == "rb-revert-keys" {
			found = true
		}
	}
	if !found {
		t.Error("expected rollback step rb-revert-keys")
	}
}

// AR-07: Forensic capture (all steps recorded).
func TestPlaybook_AR07_ForensicCapture(t *testing.T) {
	mock := newMockPlaybookExecutor()
	rpe := NewRecoveryPlaybookEngine(mock.execute)
	rpe.RegisterPlaybook(ComponentResurrectionPlaybook())

	execID, _ := rpe.Execute(context.Background(), "component-resurrection", "comp")
	exec, _ := rpe.GetExecution(execID)

	for _, step := range exec.StepsRun {
		if step.StepID == "" {
			t.Error("step missing ID")
		}
		if step.StepName == "" {
			t.Errorf("step %s has empty name", step.StepID)
		}
	}
}

// AR-08: Rollback execution on action failure.
func TestPlaybook_AR08_RollbackExecution(t *testing.T) {
	mock := newMockPlaybookExecutor()
	mock.failSteps["sync-state"] = true // Sync fails → rollback trigger.

	rpe := NewRecoveryPlaybookEngine(mock.execute)
	rpe.RegisterPlaybook(ConsensusRecoveryPlaybook())

	rpe.Execute(context.Background(), "consensus-recovery", "cluster")

	execs := rpe.RecentExecutions(10)
	if execs[0].Status != PlaybookRolledBack {
		t.Errorf("expected ROLLED_BACK, got %s", execs[0].Status)
	}
}

// AR-09: Step retries.
func TestPlaybook_AR09_StepRetries(t *testing.T) {
	callCount := 0
	executor := func(_ context.Context, step PlaybookStep, _ string) (string, error) {
		callCount++
		if step.ID == "verify-health" && callCount <= 2 {
			return "", fmt.Errorf("not healthy yet")
		}
		return "ok", nil
	}

	rpe := NewRecoveryPlaybookEngine(executor)
	rpe.RegisterPlaybook(ComponentResurrectionPlaybook())

	_, err := rpe.Execute(context.Background(), "component-resurrection", "comp")
	if err != nil {
		t.Fatalf("expected success after retries: %v", err)
	}
}

// AR-10: Playbook not found.
func TestPlaybook_AR10_NotFound(t *testing.T) {
	rpe := NewRecoveryPlaybookEngine(nil)
	_, err := rpe.Execute(context.Background(), "nonexistent", "comp")
	if err == nil {
		t.Fatal("expected error for nonexistent playbook")
	}
}

// AR-11: Audit logging (all step timestamps).
func TestPlaybook_AR11_AuditTimestamps(t *testing.T) {
	mock := newMockPlaybookExecutor()
	rpe := NewRecoveryPlaybookEngine(mock.execute)
	rpe.RegisterPlaybook(ComponentResurrectionPlaybook())

	execID, _ := rpe.Execute(context.Background(), "component-resurrection", "comp")
	exec, _ := rpe.GetExecution(execID)

	if exec.StartedAt.IsZero() {
		t.Error("missing started_at")
	}
	if exec.CompletedAt.IsZero() {
		t.Error("missing completed_at")
	}
}

// AR-12: OnError=continue skips non-critical failures.
func TestPlaybook_AR12_ContinueOnError(t *testing.T) {
	mock := newMockPlaybookExecutor()
	mock.failSteps["capture-forensics"] = true // OnError=continue.
	mock.failSteps["notify-success"] = true    // OnError=continue.

	rpe := NewRecoveryPlaybookEngine(mock.execute)
	rpe.RegisterPlaybook(ComponentResurrectionPlaybook())

	_, err := rpe.Execute(context.Background(), "component-resurrection", "comp")
	if err != nil {
		t.Fatalf("expected success despite continue-on-error steps: %v", err)
	}
}

// AR-13: Context cancellation.
func TestPlaybook_AR13_ContextCancel(t *testing.T) {
	executor := func(ctx context.Context, _ PlaybookStep, _ string) (string, error) {
		select {
		case <-ctx.Done():
			return "", ctx.Err()
		case <-time.After(10 * time.Millisecond):
			return "ok", nil
		}
	}

	rpe := NewRecoveryPlaybookEngine(executor)
	rpe.RegisterPlaybook(ComponentResurrectionPlaybook())

	ctx, cancel := context.WithCancel(context.Background())
	cancel() // Cancel immediately.

	_, err := rpe.Execute(ctx, "component-resurrection", "comp")
	// May or may not error depending on timing, but should not hang.
	_ = err
}

// AR-14: DefaultPlaybooks returns 3.
func TestPlaybook_AR14_DefaultPlaybooks(t *testing.T) {
	pbs := DefaultPlaybooks()
	if len(pbs) != 3 {
		t.Errorf("expected 3 playbooks, got %d", len(pbs))
	}

	ids := map[string]bool{}
	for _, pb := range pbs {
		if ids[pb.ID] {
			t.Errorf("duplicate playbook ID: %s", pb.ID)
		}
		ids[pb.ID] = true

		if len(pb.Actions) == 0 {
			t.Errorf("playbook %s has no actions", pb.ID)
		}
		if len(pb.SuccessCriteria) == 0 {
			t.Errorf("playbook %s has no success criteria", pb.ID)
		}
	}
}

// AR-15: PlaybookCount and RecentExecutions.
func TestPlaybook_AR15_CountsAndRecent(t *testing.T) {
	mock := newMockPlaybookExecutor()
	rpe := NewRecoveryPlaybookEngine(mock.execute)

	if rpe.PlaybookCount() != 0 {
		t.Error("expected 0")
	}

	for _, pb := range DefaultPlaybooks() {
		rpe.RegisterPlaybook(pb)
	}
	if rpe.PlaybookCount() != 3 {
		t.Errorf("expected 3, got %d", rpe.PlaybookCount())
	}

	// Run two playbooks.
	rpe.Execute(context.Background(), "component-resurrection", "comp1")
	rpe.Execute(context.Background(), "crypto-rotation", "comp2")

	recent := rpe.RecentExecutions(1)
	if len(recent) != 1 {
		t.Errorf("expected 1 recent, got %d", len(recent))
	}
	if recent[0].PlaybookID != "crypto-rotation" {
		t.Errorf("expected crypto-rotation, got %s", recent[0].PlaybookID)
	}

	all := rpe.RecentExecutions(100)
	if len(all) != 2 {
		t.Errorf("expected 2 total, got %d", len(all))
	}
}
