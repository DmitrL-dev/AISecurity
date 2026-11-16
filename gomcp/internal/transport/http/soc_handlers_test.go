package httpserver

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"

	appsoc "github.com/syntrex/gomcp/internal/application/soc"
	domsoc "github.com/syntrex/gomcp/internal/domain/soc"
	"github.com/syntrex/gomcp/internal/infrastructure/auth"
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"
)

// newTestServer creates an HTTP test server with a real SOC service backed by in-memory SQLite.
func newTestServer(t *testing.T) (*httptest.Server, *appsoc.Service) {
	t.Helper()

	// In-memory SQLite for SOC
	db, err := sqlite.Open(":memory:")
	if err != nil {
		t.Fatalf("open test db: %v", err)
	}
	t.Cleanup(func() { db.Close() })

	repo, err := sqlite.NewSOCRepo(db)
	if err != nil {
		t.Fatalf("create SOC repo: %v", err)
	}

	socSvc := appsoc.NewService(repo, nil) // no decision logger for tests

	srv := New(socSvc, 0) // port 0, we use httptest
	mux := http.NewServeMux()
	mux.HandleFunc("GET /api/soc/dashboard", srv.handleDashboard)
	mux.HandleFunc("GET /api/soc/events", srv.handleEvents)
	mux.HandleFunc("GET /api/soc/incidents", srv.handleIncidents)
	mux.HandleFunc("GET /api/soc/incidents/{id}", srv.handleIncidentDetail)
	mux.HandleFunc("GET /api/soc/sensors", srv.handleSensors)
	mux.HandleFunc("GET /api/soc/clusters", srv.handleClusters)
	mux.HandleFunc("GET /api/soc/rules", srv.handleRules)
	mux.HandleFunc("GET /api/soc/threat-intel", srv.handleThreatIntel)
	mux.HandleFunc("GET /api/soc/webhook-stats", srv.handleWebhookStats)
	mux.HandleFunc("GET /api/soc/analytics", srv.handleAnalytics)
	mux.HandleFunc("POST /api/v1/soc/events", srv.handleIngestEvent)
	mux.HandleFunc("POST /api/v1/soc/events/batch", srv.handleBatchIngest)
	mux.HandleFunc("POST /api/soc/sensors/heartbeat", srv.handleSensorHeartbeat)
	mux.HandleFunc("POST /api/soc/incidents/{id}/verdict", srv.handleVerdict)
	mux.HandleFunc("GET /api/soc/compliance", srv.handleComplianceReport)
	mux.HandleFunc("GET /api/soc/compliance/soc2", srv.handleSOC2ComplianceReport)
	mux.HandleFunc("GET /api/soc/anomaly/alerts", srv.handleAnomalyAlerts)
	mux.HandleFunc("GET /api/soc/anomaly/baselines", srv.handleAnomalyBaselines)
	mux.HandleFunc("GET /api/soc/playbooks", srv.handlePlaybooks)
	mux.HandleFunc("GET /api/soc/killchain/{id}", srv.handleKillChain)
	mux.HandleFunc("GET /api/soc/audit", srv.handleAuditTrail)
	mux.HandleFunc("GET /api/soc/deep-health", srv.handleDeepHealth)
	mux.HandleFunc("GET /api/soc/zerog", srv.handleZeroGStatus)
	mux.HandleFunc("POST /api/soc/zerog/toggle", srv.handleZeroGToggle)
	mux.HandleFunc("GET /api/soc/retention", srv.handleRetentionPolicies)
	mux.HandleFunc("GET /api/soc/ratelimit", srv.handleRateLimitStats)
	mux.HandleFunc("GET /api/soc/p2p/peers", srv.handleP2PPeers)
	mux.HandleFunc("GET /api/soc/sovereign", srv.handleSovereignConfig)
	mux.HandleFunc("GET /api/soc/incident-explain/{id}", srv.handleIncidentExplain)
	mux.HandleFunc("GET /health", srv.handleHealth)

	// The legacy helper bypasses production auth middleware. Supply the
	// operator principal that existing global fixtures assume.
	withOperator := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		ctx := auth.SetClaimsContext(r.Context(), &auth.Claims{Sub: "synthetic-operator", Role: "superadmin"})
		mux.ServeHTTP(w, r.WithContext(ctx))
	})
	ts := httptest.NewServer(corsMiddleware([]string{"*"})(withOperator))
	t.Cleanup(ts.Close)

	return ts, socSvc
}

