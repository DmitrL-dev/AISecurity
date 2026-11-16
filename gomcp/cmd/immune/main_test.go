package main

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/syntrex/gomcp/internal/infrastructure/guard"
)

// Review 13.06 (audit D5): integration coverage for the immune /mode control
// endpoint. The POST path mutates a runtime security control, so it must fail
// closed when no control token is configured, reject a wrong token, accept the
// right one, and validate the mode value. GET stays open for liveness probes.

func newTestGuard() *guard.Guard {
	return guard.New(&guard.Policy{Mode: guard.ModeAudit})
}

func TestModeHandler_PostFailsClosedWithoutToken(t *testing.T) {
	// SOC_IMMUNE_CONTROL_TOKEN intentionally unset.
	g := newTestGuard()
	r := httptest.NewRequest(http.MethodPost, "/mode", strings.NewReader(`{"mode":"enforce"}`))
	w := httptest.NewRecorder()

	modeHandler(g)(w, r)

	if w.Code != http.StatusForbidden {
		t.Fatalf("no control token must be 403 (fail closed), got %d", w.Code)
	}
	if g.CurrentMode() != guard.ModeAudit {
		t.Fatalf("mode must be unchanged, got %s", g.CurrentMode())
	}
}

func TestModeHandler_PostRejectsWrongToken(t *testing.T) {
	t.Setenv("SOC_IMMUNE_CONTROL_TOKEN", "right-token")
	g := newTestGuard()
	r := httptest.NewRequest(http.MethodPost, "/mode", strings.NewReader(`{"mode":"enforce"}`))
	r.Header.Set("X-Control-Token", "wrong-token")
	w := httptest.NewRecorder()

	modeHandler(g)(w, r)

	if w.Code != http.StatusUnauthorized {
		t.Fatalf("wrong control token must be 401, got %d", w.Code)
	}
	if g.CurrentMode() != guard.ModeAudit {
		t.Fatalf("mode must be unchanged, got %s", g.CurrentMode())
	}
}

func TestModeHandler_PostAcceptsRightTokenAndValidMode(t *testing.T) {
	t.Setenv("SOC_IMMUNE_CONTROL_TOKEN", "right-token")
	g := newTestGuard()
	r := httptest.NewRequest(http.MethodPost, "/mode", strings.NewReader(`{"mode":"enforce"}`))
	r.Header.Set("X-Control-Token", "right-token")
	w := httptest.NewRecorder()

	modeHandler(g)(w, r)

	if w.Code != http.StatusOK {
		t.Fatalf("valid token + mode must be 200, got %d (%s)", w.Code, w.Body.String())
	}
	if g.CurrentMode() != guard.ModeEnforce {
		t.Fatalf("mode must be enforce, got %s", g.CurrentMode())
	}
}

func TestModeHandler_PostRejectsInvalidMode(t *testing.T) {
	t.Setenv("SOC_IMMUNE_CONTROL_TOKEN", "right-token")
	g := newTestGuard()
	r := httptest.NewRequest(http.MethodPost, "/mode", strings.NewReader(`{"mode":"god-mode"}`))
	r.Header.Set("X-Control-Token", "right-token")
	w := httptest.NewRecorder()

	modeHandler(g)(w, r)

	if w.Code != http.StatusBadRequest {
		t.Fatalf("invalid mode must be 400, got %d", w.Code)
	}
	if g.CurrentMode() != guard.ModeAudit {
		t.Fatalf("invalid mode must not change state, got %s", g.CurrentMode())
	}
}

func TestModeHandler_GetIsOpen(t *testing.T) {
	// No token configured; GET must still report the current mode.
	g := newTestGuard()
	r := httptest.NewRequest(http.MethodGet, "/mode", nil)
	w := httptest.NewRecorder()

	modeHandler(g)(w, r)

	if w.Code != http.StatusOK {
		t.Fatalf("GET /mode must be 200, got %d", w.Code)
	}
	if !strings.Contains(w.Body.String(), "audit") {
		t.Fatalf("GET /mode must report current mode, got %s", w.Body.String())
	}
}
