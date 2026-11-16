package main

import (
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"sync"
	"testing"

	domsoc "github.com/syntrex/gomcp/internal/domain/soc"
	"github.com/syntrex/gomcp/internal/infrastructure/guard"
	"github.com/syntrex/gomcp/internal/infrastructure/logging"
)

// newLogOnlyFW returns the honest, non-enforcing firewall (empty backend).
func newLogOnlyFW() domsoc.Firewall {
	return domsoc.NewFirewall(domsoc.FirewallConfig{})
}

// captured holds what the fake SOC ingest endpoint received.
type captured struct {
	mu   sync.Mutex
	body map[string]any
	hits int
}

func fakeSOC(t *testing.T, cap *captured) *httptest.Server {
	t.Helper()
	mux := http.NewServeMux()
	mux.HandleFunc("/api/v1/soc/events", func(w http.ResponseWriter, r *http.Request) {
		raw, _ := io.ReadAll(r.Body)
		var m map[string]any
		_ = json.Unmarshal(raw, &m)
		cap.mu.Lock()
		cap.body = m
		cap.hits++
		cap.mu.Unlock()
		w.WriteHeader(http.StatusCreated)
		_, _ = w.Write([]byte(`{"event_id":"evt-1","status":"ingested"}`))
	})
	return httptest.NewServer(mux)
}

// TestForwarder_PostsViolationToSOC verifies a violation is POSTed to the real
// SOC ingest endpoint with source=immune and the honest action in metadata.
func TestForwarder_PostsViolationToSOC(t *testing.T) {
	cap := &captured{}
	srv := fakeSOC(t, cap)
	defer srv.Close()

	f := newSOCForwarder(srv.URL, "sensor-immune-01", "", logging.New("text", "error"))
	if !f.enabled {
		t.Fatal("forwarder should be enabled when bus URL is set")
	}

	f.Forward(guard.Violation{
		ProcessName: "soc-correlate",
		PID:         4242,
		Type:        "network",
		Detail:      "network access denied (no network allowed): 8.8.8.8:443",
		Severity:    "CRITICAL",
		Action:      "logged",
		PolicyMode:  guard.ModeEnforce,
	})

	cap.mu.Lock()
	defer cap.mu.Unlock()
	if cap.hits != 1 {
		t.Fatalf("expected 1 POST to SOC, got %d", cap.hits)
	}
	if cap.body["source"] != "immune" {
		t.Errorf("source = %v, want immune", cap.body["source"])
	}
	if cap.body["severity"] != "CRITICAL" {
		t.Errorf("severity = %v, want CRITICAL", cap.body["severity"])
	}
	if cap.body["category"] != "exfiltration" {
		t.Errorf("category = %v, want exfiltration (network maps to exfiltration)", cap.body["category"])
	}
	meta, ok := cap.body["metadata"].(map[string]any)
	if !ok {
		t.Fatalf("metadata missing or wrong type: %v", cap.body["metadata"])
	}
	if meta["guard_action"] != "logged" {
		t.Errorf("guard_action = %v, want logged (honest: not blocked)", meta["guard_action"])
	}
	if meta["guard_pid"] != "4242" {
		t.Errorf("guard_pid = %v, want 4242", meta["guard_pid"])
	}
}

// TestForwarder_DisabledWhenNoURL verifies the honest no-op path: no URL → not
// enabled, Forward is a safe no-op (no panic, nothing sent).
func TestForwarder_DisabledWhenNoURL(t *testing.T) {
	f := newSOCForwarder("", "sensor-immune-01", "", logging.New("text", "error"))
	if f.enabled {
		t.Fatal("forwarder must be disabled when no bus URL is configured")
	}
	// Must not panic and must be a no-op.
	f.Forward(guard.Violation{ProcessName: "x", Type: "syscall", Action: "logged"})
}

