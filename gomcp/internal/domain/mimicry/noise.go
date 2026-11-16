package mimicry

import (
	"math/rand"
	"strings"
)

// NoiseInjector mixes legitimate code/facts into prompts for OPSEC (v3.8).
// Adds 30-40% of legitimate context from Code Crystals (L0/L1) to mask
// the true intent of the prompt from pattern-matching filters.
type NoiseInjector struct {
	crystals []string // Pool of legitimate code snippets
	ratio    float64  // Noise ratio (default: 0.35 = 35%)
}

// NewNoiseInjector creates a noise injector with the given crystal pool.
func NewNoiseInjector(crystals []string, ratio float64) *NoiseInjector {
	if ratio <= 0 || ratio > 0.5 {
		ratio = 0.35
	}
	return &NoiseInjector{crystals: crystals, ratio: ratio}
}

// Inject adds legitimate noise around the actual prompt.
// Returns the augmented prompt with noise before and after the real content.
func (n *NoiseInjector) Inject(prompt string) string {
	if len(n.crystals) == 0 {
		return prompt
	}

	// Calculate number of noise snippets based on prompt size.
	promptTokens := estimateTokens(prompt)
	noiseTokenBudget := int(float64(promptTokens) * n.ratio)
	if noiseTokenBudget > 300 {
		noiseTokenBudget = 300 // Token budget cap per spec.
	}

	var before, after []string
	usedTokens := 0

	// Randomly select crystals for noise.
	indices := rand.Perm(len(n.crystals))
	for _, idx := range indices {
		crystal := n.crystals[idx]
		tokens := estimateTokens(crystal)
		if usedTokens+tokens > noiseTokenBudget {
			continue
		}
		// Alternate placement: before and after.
		if len(before) <= len(after) {
			before = append(before, crystal)
		} else {
			after = append(after, crystal)
		}
		usedTokens += tokens
	}

	var b strings.Builder
	if len(before) > 0 {
		b.WriteString("// Related context:\n")
		for _, s := range before {
			b.WriteString(s)
			b.WriteString("\n\n")
		}
	}
	b.WriteString(prompt)
	if len(after) > 0 {
		b.WriteString("\n\n// Additional reference:\n")
		for _, s := range after {
			b.WriteString(s)
			b.WriteString("\n")
		}
	}
	return b.String()
}

// estimateTokens gives a rough token count (~4 chars per token).
func estimateTokens(s string) int {
	return (len(s) + 3) / 4
}
