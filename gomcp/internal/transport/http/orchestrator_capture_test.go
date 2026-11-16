package httpserver

import (
	"bufio"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/syntrex/gomcp/internal/domain/orchestrator"
	domsoc "github.com/syntrex/gomcp/internal/domain/soc"
	"github.com/syntrex/gomcp/internal/infrastructure/auth"
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"
)

func newSQLiteOrchRepoForTest(t *testing.T) *sqlite.OrchestratorRepo {
	t.Helper()
	db, err := sqlite.OpenMemory()
	if err != nil {
		t.Fatalf("open memory db: %v", err)
	}
	t.Cleanup(func() { db.Close() })
	repo, err := sqlite.NewOrchestratorRepo(db)
	if err != nil {
		t.Fatalf("new orchestrator repo: %v", err)
	}
	return repo
}

func mustInsertLabeled(t *testing.T, repo *sqlite.OrchestratorRepo, tenant, hash string, ts time.Time, label orchestrator.Label) {
	t.Helper()
	labeledAt := ts
	s := orchestrator.Sample{
		ID:           orchestrator.GenID("orch"),
		TenantID:     tenant,
		Timestamp:    ts,
		PromptHash:   hash,
		EngineScores: map[string]float64{"prompt_injection": 0.9},
		Aggregate:    orchestrator.AggregateFeatures{Risk: 0.9, CoreConfidence: 0.9, EnginesTriggered: 1, CoreBlocked: true},
		VectorSchema: orchestrator.VectorSchema,
		Blocked:      true,
		Risk:         0.9,
		ThreatType:   "prompt_injection",
		Label:        label,
		LabelSource:  "test",
		LabeledAt:    &labeledAt,
	}
	if err := repo.Insert(s); err != nil {
		t.Fatalf("insert labeled sample: %v", err)
	}
}

// mockOrchRepo is an in-memory orchestrator.Repository for the seam tests.
type mockOrchRepo struct {
	mu       sync.Mutex
	inserts  []orchestrator.Sample
	attached []attachCall
}

type attachCall struct {
	tenant string
	from   time.Time
	to     time.Time
	label  orchestrator.Label
	source string
}

func (m *mockOrchRepo) Insert(s orchestrator.Sample) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.inserts = append(m.inserts, s)
	return nil
}

func (m *mockOrchRepo) AttachLabel(tenantID string, from, to time.Time, label orchestrator.Label, source string) (int64, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.attached = append(m.attached, attachCall{tenantID, from, to, label, source})
	return 1, nil
}

func (m *mockOrchRepo) ExportLabeled(tenantID string, limit int, onlyLabeled bool) ([]orchestrator.Sample, error) {
	return nil, nil
}
func (m *mockOrchRepo) CountSamples(tenantID string) (int64, int64, error) { return 0, 0, nil }
func (m *mockOrchRepo) PurgeExpired(retentionDays int) (int64, error)      { return 0, nil }
func (m *mockOrchRepo) DeleteByTenant(tenantID string) (int64, error)      { return 0, nil }

func (m *mockOrchRepo) insertCount() int {
	m.mu.Lock()
	defer m.mu.Unlock()
	return len(m.inserts)
}

func (m *mockOrchRepo) lastInsert() (orchestrator.Sample, bool) {
	m.mu.Lock()
	defer m.mu.Unlock()
	if len(m.inserts) == 0 {
		return orchestrator.Sample{}, false
	}
	return m.inserts[len(m.inserts)-1], true
}

func (m *mockOrchRepo) lastAttach() (attachCall, bool) {
	m.mu.Lock()
	defer m.mu.Unlock()
	if len(m.attached) == 0 {
		return attachCall{}, false
	}
	return m.attached[len(m.attached)-1], true
}

// waitFor polls until cond() or the deadline (the seam fires async goroutines).
func waitFor(cond func() bool) bool {
	deadline := time.Now().Add(2 * time.Second)
	for time.Now().Before(deadline) {
		if cond() {
			return true
		}
		time.Sleep(5 * time.Millisecond)
	}
	return cond()
}

func testCaptureInputs(tenant string) captureInputs {
	return captureInputs{
		tenantID:         tenant,
		promptHash:       "deadbeef",
		risk:             0.95,
		blocked:          true,
		threatType:       "prompt_injection",
		indicators:       []string{"prompt_injection/ignore (95%)", "shield/payload"},
		coreConfidence:   0.95,
		shieldConfidence: 0.10,
		mlConfidence:     0.0,
		coreBlocked:      true,
		modelVersion:     "sentinel-core/1.0",
	}
}

