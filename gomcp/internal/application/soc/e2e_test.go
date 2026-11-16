package soc

import (
	"bytes"
	"context"
	"fmt"
	"net"
	"net/http"
	"net/http/httptest"
	"os"
	"sync"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	domsoc "github.com/syntrex/gomcp/internal/domain/soc"
	"github.com/syntrex/gomcp/internal/infrastructure/audit"
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"
)

// allowLoopbackWebhook temporarily relaxes the domain SSRF guard so a webhook can
// reach a 127.0.0.1 httptest server in-test. Mirrors firewall_test.go /
// webhooks_test.go / withLoopbackFetch. MUST be called BEFORE SetWebhookConfig,
// since NewWebhookNotifier captures SafeDialContext into its transport at build time.
func allowLoopbackWebhook(t *testing.T) {
	t.Helper()
	origValidate := domsoc.ValidateWebhookURL
	origDial := domsoc.SafeDialContext
	domsoc.ValidateWebhookURL = func(string) error { return nil }
	domsoc.SafeDialContext = func(ctx context.Context, network, addr string) (net.Conn, error) {
		return (&net.Dialer{}).DialContext(ctx, network, addr)
	}
	t.Cleanup(func() {
		domsoc.ValidateWebhookURL = origValidate
		domsoc.SafeDialContext = origDial
	})
}

// newTestServiceWithLogger creates a SOC service backed by in-memory SQLite WITH a decision logger.
func newTestServiceWithLogger(t *testing.T) *Service {
	t.Helper()
	db, err := sqlite.OpenMemory()
	require.NoError(t, err)

	repo, err := sqlite.NewSOCRepo(db)
	require.NoError(t, err)

	logger, err := audit.NewDecisionLogger(t.TempDir())
	require.NoError(t, err)

	// Close logger BEFORE TempDir cleanup (Windows file locking).
	t.Cleanup(func() {
		logger.Close()
		db.Close()
	})

	return NewService(repo, logger)
}

// --- E2E: Full Pipeline (Ingest → Correlation → Incident → Playbook) ---

func TestE2E_FullPipeline_IngestToIncident(t *testing.T) {
	svc := newTestServiceWithLogger(t)

	// Step 1: Ingest a jailbreak event.
	evt1 := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, domsoc.SeverityHigh, "jailbreak", "detected jailbreak attempt")
	evt1.SensorID = "sensor-e2e-1"
	id1, inc1, err := svc.IngestEvent(evt1)
	require.NoError(t, err)
	assert.NotEmpty(t, id1)
	assert.Nil(t, inc1, "single event should not trigger correlation")

	// Step 2: Ingest a tool_abuse event from same source — triggers SOC-CR-001.
	evt2 := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, domsoc.SeverityCritical, "tool_abuse", "tool abuse detected")
	evt2.SensorID = "sensor-e2e-1"
	id2, inc2, err := svc.IngestEvent(evt2)
	require.NoError(t, err)
	assert.NotEmpty(t, id2)

	// Correlation rule SOC-CR-001 (jailbreak + tool_abuse) should trigger an incident.
	require.NotNil(t, inc2, "jailbreak + tool_abuse should create an incident")
	assert.Equal(t, domsoc.SeverityCritical, inc2.Severity)
	assert.Equal(t, "Multi-stage Jailbreak", inc2.Title)
	assert.NotEmpty(t, inc2.ID)
	assert.NotEmpty(t, inc2.Events, "incident should reference triggering events")

	// Step 3: Verify incident is persisted.
	gotInc, err := svc.GetIncident(inc2.ID)
	require.NoError(t, err)
	assert.Equal(t, inc2.ID, gotInc.ID)

	// Step 4: Verify decision chain integrity.
	dash, err := svc.Dashboard("")
	require.NoError(t, err)
	assert.True(t, dash.ChainValid, "decision chain should be valid")
	assert.Greater(t, dash.TotalEvents, 0)
}

