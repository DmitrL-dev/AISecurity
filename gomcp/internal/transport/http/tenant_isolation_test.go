package httpserver

import (
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	appsoc "github.com/syntrex/gomcp/internal/application/soc"
	domsoc "github.com/syntrex/gomcp/internal/domain/soc"
	"github.com/syntrex/gomcp/internal/infrastructure/auth"
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"
)

// Review 13.06 (audit): end-to-end integration tests for the SOC tenant-isolation
// and sensor-auth fixes — handler → service → real in-memory SQLite repo, with
// JWT claims injected (the test mux has no JWT middleware, so we set them
// directly, exactly as the middleware would).

func setupIsoSrv(t *testing.T) (*Server, *appsoc.Service) {
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
	svc := appsoc.NewService(repo, nil)
	return New(svc, 0), svc
}

func isoReq(method, target, role, tenant string) *http.Request {
	r := httptest.NewRequest(method, target, nil)
	return r.WithContext(auth.SetClaimsContext(r.Context(), &auth.Claims{Sub: "synthetic-principal", Role: role, TenantID: tenant}))
}

func seedIncident(t *testing.T, svc *appsoc.Service, title, tenant string) domsoc.Incident {
	t.Helper()
	inc := domsoc.NewIncident(title, domsoc.SeverityHigh, "rule")
	inc.TenantID = tenant
	if err := svc.Repo().InsertIncident(inc); err != nil {
		t.Fatalf("insert incident: %v", err)
	}
	return inc
}

// B1 + B4: a tenant cannot read another tenant's incident (opaque 404), but can
// read its own.
func TestTenantIsolation_IncidentIDOR(t *testing.T) {
	srv, svc := setupIsoSrv(t)
	incA := seedIncident(t, svc, "alpha incident", "tnt-a")
	incB := seedIncident(t, svc, "bravo incident", "tnt-b")

	// tenant-A analyst → tenant-B incident → 404
	r := isoReq("GET", "/api/soc/incidents/"+incB.ID, "analyst", "tnt-a")
	r.SetPathValue("id", incB.ID)
	rec := httptest.NewRecorder()
	srv.handleIncidentDetail(rec, r)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("cross-tenant read must be 404, got %d (%s)", rec.Code, rec.Body.String())
	}

	// tenant-A analyst → own incident → 200
	r2 := isoReq("GET", "/api/soc/incidents/"+incA.ID, "analyst", "tnt-a")
	r2.SetPathValue("id", incA.ID)
	rec2 := httptest.NewRecorder()
	srv.handleIncidentDetail(rec2, r2)
	if rec2.Code != http.StatusOK {
		t.Fatalf("own-tenant read must be 200, got %d", rec2.Code)
	}

	// superadmin → any incident → 200
	r3 := isoReq("GET", "/api/soc/incidents/"+incB.ID, "superadmin", "tnt-x")
	r3.SetPathValue("id", incB.ID)
	rec3 := httptest.NewRecorder()
	srv.handleIncidentDetail(rec3, r3)
	if rec3.Code != http.StatusOK {
		t.Fatalf("superadmin cross-tenant read must be 200, got %d", rec3.Code)
	}
}

// B2: the advanced incident list is scoped to the caller's tenant.
func TestTenantIsolation_AdvancedListScoped(t *testing.T) {
	srv, svc := setupIsoSrv(t)
	seedIncident(t, svc, "alpha-incident", "tnt-a")
	seedIncident(t, svc, "bravo-incident", "tnt-b")

	r := isoReq("GET", "/api/soc/incidents/advanced", "viewer", "tnt-a")
	rec := httptest.NewRecorder()
	srv.handleIncidentsAdvanced(rec, r)
	if rec.Code != http.StatusOK {
		t.Fatalf("advanced list status %d", rec.Code)
	}
	body := rec.Body.String()
	if strings.Contains(body, "bravo-incident") {
		t.Fatal("tenant-A advanced list LEAKED a tenant-B incident")
	}
	if !strings.Contains(body, "alpha-incident") {
		t.Fatal("tenant-A advanced list is missing its own incident")
	}

	// superadmin sees both tenants.
	rs := isoReq("GET", "/api/soc/incidents/advanced", "superadmin", "tnt-x")
	recs := httptest.NewRecorder()
	srv.handleIncidentsAdvanced(recs, rs)
	sb := recs.Body.String()
	if !strings.Contains(sb, "alpha-incident") || !strings.Contains(sb, "bravo-incident") {
		t.Fatal("superadmin advanced list must include all tenants")
	}
}

// A4: when sensor keys are configured, ingest rejects wrong/missing keys and
// accepts the correct one (auth gate); when unset, ingest stays keyless.
func TestSensorKeyEnforcement(t *testing.T) {
	_, svc := setupIsoSrv(t)
	svc.SetSensorKeys(map[string]string{"sensorA": "secret1"})

	wrong := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, domsoc.SeverityHigh, "test", "d")
	wrong.SensorID = "sensorA"
	wrong.SensorKey = "nope"
	if _, _, err := svc.IngestEvent(wrong); !errors.Is(err, domsoc.ErrAuthFailed) {
		t.Fatalf("wrong sensor key must fail with ErrAuthFailed, got %v", err)
	}

	right := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, domsoc.SeverityHigh, "test", "d")
	right.SensorID = "sensorA"
	right.SensorKey = "secret1"
	if _, _, err := svc.IngestEvent(right); errors.Is(err, domsoc.ErrAuthFailed) {
		t.Fatalf("valid sensor key must pass the auth gate, got auth error: %v", err)
	}
}

// Input-boundary: a huge ?page value must not overflow (page-1)*limit into a
// negative slice index and panic. Regression for the slice-bounds panic in the
// advanced incident list. Pre-fix this returned 500 via a recovered runtime
// panic ("slice bounds out of range [:-N]"); post-fix the page is clamped and
// the handler returns 200 with an empty page.
func TestIncidentsAdvanced_PageOverflow_NoPanic(t *testing.T) {
	srv, svc := setupIsoSrv(t)
	seedIncident(t, svc, "alpha-incident", "tnt-a")

	// page ~ maxint64/10; (page-1)*20 overflows int64 to a negative start.
	r := isoReq("GET", "/api/soc/incidents/advanced?page=922337203685477580&limit=20", "viewer", "tnt-a")
	rec := httptest.NewRecorder()
	srv.handleIncidentsAdvanced(rec, r)

	if rec.Code != http.StatusOK {
		t.Fatalf("oversized page must be clamped to a 200, got %d (%s)", rec.Code, rec.Body.String())
	}
	// A clamped, out-of-range page yields no incidents (not a leak, not a crash).
	if strings.Contains(rec.Body.String(), "alpha-incident") {
		t.Fatalf("clamped out-of-range page should return an empty page, got %s", rec.Body.String())
	}
}

// A4: ParseSensorKeys parsing (opt-in; empty → nil/keyless).
func TestParseSensorKeys(t *testing.T) {
	if got := appsoc.ParseSensorKeys(""); got != nil {
		t.Fatalf("empty → nil (keyless), got %v", got)
	}
	got := appsoc.ParseSensorKeys("a:k1, b:k2 ,bad,:nokey,noval:")
	if len(got) != 2 || got["a"] != "k1" || got["b"] != "k2" {
		t.Fatalf("parse: got %v", got)
	}
}
