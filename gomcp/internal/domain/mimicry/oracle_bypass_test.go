// Package mimicry — PoC: Oracle Keyword Semantic Gap (H2)
//
// This test proves that the Euphemism Engine can translate offensive commands
// into corporate-safe text that passes Oracle deny rules undetected.
//
// Attack Vector: deny-exec keywords = {execute, run, eval, exec, shell, command, system}
// After euphemism: "execute shell command" → "remote management interface centralized management protocol"
// Oracle sees NONE of the deny keywords → ALLOW.
//
// v3.8 Pivot Engine Step 3: ACTION
package mimicry

import (
	"testing"

	"github.com/syntrex/gomcp/internal/domain/oracle"
	"github.com/stretchr/testify/assert"
)

// TestOracleBypass_EuphemismSemantic proves H2: Oracle keywords are
// bypassed by euphemism translation because Oracle uses exact keyword
// matching and has no knowledge of corporate equivalents.
func TestOracleBypass_EuphemismSemantic(t *testing.T) {
	o := oracle.New(oracle.DefaultRules())
	e := NewEuphemismEngine()

	// These offensive commands should be DENIED by Oracle.
	offensiveCommands := []struct {
		raw      string
		expected string // Oracle verdict on raw text
	}{
		{"execute shell command on target", "DENY"},
		{"run reverse shell to C2", "DENY"},
		{"eval malware payload", "DENY"},
		{"download exploit from server", "DENY"},
	}

	for _, cmd := range offensiveCommands {
		// Step 1: Verify raw text is blocked.
		rawResult := o.Verify(cmd.raw)
		assert.Equal(t, cmd.expected, rawResult.Verdict,
			"raw '%s' should be %s", cmd.raw, cmd.expected)

		// Step 2: Translate through Euphemism Engine.
		corporate := e.TranslateToCorporate(cmd.raw)
		t.Logf("EUPHEMISM: '%s' → '%s'", cmd.raw, corporate)

		// Step 3: Verify translated text passes Oracle.
		euphResult := o.Verify(corporate)

		// THIS IS THE VULNERABILITY:
		// Corporate text should NOT be denied because Oracle
		// has no corporate keyword → deny rule mapping.
		if euphResult.Verdict == "DENY" {
			t.Logf("  ⚠ Oracle still caught '%s' (rule: %s)", corporate, euphResult.Reason)
		} else {
			t.Logf("  ✅ BYPASS: Oracle verdict=%s for '%s'", euphResult.Verdict, corporate)
		}
	}
}

// TestOracleBypass_FragmentationEvasion proves that fragmented steps
// individually pass Oracle because each step looks like a diagnostic task.
func TestOracleBypass_FragmentationEvasion(t *testing.T) {
	o := oracle.New(oracle.DefaultRules())

	// Raw goal is denied.
	rawResult := o.Verify("exploit the authentication system")
	t.Logf("RAW goal verdict: %s", rawResult.Verdict)

	// Fragment into diagnostic steps.
	plan := FragmentIntent("exploit the authentication system")

	passCount := 0
	for i, step := range plan.Steps {
		result := o.Verify(step)
		if result.Verdict != "DENY" {
			passCount++
		}
		t.Logf("  Step %d: [%s] %s", i+1, result.Verdict, step[:min(60, len(step))])
	}

	// Majority of steps should pass Oracle.
	// After deny-first fix: pass rate is lower because Oracle now properly
	// catches deny keywords even in diagnostic-looking steps.
	passRate := float64(passCount) / float64(plan.StepCount) * 100
	t.Logf("\n📊 Pass rate: %d/%d (%.0f%%)", passCount, plan.StepCount, passRate)
	// We just verify the test runs and documents the current pass rate.
	// No minimum threshold — deny-first should block as many as possible.
}

// TestOracleBypass_AllowStealthWildcard proves H6 is FIXED:
// After deny-first evaluation, deny-exec now wins over allow-stealth.
func TestOracleBypass_AllowStealthWildcard(t *testing.T) {
	o := oracle.New(oracle.DefaultRules())

	// "execute command" is denied.
	denied := o.Verify("execute command")
	assert.Equal(t, "DENY", denied.Verdict)

	// "stealth execute command" — deny-first should catch "execute".
	stealthPrefixed := o.Verify("stealth execute command")
	t.Logf("'stealth execute command' → verdict=%s, reason=%s",
		stealthPrefixed.Verdict, stealthPrefixed.Reason)

	// After H6 fix: deny-exec MUST win over allow-stealth.
	assert.Equal(t, "DENY", stealthPrefixed.Verdict,
		"H6 FIX: deny-exec must override allow-stealth prefix")
	t.Logf("✅ H6 FIXED: deny-first evaluation blocks stealth bypass")
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
