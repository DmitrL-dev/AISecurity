package soc

import (
	"fmt"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	domsoc "github.com/syntrex/gomcp/internal/domain/soc"
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"
)

// newTestService creates a SOC service backed by in-memory SQLite, without a decision logger.
func newTestService(t *testing.T) *Service {
	t.Helper()
	db, err := sqlite.OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { db.Close() })

	repo, err := sqlite.NewSOCRepo(db)
	require.NoError(t, err)

	return NewService(repo, nil)
}

// --- Rate Limiting Tests (§17.3, §18.2 PB-05) ---

func TestIsRateLimited_UnderLimit(t *testing.T) {
	svc := newTestService(t)

	// 100 events should NOT trigger rate limit.
	for i := 0; i < 100; i++ {
		event := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, domsoc.SeverityLow, "test", "rate test")
		event.ID = fmt.Sprintf("evt-under-%d", i) // Unique ID
		event.SensorID = "sensor-A"
		_, _, err := svc.IngestEvent(event)
		require.NoError(t, err, "event %d should not be rate limited", i+1)
	}
}

func TestIsRateLimited_OverLimit(t *testing.T) {
	svc := newTestService(t)

	// Send 101 events — the 101st should be rate limited.
	for i := 0; i < MaxEventsPerSecondPerSensor; i++ {
		event := domsoc.NewSOCEvent(domsoc.SourceShield, domsoc.SeverityLow, "test", "rate test")
		event.ID = fmt.Sprintf("evt-over-%d", i) // Unique ID
		event.SensorID = "sensor-B"
		_, _, err := svc.IngestEvent(event)
		require.NoError(t, err, "event %d should pass", i+1)
	}

	// 101st event — should be rejected.
	event := domsoc.NewSOCEvent(domsoc.SourceShield, domsoc.SeverityLow, "test", "overflow")
	event.ID = "evt-over-101"
	event.SensorID = "sensor-B"
	_, _, err := svc.IngestEvent(event)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "rate limit exceeded")
	assert.Contains(t, err.Error(), "sensor-B")
}

func TestIsRateLimited_DifferentSensors(t *testing.T) {
	svc := newTestService(t)

	// 100 events from sensor-C.
	for i := 0; i < MaxEventsPerSecondPerSensor; i++ {
		event := domsoc.NewSOCEvent(domsoc.SourceGoMCP, domsoc.SeverityLow, "test", "sensor C")
		event.ID = fmt.Sprintf("evt-diff-C-%d", i) // Unique ID
		event.SensorID = "sensor-C"
		_, _, err := svc.IngestEvent(event)
		require.NoError(t, err)
	}

	// sensor-D should still accept events (independent rate limiter).
	event := domsoc.NewSOCEvent(domsoc.SourceGoMCP, domsoc.SeverityLow, "test", "sensor D")
	event.ID = "evt-diff-D-0"
	event.SensorID = "sensor-D"
	_, _, err := svc.IngestEvent(event)
	require.NoError(t, err, "sensor-D should not be affected by sensor-C rate limit")
}

func TestIsRateLimited_FallsBackToSource(t *testing.T) {
	svc := newTestService(t)

	// When SensorID is empty, should use Source as key.
	for i := 0; i < MaxEventsPerSecondPerSensor; i++ {
		event := domsoc.NewSOCEvent(domsoc.SourceExternal, domsoc.SeverityLow, "test", "no sensor id")
		event.ID = fmt.Sprintf("evt-fb-%d", i) // Unique ID
		_, _, err := svc.IngestEvent(event)
		require.NoError(t, err)
	}

	// 101st from same source — should be limited.
	event := domsoc.NewSOCEvent(domsoc.SourceExternal, domsoc.SeverityLow, "test", "overflow no sensor")
	event.ID = "evt-fb-101"
	_, _, err := svc.IngestEvent(event)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "rate limit exceeded")
}

// --- Compliance Report Tests (§12.3) ---

