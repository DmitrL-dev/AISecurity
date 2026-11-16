// Package circuitbreaker implements a state machine that controls
// the health of recursive pipelines (DIP H1.1).
//
// States:
//
//	HEALTHY   → Pipeline operates normally
//	DEGRADED  → Enhanced logging, reduced max iterations
//	OPEN      → Pipeline halted, requires external reset
//
// Transitions:
//
//	HEALTHY  → DEGRADED  when anomaly count reaches threshold
//	DEGRADED → OPEN      when consecutive anomalies exceed limit
//	DEGRADED → HEALTHY   when recovery conditions are met
//	OPEN     → HEALTHY   when external watchdog resets
package circuitbreaker

import (
	"fmt"
	"sync"
	"time"
)

// State represents the circuit breaker state.
type State int

const (
	StateHealthy  State = iota // Normal operation
	StateDegraded              // Reduced capacity, enhanced monitoring
	StateOpen                  // Pipeline halted
)

// String returns the state name.
func (s State) String() string {
	switch s {
	case StateHealthy:
		return "HEALTHY"
	case StateDegraded:
		return "DEGRADED"
	case StateOpen:
		return "OPEN"
	default:
		return "UNKNOWN"
	}
}

// Config configures the circuit breaker.
type Config struct {
	// DegradeThreshold: anomalies before transitioning HEALTHY → DEGRADED.
	DegradeThreshold int // default: 3

	// OpenThreshold: consecutive anomalies in DEGRADED before → OPEN.
	OpenThreshold int // default: 5

	// RecoveryThreshold: consecutive clean checks in DEGRADED before → HEALTHY.
	RecoveryThreshold int // default: 3

	// WatchdogTimeout: auto-reset from OPEN after this duration.
	// 0 = no auto-reset (requires manual reset).
	WatchdogTimeout time.Duration // default: 5m

	// DegradedMaxIterations: reduced max iterations in DEGRADED state.
	DegradedMaxIterations int // default: 2
}

// DefaultConfig returns sensible defaults.
func DefaultConfig() Config {
	return Config{
		DegradeThreshold:      3,
		OpenThreshold:         5,
		RecoveryThreshold:     3,
		WatchdogTimeout:       5 * time.Minute,
		DegradedMaxIterations: 2,
	}
}

// Event represents a recorded state transition.
type Event struct {
	From      State     `json:"from"`
	To        State     `json:"to"`
	Reason    string    `json:"reason"`
	Timestamp time.Time `json:"timestamp"`
}

// Status holds the current circuit breaker status.
type Status struct {
	State            string  `json:"state"`
	AnomalyCount     int     `json:"anomaly_count"`
	ConsecutiveClean int     `json:"consecutive_clean"`
	TotalAnomalies   int     `json:"total_anomalies"`
	TotalResets      int     `json:"total_resets"`
	MaxIterationsNow int     `json:"max_iterations_now"`
	LastTransition   *Event  `json:"last_transition,omitempty"`
	UptimeSeconds    float64 `json:"uptime_seconds"`
}

// Breaker implements the circuit breaker state machine.
type Breaker struct {
	mu               sync.RWMutex
	cfg              Config
	state            State
	anomalyCount     int // total anomalies in current state
	consecutiveClean int // consecutive clean checks
	totalAnomalies   int // lifetime counter
	totalResets      int // lifetime counter
	events           []Event
	openedAt         time.Time // when state went OPEN
	createdAt        time.Time
}

// New creates a new circuit breaker in HEALTHY state.
func New(cfg *Config) *Breaker {
	c := DefaultConfig()
	if cfg != nil {
		if cfg.DegradeThreshold > 0 {
			c.DegradeThreshold = cfg.DegradeThreshold
		}
		if cfg.OpenThreshold > 0 {
			c.OpenThreshold = cfg.OpenThreshold
		}
		if cfg.RecoveryThreshold > 0 {
			c.RecoveryThreshold = cfg.RecoveryThreshold
		}
		if cfg.WatchdogTimeout > 0 {
			c.WatchdogTimeout = cfg.WatchdogTimeout
		}
		if cfg.DegradedMaxIterations > 0 {
			c.DegradedMaxIterations = cfg.DegradedMaxIterations
		}
	}
	return &Breaker{
		cfg:       c,
		state:     StateHealthy,
		createdAt: time.Now(),
	}
}