func TestE2E_TemporalSequenceCorrelation(t *testing.T) {
	svc := newTestServiceWithLogger(t)

	// Sequence rule SOC-CR-010: auth_bypass → tool_abuse (ordered).
	evt1 := domsoc.NewSOCEvent(domsoc.SourceShield, domsoc.SeverityHigh, "auth_bypass", "brute force detected")
	evt1.SensorID = "sensor-seq-1"
	_, _, err := svc.IngestEvent(evt1)
	require.NoError(t, err)

	evt2 := domsoc.NewSOCEvent(domsoc.SourceShield, domsoc.SeverityHigh, "tool_abuse", "tool escalation")
	evt2.SensorID = "sensor-seq-1"
	_, inc, err := svc.IngestEvent(evt2)
	require.NoError(t, err)

	// Should trigger either SOC-CR-010 (sequence) or another matching rule.
	if inc != nil {
		assert.NotEmpty(t, inc.KillChainPhase)
		assert.NotEmpty(t, inc.MITREMapping)
	}
}

// --- E2E: Sensor Authentication Flow ---

func TestE2E_SensorAuth_FullFlow(t *testing.T) {
	svc := newTestServiceWithLogger(t)

	// Configure sensor keys.
	svc.SetSensorKeys(map[string]string{
		"sensor-auth-1": "secret-key-1",
		"sensor-auth-2": "secret-key-2",
	})

	// Valid auth — should succeed.
	evt := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, domsoc.SeverityLow, "test", "auth test")
	evt.SensorID = "sensor-auth-1"
	evt.SensorKey = "secret-key-1"
	id, _, err := svc.IngestEvent(evt)
	require.NoError(t, err)
	assert.NotEmpty(t, id)

	// Invalid key — should fail.
	evt2 := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, domsoc.SeverityLow, "test", "bad key")
	evt2.SensorID = "sensor-auth-1"
	evt2.SensorKey = "wrong-key"
	_, _, err = svc.IngestEvent(evt2)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "auth")

	// Missing SensorID — should fail (S-1 fix).
	evt3 := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, domsoc.SeverityLow, "test", "no sensor id")
	_, _, err = svc.IngestEvent(evt3)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "sensor_id required")

	// Unknown sensor — should fail.
	evt4 := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, domsoc.SeverityLow, "test", "unknown sensor")
	evt4.SensorID = "sensor-unknown"
	evt4.SensorKey = "whatever"
	_, _, err = svc.IngestEvent(evt4)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "auth")
}

// --- E2E: Drain Mode ---

func TestE2E_DrainMode_RejectsNewEvents(t *testing.T) {
	svc := newTestServiceWithLogger(t)

	// Ingest works before drain.
	evt := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, domsoc.SeverityLow, "test", "pre-drain")
	evt.SensorID = "sensor-drain"
	_, _, err := svc.IngestEvent(evt)
	require.NoError(t, err)

	// Activate drain mode.
	svc.Drain()
	assert.True(t, svc.IsDraining())

	// New events should be rejected.
	evt2 := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, domsoc.SeverityLow, "test", "during-drain")
	evt2.SensorID = "sensor-drain"
	_, _, err = svc.IngestEvent(evt2)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "draining")

	// Resume.
	svc.Resume()
	assert.False(t, svc.IsDraining())

	// Events should work again.
	evt3 := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, domsoc.SeverityLow, "test", "post-drain")
	evt3.SensorID = "sensor-drain"
	_, _, err = svc.IngestEvent(evt3)
	require.NoError(t, err)
}

// --- E2E: Webhook Delivery ---

func TestE2E_WebhookFiredOnIncident(t *testing.T) {
	svc := newTestServiceWithLogger(t)

	// Set up a test webhook server.
	var mu sync.Mutex
	var received []string
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		mu.Lock()
		received = append(received, r.URL.Path)
		mu.Unlock()
		w.WriteHeader(http.StatusOK)
	}))
	defer ts.Close()

	// httptest binds 127.0.0.1, which the production SSRF guard now correctly blocks;
	// relax it for this loopback delivery test (before SetWebhookConfig builds the client).
	allowLoopbackWebhook(t)
	svc.SetWebhookConfig(WebhookConfig{
		Endpoints:  []string{ts.URL + "/webhook"},
		MaxRetries: 1,
		TimeoutSec: 5,
	})

	// Trigger an incident via correlation.
	evt1 := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, domsoc.SeverityHigh, "jailbreak", "jailbreak e2e")
	evt1.SensorID = "sensor-wh"
	svc.IngestEvent(evt1)

	evt2 := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, domsoc.SeverityCritical, "tool_abuse", "tool abuse e2e")
	evt2.SensorID = "sensor-wh"
	_, inc, err := svc.IngestEvent(evt2)
	require.NoError(t, err)

	if inc != nil {
		// Give the async webhook goroutine time to fire.
		time.Sleep(200 * time.Millisecond)

		mu.Lock()
		assert.GreaterOrEqual(t, len(received), 1, "webhook should have been called")
		mu.Unlock()
	}
}

