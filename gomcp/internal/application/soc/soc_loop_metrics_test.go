package soc

import (
	"bytes"
	"strings"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	domsoc "github.com/syntrex/gomcp/internal/domain/soc"
)

// TestE2E_SOCLoop_AutoPlaybook_And_RealMTTD_MTTR drives a real event sequence
// through the FULL automatic chain (IMP6):
//
//	ingest auth_bypass → ingest exfiltration → correlation (SOC-CR-003, CRITICAL)
//	→ incident created → matching playbook (pb-quarantine-exfil) AUTO-FIRES
//	→ incident resolved → analytics reports REAL MTTD + MTTR from timestamps.
//
// It proves the playbook fires WITHOUT a manual RunPlaybook call, that MTTD is
// derived from the first-event timestamp (not zero), and that MTTR comes from
// ResolvedAt (not the inflated UpdatedAt or a static value).
func TestE2E_SOCLoop_AutoPlaybook_And_RealMTTD_MTTR(t *testing.T) {
	svc := newTestServiceWithLogger(t)

	const sensor = "sensor-loop-1"

	// First event of the attack, deliberately 90s in the past so the detect
	// latency (incident.CreatedAt − FirstEventAt) is a real, positive span.
	evt1 := domsoc.NewSOCEvent(domsoc.SourceShield, domsoc.SeverityHigh, "auth_bypass", "credential brute force")
	evt1.SensorID = sensor
	evt1.Timestamp = time.Now().Add(-90 * time.Second)
	evt1.ID = "evt-loop-1"
	_, inc1, err := svc.IngestEvent(evt1)
	require.NoError(t, err)
	require.Nil(t, inc1, "single event must not correlate")

	// Second event completes SOC-CR-003 (auth_bypass → exfiltration, CRITICAL).
	// The completing event's category is "exfiltration", which matches the
	// built-in pb-quarantine-exfil playbook (Severity HIGH, Categories=[exfiltration]).
	evt2 := domsoc.NewSOCEvent(domsoc.SourceShield, domsoc.SeverityHigh, "exfiltration", "bulk data egress")
	evt2.SensorID = sensor
	evt2.Timestamp = time.Now().Add(-30 * time.Second)
	evt2.ID = "evt-loop-2"
	_, incident, err := svc.IngestEvent(evt2)
	require.NoError(t, err)
	require.NotNil(t, incident, "auth_bypass + exfiltration must create an incident (SOC-CR-003)")
	assert.Equal(t, domsoc.SeverityCritical, incident.Severity)

	// --- IMP6: the matching playbook AUTO-FIRED on incident creation ---
	assert.NotEmpty(t, incident.PlaybookApplied,
		"a matching playbook must auto-fire on the ingest path (not only via manual RunPlaybook)")

	// The execution log records the auto-fired run.
	pe := svc.PlaybookEngine()
	execs := pe.ExecutionLog(50)
	var quarantineRun *domsoc.PlaybookExecution
	for i := range execs {
		if execs[i].IncidentID == incident.ID && execs[i].PlaybookID == "pb-quarantine-exfil" {
			quarantineRun = &execs[i]
		}
	}
	require.NotNil(t, quarantineRun, "pb-quarantine-exfil should have auto-fired for the exfil incident; log=%+v", execs)
	assert.Equal(t, "success", quarantineRun.Status, "quarantine+escalate actions both succeed (log-only escalate)")
	assert.Greater(t, quarantineRun.ActionsRun, 0)

	// --- IMP6: MTTD is derived from the real first-event timestamp ---
	require.False(t, incident.FirstEventAt.IsZero(), "incident must record the earliest correlated-event time")
	detect, ok := incident.DetectLatency()
	require.True(t, ok, "detect latency must be measurable")
	assert.Greater(t, detect, time.Duration(0), "MTTD anchor must produce a positive detect latency")
	// FirstEventAt must be the EARLIEST event (evt1 @ -90s), not evt2 @ -30s.
	assert.WithinDuration(t, evt1.Timestamp, incident.FirstEventAt, time.Second)

	// --- Resolve the incident; it must flow into MTTR as a real measurement ---
	require.NoError(t, svc.ChangeIncidentStatus(incident.ID, domsoc.StatusResolved, "analyst@test"))

	got, err := svc.GetIncident(incident.ID)
	require.NoError(t, err)
	require.NotNil(t, got.ResolvedAt, "resolved incident must persist resolved_at")
	require.False(t, got.FirstEventAt.IsZero(), "first_event_at must survive the persistence round-trip")

	// Analytics computes MTTD from the live loop's real first-event anchor.
	report, err := svc.Analytics("", 24)
	require.NoError(t, err)
	assert.Greater(t, report.MTTDSeconds, 0.0, "analytics MTTD must be computed from real timestamps, not zero")
	assert.GreaterOrEqual(t, report.MeasuredDetections, 1)

	// --- MTTR magnitude: prove it uses ResolvedAt (not UpdatedAt) with a known
	// 2h span. The live incident above resolved within wall-clock granularity (a
	// ~0s span, correctly NOT counted as a positive resolution), so we drive MTTR
	// with an incident carrying explicit timestamps and a LATER UpdatedAt (e.g. a
	// note edited after resolution): an honest MTTR must report the 2h
	// created→resolved span, NOT the 3h created→updated span. ---
	created := time.Now().Add(-3 * time.Hour)
	resolved := created.Add(2 * time.Hour)
	updated := created.Add(3 * time.Hour) // touched after resolution
	manual := domsoc.Incident{
		ID:         "INC-MTTR-PROOF",
		Status:     domsoc.StatusResolved,
		Severity:   domsoc.SeverityHigh,
		Title:      "MTTR proof",
		CreatedAt:  created,
		UpdatedAt:  updated,
		ResolvedAt: &resolved,
	}
	require.NoError(t, svc.Repo().InsertIncident(manual))
	require.NoError(t, svc.Repo().UpdateIncident(&manual)) // persist resolved_at + updated_at

	report2, err := svc.Analytics("", 24)
	require.NoError(t, err)
	require.GreaterOrEqual(t, report2.ResolvedIncidents, 1, "the 2h proof incident must be counted into MTTR")
	// Mean over {2h proof} (+ possibly the ~0h live one): in (≈1h, 2.01h]. The 3h
	// UpdatedAt span would push it >2h, so the upper bound proves ResolvedAt is used.
	assert.Greater(t, report2.MTTR, 0.0, "MTTR must be computed from resolved_at, not static/zero")
	assert.LessOrEqual(t, report2.MTTR, 2.01,
		"MTTR must use ResolvedAt (≤2h), never the later UpdatedAt (3h)")
}