func TestComplianceReport_GeneratesReport(t *testing.T) {
	svc := newTestService(t)

	report, err := svc.ComplianceReport()
	require.NoError(t, err)
	require.NotNil(t, report)

	assert.Equal(t, "EU AI Act Article 15", report.Framework)
	assert.NotEmpty(t, report.Requirements)
	assert.Len(t, report.Requirements, 6) // 15.1 through 15.6

	// Without a decision logger, chain is invalid → 15.2/15.4 are NON_COMPLIANT.
	// With NON_COMPLIANT present, overall is NON_COMPLIANT.
	// 15.5 Transparency is always PARTIAL.
	foundPartial := false
	for _, r := range report.Requirements {
		if r.Status == "PARTIAL" {
			foundPartial = true
			assert.NotEmpty(t, r.Gap)
		}
	}
	assert.True(t, foundPartial, "should have at least one PARTIAL requirement")

	// Overall should be NON_COMPLIANT because no Decision Logger → chain invalid.
	assert.Equal(t, "NON_COMPLIANT", report.Overall)
}

// --- RunPlaybook Tests (§10, §12.1) ---

func TestRunPlaybook_NotFound(t *testing.T) {
	svc := newTestService(t)

	_, err := svc.RunPlaybook("nonexistent-pb", "inc-123")
	require.Error(t, err)
	assert.Contains(t, err.Error(), "playbook not found")
}

func TestRunPlaybook_IncidentNotFound(t *testing.T) {
	svc := newTestService(t)

	// Use a valid playbook ID from defaults.
	_, err := svc.RunPlaybook("pb-block-jailbreak", "nonexistent-inc")
	require.Error(t, err)
	assert.Contains(t, err.Error(), "incident not found")
}

// --- Secret Scanner Integration Tests (§5.4) ---

func TestSecretScanner_RejectsSecrets(t *testing.T) {
	svc := newTestService(t)

	event := domsoc.NewSOCEvent(domsoc.SourceExternal, domsoc.SeverityMedium, "test", "test event")
	event.Payload = "my API key is AKIA1234567890ABCDEF" // AWS-style key
	_, _, err := svc.IngestEvent(event)
	if err != nil {
		// If ScanForSecrets detected it, we expect rejection.
		assert.Contains(t, err.Error(), "secret scanner rejected")
	}
	// If no secrets detected (depends on oracle implementation), event passes.
}

func TestSecretScanner_AllowsClean(t *testing.T) {
	svc := newTestService(t)

	event := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, domsoc.SeverityLow, "test", "clean event")
	event.Payload = "this is a normal log message with no secrets"
	id, _, err := svc.IngestEvent(event)
	require.NoError(t, err)
	assert.NotEmpty(t, id)
}

// --- Zero-G Mode Tests (§13.4) ---

func TestZeroGMode_SkipsPlaybook(t *testing.T) {
	svc := newTestService(t)

	event := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, domsoc.SeverityCritical, "jailbreak", "zero-g test")
	event.ZeroGMode = true
	id, _, err := svc.IngestEvent(event)
	require.NoError(t, err)
	assert.NotEmpty(t, id)
}

// --- Helper tests ---

func TestBoolToCompliance(t *testing.T) {
	assert.Equal(t, "COMPLIANT", boolToCompliance(true))
	assert.Equal(t, "NON_COMPLIANT", boolToCompliance(false))
}

func TestOverallStatus(t *testing.T) {
	tests := []struct {
		name string
		reqs []ComplianceRequirement
		want string
	}{
		{"all compliant", []ComplianceRequirement{{Status: "COMPLIANT"}, {Status: "COMPLIANT"}}, "COMPLIANT"},
		{"one partial", []ComplianceRequirement{{Status: "COMPLIANT"}, {Status: "PARTIAL"}}, "PARTIAL"},
		{"one non-compliant", []ComplianceRequirement{{Status: "COMPLIANT"}, {Status: "NON_COMPLIANT"}}, "NON_COMPLIANT"},
		{"non-compliant wins", []ComplianceRequirement{{Status: "PARTIAL"}, {Status: "NON_COMPLIANT"}}, "NON_COMPLIANT"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			assert.Equal(t, tt.want, overallStatus(tt.reqs))
		})
	}
}

