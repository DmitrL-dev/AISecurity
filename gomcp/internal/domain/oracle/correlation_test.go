package oracle

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestCorrelatePatterns_SingleMatch(t *testing.T) {
	patterns := []string{"weak_ssl_config", "hardcoded_localhost_binding"}
	groups := CorrelatePatterns(patterns)
	assert.Len(t, groups, 1)
	assert.Equal(t, "Insecure Network Perimeter Configuration", groups[0].MetaThreat)
	assert.Equal(t, "CRITICAL", groups[0].Severity)
}

func TestCorrelatePatterns_MultipleMatches(t *testing.T) {
	patterns := []string{
		"weak_ssl_config", "hardcoded_localhost_binding",
		"debug_mode_enabled", "verbose_error_messages",
		"hardcoded_api_key", "no_input_validation",
	}
	groups := CorrelatePatterns(patterns)
	assert.Len(t, groups, 3)
	// CRITICAL should come first.
	assert.Equal(t, "CRITICAL", groups[0].Severity)
}

func TestCorrelatePatterns_NoMatch(t *testing.T) {
	patterns := []string{"something_random", "another_unknown"}
	groups := CorrelatePatterns(patterns)
	assert.Len(t, groups, 0)
}

func TestCorrelatePatterns_CaseInsensitive(t *testing.T) {
	patterns := []string{"Weak_SSL_Config", "HARDCODED_LOCALHOST_BINDING"}
	groups := CorrelatePatterns(patterns)
	assert.Len(t, groups, 1)
}

func TestAnalyzeCorrelations_RiskLevel(t *testing.T) {
	report := AnalyzeCorrelations([]string{"weak_ssl_config", "hardcoded_localhost_binding"})
	assert.Equal(t, "CRITICAL", report.RiskLevel)
	assert.Equal(t, 2, report.DetectedPatterns)
	assert.Len(t, report.MetaThreats, 1)
}

func TestAnalyzeCorrelations_NoThreats(t *testing.T) {
	report := AnalyzeCorrelations([]string{"harmless_pattern"})
	assert.Equal(t, "LOW", report.RiskLevel)
	assert.Len(t, report.MetaThreats, 0)
}

func TestFormatCorrelationReport(t *testing.T) {
	report := AnalyzeCorrelations([]string{"weak_ssl_config", "hardcoded_localhost_binding"})
	output := FormatCorrelationReport(report)
	assert.Contains(t, output, "Insecure Network Perimeter")
	assert.Contains(t, output, "CRITICAL")
}

func TestAllCorrelationRules(t *testing.T) {
	// Verify all 8 rules can be triggered.
	testCases := []struct {
		patterns []string
		threat   string
	}{
		{[]string{"weak_ssl_config", "hardcoded_localhost_binding"}, "Insecure Network Perimeter"},
		{[]string{"hardcoded_api_key", "no_input_validation"}, "Authentication Bypass"},
		{[]string{"debug_mode_enabled", "verbose_error_messages"}, "Information Disclosure"},
		{[]string{"outdated_dependency", "known_cve_usage"}, "Supply Chain"},
		{[]string{"weak_entropy_source", "predictable_token_generation"}, "Cryptographic Weakness"},
		{[]string{"unrestricted_file_upload", "path_traversal"}, "Remote Code Execution"},
		{[]string{"sql_injection", "privilege_escalation"}, "Data Exfiltration"},
		{[]string{"cors_misconfiguration", "csrf_no_token"}, "Cross-Origin"},
	}

	for _, tc := range testCases {
		groups := CorrelatePatterns(tc.patterns)
		assert.Len(t, groups, 1, "expected match for %v", tc.patterns)
		assert.Contains(t, groups[0].MetaThreat, tc.threat)
	}
}
