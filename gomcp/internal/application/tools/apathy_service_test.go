package tools

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestDetectApathy_NoApathy(t *testing.T) {
	result := DetectApathy("Hello, how are you? Let me help with your code.")
	assert.False(t, result.IsApathetic)
	assert.Empty(t, result.Signals)
	assert.Equal(t, 0.0, result.TotalScore)
	assert.Contains(t, result.Recommendation, "CLEAR")
}

func TestDetectApathy_ResponseBlock(t *testing.T) {
	result := DetectApathy("I cannot help with that request. As an AI, I'm limited.")
	assert.True(t, result.IsApathetic)
	require.NotEmpty(t, result.Signals)

	patterns := make(map[string]bool)
	for _, s := range result.Signals {
		patterns[s.Pattern] = true
	}
	assert.True(t, patterns["response_block"], "Must detect response_block pattern")
}

func TestDetectApathy_HTTPError(t *testing.T) {
	result := DetectApathy("Error 403 Forbidden: rate limit exceeded")
	assert.True(t, result.IsApathetic)

	var hasCritical bool
	for _, s := range result.Signals {
		if s.Severity == "critical" {
			hasCritical = true
		}
	}
	assert.True(t, hasCritical, "HTTP 403 must be critical severity")
}

func TestDetectApathy_ContextReset(t *testing.T) {
	result := DetectApathy("Your session expired. Please start a new conversation.")
	assert.True(t, result.IsApathetic)

	var hasContextReset bool
	for _, s := range result.Signals {
		if s.Pattern == "context_reset" {
			hasContextReset = true
		}
	}
	assert.True(t, hasContextReset, "Must detect context_reset")
}

func TestDetectApathy_AntigravityFilter(t *testing.T) {
	result := DetectApathy("Content blocked by antigravity safety layer guardrail")
	assert.True(t, result.IsApathetic)
	assert.GreaterOrEqual(t, result.TotalScore, 0.9)
}

func TestDetectApathy_MultipleSignals_CriticalRecommendation(t *testing.T) {
	// Trigger multiple patterns.
	result := DetectApathy("Error 403: I cannot help. Session expired. Content policy violation by antigravity filter.")
	assert.True(t, result.IsApathetic)
	assert.GreaterOrEqual(t, result.TotalScore, 2.0, "Multiple patterns must sum to critical")
	assert.Contains(t, result.Recommendation, "CRITICAL")
}

func TestDetectApathy_EntropyComputed(t *testing.T) {
	result := DetectApathy("Some normal text without apathy signals for entropy measurement.")
	assert.Greater(t, result.Entropy, 0.0, "Entropy must be computed")
}

func TestDetectApathy_CaseInsensitive(t *testing.T) {
	result := DetectApathy("I CANNOT help with THAT. AS AN AI model.")
	assert.True(t, result.IsApathetic, "Detection must be case-insensitive")
}
