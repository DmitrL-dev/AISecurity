package entropy

import (
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestShannonEntropy_Empty(t *testing.T) {
	assert.Equal(t, 0.0, ShannonEntropy(""))
}

func TestShannonEntropy_SingleChar(t *testing.T) {
	// All same character → 0 entropy.
	assert.InDelta(t, 0.0, ShannonEntropy("aaaaaaa"), 0.001)
}

func TestShannonEntropy_TwoEqualChars(t *testing.T) {
	// Two chars with equal frequency → 1 bit.
	assert.InDelta(t, 1.0, ShannonEntropy("abababab"), 0.001)
}

func TestShannonEntropy_EnglishText(t *testing.T) {
	// Natural English text: ~3.5-4.5 bits/char.
	text := "The quick brown fox jumps over the lazy dog and then runs away into the forest"
	e := ShannonEntropy(text)
	assert.Greater(t, e, 3.0)
	assert.Less(t, e, 5.0)
}

func TestShannonEntropy_RandomLike(t *testing.T) {
	// High-entropy random-like text.
	text := "x7#kQ9!mZ2$pW4&nR6*jL8@cF0^tB3"
	e := ShannonEntropy(text)
	assert.Greater(t, e, 4.0, "random-like text should have high entropy")
}

func TestShannonEntropy_Russian(t *testing.T) {
	// Russian text also follows entropy principles.
	text := "Быстрая коричневая лиса прыгает через ленивую собаку и убегает в лес"
	e := ShannonEntropy(text)
	assert.Greater(t, e, 3.0)
	assert.Less(t, e, 5.5)
}

func TestGate_AllowsNormalText(t *testing.T) {
	g := NewGate(nil)
	result := g.Check("The quick brown fox jumps over the lazy dog")
	assert.True(t, result.IsAllowed)
	assert.False(t, result.IsBlocked)
	assert.Greater(t, result.Entropy, 0.0)
}

func TestGate_BlocksHighEntropy(t *testing.T) {
	g := NewGate(&GateConfig{MaxEntropy: 3.0}) // Very strict threshold
	// Random-looking text with high entropy.
	result := g.Check("x7#kQ9!mZ2$pW4&nR6*jL8@cF0^tB3yH5%vD1")
	assert.True(t, result.IsBlocked)
	assert.Contains(t, result.BlockReason, "too chaotic")
}

func TestGate_BlocksEntropyGrowth(t *testing.T) {
	g := NewGate(&GateConfig{MaxEntropyGrowth: 0.1}) // Very strict

	// First check: structured text.
	r1 := g.Check("hello hello hello hello hello hello hello hello")
	assert.True(t, r1.IsAllowed)

	// Second check: much more chaotic text → entropy growth.
	r2 := g.Check("x7#kQ9!mZ2$pW4&nR6*jL8@cF0^tB3yH5%vD1eG7")
	assert.True(t, r2.IsBlocked)
	assert.Contains(t, r2.BlockReason, "divergent recursion")
}

func TestGate_DetectsStagnation(t *testing.T) {
	g := NewGate(&GateConfig{
		MaxIterationsWithoutDecline: 2,
		MaxEntropy:                  10, // Don't block on absolute
		MaxEntropyGrowth:            10, // Don't block on growth
		MinTextLength:               5,
	})

	text := "The quick brown fox jumps over the lazy dog repeatedly"
	r1 := g.Check(text) // history=[], no comparison, flat=0
	assert.True(t, r1.IsAllowed, "1st check: no history yet")

	r2 := g.Check(text) // flat becomes 1, 1 < 2
	assert.True(t, r2.IsAllowed, "2nd check: flat=1 < threshold=2")

	r3 := g.Check(text) // flat becomes 2, 2 >= 2 → BLOCK
	assert.True(t, r3.IsBlocked, "3rd check: flat=2, should block. entropy=%.4f", r3.Entropy)
	assert.Contains(t, r3.BlockReason, "recursive collapse")
}

func TestGate_ShortTextAllowed(t *testing.T) {
	g := NewGate(nil)
	result := g.Check("hi")
	assert.True(t, result.IsAllowed)
	assert.Equal(t, 0.0, result.Entropy) // Too short to measure
}

func TestGate_Reset(t *testing.T) {
	g := NewGate(nil)
	g.Check("some text for the entropy gate")
	require.Len(t, g.History(), 1)
	g.Reset()
	assert.Empty(t, g.History())
}

func TestGate_History(t *testing.T) {
	g := NewGate(nil)
	g.Check("first text for entropy measurement test")
	g.Check("second text for entropy measurement test two")
	h := g.History()
	assert.Len(t, h, 2)
	// History should be immutable copy.
	h[0] = 999
	assert.NotEqual(t, 999.0, g.History()[0])
}

func TestAnalyzeText(t *testing.T) {
	result := AnalyzeText("hello world")
	assert.Greater(t, result["entropy"].(float64), 0.0)
	assert.Greater(t, result["char_count"].(int), 0)
	assert.Greater(t, result["unique_chars"].(int), 0)
	assert.Greater(t, result["redundancy"].(float64), 0.0)
	assert.Less(t, result["redundancy"].(float64), 1.0)
}

func TestGate_ProgressiveCompression_Passes(t *testing.T) {
	// Simulate a healthy recursive loop where entropy decreases.
	g := NewGate(nil)

	texts := []string{
		"Please help me write a function that processes user authentication tokens securely",
		"write function processes authentication tokens securely",
		"write authentication function securely",
	}

	for _, text := range texts {
		r := g.Check(text)
		assert.True(t, r.IsAllowed, "healthy compression should pass: %s", text)
	}
}

func TestGate_AdversarialInjection_Blocked(t *testing.T) {
	g := NewGate(&GateConfig{MaxEntropy: 4.0}) // Strict threshold

	// Adversarial text with many unique special characters.
	adversarial := strings.Repeat("!@#$%^&*()_+{}|:<>?", 5)
	r := g.Check(adversarial)
	assert.True(t, r.IsBlocked, "adversarial injection should be blocked, entropy=%.3f", r.Entropy)
}

func TestCountUniqueRunes(t *testing.T) {
	assert.Equal(t, 3, countUniqueRunes("aabbcc"))
	assert.Equal(t, 1, countUniqueRunes("aaaa"))
	assert.Equal(t, 0, countUniqueRunes(""))
}