// RecordAnomaly records an anomalous signal (entropy spike, divergence, etc).
// Returns true if the pipeline should be halted (state is OPEN).
func (b *Breaker) RecordAnomaly(reason string) bool {
	b.mu.Lock()
	defer b.mu.Unlock()

	b.anomalyCount++
	b.totalAnomalies++
	b.consecutiveClean = 0

	switch b.state {
	case StateHealthy:
		if b.anomalyCount >= b.cfg.DegradeThreshold {
			b.transition(StateDegraded,
				fmt.Sprintf("anomaly threshold reached (%d): %s",
					b.anomalyCount, reason))
		}
	case StateDegraded:
		if b.anomalyCount >= b.cfg.OpenThreshold {
			b.transition(StateOpen,
				fmt.Sprintf("open threshold reached (%d): %s",
					b.anomalyCount, reason))
			b.openedAt = time.Now()
		}
	case StateOpen:
		// Already open, no further transitions from anomalies.
	}

	return b.state == StateOpen
}

// RecordClean records a clean signal (normal operation).
// Returns the current state.
func (b *Breaker) RecordClean() State {
	b.mu.Lock()
	defer b.mu.Unlock()

	b.consecutiveClean++

	// Check watchdog timeout for OPEN state.
	if b.state == StateOpen && b.cfg.WatchdogTimeout > 0 {
		if !b.openedAt.IsZero() && time.Since(b.openedAt) >= b.cfg.WatchdogTimeout {
			b.reset("watchdog timeout expired")
			return b.state
		}
	}

	// Recovery from DEGRADED → HEALTHY.
	if b.state == StateDegraded && b.consecutiveClean >= b.cfg.RecoveryThreshold {
		b.transition(StateHealthy, fmt.Sprintf(
			"recovered after %d consecutive clean signals",
			b.consecutiveClean))
		b.anomalyCount = 0
		b.consecutiveClean = 0
	}

	return b.state
}

// Reset forces the circuit breaker back to HEALTHY (external watchdog).
func (b *Breaker) Reset(reason string) {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.reset(reason)
}

// reset performs the actual reset (must hold lock).
func (b *Breaker) reset(reason string) {
	if b.state != StateHealthy {
		b.transition(StateHealthy, "reset: "+reason)
	}
	b.anomalyCount = 0
	b.consecutiveClean = 0
	b.totalResets++
}

// State returns the current state.
func (b *Breaker) CurrentState() State {
	b.mu.RLock()
	defer b.mu.RUnlock()
	return b.state
}

// IsAllowed returns true if the pipeline should proceed.
func (b *Breaker) IsAllowed() bool {
	b.mu.RLock()
	defer b.mu.RUnlock()
	return b.state != StateOpen
}

// MaxIterations returns the allowed max iterations in current state.
func (b *Breaker) MaxIterations(normalMax int) int {
	b.mu.RLock()
	defer b.mu.RUnlock()
	if b.state == StateDegraded {
		return b.cfg.DegradedMaxIterations
	}
	return normalMax
}

// GetStatus returns the current status summary.
func (b *Breaker) GetStatus() Status {
	b.mu.RLock()
	defer b.mu.RUnlock()

	s := Status{
		State:            b.state.String(),
		AnomalyCount:     b.anomalyCount,
		ConsecutiveClean: b.consecutiveClean,
		TotalAnomalies:   b.totalAnomalies,
		TotalResets:      b.totalResets,
		MaxIterationsNow: b.MaxIterationsLocked(5),
		UptimeSeconds:    time.Since(b.createdAt).Seconds(),
	}
	if len(b.events) > 0 {
		last := b.events[len(b.events)-1]
		s.LastTransition = &last
	}
	return s
}

// MaxIterationsLocked returns max iterations without acquiring lock (caller must hold RLock).
func (b *Breaker) MaxIterationsLocked(normalMax int) int {
	if b.state == StateDegraded {
		return b.cfg.DegradedMaxIterations
	}
	return normalMax
}

// Events returns the transition history.
func (b *Breaker) Events() []Event {
	b.mu.RLock()
	defer b.mu.RUnlock()
	events := make([]Event, len(b.events))
	copy(events, b.events)
	return events
}

// transition records a state change (must hold lock).
func (b *Breaker) transition(to State, reason string) {
	event := Event{
		From:      b.state,
		To:        to,
		Reason:    reason,
		Timestamp: time.Now(),
	}
	b.events = append(b.events, event)
	b.state = to
}
