package alert_test

import (
	"testing"
	"time"

	"github.com/syntrex/gomcp/internal/domain/alert"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestAlert_New(t *testing.T) {
	a := alert.New(alert.SourceEntropy, alert.SeverityWarning, "entropy spike", 5)
	assert.Contains(t, a.ID, "alert-")
	assert.Equal(t, alert.SourceEntropy, a.Source)
	assert.Equal(t, alert.SeverityWarning, a.Severity)
	assert.Equal(t, "entropy spike", a.Message)
	assert.Equal(t, 5, a.Cycle)
	assert.False(t, a.Resolved)
	assert.WithinDuration(t, time.Now(), a.Timestamp, time.Second)
}

func TestAlert_WithValue(t *testing.T) {
	a := alert.New(alert.SourceEntropy, alert.SeverityCritical, "high", 1).WithValue(0.95)
	assert.Equal(t, 0.95, a.Value)
}

func TestSeverity_String(t *testing.T) {
	assert.Equal(t, "INFO", alert.SeverityInfo.String())
	assert.Equal(t, "WARNING", alert.SeverityWarning.String())
	assert.Equal(t, "CRITICAL", alert.SeverityCritical.String())
}

func TestSeverity_Icon(t *testing.T) {
	assert.Equal(t, "🟢", alert.SeverityInfo.Icon())
	assert.Equal(t, "⚠️", alert.SeverityWarning.Icon())
	assert.Equal(t, "🔴", alert.SeverityCritical.Icon())
}

func TestBus_EmitAndRecent(t *testing.T) {
	bus := alert.NewBus(10)

	bus.Emit(alert.New(alert.SourceSystem, alert.SeverityInfo, "msg1", 1))
	bus.Emit(alert.New(alert.SourceSystem, alert.SeverityWarning, "msg2", 2))
	bus.Emit(alert.New(alert.SourceSystem, alert.SeverityCritical, "msg3", 3))

	recent := bus.Recent(2)
	require.Len(t, recent, 2)
	assert.Equal(t, "msg3", recent[0].Message, "newest first")
	assert.Equal(t, "msg2", recent[1].Message)
}

func TestBus_RecentOverflow(t *testing.T) {
	bus := alert.NewBus(3)

	for i := 0; i < 5; i++ {
		bus.Emit(alert.New(alert.SourceSystem, alert.SeverityInfo, "m", i))
	}

	assert.Equal(t, 3, bus.Count(), "count capped at capacity")
	recent := bus.Recent(10) // request more than capacity
	assert.Len(t, recent, 3, "returns at most capacity")
}

func TestBus_Subscribe(t *testing.T) {
	bus := alert.NewBus(10)
	ch := bus.Subscribe(5)

	bus.Emit(alert.New(alert.SourceGenome, alert.SeverityCritical, "genome drift", 1))

	select {
	case a := <-ch:
		assert.Equal(t, "genome drift", a.Message)
	case <-time.After(time.Second):
		t.Fatal("subscriber did not receive alert")
	}
}

func TestBus_MaxSeverity(t *testing.T) {
	bus := alert.NewBus(10)
	bus.Emit(alert.New(alert.SourceSystem, alert.SeverityInfo, "ok", 1))
	bus.Emit(alert.New(alert.SourceEntropy, alert.SeverityWarning, "spike", 2))
	bus.Emit(alert.New(alert.SourceSystem, alert.SeverityInfo, "ok2", 3))

	assert.Equal(t, alert.SeverityWarning, bus.MaxSeverity(5))
}

func TestBus_Empty(t *testing.T) {
	bus := alert.NewBus(10)
	assert.Empty(t, bus.Recent(5))
	assert.Equal(t, 0, bus.Count())
	assert.Equal(t, alert.SeverityInfo, bus.MaxSeverity(5))
}
