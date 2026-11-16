package resilience

import (
	"context"
	"fmt"
	"log/slog"
	"sync"
	"time"
)

// PlaybookStatus tracks the state of a running playbook.
type PlaybookStatus string

const (
	PlaybookPending   PlaybookStatus = "PENDING"
	PlaybookRunning   PlaybookStatus = "RUNNING"
	PlaybookSucceeded PlaybookStatus = "SUCCEEDED"
	PlaybookFailed    PlaybookStatus = "FAILED"
	PlaybookRolledBack PlaybookStatus = "ROLLED_BACK"
)

// PlaybookStep is a single step in a recovery playbook.
type PlaybookStep struct {
	ID          string                 `json:"id"`
	Name        string                 `json:"name"`
	Type        string                 `json:"type"` // shell, api, consensus, crypto, systemd, http, prometheus
	Timeout     time.Duration          `json:"timeout"`
	Retries     int                    `json:"retries"`
	Params      map[string]interface{} `json:"params,omitempty"`
	OnError     string                 `json:"on_error"` // abort, continue, rollback
	Condition   string                 `json:"condition,omitempty"` // prerequisite condition
}

// Playbook defines a complete recovery procedure.
type Playbook struct {
	ID              string                 `json:"id"`
	Name            string                 `json:"name"`
	Version         string                 `json:"version"`
	TriggerMetric   string                 `json:"trigger_metric"`
	TriggerSeverity string                 `json:"trigger_severity"`
	DiagnosisChecks []PlaybookStep         `json:"diagnosis_checks"`
	Actions         []PlaybookStep         `json:"actions"`
	RollbackActions []PlaybookStep         `json:"rollback_actions"`
	SuccessCriteria []string               `json:"success_criteria"`
}

// PlaybookExecution tracks a single playbook run.
type PlaybookExecution struct {
	ID           string         `json:"id"`
	PlaybookID   string         `json:"playbook_id"`
	Component    string         `json:"component"`
	Status       PlaybookStatus `json:"status"`
	StartedAt    time.Time      `json:"started_at"`
	CompletedAt  time.Time      `json:"completed_at,omitempty"`
	StepsRun     []StepResult   `json:"steps_run"`
	Error        string         `json:"error,omitempty"`
}

// StepResult records the execution of a single playbook step.
type StepResult struct {
	StepID    string        `json:"step_id"`
	StepName  string        `json:"step_name"`
	Success   bool          `json:"success"`
	Duration  time.Duration `json:"duration"`
	Output    string        `json:"output,omitempty"`
	Error     string        `json:"error,omitempty"`
}

// PlaybookExecutorFunc runs a single playbook step.
type PlaybookExecutorFunc func(ctx context.Context, step PlaybookStep, component string) (string, error)

// RecoveryPlaybookEngine manages and executes recovery playbooks.
type RecoveryPlaybookEngine struct {
	mu         sync.RWMutex
	playbooks  map[string]*Playbook
	executions []*PlaybookExecution
	execCount  int64
	executor   PlaybookExecutorFunc
	logger     *slog.Logger
}

// NewRecoveryPlaybookEngine creates a new playbook engine.
func NewRecoveryPlaybookEngine(executor PlaybookExecutorFunc) *RecoveryPlaybookEngine {
	return &RecoveryPlaybookEngine{
		playbooks:  make(map[string]*Playbook),
		executions: make([]*PlaybookExecution, 0),
		executor:   executor,
		logger:     slog.Default().With("component", "sarl-recovery-playbooks"),
	}
}

// RegisterPlaybook adds a playbook to the engine.
func (rpe *RecoveryPlaybookEngine) RegisterPlaybook(pb Playbook) {
	rpe.mu.Lock()
	defer rpe.mu.Unlock()
	rpe.playbooks[pb.ID] = &pb
	rpe.logger.Info("playbook registered", "id", pb.ID, "name", pb.Name)
}

