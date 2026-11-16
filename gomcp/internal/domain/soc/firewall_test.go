package soc

import (
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

func TestLogOnlyFirewall_NeverEnforces(t *testing.T) {
	fw := NewFirewall(FirewallConfig{}) // empty backend → log-only
	if fw.Type() != "log-only" {
		t.Fatalf("expected log-only backend, got %q", fw.Type())
	}
	enforced, detail, err := fw.Block("203.0.113.7", time.Hour, "test")
	if err != nil {
		t.Fatalf("log-only Block returned error: %v", err)
	}
	if enforced {
		t.Fatal("log-only firewall must NEVER report enforced=true")
	}
	if detail == "" {
		t.Fatal("log-only firewall must explain why it did not enforce")
	}
}

func TestNewFirewall_UnknownBackendFallsBackToLogOnly(t *testing.T) {
	fw := NewFirewall(FirewallConfig{Backend: "totally-bogus"})
	if fw.Type() != "log-only" {
		t.Fatalf("unknown backend must fall back to log-only, got %q", fw.Type())
	}
}

func TestFirewall_RejectsNonIP(t *testing.T) {
	fw := NewFirewall(FirewallConfig{})
	if _, _, err := fw.Block("not-an-ip; rm -rf /", time.Hour, "x"); err == nil {
		t.Fatal("expected error for non-IP input (shell-injection guard)")
	}
}

func TestHTTPFirewall_EnforcesOn2xx(t *testing.T) {
	var gotBody map[string]any
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		b, _ := io.ReadAll(r.Body)
		_ = json.Unmarshal(b, &gotBody)
		if auth := r.Header.Get("Authorization"); auth != "Bearer tok123" {
			t.Errorf("missing/wrong auth header: %q", auth)
		}
		w.WriteHeader(http.StatusOK)
	}))
	defer srv.Close()

	// SafeDialContext blocks loopback by default; relax SSRF guards for the test
	// (httptest binds 127.0.0.1). Restore after.
	origDial := SafeDialContext
	origValidate := ValidateWebhookURL
	SafeDialContext = nil // use default dialer (allows loopback in test)
	ValidateWebhookURL = func(string) error { return nil }
	defer func() { SafeDialContext = origDial; ValidateWebhookURL = origValidate }()

	fw := NewHTTPFirewall(srv.URL, "tok123")
	enforced, detail, err := fw.Block("203.0.113.9", 2*time.Hour, "c2")
	if err != nil {
		t.Fatalf("HTTPFirewall.Block error: %v", err)
	}
	if !enforced {
		t.Fatal("HTTPFirewall must report enforced=true on 2xx")
	}
	if !strings.Contains(detail, "cloud firewall") {
		t.Errorf("unexpected detail: %q", detail)
	}
	if gotBody["action"] != "block" || gotBody["ip"] != "203.0.113.9" {
		t.Errorf("unexpected request body: %#v", gotBody)
	}
}

func TestHTTPFirewall_NotEnforcedOnError(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	}))
	defer srv.Close()

	origDial := SafeDialContext
	origValidate := ValidateWebhookURL
	SafeDialContext = nil
	ValidateWebhookURL = func(string) error { return nil }
	defer func() { SafeDialContext = origDial; ValidateWebhookURL = origValidate }()

	fw := NewHTTPFirewall(srv.URL, "")
	enforced, _, err := fw.Block("203.0.113.9", time.Hour, "c2")
	if err == nil {
		t.Fatal("expected error on 5xx response")
	}
	if enforced {
		t.Fatal("must not report enforced on a failed POST")
	}
}

func TestHTTPFirewall_NoURLIsHonestlyDisabled(t *testing.T) {
	fw := NewHTTPFirewall("", "")
	enforced, detail, err := fw.Block("203.0.113.9", time.Hour, "c2")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if enforced {
		t.Fatal("http backend with no URL must report not-enforced")
	}
	if detail == "" {
		t.Fatal("expected a not-configured detail")
	}
}

// TestBlockIPExecutor_LogOnlyReturnsError verifies the honesty contract at the
// executor layer: a non-enforcing backend yields an ERROR (→ partial_failure),
// not a fake success.
func TestBlockIPExecutor_LogOnlyReturnsError(t *testing.T) {
	exec := NewBlockIPExecutor(&LogOnlyFirewall{})
	_, err := exec.Execute(ActionParams{
		IncidentID: "INC-1",
		Extra:      map[string]any{"ip": "203.0.113.5", "duration": "3600"},
	})
	if err == nil {
		t.Fatal("block_ip with log-only backend must return an error (not a fake success)")
	}
	if !strings.Contains(err.Error(), "NOT enforced") {
		t.Errorf("error should state NOT enforced, got: %v", err)
	}
}

func TestBlockIPExecutor_EnforcedReturnsSuccess(t *testing.T) {
	exec := NewBlockIPExecutor(&fakeEnforcingFirewall{})
	res, err := exec.Execute(ActionParams{
		IncidentID: "INC-2",
		Extra:      map[string]any{"ip": "203.0.113.6", "duration": "60"},
	})
	if err != nil {
		t.Fatalf("expected success, got error: %v", err)
	}
	if !strings.Contains(res, "BLOCKED") {
		t.Errorf("expected BLOCKED in result, got: %q", res)
	}
}

func TestBlockIPExecutor_NilBackendDefaultsLogOnly(t *testing.T) {
	// Zero-value executor (backward compat) must default to honest log-only.
	exec := &BlockIPExecutor{}
	_, err := exec.Execute(ActionParams{Extra: map[string]any{"ip": "203.0.113.5"}})
	if err == nil {
		t.Fatal("zero-value BlockIPExecutor must default to log-only (error, not fake success)")
	}
}

type fakeEnforcingFirewall struct{}

func (f *fakeEnforcingFirewall) Type() string { return "fake" }
func (f *fakeEnforcingFirewall) Block(ip string, ttl time.Duration, reason string) (bool, string, error) {
	return true, "blocked (fake)", nil
}
func (f *fakeEnforcingFirewall) Unblock(ip string) error { return nil }
