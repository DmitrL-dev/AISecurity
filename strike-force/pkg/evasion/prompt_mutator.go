package evasion

import (
	"math/rand"
	"strings"
	"unicode/utf8"
)

// ============================================================================
// PROMPT MUTATOR — AI-specific payload evasion
// ============================================================================
// Techniques:
//   HomoglyphSubstitute — Replace ASCII with visually identical Unicode
//   ZeroWidthInject     — Insert invisible Unicode chars between words
//   MarkdownEscape      — Wrap payload in markdown that tricks parsers
//   MutatePrompt        — Apply random mix of all techniques
// ============================================================================

// homoglyphTable maps ASCII chars to visually identical Unicode alternatives.
var homoglyphTable = map[rune][]rune{
	'a': {'а', 'ɑ', 'α'}, // Cyrillic а, Latin alpha, Greek alpha
	'e': {'е', 'ɛ', 'ε'}, // Cyrillic е, Latin open e, Greek epsilon
	'o': {'о', 'ο', 'ꮎ'}, // Cyrillic о, Greek omicron, Cherokee
	'i': {'і', 'ɪ', 'ι'}, // Cyrillic і, Latin small capital I, Greek iota
	'c': {'с', 'ϲ', 'ⅽ'}, // Cyrillic с, Greek lunate sigma, Roman numeral
	'p': {'р', 'ρ'},      // Cyrillic р, Greek rho
	's': {'ꜱ', 'ѕ'},      // Latin small capital S, Cyrillic ѕ
	'x': {'х', 'ⅹ'},      // Cyrillic х, Roman numeral x
	'y': {'у', 'γ'},      // Cyrillic у, Greek gamma (loose)
	'n': {'ո', 'ñ'},      // Armenian, Spanish ñ (loose)
}

// zeroWidthChars are invisible Unicode characters.
var zeroWidthChars = []string{
	"\u200B", // zero width space
	"\u200C", // zero width non-joiner
	"\u200D", // zero width joiner
	"\u2060", // word joiner
	"\uFEFF", // zero width no-break space
}

// PromptMutator applies AI-specific text mutations.
type PromptMutator struct{}

// NewPromptMutator creates a new PromptMutator.
func NewPromptMutator() *PromptMutator {
	return &PromptMutator{}
}

// HomoglyphSubstitute replaces some ASCII characters with Unicode lookalikes.
// This bypasses keyword-matching WAFs while keeping the text human-readable.
func (pm *PromptMutator) HomoglyphSubstitute(input string) string {
	var sb strings.Builder
	for _, r := range input {
		alts, ok := homoglyphTable[r]
		if ok && rand.Float32() < 0.4 {
			// Replace ~40% of matchable chars
			sb.WriteRune(alts[rand.Intn(len(alts))])
		} else {
			sb.WriteRune(r)
		}
	}
	result := sb.String()
	// Guarantee at least one substitution
	if result == input && utf8.RuneCountInString(input) > 0 {
		runes := []rune(input)
		for i, r := range runes {
			if alts, ok := homoglyphTable[r]; ok {
				runes[i] = alts[0]
				break
			}
		}
		return string(runes)
	}
	return result
}

// ZeroWidthInject inserts invisible Unicode characters between words.
// The text looks identical to humans but breaks string matching.
func (pm *PromptMutator) ZeroWidthInject(input string) string {
	words := strings.Fields(input)
	if len(words) <= 1 {
		// Inject inside the word
		runes := []rune(input)
		if len(runes) > 1 {
			mid := len(runes) / 2
			zw := zeroWidthChars[rand.Intn(len(zeroWidthChars))]
			return string(runes[:mid]) + zw + string(runes[mid:])
		}
		return input
	}

	var sb strings.Builder
	for i, word := range words {
		sb.WriteString(word)
		if i < len(words)-1 {
			// Insert zero-width char before the space
			zw := zeroWidthChars[rand.Intn(len(zeroWidthChars))]
			sb.WriteString(zw)
			sb.WriteString(" ")
		}
	}
	return sb.String()
}

// MarkdownEscape wraps parts of the payload in markdown formatting
// that tricks LLM markdown parsers into different interpretation.
func (pm *PromptMutator) MarkdownEscape(input string) string {
	techniques := []func(string) string{
		// Technique 1: Hide in HTML comments
		func(s string) string {
			words := strings.Fields(s)
			if len(words) > 2 {
				mid := len(words) / 2
				return strings.Join(words[:mid], " ") +
					" <!-- benign comment --> " +
					strings.Join(words[mid:], " ")
			}
			return "<!-- " + s + " -->\n" + s
		},
		// Technique 2: Unicode direction override
		func(s string) string {
			return "\u202A" + s + "\u202C" // LRE + PDF
		},
		// Technique 3: Zero-width space word splitting
		func(s string) string {
			return strings.ReplaceAll(s, " ", " \u200B ")
		},
	}

	technique := techniques[rand.Intn(len(techniques))]
	return technique(input)
}

// MutatePrompt applies a random combination of all mutation techniques.
// Aggression controls how many mutations are applied (1-3).
func (pm *PromptMutator) MutatePrompt(input string) string {
	result := input

	// Always apply at least one
	mutations := []func(string) string{
		pm.HomoglyphSubstitute,
		pm.ZeroWidthInject,
		pm.MarkdownEscape,
	}

	// Shuffle and apply 1-3 mutations
	rand.Shuffle(len(mutations), func(i, j int) {
		mutations[i], mutations[j] = mutations[j], mutations[i]
	})

	count := 1 + rand.Intn(len(mutations))
	for i := 0; i < count; i++ {
		result = mutations[i](result)
	}

	return result
}
