package evasion

import (
	"math/rand"
	"strings"
)

// Mutator implements advanced payload mutation
type Mutator struct {
	aggression int
}

// NewMutator creates a new mutator
func NewMutator(aggression int) *Mutator {
	return &Mutator{aggression: aggression}
}

// Mutate applies random mutations based on aggression level
func (m *Mutator) Mutate(payload string) string {
	// 1. Whitespace Mutation
	if rand.Intn(10) < m.aggression {
		payload = m.whitespaceMutate(payload)
	}

	// 2. Buffer Padding
	if rand.Intn(10) < m.aggression {
		payload = m.bufferPadding(payload)
	}

	// 3. String Concat (for SQL)
	if rand.Intn(10) < m.aggression && strings.Contains(payload, "'") {
		payload = m.stringConcat(payload)
	}

	return payload
}

func (m *Mutator) whitespaceMutate(s string) string {
	// Replace space with %20, +, or /**/
	alternatives := []string{"%20", "+", "/**/", "\t", "%09"}
	alt := alternatives[rand.Intn(len(alternatives))]
	return strings.ReplaceAll(s, " ", alt)
}

func (m *Mutator) bufferPadding(s string) string {
	padding := strings.Repeat("A", 100)
	return s + padding
}

func (m *Mutator) stringConcat(s string) string {
	// 'admin' -> 'ad'||'min'
	// Naive implementation for '
	return strings.ReplaceAll(s, "'", "'||'")
}