// TestGuardEnforcerHonesty verifies the core honesty contract: in enforce mode a
// violation is only counted/labelled "blocked" when the enforcer ACTUALLY
// enforced. A log-only enforcer must downgrade the action to "logged" and leave
// stats.Blocked at zero.
func TestGuardEnforcerHonesty_LogOnlyNotCountedBlocked(t *testing.T) {
	p := &guard.Policy{
		Mode: guard.ModeEnforce,
		Processes: map[string]guard.ProcessPolicy{
			"soc-correlate": {AllowedNetwork: []string{}}, // no network at all
		},
	}
	g := guard.New(p)

	// Honest log-only enforcer: nothing was actually enforced.
	g.SetEnforcer(func(v guard.Violation) (string, bool) {
		return "logged", false
	})

	var got guard.Violation
	g.OnViolation(func(v guard.Violation) { got = v })

	v := g.CheckNetwork("soc-correlate", 10, "8.8.8.8:443")
	if v == nil {
		t.Fatal("expected a network violation")
	}
	// The handler must observe the TRUTHFUL (downgraded) action.
	if got.Action != "logged" {
		t.Errorf("handler action = %q, want logged (enforcer did not block)", got.Action)
	}
	if got.SrcIP != "8.8.8.8:443" {
		t.Errorf("SrcIP = %q, want the peer addr for enforcement", got.SrcIP)
	}
	if b := g.Stats().Blocked; b != 0 {
		t.Errorf("stats.Blocked = %d, want 0 (nothing was actually blocked)", b)
	}
}

// TestGuardEnforcerHonesty_RealBlockIsCounted verifies the converse: an enforcer
// that reports a real block is counted and labelled "blocked".
func TestGuardEnforcerHonesty_RealBlockIsCounted(t *testing.T) {
	p := &guard.Policy{
		Mode: guard.ModeEnforce,
		Processes: map[string]guard.ProcessPolicy{
			"soc-correlate": {AllowedNetwork: []string{}},
		},
	}
	g := guard.New(p)
	g.SetEnforcer(func(v guard.Violation) (string, bool) {
		return "blocked", true // a real firewall rule was installed
	})

	g.CheckNetwork("soc-correlate", 11, "8.8.8.8:443")
	if b := g.Stats().Blocked; b != 1 {
		t.Errorf("stats.Blocked = %d, want 1 (enforcer reported a real block)", b)
	}
}

// TestEnforcer_NetworkLogOnlyWhenNoBackend verifies the enforcer itself is honest
// when no firewall backend is configured: enforce mode + network violation → it
// does NOT claim a block.
func TestEnforcer_NetworkLogOnlyWhenNoBackend(t *testing.T) {
	// Empty backend → LogOnlyFirewall (enforced=false always).
	fw := newLogOnlyFW()
	enf := newEnforcer(fw, false, logging.New("text", "error"))

	action, enforced := enf.enforce(guard.Violation{
		Type:       "network",
		SrcIP:      "8.8.8.8:443",
		PolicyMode: guard.ModeEnforce,
	})
	if enforced {
		t.Error("enforced=true but no firewall backend is configured")
	}
	if action != "logged" {
		t.Errorf("action = %q, want logged", action)
	}
}

// TestEnforcer_AuditNeverBlocks verifies audit mode never enforces regardless.
func TestEnforcer_AuditNeverBlocks(t *testing.T) {
	enf := newEnforcer(newLogOnlyFW(), true, logging.New("text", "error"))
	action, enforced := enf.enforce(guard.Violation{
		Type:       "network",
		SrcIP:      "8.8.8.8:443",
		PolicyMode: guard.ModeAudit,
	})
	if enforced || action != "logged" {
		t.Errorf("audit mode must be log-only, got action=%q enforced=%v", action, enforced)
	}
}

// TestEnforcer_KillGatedOff verifies process-kill is log-only unless explicitly
// allowed, even in enforce mode.
func TestEnforcer_KillGatedOff(t *testing.T) {
	enf := newEnforcer(newLogOnlyFW(), false /* allowKill */, logging.New("text", "error"))
	action, enforced := enf.enforce(guard.Violation{
		Type:       "syscall",
		PID:        999999,
		PolicyMode: guard.ModeEnforce,
	})
	if enforced || action != "logged" {
		t.Errorf("kill must be gated off by default, got action=%q enforced=%v", action, enforced)
	}
}
