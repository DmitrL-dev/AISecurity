package httpserver

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	shadowai "github.com/syntrex/gomcp/internal/application/shadow_ai"
	appsoc "github.com/syntrex/gomcp/internal/application/soc"
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"
)

// mountShadowAI mounts the shadow-AI handlers on a bare mux (RBAC bypassed, like
// newTestServer) so the test exercises the wiring/handler logic directly.
func mountShadowAI(srv *Server) *http.ServeMux {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /api/v1/shadow-ai/stats", srv.handleShadowAIStats)
	mux.HandleFunc("GET /api/v1/shadow-ai/events", srv.handleShadowAIEvents)
	mux.HandleFunc("GET /api/v1/shadow-ai/integrations", srv.handleShadowAIIntegrations)
	mux.HandleFunc("GET /api/v1/shadow-ai/compliance", srv.handleShadowAICompliance)
	mux.HandleFunc("POST /api/v1/shadow-ai/ingest", srv.handleShadowAINetworkIngest)
	return mux
}

func newWiringTestServer(t *testing.T) *Server {
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

// TestShadowAI_Routes503WhenUnconfigured proves the dead-route default: with no
// controller wired, the routes honestly return 503 (not a fake 200).
func TestShadowAI_Routes503WhenUnconfigured(t *testing.T) {
	srv := newWiringTestServer(t)
	// Deliberately DO NOT call SetShadowAI — s.shadowAI stays nil.
	ts := httptest.NewServer(mountShadowAI(srv))
	defer ts.Close()

	for _, path := range []string{
		"/api/v1/shadow-ai/stats",
		"/api/v1/shadow-ai/events",
		"/api/v1/shadow-ai/integrations",
		"/api/v1/shadow-ai/compliance",
	} {
		resp, err := http.Get(ts.URL + path)
		if err != nil {
			t.Fatalf("GET %s: %v", path, err)
		}
		resp.Body.Close()
		if resp.StatusCode != http.StatusServiceUnavailable {
			t.Errorf("GET %s: expected 503 when unconfigured, got %d", path, resp.StatusCode)
		}
	}
}

// TestShadowAI_RoutesLiveWhenConfigured proves wiring a controller flips the
// routes from 503 to live 200s, with an honest empty event store.
func TestShadowAI_RoutesLiveWhenConfigured(t *testing.T) {
	srv := newWiringTestServer(t)
	srv.SetShadowAI(shadowai.NewShadowAIController())
	ts := httptest.NewServer(mountShadowAI(srv))
	defer ts.Close()

	// stats: 200
	resp, err := http.Get(ts.URL + "/api/v1/shadow-ai/stats")
	if err != nil {
		t.Fatalf("GET stats: %v", err)
	}
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("stats: expected 200 when configured, got %d", resp.StatusCode)
	}
	resp.Body.Close()

	// integrations: 200 with zero plugins (honest empty)
	resp, err = http.Get(ts.URL + "/api/v1/shadow-ai/integrations")
	if err != nil {
		t.Fatalf("GET integrations: %v", err)
	}
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("integrations: expected 200, got %d", resp.StatusCode)
	}
	var integ struct {
		Count int `json:"count"`
	}
	_ = json.NewDecoder(resp.Body).Decode(&integ)
	resp.Body.Close()
	if integ.Count != 0 {
		t.Errorf("expected 0 integrations (no creds), got %d", integ.Count)
	}

	// events: 200 with an empty list (no synthetic data)
	resp, err = http.Get(ts.URL + "/api/v1/shadow-ai/events")
	if err != nil {
		t.Fatalf("GET events: %v", err)
	}
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("events: expected 200, got %d", resp.StatusCode)
	}
	var ev struct {
		Count  int           `json:"count"`
		Events []interface{} `json:"events"`
	}
	_ = json.NewDecoder(resp.Body).Decode(&ev)
	resp.Body.Close()
	if ev.Count != 0 || len(ev.Events) != 0 {
		t.Errorf("expected empty event store, got count=%d len=%d", ev.Count, len(ev.Events))
	}
}

// TestShadowAI_ComplianceAuditHonest proves the compliance report's AuditComplete
// reflects reality: false until the SOC event bridge is wired, true after.
func TestShadowAI_ComplianceAuditHonest(t *testing.T) {
	srv := newWiringTestServer(t)
	ctrl := shadowai.NewShadowAIController()
	srv.SetShadowAI(ctrl)
	ts := httptest.NewServer(mountShadowAI(srv))
	defer ts.Close()

	get := func() bool {
		resp, err := http.Get(ts.URL + "/api/v1/shadow-ai/compliance?period=30d")
		if err != nil {
			t.Fatalf("GET compliance: %v", err)
		}
		defer resp.Body.Close()
		if resp.StatusCode != http.StatusOK {
			t.Fatalf("compliance: expected 200, got %d", resp.StatusCode)
		}
		var rep struct {
			AuditComplete bool `json:"audit_complete"`
		}
		_ = json.NewDecoder(resp.Body).Decode(&rep)
		return rep.AuditComplete
	}

	if get() {
		t.Error("audit_complete must be FALSE before SOC emitter is wired (no audit path)")
	}

	ctrl.SetSOCEventEmitter(func(_, _, _, _ string, _ map[string]string) {})
	if !get() {
		t.Error("audit_complete must be TRUE once SOC emitter is wired")
	}
}

// TestShadowAI_IngestEmptyUntilFed proves the ingest route accepts events but the
// store stays empty for a non-AI destination (no fabricated discoveries).
func TestShadowAI_IngestEmptyUntilFed(t *testing.T) {
	srv := newWiringTestServer(t)
	srv.SetShadowAI(shadowai.NewShadowAIController())
	ts := httptest.NewServer(mountShadowAI(srv))
	defer ts.Close()

	// A benign, non-AI destination must NOT be recorded as a discovery.
	body, _ := json.Marshal(map[string]any{
		"user": "alice", "hostname": "ws-1", "destination": "example.com", "port": 443,
	})
	resp, err := http.Post(ts.URL+"/api/v1/shadow-ai/ingest", "application/json", bytes.NewReader(body))
	if err != nil {
		t.Fatalf("POST ingest: %v", err)
	}
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("ingest: expected 200, got %d", resp.StatusCode)
	}
	var out struct {
		Detected bool `json:"detected"`
	}
	_ = json.NewDecoder(resp.Body).Decode(&out)
	resp.Body.Close()
	if out.Detected {
		t.Error("benign destination must not be detected as shadow-AI")
	}

	// Store remains empty.
	resp, err = http.Get(ts.URL + "/api/v1/shadow-ai/stats")
	if err != nil {
		t.Fatalf("GET stats: %v", err)
	}
	var stats struct {
		Total int `json:"total_attempts"`
	}
	_ = json.NewDecoder(resp.Body).Decode(&stats)
	resp.Body.Close()
	if stats.Total != 0 {
		t.Errorf("expected empty store after benign ingest, got total=%d", stats.Total)
	}
}
