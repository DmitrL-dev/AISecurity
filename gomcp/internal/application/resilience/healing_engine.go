package resilience

import (
	"context"
	"fmt"
	"log/slog"
	"sync"
	"time"
)

// HealingState represents the FSM state of a healing operation.
type HealingState string

const (
	HealingIdle       HealingState = "IDLE"
	HealingDiagnosing HealingState = "DIAGNOSING"
	HealingActive     HealingState = "HEALING"
	HealingVerifying  HealingState = "VERIFYING"
	HealingCompleted  HealingState = "COMPLETED"
	HealingFailed     HealingState = "FAILED"
)

// HealingResult summarizes a completed healing operation.
type HealingResult string

const (
	ResultSuccess HealingResult = "SUCCESS"
	ResultFailed  HealingResult = "FAILED"
	ResultSkipped HealingResult = "SKIPPED"
)

// ActionType defines the kinds of healing actions.
type ActionType string

const (
	ActionGracefulStop    ActionType = "graceful_stop"
	ActionClearTempFiles  ActionType = "clear_temp_files"
	ActionStartComponent  ActionType = "start_component"
	ActionVerifyHealth    ActionType = "verify_health"
	ActionNotifySOC       ActionType = "notify_soc"
	ActionFreezeConfig    ActionType = "freeze_config"
	ActionRollbackConfig  ActionType = "rollback_config"
	ActionVerifyConfig    ActionType = "verify_config"
	ActionSwitchReadOnly  ActionType = "switch_to_readonly"
	ActionBackupDB        ActionType = "backup_db"
	ActionRestoreSnapshot ActionType = "restore_snapshot"
	ActionVerifyIntegrity ActionType = "verify_integrity"
	ActionResumeWrites    ActionType = "resume_writes"
	ActionDisableRules    ActionType = "disable_rules"
	ActionRevertRules     ActionType = "revert_rules"
	ActionReloadEngine    ActionType = "reload_engine"
	ActionIsolateNetwork  ActionType = "isolate_network"
	ActionRegenCerts      ActionType = "regenerate_certs"
	ActionRestoreNetwork  ActionType = "restore_network"
	ActionNotifyArchitect ActionType = "notify_architect"
	ActionEnterSafeMode   ActionType = "enter_safe_mode"
)

// Action is a single step in a healing strategy.
type Action struct {
	Type    ActionType             `json:"type"`
	Params  map[string]interface{} `json:"params,omitempty"`
	Timeout time.Duration          `json:"timeout"`
	OnError string                 `json:"on_error"` // "continue", "abort", "rollback"
}

// TriggerCondition defines when a healing strategy activates.
type TriggerCondition struct {
	Metrics             []string          `json:"metrics,omitempty"`
	Statuses            []ComponentStatus `json:"statuses,omitempty"`
	ConsecutiveFailures int               `json:"consecutive_failures"`
	WithinWindow        time.Duration     `json:"within_window"`
}

// RollbackPlan defines what happens if healing fails.
type RollbackPlan struct {
	OnFailure string   `json:"on_failure"` // "escalate", "enter_safe_mode", "maintain_isolation"
	Actions   []Action `json:"actions,omitempty"`
}

// HealingStrategy is a complete self-healing plan.
type HealingStrategy struct {
	ID          string           `json:"id"`
	Name        string           `json:"name"`
	Trigger     TriggerCondition `json:"trigger"`
	Actions     []Action         `json:"actions"`
	Rollback    RollbackPlan     `json:"rollback"`
	MaxAttempts int              `json:"max_attempts"`
	Cooldown    time.Duration    `json:"cooldown"`
}

// Diagnosis is the result of root cause analysis.
type Diagnosis struct {
	Component     string        `json:"component"`
	Metric        string        `json:"metric"`
	RootCause     string        `json:"root_cause"`
	Confidence    float64       `json:"confidence"`
	SuggestedFix  string        `json:"suggested_fix"`
	RelatedAlerts []HealthAlert `json:"related_alerts,omitempty"`
}

// HealingOperation tracks a single healing attempt.
type HealingOperation struct {
	ID            string        `json:"id"`
	StrategyID    string        `json:"strategy_id"`
	Component     string        `json:"component"`
	State         HealingState  `json:"state"`
	Diagnosis     *Diagnosis    `json:"diagnosis,omitempty"`
	ActionsRun    []ActionLog   `json:"actions_run"`
	Result        HealingResult `json:"result"`
	StartedAt     time.Time     `json:"started_at"`
	CompletedAt   time.Time     `json:"completed_at,omitempty"`
	Error         string        `json:"error,omitempty"`
	AttemptNumber int           `json:"attempt_number"`
}

