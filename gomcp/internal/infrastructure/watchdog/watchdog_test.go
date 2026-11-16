package watchdog

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestRegisterPeer(t *testing.T) {
	m := NewMonitor("test-self")
	m.RegisterPeer("immune", "http://localhost:9760/health")
	m.RegisterPeer("sidecar", "http://localhost:9770/health")

	peers := m.AllPeers()
	if len(peers) != 2 {
		t.Fatalf("peer count = %d, want 2", len(peers))
	}
}

func TestHealthyPeer(t *testing.T) {
	// Create a mock healthy peer.
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))
	defer srv.Close()

	m := NewMonitor("test-self")
	m.RegisterPeer("healthy-peer", srv.URL+"/health")

	// Run one check cycle.
	ctx := context.Background()
	m.checkAllPeers(ctx)

	peer, ok := m.GetPeerStatus("healthy-peer")
	if !ok {
		t.Fatal("peer not found")
	}
	if peer.Status != StatusHealthy {
		t.Errorf("status = %s, want HEALTHY", peer.Status)
	}
	if peer.MissedCount != 0 {
		t.Errorf("missed = %d, want 0", peer.MissedCount)
	}
}

func TestUnhealthyPeerDegraded(t *testing.T) {
	// Peer that's down (no server listening).
	m := NewMonitor("test-self")
	m.RegisterPeer("dead-peer", "http://127.0.0.1:19999/health")

	ctx := context.Background()

	// One miss → DEGRADED.
	m.checkAllPeers(ctx)

	peer, _ := m.GetPeerStatus("dead-peer")
	if peer.Status != StatusDegraded {
		t.Errorf("status = %s, want DEGRADED", peer.Status)
	}
	if peer.MissedCount != 1 {
		t.Errorf("missed = %d, want 1", peer.MissedCount)
	}
}

func TestEscalationToRestart(t *testing.T) {
	m := NewMonitor("test-self")
	m.RegisterPeer("flaky-peer", "http://127.0.0.1:19999/health")

	var escalations []EscalationAction
	m.OnEscalation(func(a EscalationAction) {
		escalations = append(escalations, a)
	})

	ctx := context.Background()

	// Miss 3 heartbeats → should trigger restart.
	for i := 0; i < MaxMissedBeforeRestart; i++ {
		m.checkAllPeers(ctx)
	}

	peer, _ := m.GetPeerStatus("flaky-peer")
	if peer.Status != StatusOffline {
		t.Errorf("status = %s, want OFFLINE", peer.Status)
	}
	if peer.RestartCount != 1 {
		t.Errorf("restart_count = %d, want 1", peer.RestartCount)
	}

	// Check that escalation was fired.
	found := false
	for _, e := range escalations {
		if e.Action == "restart" {
			found = true
			break
		}
	}
	if !found {
		t.Error("expected 'restart' escalation, got none")
	}
}

func TestEscalationToIsolate(t *testing.T) {
	m := NewMonitor("test-self")
	m.RegisterPeer("broken-peer", "http://127.0.0.1:19999/health")

	var escalations []EscalationAction
	m.OnEscalation(func(a EscalationAction) {
		escalations = append(escalations, a)
	})

	ctx := context.Background()

	// Trigger MaxRestartsBeforeIsolate restart cycles.
	for r := 0; r < MaxRestartsBeforeIsolate; r++ {
		for i := 0; i < MaxMissedBeforeRestart; i++ {
			m.checkAllPeers(ctx)
		}
	}

	// Now one more miss cycle should trigger isolation.
	for i := 0; i < MaxMissedBeforeRestart; i++ {
		m.checkAllPeers(ctx)
	}

	peer, _ := m.GetPeerStatus("broken-peer")
	if peer.Status != StatusIsolated {
		t.Errorf("status = %s, want ISOLATED", peer.Status)
	}

	// Check for isolate escalation.
	found := false
	for _, e := range escalations {
		if e.Action == "isolate" {
			found = true
			if e.Severity != "CRITICAL" {
				t.Errorf("isolate severity = %s, want CRITICAL", e.Severity)
			}
			break
		}
	}
	if !found {
		t.Error("expected 'isolate' escalation, got none")
	}
}

func TestRecoveryAfterRestart(t *testing.T) {
	// Peer goes down, gets restarted (simulated), then comes back.
	healthy := true
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if healthy {
			w.WriteHeader(http.StatusOK)
		} else {
			w.WriteHeader(http.StatusServiceUnavailable)
		}
	}))
	defer srv.Close()

	m := NewMonitor("test-self")
	m.RegisterPeer("recovering-peer", srv.URL+"/health")

	ctx := context.Background()

	// Initially healthy.
	m.checkAllPeers(ctx)
	peer, _ := m.GetPeerStatus("recovering-peer")
	if peer.Status != StatusHealthy {
		t.Fatalf("initial status = %s, want HEALTHY", peer.Status)
	}

	// Goes down.
	healthy = false
	m.checkAllPeers(ctx)
	peer, _ = m.GetPeerStatus("recovering-peer")
	if peer.Status != StatusDegraded {
		t.Fatalf("down status = %s, want DEGRADED", peer.Status)
	}

	// Comes back.
	healthy = true
	m.checkAllPeers(ctx)
	peer, _ = m.GetPeerStatus("recovering-peer")
	if peer.Status != StatusHealthy {
		t.Errorf("recovered status = %s, want HEALTHY", peer.Status)
	}
	if peer.MissedCount != 0 {
		t.Errorf("missed after recovery = %d, want 0", peer.MissedCount)
	}
}

func TestStats(t *testing.T) {
	m := NewMonitor("test-self")
	m.RegisterPeer("p1", "http://127.0.0.1:19999/health")

	ctx := context.Background()
	m.checkAllPeers(ctx)
	m.checkAllPeers(ctx)

	stats := m.Stats()
	if stats.TotalChecks != 2 {
		t.Errorf("total_checks = %d, want 2", stats.TotalChecks)
	}
	if stats.TotalMisses != 2 {
		t.Errorf("total_misses = %d, want 2", stats.TotalMisses)
	}
	if stats.PeerCount != 1 {
		t.Errorf("peer_count = %d, want 1", stats.PeerCount)
	}
}

func TestServeHTTP(t *testing.T) {
	m := NewMonitor("test-self")
	m.RegisterPeer("p1", "http://localhost:9760/health")

	w := httptest.NewRecorder()
	r := httptest.NewRequest(http.MethodGet, "/mesh", nil)

	m.ServeHTTP(w, r)

	if w.Code != http.StatusOK {
		t.Errorf("status = %d, want 200", w.Code)
	}
	if ct := w.Header().Get("Content-Type"); ct != "application/json" {
		t.Errorf("content-type = %s, want application/json", ct)
	}
}

func TestMonitorStartStop(t *testing.T) {
	m := NewMonitor("test-self")
	m.interval = 50 * time.Millisecond // Fast for tests.

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))
	defer srv.Close()

	m.RegisterPeer("fast-peer", srv.URL+"/health")

	ctx, cancel := context.WithTimeout(context.Background(), 200*time.Millisecond)
	defer cancel()

	m.Start(ctx) // Blocks until context expires.

	stats := m.Stats()
	if stats.TotalChecks < 2 {
		t.Errorf("expected at least 2 checks in 200ms, got %d", stats.TotalChecks)
	}
}