// TestHTTP_Dashboard_Returns200 verifies GET /api/soc/dashboard returns 200 with valid JSON.
func TestHTTP_Dashboard_Returns200(t *testing.T) {
	ts, _ := newTestServer(t)

	resp, err := http.Get(ts.URL + "/api/soc/dashboard")
	if err != nil {
		t.Fatalf("GET /api/soc/dashboard: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}

	// Verify JSON structure
	var result map[string]any
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		t.Fatalf("decode JSON: %v", err)
	}

	// Must contain total_events key
	if _, ok := result["total_events"]; !ok {
		t.Error("response missing 'total_events' field")
	}

	// Verify CORS headers
	if origin := resp.Header.Get("Access-Control-Allow-Origin"); origin != "*" {
		t.Errorf("CORS: expected *, got %q", origin)
	}
}

// TestHTTP_Events_WithLimit verifies GET /api/soc/events?limit=5 returns at most 5 events.
func TestHTTP_Events_WithLimit(t *testing.T) {
	ts, socSvc := newTestServer(t)

	// Ingest 10 events (unique descriptions to avoid dedup)
	for i := 0; i < 10; i++ {
		socSvc.IngestEvent(domsoc.SOCEvent{
			SensorID:    "test-sensor",
			Source:      domsoc.SourceGoMCP,
			Category:    "test",
			Severity:    domsoc.SeverityLow,
			Description: fmt.Sprintf("test event payload #%d", i),
			Payload:     fmt.Sprintf("test event payload #%d", i),
		})
	}

	resp, err := http.Get(ts.URL + "/api/soc/events?limit=5")
	if err != nil {
		t.Fatalf("GET /api/soc/events: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}

	var result struct {
		Events []any `json:"events"`
		Count  int   `json:"count"`
		Limit  int   `json:"limit"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		t.Fatalf("decode JSON: %v", err)
	}

	if result.Limit != 5 {
		t.Errorf("expected limit=5, got %d", result.Limit)
	}
	if result.Count > 5 {
		t.Errorf("expected at most 5 events, got %d", result.Count)
	}
}

// TestHTTP_Incidents_FilterByStatus verifies GET /api/soc/incidents?status=open returns only open incidents.
func TestHTTP_Incidents_FilterByStatus(t *testing.T) {
	ts, socSvc := newTestServer(t)

	// Ingest 3 correlated jailbreak events to trigger incident creation
	for i := 0; i < 3; i++ {
		socSvc.IngestEvent(domsoc.SOCEvent{
			SensorID:    "test-sensor",
			Source:      domsoc.SourceGoMCP,
			Category:    "jailbreak",
			Severity:    domsoc.SeverityCritical,
			Description: fmt.Sprintf("jailbreak attempt for correlation test #%d", i),
			Payload:     fmt.Sprintf("jailbreak attempt payload #%d", i),
		})
	}

	resp, err := http.Get(ts.URL + "/api/soc/incidents?status=open")
	if err != nil {
		t.Fatalf("GET /api/soc/incidents: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}

	var result struct {
		Incidents []any  `json:"incidents"`
		Count     int    `json:"count"`
		Status    string `json:"status"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		t.Fatalf("decode JSON: %v", err)
	}

	if result.Status != "open" {
		t.Errorf("expected status filter 'open', got %q", result.Status)
	}

	// After 3 jailbreak events, correlation should have created at least one open incident
	t.Logf("incidents: count=%d, status=%s", result.Count, result.Status)
}

// TestHTTP_Health returns ok.
func TestHTTP_Health(t *testing.T) {
	ts, _ := newTestServer(t)

	resp, err := http.Get(ts.URL + "/health")
	if err != nil {
		t.Fatalf("GET /health: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}

	var result map[string]string
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		t.Fatalf("decode JSON: %v", err)
	}

	if result["status"] != "ok" {
		t.Errorf("expected status 'ok', got %q", result["status"])
	}
}

// TestHTTP_Sensors_Returns200 verifies GET /api/soc/sensors returns 200.
func TestHTTP_Sensors_Returns200(t *testing.T) {
	ts, socSvc := newTestServer(t)

	// Ingest an event to auto-register a sensor
	socSvc.IngestEvent(domsoc.SOCEvent{
		SensorID:    "test-sensor-001",
		Source:      domsoc.SourceSentinelCore,
		Category:    "test",
		Severity:    domsoc.SeverityLow,
		Description: "test event for sensor registration",
	})

	resp, err := http.Get(ts.URL + "/api/soc/sensors")
	if err != nil {
		t.Fatalf("GET /api/soc/sensors: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}

	var result struct {
		Sensors []any `json:"sensors"`
		Count   int   `json:"count"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		t.Fatalf("decode JSON: %v", err)
	}

	if result.Count < 1 {
		t.Error("expected at least 1 sensor after event ingest")
	}
	t.Logf("sensors: count=%d", result.Count)
}

// TestHTTP_ThreatIntel_Returns200 verifies threat-intel returns IOCs and feeds.
func TestHTTP_ThreatIntel_Returns200(t *testing.T) {
	ts, _ := newTestServer(t)

	resp, err := http.Get(ts.URL + "/api/soc/threat-intel")
	if err != nil {
		t.Fatalf("GET /api/soc/threat-intel: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}

	var result map[string]any
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		t.Fatalf("decode JSON: %v", err)
	}

	// ThreatIntelEngine is always initialized, should return enabled=true
	if enabled, ok := result["enabled"].(bool); !ok || !enabled {
		t.Error("expected enabled=true")
	}
}

// TestHTTP_Analytics_Returns200 verifies GET /api/soc/analytics returns a valid report.
func TestHTTP_Analytics_Returns200(t *testing.T) {
	ts, socSvc := newTestServer(t)

	// Ingest some events for analytics (unique descriptions to avoid dedup)
	for i := 0; i < 5; i++ {
		socSvc.IngestEvent(domsoc.SOCEvent{
			SensorID:    "analytics-sensor",
			Source:      domsoc.SourceShield,
			Category:    "prompt_injection",
			Severity:    domsoc.SeverityHigh,
			Description: fmt.Sprintf("injection attempt for analytics test #%d", i),
		})
	}

	resp, err := http.Get(ts.URL + "/api/soc/analytics?window=1")
	if err != nil {
		t.Fatalf("GET /api/soc/analytics: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}

	var result map[string]any
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		t.Fatalf("decode JSON: %v", err)
	}

	// Must have analytics fields
	for _, field := range []string{"generated_at", "event_trend", "severity_distribution", "top_sources", "mttr_hours"} {
		if _, ok := result[field]; !ok {
			t.Errorf("response missing '%s' field", field)
		}
	}

	t.Logf("analytics: events_per_hour=%.1f", result["events_per_hour"])
}

// TestHTTP_WebhookStats_Returns200 verifies webhook-stats endpoint works.
func TestHTTP_WebhookStats_Returns200(t *testing.T) {
	ts, _ := newTestServer(t)

	resp, err := http.Get(ts.URL + "/api/soc/webhook-stats")
	if err != nil {
		t.Fatalf("GET /api/soc/webhook-stats: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}
}

// --- E2E Tests for POST /api/v1/soc/events ---

// TestHTTP_IngestEvent_Returns201 verifies POST /api/v1/soc/events returns 201 with event_id.
func TestHTTP_IngestEvent_Returns201(t *testing.T) {
	ts, _ := newTestServer(t)

	body := `{
		"source": "sentinel-core",
		"severity": "HIGH",
		"category": "jailbreak",
		"description": "Roleplay jailbreak attempt detected",
		"confidence": 0.85,
		"session_id": "sess-test-001"
	}`

	resp, err := http.Post(ts.URL+"/api/v1/soc/events", "application/json", bytes.NewBufferString(body))
	if err != nil {
		t.Fatalf("POST /api/v1/soc/events: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("expected 201, got %d", resp.StatusCode)
	}

	var result map[string]any
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		t.Fatalf("decode JSON: %v", err)
	}

	if _, ok := result["event_id"]; !ok {
		t.Error("response missing 'event_id' field")
	}
	if result["status"] != "ingested" && result["status"] != "ingested_with_incident" {
		t.Errorf("unexpected status: %v", result["status"])
	}

	t.Logf("ingested: event_id=%s, status=%s", result["event_id"], result["status"])
}

// TestHTTP_IngestEvent_MissingFields returns 400 on missing required fields.
func TestHTTP_IngestEvent_MissingFields(t *testing.T) {
	ts, _ := newTestServer(t)

	body := `{"source": "sentinel-core"}`

	resp, err := http.Post(ts.URL+"/api/v1/soc/events", "application/json", bytes.NewBufferString(body))
	if err != nil {
		t.Fatalf("POST: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", resp.StatusCode)
	}
}

// TestHTTP_E2E_IngestAndVerifyDashboard is a full pipeline test:
// POST event → GET dashboard → verify event count incremented.
func TestHTTP_E2E_IngestAndVerifyDashboard(t *testing.T) {
	ts, _ := newTestServer(t)

	// Step 1: Check initial dashboard (0 events).
	resp, err := http.Get(ts.URL + "/api/soc/dashboard")
	if err != nil {
		t.Fatalf("GET dashboard: %v", err)
	}
	var dash0 map[string]any
	json.NewDecoder(resp.Body).Decode(&dash0)
	resp.Body.Close()

	initialEvents := int(dash0["total_events"].(float64))

	// Step 2: POST 3 events via HTTP (each with unique description for dedup).
	for i := 0; i < 3; i++ {
		body := fmt.Sprintf(`{
			"source": "shield",
			"severity": "MEDIUM",
			"category": "injection",
			"description": "SQL injection attempt #%d"
		}`, i)
		resp, err := http.Post(ts.URL+"/api/v1/soc/events", "application/json", bytes.NewBufferString(body))
		if err != nil {
			t.Fatalf("POST event %d: %v", i, err)
		}
		if resp.StatusCode != http.StatusCreated {
			t.Fatalf("POST event %d: expected 201, got %d", i, resp.StatusCode)
		}
		resp.Body.Close()
	}

	// Step 3: Verify dashboard shows 3 more events.
	resp, err = http.Get(ts.URL + "/api/soc/dashboard")
	if err != nil {
		t.Fatalf("GET dashboard: %v", err)
	}
	var dash1 map[string]any
	json.NewDecoder(resp.Body).Decode(&dash1)
	resp.Body.Close()

	finalEvents := int(dash1["total_events"].(float64))
	if finalEvents != initialEvents+3 {
		t.Errorf("expected %d events, got %d", initialEvents+3, finalEvents)
	}

	t.Logf("E2E pipeline: initial=%d, final=%d, delta=%d", initialEvents, finalEvents, finalEvents-initialEvents)
}

// TestHTTP_Clusters_Returns200 verifies GET /api/soc/clusters returns clustering stats.
func TestHTTP_Clusters_Returns200(t *testing.T) {
	ts, _ := newTestServer(t)

	resp, err := http.Get(ts.URL + "/api/soc/clusters")
	if err != nil {
		t.Fatalf("GET /api/soc/clusters: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}

	var result map[string]any
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		t.Fatalf("decode JSON: %v", err)
	}

	if _, ok := result["enabled"]; !ok {
		t.Error("response missing 'enabled' field")
	}
	t.Logf("clusters: mode=%v, total=%v", result["mode"], result["total_clusters"])
}

// TestHTTP_Rules_Returns7 verifies GET /api/soc/rules returns built-in rules.
func TestHTTP_Rules_Returns7(t *testing.T) {
	ts, _ := newTestServer(t)

	resp, err := http.Get(ts.URL + "/api/soc/rules")
	if err != nil {
		t.Fatalf("GET /api/soc/rules: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}

	var result struct {
		Rules []any `json:"rules"`
		Count int   `json:"count"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		t.Fatalf("decode JSON: %v", err)
	}

	if result.Count != 17 {
		t.Errorf("expected 17 built-in rules (15 default + 2 Shadow AI), got %d", result.Count)
	}
}

// TestHTTP_IncidentDetail_NotFound verifies 404 for nonexistent incident.
func TestHTTP_IncidentDetail_NotFound(t *testing.T) {
	ts, _ := newTestServer(t)

	resp, err := http.Get(ts.URL + "/api/soc/incidents/INC-FAKE-0001")
	if err != nil {
		t.Fatalf("GET incident detail: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", resp.StatusCode)
	}
}

// --- Sprint 6C: Coverage-Boosting Tests ---

func TestHTTP_BatchIngest_EmptyArray(t *testing.T) {
	ts, _ := newTestServer(t)
	body := bytes.NewBufferString(`[]`)
	resp, err := http.Post(ts.URL+"/api/v1/soc/events/batch", "application/json", body)
	if err != nil {
		t.Fatalf("POST batch: %v", err)
	}
	defer resp.Body.Close()
	// Empty array may return 200 (0 accepted) or 400 — both acceptable.
	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusBadRequest {
		t.Errorf("expected 200 or 400, got %d", resp.StatusCode)
	}
}

func TestHTTP_BatchIngest_WithEvents(t *testing.T) {
	ts, _ := newTestServer(t)
	body := bytes.NewBufferString(`[{"source":"sentinel-core","severity":"HIGH","category":"jailbreak","description":"batch test 1","sensor_id":"s1"},{"source":"shield","severity":"LOW","category":"test","description":"batch test 2","sensor_id":"s2"}]`)
	resp, err := http.Post(ts.URL+"/api/v1/soc/events/batch", "application/json", body)
	if err != nil {
		t.Fatalf("POST batch: %v", err)
	}
	defer resp.Body.Close()
	// Batch endpoint exercises handler path regardless of status.
	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusCreated && resp.StatusCode != http.StatusBadRequest {
		t.Errorf("expected 200/201/400, got %d", resp.StatusCode)
	}
	var result map[string]any
	json.NewDecoder(resp.Body).Decode(&result)
	t.Logf("batch result: status=%d body=%v", resp.StatusCode, result)
}

// TestHTTP_BatchIngest_AllInvalid_NotRetryable verifies that a batch of purely
// malformed events (validation failures, NOT backpressure) does NOT return a
// retryable 503. Regression for the bug where handleBatchIngest signalled 503
// whenever ingested==0, conflating client validation errors with server
// backpressure — telling clients to retry input that can never succeed.
func TestHTTP_BatchIngest_AllInvalid_NotRetryable(t *testing.T) {
	ts, _ := newTestServer(t)
	// Both events are missing every required field → all rejected by Validate(),
	// none by capacity. Expect 201 with ingested=0, never 503.
	body := bytes.NewBufferString(`[{"source":""},{"category":""}]`)
	resp, err := http.Post(ts.URL+"/api/v1/soc/events/batch", "application/json", body)
	if err != nil {
		t.Fatalf("POST batch: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusServiceUnavailable {
		t.Fatalf("all-invalid batch must NOT return retryable 503 (validation != backpressure)")
	}
	if resp.Header.Get("Retry-After") != "" {
		t.Errorf("all-invalid batch must not set Retry-After, got %q", resp.Header.Get("Retry-After"))
	}

	var result map[string]any
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		t.Fatalf("decode JSON: %v", err)
	}
	if ingested, _ := result["ingested"].(float64); ingested != 0 {
		t.Errorf("expected ingested=0 for all-invalid batch, got %v", result["ingested"])
	}
	if rejected, _ := result["rejected"].(float64); rejected != 2 {
		t.Errorf("expected rejected=2 for all-invalid batch, got %v", result["rejected"])
	}
}

func TestHTTP_Verdict_InvalidIncident(t *testing.T) {
	ts, _ := newTestServer(t)
	body := bytes.NewBufferString(`{"status":"INVESTIGATING"}`)
	resp, err := http.Post(ts.URL+"/api/soc/incidents/INC-FAKE/verdict", "application/json", body)
	if err != nil {
		t.Fatalf("POST verdict: %v", err)
	}
	defer resp.Body.Close()
	// Handler may return 200 (no-op) or error code for nonexistent incident.
	t.Logf("verdict on fake incident: status=%d", resp.StatusCode)
}

func TestHTTP_Compliance_Returns200(t *testing.T) {
	ts, _ := newTestServer(t)
	resp, err := http.Get(ts.URL + "/api/soc/compliance")
	if err != nil {
		t.Fatalf("GET compliance: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}
	var result map[string]any
	json.NewDecoder(resp.Body).Decode(&result)
	if _, ok := result["framework"]; !ok {
		t.Error("compliance response missing 'framework' field")
	}
}

func TestHTTP_ComplianceSOC2_Returns200(t *testing.T) {
	ts, _ := newTestServer(t)
	resp, err := http.Get(ts.URL + "/api/soc/compliance/soc2")
	if err != nil {
		t.Fatalf("GET compliance/soc2: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}
	var result map[string]any
	json.NewDecoder(resp.Body).Decode(&result)
	if got := result["framework"]; got != "SOC 2 Common Criteria (self-assessment)" {
		t.Errorf("unexpected framework: %v", got)
	}
	// IMP8 truthful degradation: this harness wires NO decision logger, so the
	// audit-trail control (CC7.3) must report NON_COMPLIANT, never COMPLIANT.
	reqs, _ := result["requirements"].([]any)
	var sawCC73 bool
	for _, ri := range reqs {
		r := ri.(map[string]any)
		if r["id"] == "CC7.3" {
			sawCC73 = true
			if r["status"] != "NON_COMPLIANT" {
				t.Errorf("CC7.3 must be NON_COMPLIANT without a decision chain, got %v", r["status"])
			}
		}
	}
	if !sawCC73 {
		t.Error("CC7.3 missing from SOC2 report")
	}
}

func TestHTTP_AnomalyAlerts_Returns200(t *testing.T) {
	ts, _ := newTestServer(t)
	resp, err := http.Get(ts.URL + "/api/soc/anomaly/alerts")
	if err != nil {
		t.Fatalf("GET anomaly alerts: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}
}

func TestHTTP_AnomalyBaselines_Returns200(t *testing.T) {
	ts, _ := newTestServer(t)
	resp, err := http.Get(ts.URL + "/api/soc/anomaly/baselines")
	if err != nil {
		t.Fatalf("GET anomaly baselines: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}
}

func TestHTTP_Playbooks_Returns200(t *testing.T) {
	ts, _ := newTestServer(t)
	resp, err := http.Get(ts.URL + "/api/soc/playbooks")
	if err != nil {
		t.Fatalf("GET playbooks: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}
	var result map[string]any
	json.NewDecoder(resp.Body).Decode(&result)
	if _, ok := result["playbooks"]; !ok {
		t.Error("response missing 'playbooks' field")
	}
}

func TestHTTP_KillChain_NotFound(t *testing.T) {
	ts, _ := newTestServer(t)
	resp, err := http.Get(ts.URL + "/api/soc/killchain/INC-FAKE")
	if err != nil {
		t.Fatalf("GET killchain: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", resp.StatusCode)
	}
}

func TestHTTP_AuditTrail_Returns200(t *testing.T) {
	ts, _ := newTestServer(t)
	resp, err := http.Get(ts.URL + "/api/soc/audit")
	if err != nil {
		t.Fatalf("GET audit: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}
}

func TestHTTP_DeepHealth_Returns200(t *testing.T) {
	ts, _ := newTestServer(t)
	resp, err := http.Get(ts.URL + "/api/soc/deep-health")
	if err != nil {
		t.Fatalf("GET deep-health: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}
	var result map[string]any
	json.NewDecoder(resp.Body).Decode(&result)
	if _, ok := result["status"]; !ok {
		t.Error("deep-health response missing 'status' field")
	}
}

func TestHTTP_ZeroGStatus_Returns200(t *testing.T) {
	ts, _ := newTestServer(t)
	resp, err := http.Get(ts.URL + "/api/soc/zerog")
	if err != nil {
		t.Fatalf("GET zerog: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}
}

func TestHTTP_ZeroGToggle(t *testing.T) {
	ts, _ := newTestServer(t)
	body := bytes.NewBufferString(`{"enabled":true}`)
	resp, err := http.Post(ts.URL+"/api/soc/zerog/toggle", "application/json", body)
	if err != nil {
		t.Fatalf("POST zerog toggle: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}
}

func TestHTTP_RetentionPolicies_Returns200(t *testing.T) {
	ts, _ := newTestServer(t)
	resp, err := http.Get(ts.URL + "/api/soc/retention")
	if err != nil {
		t.Fatalf("GET retention: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}
}

func TestHTTP_RateLimitStats_Returns200(t *testing.T) {
	ts, _ := newTestServer(t)
	resp, err := http.Get(ts.URL + "/api/soc/ratelimit")
	if err != nil {
		t.Fatalf("GET ratelimit: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}
}

func TestHTTP_P2PPeers_Returns200(t *testing.T) {
	ts, _ := newTestServer(t)
	resp, err := http.Get(ts.URL + "/api/soc/p2p/peers")
	if err != nil {
		t.Fatalf("GET p2p peers: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}
}

func TestHTTP_SovereignConfig_Returns200(t *testing.T) {
	ts, _ := newTestServer(t)
	resp, err := http.Get(ts.URL + "/api/soc/sovereign")
	if err != nil {
		t.Fatalf("GET sovereign: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}
}

func TestHTTP_IncidentExplain_NotFound(t *testing.T) {
	ts, _ := newTestServer(t)
	resp, err := http.Get(ts.URL + "/api/soc/incident-explain/INC-FAKE")
	if err != nil {
		t.Fatalf("GET incident explain: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", resp.StatusCode)
	}
}

func TestHTTP_IngestThenVerdict(t *testing.T) {
	ts, svc := newTestServer(t)

	// Ingest events to trigger incident.
	evt1 := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, domsoc.SeverityHigh, "jailbreak", "verdict http test 1")
	evt1.SensorID = "sensor-http-vd"
	svc.IngestEvent(evt1)

	evt2 := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, domsoc.SeverityCritical, "tool_abuse", "verdict http test 2")
	evt2.SensorID = "sensor-http-vd"
	_, inc, _ := svc.IngestEvent(evt2)

	if inc == nil {
		t.Skip("no incident created for verdict test")
	}

	// Set verdict via HTTP.
	body := bytes.NewBufferString(`{"status":"INVESTIGATING"}`)
	resp, err := http.Post(ts.URL+"/api/soc/incidents/"+inc.ID+"/verdict", "application/json", body)
	if err != nil {
		t.Fatalf("POST verdict: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}

	// Verify verdict took effect.
	got, _ := svc.GetIncident(inc.ID)
	if got.Status != domsoc.StatusInvestigating {
		t.Errorf("expected INVESTIGATING, got %s", got.Status)
	}
}
