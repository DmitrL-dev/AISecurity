package postgres

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"github.com/pressly/goose/v3"
	"github.com/syntrex/gomcp/internal/domain/soc"
	"io"
	"log/slog"
	"net/url"
	"os"
	"reflect"
	"strings"
	"testing"
	"time"
)

func auditSOCRepo(t *testing.T) *SOCRepo {
	t.Helper()
	dsn := os.Getenv("SPECTORN_SOC_AUDIT_FIXTURE_DSN")
	if dsn == "" {
		t.Skip("explicit isolated PostgreSQL fixture DSN not provided")
	}
	u, err := url.Parse(dsn)
	if err != nil || u.Hostname() != "audit-socket.invalid" || !strings.HasPrefix(u.Query().Get("host"), "/workspace/tmp/pgf-") || u.Query().Get("sslmode") != "disable" {
		t.Fatal("refusing non-fixture database")
	}
	pool, err := sql.Open("pgx", dsn)
	if err != nil {
		t.Fatal("open fixture")
	}
	t.Cleanup(func() { pool.Close() })
	pool.SetMaxOpenConns(2)
	// Each test owns a newly named schema in the new synthetic-only DB. Nothing
	// is dropped from an existing database and no external environment is used.
	schema := "audit_" + strings.ToLower(strings.ReplaceAll(t.Name(), "/", "_"))
	if _, err := pool.Exec("CREATE SCHEMA " + schema); err != nil {
		t.Fatal("create fixture schema")
	}
	// search_path must apply to every pooled connection, including racing upserts.
	pool.Close()
	q := u.Query()
	q.Set("search_path", schema)
	u.RawQuery = q.Encode()
	pool, err = sql.Open("pgx", u.String())
	if err != nil {
		t.Fatal("open fixture schema")
	}
	pool.SetMaxOpenConns(2)
	t.Cleanup(func() { pool.Close() })
	db := &DB{pool: pool, logger: slog.New(slog.NewTextHandler(io.Discard, nil))}
	goose.SetBaseFS(migrations)
	if err := goose.SetDialect("postgres"); err != nil {
		t.Fatal(err)
	}
	if err := goose.UpTo(pool, "migrations", 6); err != nil {
		t.Fatal("legacy migrations failed")
	}
	if _, err := pool.Exec(`INSERT INTO soc_incidents (id,severity,title,created_at,updated_at,event_ids) VALUES ('legacy','HIGH','legacy',now(),now(),'["legacy-event"]')`); err != nil {
		t.Fatal("legacy seed failed")
	}
	if err := db.migrate(); err != nil {
		t.Fatal("additive migration failed")
	}
	repo := NewSOCRepo(db)
	legacy, err := repo.GetIncident("legacy")
	if err != nil || legacy.Title != "legacy" || !reflect.DeepEqual(legacy.Events, []string{"legacy-event"}) || legacy.AssignedTo != "" || len(legacy.Notes) != 0 || len(legacy.Timeline) != 0 {
		t.Fatal("legacy evidence changed")
	}
	if err := db.migrate(); err != nil {
		t.Fatal("migration not repeatable")
	}
	return repo
}