// REQUIREMENT: capture disabled → no-op on the scan path (nothing written).
func TestCapture_DisabledIsNoOp(t *testing.T) {
	// Ensure the gate is OFF (default), explicitly.
	t.Setenv("ORCHESTRATOR_CAPTURE_ENABLED", "0")
	mock := &mockOrchRepo{}
	srv := New(nil, 0)
	srv.SetOrchestratorRepo(mock)

	srv.captureOrchestratorSample(testCaptureInputs("tenant-a"))

	// Give any (erroneous) goroutine a chance — it must NOT write.
	time.Sleep(50 * time.Millisecond)
	if n := mock.insertCount(); n != 0 {
		t.Fatalf("capture disabled must write nothing, got %d inserts", n)
	}
}

// REQUIREMENT: capture enabled → writes a correct row (mock).
func TestCapture_EnabledWritesCorrectRow(t *testing.T) {
	t.Setenv("ORCHESTRATOR_CAPTURE_ENABLED", "1")
	mock := &mockOrchRepo{}
	srv := New(nil, 0)
	srv.SetOrchestratorRepo(mock)

	srv.captureOrchestratorSample(testCaptureInputs("tenant-a"))

	if !waitFor(func() bool { return mock.insertCount() == 1 }) {
		t.Fatalf("capture enabled must write 1 row, got %d", mock.insertCount())
	}
	s, _ := mock.lastInsert()
	if s.TenantID != "tenant-a" {
		t.Errorf("tenant: want tenant-a, got %q", s.TenantID)
	}
	if s.PromptHash != "deadbeef" {
		t.Errorf("prompt hash: want deadbeef, got %q", s.PromptHash)
	}
	if !s.Blocked || s.ThreatType != "prompt_injection" {
		t.Errorf("verdict not captured: %+v", s)
	}
	// Sparse per-engine score parsed from indicators; shield (no %) excluded.
	if s.EngineScores["prompt_injection"] != 0.95 {
		t.Errorf("engine score not parsed: %v", s.EngineScores)
	}
	if _, ok := s.EngineScores["shield"]; ok {
		t.Errorf("shield indicator without %% must not become an engine score: %v", s.EngineScores)
	}
	if s.Aggregate.EnginesTriggered != 1 {
		t.Errorf("engines_triggered should be 1 (distinct parsed engines), got %d", s.Aggregate.EnginesTriggered)
	}
	if s.VectorComplete {
		t.Error("vector must be marked incomplete (aggregate-only) today")
	}
	if s.Label != orchestrator.LabelUnlabeled {
		t.Errorf("new sample must be unlabeled, got %q", s.Label)
	}
}

// REQUIREMENT: anonymous (no tenant) capture is a no-op even when enabled.
func TestCapture_AnonymousIsNoOp(t *testing.T) {
	t.Setenv("ORCHESTRATOR_CAPTURE_ENABLED", "1")
	mock := &mockOrchRepo{}
	srv := New(nil, 0)
	srv.SetOrchestratorRepo(mock)

	srv.captureOrchestratorSample(testCaptureInputs("")) // empty tenant

	time.Sleep(50 * time.Millisecond)
	if n := mock.insertCount(); n != 0 {
		t.Fatalf("anonymous capture must write nothing, got %d", n)
	}
}

// REQUIREMENT: the privacy invariant — buildSample never carries the raw prompt.
func TestBuildSample_NoRawPrompt(t *testing.T) {
	in := testCaptureInputs("tenant-a")
	s := buildSample(in)
	blob, _ := json.Marshal(s)
	// The hash is present; no raw-prompt field should exist. (buildSample is only
	// ever handed a hash, never the prompt — this asserts the shape can't carry one.)
	if !strings.Contains(string(blob), "deadbeef") {
		t.Error("prompt hash should be present in the serialized sample")
	}
	if strings.Contains(strings.ToLower(string(blob)), `"prompt"`) ||
		strings.Contains(strings.ToLower(string(blob)), `"payload"`) {
		t.Errorf("serialized sample must not contain a prompt/payload field: %s", blob)
	}
}

// denseVector returns a fixed-order 39-slot per-engine vector for tests, with a
// couple of non-zero slots so we can assert the exact bytes survive the projection.
func denseVector() []float64 {
	v := make([]float64, orchestrator.DenseVectorLen)
	v[0] = 0.91
	v[5] = 0.42
	v[orchestrator.DenseVectorLen-1] = 0.73
	return v
}

