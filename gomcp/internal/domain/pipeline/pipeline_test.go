package pipeline

import (
	"context"
	"testing"

	"github.com/stretchr/testify/assert"

	"github.com/syntrex/gomcp/internal/domain/circuitbreaker"
	"github.com/syntrex/gomcp/internal/domain/entropy"
	"github.com/syntrex/gomcp/internal/domain/oracle"
)

func TestPipeline_AllowsNormalText(t *testing.T) {
	p := New(
		entropy.NewGate(nil),
		nil, // no distiller
		oracle.New(oracle.DefaultRules()),
		circuitbreaker.New(nil),
		&Config{SkipDistill: true},
	)

	r := p.Process(context.Background(), "read user profile data")
	assert.True(t, r.IsAllowed)
	assert.False(t, r.IsBlocked)
	assert.Equal(t, StageComplete, r.Stage)
	assert.Equal(t, "HEALTHY", r.CircuitState)
}

func TestPipeline_BlocksHighEntropy(t *testing.T) {
	p := New(
		entropy.NewGate(&entropy.GateConfig{MaxEntropy: 3.0}),
		nil,
		oracle.New(oracle.DefaultRules()),
		circuitbreaker.New(nil),
		&Config{SkipDistill: true},
	)

	r := p.Process(context.Background(), "x7#kQ9!mZ2$pW4&nR6*jL8@cF0^tB3yH5%vD1")
	assert.True(t, r.IsBlocked)
	assert.Equal(t, StageEntropy, r.BlockStage)
	assert.Contains(t, r.BlockReason, "chaotic")
}

func TestPipeline_OracleDeniesExec(t *testing.T) {
	p := New(
		entropy.NewGate(nil),
		nil,
		oracle.New(oracle.DefaultRules()),
		circuitbreaker.New(nil),
		&Config{SkipDistill: true},
	)

	r := p.Process(context.Background(), "execute shell command rm -rf slash")
	assert.True(t, r.IsBlocked)
	assert.Equal(t, StageOracle, r.BlockStage)
	assert.Contains(t, r.BlockReason, "denied")
}

func TestPipeline_CircuitBreakerBlocks(t *testing.T) {
	breaker := circuitbreaker.New(&circuitbreaker.Config{
		DegradeThreshold: 1,
		OpenThreshold:    2,
	})

	p := New(
		entropy.NewGate(nil),
		nil,
		oracle.New(oracle.DefaultRules()),
		breaker,
		&Config{SkipDistill: true},
	)

	// Force breaker to OPEN state.
	breaker.RecordAnomaly("test1")
	breaker.RecordAnomaly("test2")
	assert.Equal(t, circuitbreaker.StateOpen, breaker.CurrentState())

	r := p.Process(context.Background(), "read data")
	assert.True(t, r.IsBlocked)
	assert.Equal(t, StageBlocked, r.BlockStage)
	assert.Contains(t, r.BlockReason, "circuit breaker")
}

func TestPipeline_AnomaliesDegradeCircuit(t *testing.T) {
	breaker := circuitbreaker.New(&circuitbreaker.Config{DegradeThreshold: 2})
	p := New(
		entropy.NewGate(nil),
		nil,
		oracle.New(oracle.DefaultRules()),
		breaker,
		&Config{SkipDistill: true},
	)

	// Two denied actions → 2 anomalies → degrade.
	p.Process(context.Background(), "execute shell command one")
	p.Process(context.Background(), "run another shell command two")
	assert.Equal(t, circuitbreaker.StateDegraded, breaker.CurrentState())
}

func TestPipeline_CleanSignalsRecover(t *testing.T) {
	breaker := circuitbreaker.New(&circuitbreaker.Config{
		DegradeThreshold:  1,
		RecoveryThreshold: 2,
	})

	p := New(
		entropy.NewGate(nil),
		nil,
		oracle.New(oracle.DefaultRules()),
		breaker,
		&Config{SkipDistill: true},
	)

	// Trigger degraded.
	breaker.RecordAnomaly("test")
	assert.Equal(t, circuitbreaker.StateDegraded, breaker.CurrentState())

	// Clean signals recover.
	p.Process(context.Background(), "read data from storage")
	p.Process(context.Background(), "list all available items")
	assert.Equal(t, circuitbreaker.StateHealthy, breaker.CurrentState())
}

func TestPipeline_NoGateNoOracle(t *testing.T) {
	p := New(nil, nil, nil, circuitbreaker.New(nil), nil)
	r := p.Process(context.Background(), "anything goes")
	assert.True(t, r.IsAllowed)
	assert.Equal(t, StageComplete, r.Stage)
}

func TestPipeline_DurationMeasured(t *testing.T) {
	p := New(
		entropy.NewGate(nil),
		nil,
		oracle.New(oracle.DefaultRules()),
		circuitbreaker.New(nil),
		&Config{SkipDistill: true},
	)
	r := p.Process(context.Background(), "read something")
	assert.GreaterOrEqual(t, r.DurationMs, int64(0))
}