// Execute runs a playbook for a given component. Returns the execution ID.
func (rpe *RecoveryPlaybookEngine) Execute(ctx context.Context, playbookID, component string) (string, error) {
	rpe.mu.Lock()
	pb, ok := rpe.playbooks[playbookID]
	if !ok {
		rpe.mu.Unlock()
		return "", fmt.Errorf("playbook %s not found", playbookID)
	}

	rpe.execCount++
	exec := &PlaybookExecution{
		ID:         fmt.Sprintf("exec-%d", rpe.execCount),
		PlaybookID: playbookID,
		Component:  component,
		Status:     PlaybookRunning,
		StartedAt:  time.Now(),
		StepsRun:   make([]StepResult, 0),
	}
	rpe.executions = append(rpe.executions, exec)
	rpe.mu.Unlock()

	rpe.logger.Info("playbook execution started",
		"exec_id", exec.ID,
		"playbook", pb.Name,
		"component", component,
	)

	// Phase 1: Diagnosis checks.
	for _, check := range pb.DiagnosisChecks {
		result := rpe.runStep(ctx, check, component)
		rpe.appendStep(exec, result)
		if !result.Success {
			rpe.logger.Warn("diagnosis check failed",
				"step", check.ID,
				"error", result.Error,
			)
		}
	}

	// Phase 2: Execute recovery actions.
	var execErr error
	for _, action := range pb.Actions {
		result := rpe.runStep(ctx, action, component)
		rpe.appendStep(exec, result)

		if !result.Success {
			switch action.OnError {
			case "continue":
				continue
			case "rollback":
				execErr = fmt.Errorf("step %s failed (rollback): %s", action.ID, result.Error)
			default: // "abort"
				execErr = fmt.Errorf("step %s failed: %s", action.ID, result.Error)
			}
			break
		}
	}

	// Phase 3: Handle result.
	if execErr != nil {
		rpe.logger.Error("playbook failed, executing rollback",
			"exec_id", exec.ID,
			"error", execErr,
		)

		// Execute rollback.
		for _, rb := range pb.RollbackActions {
			result := rpe.runStep(ctx, rb, component)
			rpe.appendStep(exec, result)
		}

		rpe.mu.Lock()
		exec.Status = PlaybookRolledBack
		exec.Error = execErr.Error()
		rpe.mu.Unlock()
	} else {
		rpe.mu.Lock()
		exec.Status = PlaybookSucceeded
		rpe.mu.Unlock()
		rpe.logger.Info("playbook succeeded",
			"exec_id", exec.ID,
			"component", component,
			"duration", time.Since(exec.StartedAt),
		)
	}

	rpe.mu.Lock()
	exec.CompletedAt = time.Now()
	rpe.mu.Unlock()
	return exec.ID, execErr
}

// appendStep records a completed step on an execution under the engine lock.
//
// Review pass 4 (error-handling/resource-safety): Execute mutates the execution
// record (StepsRun/Status/Error/CompletedAt) after releasing the registration
// lock, while GetExecution/RecentExecutions read those fields under RLock and
// deep-copy. The copy only prevents a torn read if the writer also holds the
// lock; otherwise it is a data race. Serialize the StepsRun append here.
func (rpe *RecoveryPlaybookEngine) appendStep(exec *PlaybookExecution, result StepResult) {
	rpe.mu.Lock()
	exec.StepsRun = append(exec.StepsRun, result)
	rpe.mu.Unlock()
}

// runStep executes a single step with timeout and retries.
func (rpe *RecoveryPlaybookEngine) runStep(ctx context.Context, step PlaybookStep, component string) StepResult {
	start := time.Now()
	result := StepResult{
		StepID:   step.ID,
		StepName: step.Name,
	}

	retries := step.Retries
	if retries <= 0 {
		retries = 1
	}

	var lastErr error
	for attempt := 0; attempt < retries; attempt++ {
		stepCtx := ctx
		var cancel context.CancelFunc
		if step.Timeout > 0 {
			stepCtx, cancel = context.WithTimeout(ctx, step.Timeout)
		}

		output, err := rpe.executor(stepCtx, step, component)

		if cancel != nil {
			cancel()
		}

		if err == nil {
			result.Success = true
			result.Output = output
			result.Duration = time.Since(start)
			return result
		}
		lastErr = err

		if attempt < retries-1 {
			rpe.logger.Warn("step retry",
				"step", step.ID,
				"attempt", attempt+1,
				"error", err,
			)
		}
	}

	result.Success = false
	result.Error = lastErr.Error()
	result.Duration = time.Since(start)
	return result
}