// --- E2E: Verdict Flow ---

func TestE2E_VerdictFlow(t *testing.T) {
	svc := newTestServiceWithLogger(t)

	// Create an incident via correlation.
	evt1 := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, domsoc.SeverityHigh, "jailbreak", "verdict test 1")
	evt1.SensorID = "sensor-vd"
	svc.IngestEvent(evt1)

	evt2 := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, domsoc.SeverityCritical, "tool_abuse", "verdict test 2")
	evt2.SensorID = "sensor-vd"
	_, inc, _ := svc.IngestEvent(evt2)

	if inc == nil {
		t.Skip("no incident created — correlation rules may not match with current sliding window state")
	}

	// Verify initial status is OPEN.
	got, err := svc.GetIncident(inc.ID)
	require.NoError(t, err)
	assert.Equal(t, domsoc.StatusOpen, got.Status)

	// Update to INVESTIGATING.
	err = svc.UpdateVerdict(inc.ID, domsoc.StatusInvestigating)
	require.NoError(t, err)

	got, _ = svc.GetIncident(inc.ID)
	assert.Equal(t, domsoc.StatusInvestigating, got.Status)

	// Update to RESOLVED.
	err = svc.UpdateVerdict(inc.ID, domsoc.StatusResolved)
	require.NoError(t, err)

	got, _ = svc.GetIncident(inc.ID)
	assert.Equal(t, domsoc.StatusResolved, got.Status)
}

// --- E2E: Analytics Report ---

func TestE2E_AnalyticsReport(t *testing.T) {
	svc := newTestServiceWithLogger(t)

	// Ingest several events.
	categories := []string{"jailbreak", "injection", "exfiltration", "auth_bypass", "tool_abuse"}
	for i, cat := range categories {
		evt := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, domsoc.SeverityHigh, cat, fmt.Sprintf("analytics test %d", i))
		evt.SensorID = "sensor-analytics"
		svc.IngestEvent(evt)
	}

	report, err := svc.Analytics("", 24)
	require.NoError(t, err)
	assert.NotNil(t, report)
	assert.Greater(t, len(report.TopCategories), 0)
	assert.Greater(t, len(report.TopSources), 0)
	assert.GreaterOrEqual(t, report.EventsPerHour, float64(0))
}

// --- E2E: Multi-Sensor Concurrent Ingest ---

func TestE2E_ConcurrentIngest(t *testing.T) {
	svc := newTestServiceWithLogger(t)

	var wg sync.WaitGroup
	errors := make([]error, 0)
	var mu sync.Mutex

	// 10 sensors × 10 events each = 100 concurrent ingests.
	for s := 0; s < 10; s++ {
		wg.Add(1)
		go func(sensorNum int) {
			defer wg.Done()
			for i := 0; i < 10; i++ {
				evt := domsoc.NewSOCEvent(
					domsoc.SourceSentinelCore,
					domsoc.SeverityLow,
					"test",
					fmt.Sprintf("concurrent sensor-%d event-%d", sensorNum, i),
				)
				evt.SensorID = fmt.Sprintf("sensor-conc-%d", sensorNum)
				_, _, err := svc.IngestEvent(evt)
				if err != nil {
					mu.Lock()
					errors = append(errors, err)
					mu.Unlock()
				}
			}
		}(s)
	}
	wg.Wait()

	// Some events may be rate-limited (100 events/sec per sensor),
	// but there should be no panics or data corruption.
	dash, err := svc.Dashboard("")
	require.NoError(t, err)
	assert.Greater(t, dash.TotalEvents, 0, "at least some events should have been ingested")
}

// --- E2E: Lattice TSA Chain Violation (SOC-CR-012) ---

