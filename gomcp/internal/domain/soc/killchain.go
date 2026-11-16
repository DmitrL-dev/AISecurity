package soc

import (
	"sort"
	"time"
)

// KillChainPhases defines the standard Cyber Kill Chain phases (Lockheed Martin + MITRE ATT&CK).
var KillChainPhases = []string{
	"Reconnaissance",
	"Weaponization",
	"Delivery",
	"Exploitation",
	"Installation",
	"Command & Control",
	"Actions on Objectives",
	// AI-specific additions:
	"Defense Evasion",
	"Persistence",
	"Exfiltration",
	"Impact",
}

// KillChainStep represents one step in a reconstructed attack chain.
type KillChainStep struct {
	Phase      string    `json:"phase"`
	EventIDs   []string  `json:"event_ids"`
	Severity   string    `json:"severity"`
	Categories []string  `json:"categories"`
	FirstSeen  time.Time `json:"first_seen"`
	LastSeen   time.Time `json:"last_seen"`
	RuleID     string    `json:"rule_id,omitempty"`
}

// KillChain represents a reconstructed attack chain from correlated incidents.
type KillChain struct {
	ID         string          `json:"id"`
	IncidentID string          `json:"incident_id"`
	Steps      []KillChainStep `json:"steps"`
	Coverage   float64         `json:"coverage"` // 0.0-1.0: fraction of Kill Chain phases observed
	MaxPhase   string          `json:"max_phase"`
	StartTime  time.Time       `json:"start_time"`
	EndTime    time.Time       `json:"end_time"`
	Duration   string          `json:"duration"`
}

// ReconstructKillChain builds an attack chain from an incident and its events.
func ReconstructKillChain(incident Incident, events []SOCEvent, rules []SOCCorrelationRule) *KillChain {
	if len(events) == 0 {
		return nil
	}

	// Map rule ID → kill chain phase
	rulePhases := make(map[string]string)
	for _, r := range rules {
		rulePhases[r.ID] = r.KillChainPhase
	}

	// Group events by kill chain phase
	phaseEvents := make(map[string][]SOCEvent)
	for _, e := range events {
		phase := categorizePhase(e.Category, rulePhases, incident.CorrelationRule)
		if phase != "" {
			phaseEvents[phase] = append(phaseEvents[phase], e)
		}
	}

	// Build steps
	var steps []KillChainStep
	for _, phase := range KillChainPhases {
		evts, ok := phaseEvents[phase]
		if !ok {
			continue
		}

		cats := uniqueCategories(evts)
		ids := make([]string, len(evts))
		var firstSeen, lastSeen time.Time
		maxSev := SeverityInfo

		for i, e := range evts {
			ids[i] = e.ID
			if firstSeen.IsZero() || e.Timestamp.Before(firstSeen) {
				firstSeen = e.Timestamp
			}
			if e.Timestamp.After(lastSeen) {
				lastSeen = e.Timestamp
			}
			if e.Severity.Rank() > maxSev.Rank() {
				maxSev = e.Severity
			}
		}

		steps = append(steps, KillChainStep{
			Phase:      phase,
			EventIDs:   ids,
			Severity:   string(maxSev),
			Categories: cats,
			FirstSeen:  firstSeen,
			LastSeen:   lastSeen,
			RuleID:     incident.CorrelationRule,
		})
	}

	if len(steps) == 0 {
		return nil
	}

	// Sort by first seen
	sort.Slice(steps, func(i, j int) bool {
		return steps[i].FirstSeen.Before(steps[j].FirstSeen)
	})

	coverage := float64(len(steps)) / float64(len(KillChainPhases))
	startTime := steps[0].FirstSeen
	endTime := steps[len(steps)-1].LastSeen
	duration := endTime.Sub(startTime)

	return &KillChain{
		ID:         "KC-" + incident.ID,
		IncidentID: incident.ID,
		Steps:      steps,
		Coverage:   coverage,
		MaxPhase:   steps[len(steps)-1].Phase,
		StartTime:  startTime,
		EndTime:    endTime,
		Duration:   duration.String(),
	}
}

// categorizePhase maps event category → Kill Chain phase.
func categorizePhase(category string, rulePhases map[string]string, ruleID string) string {
	// First check if the triggering rule has a phase
	if phase, ok := rulePhases[ruleID]; ok && phase != "" {
		return phase
	}

	// Category → phase mapping
	switch category {
	case "reconnaissance", "scanning", "enumeration":
		return "Reconnaissance"
	case "weaponization", "payload_crafting":
		return "Weaponization"
	case "delivery", "phishing", "social_engineering":
		return "Delivery"
	case "jailbreak", "prompt_injection", "injection", "exploitation":
		return "Exploitation"
	case "persistence", "backdoor":
		return "Persistence"
	case "command_control", "c2", "beacon":
		return "Command & Control"
	case "tool_abuse", "unauthorized_tool_use":
		return "Actions on Objectives"
	case "defense_evasion", "evasion", "obfuscation", "encoding":
		return "Defense Evasion"
	case "exfiltration", "data_leak", "data_theft":
		return "Exfiltration"
	case "auth_bypass", "brute_force", "credential_theft":
		return "Exploitation"
	case "sensor_anomaly", "sensor_manipulation":
		return "Defense Evasion"
	case "data_poisoning", "model_manipulation":
		return "Impact"
	default:
		return "Actions on Objectives"
	}
}

func uniqueCategories(events []SOCEvent) []string {
	seen := make(map[string]bool)
	var result []string
	for _, e := range events {
		if !seen[e.Category] {
			seen[e.Category] = true
			result = append(result, e.Category)
		}
	}
	return result
}
