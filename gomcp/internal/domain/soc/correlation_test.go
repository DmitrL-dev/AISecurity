package soc

import (
	"testing"
	"time"
)

func TestCorrelateMultistageJailbreak(t *testing.T) {
	now := time.Now()
	events := []SOCEvent{
		{ID: "e1", Source: SourceSentinelCore, Category: "jailbreak", Severity: SeverityHigh, Timestamp: now.Add(-2 * time.Minute)},
		{ID: "e2", Source: SourceSentinelCore, Category: "tool_abuse", Severity: SeverityHigh, Timestamp: now.Add(-1 * time.Minute)},
	}

	rules := DefaultSOCCorrelationRules()
	matches := CorrelateSOCEvents(events, rules)

	found := false
	for _, m := range matches {
		if m.Rule.ID == "SOC-CR-001" {
			found = true
			if len(m.Events) < 2 {
				t.Errorf("expected at least 2 matched events, got %d", len(m.Events))
			}
		}
	}
	if !found {
		t.Error("SOC-CR-001 (Multi-stage Jailbreak) should have matched")
	}
}

func TestCorrelateOutsideWindow(t *testing.T) {
	now := time.Now()
	// Events too far apart — outside 5-minute window.
	events := []SOCEvent{
		{ID: "e1", Source: SourceSentinelCore, Category: "jailbreak", Severity: SeverityHigh, Timestamp: now.Add(-10 * time.Minute)},
		{ID: "e2", Source: SourceSentinelCore, Category: "tool_abuse", Severity: SeverityHigh, Timestamp: now.Add(-1 * time.Minute)},
	}

	rules := []SOCCorrelationRule{DefaultSOCCorrelationRules()[0]} // SOC-CR-001 only
	matches := CorrelateSOCEvents(events, rules)

	if len(matches) != 0 {
		t.Error("should not match events outside the time window")
	}
}

func TestCorrelateCoordinatedAttack(t *testing.T) {
	now := time.Now()
	events := []SOCEvent{
		{ID: "e1", Source: SourceSentinelCore, Category: "jailbreak", Timestamp: now.Add(-3 * time.Minute)},
		{ID: "e2", Source: SourceSentinelCore, Category: "injection", Timestamp: now.Add(-2 * time.Minute)},
		{ID: "e3", Source: SourceSentinelCore, Category: "exfiltration", Timestamp: now.Add(-1 * time.Minute)},
	}

	rules := DefaultSOCCorrelationRules()
	matches := CorrelateSOCEvents(events, rules)

	found := false
	for _, m := range matches {
		if m.Rule.ID == "SOC-CR-002" {
			found = true
			if len(m.Events) < 3 {
				t.Errorf("expected at least 3 matched events, got %d", len(m.Events))
			}
		}
	}
	if !found {
		t.Error("SOC-CR-002 (Coordinated Attack) should have matched")
	}
}

func TestCorrelateCoordinatedAttackDifferentSources(t *testing.T) {
	now := time.Now()
	// Events from different sources — should NOT match coordinated attack.
	events := []SOCEvent{
		{ID: "e1", Source: SourceSentinelCore, Category: "jailbreak", Timestamp: now.Add(-3 * time.Minute)},
		{ID: "e2", Source: SourceShield, Category: "injection", Timestamp: now.Add(-2 * time.Minute)},
		{ID: "e3", Source: SourceImmune, Category: "exfiltration", Timestamp: now.Add(-1 * time.Minute)},
	}

	rules := []SOCCorrelationRule{DefaultSOCCorrelationRules()[1]} // SOC-CR-002 only
	matches := CorrelateSOCEvents(events, rules)

	if len(matches) != 0 {
		t.Error("coordinated attack should only match same-source events")
	}
}

func TestCorrelatePrivilegeEscalation(t *testing.T) {
	now := time.Now()
	events := []SOCEvent{
		{ID: "e1", Source: SourceGoMCP, Category: "auth_bypass", Timestamp: now.Add(-10 * time.Minute)},
		{ID: "e2", Source: SourceGoMCP, Category: "exfiltration", Timestamp: now.Add(-2 * time.Minute)},
	}

	rules := DefaultSOCCorrelationRules()
	matches := CorrelateSOCEvents(events, rules)

	found := false
	for _, m := range matches {
		if m.Rule.ID == "SOC-CR-003" {
			found = true
		}
	}
	if !found {
		t.Error("SOC-CR-003 (Privilege Escalation Chain) should have matched")
	}
}

func TestCorrelateSortsBySeverity(t *testing.T) {
	now := time.Now()
	events := []SOCEvent{
		{ID: "e1", Source: SourceGoMCP, Category: "prompt_injection", Timestamp: now.Add(-2 * time.Minute)},
		{ID: "e2", Source: SourceGoMCP, Category: "jailbreak", Timestamp: now.Add(-1 * time.Minute)},
		{ID: "e3", Source: SourceGoMCP, Category: "tool_abuse", Timestamp: now.Add(-1 * time.Minute)},
	}

	rules := DefaultSOCCorrelationRules()
	matches := CorrelateSOCEvents(events, rules)

	if len(matches) < 2 {
		t.Fatalf("expected at least 2 matches, got %d", len(matches))
	}
	// First match should be CRITICAL (highest severity).
	if matches[0].Rule.Severity != SeverityCritical {
		t.Errorf("first match should be CRITICAL, got %s", matches[0].Rule.Severity)
	}
}

func TestCorrelateEmptyInput(t *testing.T) {
	if matches := CorrelateSOCEvents(nil, DefaultSOCCorrelationRules()); matches != nil {
		t.Error("nil events should return nil")
	}
	if matches := CorrelateSOCEvents([]SOCEvent{}, nil); matches != nil {
		t.Error("nil rules should return nil")
	}
}

func TestDefaultRuleCount(t *testing.T) {
	rules := DefaultSOCCorrelationRules()
	if len(rules) != 17 {
		t.Errorf("expected 17 default rules (15 original + 2 Shadow AI), got %d", len(rules))
	}
}