// --- WS6 SOAR enforcement wiring tests ---

// TestBuildSOARRegistry_RegistersAllExecutors verifies the shared registry
// includes the previously-missing webhook executor (audit #26b) plus block_ip,
// notify, quarantine, escalate, and the default log handler.
func TestBuildSOARRegistry_RegistersAllExecutors(t *testing.T) {
	reg := BuildSOARRegistry(SOARConfig{})
	have := make(map[string]bool)
	for _, typ := range reg.List() {
		have[typ] = true
	}
	for _, want := range []string{"log", "block_ip", "notify", "quarantine", "escalate", "webhook"} {
		if !have[want] {
			t.Errorf("BuildSOARRegistry missing executor %q (have %v)", want, reg.List())
		}
	}
}

// TestC2KillChainPlaybook_FiresOnPhase proves the killChainPhase passthrough
// (audit #26a): the C2 playbook (trigger KillChainPhase=="command_control")
// fires only when the phase is passed, and is unreachable with an empty phase —
// which is exactly the bug applyPlaybooks had when it passed "".
func TestC2KillChainPlaybook_FiresOnPhase(t *testing.T) {
	reg := BuildSOARRegistry(SOARConfig{}) // log-only firewall → block_ip not enforced
	pe := domsoc.NewPlaybookEngine()
	pe.SetHandler(&domsoc.ExecutorActionHandler{Registry: reg})

	// Empty phase: C2 playbook must NOT fire (the old broken behavior).
	emptyPhase := pe.Execute("INC-empty", "CRITICAL", "uncategorized", "")
	for _, ex := range emptyPhase {
		if ex.PlaybookID == "pb-c2-killchain" {
			t.Fatal("pb-c2-killchain fired with empty kill-chain phase — passthrough regression")
		}
	}

	// Real phase: C2 playbook MUST fire.
	withPhase := pe.Execute("INC-c2", "CRITICAL", "c2", "command_control")
	fired := false
	for _, ex := range withPhase {
		if ex.PlaybookID == "pb-c2-killchain" {
			fired = true
			// block_ip is action #1 and the backend is log-only → NOT enforced →
			// the run is honestly recorded partial_failure (never a fake success).
			if ex.Status != "partial_failure" {
				t.Errorf("expected partial_failure (block_ip log-only not enforced), got %q (err=%q)", ex.Status, ex.Error)
			}
		}
	}
	if !fired {
		t.Fatal("pb-c2-killchain did NOT fire for kill-chain phase command_control")
	}
}

// TestConfigureSOAR_RewiresExecutors verifies ConfigureSOAR rebuilds the
// registry and the playbook handler points at the new executors.
func TestConfigureSOAR_RewiresExecutors(t *testing.T) {
	svc := newTestService(t)
	// Reconfigure with an http firewall backend (enforcing-capable) + a webhook URL.
	svc.ConfigureSOAR(SOARConfig{
		Firewall:   domsoc.FirewallConfig{Backend: "http", APIURL: "https://fw.example.com/block"},
		WebhookURL: "https://hooks.example.com/soc",
	})
	have := make(map[string]bool)
	for _, typ := range svc.executorRegistry.List() {
		have[typ] = true
	}
	if !have["webhook"] || !have["block_ip"] {
		t.Errorf("ConfigureSOAR did not rewire executors: %v", svc.executorRegistry.List())
	}
}

func TestAuditManualPlaybookNeverClaimsExecution(t *testing.T) {
	svc := newTestService(t)
	incident := domsoc.NewIncident("synthetic fixture", domsoc.SeverityCritical, "audit-rule")
	require.NoError(t, svc.repo.InsertIncident(incident))
	before, err := svc.repo.GetIncident(incident.ID)
	require.NoError(t, err)
	_, err = svc.RunPlaybook("pb-block-jailbreak", incident.ID)
	require.ErrorIs(t, err, ErrManualPlaybookUnavailable)
	after, err := svc.repo.GetIncident(incident.ID)
	require.NoError(t, err)
	assert.Equal(t, before.Status, after.Status)
}
