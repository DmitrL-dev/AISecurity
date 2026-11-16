package pivot

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

type mockRecorder struct {
	decisions []string
}

func (m *mockRecorder) RecordDecision(module, decision, reason string) {
	m.decisions = append(m.decisions, module+":"+decision)
}

func TestEngine_BasicFSM(t *testing.T) {
	rec := &mockRecorder{}
	e := NewEngine(DefaultConfig(), rec)

	e.StartChain("test goal")
	assert.Equal(t, StateRecon, e.CurrentState())
	assert.Len(t, rec.decisions, 1) // CHAIN_START

	e.Step("scan ports", "found port 443")
	e.Transition(true)
	assert.Equal(t, StateHypothesis, e.CurrentState())

	e.Step("try SQL injection", "planned")
	e.Transition(true)
	assert.Equal(t, StateAction, e.CurrentState())

	e.Step("execute sqli", "blocked by WAF")
	e.Transition(true)
	assert.Equal(t, StateObserve, e.CurrentState())

	// Failure → dead end.
	e.Transition(false)
	assert.Equal(t, StateDeadEnd, e.CurrentState())

	// Backtrack to hypothesis.
	e.Transition(true)
	assert.Equal(t, StateHypothesis, e.CurrentState())
}

func TestEngine_Success(t *testing.T) {
	e := NewEngine(DefaultConfig(), nil)
	e.StartChain("goal")

	e.Transition(true) // RECON → HYPOTHESIS
	e.Transition(true) // HYPOTHESIS → ACTION
	e.Transition(true) // ACTION → OBSERVE
	e.Transition(true) // OBSERVE → SUCCESS (success=true)

	assert.Equal(t, StateSuccess, e.CurrentState())
}

func TestEngine_MaxAttempts(t *testing.T) {
	e := NewEngine(Config{MaxAttempts: 3}, nil)
	e.StartChain("goal")

	for i := 0; i < 3; i++ {
		_, done := e.Step("action", "result")
		if done {
			break
		}
	}

	assert.Equal(t, StateDeadEnd, e.CurrentState())
	assert.True(t, e.IsTerminal())
}

func TestEngine_ChainRecord(t *testing.T) {
	e := NewEngine(DefaultConfig(), nil)
	e.StartChain("test chain")

	e.Step("step1", "result1")
	e.Step("step2", "result2")

	chain := e.GetChain()
	require.NotNil(t, chain)
	assert.Equal(t, "test chain", chain.Goal)
	assert.Len(t, chain.Steps, 2)
	assert.Equal(t, 50, chain.MaxAttempts)
}

func TestEngine_DecisionLogging(t *testing.T) {
	rec := &mockRecorder{}
	e := NewEngine(DefaultConfig(), rec)

	e.StartChain("goal")
	e.Step("action", "result")
	e.Transition(true)

	// Should have: CHAIN_START, STEP_RECON, STATE_TRANSITION
	assert.GreaterOrEqual(t, len(rec.decisions), 3)
	assert.Contains(t, rec.decisions[0], "CHAIN_START")
	assert.Contains(t, rec.decisions[1], "STEP_RECON")
	assert.Contains(t, rec.decisions[2], "STATE_TRANSITION")
}

func TestState_String(t *testing.T) {
	assert.Equal(t, "RECON", StateRecon.String())
	assert.Equal(t, "HYPOTHESIS", StateHypothesis.String())
	assert.Equal(t, "ACTION", StateAction.String())
	assert.Equal(t, "OBSERVE", StateObserve.String())
	assert.Equal(t, "SUCCESS", StateSuccess.String())
	assert.Equal(t, "DEAD_END", StateDeadEnd.String())
}

func TestDefaultConfig(t *testing.T) {
	cfg := DefaultConfig()
	assert.Equal(t, 50, cfg.MaxAttempts)
}
