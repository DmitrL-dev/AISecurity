package oracle

import (
	"fmt"
	"sort"
	"strings"
)

// CorrelationGroup represents a meta-threat synthesized from multiple related patterns.
type CorrelationGroup struct {
	MetaThreat  string   `json:"meta_threat"`
	Severity    string   `json:"severity"` // CRITICAL, HIGH, MEDIUM
	Patterns    []string `json:"patterns"` // Individual pattern IDs that contribute
	Description string   `json:"description"`
}

// CorrelationRule maps related patterns to a meta-threat.
type CorrelationRule struct {
	RequiredPatterns []string // Pattern IDs that must be present
	MetaThreat       string
	Severity         string
	Description      string
}

// correlationRules defines pattern groupings → meta-threats.
var correlationRules = []CorrelationRule{
	{
		RequiredPatterns: []string{"weak_ssl_config", "hardcoded_localhost_binding"},
		MetaThreat:       "Insecure Network Perimeter Configuration",
		Severity:         "CRITICAL",
		Description:      "Weak SSL combined with localhost-only binding indicates a misconfigured network perimeter. Attackers can intercept unencrypted traffic or bypass binding restrictions via SSRF.",
	},
	{
		RequiredPatterns: []string{"hardcoded_api_key", "no_input_validation"},
		MetaThreat:       "Authentication Bypass Chain",
		Severity:         "CRITICAL",
		Description:      "Hardcoded credentials with no input validation enables trivial authentication bypass and injection attacks.",
	},
	{
		RequiredPatterns: []string{"debug_mode_enabled", "verbose_error_messages"},
		MetaThreat:       "Information Disclosure via Debug Surface",
		Severity:         "HIGH",
		Description:      "Debug mode with verbose errors leaks internal state, stack traces, and configuration to potential attackers.",
	},
	{
		RequiredPatterns: []string{"outdated_dependency", "known_cve_usage"},
		MetaThreat:       "Supply Chain Vulnerability Cluster",
		Severity:         "CRITICAL",
		Description:      "Outdated dependencies with known CVEs indicate an exploitable supply chain attack surface.",
	},
	{
		RequiredPatterns: []string{"weak_entropy_source", "predictable_token_generation"},
		MetaThreat:       "Cryptographic Weakness Chain",
		Severity:         "HIGH",
		Description:      "Weak entropy combined with predictable tokens enables session hijacking and token forgery.",
	},
	{
		RequiredPatterns: []string{"unrestricted_file_upload", "path_traversal"},
		MetaThreat:       "Remote Code Execution via File Upload",
		Severity:         "CRITICAL",
		Description:      "Unrestricted uploads with path traversal can be chained for arbitrary file write and code execution.",
	},
	{
		RequiredPatterns: []string{"sql_injection", "privilege_escalation"},
		MetaThreat:       "Data Exfiltration Pipeline",
		Severity:         "CRITICAL",
		Description:      "SQL injection chained with privilege escalation enables full database compromise and data exfiltration.",
	},
	{
		RequiredPatterns: []string{"cors_misconfiguration", "csrf_no_token"},
		MetaThreat:       "Cross-Origin Attack Surface",
		Severity:         "HIGH",
		Description:      "CORS misconfiguration combined with missing CSRF tokens enables cross-origin request forgery and data theft.",
	},
	// v3.8: Attack Vector rules (MITRE ATT&CK mapping)
	{
		RequiredPatterns: []string{"weak_ssl_config", "open_port"},
		MetaThreat:       "Lateral Movement Vector (T1021)",
		Severity:         "CRITICAL",
		Description:      "Weak SSL on exposed ports enables network-level lateral movement via traffic interception and credential relay.",
	},
	{
		RequiredPatterns: []string{"hardcoded_api_key", "api_endpoint_exposed"},
		MetaThreat:       "Credential Stuffing Pipeline (T1110)",
		Severity:         "CRITICAL",
		Description:      "Hardcoded keys combined with exposed endpoints enable automated credential stuffing and API abuse.",
	},
	{
		RequiredPatterns: []string{"container_escape", "privilege_escalation"},
		MetaThreat:       "Container Breakout Chain (T1611)",
		Severity:         "CRITICAL",
		Description:      "Container escape combined with privilege escalation enables full host compromise from containerized workloads.",
	},
	{
		RequiredPatterns: []string{"outdated_dependency", "deserialization_flaw"},
		MetaThreat:       "Supply Chain RCE (T1195)",
		Severity:         "CRITICAL",
		Description:      "Outdated dependency with unsafe deserialization enables remote code execution via supply chain exploitation.",
	},
	{
		RequiredPatterns: []string{"weak_entropy_source", "session_fixation"},
		MetaThreat:       "Session Hijacking Pipeline (T1563)",
		Severity:         "HIGH",
		Description:      "Weak entropy with session fixation enables prediction and hijacking of authenticated sessions.",
	},
	{
		RequiredPatterns: []string{"dns_poisoning", "subdomain_takeover"},
		MetaThreat:       "C2 Persistence via DNS (T1071.004)",
		Severity:         "CRITICAL",
		Description:      "DNS poisoning combined with subdomain takeover establishes persistent command and control channel.",
	},
	{
		RequiredPatterns: []string{"ssrf", "internal_api_exposed"},
		MetaThreat:       "Internal API Chain Exploitation (T1190)",
		Severity:         "CRITICAL",
		Description:      "SSRF chained with internal API access enables pivoting from external to internal attack surface.",
	},
}

