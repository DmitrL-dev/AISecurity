// Package watchdog implements the SEC-004 Watchdog Mesh Framework.
//
// Mutual monitoring between SOC agents (immune, sidecar, shield)
// with automatic restart escalation:
//
//  1. Heartbeat check every 30s
//  2. 3 missed heartbeats → attempt systemd restart
//  3. 3 failed restarts → eBPF isolation + CRITICAL alert
//  4. Architect notification via webhook
//
// Each agent registers as a peer and monitors all others.
package watchdog

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"sync"
	"time"
)

// PeerStatus defines the health state of a peer.
type PeerStatus string

const (
	StatusHealthy  PeerStatus = "HEALTHY"
	StatusDegraded PeerStatus = "DEGRADED"
	StatusOffline  PeerStatus = "OFFLINE"
	StatusIsolated PeerStatus = "ISOLATED"

	// DefaultHeartbeatInterval is the check interval.
	DefaultHeartbeatInterval = 30 * time.Second

	// MaxMissedBeforeRestart triggers auto-restart.
	MaxMissedBeforeRestart = 3

	// MaxRestartsBeforeIsolate triggers eBPF isolation.
	MaxRestartsBeforeIsolate = 3
)

// PeerHealth tracks the health state of a single peer agent.
type PeerHealth struct {
	Name           string     `json:"name"`
	Endpoint       string     `json:"endpoint"` // HTTP health endpoint
	Status         PeerStatus `json:"status"`
	LastSeen       time.Time  `json:"last_seen"`
	MissedCount    int        `json:"missed_count"`
	RestartCount   int        `json:"restart_count"`
	LastRestart    time.Time  `json:"last_restart,omitempty"`
	ResponseTimeMs int64      `json:"response_time_ms"`
}

// EscalationHandler is called when a peer requires escalation action.
type EscalationHandler func(action EscalationAction)

// EscalationAction describes what the mesh decided to do.
type EscalationAction struct {
	Timestamp time.Time `json:"timestamp"`
	PeerName  string    `json:"peer_name"`
	Action    string    `json:"action"` // restart, isolate, alert_architect
	Reason    string    `json:"reason"`
	Severity  string    `json:"severity"`
}

// Monitor is the watchdog mesh peer monitor.
type Monitor struct {
	mu         sync.RWMutex
	selfName   string
	peers      map[string]*PeerHealth
	interval   time.Duration
	handlers   []EscalationHandler
	httpClient *http.Client
	logger     *slog.Logger
	stats      MonitorStats
}

// MonitorStats tracks mesh health metrics.
type MonitorStats struct {
	mu              sync.Mutex
	TotalChecks     int64     `json:"total_checks"`
	TotalMisses     int64     `json:"total_misses"`
	TotalRestarts   int64     `json:"total_restarts"`
	TotalIsolations int64     `json:"total_isolations"`
	StartedAt       time.Time `json:"started_at"`
	PeerCount       int       `json:"peer_count"`
}

// NewMonitor creates a new watchdog mesh monitor.
func NewMonitor(selfName string) *Monitor {
	return &Monitor{
		selfName: selfName,
		peers:    make(map[string]*PeerHealth),
		interval: DefaultHeartbeatInterval,
		httpClient: &http.Client{
			Timeout: 5 * time.Second,
		},
		logger: slog.Default().With("component", "sec-004-watchdog", "self", selfName),
		stats: MonitorStats{
			StartedAt: time.Now(),
		},
	}
}

// RegisterPeer adds a peer agent to the monitoring mesh.
func (m *Monitor) RegisterPeer(name, endpoint string) {
	m.mu.Lock()
	defer m.mu.Unlock()

	m.peers[name] = &PeerHealth{
		Name:     name,
		Endpoint: endpoint,
		Status:   StatusHealthy,
		LastSeen: time.Now(),
	}
	m.stats.PeerCount = len(m.peers)
	m.logger.Info("peer registered", "peer", name, "endpoint", endpoint)
}

// OnEscalation registers a handler for escalation events.
func (m *Monitor) OnEscalation(h EscalationHandler) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.handlers = append(m.handlers, h)
}

// Start begins the heartbeat monitoring loop.
func (m *Monitor) Start(ctx context.Context) {
	m.logger.Info("watchdog mesh started",
		"interval", m.interval,
		"peers", m.peerNames(),
	)

	ticker := time.NewTicker(m.interval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			m.logger.Info("watchdog mesh stopped")
			return
		case <-ticker.C:
			m.checkAllPeers(ctx)
		}
	}
}

// checkAllPeers performs a health check on every registered peer.
func (m *Monitor) checkAllPeers(ctx context.Context) {
	m.mu.RLock()
	peers := make([]*PeerHealth, 0, len(m.peers))
	for _, p := range m.peers {
		peers = append(peers, p)
	}
	m.mu.RUnlock()

	for _, peer := range peers {
		m.checkPeer(ctx, peer)
	}
}

