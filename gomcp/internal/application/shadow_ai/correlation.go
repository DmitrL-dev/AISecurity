package shadow_ai

import (
	"time"

	domsoc "github.com/syntrex/gomcp/internal/domain/soc"
)

// ShadowAICorrelationRules returns SOC correlation rules specific to Shadow AI
// detection. These integrate into the existing SOC correlation engine.
func ShadowAICorrelationRules() []domsoc.SOCCorrelationRule {
	return []domsoc.SOCCorrelationRule{
		{
			ID:                 "SAI-CR-001",
			Name:               "Multi-Service Shadow AI",
			RequiredCategories: []string{"shadow_ai_usage"},
			MinEvents:          3,
			TimeWindow:         10 * time.Minute,
			Severity:           domsoc.SeverityHigh,
			KillChainPhase:     "Reconnaissance",
			MITREMapping:       []string{"T1595"},
			Description:        "User accessing 3+ distinct AI services within 10 minutes. Indicates active AI tool exploration or data shopping across providers.",
		},
		{
			ID:                 "SAI-CR-002",
			Name:               "Shadow AI + Data Exfiltration",
			RequiredCategories: []string{"shadow_ai_usage", "exfiltration"},
			MinEvents:          2,
			TimeWindow:         15 * time.Minute,
			Severity:           domsoc.SeverityCritical,
			KillChainPhase:     "Exfiltration",
			MITREMapping:       []string{"T1041", "T1567"},
			Description:        "Shadow AI usage followed by data exfiltration attempt. Possible corporate data leakage via unauthorized AI services.",
		},
		{
			ID:                 "SAI-CR-003",
			Name:               "Shadow AI Volume Spike",
			RequiredCategories: []string{"shadow_ai_usage"},
			MinEvents:          10,
			TimeWindow:         1 * time.Hour,
			Severity:           domsoc.SeverityHigh,
			KillChainPhase:     "Actions on Objectives",
			MITREMapping:       []string{"T1048"},
			Description:        "10+ shadow AI events from same source within 1 hour. Indicates bulk data transfer to external AI service.",
		},
		{
			ID:                 "SAI-CR-004",
			Name:               "Shadow AI After Hours",
			RequiredCategories: []string{"shadow_ai_usage"},
			MinEvents:          2,
			TimeWindow:         30 * time.Minute,
			Severity:           domsoc.SeverityMedium,
			KillChainPhase:     "Persistence",
			MITREMapping:       []string{"T1053"},
			Description:        "Shadow AI usage outside business hours (detected via timestamp clustering). May indicate automated scripts or insider threat.",
		},
		{
			ID:                 "SAI-CR-005",
			Name:               "Integration Failure Chain",
			RequiredCategories: []string{"integration_health"},
			MinEvents:          3,
			TimeWindow:         5 * time.Minute,
			Severity:           domsoc.SeverityCritical,
			KillChainPhase:     "Defense Evasion",
			MITREMapping:       []string{"T1562"},
			Description:        "3+ integration health failures in 5 minutes. Possible attack on enforcement infrastructure to blind Shadow AI detection.",
		},
		{
			ID:                 "SAI-CR-006",
			Name:               "Shadow AI + PII Leak",
			RequiredCategories: []string{"shadow_ai_usage", "pii_leak"},
			MinEvents:          2,
			TimeWindow:         10 * time.Minute,
			Severity:           domsoc.SeverityCritical,
			KillChainPhase:     "Exfiltration",
			MITREMapping:       []string{"T1567.002"},
			Description:        "Shadow AI usage combined with PII leak detection. GDPR/regulatory violation in progress — immediate response required.",
		},
		{
			ID:                 "SAI-CR-007",
			Name:               "Shadow AI Evasion Attempt",
			SequenceCategories: []string{"shadow_ai_usage", "evasion"},
			MinEvents:          2,
			TimeWindow:         10 * time.Minute,
			Severity:           domsoc.SeverityHigh,
			KillChainPhase:     "Defense Evasion",
			MITREMapping:       []string{"T1090", "T1573"},
			Description:        "Shadow AI usage followed by evasion technique (VPN, proxy chaining, encoding). User attempting to bypass detection.",
		},
		{
			ID:                 "SAI-CR-008",
			Name:               "Cross-Department AI Usage",
			RequiredCategories: []string{"shadow_ai_usage"},
			MinEvents:          5,
			TimeWindow:         30 * time.Minute,
			Severity:           domsoc.SeverityMedium,
			CrossSensor:        true,
			KillChainPhase:     "Lateral Movement",
			MITREMapping:       []string{"T1021"},
			Description:        "Shadow AI events from 5+ distinct network segments/sensors within 30 minutes. Indicates coordinated policy circumvention or compromised credentials used across departments.",
		},
		// Severity trend: escalating shadow AI event severity
		{
			ID:             "SAI-CR-009",
			Name:           "Shadow AI Escalation",
			SeverityTrend:  "ascending",
			TrendCategory:  "shadow_ai_usage",
			MinEvents:      3,
			TimeWindow:     30 * time.Minute,
			Severity:       domsoc.SeverityCritical,
			KillChainPhase: "Exploitation",
			MITREMapping:   []string{"T1059"},
			Description:    "Ascending severity pattern in Shadow AI events: user escalating from casual browsing to bulk data uploads. Crescendo data theft in progress.",
		},
	}
}
