package soc

import (
	"errors"
	"testing"

	domsoc "github.com/syntrex/gomcp/internal/domain/soc"
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"
)

// Review 14.06 R3: the gateway→SOC seam ingests TRUSTED in-process events that
// must bypass sensor-PSK auth (which authenticates EXTERNAL sensors). Verify
// IngestInternalEvent bypasses auth while IngestEvent still enforces it.
func TestIngestInternalEvent_BypassesSensorAuth(t *testing.T) {
	db, err := sqlite.Open(":memory:")
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	defer db.Close()
	repo, err := sqlite.NewSOCRepo(db)
	if err != nil {
		t.Fatalf("repo: %v", err)
	}
	svc := NewService(repo, nil)
	svc.SetSensorKeys(map[string]string{"sensorA": "secret1"}) // auth now enforced for externals

	// External event with no sensor key → rejected.
	ext := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, domsoc.SeverityHigh, "jailbreak", "external probe")
	if _, _, err := svc.IngestEvent(ext); !errors.Is(err, domsoc.ErrAuthFailed) {
		t.Fatalf("external event without key must fail auth, got %v", err)
	}

	// Internal (trusted) event with no sensor key → ingested.
	intl := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, domsoc.SeverityHigh, "jailbreak", "gateway scan blocked: jailbreak")
	intl.TenantID = "tnt-x"
	id, _, err := svc.IngestInternalEvent(intl)
	if errors.Is(err, domsoc.ErrAuthFailed) {
		t.Fatalf("internal event must BYPASS sensor auth, got auth error: %v", err)
	}
	if err != nil {
		t.Fatalf("internal ingest failed: %v", err)
	}
	if id == "" {
		t.Fatal("internal ingest returned empty event id")
	}
}

// Review 14.06 round-5: GDPR Art.17 erasure must remove ALL of one tenant's SOC
// data and ONLY that tenant's — and refuse an empty tenant (never store-wide).
func TestEraseTenant_RemovesOnlyThatTenant(t *testing.T) {
	db, err := sqlite.Open(":memory:")
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	defer db.Close()
	repo, err := sqlite.NewSOCRepo(db)
	if err != nil {
		t.Fatalf("repo: %v", err)
	}
	svc := NewService(repo, nil)

	mk := func(tenant, cat string) {
		e := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, domsoc.SeverityHigh, cat, cat+" "+tenant)
		e.TenantID = tenant
		e.SensorID = "s-" + tenant
		if _, _, err := svc.IngestInternalEvent(e); err != nil {
			t.Fatalf("ingest %s/%s: %v", tenant, cat, err)
		}
	}
	mk("tnt-a", "jailbreak")
	mk("tnt-a", "injection")
	mk("tnt-b", "jailbreak")

	rows, err := svc.EraseTenant("tnt-a")
	if err != nil {
		t.Fatalf("erase: %v", err)
	}
	if rows == 0 {
		t.Fatal("expected rows deleted for tnt-a")
	}

	if ev, _ := repo.ListEvents("tnt-a", 100); len(ev) != 0 {
		t.Fatalf("tnt-a events must be fully erased, got %d", len(ev))
	}
	if ev, _ := repo.ListEvents("tnt-b", 100); len(ev) == 0 {
		t.Fatal("tnt-b events must survive erasure of tnt-a")
	}

	// Idempotent re-run is harmless; empty tenant is refused (never store-wide).
	if _, err := svc.EraseTenant("tnt-a"); err != nil {
		t.Fatalf("idempotent re-erase must not error: %v", err)
	}
	if _, err := svc.EraseTenant(""); err == nil {
		t.Fatal("empty tenant_id must be refused")
	}
}

// Review 14.06 round-2: Analytics must scope to the caller's tenant (it
// previously hardcoded "" and leaked all-tenant aggregates to any viewer).
func TestAnalytics_TenantScoped(t *testing.T) {
	db, err := sqlite.Open(":memory:")
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	defer db.Close()
	repo, err := sqlite.NewSOCRepo(db)
	if err != nil {
		t.Fatalf("repo: %v", err)
	}
	svc := NewService(repo, nil)

	mk := func(tenant, cat, desc string) {
		e := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, domsoc.SeverityHigh, cat, desc)
		e.TenantID = tenant
		if _, _, err := svc.IngestInternalEvent(e); err != nil {
			t.Fatalf("ingest: %v", err)
		}
	}
	mk("tnt-a", "jailbreak", "a1")
	mk("tnt-a", "jailbreak", "a2")
	mk("tnt-b", "injection", "b1")
	mk("tnt-b", "injection", "b2")

	cats := func(r *AnalyticsReport) map[string]bool {
		m := map[string]bool{}
		for _, c := range r.TopCategories {
			m[c.Category] = true
		}
		return m
	}
	ra, _ := svc.Analytics("tnt-a", 24)
	rb, _ := svc.Analytics("tnt-b", 24)
	rall, _ := svc.Analytics("", 24)

	if c := cats(ra); c["injection"] || !c["jailbreak"] {
		t.Fatalf("tnt-a analytics leaked tnt-b or missing own: %v", c)
	}
	if c := cats(rb); c["jailbreak"] || !c["injection"] {
		t.Fatalf("tnt-b analytics leaked tnt-a or missing own: %v", c)
	}
	if c := cats(rall); !c["jailbreak"] || !c["injection"] {
		t.Fatalf("superadmin (empty scope) analytics must see all: %v", c)
	}
}