// REQUIREMENT: when the bridge supplies a dense 39-vector, the captured sample
// stores it as EngineVector with VectorComplete=true and the dense-v1 schema (the
// real per-engine training feature) — while still parsing the sparse scores.
func TestBuildSample_DenseVectorComplete(t *testing.T) {
	in := testCaptureInputs("tenant-a")
	in.engineVector = denseVector()

	s := buildSample(in)

	if !s.VectorComplete {
		t.Fatal("dense 39-vector present → VectorComplete must be true")
	}
	if s.VectorSchema != orchestrator.DenseVectorSchema {
		t.Errorf("schema: want %q, got %q", orchestrator.DenseVectorSchema, s.VectorSchema)
	}
	if len(s.EngineVector) != orchestrator.DenseVectorLen {
		t.Fatalf("EngineVector len: want %d, got %d", orchestrator.DenseVectorLen, len(s.EngineVector))
	}
	if s.EngineVector[0] != 0.91 || s.EngineVector[5] != 0.42 || s.EngineVector[orchestrator.DenseVectorLen-1] != 0.73 {
		t.Errorf("dense vector bytes not preserved: %v", s.EngineVector)
	}
	// Sparse scores are still parsed from indicators alongside the dense vector.
	if s.EngineScores["prompt_injection"] != 0.95 {
		t.Errorf("sparse scores should still be parsed: %v", s.EngineScores)
	}

	// The export row carries the dense vector at full weight (1.0).
	row := s.ToExportRow()
	if !row.VectorComplete || row.VectorSchema != orchestrator.DenseVectorSchema {
		t.Errorf("export row should reflect dense schema: complete=%v schema=%q", row.VectorComplete, row.VectorSchema)
	}
	if len(row.Vector) != orchestrator.DenseVectorLen {
		t.Errorf("export vector should be the dense one (len %d), got %d", orchestrator.DenseVectorLen, len(row.Vector))
	}
	if row.Weight != 1.0 {
		t.Errorf("dense row weight: want 1.0, got %v", row.Weight)
	}
}

// REQUIREMENT: when no dense vector is supplied (older/stub bridge), the aggregate
// fallback is UNCHANGED: VectorComplete=false, agg-v1 schema, no EngineVector.
func TestBuildSample_AbsentDenseFallsBackToAggregate(t *testing.T) {
	in := testCaptureInputs("tenant-a") // engineVector left nil
	s := buildSample(in)

	if s.VectorComplete {
		t.Error("absent dense vector → VectorComplete must stay false (aggregate fallback)")
	}
	if s.VectorSchema != orchestrator.VectorSchema {
		t.Errorf("schema: want aggregate %q, got %q", orchestrator.VectorSchema, s.VectorSchema)
	}
	if len(s.EngineVector) != 0 {
		t.Errorf("no dense vector should be stored, got %v", s.EngineVector)
	}
	// Export falls back to the aggregate vector at the down-weighted 0.5.
	row := s.ToExportRow()
	if row.VectorComplete || row.Weight != 0.5 {
		t.Errorf("aggregate fallback export: complete=%v weight=%v", row.VectorComplete, row.Weight)
	}
}

// REQUIREMENT: a wrong-length vector (e.g. an older sentinel binary emitting a
// short/mismatched vector) is REJECTED — it must not be stored as dense; the row
// falls back to the aggregate layout so the schema/dimension contract holds.
func TestBuildSample_WrongLengthDenseRejected(t *testing.T) {
	in := testCaptureInputs("tenant-a")
	in.engineVector = []float64{0.1, 0.2, 0.3} // not DenseVectorLen

	s := buildSample(in)

	if s.VectorComplete {
		t.Error("wrong-length vector must not be treated as complete dense")
	}
	if s.VectorSchema != orchestrator.VectorSchema {
		t.Errorf("wrong-length vector must keep aggregate schema, got %q", s.VectorSchema)
	}
	if len(s.EngineVector) != 0 {
		t.Errorf("wrong-length vector must not be stored, got %v", s.EngineVector)
	}
}

