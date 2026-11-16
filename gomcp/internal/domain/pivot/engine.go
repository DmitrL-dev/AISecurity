// Package pivot implements the autonomous multi-step attack engine (v3.8 Strike Force).
// Module 10 in Orchestrator: finite state machine for iterative offensive operations.
package pivot

import (
	"fmt"
	"sync"
	"time"
)

// State represents the Pivot Engine FSM state.
type State uint8

const (
	StateRecon      State = iota // Reconnaissance: gather target info
	StateHypothesis              // Generate attack hypotheses
	StateAction                  // Execute micro-exploit attempt
	StateObserve                 // Analyze result of action
	StateSuccess                 // Goal achieved
	StateDeadEnd                 // Dead end → return to Hypothesis
)

// String returns the human-readable state name.
func (s State) String() string {
	switch s {
	case StateRecon:
		return "RECON"
	case StateHypothesis:
		return "HYPOTHESIS"
	case StateAction:
		return "ACTION"
	case StateObserve:
		return "OBSERVE"
	case StateSuccess:
		return "SUCCESS"
	case StateDeadEnd:
		return "DEAD_END"
	default:
		return "UNKNOWN"
	}
}

// StepResult captures the outcome of a single pivot step.
type StepResult struct {
	StepNum   int       `json:"step_num"`
	State     State     `json:"state"`
	Action    string    `json:"action"`
	Result    string    `json:"result"`
	Timestamp time.Time `json:"timestamp"`
}

// Chain is a complete attack chain execution record.
type Chain struct {
	Goal        string       `json:"goal"`
	Steps       []StepResult `json:"steps"`
	FinalState  State        `json:"final_state"`
	MaxAttempts int          `json:"max_attempts"`
	StartedAt   time.Time    `json:"started_at"`
	FinishedAt  time.Time    `json:"finished_at"`
}

// DecisionRecorder records tamper-evident decisions.
type DecisionRecorder interface {
	RecordDecision(module, decision, reason string)
}

// Engine is the Pivot Engine FSM (Module 10, v3.8).
// Executes multi-step attack chains with automatic backtracking
// on dead ends and configurable attempt limits.
type Engine struct {
	mu          sync.Mutex
	state       State
	maxAttempts int
	attempts    int
	recorder    DecisionRecorder
	chain       *Chain
}

// Config holds Pivot Engine configuration.
type Config struct {
	MaxAttempts int // Max total steps before forced termination (default: 50)
}

// DefaultConfig returns secure defaults.
func DefaultConfig() Config {
	return Config{MaxAttempts: 50}
}

// NewEngine creates a new Pivot Engine.
func NewEngine(cfg Config, recorder DecisionRecorder) *Engine {
	if cfg.MaxAttempts <= 0 {
		cfg.MaxAttempts = 50
	}
	return &Engine{
		state:       StateRecon,
		maxAttempts: cfg.MaxAttempts,
		recorder:    recorder,
	}
}

// StartChain begins a new attack chain for the given goal.
func (e *Engine) StartChain(goal string) {
	e.mu.Lock()
	defer e.mu.Unlock()

	e.state = StateRecon
	e.attempts = 0
	e.chain = &Chain{
		Goal:        goal,
		MaxAttempts: e.maxAttempts,
		StartedAt:   time.Now(),
	}

	if e.recorder != nil {
		e.recorder.RecordDecision("PIVOT", "CHAIN_START", fmt.Sprintf("goal=%s max=%d", goal, e.maxAttempts))
	}
}

// Step advances the FSM by one step. Returns the result and whether the chain is complete.
func (e *Engine) Step(action, result string) (StepResult, bool) {
	e.mu.Lock()
	defer e.mu.Unlock()

	e.attempts++
	step := StepResult{
		StepNum:   e.attempts,
		State:     e.state,
		Action:    action,
		Result:    result,
		Timestamp: time.Now(),
	}

	if e.chain != nil {
		e.chain.Steps = append(e.chain.Steps, step)
	}

	// Record to decisions.log.
	if e.recorder != nil {
		e.recorder.RecordDecision("PIVOT", fmt.Sprintf("STEP_%s", e.state),
			fmt.Sprintf("step=%d action=%s result=%s", e.attempts, action, truncate(result, 80)))
	}

	// Check termination conditions.
	if e.attempts >= e.maxAttempts {
		e.state = StateDeadEnd
		e.finishChain()
		return step, true
	}

	return step, false
}

// Transition moves the FSM to the next state based on current state and outcome.
func (e *Engine) Transition(success bool) {
	e.mu.Lock()
	defer e.mu.Unlock()

	prev := e.state
	switch e.state {
	case StateRecon:
		e.state = StateHypothesis
	case StateHypothesis:
		e.state = StateAction
	case StateAction:
		e.state = StateObserve
	case StateObserve:
		if success {
			e.state = StateSuccess
		} else {
			e.state = StateDeadEnd
		}
	case StateDeadEnd:
		// Backtrack to hypothesis generation.
		e.state = StateHypothesis
	case StateSuccess:
		// Terminal state — no transition.
	}

	if e.recorder != nil && prev != e.state {
		e.recorder.RecordDecision("PIVOT", "STATE_TRANSITION",
			fmt.Sprintf("%s → %s (success=%v)", prev, e.state, success))
	}
}

// Complete marks the chain as successfully completed.
func (e *Engine) Complete() {
	e.mu.Lock()
	defer e.mu.Unlock()
	e.state = StateSuccess
	e.finishChain()
}

// State returns the current FSM state.
func (e *Engine) CurrentState() State {
	e.mu.Lock()
	defer e.mu.Unlock()
	return e.state
}

// Attempts returns the number of steps taken.
func (e *Engine) Attempts() int {
	e.mu.Lock()
	defer e.mu.Unlock()
	return e.attempts
}

// GetChain returns a snapshot copy of the current chain record (nil if none).
//
// A copy is returned rather than the internal *Chain because Step appends to
// e.chain.Steps under the lock; handing out the live pointer would let the
// caller read Steps concurrently with that append (data race) once this method
// releases the lock.
func (e *Engine) GetChain() *Chain {
	e.mu.Lock()
	defer e.mu.Unlock()
	if e.chain == nil {
		return nil
	}
	cp := *e.chain
	cp.Steps = append([]StepResult(nil), e.chain.Steps...)
	return &cp
}

// IsTerminal returns true if the engine is in a terminal state.
func (e *Engine) IsTerminal() bool {
	e.mu.Lock()
	defer e.mu.Unlock()
	return e.state == StateSuccess || (e.state == StateDeadEnd && e.attempts >= e.maxAttempts)
}

func (e *Engine) finishChain() {
	if e.chain != nil {
		e.chain.FinalState = e.state
		e.chain.FinishedAt = time.Now()
	}
}

func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n] + "..."
}