// TestSOCMetrics_Exposition asserts the SOC-plane self-observability endpoint
// (IMP7) emits the required series after driving the loop, and that NO unbounded
// per-tenant/per-sensor label leaks into the exposition.
func TestSOCMetrics_Exposition(t *testing.T) {
	svc := newTestServiceWithLogger(t)

	// Drive the same auto-firing sequence so every series has a value.
	const sensor = "sensor-metrics-1"
	const tenant = "tenant-secret-xyz"

	evt1 := domsoc.NewSOCEvent(domsoc.SourceShield, domsoc.SeverityHigh, "auth_bypass", "brute force")
	evt1.SensorID = sensor
	evt1.TenantID = tenant
	evt1.Timestamp = time.Now().Add(-60 * time.Second)
	evt1.ID = "evt-m-1"
	_, _, err := svc.IngestEvent(evt1)
	require.NoError(t, err)

	evt2 := domsoc.NewSOCEvent(domsoc.SourceShield, domsoc.SeverityHigh, "exfiltration", "egress")
	evt2.SensorID = sensor
	evt2.TenantID = tenant
	evt2.Timestamp = time.Now().Add(-20 * time.Second)
	evt2.ID = "evt-m-2"
	_, incident, err := svc.IngestEvent(evt2)
	require.NoError(t, err)
	require.NotNil(t, incident)
	require.NoError(t, svc.ChangeIncidentStatus(incident.ID, domsoc.StatusResolved, "analyst@test"))

	var buf bytes.Buffer
	svc.WriteMetrics(&buf)
	out := buf.String()

	// Required SOC series (IMP7).
	for _, want := range []string{
		"soc_events_ingested_total",
		`soc_events_ingested_total{severity="HIGH"}`,
		`soc_events_ingested_total{source="shield"}`,
		"soc_incidents_created_total",
		"soc_playbook_runs_total",
		`soc_playbook_runs_total{outcome="success"}`,
		"soc_correlation_latency_seconds_bucket",
		"soc_correlation_latency_seconds_count",
		"soc_open_incidents",
		"soc_mttd_seconds",
		"soc_mttr_hours",
	} {
		assert.Containsf(t, out, want, "metrics exposition missing %q\n---\n%s", want, out)
	}

	// Cardinality discipline: the tenant id / sensor id MUST NOT appear as labels.
	assert.NotContains(t, out, tenant, "tenant id leaked into /metrics labels (cardinality bomb)")
	assert.NotContains(t, out, sensor, "sensor id leaked into /metrics labels (cardinality bomb)")

	// Events counter must be ≥2 (both ingested).
	assert.Contains(t, out, "soc_events_ingested_total 2")
	// Incident counter must be ≥1.
	assert.Contains(t, out, "soc_incidents_created_total 1")
}

// TestSOCMetrics_BoundedPlaybookSeries proves the per-playbook counter is capped
// so a flood of distinct custom playbook IDs cannot grow the series set without
// bound (cardinality discipline, IMP7).
func TestSOCMetrics_BoundedPlaybookSeries(t *testing.T) {
	m := domsoc.NewSOCMetrics()
	// Record far more distinct playbook ids than the cap (64).
	for i := 0; i < 500; i++ {
		m.RecordPlaybookRun(idForIndex(i), "success")
	}
	var buf bytes.Buffer
	m.Write(&buf, domsoc.Snapshot{})
	out := buf.String()

	// Count distinct soc_playbook_runs_by_id_total{playbook=...} lines.
	lines := strings.Split(out, "\n")
	distinct := 0
	for _, ln := range lines {
		if strings.HasPrefix(ln, "soc_playbook_runs_by_id_total{") {
			distinct++
		}
	}
	assert.LessOrEqual(t, distinct, 65, "per-playbook series must be capped (got %d)", distinct)
	assert.Contains(t, out, `playbook="_other"`, "overflow ids must route to the _other bucket")
}

func idForIndex(i int) string {
	return "pb-flood-" + string(rune('a'+(i%26))) + "-" + itoa(i)
}

func itoa(i int) string {
	if i == 0 {
		return "0"
	}
	var b [12]byte
	pos := len(b)
	for i > 0 {
		pos--
		b[pos] = byte('0' + i%10)
		i /= 10
	}
	return string(b[pos:])
}
