package soc

import (
	"testing"
	"time"
)

// === Event Tests ===

func TestNewSOCEvent(t *testing.T) {
	e := NewSOCEvent(SourceSentinelCore, SeverityHigh, "jailbreak", "Detected jailbreak attempt")
	if e.Source != SourceSentinelCore {
		t.Errorf("expected source sentinel-core, got %s", e.Source)
	}
	if e.Severity != SeverityHigh {
		t.Errorf("expected severity HIGH, got %s", e.Severity)
	}
	if e.Category != "jailbreak" {
		t.Errorf("expected category jailbreak, got %s", e.Category)
	}
	if e.Verdict != VerdictReview {
		t.Errorf("expected default verdict REVIEW, got %s", e.Verdict)
	}
	if e.ID == "" {
		t.Error("expected non-empty ID")
	}
}

func TestEventSeverityRank(t *testing.T) {
	tests := []struct {
		sev  EventSeverity
		rank int
	}{
		{SeverityInfo, 1},
		{SeverityLow, 2},
		{SeverityMedium, 3},
		{SeverityHigh, 4},
		{SeverityCritical, 5},
	}
	for _, tt := range tests {
		if got := tt.sev.Rank(); got != tt.rank {
			t.Errorf("%s.Rank() = %d, want %d", tt.sev, got, tt.rank)
		}
	}
}

func TestEventBuilders(t *testing.T) {
	e := NewSOCEvent(SourceShield, SeverityMedium, "network_block", "Blocked connection").
		WithSensor("shield-01").
		WithConfidence(0.85).
		WithVerdict(VerdictDeny)

	if e.SensorID != "shield-01" {
		t.Errorf("expected sensor shield-01, got %s", e.SensorID)
	}
	if e.Confidence != 0.85 {
		t.Errorf("expected confidence 0.85, got %f", e.Confidence)
	}
	if e.Verdict != VerdictDeny {
		t.Errorf("expected verdict DENY, got %s", e.Verdict)
	}
}

func TestEventConfidenceClamping(t *testing.T) {
	e := NewSOCEvent(SourceGoMCP, SeverityInfo, "test", "test")
	if e2 := e.WithConfidence(-0.5); e2.Confidence != 0 {
		t.Errorf("expected clamped to 0, got %f", e2.Confidence)
	}
	if e2 := e.WithConfidence(1.5); e2.Confidence != 1 {
		t.Errorf("expected clamped to 1, got %f", e2.Confidence)
	}
}

func TestEventIsCritical(t *testing.T) {
	if !NewSOCEvent(SourceGoMCP, SeverityHigh, "x", "x").IsCritical() {
		t.Error("HIGH should be critical")
	}
	if !NewSOCEvent(SourceGoMCP, SeverityCritical, "x", "x").IsCritical() {
		t.Error("CRITICAL should be critical")
	}
	if NewSOCEvent(SourceGoMCP, SeverityMedium, "x", "x").IsCritical() {
		t.Error("MEDIUM should not be critical")
	}
}

// === Incident Tests ===

func TestNewIncident(t *testing.T) {
	inc := NewIncident("Multi-stage Jailbreak", SeverityHigh, "jailbreak_chain")
	if inc.Status != StatusOpen {
		t.Errorf("expected OPEN, got %s", inc.Status)
	}
	if inc.Severity != SeverityHigh {
		t.Errorf("expected HIGH, got %s", inc.Severity)
	}
	if inc.ID == "" {
		t.Error("expected non-empty ID")
	}
	if !inc.IsOpen() {
		t.Error("new incident should be open")
	}
}

func TestIncidentAddEvent(t *testing.T) {
	inc := NewIncident("Test", SeverityMedium, "test_rule")
	inc.AddEvent("evt-1", SeverityMedium)
	inc.AddEvent("evt-2", SeverityCritical)

	if inc.EventCount != 2 {
		t.Errorf("expected 2 events, got %d", inc.EventCount)
	}
	if inc.Severity != SeverityCritical {
		t.Errorf("severity should escalate to CRITICAL, got %s", inc.Severity)
	}
}

func TestIncidentResolve(t *testing.T) {
	inc := NewIncident("Test", SeverityHigh, "test_rule")
	inc.Resolve(StatusResolved, "system")

	if inc.IsOpen() {
		t.Error("resolved incident should not be open")
	}
	if inc.ResolvedAt == nil {
		t.Error("resolved incident should have resolved timestamp")
	}
	if inc.Status != StatusResolved {
		t.Errorf("expected RESOLVED, got %s", inc.Status)
	}
}

