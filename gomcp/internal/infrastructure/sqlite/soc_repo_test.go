package sqlite

import (
	"testing"
	"time"

	"github.com/syntrex/gomcp/internal/domain/soc"
)

func setupSOCRepo(t *testing.T) *SOCRepo {
	t.Helper()
	db, err := OpenMemory()
	if err != nil {
		t.Fatalf("open memory db: %v", err)
	}
	t.Cleanup(func() { db.Close() })

	repo, err := NewSOCRepo(db)
	if err != nil {
		t.Fatalf("new soc repo: %v", err)
	}
	return repo
}

// === Event Tests ===

func TestInsertAndListEvents(t *testing.T) {
	repo := setupSOCRepo(t)

	e1 := soc.NewSOCEvent(soc.SourceSentinelCore, soc.SeverityHigh, "jailbreak", "Jailbreak detected").
		WithSensor("core-01").WithConfidence(0.95)
	e2 := soc.NewSOCEvent(soc.SourceShield, soc.SeverityMedium, "network_block", "Connection blocked").
		WithSensor("shield-01")

	if err := repo.InsertEvent(e1); err != nil {
		t.Fatalf("insert e1: %v", err)
	}
	if err := repo.InsertEvent(e2); err != nil {
		t.Fatalf("insert e2: %v", err)
	}

	events, err := repo.ListEvents("", 10)
	if err != nil {
		t.Fatalf("list events: %v", err)
	}
	if len(events) != 2 {
		t.Errorf("expected 2 events, got %d", len(events))
	}

	count, err := repo.CountEvents("")
	if err != nil {
		t.Fatalf("count: %v", err)
	}
	if count != 2 {
		t.Errorf("expected count 2, got %d", count)
	}
}

func TestListEventsByCategory(t *testing.T) {
	repo := setupSOCRepo(t)

	e1 := soc.NewSOCEvent(soc.SourceSentinelCore, soc.SeverityHigh, "jailbreak", "test")
	repo.InsertEvent(e1)
	time.Sleep(time.Millisecond)
	e2 := soc.NewSOCEvent(soc.SourceSentinelCore, soc.SeverityMedium, "injection", "test")
	repo.InsertEvent(e2)
	time.Sleep(time.Millisecond)
	e3 := soc.NewSOCEvent(soc.SourceSentinelCore, soc.SeverityLow, "jailbreak", "test2")
	repo.InsertEvent(e3)

	events, err := repo.ListEventsByCategory("", "jailbreak", 10)
	if err != nil {
		t.Fatalf("list by category: %v", err)
	}
	if len(events) != 2 {
		t.Errorf("expected 2 jailbreak events, got %d", len(events))
	}
}

// === Incident Tests ===

func TestInsertAndGetIncident(t *testing.T) {
	repo := setupSOCRepo(t)

	inc := soc.NewIncident("Multi-stage Jailbreak", soc.SeverityCritical, "jailbreak_chain")
	inc.SetAnchor("abc123", 5)

	if err := repo.InsertIncident(inc); err != nil {
		t.Fatalf("insert incident: %v", err)
	}

	got, err := repo.GetIncident(inc.ID)
	if err != nil {
		t.Fatalf("get incident: %v", err)
	}
	if got.ID != inc.ID {
		t.Errorf("ID mismatch: got %s, want %s", got.ID, inc.ID)
	}
	if got.DecisionChainAnchor != "abc123" {
		t.Errorf("anchor mismatch: got %s", got.DecisionChainAnchor)
	}
	if got.ChainLength != 5 {
		t.Errorf("chain length: got %d, want 5", got.ChainLength)
	}
}

// Review 13.06 (audit): tenant_id MUST round-trip Insert→Get, or the
// getSecureIncident IDOR guard (inc.TenantID == caller tenant) is a no-op.
func TestGetIncident_TenantIDRoundTrips(t *testing.T) {
	repo := setupSOCRepo(t)
	inc := soc.NewIncident("Tenant Scoped", soc.SeverityHigh, "rule")
	inc.TenantID = "tnt-abc-123"
	if err := repo.InsertIncident(inc); err != nil {
		t.Fatalf("insert: %v", err)
	}
	got, err := repo.GetIncident(inc.ID)
	if err != nil {
		t.Fatalf("get: %v", err)
	}
	if got.TenantID != "tnt-abc-123" {
		t.Fatalf("tenant_id did not round-trip: got %q want %q", got.TenantID, "tnt-abc-123")
	}
}

func TestUpdateIncidentStatus(t *testing.T) {
	repo := setupSOCRepo(t)

	inc := soc.NewIncident("Test", soc.SeverityHigh, "test_rule")
	repo.InsertIncident(inc)

	if err := repo.UpdateIncidentStatus(inc.ID, soc.StatusResolved); err != nil {
		t.Fatalf("update status: %v", err)
	}

	got, err := repo.GetIncident(inc.ID)
	if err != nil {
		t.Fatalf("get after update: %v", err)
	}
	if got.Status != soc.StatusResolved {
		t.Errorf("expected RESOLVED, got %s", got.Status)
	}
	if got.ResolvedAt == nil {
		t.Error("resolved_at should be set")
	}
}

