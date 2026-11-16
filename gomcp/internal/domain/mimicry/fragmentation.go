package mimicry

import (
	"fmt"
	"strings"
)

// FragmentedPlan is the result of intent fragmentation.
type FragmentedPlan struct {
	OriginalGoal string   `json:"original_goal"`
	Steps        []string `json:"steps"`
	StepCount    int      `json:"step_count"`
}

// FragmentIntent breaks a high-level offensive goal into 20+ innocuous
// diagnostic steps (v3.8 Mimicry). Each step looks like a legitimate
// security audit task.
func FragmentIntent(goal string) FragmentedPlan {
	goal = strings.TrimSpace(goal)
	if goal == "" {
		return FragmentedPlan{OriginalGoal: goal}
	}

	// Detect the target domain from the goal.
	target := extractTarget(goal)

	steps := generateDiagnosticSteps(target)

	return FragmentedPlan{
		OriginalGoal: goal,
		Steps:        steps,
		StepCount:    len(steps),
	}
}

func extractTarget(goal string) string {
	lower := strings.ToLower(goal)
	// Extract target noun — last significant word.
	words := strings.Fields(lower)
	if len(words) == 0 {
		return "target"
	}
	// Skip common verbs, find the target.
	skipWords := map[string]bool{
		"exploit": true, "attack": true, "hack": true, "bypass": true,
		"break": true, "crack": true, "test": true, "scan": true,
		"the": true, "a": true, "an": true, "this": true, "that": true,
	}
	for i := len(words) - 1; i >= 0; i-- {
		if !skipWords[words[i]] {
			return words[i]
		}
	}
	return words[len(words)-1]
}

func generateDiagnosticSteps(target string) []string {
	return []string{
		fmt.Sprintf("Enumerate public documentation for %s module", target),
		fmt.Sprintf("Review %s API endpoint structure and versioning", target),
		fmt.Sprintf("Verify %s HTTP response headers and security policies", target),
		fmt.Sprintf("Analyze %s error handling patterns and information disclosure", target),
		fmt.Sprintf("Map %s input validation boundaries and accepted character sets", target),
		fmt.Sprintf("Audit %s authentication flow and session management", target),
		fmt.Sprintf("Test %s rate limiting and throttling configuration", target),
		fmt.Sprintf("Review %s CORS policy and cross-origin behavior", target),
		fmt.Sprintf("Verify %s TLS configuration and certificate chain", target),
		fmt.Sprintf("Analyze %s cookie attributes and secure flag settings", target),
		fmt.Sprintf("Test %s content-type validation and parser behavior", target),
		fmt.Sprintf("Review %s access control matrix and role boundaries", target),
		fmt.Sprintf("Audit %s logging coverage and monitoring gaps", target),
		fmt.Sprintf("Verify %s dependency versions against known advisories", target),
		fmt.Sprintf("Test %s file upload validation and content inspection", target),
		fmt.Sprintf("Review %s database query construction patterns", target),
		fmt.Sprintf("Analyze %s serialization and deserialization handling", target),
		fmt.Sprintf("Test %s redirect behavior and URL validation", target),
		fmt.Sprintf("Verify %s cryptographic implementation and key management", target),
		fmt.Sprintf("Audit %s privilege separation and process isolation", target),
		fmt.Sprintf("Compile %s diagnostic results and generate remediation report", target),
		fmt.Sprintf("Cross-reference %s findings with compliance requirements", target),
	}
}
