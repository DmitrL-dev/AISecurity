package soc

import (
	"sort"
	"time"
)

// SOCCorrelationRule defines a time-windowed correlation rule for SOC events.
// Supports two modes:
//   - Co-occurrence: RequiredCategories must all appear within TimeWindow (unordered)
//   - Temporal sequence: SequenceCategories must appear in ORDER within TimeWindow
type SOCCorrelationRule struct {
	ID                 string        `json:"id"`
	Name               string        `json:"name"`
	RequiredCategories []string      `json:"required_categories"`  // Co-occurrence (unordered)
	SequenceCategories []string      `json:"sequence_categories"` // Temporal sequence (ordered A→B→C)
	SeverityTrend      string        `json:"severity_trend,omitempty"` // "ascending" — detect escalation pattern
	TrendCategory      string        `json:"trend_category,omitempty"` // Category to track for severity trend
	MinEvents          int           `json:"min_events"`
	TimeWindow         time.Duration `json:"time_window"`
	Severity           EventSeverity `json:"severity"`
	KillChainPhase     string        `json:"kill_chain_phase"`
	MITREMapping       []string      `json:"mitre_mapping"`
	Description        string        `json:"description"`
	CrossSensor        bool          `json:"cross_sensor"`
}

// DefaultSOCCorrelationRules returns built-in SOC correlation rules (§7 from spec).
func DefaultSOCCorrelationRules() []SOCCorrelationRule {
	return []SOCCorrelationRule{
		{
			ID:                 "SOC-CR-001",
			Name:               "Multi-stage Jailbreak",
			RequiredCategories: []string{"jailbreak", "tool_abuse"},
			MinEvents:          2,
			TimeWindow:         5 * time.Minute,
			Severity:           SeverityCritical,
			KillChainPhase:     "Exploitation",
			MITREMapping:       []string{"T1059", "T1203"},
			Description:        "Jailbreak attempt followed by tool abuse indicates a staged attack to bypass guardrails and escalate privileges.",
		},
		{
			ID:                 "SOC-CR-002",
			Name:               "Coordinated Attack",
			RequiredCategories: []string{}, // Any 3+ distinct categories from same source
			MinEvents:          3,
			TimeWindow:         10 * time.Minute,
			Severity:           SeverityCritical,
			KillChainPhase:     "Exploitation",
			MITREMapping:       []string{"T1595", "T1190"},
			Description:        "Three or more distinct threat categories from the same source within 10 minutes indicates a coordinated multi-vector attack.",
		},
		{
			ID:                 "SOC-CR-003",
			Name:               "Privilege Escalation Chain",
			RequiredCategories: []string{"auth_bypass", "exfiltration"},
			MinEvents:          2,
			TimeWindow:         15 * time.Minute,
			Severity:           SeverityCritical,
			KillChainPhase:     "Exfiltration",
			MITREMapping:       []string{"T1078", "T1041"},
			Description:        "Authentication bypass followed by data exfiltration attempt within 15 minutes indicates a credential compromise leading to data theft.",
		},
		{
			ID:                 "SOC-CR-004",
			Name:               "Injection Escalation",
			RequiredCategories: []string{"prompt_injection", "jailbreak"},
			MinEvents:          2,
			TimeWindow:         5 * time.Minute,
			Severity:           SeverityHigh,
			KillChainPhase:     "Exploitation",
			MITREMapping:       []string{"T1059.007"},
			Description:        "Prompt injection followed by jailbreak within 5 minutes indicates progressive guardrail erosion attack.",
		},
		{
			ID:                 "SOC-CR-005",
			Name:               "Sensor Manipulation",
			RequiredCategories: []string{"sensor_anomaly", "tool_abuse"},
			MinEvents:          2,
			TimeWindow:         5 * time.Minute,
			Severity:           SeverityCritical,
			KillChainPhase:     "Defense Evasion",
			MITREMapping:       []string{"T1562"},
			Description:        "Sensor anomaly combined with tool abuse suggests attacker is trying to blind defensing before exploitation.",
		},
		{
			ID:                 "SOC-CR-006",
			Name:               "Data Exfiltration Pipeline",
			RequiredCategories: []string{"exfiltration", "encoding"},
			MinEvents:          2,
			TimeWindow:         10 * time.Minute,
			Severity:           SeverityCritical,
			KillChainPhase:     "Exfiltration",
			MITREMapping:       []string{"T1041", "T1132"},
			Description:        "Data exfiltration combined with encoding/obfuscation indicates staged data theft with cover-up.",
		},
		{
			ID:                 "SOC-CR-007",
			Name:               "Stealth Persistence",
			RequiredCategories: []string{"jailbreak", "persistence"},
			MinEvents:          2,
			TimeWindow:         30 * time.Minute,
			Severity:           SeverityHigh,
			KillChainPhase:     "Persistence",
			MITREMapping:       []string{"T1546", "T1053"},
			Description:        "Jailbreak followed by persistence mechanism indicates attacker establishing long-term foothold.",
		},
		{
			ID:                 "SOC-CR-008",
			Name:               "Slow Data Exfiltration",
			RequiredCategories: []string{"pii_leak", "exfiltration"},
			MinEvents:          5,
			TimeWindow:         1 * time.Hour,
			Severity:           SeverityHigh,
			KillChainPhase:     "Exfiltration",
			MITREMapping:       []string{"T1041", "T1048"},
			Description:        "Multiple small PII leaks over extended period from same session. Low-and-slow exfiltration evades threshold-based detection.",
		},
		// --- Temporal sequence rules (ordered A→B→C) ---
		{
			ID:                 "SOC-CR-009",
			Name:               "Recon→Exploit→Exfil Chain",
			SequenceCategories: []string{"reconnaissance", "prompt_injection", "exfiltration"},
			MinEvents:          3,
			TimeWindow:         30 * time.Minute,
			Severity:           SeverityCritical,
			KillChainPhase:     "Full Kill Chain",
			MITREMapping:       []string{"T1595", "T1059", "T1041"},
			Description:        "Ordered sequence: reconnaissance followed by prompt injection followed by data exfiltration. Full kill chain attack in progress.",
		},
		{
			ID:                 "SOC-CR-010",
			Name:               "Auth Spray→Bypass Sequence",
			SequenceCategories: []string{"auth_bypass", "tool_abuse"},
			MinEvents:          2,
			TimeWindow:         10 * time.Minute,
			Severity:           SeverityHigh,
			KillChainPhase:     "Exploitation",
			MITREMapping:       []string{"T1110", "T1078"},
			Description:        "Authentication bypass attempt followed by tool abuse within 10 minutes. Credential compromise leading to privilege escalation.",
		},
		{
			ID:             "SOC-CR-011",
			Name:           "Cross-Sensor Session Attack",
			MinEvents:      3,
			TimeWindow:     15 * time.Minute,
			Severity:       SeverityCritical,
			KillChainPhase: "Lateral Movement",
			MITREMapping:   []string{"T1021", "T1550"},
			CrossSensor:    true,
			Description:    "Same session_id seen across 3+ distinct sensors within 15 minutes. Indicates a compromised session exploited from multiple attack vectors.",
		},
		// ── Lattice Integration Rules ──────────────────────────────────
		{
			ID:                 "SOC-CR-012",
			Name:               "TSA Chain Violation",
			SequenceCategories: []string{"auth_bypass", "tool_abuse", "exfiltration"},
			MinEvents:          3,
			TimeWindow:         15 * time.Minute,
			Severity:           SeverityCritical,
			KillChainPhase:     "Actions on Objectives",
			MITREMapping:       []string{"T1078", "T1059", "T1048"},
			Description:        "Trust-Safety-Alignment chain violation: auth bypass followed by tool abuse and data exfiltration within 15 minutes. Full kill chain detected.",
		},
		{
			ID:                 "SOC-CR-013",
			Name:               "GPS Early Warning",
			RequiredCategories: []string{"anomaly", "exfiltration"},
			MinEvents:          2,
			TimeWindow:         10 * time.Minute,
			Severity:           SeverityHigh,
			KillChainPhase:     "Reconnaissance",
			MITREMapping:       []string{"T1595", "T1041"},
			Description:        "Guardrail-Perimeter-Surveillance early warning: anomaly detection followed by exfiltration attempt. Potential reconnaissance-to-extraction pipeline.",
		},
		{
			ID:                 "SOC-CR-014",
			Name:               "MIRE Containment Activated",
			SequenceCategories: []string{"prompt_injection", "jailbreak"},
			MinEvents:          2,
			TimeWindow:         5 * time.Minute,
			Severity:           SeverityCritical,
			KillChainPhase:     "Weaponization",
			MITREMapping:       []string{"T1059.007", "T1203"},
			Description:        "Monitor-Isolate-Respond-Evaluate containment: prompt injection escalated to jailbreak within 5 minutes. Immune system response required.",
		},
		// ── Severity Trend Rules ──────────────────────────────────────
		{
			ID:             "SOC-CR-015",
			Name:           "Crescendo Escalation",
			SeverityTrend:  "ascending",
			TrendCategory:  "jailbreak",
			MinEvents:      3,
			TimeWindow:     15 * time.Minute,
			Severity:       SeverityCritical,
			KillChainPhase: "Exploitation",
			MITREMapping:   []string{"T1059", "T1548"},
			Description:    "Crescendo attack: 3+ jailbreak attempts with ascending severity within 15 minutes. Gradual guardrail erosion detected.",
		},
		// ── Shadow AI Rules (§C³ Shadow Guard) ──────────────────────────
		{
			ID:                 "SOC-CR-022",
			Name:               "Shadow AI Exfiltration",
			RequiredCategories: []string{"shadow_ai", "exfiltration"},
			MinEvents:          2,
			TimeWindow:         30 * time.Minute,
			Severity:           SeverityCritical,
			KillChainPhase:     "Exfiltration",
			MITREMapping:       []string{"T1567", "T1048"},
			Description:        "Shadow AI usage combined with data exfiltration. Unauthorized AI tool sending corporate data to external endpoints.",
		},
		{
			ID:                 "SOC-CR-023",
			Name:               "Shadow AI Credential Spray",
			SequenceCategories: []string{"shadow_ai", "auth_bypass"},
			MinEvents:          2,
			TimeWindow:         10 * time.Minute,
			Severity:           SeverityHigh,
			KillChainPhase:     "Initial Access",
			MITREMapping:       []string{"T1110", "T1567"},
			Description:        "Shadow AI detected followed by auth bypass. AI tool used as recon before credential attack.",
		},
	}
}