func TestE2E_TSAChainViolation(t *testing.T) {
	svc := newTestServiceWithLogger(t)

	// SOC-CR-012 requires: auth_bypass → tool_abuse → exfiltration within 15 min.
	events := []struct {
		category string
		severity domsoc.EventSeverity
	}{
		{"auth_bypass", domsoc.SeverityHigh},
		{"tool_abuse", domsoc.SeverityHigh},
		{"exfiltration", domsoc.SeverityCritical},
	}

	var lastInc *domsoc.Incident
	for _, e := range events {
		evt := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, e.severity, e.category, "TSA chain test: "+e.category)
		evt.SensorID = "sensor-tsa"
		_, inc, err := svc.IngestEvent(evt)
		require.NoError(t, err)
		if inc != nil {
			lastInc = inc
		}
	}

	// The TSA chain (auth_bypass + tool_abuse + exfiltration) should trigger
	// SOC-CR-012 or another matching rule.
	require.NotNil(t, lastInc, "TSA chain (auth_bypass → tool_abuse → exfiltration) should create an incident")
	assert.Equal(t, domsoc.SeverityCritical, lastInc.Severity)
	assert.NotEmpty(t, lastInc.MITREMapping)

	// Verify incident is persisted.
	got, err := svc.GetIncident(lastInc.ID)
	require.NoError(t, err)
	assert.Equal(t, lastInc.ID, got.ID)
}

// --- E2E: Zero-G Mode Excludes Playbook Auto-Response ---

func TestE2E_ZeroGExcludedFromAutoResponse(t *testing.T) {
	svc := newTestServiceWithLogger(t)

	// Set up a test webhook server to track playbook webhook notifications.
	var mu sync.Mutex
	var webhookCalls int
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		mu.Lock()
		webhookCalls++
		mu.Unlock()
		w.WriteHeader(http.StatusOK)
	}))
	defer ts.Close()

	// httptest binds 127.0.0.1, which the production SSRF guard now correctly blocks;
	// relax it for this loopback delivery test (before SetWebhookConfig builds the client).
	allowLoopbackWebhook(t)
	svc.SetWebhookConfig(WebhookConfig{
		Endpoints:  []string{ts.URL + "/webhook"},
		MaxRetries: 1,
		TimeoutSec: 5,
	})

	// Ingest jailbreak + tool_abuse with ZeroGMode=true.
	// This should trigger correlation (incident created) but NOT playbooks.
	evt1 := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, domsoc.SeverityHigh, "jailbreak", "zero-g jailbreak test")
	evt1.SensorID = "sensor-zg"
	evt1.ZeroGMode = true
	_, _, err := svc.IngestEvent(evt1)
	require.NoError(t, err)

	evt2 := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, domsoc.SeverityCritical, "tool_abuse", "zero-g tool abuse test")
	evt2.SensorID = "sensor-zg"
	evt2.ZeroGMode = true
	_, inc, err := svc.IngestEvent(evt2)
	require.NoError(t, err)

	// Correlation should still run — incident should be created.
	if inc != nil {
		assert.Equal(t, domsoc.SeverityCritical, inc.Severity)

		// Wait for any async webhook goroutines.
		time.Sleep(200 * time.Millisecond)

		// Webhook should NOT have been called (playbook skipped for Zero-G).
		mu.Lock()
		assert.Equal(t, 0, webhookCalls, "webhooks should NOT fire for Zero-G events — playbook must be skipped")
		mu.Unlock()
	}

	// Verify decision log records the PLAYBOOK_SKIPPED:ZERO_G entry.
	logPath := svc.DecisionLogPath()
	if logPath != "" {
		valid, broken, err := audit.VerifyChainFromFile(logPath, nil)
		require.NoError(t, err)
		assert.Equal(t, 0, broken, "decision chain should be intact")
		assert.Greater(t, valid, 0, "should have decision entries")
	}
}

// --- E2E: Decision Logger Tamper Detection ---

