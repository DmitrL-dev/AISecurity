package resilience

import (
	"context"
	"fmt"
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

// --- Mock executor for tests ---

type mockExecutorLog struct {
	mu      sync.Mutex
	actions []ActionType
	fail    map[ActionType]bool
	count   atomic.Int64
}

func newMockExecutor() *mockExecutorLog {
	return &mockExecutorLog{
		fail: make(map[ActionType]bool),
	}
}

func (m *mockExecutorLog) execute(_ context.Context, action Action, _ string) error {
	m.count.Add(1)
	// execute is invoked from the engine's Start goroutine; tests read
	// actionList() after cancellation, so the slice access must be guarded.
	m.mu.Lock()
	m.actions = append(m.actions, action.Type)
	m.mu.Unlock()
	if m.fail[action.Type] {
		return fmt.Errorf("action %s failed", action.Type)
	}
	return nil
}

// actionList returns a copy of the recorded actions under the lock.
func (m *mockExecutorLog) actionList() []ActionType {
	m.mu.Lock()
	defer m.mu.Unlock()
	out := make([]ActionType, len(m.actions))
	copy(out, m.actions)
	return out
}

// --- Healing Engine Tests ---

// HE-01: Component restart (success).
func TestHealingEngine_HE01_RestartSuccess(t *testing.T) {
	mock := newMockExecutor()
	alertCh := make(chan HealthAlert, 10)
	// escalated is written by the engine's Start goroutine and read by the
	// test after cancellation; use atomic.Bool to avoid a data race.
	var escalated atomic.Bool

	he := NewHealingEngine(alertCh, mock.execute, func(_ HealthAlert) {
		escalated.Store(true)
	})
	he.RegisterStrategy(RestartComponentStrategy())

	alertCh <- HealthAlert{
		Component:       "soc-ingest",
		Severity:        SeverityCritical,
		Metric:          "quorum",
		SuggestedAction: "restart",
		Timestamp:       time.Now(),
	}

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	// Run one healing cycle.
	go he.Start(ctx)
	time.Sleep(200 * time.Millisecond)
	cancel()

	ops := he.RecentOperations(10)
	if len(ops) == 0 {
		t.Fatal("expected at least 1 operation")
	}
	if ops[0].Result != ResultSuccess {
		t.Errorf("expected SUCCESS, got %s (error: %s)", ops[0].Result, ops[0].Error)
	}
	if escalated.Load() {
		t.Error("should not have escalated on success")
	}
}

// HE-02: Component restart (failure ×3 → escalate).
func TestHealingEngine_HE02_RestartFailureEscalate(t *testing.T) {
	mock := newMockExecutor()
	mock.fail[ActionStartComponent] = true // Start always fails.

	alertCh := make(chan HealthAlert, 10)
	// escalated is written by the engine's Start goroutine and read by the
	// test after cancellation; use atomic.Bool to avoid a data race.
	var escalated atomic.Bool

	he := NewHealingEngine(alertCh, mock.execute, func(_ HealthAlert) {
		escalated.Store(true)
	})
	he.RegisterStrategy(RestartComponentStrategy())

	alertCh <- HealthAlert{
		Component:       "soc-correlate",
		Severity:        SeverityCritical,
		Metric:          "quorum",
		SuggestedAction: "restart",
		Timestamp:       time.Now(),
	}

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	go he.Start(ctx)
	time.Sleep(200 * time.Millisecond)
	cancel()

	if !escalated.Load() {
		t.Error("expected escalation on failure")
	}

	ops := he.RecentOperations(10)
	if len(ops) == 0 {
		t.Fatal("expected operation")
	}
	if ops[0].Result != ResultFailed {
		t.Errorf("expected FAILED, got %s", ops[0].Result)
	}
}

// HE-03: Config rollback strategy matching.
func TestHealingEngine_HE03_ConfigRollback(t *testing.T) {
	mock := newMockExecutor()
	alertCh := make(chan HealthAlert, 10)

	he := NewHealingEngine(alertCh, mock.execute, nil)
	he.RegisterStrategy(RollbackConfigStrategy())

	alertCh <- HealthAlert{
		Component: "soc-ingest",
		Severity:  SeverityWarning,
		Metric:    "config_tampering",
		Timestamp: time.Now(),
	}

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	go he.Start(ctx)
	time.Sleep(200 * time.Millisecond)
	cancel()

	ops := he.RecentOperations(10)
	if len(ops) == 0 {
		t.Fatal("expected operation for config rollback")
	}
	if ops[0].StrategyID != "ROLLBACK_CONFIG" {
		t.Errorf("expected ROLLBACK_CONFIG, got %s", ops[0].StrategyID)
	}
}

// HE-04: Database recovery.
func TestHealingEngine_HE04_DatabaseRecovery(t *testing.T) {
	mock := newMockExecutor()
	alertCh := make(chan HealthAlert, 10)

	he := NewHealingEngine(alertCh, mock.execute, nil)
	he.RegisterStrategy(RecoverDatabaseStrategy())

	alertCh <- HealthAlert{
		Component: "soc-correlate",
		Severity:  SeverityCritical,
		Metric:    "database_corruption",
		Timestamp: time.Now(),
	}

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	go he.Start(ctx)
	time.Sleep(200 * time.Millisecond)
	cancel()

	ops := he.RecentOperations(10)
	if len(ops) == 0 {
		t.Fatal("expected DB recovery op")
	}
	if ops[0].StrategyID != "RECOVER_DATABASE" {
		t.Errorf("expected RECOVER_DATABASE, got %s", ops[0].StrategyID)
	}
}

// HE-05: Rule poisoning defense.
func TestHealingEngine_HE05_RulePoisoning(t *testing.T) {
	mock := newMockExecutor()
	alertCh := make(chan HealthAlert, 10)

	he := NewHealingEngine(alertCh, mock.execute, nil)
	he.RegisterStrategy(RecoverRulesStrategy())

	alertCh <- HealthAlert{
		Component: "soc-correlate",
		Severity:  SeverityWarning,
		Metric:    "rule_execution_failure_rate",
		Timestamp: time.Now(),
	}

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	go he.Start(ctx)
	time.Sleep(200 * time.Millisecond)
	cancel()

	ops := he.RecentOperations(10)
	if len(ops) == 0 {
		t.Fatal("expected rule recovery op")
	}
	if ops[0].StrategyID != "RECOVER_RULES" {
		t.Errorf("expected RECOVER_RULES, got %s", ops[0].StrategyID)
	}
}

// HE-06: Network isolation recovery.
func TestHealingEngine_HE06_NetworkRecovery(t *testing.T) {
	mock := newMockExecutor()
	alertCh := make(chan HealthAlert, 10)

	he := NewHealingEngine(alertCh, mock.execute, nil)
	he.RegisterStrategy(RecoverNetworkStrategy())

	alertCh <- HealthAlert{
		Component: "soc-respond",
		Severity:  SeverityWarning,
		Metric:    "network_partition",
		Timestamp: time.Now(),
	}

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	go he.Start(ctx)
	time.Sleep(200 * time.Millisecond)
	cancel()

	ops := he.RecentOperations(10)
	if len(ops) == 0 {
		t.Fatal("expected network recovery op")
	}
	if ops[0].StrategyID != "RECOVER_NETWORK" {
		t.Errorf("expected RECOVER_NETWORK, got %s", ops[0].StrategyID)
	}
}

// HE-07: Cooldown enforcement.
func TestHealingEngine_HE07_Cooldown(t *testing.T) {
	mock := newMockExecutor()
	alertCh := make(chan HealthAlert, 10)

	he := NewHealingEngine(alertCh, mock.execute, nil)
	he.RegisterStrategy(RestartComponentStrategy())

	// Set cooldown manually.
	he.setCooldown("RESTART_COMPONENT", 1*time.Hour)

	if !he.isInCooldown("RESTART_COMPONENT") {
		t.Error("expected cooldown active")
	}

	alertCh <- HealthAlert{
		Component:       "soc-ingest",
		Severity:        SeverityCritical,
		Metric:          "quorum",
		SuggestedAction: "restart",
		Timestamp:       time.Now(),
	}

	ctx, cancel := context.WithTimeout(context.Background(), 500*time.Millisecond)
	defer cancel()

	go he.Start(ctx)
	time.Sleep(200 * time.Millisecond)
	cancel()

	ops := he.RecentOperations(10)
	if len(ops) != 0 {
		t.Error("expected 0 operations during cooldown")
	}
}

// HE-08: Rollback on failure.
func TestHealingEngine_HE08_Rollback(t *testing.T) {
	mock := newMockExecutor()
	mock.fail[ActionStartComponent] = true

	alertCh := make(chan HealthAlert, 10)
	he := NewHealingEngine(alertCh, mock.execute, func(_ HealthAlert) {})

	strategy := RollbackConfigStrategy()
	he.RegisterStrategy(strategy)

	alertCh <- HealthAlert{
		Component: "soc-ingest",
		Severity:  SeverityWarning,
		Metric:    "config_tampering",
		Timestamp: time.Now(),
	}

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	go he.Start(ctx)
	time.Sleep(200 * time.Millisecond)
	cancel()

	// Rollback should have executed enter_safe_mode.
	actions := mock.actionList()
	foundSafeMode := false
	for _, a := range actions {
		if a == ActionEnterSafeMode {
			foundSafeMode = true
		}
	}
	if !foundSafeMode {
		t.Errorf("expected safe mode in rollback, actions: %v", actions)
	}
}

// HE-09: State machine transitions.
func TestHealingEngine_HE09_StateTransitions(t *testing.T) {
	mock := newMockExecutor()
	alertCh := make(chan HealthAlert, 10)

	he := NewHealingEngine(alertCh, mock.execute, nil)
	he.RegisterStrategy(RestartComponentStrategy())

	alertCh <- HealthAlert{
		Component:       "comp",
		Severity:        SeverityCritical,
		Metric:          "quorum",
		SuggestedAction: "restart",
		Timestamp:       time.Now(),
	}

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	go he.Start(ctx)
	time.Sleep(200 * time.Millisecond)
	cancel()

	ops := he.RecentOperations(10)
	if len(ops) == 0 {
		t.Fatal("expected operation")
	}
	// Final state should be COMPLETED.
	if ops[0].State != HealingCompleted {
		t.Errorf("expected COMPLETED, got %s", ops[0].State)
	}
}

// HE-10: Audit logging — all actions recorded.
func TestHealingEngine_HE10_AuditLogging(t *testing.T) {
	mock := newMockExecutor()
	alertCh := make(chan HealthAlert, 10)

	he := NewHealingEngine(alertCh, mock.execute, nil)
	he.RegisterStrategy(RestartComponentStrategy())

	alertCh <- HealthAlert{
		Component:       "comp",
		Severity:        SeverityCritical,
		Metric:          "quorum",
		SuggestedAction: "restart",
		Timestamp:       time.Now(),
	}

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	go he.Start(ctx)
	time.Sleep(200 * time.Millisecond)
	cancel()

	ops := he.RecentOperations(10)
	if len(ops) == 0 {
		t.Fatal("expected operation")
	}
	if len(ops[0].ActionsRun) == 0 {
		t.Error("expected action logs")
	}
	for _, al := range ops[0].ActionsRun {
		if al.StartedAt.IsZero() {
			t.Error("action log missing start time")
		}
	}
}

// HE-11: Parallel healing — no race conditions.
func TestHealingEngine_HE11_Parallel(t *testing.T) {
	mock := newMockExecutor()
	alertCh := make(chan HealthAlert, 100)

	he := NewHealingEngine(alertCh, mock.execute, nil)
	for _, s := range DefaultStrategies() {
		he.RegisterStrategy(s)
	}

	// Send many alerts concurrently.
	for i := 0; i < 10; i++ {
		alertCh <- HealthAlert{
			Component:       fmt.Sprintf("comp-%d", i),
			Severity:        SeverityCritical,
			Metric:          "quorum",
			SuggestedAction: "restart",
			Timestamp:       time.Now(),
		}
	}

	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()

	go he.Start(ctx)
	time.Sleep(1 * time.Second)
	cancel()

	// All 10 alerts processed (first gets an op, rest hit cooldown).
	ops := he.RecentOperations(100)
	if len(ops) == 0 {
		t.Fatal("expected at least 1 operation")
	}
}

// HE-12: No matching strategy → no operation.
func TestHealingEngine_HE12_NoStrategy(t *testing.T) {
	mock := newMockExecutor()
	alertCh := make(chan HealthAlert, 10)

	he := NewHealingEngine(alertCh, mock.execute, nil)
	// No strategies registered.

	alertCh <- HealthAlert{
		Component: "comp",
		Severity:  SeverityCritical,
		Metric:    "unknown_metric",
		Timestamp: time.Now(),
	}

	ctx, cancel := context.WithTimeout(context.Background(), 500*time.Millisecond)
	defer cancel()

	go he.Start(ctx)
	time.Sleep(200 * time.Millisecond)
	cancel()

	ops := he.RecentOperations(10)
	if len(ops) != 0 {
		t.Errorf("expected 0 operations, got %d", len(ops))
	}
}

// Test diagnosis (various root causes).
func TestHealingEngine_Diagnosis(t *testing.T) {
	mock := newMockExecutor()
	he := NewHealingEngine(nil, mock.execute, nil)

	tests := []struct {
		metric    string
		current   float64
		wantCause string
	}{
		{"memory", 95, "memory_exhaustion"},
		{"cpu", 95, "cpu_saturation"},
		{"error_rate", 10, "elevated_error_rate"},
		{"latency_p99", 200, "latency_degradation"},
		{"quorum", 0.3, "quorum_loss"},
		{"custom", 100, "threshold_breach_custom"},
	}

	for _, tt := range tests {
		alert := HealthAlert{
			Component: "test",
			Metric:    tt.metric,
			Current:   tt.current,
		}
		d := he.diagnose(alert)
		if d.RootCause != tt.wantCause {
			t.Errorf("metric=%s: expected %s, got %s", tt.metric, tt.wantCause, d.RootCause)
		}
		if d.Confidence <= 0 || d.Confidence > 1 {
			t.Errorf("metric=%s: invalid confidence %f", tt.metric, d.Confidence)
		}
	}
}

// Test DefaultStrategies returns 5 strategies.
func TestDefaultStrategies(t *testing.T) {
	strategies := DefaultStrategies()
	if len(strategies) != 5 {
		t.Errorf("expected 5 strategies, got %d", len(strategies))
	}

	ids := map[string]bool{}
	for _, s := range strategies {
		if ids[s.ID] {
			t.Errorf("duplicate strategy ID: %s", s.ID)
		}
		ids[s.ID] = true
		if s.MaxAttempts <= 0 {
			t.Errorf("strategy %s: invalid max_attempts %d", s.ID, s.MaxAttempts)
		}
		if s.Cooldown <= 0 {
			t.Errorf("strategy %s: invalid cooldown %v", s.ID, s.Cooldown)
		}
		if len(s.Actions) == 0 {
			t.Errorf("strategy %s: no actions defined", s.ID)
		}
	}
}

// Test StrategyCount.
func TestHealingEngine_StrategyCount(t *testing.T) {
	he := NewHealingEngine(nil, nil, nil)
	if he.StrategyCount() != 0 {
		t.Error("expected 0")
	}
	for _, s := range DefaultStrategies() {
		he.RegisterStrategy(s)
	}
	if he.StrategyCount() != 5 {
		t.Errorf("expected 5, got %d", he.StrategyCount())
	}
}

// Test GetOperation.
func TestHealingEngine_GetOperation(t *testing.T) {
	mock := newMockExecutor()
	alertCh := make(chan HealthAlert, 10)

	he := NewHealingEngine(alertCh, mock.execute, nil)
	he.RegisterStrategy(RestartComponentStrategy())

	alertCh <- HealthAlert{
		Component:       "comp",
		Severity:        SeverityCritical,
		Metric:          "quorum",
		SuggestedAction: "restart",
		Timestamp:       time.Now(),
	}

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	go he.Start(ctx)
	time.Sleep(200 * time.Millisecond)
	cancel()

	op, ok := he.GetOperation("heal-1")
	if !ok {
		t.Fatal("expected operation heal-1")
	}
	if op.Component != "comp" {
		t.Errorf("expected comp, got %s", op.Component)
	}

	_, ok = he.GetOperation("nonexistent")
	if ok {
		t.Error("expected not found for nonexistent")
	}
}

// Test action OnError=continue.
func TestHealingEngine_ActionContinueOnError(t *testing.T) {
	mock := newMockExecutor()
	mock.fail[ActionGracefulStop] = true // First action fails but marked continue.

	alertCh := make(chan HealthAlert, 10)
	he := NewHealingEngine(alertCh, mock.execute, nil)
	he.RegisterStrategy(RestartComponentStrategy())

	alertCh <- HealthAlert{
		Component:       "comp",
		Severity:        SeverityCritical,
		Metric:          "quorum",
		SuggestedAction: "restart",
		Timestamp:       time.Now(),
	}

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	go he.Start(ctx)
	time.Sleep(200 * time.Millisecond)
	cancel()

	ops := he.RecentOperations(10)
	if len(ops) == 0 {
		t.Fatal("expected operation")
	}
	// Should still succeed because graceful_stop has OnError=continue.
	if ops[0].Result != ResultSuccess {
		t.Errorf("expected SUCCESS (continue on error), got %s", ops[0].Result)
	}
}
