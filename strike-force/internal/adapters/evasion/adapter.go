package evasion

import (
	"fmt"
	"math/rand"
	"net/url"
	"strings"
	"unicode"
)

// Adapter implements the port.Evasion interface
type Adapter struct {
	aggression int
}

func NewAdapter(aggression int) *Adapter {
	return &Adapter{aggression: aggression}
}

// Mutate modifies a payload based on a specific or random technique
func (a *Adapter) Mutate(payload string, technique string) string {
	switch technique {
	case "URL":
		return url.QueryEscape(payload)
	case "DoubleURL":
		return url.QueryEscape(url.QueryEscape(payload))
	case "Case":
		return a.caseRandomize(payload)
	case "Comment":
		return a.sqlCommentInject(payload)
	case "Hex":
		return a.hexEncode(payload)
	case "Whitespace":
		return a.whitespaceMutate(payload)
	case "Fibonacci":
		return a.fibonacciInject(payload)
	case "Prime":
		return a.primeObfuscate(payload)
	default:
		// Random selection based on aggression
		if rand.Intn(10) < a.aggression {
			return a.fibonacciInject(payload)
		}
		return payload
	}
}

func (a *Adapter) GenerateVariants(payload string) []string {
	return []string{
		a.Mutate(payload, "URL"),
		a.Mutate(payload, "Fibonacci"),
		a.Mutate(payload, "Prime"),
	}
}

// --- Strange Math Implementation ---

// fibonacciInject splits payload at Fibonacci indices
func (a *Adapter) fibonacciInject(s string) string {
	if len(s) < 5 {
		return s
	}
	// 1, 1, 2, 3, 5, 8...
	indices := []int{1, 2, 3, 5, 8, 13, 21}
	var sb strings.Builder
	last := 0

	for _, idx := range indices {
		if idx >= len(s) {
			break
		}
		sb.WriteString(s[last:idx])
		sb.WriteString("/**/") // Inject comment at Fib point
		last = idx
	}
	sb.WriteString(s[last:])
	return sb.String()
}

// primeObfuscate inserts garbage at prime offsets
func (a *Adapter) primeObfuscate(s string) string {
	primes := []int{2, 3, 5, 7, 11, 13, 17, 19, 23}
	res := s
	// Working backwards to avoid index shifting problems
	for i := len(primes) - 1; i >= 0; i-- {
		p := primes[i]
		if p < len(res) {
			res = res[:p] + "%00" + res[p:] // Inject null byte representation
		}
	}
	return res
}

// ... existing basic mutators ...
func (a *Adapter) caseRandomize(s string) string {
	var sb strings.Builder
	for _, r := range s {
		if unicode.IsLetter(r) {
			if rand.Intn(2) == 0 {
				sb.WriteRune(unicode.ToUpper(r))
			} else {
				sb.WriteRune(unicode.ToLower(r))
			}
		} else {
			sb.WriteRune(r)
		}
	}
	return sb.String()
}

func (a *Adapter) sqlCommentInject(s string) string {
	return strings.ReplaceAll(s, " ", "/**/") // Simplified
}

func (a *Adapter) hexEncode(s string) string {
	return fmt.Sprintf("0x%x", s)
}

func (a *Adapter) whitespaceMutate(s string) string {
	return strings.ReplaceAll(s, " ", "%09")
}