// checkPeer performs a single health check on a peer.
func (m *Monitor) checkPeer(ctx context.Context, peer *PeerHealth) {
	m.stats.mu.Lock()
	m.stats.TotalChecks++
	m.stats.mu.Unlock()

	start := time.Now()
	healthy := m.pingPeer(ctx, peer.Endpoint)
	elapsed := time.Since(start)

	// Mutate peer state under the lock, but fire escalation handlers AFTER
	// releasing it. Handlers are caller-supplied and may legitimately call
	// back into the Monitor (GetPeerStatus/AllPeers/Stats/RegisterPeer);
	// invoking them while holding m.mu would self-deadlock. action stays nil
	// when there is nothing to escalate.
	var action *EscalationAction

	m.mu.Lock()
	if healthy {
		peer.Status = StatusHealthy
		peer.LastSeen = time.Now()
		peer.MissedCount = 0
		peer.ResponseTimeMs = elapsed.Milliseconds()
		m.mu.Unlock()
		return
	}

	// Missed heartbeat.
	peer.MissedCount++
	m.stats.mu.Lock()
	m.stats.TotalMisses++
	m.stats.mu.Unlock()

	m.logger.Warn("peer missed heartbeat",
		"peer", peer.Name,
		"missed", peer.MissedCount,
		"last_seen", peer.LastSeen,
	)

	// Escalation ladder.
	switch {
	case peer.MissedCount >= MaxMissedBeforeRestart && peer.RestartCount >= MaxRestartsBeforeIsolate:
		// Level 3: Isolate via eBPF + alert architect.
		peer.Status = StatusIsolated
		m.stats.mu.Lock()
		m.stats.TotalIsolations++
		m.stats.mu.Unlock()

		action = &EscalationAction{
			Timestamp: time.Now(),
			PeerName:  peer.Name,
			Action:    "isolate",
			Reason:    fmt.Sprintf("peer %s offline after %d restarts — eBPF isolation engaged", peer.Name, peer.RestartCount),
			Severity:  "CRITICAL",
		}

	case peer.MissedCount >= MaxMissedBeforeRestart:
		// Level 2: Attempt restart.
		peer.Status = StatusOffline
		peer.RestartCount++
		peer.LastRestart = time.Now()
		m.stats.mu.Lock()
		m.stats.TotalRestarts++
		m.stats.mu.Unlock()

		action = &EscalationAction{
			Timestamp: time.Now(),
			PeerName:  peer.Name,
			Action:    "restart",
			Reason:    fmt.Sprintf("peer %s missed %d heartbeats — restart attempt %d", peer.Name, peer.MissedCount, peer.RestartCount),
			Severity:  "HIGH",
		}
		peer.MissedCount = 0 // Reset after restart attempt.

	default:
		// Level 1: Mark degraded.
		peer.Status = StatusDegraded
		action = &EscalationAction{
			Timestamp: time.Now(),
			PeerName:  peer.Name,
			Action:    "alert",
			Reason:    fmt.Sprintf("peer %s missed %d heartbeat(s)", peer.Name, peer.MissedCount),
			Severity:  "MEDIUM",
		}
	}
	m.mu.Unlock()

	m.escalate(*action)
}

// pingPeer sends an HTTP GET to the peer's health endpoint.
func (m *Monitor) pingPeer(ctx context.Context, endpoint string) bool {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, endpoint, nil)
	if err != nil {
		return false
	}

	resp, err := m.httpClient.Do(req)
	if err != nil {
		return false
	}
	defer resp.Body.Close()

	return resp.StatusCode == http.StatusOK
}

// escalate notifies all registered handlers and logs the action.
func (m *Monitor) escalate(action EscalationAction) {
	m.logger.Warn("WATCHDOG ESCALATION",
		"peer", action.PeerName,
		"action", action.Action,
		"severity", action.Severity,
		"reason", action.Reason,
	)

	// Snapshot handlers under the read lock, then invoke them WITHOUT any lock
	// held so a handler may safely call back into the Monitor.
	m.mu.RLock()
	handlers := make([]EscalationHandler, len(m.handlers))
	copy(handlers, m.handlers)
	m.mu.RUnlock()
	for _, h := range handlers {
		h(action)
	}
}

// PeerStatus returns the current status of a specific peer.
func (m *Monitor) GetPeerStatus(name string) (*PeerHealth, bool) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	p, ok := m.peers[name]
	if !ok {
		return nil, false
	}
	cp := *p // Return a copy.
	return &cp, true
}

// AllPeers returns a snapshot of all peer health states.
func (m *Monitor) AllPeers() []PeerHealth {
	m.mu.RLock()
	defer m.mu.RUnlock()

	result := make([]PeerHealth, 0, len(m.peers))
	for _, p := range m.peers {
		result = append(result, *p)
	}
	return result
}

// Stats returns current watchdog metrics.
func (m *Monitor) Stats() MonitorStats {
	m.stats.mu.Lock()
	defer m.stats.mu.Unlock()
	return MonitorStats{
		TotalChecks:     m.stats.TotalChecks,
		TotalMisses:     m.stats.TotalMisses,
		TotalRestarts:   m.stats.TotalRestarts,
		TotalIsolations: m.stats.TotalIsolations,
		StartedAt:       m.stats.StartedAt,
		PeerCount:       m.stats.PeerCount,
	}
}

// ServeHTTP provides the mesh status as JSON (for embedding in other servers).
func (m *Monitor) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]any{
		"self":  m.selfName,
		"peers": m.AllPeers(),
		"stats": m.Stats(),
	})
}

// peerNames returns a list of registered peer names.
func (m *Monitor) peerNames() []string {
	names := make([]string, 0, len(m.peers))
	for n := range m.peers {
		names = append(names, n)
	}
	return names
}
