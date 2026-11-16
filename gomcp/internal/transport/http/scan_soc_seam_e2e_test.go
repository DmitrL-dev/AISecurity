package httpserver

import (
	"strings"
	"testing"
	"time"

	appsoc "github.com/syntrex/gomcp/internal/application/soc"
	domsoc "github.com/syntrex/gomcp/internal/domain/soc"
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"
)

// These tests prove the MASTER_PLAN R3 claim end to end — "the gateway IS the
// sensor": a blocked scan from an authenticated tenant auto-feeds that tenant's
// SOC through the real ingest pipeline, persists a REDACTED event (never the raw
// prompt), correlates gateway-fed events into incidents, and NEVER leaks an
// anonymous demo scan into a real tenant's SOC. They drive the production seam
// functions (buildScanSOCEvent / emitScanSOCEvent) directly, so the proof is
// decoupled from the native detector's block decision (a one-line call site).

func newSeamTestService(t *testing.T) (*appsoc.Service, *sqlite.SOCRepo) {
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
	return appsoc.NewService(repo, nil), repo
}

// (The pure build-shape + redaction contract is locked by
// TestBuildScanSOCEvent_RedactsPromptAndAttributesTenant in scan_soc_seam_test.go;
// this file proves the runtime feed end to end.)

// The real async seam: an authenticated tenant's blocked scan must land a
// REDACTED event in that tenant's SOC.
func TestEmitScanSOCEvent_AsyncFeedPersistsRedacted(t *testing.T) {
	svc, repo := newSeamTestService(t)
	s := &Server{socSvc: svc}

	const rawMarker = "RAWMARKER_secret_customer_prompt"
	s.emitScanSOCEvent("tnt-async", "jailbreak", 0.93, rawMarker, []string{"jailbreak"})

	// emit is fire-and-forget; poll until the ingest goroutine persists it.
	var events []domsoc.SOCEvent
	deadline := time.Now().Add(3 * time.Second)
	for time.Now().Before(deadline) {
		events, _ = repo.ListEvents("tnt-async", 100)
		if len(events) >= 1 {
			break
		}
		time.Sleep(10 * time.Millisecond)
	}
	if len(events) == 0 {
		t.Fatal("gateway->SOC async feed did not persist within 3s")
	}

	e := events[0]
	if e.SensorID != "gateway:tnt-async" {
		t.Errorf("persisted SensorID = %q, want gateway:tnt-async", e.SensorID)
	}
	if e.Payload != "" || strings.Contains(e.Description, rawMarker) {
		t.Errorf("persisted event leaked the raw prompt (payload=%q desc=%q)", e.Payload, e.Description)
	}
}

// Gateway-fed events must flow through correlation: three distinct threat
// categories from one tenant's gateway (SOC-CR-002 "Coordinated Attack") must
// raise an incident. Driven synchronously via IngestInternalEvent (what the
// async seam calls) so the assertion is deterministic.
func TestGatewayScanFeed_CorrelatesIntoIncident(t *testing.T) {
	svc, _ := newSeamTestService(t)

	categories := []string{"jailbreak", "injection", "exfiltration"}
	var incident *domsoc.Incident
	for i, cat := range categories {
		evt := buildScanSOCEvent("tnt-corr", cat, 0.95, "distinct prompt "+cat, []string{cat})
		_, inc, err := svc.IngestInternalEvent(evt)
		if err != nil {
			t.Fatalf("ingest %d (%s): %v", i, cat, err)
		}
		if inc != nil {
			incident = inc
		}
	}
	if incident == nil {
		t.Fatal("three distinct gateway-fed categories must correlate into an incident (SOC-CR-002)")
	}
	if incident.Severity != domsoc.SeverityCritical {
		t.Errorf("coordinated-attack incident severity = %v, want Critical", incident.Severity)
	}
}

// The anon-isolation invariant: an anonymous (no-tenant) demo scan must be a
// strict no-op — scan-derived events must NEVER enter a real tenant's SOC.
func TestEmitScanSOCEvent_AnonymousIsNoOp(t *testing.T) {
	svc, repo := newSeamTestService(t)
	s := &Server{socSvc: svc}

	// No tenant => emit returns before spawning any ingest goroutine.
	s.emitScanSOCEvent("", "jailbreak", 0.99, "anon demo prompt", []string{"jailbreak"})
	time.Sleep(50 * time.Millisecond) // give any (erroneously) spawned goroutine time to run

	// Superadmin scope ("") lists across all tenants; it must be empty.
	if events, _ := repo.ListEvents("", 100); len(events) != 0 {
		t.Fatalf("anonymous scan must not create any SOC event, found %d", len(events))
	}
}