// ActionLog records the execution of a single action.
type ActionLog struct {
	Action    ActionType    `json:"action"`
	StartedAt time.Time     `json:"started_at"`
	Duration  time.Duration `json:"duration"`
	Success   bool          `json:"success"`
	Error     string        `json:"error,omitempty"`
}

// ActionExecutorFunc is the callback that actually runs an action.
// Implementations handle the real system operations (restart, rollback, etc.).
type ActionExecutorFunc func(ctx context.Context, action Action, component string) error

// HealingEngine is the L2 Self-Healing orchestrator.
type HealingEngine struct {
	mu         sync.RWMutex
	strategies []HealingStrategy
	cooldowns  map[string]time.Time // strategyID → earliest next run
	operations []*HealingOperation
	opCounter  int64
	executor   ActionExecutorFunc
	alertBus   <-chan HealthAlert
	escalateFn func(HealthAlert) // called on unrecoverable failure
	logger     *slog.Logger
}

// NewHealingEngine creates a new self-healing engine.
func NewHealingEngine(
	alertBus <-chan HealthAlert,
	executor ActionExecutorFunc,
	escalateFn func(HealthAlert),
) *HealingEngine {
	return &HealingEngine{
		cooldowns:  make(map[string]time.Time),
		operations: make([]*HealingOperation, 0),
		executor:   executor,
		alertBus:   alertBus,
		escalateFn: escalateFn,
		logger:     slog.Default().With("component", "sarl-healing-engine"),
	}
}

// RegisterStrategy adds a healing strategy.
func (he *HealingEngine) RegisterStrategy(s HealingStrategy) {
	he.mu.Lock()
	defer he.mu.Unlock()
	he.strategies = append(he.strategies, s)
	he.logger.Info("strategy registered", "id", s.ID, "name", s.Name)
}

// Start begins listening for alerts and initiating healing. Blocks until ctx is cancelled.
func (he *HealingEngine) Start(ctx context.Context) {
	he.logger.Info("healing engine started", "strategies", len(he.strategies))

	for {
		select {
		case <-ctx.Done():
			he.logger.Info("healing engine stopped")
			return
		case alert, ok := <-he.alertBus:
			if !ok {
				return
			}
			if alert.Severity == SeverityCritical || alert.Severity == SeverityWarning {
				he.initiateHealing(ctx, alert)
			}
		}
	}
}

// initiateHealing runs the healing pipeline for an alert.
func (he *HealingEngine) initiateHealing(ctx context.Context, alert HealthAlert) {
	strategy := he.findStrategy(alert)
	if strategy == nil {
		he.logger.Info("no matching strategy for alert",
			"component", alert.Component,
			"metric", alert.Metric,
		)
		return
	}

	if he.isInCooldown(strategy.ID) {
		he.logger.Info("strategy in cooldown",
			"strategy", strategy.ID,
			"component", alert.Component,
		)
		return
	}

	op := he.createOperation(strategy, alert.Component)

	he.logger.Info("healing initiated",
		"op_id", op.ID,
		"strategy", strategy.ID,
		"component", alert.Component,
	)

	// Phase 1: Diagnose.
	he.transitionOp(op, HealingDiagnosing)
	diagnosis := he.diagnose(alert)
	he.mu.Lock()
	op.Diagnosis = &diagnosis
	he.mu.Unlock()

	// Phase 2: Execute healing actions.
	he.transitionOp(op, HealingActive)
	execErr := he.executeActions(ctx, strategy, op)

	// Phase 3: Verify recovery.
	if execErr == nil {
		he.transitionOp(op, HealingVerifying)
		verifyErr := he.verifyRecovery(ctx, strategy, op.Component)
		if verifyErr != nil {
			execErr = verifyErr
		}
	}

	// Phase 4: Complete or fail.
	if execErr == nil {
		he.transitionOp(op, HealingCompleted)
		he.mu.Lock()
		op.Result = ResultSuccess
		he.mu.Unlock()
		he.logger.Info("healing completed successfully",
			"op_id", op.ID,
			"component", op.Component,
			"duration", time.Since(op.StartedAt),
		)
	} else {
		he.transitionOp(op, HealingFailed)
		he.mu.Lock()
		op.Result = ResultFailed
		op.Error = execErr.Error()
		he.mu.Unlock()
		he.logger.Error("healing failed",
			"op_id", op.ID,
			"component", op.Component,
			"error", execErr,
		)

		// Execute rollback.
		he.executeRollback(ctx, strategy, op)

		// Escalate.
		if he.escalateFn != nil {
			he.escalateFn(alert)
		}
	}

	he.mu.Lock()
	op.CompletedAt = time.Now()
	he.mu.Unlock()
	he.setCooldown(strategy.ID, strategy.Cooldown)
}

