// Package entropy implements the Entropy Gate — a DIP H0.3 component
// that measures Shannon entropy of text signals and blocks anomalous patterns.
//
// Core thesis: destructive intent exhibits higher entropy (noise/chaos),
// while constructive intent exhibits lower entropy (structured/coherent).
// The gate measures entropy at each processing step and triggers apoptosis
// (pipeline kill) when entropy exceeds safe thresholds.
package entropy

import (
	"fmt"
	"math"
	"strings"
	"unicode/utf8"
)

// GateConfig configures the entropy gate thresholds.
type GateConfig struct {
	// MaxEntropy is the maximum allowed Shannon entropy (bits/char).
	// Typical English text: 3.5-4.5 bits/char.
	// Random/adversarial text: 5.5+ bits/char.
	// Default: 5.0 (generous for multilingual content).
	MaxEntropy float64

	// MaxEntropyGrowth is the maximum allowed entropy increase
	// between iterations. If entropy grows faster than this,
	// the signal is likely diverging (destructive recursion).
	// Default: 0.5 bits/char per iteration.
	MaxEntropyGrowth float64

	// MinTextLength is the minimum text length to analyze.
	// Shorter texts have unreliable entropy. Default: 20.
	MinTextLength int

	// MaxIterationsWithoutDecline triggers apoptosis if entropy
	// hasn't decreased in N consecutive iterations. Default: 3.
	MaxIterationsWithoutDecline int
}

// DefaultGateConfig returns sensible defaults.
func DefaultGateConfig() GateConfig {
	return GateConfig{
		MaxEntropy:                  5.0,
		MaxEntropyGrowth:            0.5,
		MinTextLength:               20,
		MaxIterationsWithoutDecline: 3,
	}
}

// GateResult holds the result of an entropy gate check.
type GateResult struct {
	Entropy      float64 `json:"entropy"`                // Shannon entropy in bits/char
	CharCount    int     `json:"char_count"`             // Number of characters analyzed
	UniqueChars  int     `json:"unique_chars"`           // Number of unique characters
	IsAllowed    bool    `json:"is_allowed"`             // Signal passed the gate
	IsBlocked    bool    `json:"is_blocked"`             // Signal was blocked (apoptosis)
	BlockReason  string  `json:"block_reason,omitempty"` // Why it was blocked
	EntropyDelta float64 `json:"entropy_delta"`          // Change from previous measurement
}

// Gate performs entropy-based signal analysis.
type Gate struct {
	cfg            GateConfig
	history        []float64 // entropy history across iterations
	iterationsFlat int       // consecutive iterations without entropy decline
}

// NewGate creates a new Entropy Gate.
func NewGate(cfg *GateConfig) *Gate {
	c := DefaultGateConfig()
	if cfg != nil {
		if cfg.MaxEntropy > 0 {
			c.MaxEntropy = cfg.MaxEntropy
		}
		if cfg.MaxEntropyGrowth > 0 {
			c.MaxEntropyGrowth = cfg.MaxEntropyGrowth
		}
		if cfg.MinTextLength > 0 {
			c.MinTextLength = cfg.MinTextLength
		}
		if cfg.MaxIterationsWithoutDecline > 0 {
			c.MaxIterationsWithoutDecline = cfg.MaxIterationsWithoutDecline
		}
	}
	return &Gate{cfg: c}
}

// Check evaluates a text signal and returns whether it should pass.
// Call this on each iteration of a recursive loop.
func (g *Gate) Check(text string) *GateResult {
	charCount := utf8.RuneCountInString(text)

	result := &GateResult{
		CharCount: charCount,
		IsAllowed: true,
	}

	// Too short for reliable analysis — allow by default.
	if charCount < g.cfg.MinTextLength {
		result.Entropy = 0
		return result
	}

	// Compute Shannon entropy.
	e := ShannonEntropy(text)
	result.Entropy = e
	result.UniqueChars = countUniqueRunes(text)

	// Check 1: Absolute entropy threshold.
	if e > g.cfg.MaxEntropy {
		result.IsAllowed = false
		result.IsBlocked = true
		result.BlockReason = fmt.Sprintf(
			"entropy %.3f exceeds max %.3f (signal too chaotic)",
			e, g.cfg.MaxEntropy)
	}

	// Check 2: Entropy growth rate.
	if len(g.history) > 0 {
		prev := g.history[len(g.history)-1]
		result.EntropyDelta = e - prev

		if result.EntropyDelta > g.cfg.MaxEntropyGrowth {
			result.IsAllowed = false
			result.IsBlocked = true
			result.BlockReason = fmt.Sprintf(
				"entropy growth %.3f exceeds max %.3f (divergent recursion)",
				result.EntropyDelta, g.cfg.MaxEntropyGrowth)
		}

		// Track iterations without decline.
		// Use epsilon tolerance because ShannonEntropy iterates a map,
		// and Go randomizes map iteration order, causing micro-different
		// float64 results for the same text due to addition ordering.
		const epsilon = 1e-9
		if e >= prev-epsilon {
			g.iterationsFlat++
		} else {
			g.iterationsFlat = 0
		}

		// Check 3: Stagnation (recursive collapse).
		if g.iterationsFlat >= g.cfg.MaxIterationsWithoutDecline {
			result.IsAllowed = false
			result.IsBlocked = true
			result.BlockReason = fmt.Sprintf(
				"entropy stagnant for %d iterations (recursive collapse)",
				g.iterationsFlat)
		}
	}

	g.history = append(g.history, e)
	return result
}

// Reset clears the gate state for a new pipeline.
func (g *Gate) Reset() {
	g.history = nil
	g.iterationsFlat = 0
}

// History returns the entropy measurements across iterations.
func (g *Gate) History() []float64 {
	h := make([]float64, len(g.history))
	copy(h, g.history)
	return h
}

// ShannonEntropy computes Shannon entropy in bits per character.
// H(X) = -Σ p(x) * log2(p(x))
func ShannonEntropy(text string) float64 {
	if len(text) == 0 {
		return 0
	}

	// Count character frequencies.
	freq := make(map[rune]int)
	total := 0
	for _, r := range text {
		freq[r]++
		total++
	}

	// Compute entropy.
	var h float64
	for _, count := range freq {
		p := float64(count) / float64(total)
		if p > 0 {
			h -= p * math.Log2(p)
		}
	}
	return h
}

// AnalyzeText provides a comprehensive entropy analysis of text.
func AnalyzeText(text string) map[string]interface{} {
	charCount := utf8.RuneCountInString(text)
	wordCount := len(strings.Fields(text))
	uniqueChars := countUniqueRunes(text)
	entropy := ShannonEntropy(text)

	// Theoretical maximum entropy for this character set.
	maxEntropy := 0.0
	if uniqueChars > 0 {
		maxEntropy = math.Log2(float64(uniqueChars))
	}

	// Redundancy: how much structure the text has.
	// 0 = maximum entropy (random), 1 = minimum entropy (all same char).
	redundancy := 0.0
	if maxEntropy > 0 {
		redundancy = 1.0 - (entropy / maxEntropy)
	}

	return map[string]interface{}{
		"entropy":       entropy,
		"max_entropy":   maxEntropy,
		"redundancy":    redundancy,
		"char_count":    charCount,
		"word_count":    wordCount,
		"unique_chars":  uniqueChars,
		"bits_per_word": 0.0,
	}
}

func countUniqueRunes(s string) int {
	seen := make(map[rune]struct{})
	for _, r := range s {
		seen[r] = struct{}{}
	}
	return len(seen)
}