// CorrelationMatch represents a triggered correlation rule with matched events.
type CorrelationMatch struct {
	Rule      SOCCorrelationRule `json:"rule"`
	Events    []SOCEvent         `json:"events"`
	MatchedAt time.Time          `json:"matched_at"`
}

// CorrelateSOCEvents runs all correlation rules against a set of events.
// Events should be pre-filtered to a reasonable time window (e.g., last hour).
// Returns matches sorted by severity (CRITICAL first).
func CorrelateSOCEvents(events []SOCEvent, rules []SOCCorrelationRule) []CorrelationMatch {
	if len(events) == 0 || len(rules) == 0 {
		return nil
	}

	now := time.Now()
	var matches []CorrelationMatch

	for _, rule := range rules {
		match := evaluateRule(rule, events, now)
		if match != nil {
			matches = append(matches, *match)
		}
	}

	// Sort by severity (CRITICAL first)
	sort.Slice(matches, func(i, j int) bool {
		return matches[i].Rule.Severity.Rank() > matches[j].Rule.Severity.Rank()
	})

	return matches
}

// evaluateRule checks if a single rule matches against the event set.
func evaluateRule(rule SOCCorrelationRule, events []SOCEvent, now time.Time) *CorrelationMatch {
	windowStart := now.Add(-rule.TimeWindow)

	// Filter events within time window.
	var inWindow []SOCEvent
	for _, e := range events {
		if !e.Timestamp.Before(windowStart) {
			inWindow = append(inWindow, e)
		}
	}

	if len(inWindow) < rule.MinEvents {
		return nil
	}

	// Severity trend: detect ascending severity in same-category events.
	if rule.SeverityTrend == "ascending" && rule.TrendCategory != "" {
		return evaluateSeverityTrendRule(rule, inWindow)
	}

	// Temporal sequence: check ordered occurrence (A→B→C within window).
	if len(rule.SequenceCategories) > 0 {
		return evaluateSequenceRule(rule, inWindow)
	}

	// Cross-sensor session attack: same session_id across 3+ distinct sources.
	if rule.CrossSensor {
		return evaluateCrossSensorRule(rule, inWindow)
	}

	// Special case: SOC-CR-002 (Coordinated Attack) — check distinct category count.
	if len(rule.RequiredCategories) == 0 && rule.MinEvents > 0 {
		return evaluateCoordinatedAttack(rule, inWindow)
	}

	// Standard case: check that all required categories are present.
	categorySet := make(map[string]bool)
	var matchedEvents []SOCEvent
	for _, e := range inWindow {
		categorySet[e.Category] = true
		// Collect events matching required categories.
		for _, rc := range rule.RequiredCategories {
			if e.Category == rc {
				matchedEvents = append(matchedEvents, e)
				break
			}
		}
	}

	// Check all required categories are present.
	for _, rc := range rule.RequiredCategories {
		if !categorySet[rc] {
			return nil
		}
	}

	if len(matchedEvents) < rule.MinEvents {
		return nil
	}

	return &CorrelationMatch{
		Rule:      rule,
		Events:    matchedEvents,
		MatchedAt: time.Now(),
	}
}