// findStrategy returns the first matching strategy for an alert.
func (he *HealingEngine) findStrategy(alert HealthAlert) *HealingStrategy {
	he.mu.RLock()
	defer he.mu.RUnlock()

	for i := range he.strategies {
		s := &he.strategies[i]
		if he.matchesTrigger(s.Trigger, alert) {
			return s
		}
	}
	return nil
}

// matchesTrigger checks if an alert matches a strategy's trigger condition.
func (he *HealingEngine) matchesTrigger(trigger TriggerCondition, alert HealthAlert) bool {
	// Match by metric name.
	for _, m := range trigger.Metrics {
		if m == alert.Metric {
			return true
		}
	}

	// Match by component status.
	for _, s := range trigger.Statuses {
		switch s {
		case StatusCritical:
			if alert.Severity == SeverityCritical {
				return true
			}
		case StatusOffline:
			if alert.Severity == SeverityCritical && alert.SuggestedAction == "restart" {
				return true
			}
		}
	}

	return false
}

// isInCooldown checks if a strategy is still in its cooldown period.
func (he *HealingEngine) isInCooldown(strategyID string) bool {
	he.mu.RLock()
	defer he.mu.RUnlock()

	earliest, ok := he.cooldowns[strategyID]
	return ok && time.Now().Before(earliest)
}

// setCooldown marks a strategy as cooling down.
func (he *HealingEngine) setCooldown(strategyID string, duration time.Duration) {
	he.mu.Lock()
	defer he.mu.Unlock()
	he.cooldowns[strategyID] = time.Now().Add(duration)
}

// createOperation creates and records a new healing operation.
func (he *HealingEngine) createOperation(strategy *HealingStrategy, component string) *HealingOperation {
	he.mu.Lock()
	defer he.mu.Unlock()

	he.opCounter++
	op := &HealingOperation{
		ID:         fmt.Sprintf("heal-%d", he.opCounter),
		StrategyID: strategy.ID,
		Component:  component,
		State:      HealingIdle,
		StartedAt:  time.Now(),
		ActionsRun: make([]ActionLog, 0),
	}
	he.operations = append(he.operations, op)
	return op
}

// transitionOp moves an operation to a new state.
//
// Review pass 4 (error-handling/resource-safety): the write to op.State must be
// serialized with GetOperation/RecentOperations, which read operation fields
// under he.mu. Those readers deep-copy under RLock, but that copy only protects
// against torn reads if the writer also holds the lock — otherwise it is a data
// race (confirmed by `go test -race`). Hold the lock for the field mutation.
func (he *HealingEngine) transitionOp(op *HealingOperation, newState HealingState) {
	he.mu.Lock()
	from := op.State
	op.State = newState
	he.mu.Unlock()
	he.logger.Debug("healing state transition",
		"op_id", op.ID,
		"from", from,
		"to", newState,
	)
}

// diagnose performs root cause analysis for an alert.
func (he *HealingEngine) diagnose(alert HealthAlert) Diagnosis {
	var rootCause string
	var confidence float64
	var suggestedFix string

	switch {
	case alert.Metric == "memory" && alert.Current > 90:
		rootCause = "memory_exhaustion"
		confidence = 0.9
		suggestedFix = "restart with increased limits"
	case alert.Metric == "cpu" && alert.Current > 90:
		rootCause = "cpu_saturation"
		confidence = 0.8
		suggestedFix = "check for runaway goroutines"
	case alert.Metric == "error_rate":
		rootCause = "elevated_error_rate"
		confidence = 0.7
		suggestedFix = "check dependencies and config"
	case alert.Metric == "latency_p99":
		rootCause = "latency_degradation"
		confidence = 0.6
		suggestedFix = "check database and network"
	case alert.Metric == "quorum":
		rootCause = "quorum_loss"
		confidence = 0.95
		suggestedFix = "activate safe mode"
	default:
		rootCause = fmt.Sprintf("threshold_breach_%s", alert.Metric)
		confidence = 0.5
		suggestedFix = "investigate manually"
	}

	return Diagnosis{
		Component:    alert.Component,
		Metric:       alert.Metric,
		RootCause:    rootCause,
		Confidence:   confidence,
		SuggestedFix: suggestedFix,
	}
}

