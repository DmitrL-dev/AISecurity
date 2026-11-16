package soc

import "time"

// GenAI EDR Detection Rules (SDD-001)
//
// 6 correlation rules for detecting GenAI agent threats,
// ported from Elastic's production detection ruleset.
// Rules SOC-CR-016 through SOC-CR-021.

// GenAICorrelationRules returns the 6 GenAI-specific detection rules.
// These are appended to DefaultSOCCorrelationRules() in the correlation engine.
func GenAICorrelationRules() []SOCCorrelationRule {
	return []SOCCorrelationRule{
		// R1: GenAI Child Process Execution (BBR — info-level building block)
		{
			ID:                 "SOC-CR-016",
			Name:               "GenAI Child Process Execution",
			RequiredCategories: []string{CategoryGenAIChildProcess},
			MinEvents:          1,
			TimeWindow:         1 * time.Minute,
			Severity:           SeverityInfo,
			KillChainPhase:     "Execution",
			MITREMapping:       []string{"T1059"},
			Description:        "GenAI agent spawned a child process. Building block rule — provides visibility into GenAI process activity. Not actionable alone.",
		},
		// R2: GenAI Suspicious Descendant (sequence: child → suspicious tool)
		{
			ID:                 "SOC-CR-017",
			Name:               "GenAI Suspicious Descendant",
			SequenceCategories: []string{CategoryGenAIChildProcess, "tool_abuse"},
			MinEvents:          2,
			TimeWindow:         5 * time.Minute,
			Severity:           SeverityMedium,
			KillChainPhase:     "Execution",
			MITREMapping:       []string{"T1059", "T1059.004"},
			Description:        "GenAI agent spawned a child process that performed suspicious activity (shell execution, network tool usage). Potential GenAI-facilitated attack.",
		},
		// R3: GenAI Unusual Domain Connection (new_terms equivalent)
		{
			ID:                 "SOC-CR-018",
			Name:               "GenAI Unusual Domain Connection",
			RequiredCategories: []string{CategoryGenAIUnusualDomain},
			MinEvents:          1,
			TimeWindow:         5 * time.Minute,
			Severity:           SeverityMedium,
			KillChainPhase:     "Command and Control",
			MITREMapping:       []string{"T1071", "T1102"},
			Description:        "GenAI process connected to a previously-unseen domain. May indicate command-and-control channel established through GenAI agent.",
		},
		// R4: GenAI Credential Access (CRITICAL — auto kill_process)
		{
			ID:                 "SOC-CR-019",
			Name:               "GenAI Credential Access",
			SequenceCategories: []string{CategoryGenAIChildProcess, CategoryGenAICredentialAccess},
			MinEvents:          2,
			TimeWindow:         2 * time.Minute,
			Severity:           SeverityCritical,
			KillChainPhase:     "Credential Access",
			MITREMapping:       []string{"T1555", "T1539", "T1552"},
			Description:        "CRITICAL: GenAI agent or its descendant accessed credential file (credentials.db, cookies, logins.json, SSH keys). Auto-response: kill_process. This matches Elastic's production detection for real credential theft by Claude/Cursor processes.",
		},
		// R5: GenAI Persistence Mechanism
		{
			ID:                 "SOC-CR-020",
			Name:               "GenAI Persistence Mechanism",
			SequenceCategories: []string{CategoryGenAIChildProcess, CategoryGenAIPersistence},
			MinEvents:          2,
			TimeWindow:         10 * time.Minute,
			Severity:           SeverityHigh,
			KillChainPhase:     "Persistence",
			MITREMapping:       []string{"T1543", "T1547", "T1053"},
			Description:        "GenAI agent created a persistence mechanism (startup entry, LaunchAgent, cron job, systemd service). Establishing long-term foothold through AI agent.",
		},
		// R6: GenAI Config Modification by Non-GenAI Process
		{
			ID:                 "SOC-CR-021",
			Name:               "GenAI Config Modification",
			RequiredCategories: []string{CategoryGenAIConfigModification},
			MinEvents:          1,
			TimeWindow:         5 * time.Minute,
			Severity:           SeverityMedium,
			KillChainPhase:     "Defense Evasion",
			MITREMapping:       []string{"T1562", "T1112"},
			Description:        "Non-GenAI process modified GenAI agent configuration (hooks, MCP servers, tool permissions). Potential defense evasion or supply-chain attack via config poisoning.",
		},
	}
}

// GenAIAutoActions returns the auto-response actions for GenAI rules.
// Currently only SOC-CR-019 (credential access) has auto-response.
func GenAIAutoActions() map[string]*AutoAction {
	return map[string]*AutoAction{
		"SOC-CR-019": {
			Type:   "kill_process",
			Target: "genai_descendant",
			Reason: "GenAI descendant accessing credential files — immediate termination required per SDD-001 M5",
		},
	}
}

// AllSOCCorrelationRules returns all correlation rules including GenAI rules.
// This combines the 15 default rules with the 6 GenAI rules = 21 total.
func AllSOCCorrelationRules() []SOCCorrelationRule {
	rules := DefaultSOCCorrelationRules()
	rules = append(rules, GenAICorrelationRules()...)
	return rules
}

// EvaluateGenAIAutoResponse checks if a correlation match triggers an auto-response.
// Returns the AutoAction if one exists for the matched rule, or nil.
func EvaluateGenAIAutoResponse(match CorrelationMatch) *AutoAction {
	actions := GenAIAutoActions()
	if action, ok := actions[match.Rule.ID]; ok {
		return action
	}
	return nil
}