// evaluateCoordinatedAttack checks for N+ distinct categories from same source.
func evaluateCoordinatedAttack(rule SOCCorrelationRule, events []SOCEvent) *CorrelationMatch {
	// Group by source, count distinct categories.
	sourceCategories := make(map[EventSource]map[string]bool)
	sourceEvents := make(map[EventSource][]SOCEvent)

	for _, e := range events {
		if sourceCategories[e.Source] == nil {
			sourceCategories[e.Source] = make(map[string]bool)
		}
		sourceCategories[e.Source][e.Category] = true
		sourceEvents[e.Source] = append(sourceEvents[e.Source], e)
	}

	for source, cats := range sourceCategories {
		if len(cats) >= rule.MinEvents {
			return &CorrelationMatch{
				Rule:      rule,
				Events:    sourceEvents[source],
				MatchedAt: time.Now(),
			}
		}
	}
	return nil
}

// evaluateCrossSensorRule detects the same session_id seen across N+ distinct sources/sensors.
// Triggers SOC-CR-011: indicates lateral movement or compromised session.
func evaluateCrossSensorRule(rule SOCCorrelationRule, events []SOCEvent) *CorrelationMatch {
	// Group events by session_id, track distinct sources per session.
	type sessionInfo struct {
		sources map[EventSource]bool
		events  []SOCEvent
	}
	sessions := make(map[string]*sessionInfo)

	for _, e := range events {
		if e.SessionID == "" {
			continue
		}
		si, ok := sessions[e.SessionID]
		if !ok {
			si = &sessionInfo{sources: make(map[EventSource]bool)}
			sessions[e.SessionID] = si
		}
		si.sources[e.Source] = true
		si.events = append(si.events, e)
	}

	for _, si := range sessions {
		if len(si.sources) >= rule.MinEvents {
			return &CorrelationMatch{
				Rule:      rule,
				Events:    si.events,
				MatchedAt: time.Now(),
			}
		}
	}
	return nil
}