// executeActions runs each action in sequence.
func (he *HealingEngine) executeActions(ctx context.Context, strategy *HealingStrategy, op *HealingOperation) error {
	for _, action := range strategy.Actions {
		actionCtx := ctx
		var cancel context.CancelFunc
		if action.Timeout > 0 {
			actionCtx, cancel = context.WithTimeout(ctx, action.Timeout)
		}

		start := time.Now()
		err := he.executor(actionCtx, action, op.Component)
		duration := time.Since(start)

		if cancel != nil {
			cancel()
		}

		logEntry := ActionLog{
			Action:    action.Type,
			StartedAt: start,
			Duration:  duration,
			Success:   err == nil,
		}
		if err != nil {
			logEntry.Error = err.Error()
		}
		he.mu.Lock()
		op.ActionsRun = append(op.ActionsRun, logEntry)
		he.mu.Unlock()

		if err != nil {
			switch action.OnError {
			case "continue":
				he.logger.Warn("action failed, continuing",
					"action", action.Type,
					"error", err,
				)
			case "rollback":
				return fmt.Errorf("action %s failed (rollback): %w", action.Type, err)
			default: // "abort"
				return fmt.Errorf("action %s failed: %w", action.Type, err)
			}
		}
	}
	return nil
}

// verifyRecovery checks if the component is healthy after healing.
func (he *HealingEngine) verifyRecovery(ctx context.Context, strategy *HealingStrategy, component string) error {
	// Execute a verify_health action if not already in the strategy.
	verifyAction := Action{
		Type:    ActionVerifyHealth,
		Timeout: 30 * time.Second,
	}
	return he.executor(ctx, verifyAction, component)
}

// executeRollback runs the rollback plan for a failed healing.
func (he *HealingEngine) executeRollback(ctx context.Context, strategy *HealingStrategy, op *HealingOperation) {
	if len(strategy.Rollback.Actions) == 0 {
		he.logger.Info("no rollback actions defined",
			"strategy", strategy.ID,
		)
		return
	}

	he.logger.Warn("executing rollback",
		"strategy", strategy.ID,
		"component", op.Component,
	)

	for _, action := range strategy.Rollback.Actions {
		if err := he.executor(ctx, action, op.Component); err != nil {
			he.logger.Error("rollback action failed",
				"action", action.Type,
				"error", err,
			)
		}
	}
}

// GetOperation returns a healing operation by ID.
// Returns a deep copy to prevent data races with the healing goroutine.
func (he *HealingEngine) GetOperation(id string) (*HealingOperation, bool) {
	he.mu.RLock()
	defer he.mu.RUnlock()

	for _, op := range he.operations {
		if op.ID == id {
			cp := *op
			cp.ActionsRun = make([]ActionLog, len(op.ActionsRun))
			copy(cp.ActionsRun, op.ActionsRun)
			if op.Diagnosis != nil {
				diag := *op.Diagnosis
				cp.Diagnosis = &diag
			}
			return &cp, true
		}
	}
	return nil, false
}

// RecentOperations returns the last N operations.
// Returns deep copies to prevent data races with the healing goroutine.
func (he *HealingEngine) RecentOperations(n int) []HealingOperation {
	he.mu.RLock()
	defer he.mu.RUnlock()

	total := len(he.operations)
	if total == 0 {
		return nil
	}
	start := total - n
	if start < 0 {
		start = 0
	}

	result := make([]HealingOperation, 0, n)
	for i := start; i < total; i++ {
		cp := *he.operations[i]
		cp.ActionsRun = make([]ActionLog, len(he.operations[i].ActionsRun))
		copy(cp.ActionsRun, he.operations[i].ActionsRun)
		if he.operations[i].Diagnosis != nil {
			diag := *he.operations[i].Diagnosis
			cp.Diagnosis = &diag
		}
		result = append(result, cp)
	}
	return result
}

// StrategyCount returns the number of registered strategies.
func (he *HealingEngine) StrategyCount() int {
	he.mu.RLock()
	defer he.mu.RUnlock()
	return len(he.strategies)
}
