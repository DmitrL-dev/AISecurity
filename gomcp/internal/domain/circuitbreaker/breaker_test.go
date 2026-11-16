package circuitbreaker

import (
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestNew_DefaultState(t *testing.T) {
	b := New(nil)
	assert.Equal(t, StateHealthy, b.CurrentState())
	assert.True(t, b.IsAllowed())
}

func TestBreaker_HealthyToDegraded(t *testing.T) {
	b := New(&Config{DegradeThreshold: 3})

	// 2 anomalies: still healthy.
	b.RecordAnomaly("test1")
	b.RecordAnomaly("test2")
	assert.Equal(t, StateHealthy, b.CurrentState())

	// 3rd anomaly: degrade.
	b.RecordAnomaly("test3")
	assert.Equal(t, StateDegraded, b.CurrentState())
	assert.True(t, b.IsAllowed(), "degraded still allows pipeline")
}

func TestBreaker_DegradedToOpen(t *testing.T) {
	b := New(&Config{DegradeThreshold: 1, OpenThreshold: 3})

	// Trigger degraded.
	halted := b.RecordAnomaly("trigger degrade")
	assert.False(t, halted)
	assert.Equal(t, StateDegraded, b.CurrentState())

	// More anomalies until open.
	b.RecordAnomaly("a2")
	halted = b.RecordAnomaly("a3")
	assert.True(t, halted)
	assert.Equal(t, StateOpen, b.CurrentState())
	assert.False(t, b.IsAllowed())
}

func TestBreaker_DegradedRecovery(t *testing.T) {
	b := New(&Config{DegradeThreshold: 1, RecoveryThreshold: 2})

	b.RecordAnomaly("trigger")
	assert.Equal(t, StateDegraded, b.CurrentState())

	// 1 clean: not enough.
	b.RecordClean()
	assert.Equal(t, StateDegraded, b.CurrentState())

	// 2 clean: recovery.
	b.RecordClean()
	assert.Equal(t, StateHealthy, b.CurrentState())
}

func TestBreaker_RecoveryResetByAnomaly(t *testing.T) {
	b := New(&Config{DegradeThreshold: 1, RecoveryThreshold: 3})

	b.RecordAnomaly("trigger")
	b.RecordClean()
	b.RecordClean()
	// Anomaly resets consecutive clean count.
	b.RecordAnomaly("reset")
	b.RecordClean()
	assert.Equal(t, StateDegraded, b.CurrentState(), "recovery should be reset")
}

func TestBreaker_ManualReset(t *testing.T) {
	b := New(&Config{DegradeThreshold: 1, OpenThreshold: 2})

	b.RecordAnomaly("a1")
	b.RecordAnomaly("a2")
	assert.Equal(t, StateOpen, b.CurrentState())

	b.Reset("external watchdog")
	assert.Equal(t, StateHealthy, b.CurrentState())
	assert.True(t, b.IsAllowed())
}

func TestBreaker_WatchdogAutoReset(t *testing.T) {
	b := New(&Config{
		DegradeThreshold: 1,
		OpenThreshold:    2,
		WatchdogTimeout:  10 * time.Millisecond,
	})

	b.RecordAnomaly("a1")
	b.RecordAnomaly("a2")
	assert.Equal(t, StateOpen, b.CurrentState())

	// Wait for watchdog.
	time.Sleep(15 * time.Millisecond)

	// RecordClean triggers watchdog check.
	state := b.RecordClean()
	assert.Equal(t, StateHealthy, state)
}

func TestBreaker_DegradedReducesIterations(t *testing.T) {
	b := New(&Config{DegradeThreshold: 1, DegradedMaxIterations: 2})

	assert.Equal(t, 5, b.MaxIterations(5), "healthy: full iterations")

	b.RecordAnomaly("trigger")
	assert.Equal(t, 2, b.MaxIterations(5), "degraded: reduced iterations")
}

func TestBreaker_Events(t *testing.T) {
	b := New(&Config{DegradeThreshold: 1, OpenThreshold: 2})

	b.RecordAnomaly("a1")
	b.RecordAnomaly("a2")
	b.Reset("test")

	events := b.Events()
	require.Len(t, events, 3) // HEALTHY→DEGRADED, DEGRADED→OPEN, OPEN→HEALTHY
	assert.Equal(t, StateHealthy, events[0].From)
	assert.Equal(t, StateDegraded, events[0].To)
	assert.Equal(t, StateDegraded, events[1].From)
	assert.Equal(t, StateOpen, events[1].To)
	assert.Equal(t, StateOpen, events[2].From)
	assert.Equal(t, StateHealthy, events[2].To)
}

func TestBreaker_GetStatus(t *testing.T) {
	b := New(nil)
	b.RecordAnomaly("test")

	s := b.GetStatus()
	assert.Equal(t, "HEALTHY", s.State)
	assert.Equal(t, 1, s.AnomalyCount)
	assert.Equal(t, 1, s.TotalAnomalies)
	assert.GreaterOrEqual(t, s.UptimeSeconds, 0.0)
}

func TestBreaker_StateString(t *testing.T) {
	assert.Equal(t, "HEALTHY", StateHealthy.String())
	assert.Equal(t, "DEGRADED", StateDegraded.String())
	assert.Equal(t, "OPEN", StateOpen.String())
	assert.Equal(t, "UNKNOWN", State(99).String())
}

func TestBreaker_ConcurrentSafety(t *testing.T) {
	b := New(&Config{DegradeThreshold: 100})
	done := make(chan struct{})

	go func() {
		for i := 0; i < 50; i++ {
			b.RecordAnomaly("concurrent")
		}
		done <- struct{}{}
	}()

	go func() {
		for i := 0; i < 50; i++ {
			b.RecordClean()
		}
		done <- struct{}{}
	}()

	go func() {
		for i := 0; i < 50; i++ {
			_ = b.GetStatus()
			_ = b.IsAllowed()
			_ = b.CurrentState()
		}
		done <- struct{}{}
	}()

	<-done
	<-done
	<-done
	// No race condition panic = pass.
}