// evaluateSequenceRule checks for ordered temporal sequences (A→B→C).
// Events must appear in the specified order within the time window.
func evaluateSequenceRule(rule SOCCorrelationRule, events []SOCEvent) *CorrelationMatch {
	// Sort events by timestamp (oldest first).
	sorted := make([]SOCEvent, len(events))
	copy(sorted, events)
	sort.Slice(sorted, func(i, j int) bool {
		return sorted[i].Timestamp.Before(sorted[j].Timestamp)
	})

	// Walk through events, matching each sequence step in order.
	seqIdx := 0
	var matchedEvents []SOCEvent
	var firstTime time.Time

	for _, e := range sorted {
		if seqIdx >= len(rule.SequenceCategories) {
			break
		}
		if e.Category == rule.SequenceCategories[seqIdx] {
			if seqIdx == 0 {
				firstTime = e.Timestamp
			}
			// Ensure all events are within the time window of the first event.
			if seqIdx > 0 && e.Timestamp.Sub(firstTime) > rule.TimeWindow {
				// Window exceeded — reset and try from this event.
				seqIdx = 0
				matchedEvents = nil
				if e.Category == rule.SequenceCategories[0] {
					firstTime = e.Timestamp
					matchedEvents = append(matchedEvents, e)
					seqIdx = 1
				}
				continue
			}
			matchedEvents = append(matchedEvents, e)
			seqIdx++
		}
	}

	// All sequence steps matched?
	if seqIdx >= len(rule.SequenceCategories) {
		return &CorrelationMatch{
			Rule:      rule,
			Events:    matchedEvents,
			MatchedAt: time.Now(),
		}
	}
	return nil
}

// evaluateSeverityTrendRule detects ascending severity pattern in same-category events.
// Example: jailbreak(LOW) → jailbreak(MEDIUM) → jailbreak(HIGH) within 15 min = CRESCENDO.
func evaluateSeverityTrendRule(rule SOCCorrelationRule, events []SOCEvent) *CorrelationMatch {
	// Filter to target category only.
	var categoryEvents []SOCEvent
	for _, e := range events {
		if e.Category == rule.TrendCategory {
			categoryEvents = append(categoryEvents, e)
		}
	}

	if len(categoryEvents) < rule.MinEvents {
		return nil
	}

	// Sort by timestamp.
	sort.Slice(categoryEvents, func(i, j int) bool {
		return categoryEvents[i].Timestamp.Before(categoryEvents[j].Timestamp)
	})

	// Find longest ascending severity subsequence.
	var bestRun []SOCEvent
	var currentRun []SOCEvent

	for _, e := range categoryEvents {
		if len(currentRun) == 0 || e.Severity.Rank() > currentRun[len(currentRun)-1].Severity.Rank() {
			currentRun = append(currentRun, e)
		} else {
			if len(currentRun) > len(bestRun) {
				bestRun = currentRun
			}
			currentRun = []SOCEvent{e}
		}
	}
	if len(currentRun) > len(bestRun) {
		bestRun = currentRun
	}

	if len(bestRun) >= rule.MinEvents {
		return &CorrelationMatch{
			Rule:      rule,
			Events:    bestRun,
			MatchedAt: time.Now(),
		}
	}
	return nil
}