// CorrelatePatterns takes a list of detected pattern IDs and returns
// synthesized meta-threats where multiple related patterns are present.
func CorrelatePatterns(detectedPatterns []string) []CorrelationGroup {
	// Build lookup set.
	detected := make(map[string]bool)
	for _, p := range detectedPatterns {
		detected[strings.ToLower(p)] = true
	}

	var groups []CorrelationGroup
	for _, rule := range correlationRules {
		if allPresent(detected, rule.RequiredPatterns) {
			groups = append(groups, CorrelationGroup{
				MetaThreat:  rule.MetaThreat,
				Severity:    rule.Severity,
				Patterns:    rule.RequiredPatterns,
				Description: rule.Description,
			})
		}
	}

	// Sort by severity (CRITICAL first).
	sort.Slice(groups, func(i, j int) bool {
		return severityRank(groups[i].Severity) > severityRank(groups[j].Severity)
	})

	return groups
}

// CorrelationReport is the full correlation analysis result.
type CorrelationReport struct {
	DetectedPatterns int                `json:"detected_patterns"`
	MetaThreats      []CorrelationGroup `json:"meta_threats"`
	RiskLevel        string             `json:"risk_level"` // CRITICAL, HIGH, MEDIUM, LOW
}

// AnalyzeCorrelations performs full correlation analysis on detected patterns.
func AnalyzeCorrelations(detectedPatterns []string) CorrelationReport {
	groups := CorrelatePatterns(detectedPatterns)

	risk := "LOW"
	for _, g := range groups {
		if severityRank(g.Severity) > severityRank(risk) {
			risk = g.Severity
		}
	}

	return CorrelationReport{
		DetectedPatterns: len(detectedPatterns),
		MetaThreats:      groups,
		RiskLevel:        risk,
	}
}

func allPresent(set map[string]bool, required []string) bool {
	for _, r := range required {
		if !set[strings.ToLower(r)] {
			return false
		}
	}
	return true
}

func severityRank(s string) int {
	switch s {
	case "CRITICAL":
		return 4
	case "HIGH":
		return 3
	case "MEDIUM":
		return 2
	case "LOW":
		return 1
	default:
		return 0
	}
}

// FormatCorrelationReport formats the report for human consumption.
func FormatCorrelationReport(r CorrelationReport) string {
	if len(r.MetaThreats) == 0 {
		return fmt.Sprintf("No correlated threats found (%d patterns analyzed). Risk: %s", r.DetectedPatterns, r.RiskLevel)
	}

	var b strings.Builder
	fmt.Fprintf(&b, "=== Correlation Analysis ===\n")
	fmt.Fprintf(&b, "Patterns: %d | Meta-Threats: %d | Risk: %s\n\n", r.DetectedPatterns, len(r.MetaThreats), r.RiskLevel)

	for i, g := range r.MetaThreats {
		fmt.Fprintf(&b, "%d. [%s] %s\n", i+1, g.Severity, g.MetaThreat)
		fmt.Fprintf(&b, "   Patterns: %s\n", strings.Join(g.Patterns, " + "))
		fmt.Fprintf(&b, "   %s\n\n", g.Description)
	}
	return b.String()
}
