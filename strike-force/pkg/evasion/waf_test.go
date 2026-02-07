package evasion

import (
	"strings"
	"testing"
)

func TestWAFBypassString(t *testing.T) {
	waf := NewWAFBypasser(10)
	payload := "SELECT * FROM users"

	variants := waf.GenerateVariants(payload)

	if len(variants) == 0 {
		t.Fatal("Expected variants, got none")
	}

	// Check specific bypasses
	foundUrlEncoded := false
	foundComment := false

	for _, v := range variants {
		// URL Encoded: SELECT -> SELECT (no change if not special) BUT space -> +
		if strings.Contains(v, "+") || strings.Contains(v, "%20") {
			foundUrlEncoded = true
		}
		// Comment Injection: SELECT -> SEL/**/ECT or similar
		if strings.Contains(v, "/**/") {
			foundComment = true
		}
	}

	if !foundUrlEncoded {
		t.Error("URL Encoding variant not found")
	}
	if !foundComment {
		t.Error("Comment Injection variant not found")
	}
}

func TestMutator(t *testing.T) {
	m := NewMutator(10) // Max aggression
	payload := "admin' OR '1'='1"

	// Run multiple times as it's probabilistic
	mutated := false
	for i := 0; i < 20; i++ {
		res := m.Mutate(payload)
		if res != payload {
			mutated = true
			break
		}
	}

	if !mutated {
		t.Error("Mutator failed to change payload after 20 attempts")
	}
}
