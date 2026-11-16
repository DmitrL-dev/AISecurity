package httpserver

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	appsoc "github.com/syntrex/gomcp/internal/application/soc"
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"
)

// Reconciliation (threat-intel): GET /api/soc/threat-intel must serve the LIVE
// store (operator-configured feeds) when it has IOCs, and fall back to the
// built-in sample engine only when no live IOCs are loaded.

func newTISrv(t *testing.T) *Server {
	t.Helper()
	db, err := sqlite.Open(":memory:")
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	t.Cleanup(func() { db.Close() })
	repo, err := sqlite.NewSOCRepo(db)
	if err != nil {
		t.Fatalf("repo: %v", err)
	}
	return New(appsoc.NewService(repo, nil), 0)
}

func TestHandleThreatIntel_ServesLiveStoreWhenPopulated(t *testing.T) {
	srv := newTISrv(t)
	store := appsoc.NewThreatIntelStore()
	store.AddIOC(appsoc.IOC{
		Type:     appsoc.IOCTypeIP,
		Value:    "203.0.113.5",
		Severity: "high",
		Source:   "unit-feed",
	})
	srv.SetThreatIntel(store)

	r := httptest.NewRequest(http.MethodGet, "/api/soc/threat-intel", nil)
	w := httptest.NewRecorder()
	srv.handleThreatIntel(w, r)

	if w.Code != http.StatusOK {
		t.Fatalf("status %d", w.Code)
	}
	body := w.Body.String()
	if !strings.Contains(body, `"source":"live-feeds"`) {
		t.Fatalf("expected live-feeds source, got %s", body)
	}
	if !strings.Contains(body, "203.0.113.5") {
		t.Fatalf("expected live IOC in body, got %s", body)
	}
}

func TestHandleThreatIntel_FallsBackToSampleWhenEmpty(t *testing.T) {
	srv := newTISrv(t)
	// Empty store attached → handler must fall back to the sample engine.
	srv.SetThreatIntel(appsoc.NewThreatIntelStore())

	r := httptest.NewRequest(http.MethodGet, "/api/soc/threat-intel", nil)
	w := httptest.NewRecorder()
	srv.handleThreatIntel(w, r)

	if w.Code != http.StatusOK {
		t.Fatalf("status %d", w.Code)
	}
	if body := w.Body.String(); !strings.Contains(body, `"source":"sample"`) {
		t.Fatalf("expected sample source fallback, got %s", body)
	}
}

func TestHandleThreatIntelMatch_LiveStore(t *testing.T) {
	srv := newTISrv(t)
	store := appsoc.NewThreatIntelStore()
	store.AddIOC(appsoc.IOC{Type: appsoc.IOCTypeDomain, Value: "evil.example", Severity: "critical", Source: "unit"})
	srv.SetThreatIntel(store)

	r := httptest.NewRequest(http.MethodPost, "/api/soc/threat-intel/match",
		strings.NewReader(`{"value":"evil.example"}`))
	w := httptest.NewRecorder()
	srv.handleThreatIntelMatch(w, r)

	if w.Code != http.StatusOK {
		t.Fatalf("status %d", w.Code)
	}
	body := w.Body.String()
	if !strings.Contains(body, `"source":"live-feeds"`) || !strings.Contains(body, "evil.example") {
		t.Fatalf("expected live-store match, got %s", body)
	}
}