// GetExecution returns a playbook execution by ID.
// Returns a deep copy to prevent data races with the execution goroutine.
func (rpe *RecoveryPlaybookEngine) GetExecution(id string) (*PlaybookExecution, bool) {
	rpe.mu.RLock()
	defer rpe.mu.RUnlock()

	for _, exec := range rpe.executions {
		if exec.ID == id {
			cp := *exec
			cp.StepsRun = make([]StepResult, len(exec.StepsRun))
			copy(cp.StepsRun, exec.StepsRun)
			return &cp, true
		}
	}
	return nil, false
}

// RecentExecutions returns the last N executions.
// Returns deep copies to prevent data races with the execution goroutine.
func (rpe *RecoveryPlaybookEngine) RecentExecutions(n int) []PlaybookExecution {
	rpe.mu.RLock()
	defer rpe.mu.RUnlock()

	total := len(rpe.executions)
	if total == 0 {
		return nil
	}
	start := total - n
	if start < 0 {
		start = 0
	}

	result := make([]PlaybookExecution, 0, n)
	for i := start; i < total; i++ {
		cp := *rpe.executions[i]
		cp.StepsRun = make([]StepResult, len(rpe.executions[i].StepsRun))
		copy(cp.StepsRun, rpe.executions[i].StepsRun)
		result = append(result, cp)
	}
	return result
}

// PlaybookCount returns the number of registered playbooks.
func (rpe *RecoveryPlaybookEngine) PlaybookCount() int {
	rpe.mu.RLock()
	defer rpe.mu.RUnlock()
	return len(rpe.playbooks)
}

// --- Built-in playbooks per ТЗ §7.1 ---

// DefaultPlaybooks returns the 3 built-in recovery playbooks.
func DefaultPlaybooks() []Playbook {
	return []Playbook{
		ComponentResurrectionPlaybook(),
		ConsensusRecoveryPlaybook(),
		CryptoRotationPlaybook(),
	}
}

// ComponentResurrectionPlaybook per ТЗ §7.1.1.
func ComponentResurrectionPlaybook() Playbook {
	return Playbook{
		ID:              "component-resurrection",
		Name:            "Component Resurrection",
		Version:         "1.0",
		TriggerMetric:   "component_offline",
		TriggerSeverity: "CRITICAL",
		DiagnosisChecks: []PlaybookStep{
			{ID: "diag-process", Name: "Check process exists", Type: "shell", Timeout: 5 * time.Second},
			{ID: "diag-crashes", Name: "Check recent crashes", Type: "shell", Timeout: 5 * time.Second},
			{ID: "diag-resources", Name: "Check resource exhaustion", Type: "prometheus", Timeout: 5 * time.Second},
			{ID: "diag-deps", Name: "Check dependency health", Type: "http", Timeout: 10 * time.Second},
		},
		Actions: []PlaybookStep{
			{ID: "capture-forensics", Name: "Capture forensics", Type: "shell", Timeout: 30 * time.Second, OnError: "continue"},
			{ID: "clear-resources", Name: "Clear temp resources", Type: "shell", Timeout: 10 * time.Second, OnError: "continue"},
			{ID: "restart-component", Name: "Restart component", Type: "systemd", Timeout: 60 * time.Second, OnError: "abort"},
			{ID: "verify-health", Name: "Verify health", Type: "http", Timeout: 30 * time.Second, Retries: 3, OnError: "abort"},
			{ID: "verify-metrics", Name: "Verify metrics", Type: "prometheus", Timeout: 30 * time.Second, OnError: "continue"},
			{ID: "notify-success", Name: "Notify SOC", Type: "api", Timeout: 5 * time.Second, OnError: "continue"},
		},
		RollbackActions: []PlaybookStep{
			{ID: "rb-safe-mode", Name: "Enter safe mode", Type: "api", Timeout: 10 * time.Second},
			{ID: "rb-notify", Name: "Notify architect", Type: "api", Timeout: 5 * time.Second},
		},
		SuccessCriteria: []string{
			"component_status == HEALTHY",
			"health_check_passed == true",
			"no_crashes_for_5min == true",
		},
	}
}