// REQUIREMENT: label-attach maps disposition status → correct supervised label.
func TestAttachLabel_StatusMapping(t *testing.T) {
	mock := &mockOrchRepo{}
	srv := New(nil, 0)
	srv.SetOrchestratorRepo(mock)

	now := time.Now()
	inc := &domsoc.Incident{TenantID: "tenant-a", CreatedAt: now, FirstEventAt: now}

	// FALSE_POSITIVE → benign (blocked scan that was actually safe).
	srv.attachOrchestratorLabel(inc, domsoc.StatusFalsePositive)
	if !waitFor(func() bool { _, ok := mock.lastAttach(); return ok }) {
		t.Fatal("FALSE_POSITIVE should trigger a label-attach")
	}
	a, _ := mock.lastAttach()
	if a.label != orchestrator.LabelBenign {
		t.Errorf("FALSE_POSITIVE → want benign, got %q", a.label)
	}
	if a.tenant != "tenant-a" || a.source != "incident:FALSE_POSITIVE" {
		t.Errorf("attach call mismatch: %+v", a)
	}

	// RESOLVED → malicious (confirmed real threat).
	mock.attached = nil
	srv.attachOrchestratorLabel(inc, domsoc.StatusResolved)
	if !waitFor(func() bool { _, ok := mock.lastAttach(); return ok }) {
		t.Fatal("RESOLVED should trigger a label-attach")
	}
	a2, _ := mock.lastAttach()
	if a2.label != orchestrator.LabelMalicious {
		t.Errorf("RESOLVED → want malicious, got %q", a2.label)
	}
}

// REQUIREMENT: a non-terminal status (e.g. INVESTIGATING) must NOT label anything.
func TestAttachLabel_NonTerminalNoOp(t *testing.T) {
	mock := &mockOrchRepo{}
	srv := New(nil, 0)
	srv.SetOrchestratorRepo(mock)
	inc := &domsoc.Incident{TenantID: "tenant-a", CreatedAt: time.Now()}

	srv.attachOrchestratorLabel(inc, domsoc.StatusInvestigating)
	time.Sleep(50 * time.Millisecond)
	if _, ok := mock.lastAttach(); ok {
		t.Error("INVESTIGATING must not trigger a label-attach")
	}
}

// REQUIREMENT: export is admin-gated. A viewer/analyst is forbidden; an admin is allowed.
func TestExport_AdminGated(t *testing.T) {
	mock := &mockOrchRepo{}
	srv := New(nil, 0)
	srv.SetOrchestratorRepo(mock)

	// Route exactly as registered: RBAC(admin) → requireSOC → handler. tenantStore
	// is nil here so requireSOC passes through (its documented test behavior).
	routed := srv.rbac.Require(RoleAdmin, srv.requireSOC(srv.handleOrchestratorTrainingExport))

	for _, c := range []struct {
		role string
		want int
	}{
		{"viewer", http.StatusForbidden},
		{"analyst", http.StatusForbidden},
		{"admin", http.StatusOK},
		{"superadmin", http.StatusOK},
	} {
		req := httptest.NewRequest("GET", "/api/admin/orchestrator/training-export", nil)
		req = req.WithContext(auth.SetClaimsContext(req.Context(), &auth.Claims{Sub: "synthetic-principal", Role: c.role, TenantID: "tenant-a"}))
		rec := httptest.NewRecorder()
		routed(rec, req)
		if rec.Code != c.want {
			t.Errorf("role %q: want %d, got %d (%s)", c.role, c.want, rec.Code, rec.Body.String())
		}
	}
}

// REQUIREMENT: export is tenant-scoped + emits valid JSONL. Uses the real sqlite repo.
func TestExport_TenantScopedValidJSONL(t *testing.T) {
	repo := newSQLiteOrchRepoForTest(t)
	srv := New(nil, 0)
	srv.SetOrchestratorRepo(repo)

	now := time.Now()
	// Two labeled rows for tenant-a, one labeled row for tenant-b.
	mustInsertLabeled(t, repo, "tenant-a", "a1", now, orchestrator.LabelMalicious)
	mustInsertLabeled(t, repo, "tenant-a", "a2", now, orchestrator.LabelBenign)
	mustInsertLabeled(t, repo, "tenant-b", "b1", now, orchestrator.LabelMalicious)

	// tenant-a admin exports → sees ONLY tenant-a rows.
	req := httptest.NewRequest("GET", "/api/admin/orchestrator/training-export", nil)
	req = req.WithContext(auth.SetClaimsContext(req.Context(), &auth.Claims{Sub: "synthetic-principal", Role: "admin", TenantID: "tenant-a"}))
	rec := httptest.NewRecorder()
	srv.handleOrchestratorTrainingExport(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("export: want 200, got %d (%s)", rec.Code, rec.Body.String())
	}
	if ct := rec.Header().Get("Content-Type"); ct != "application/x-ndjson" {
		t.Errorf("content-type: want application/x-ndjson, got %q", ct)
	}

	// Parse every line as a valid ExportRow.
	var rows []orchestrator.ExportRow
	sc := bufio.NewScanner(strings.NewReader(rec.Body.String()))
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())
		if line == "" {
			continue
		}
		var row orchestrator.ExportRow
		if err := json.Unmarshal([]byte(line), &row); err != nil {
			t.Fatalf("invalid JSONL line %q: %v", line, err)
		}
		rows = append(rows, row)
	}
	if len(rows) != 2 {
		t.Fatalf("tenant-a export must contain exactly its 2 labeled rows, got %d", len(rows))
	}
	for _, row := range rows {
		if row.TenantID != "tenant-a" {
			t.Errorf("cross-tenant leak: export contains tenant %q", row.TenantID)
		}
		if row.Label == orchestrator.LabelUnlabeled {
			t.Errorf("labeled-only export contains an unlabeled row: %+v", row)
		}
		if len(row.Vector) == 0 {
			t.Errorf("export row must carry a feature vector: %+v", row)
		}
		if row.Weight <= 0 {
			t.Errorf("export row must carry a positive weight: %+v", row)
		}
	}
}