func TestSOCPersistenceAuditRoundtrip(t *testing.T) {
	repo := auditSOCRepo(t)
	now := time.Date(2026, 10, 25, 12, 0, 0, 123456000, time.UTC)
	event := soc.NewSOCEvent(soc.SourceSentinelCore, soc.SeverityHigh, "fixture-category", "synthetic description")
	event.ID = "audit-event"
	event.TenantID = "audit-owner"
	event.Timestamp = now
	event.ContentHash = "fixture-content-hash"
	event.Metadata = map[string]string{"src_ip": "203.0.113.10", "indicator": "fixture-indicator"}
	if err := repo.InsertEvent(event); err != nil {
		t.Fatal(err)
	}
	got, err := repo.GetEvent(event.ID)
	if err != nil {
		t.Fatal(err)
	}
	if !auditEqualJSON(got, event) {
		t.Fatal("event metadata/owner lost on read")
	}
	for _, tenant := range []string{"audit-owner", ""} {
		all, err := repo.ListEvents(tenant, 2)
		if err != nil || len(all) != 1 || !auditEqualJSON(all[0], event) {
			t.Fatalf("event list evidence lost: %v", err)
		}
		byCategory, err := repo.ListEventsByCategory(tenant, event.Category, 2)
		if err != nil || len(byCategory) != 1 || !auditEqualJSON(byCategory[0], event) {
			t.Fatalf("category list evidence lost: %v", err)
		}
	}
	inc := soc.NewIncident("synthetic incident", soc.SeverityHigh, "fixture-rule")
	inc.ID = "audit-incident"
	inc.TenantID = "audit-owner"
	inc.Events = []string{event.ID}
	inc.EventCount = 1
	inc.MITREMapping = []string{"T1059"}
	inc.PlaybookApplied = "fixture-playbook"
	inc.AssignedTo = "fixture-analyst"
	inc.CreatedAt = now
	inc.UpdatedAt = now
	inc.FirstEventAt = now.Add(-time.Minute)
	inc.Notes = []soc.IncidentNote{{ID: "fixture-note", Author: "fixture-analyst", Content: "synthetic", CreatedAt: now}}
	inc.Timeline = []soc.TimelineEntry{{Timestamp: now, Type: "playbook", Actor: "system", Description: "synthetic", Metadata: map[string]any{"action": "fixture"}}}
	assertIncident := func(want soc.Incident) {
		t.Helper()
		actual, err := repo.GetIncident(want.ID)
		if err != nil {
			t.Fatal(err)
		}
		check := func(value soc.Incident) {
			if !auditEqualJSON(value, want) {
				t.Fatalf("incident evidence did not roundtrip")
			}
		}
		check(*actual)
		for _, tenant := range []string{"audit-owner", ""} {
			for _, status := range []string{string(want.Status), ""} {
				list, err := repo.ListIncidents(tenant, status, 10)
				if err != nil {
					t.Fatal(err)
				}
				found := false
				for _, v := range list {
					if v.ID == want.ID {
						found = true
						check(v)
					}
				}
				if !found {
					t.Fatal("incident missing from filtered list")
				}
			}
		}
	}
	if err := repo.InsertIncident(inc); err != nil {
		t.Fatal(err)
	}
	assertIncident(inc)
	inc.Events = append(inc.Events, "audit-event-2")
	inc.EventCount = 2
	inc.MITREMapping = append(inc.MITREMapping, "T1005")
	inc.Title = "updated-title"
	inc.Description = "updated-description"
	inc.DecisionChainAnchor = "updated-anchor"
	inc.ChainLength = 2
	inc.CorrelationRule = "updated-rule"
	inc.FirstEventAt = now.Add(-2 * time.Minute)
	resolved := now.Add(time.Minute)
	inc.ResolvedAt = &resolved
	inc.Status = soc.StatusResolved
	inc.KillChainPhase = "Exfiltration"
	inc.PlaybookApplied = "fixture-playbook-2"
	inc.AssignedTo = "fixture-analyst-2"
	inc.UpdatedAt = now.Add(time.Minute)
	inc.Notes = append(inc.Notes, soc.IncidentNote{ID: "note-2", Content: "synthetic", CreatedAt: now})
	inc.Timeline = append(inc.Timeline, soc.TimelineEntry{Timestamp: now, Type: "assign", Actor: "system"})
	if err := repo.UpdateIncident(&inc); err != nil {
		t.Fatal(err)
	}
	assertIncident(inc)
	otherOwner := inc
	otherOwner.TenantID = "foreign-owner"
	otherOwner.Title = "must-not-persist"
	if err := repo.UpdateIncident(&otherOwner); err == nil {
		t.Fatal("foreign incident update accepted")
	}
	assertIncident(inc)
	// Unencodable metadata must fail before changing stored evidence.
	invalid := inc
	invalid.PlaybookApplied = "must-not-persist"
	invalid.Timeline = []soc.TimelineEntry{{Metadata: map[string]any{"invalid": make(chan int)}}}
	if err := repo.UpdateIncident(&invalid); err == nil {
		t.Fatal("unsupported metadata accepted")
	}
	assertIncident(inc)
	foreign, err := repo.ListIncidents("foreign-owner", "", 10)
	if err != nil || len(foreign) != 0 {
		t.Fatal("foreign incidents returned")
	}
}

func TestSOCSensorAuditOwnership(t *testing.T) {
	repo := auditSOCRepo(t)
	s := soc.NewSensor("audit-sensor", soc.SensorTypeExternal)
	s.TenantID = "owner-a"
	s.EventCount = 1
	if err := repo.UpsertSensor(s); err != nil {
		t.Fatal(err)
	}
	s.EventCount = 2
	s.Status = soc.SensorStatusHealthy
	if err := repo.UpsertSensor(s); err != nil {
		t.Fatal(err)
	}
	foreign := s
	foreign.TenantID = "owner-b"
	foreign.EventCount = 999
	foreign.Status = soc.SensorStatusOffline
	if err := repo.UpsertSensor(foreign); err == nil {
		t.Fatal("foreign sensor upsert accepted")
	}
	got, err := repo.GetSensor(s.SensorID)
	if err != nil || got.TenantID != s.TenantID || got.EventCount != 2 || got.Status != s.Status {
		t.Fatal("foreign conflict changed existing sensor")
	}
	list, err := repo.ListSensors(s.TenantID)
	if err != nil || len(list) != 1 || list[0].TenantID != s.TenantID {
		t.Fatal("sensor owner lost in list")
	}
	foreignList, err := repo.ListSensors(foreign.TenantID)
	if err != nil || len(foreignList) != 0 {
		t.Fatal("foreign sensor listed")
	}
	// Simultaneous first claims share a barrier; the atomic conflict predicate
	// permits exactly one owner and leaves only that owner's data.
	start := make(chan struct{})
	results := make(chan struct {
		tenant string
		err    error
	}, 2)
	for _, tenant := range []string{"claim-a", "claim-b"} {
		go func(tenant string) {
			candidate := soc.NewSensor("audit-racing-sensor", soc.SensorTypeExternal)
			candidate.TenantID = tenant
			<-start
			results <- struct {
				tenant string
				err    error
			}{tenant, repo.UpsertSensor(candidate)}
		}(tenant)
	}
	close(start)
	winner := ""
	success := 0
	for range 2 {
		result := <-results
		if result.err == nil {
			success++
			winner = result.tenant
		}
	}
	if success != 1 {
		t.Fatalf("concurrent owners accepted: %d", success)
	}
	racing, err := repo.GetSensor("audit-racing-sensor")
	if err != nil || racing.TenantID != winner {
		t.Fatal("concurrent owner mismatch")
	}
}

func auditEqualJSON(actual, expected any) bool {
	a, err := json.Marshal(actual)
	if err != nil {
		return false
	}
	b, err := json.Marshal(expected)
	return err == nil && bytes.Equal(a, b)
}