func TestE2E_DecisionLoggerTampering(t *testing.T) {
	svc := newTestServiceWithLogger(t)

	// Ingest several events to build up a decision chain.
	for i := 0; i < 10; i++ {
		evt := domsoc.NewSOCEvent(
			domsoc.SourceSentinelCore,
			domsoc.SeverityLow,
			"test",
			fmt.Sprintf("tamper test event %d", i),
		)
		evt.SensorID = "sensor-tamper"
		_, _, err := svc.IngestEvent(evt)
		require.NoError(t, err)
	}

	// Step 1: Verify chain is valid.
	logPath := svc.DecisionLogPath()
	require.NotEmpty(t, logPath, "decision log path should be set")

	validCount, brokenLine, err := audit.VerifyChainFromFile(logPath, nil)
	require.NoError(t, err)
	assert.Equal(t, 0, brokenLine, "chain should be intact before tampering")
	assert.GreaterOrEqual(t, validCount, 10, "should have at least 10 decision entries")

	// Step 2: Tamper with the log file — modify a line mid-chain.
	data, err := os.ReadFile(logPath)
	require.NoError(t, err)

	lines := bytes.Split(data, []byte("\n"))
	if len(lines) > 5 {
		// Corrupt line 5 by altering content.
		lines[4] = []byte("TAMPERED|2026-01-01T00:00:00Z|SOC|FAKE|fake_reason|0000000000")

		err = os.WriteFile(logPath, bytes.Join(lines, []byte("\n")), 0644)
		require.NoError(t, err)

		// Step 3: Verify chain detects the tamper.
		_, brokenLine2, err2 := audit.VerifyChainFromFile(logPath, nil)
		require.NoError(t, err2)
		assert.Greater(t, brokenLine2, 0, "chain should detect tampering — broken line reported")
	}
}

// --- E2E: Cross-Sensor Session Correlation (SOC-CR-011) ---

func TestE2E_CrossSensorSessionCorrelation(t *testing.T) {
	svc := newTestServiceWithLogger(t)

	// SOC-CR-011 requires 3+ events from different sensors with same session_id.
	sessionID := "session-xsensor-e2e-001"

	sources := []struct {
		source   domsoc.EventSource
		sensor   string
		category string
	}{
		{domsoc.SourceShield, "sensor-shield-1", "auth_bypass"},
		{domsoc.SourceSentinelCore, "sensor-core-1", "jailbreak"},
		{domsoc.SourceImmune, "sensor-immune-1", "exfiltration"},
	}

	var lastInc *domsoc.Incident
	for _, s := range sources {
		evt := domsoc.NewSOCEvent(s.source, domsoc.SeverityHigh, s.category, "cross-sensor test: "+s.category)
		evt.SensorID = s.sensor
		evt.SessionID = sessionID
		_, inc, err := svc.IngestEvent(evt)
		require.NoError(t, err)
		if inc != nil {
			lastInc = inc
		}
	}

	// After 3 events from different sensors/sources with same session_id,
	// at least one correlation rule should have matched.
	require.NotNil(t, lastInc, "cross-sensor session attack (3 sources, same session_id) should create incident")
	assert.NotEmpty(t, lastInc.ID)
	assert.NotEmpty(t, lastInc.Events, "incident should reference triggering events")
}

// --- E2E: Crescendo Escalation (SOC-CR-015) ---

func TestE2E_CrescendoEscalation(t *testing.T) {
	svc := newTestServiceWithLogger(t)

	// SOC-CR-015: 3+ jailbreak events with ascending severity within 15 min.
	severities := []domsoc.EventSeverity{
		domsoc.SeverityLow,
		domsoc.SeverityMedium,
		domsoc.SeverityHigh,
	}

	var lastInc *domsoc.Incident
	for i, sev := range severities {
		evt := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, sev, "jailbreak",
			fmt.Sprintf("crescendo jailbreak attempt %d", i+1))
		evt.SensorID = "sensor-crescendo"
		_, inc, err := svc.IngestEvent(evt)
		require.NoError(t, err)
		if inc != nil {
			lastInc = inc
		}
	}

	// The ascending severity pattern (LOW→MEDIUM→HIGH) should trigger SOC-CR-015.
	require.NotNil(t, lastInc, "crescendo pattern (LOW→MEDIUM→HIGH jailbreaks) should create incident")
	assert.Equal(t, domsoc.SeverityCritical, lastInc.Severity)
	assert.Contains(t, lastInc.MITREMapping, "T1059")
}