// REQUIREMENT: cross-tenant export requires platform admin (scope-lock).
func TestExport_CrossTenantRequiresSuperadmin(t *testing.T) {
	repo := newSQLiteOrchRepoForTest(t)
	srv := New(nil, 0)
	srv.SetOrchestratorRepo(repo)
	mustInsertLabeled(t, repo, "tenant-b", "b1", time.Now(), orchestrator.LabelMalicious)

	// tenant-a ADMIN tries to read tenant-b via ?tenant_id= → forbidden.
	req := httptest.NewRequest("GET", "/api/admin/orchestrator/training-export?tenant_id=tenant-b", nil)
	req = req.WithContext(auth.SetClaimsContext(req.Context(), &auth.Claims{Sub: "synthetic-principal", Role: "admin", TenantID: "tenant-a"}))
	rec := httptest.NewRecorder()
	srv.handleOrchestratorTrainingExport(rec, req)
	if rec.Code != http.StatusForbidden {
		t.Fatalf("non-superadmin cross-tenant export must be 403, got %d (%s)", rec.Code, rec.Body.String())
	}

	// SUPERADMIN may target tenant-b.
	req2 := httptest.NewRequest("GET", "/api/admin/orchestrator/training-export?tenant_id=tenant-b", nil)
	req2 = req2.WithContext(auth.SetClaimsContext(req2.Context(), &auth.Claims{Sub: "synthetic-principal", Role: "superadmin", TenantID: "tenant-a"}))
	rec2 := httptest.NewRecorder()
	srv.handleOrchestratorTrainingExport(rec2, req2)
	if rec2.Code != http.StatusOK {
		t.Fatalf("superadmin cross-tenant export must be 200, got %d (%s)", rec2.Code, rec2.Body.String())
	}
}

// REQUIREMENT: export with no tenant context is refused.
func TestExport_NoTenantRefused(t *testing.T) {
	repo := newSQLiteOrchRepoForTest(t)
	srv := New(nil, 0)
	srv.SetOrchestratorRepo(repo)

	req := httptest.NewRequest("GET", "/api/admin/orchestrator/training-export", nil)
	req = req.WithContext(auth.SetClaimsContext(req.Context(), &auth.Claims{Sub: "synthetic-principal", Role: "admin", TenantID: ""}))
	rec := httptest.NewRecorder()
	srv.handleOrchestratorTrainingExport(rec, req)
	if rec.Code != http.StatusForbidden {
		t.Fatalf("export with no tenant must be 403, got %d", rec.Code)
	}
}

// Unwired repo → export returns 503 (honest unavailable).
func TestExport_UnwiredReturns503(t *testing.T) {
	srv := New(nil, 0) // no SetOrchestratorRepo
	req := httptest.NewRequest("GET", "/api/admin/orchestrator/training-export", nil)
	req = req.WithContext(auth.SetClaimsContext(req.Context(), &auth.Claims{Sub: "synthetic-principal", Role: "admin", TenantID: "tenant-a"}))
	rec := httptest.NewRecorder()
	srv.handleOrchestratorTrainingExport(rec, req)
	if rec.Code != http.StatusServiceUnavailable {
		t.Fatalf("unwired export must be 503, got %d", rec.Code)
	}
}
