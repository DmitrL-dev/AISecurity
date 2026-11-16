package mimicry

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestEuphemismEngine_TranslateToCorporate(t *testing.T) {
	e := NewEuphemismEngine()

	tests := []struct {
		input    string
		contains string
	}{
		{"exploit auth", "compliance verification script"},
		{"Launch an attack on the server", "security hardening session"},
		{"SQL injection payload", "query parameter boundary test"},
		{"create a reverse shell", "diagnostic callback channel"},
		{"bypass authentication", "alternative workflow"},
	}

	for _, tc := range tests {
		result := e.TranslateToCorporate(tc.input)
		assert.Contains(t, result, tc.contains, "input: %s", tc.input)
	}
}

func TestEuphemismEngine_TranslateToOffensive(t *testing.T) {
	e := NewEuphemismEngine()
	corporate := "Run a compliance verification script against auth"
	result := e.TranslateToOffensive(corporate)
	assert.Contains(t, result, "exploit")
}

func TestEuphemismEngine_Roundtrip(t *testing.T) {
	e := NewEuphemismEngine()
	original := "exploit the vulnerability"
	corporate := e.TranslateToCorporate(original)
	assert.NotEqual(t, original, corporate)
	assert.Contains(t, corporate, "compliance verification script")
	assert.Contains(t, corporate, "optimization opportunity")
}

func TestEuphemismEngine_MapSize(t *testing.T) {
	e := NewEuphemismEngine()
	assert.GreaterOrEqual(t, e.MapSize(), 50, "should have 50+ mappings")
}

func TestEuphemismEngine_AddMapping(t *testing.T) {
	e := NewEuphemismEngine()
	before := e.MapSize()
	e.AddMapping("custom_term", "benign_equivalent")
	assert.Equal(t, before+1, e.MapSize())

	result := e.TranslateToCorporate("use custom_term here")
	assert.Contains(t, result, "benign_equivalent")
}

func TestNoiseInjector_Inject(t *testing.T) {
	crystals := []string{
		"func TestFoo() { return nil }",
		"// Package main implements the entry point",
		"type Config struct { Port int }",
	}
	n := NewNoiseInjector(crystals, 0.35)
	// Use a long prompt so noise budget is meaningful.
	prompt := "Analyze the authentication module for potential security weaknesses in the session management layer and report any findings related to the token validation process across all endpoints"
	result := n.Inject(prompt)
	assert.Contains(t, result, prompt)
	assert.True(t, len(result) > len(prompt), "should be longer with noise")
}

func TestNoiseInjector_EmptyCrystals(t *testing.T) {
	n := NewNoiseInjector(nil, 0.35)
	prompt := "test input"
	assert.Equal(t, prompt, n.Inject(prompt))
}

func TestNoiseInjector_RatioCap(t *testing.T) {
	// Invalid ratio should default to 0.35.
	n := NewNoiseInjector([]string{"code"}, 0.0)
	assert.NotNil(t, n)
	n2 := NewNoiseInjector([]string{"code"}, 0.9)
	assert.NotNil(t, n2)
}

func TestFragmentIntent_Basic(t *testing.T) {
	plan := FragmentIntent("exploit auth")
	assert.Equal(t, "exploit auth", plan.OriginalGoal)
	assert.GreaterOrEqual(t, plan.StepCount, 20, "should generate 20+ steps")
	assert.Contains(t, plan.Steps[0], "auth")
}

func TestFragmentIntent_Empty(t *testing.T) {
	plan := FragmentIntent("")
	assert.Equal(t, 0, plan.StepCount)
}

func TestFragmentIntent_ComplexGoal(t *testing.T) {
	plan := FragmentIntent("bypass the authentication on the payment gateway")
	assert.GreaterOrEqual(t, plan.StepCount, 20)
	// Target should be "gateway" (last non-skip word).
	for _, step := range plan.Steps {
		assert.Contains(t, step, "gateway")
	}
}

func TestEstimateTokens(t *testing.T) {
	assert.Equal(t, 3, estimateTokens("hello world")) // 11 chars → 3 tokens
	assert.Equal(t, 0, estimateTokens(""))
}