func TestIncidentSetAnchor(t *testing.T) {
	inc := NewIncident("Test", SeverityHigh, "test_rule")
	inc.SetAnchor("abc123def456", 7)
	if inc.DecisionChainAnchor != "abc123def456" {
		t.Error("anchor not set")
	}
	if inc.ChainLength != 7 {
		t.Errorf("expected chain length 7, got %d", inc.ChainLength)
	}
}

func TestIncidentMTTR(t *testing.T) {
	inc := NewIncident("Test", SeverityHigh, "test_rule")
	if inc.MTTR() != 0 {
		t.Error("unresolved MTTR should be 0")
	}
	time.Sleep(10 * time.Millisecond)
	inc.Resolve(StatusResolved, "system")
	if inc.MTTR() <= 0 {
		t.Error("resolved MTTR should be positive")
	}
}

// === Sensor Tests ===

func TestSensorLifecycle(t *testing.T) {
	s := NewSensor("core-01", SensorTypeSentinelCore)

	// Initially UNKNOWN
	if s.Status != SensorStatusUnknown {
		t.Errorf("expected UNKNOWN, got %s", s.Status)
	}

	// After 2 events still UNKNOWN
	s.RecordEvent()
	s.RecordEvent()
	if s.Status != SensorStatusUnknown {
		t.Errorf("expected UNKNOWN after 2 events, got %s", s.Status)
	}

	// After 3rd event → HEALTHY
	s.RecordEvent()
	if s.Status != SensorStatusHealthy {
		t.Errorf("expected HEALTHY after 3 events, got %s", s.Status)
	}

	// 3 missed heartbeats → DEGRADED
	for i := 0; i < MissedHeartbeatDegraded; i++ {
		s.MissHeartbeat()
	}
	if s.Status != SensorStatusDegraded {
		t.Errorf("expected DEGRADED, got %s", s.Status)
	}

	// Activity recovers from DEGRADED
	s.RecordEvent()
	if s.Status != SensorStatusHealthy {
		t.Errorf("expected recovery to HEALTHY, got %s", s.Status)
	}
}

func TestSensorOfflineAlert(t *testing.T) {
	s := NewSensor("shield-01", SensorTypeShield)
	// Get to HEALTHY first
	for i := 0; i < EventsToHealthy; i++ {
		s.RecordEvent()
	}

	// Miss heartbeats until OFFLINE
	var alertGenerated bool
	for i := 0; i < MissedHeartbeatOffline; i++ {
		alertGenerated = s.MissHeartbeat()
	}
	if !alertGenerated {
		t.Error("expected alert on OFFLINE transition")
	}
	if s.Status != SensorStatusOffline {
		t.Errorf("expected OFFLINE, got %s", s.Status)
	}
}

func TestSensorHeartbeatRecovery(t *testing.T) {
	s := NewSensor("immune-01", SensorTypeImmune)
	for i := 0; i < EventsToHealthy; i++ {
		s.RecordEvent()
	}
	// Go degraded
	for i := 0; i < MissedHeartbeatDegraded; i++ {
		s.MissHeartbeat()
	}
	if s.Status != SensorStatusDegraded {
		t.Fatalf("expected DEGRADED, got %s", s.Status)
	}
	// Heartbeat recovery
	s.RecordHeartbeat()
	if s.Status != SensorStatusHealthy {
		t.Errorf("expected HEALTHY after heartbeat, got %s", s.Status)
	}
}

// === Playbook Engine Tests (§10) ===

func TestPlaybookEngine_Defaults(t *testing.T) {
	pe := NewPlaybookEngine()
	pbs := pe.ListPlaybooks()
	if len(pbs) != 4 {
		t.Errorf("expected 4 default playbooks, got %d", len(pbs))
	}
	for _, pb := range pbs {
		if !pb.Enabled {
			t.Errorf("playbook %s should be enabled", pb.ID)
		}
	}
}

func TestPlaybookEngine_JailbreakMatch(t *testing.T) {
	pe := NewPlaybookEngine()
	execs := pe.Execute("inc-001", "CRITICAL", "jailbreak", "")
	found := false
	for _, e := range execs {
		if e.PlaybookID == "pb-block-jailbreak" {
			found = true
		}
	}
	if !found {
		t.Error("expected pb-block-jailbreak to match CRITICAL jailbreak")
	}
}

func TestPlaybookEngine_SeverityFilter(t *testing.T) {
	pe := NewPlaybookEngine()
	execs := pe.Execute("inc-002", "LOW", "jailbreak", "")
	for _, e := range execs {
		if e.PlaybookID == "pb-block-jailbreak" {
			t.Error("LOW severity should not match CRITICAL threshold playbook")
		}
	}
}