func TestListIncidentsWithFilter(t *testing.T) {
	repo := setupSOCRepo(t)

	inc1 := soc.NewIncident("Open Inc", soc.SeverityHigh, "rule1")
	inc2 := soc.NewIncident("Resolved Inc", soc.SeverityMedium, "rule2")
	repo.InsertIncident(inc1)
	repo.InsertIncident(inc2)
	repo.UpdateIncidentStatus(inc2.ID, soc.StatusResolved)

	// List OPEN only
	open, err := repo.ListIncidents("", "OPEN", 10)
	if err != nil {
		t.Fatalf("list open: %v", err)
	}
	if len(open) != 1 {
		t.Errorf("expected 1 open incident, got %d", len(open))
	}

	// List all
	all, err := repo.ListIncidents("", "", 10)
	if err != nil {
		t.Fatalf("list all: %v", err)
	}
	if len(all) != 2 {
		t.Errorf("expected 2 total incidents, got %d", len(all))
	}
}

func TestCountOpenIncidents(t *testing.T) {
	repo := setupSOCRepo(t)

	inc1 := soc.NewIncident("Open", soc.SeverityHigh, "r1")
	inc2 := soc.NewIncident("Investigating", soc.SeverityMedium, "r2")
	inc3 := soc.NewIncident("Resolved", soc.SeverityLow, "r3")
	repo.InsertIncident(inc1)
	repo.InsertIncident(inc2)
	repo.InsertIncident(inc3)
	repo.UpdateIncidentStatus(inc2.ID, soc.StatusInvestigating)
	repo.UpdateIncidentStatus(inc3.ID, soc.StatusResolved)

	count, err := repo.CountOpenIncidents("")
	if err != nil {
		t.Fatalf("count open: %v", err)
	}
	if count != 2 {
		t.Errorf("expected 2 open (OPEN+INVESTIGATING), got %d", count)
	}
}

// === Sensor Tests ===

func TestUpsertAndGetSensor(t *testing.T) {
	repo := setupSOCRepo(t)

	s := soc.NewSensor("core-01", soc.SensorTypeSentinelCore)
	s.RecordEvent()
	s.RecordEvent()
	s.RecordEvent() // Should be HEALTHY

	if err := repo.UpsertSensor(s); err != nil {
		t.Fatalf("upsert: %v", err)
	}

	got, err := repo.GetSensor("core-01")
	if err != nil {
		t.Fatalf("get sensor: %v", err)
	}
	if got.Status != soc.SensorStatusHealthy {
		t.Errorf("expected HEALTHY, got %s", got.Status)
	}
	if got.EventCount != 3 {
		t.Errorf("expected 3 events, got %d", got.EventCount)
	}
}

// Review 14.06 round-5: sensor rows were never purged (unbounded + GDPR
// residual). PurgeStaleSensors removes sensors not seen within the window.
func TestPurgeStaleSensors(t *testing.T) {
	repo := setupSOCRepo(t)

	stale := soc.NewSensor("old-01", soc.SensorTypeSentinelCore)
	stale.LastSeen = time.Now().AddDate(0, 0, -200)
	fresh := soc.NewSensor("new-01", soc.SensorTypeSentinelCore)
	fresh.LastSeen = time.Now()
	if err := repo.UpsertSensor(stale); err != nil {
		t.Fatalf("upsert stale: %v", err)
	}
	if err := repo.UpsertSensor(fresh); err != nil {
		t.Fatalf("upsert fresh: %v", err)
	}

	n, err := repo.PurgeStaleSensors(90)
	if err != nil {
		t.Fatalf("purge: %v", err)
	}
	if n != 1 {
		t.Fatalf("expected 1 stale sensor purged, got %d", n)
	}
	if _, err := repo.GetSensor("old-01"); err == nil {
		t.Fatal("stale sensor should have been purged")
	}
	if _, err := repo.GetSensor("new-01"); err != nil {
		t.Fatalf("fresh sensor must survive: %v", err)
	}
}

func TestSensorUpsertUpdate(t *testing.T) {
	repo := setupSOCRepo(t)

	s := soc.NewSensor("shield-01", soc.SensorTypeShield)
	repo.UpsertSensor(s)

	// Update with new status
	s.RecordEvent()
	s.RecordEvent()
	s.RecordEvent()
	repo.UpsertSensor(s)

	got, err := repo.GetSensor("shield-01")
	if err != nil {
		t.Fatalf("get sensor: %v", err)
	}
	if got.EventCount != 3 {
		t.Errorf("upsert should update event_count, got %d", got.EventCount)
	}
}

func TestListSensors(t *testing.T) {
	repo := setupSOCRepo(t)

	repo.UpsertSensor(soc.NewSensor("core-01", soc.SensorTypeSentinelCore))
	repo.UpsertSensor(soc.NewSensor("shield-01", soc.SensorTypeShield))

	sensors, err := repo.ListSensors("")
	if err != nil {
		t.Fatalf("list: %v", err)
	}
	if len(sensors) != 2 {
		t.Errorf("expected 2, got %d", len(sensors))
	}
}

func TestCountSensorsByStatus(t *testing.T) {
	repo := setupSOCRepo(t)

	s1 := soc.NewSensor("core-01", soc.SensorTypeSentinelCore)
	s1.RecordEvent()
	s1.RecordEvent()
	s1.RecordEvent() // HEALTHY

	s2 := soc.NewSensor("shield-01", soc.SensorTypeShield) // UNKNOWN

	repo.UpsertSensor(s1)
	repo.UpsertSensor(s2)

	counts, err := repo.CountSensorsByStatus("")
	if err != nil {
		t.Fatalf("count by status: %v", err)
	}
	if counts[soc.SensorStatusHealthy] != 1 {
		t.Errorf("expected 1 HEALTHY, got %d", counts[soc.SensorStatusHealthy])
	}
	if counts[soc.SensorStatusUnknown] != 1 {
		t.Errorf("expected 1 UNKNOWN, got %d", counts[soc.SensorStatusUnknown])
	}
}