// ConsensusRecoveryPlaybook per ТЗ §7.1.2.
func ConsensusRecoveryPlaybook() Playbook {
	return Playbook{
		ID:              "consensus-recovery",
		Name:            "Distributed Consensus Recovery",
		Version:         "1.0",
		TriggerMetric:   "split_brain",
		TriggerSeverity: "CRITICAL",
		DiagnosisChecks: []PlaybookStep{
			{ID: "diag-peers", Name: "Check peer connectivity", Type: "api", Timeout: 10 * time.Second},
			{ID: "diag-sync", Name: "Check sync status", Type: "api", Timeout: 10 * time.Second},
			{ID: "diag-genome", Name: "Verify genome", Type: "api", Timeout: 5 * time.Second},
		},
		Actions: []PlaybookStep{
			{ID: "pause-writes", Name: "Pause all writes", Type: "api", Timeout: 10 * time.Second, OnError: "abort"},
			{ID: "elect-leader", Name: "Elect leader (Raft)", Type: "consensus", Timeout: 60 * time.Second, OnError: "abort"},
			{ID: "sync-state", Name: "Sync state from leader", Type: "api", Timeout: 300 * time.Second, OnError: "rollback"},
			{ID: "verify-consistency", Name: "Verify consistency", Type: "api", Timeout: 60 * time.Second, OnError: "abort"},
			{ID: "resume-writes", Name: "Resume writes", Type: "api", Timeout: 10 * time.Second, OnError: "abort"},
			{ID: "notify-cluster", Name: "Notify cluster", Type: "api", Timeout: 5 * time.Second, OnError: "continue"},
		},
		RollbackActions: []PlaybookStep{
			{ID: "rb-readonly", Name: "Maintain readonly", Type: "api", Timeout: 10 * time.Second},
			{ID: "rb-notify", Name: "Notify architect", Type: "api", Timeout: 5 * time.Second},
		},
		SuccessCriteria: []string{
			"leader_elected == true",
			"state_synced == true",
			"consistency_verified == true",
			"writes_resumed == true",
		},
	}
}

// CryptoRotationPlaybook per ТЗ §7.1.3.
func CryptoRotationPlaybook() Playbook {
	return Playbook{
		ID:              "crypto-rotation",
		Name:            "Cryptographic Key Rotation",
		Version:         "1.0",
		TriggerMetric:   "key_compromise",
		TriggerSeverity: "HIGH",
		DiagnosisChecks: []PlaybookStep{
			{ID: "diag-key-age", Name: "Check key age", Type: "crypto", Timeout: 5 * time.Second},
			{ID: "diag-usage", Name: "Check key usage anomaly", Type: "prometheus", Timeout: 5 * time.Second},
			{ID: "diag-tpm", Name: "Check TPM health", Type: "shell", Timeout: 5 * time.Second},
		},
		Actions: []PlaybookStep{
			{ID: "gen-keys", Name: "Generate new keys", Type: "crypto", Timeout: 30 * time.Second, OnError: "abort",
				Params: map[string]interface{}{"algorithm": "ECDSA-P256"},
			},
			{ID: "rotate-certs", Name: "Rotate mTLS certs", Type: "crypto", Timeout: 120 * time.Second, OnError: "rollback"},
			{ID: "resign-chain", Name: "Re-sign decision chain", Type: "crypto", Timeout: 300 * time.Second, OnError: "continue"},
			{ID: "verify-peers", Name: "Verify peer certs", Type: "api", Timeout: 60 * time.Second, OnError: "abort"},
			{ID: "revoke-old", Name: "Revoke old keys", Type: "crypto", Timeout: 30 * time.Second, OnError: "continue"},
			{ID: "notify-soc", Name: "Notify SOC", Type: "api", Timeout: 5 * time.Second, OnError: "continue"},
		},
		RollbackActions: []PlaybookStep{
			{ID: "rb-revert-keys", Name: "Revert to previous keys", Type: "crypto", Timeout: 30 * time.Second},
			{ID: "rb-notify", Name: "Notify architect", Type: "api", Timeout: 5 * time.Second},
		},
		SuccessCriteria: []string{
			"new_keys_generated == true",
			"certs_distributed == true",
			"peers_verified == true",
			"old_keys_revoked == true",
		},
	}
}
