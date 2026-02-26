// Package context defines domain entities for the Proactive Context Engine.
// The engine automatically injects relevant memory facts into every tool response,
// ensuring the LLM always has context without explicitly requesting it.
package context

import (
	"errors"
	"fmt"
	"strings"
	"time"
	"unicode"

	"github.com/sentinel-community/gomcp/internal/domain/memory"
)

// Default configuration values.
const (
	DefaultTokenBudget     = 300  // tokens reserved for context injection
	DefaultMaxFacts        = 10   // max facts per context frame
	DefaultRecencyWeight   = 0.25 // weight for time-based recency scoring
	DefaultFrequencyWeight = 0.15 // weight for access frequency scoring
	DefaultLevelWeight     = 0.30 // weight for hierarchy level scoring (L0 > L3)
	DefaultKeywordWeight   = 0.30 // weight for keyword match scoring
	DefaultDecayHalfLife   = 72.0 // hours until unused fact score halves
)

// FactProvider abstracts fact retrieval for the context engine.
// This decouples the engine from specific storage implementations.
type FactProvider interface {
	// GetRelevantFacts returns facts potentially relevant to the given tool arguments.
	GetRelevantFacts(args map[string]interface{}) ([]*memory.Fact, error)

	// GetL0Facts returns all L0 (project-level) facts — always included in context.
	GetL0Facts() ([]*memory.Fact, error)

	// RecordAccess increments the access counter for a fact.
	RecordAccess(factID string)
}

// ScoredFact pairs a Fact with its computed relevance score and access metadata.
type ScoredFact struct {
	Fact         *memory.Fact `json:"fact"`
	Score        float64      `json:"score"`
	AccessCount  int          `json:"access_count"`
	LastAccessed time.Time    `json:"last_accessed,omitempty"`
}

// NewScoredFact creates a ScoredFact with the given score.
func NewScoredFact(fact *memory.Fact, score float64) *ScoredFact {
	return &ScoredFact{
		Fact:  fact,
		Score: score,
	}
}

// EstimateTokens returns an approximate token count for this fact's content.
// Uses the ~4 chars per token heuristic plus overhead for formatting.
func (sf *ScoredFact) EstimateTokens() int {
	return EstimateTokenCount(sf.Fact.Content)
}

// RecordAccess increments the access counter and updates the timestamp.
func (sf *ScoredFact) RecordAccess() {
	sf.AccessCount++
	sf.LastAccessed = time.Now()
}

// ContextFrame holds the selected facts for injection into a single tool response.
type ContextFrame struct {
	ToolName    string        `json:"tool_name"`
	TokenBudget int           `json:"token_budget"`
	Facts       []*ScoredFact `json:"facts"`
	TokensUsed  int           `json:"tokens_used"`
	CreatedAt   time.Time     `json:"created_at"`
}

// NewContextFrame creates an empty context frame for the given tool.
func NewContextFrame(toolName string, tokenBudget int) *ContextFrame {
	return &ContextFrame{
		ToolName:    toolName,
		TokenBudget: tokenBudget,
		Facts:       make([]*ScoredFact, 0),
		TokensUsed:  0,
		CreatedAt:   time.Now(),
	}
}

// AddFact attempts to add a scored fact to the frame within the token budget.
// Returns true if the fact was added, false if it would exceed the budget.
func (cf *ContextFrame) AddFact(sf *ScoredFact) bool {
	tokens := sf.EstimateTokens()
	if cf.TokensUsed+tokens > cf.TokenBudget {
		return false
	}
	cf.Facts = append(cf.Facts, sf)
	cf.TokensUsed += tokens
	return true
}

// RemainingTokens returns how many tokens are left in the budget.
func (cf *ContextFrame) RemainingTokens() int {
	remaining := cf.TokenBudget - cf.TokensUsed
	if remaining < 0 {
		return 0
	}
	return remaining
}

// Format renders the context frame as a text block for injection into tool results.
// Returns empty string if no facts are present.
func (cf *ContextFrame) Format() string {
	if len(cf.Facts) == 0 {
		return ""
	}

	var b strings.Builder
	b.WriteString("\n\n---\n[MEMORY CONTEXT]\n")

	for i, sf := range cf.Facts {
		level := sf.Fact.Level.String()
		domain := sf.Fact.Domain
		if domain == "" {
			domain = "general"
		}

		b.WriteString(fmt.Sprintf("• [L%d/%s] %s", int(sf.Fact.Level), level, sf.Fact.Content))
		if domain != "general" {
			b.WriteString(fmt.Sprintf(" (domain: %s)", domain))
		}
		if i < len(cf.Facts)-1 {
			b.WriteString("\n")
		}
	}

	b.WriteString("\n[/MEMORY CONTEXT]")
	return b.String()
}

// TokenBudget tracks token consumption for context injection.
type TokenBudget struct {
	MaxTokens int `json:"max_tokens"`
	used      int
}

// NewTokenBudget creates a token budget with the given maximum.
// If max is <= 0, uses DefaultTokenBudget.
func NewTokenBudget(max int) *TokenBudget {
	if max <= 0 {
		max = DefaultTokenBudget
	}
	return &TokenBudget{
		MaxTokens: max,
		used:      0,
	}
}

// TryConsume attempts to consume n tokens. Returns true if successful.
func (tb *TokenBudget) TryConsume(n int) bool {
	if tb.used+n > tb.MaxTokens {
		return false
	}
	tb.used += n
	return true
}

// Remaining returns the number of tokens left.
func (tb *TokenBudget) Remaining() int {
	r := tb.MaxTokens - tb.used
	if r < 0 {
		return 0
	}
	return r
}

// Reset resets the budget to full capacity.
func (tb *TokenBudget) Reset() {
	tb.used = 0
}

// EngineConfig holds configuration for the Proactive Context Engine.
type EngineConfig struct {
	TokenBudget        int      `json:"token_budget"`
	MaxFacts           int      `json:"max_facts"`
	RecencyWeight      float64  `json:"recency_weight"`
	FrequencyWeight    float64  `json:"frequency_weight"`
	LevelWeight        float64  `json:"level_weight"`
	KeywordWeight      float64  `json:"keyword_weight"`
	DecayHalfLifeHours float64  `json:"decay_half_life_hours"`
	Enabled            bool     `json:"enabled"`
	SkipTools          []string `json:"skip_tools,omitempty"`

	// Computed at init for O(1) lookup.
	skipSet map[string]bool
}

// DefaultEngineConfig returns sensible defaults for the context engine.
func DefaultEngineConfig() EngineConfig {
	cfg := EngineConfig{
		TokenBudget:        DefaultTokenBudget,
		MaxFacts:           DefaultMaxFacts,
		RecencyWeight:      DefaultRecencyWeight,
		FrequencyWeight:    DefaultFrequencyWeight,
		LevelWeight:        DefaultLevelWeight,
		KeywordWeight:      DefaultKeywordWeight,
		DecayHalfLifeHours: DefaultDecayHalfLife,
		Enabled:            true,
		SkipTools:          DefaultSkipTools(),
	}
	cfg.BuildSkipSet()
	return cfg
}

// DefaultSkipTools returns the default list of tools excluded from context injection.
// These are tools that already return facts directly or system tools where context is noise.
func DefaultSkipTools() []string {
	return []string{
		"search_facts", "get_fact", "list_facts", "get_l0_facts",
		"get_stale_facts", "fact_stats", "list_domains", "process_expired",
		"semantic_search",
		"health", "version", "dashboard",
	}
}

// BuildSkipSet builds the O(1) lookup set from SkipTools slice.
// Must be called after deserialization or manual SkipTools changes.
func (c *EngineConfig) BuildSkipSet() {
	c.skipSet = make(map[string]bool, len(c.SkipTools))
	for _, t := range c.SkipTools {
		c.skipSet[t] = true
	}
}

// ShouldSkip returns true if the given tool name is in the skip list.
func (c *EngineConfig) ShouldSkip(toolName string) bool {
	if c.skipSet == nil {
		c.BuildSkipSet()
	}
	return c.skipSet[toolName]
}

// Validate checks the configuration for errors.
func (c *EngineConfig) Validate() error {
	if c.TokenBudget <= 0 {
		return errors.New("token_budget must be positive")
	}
	if c.MaxFacts <= 0 {
		return errors.New("max_facts must be positive")
	}
	if c.RecencyWeight < 0 || c.FrequencyWeight < 0 || c.LevelWeight < 0 || c.KeywordWeight < 0 {
		return errors.New("weights must be non-negative")
	}
	totalWeight := c.RecencyWeight + c.FrequencyWeight + c.LevelWeight + c.KeywordWeight
	if totalWeight == 0 {
		return errors.New("at least one weight must be positive")
	}
	return nil
}

// --- Stop words for keyword extraction ---

var stopWords = map[string]bool{
	"a": true, "an": true, "the": true, "is": true, "are": true, "was": true,
	"were": true, "be": true, "been": true, "being": true, "have": true,
	"has": true, "had": true, "do": true, "does": true, "did": true,
	"will": true, "would": true, "could": true, "should": true, "may": true,
	"might": true, "shall": true, "can": true, "to": true, "of": true,
	"in": true, "for": true, "on": true, "with": true, "at": true,
	"by": true, "from": true, "as": true, "into": true, "through": true,
	"during": true, "before": true, "after": true, "above": true,
	"below": true, "between": true, "and": true, "but": true, "or": true,
	"nor": true, "not": true, "so": true, "yet": true, "both": true,
	"either": true, "neither": true, "each": true, "every": true,
	"all": true, "any": true, "few": true, "more": true, "most": true,
	"other": true, "some": true, "such": true, "no": true, "only": true,
	"same": true, "than": true, "too": true, "very": true, "just": true,
	"about": true, "up": true, "out": true, "if": true, "then": true,
	"that": true, "this": true, "these": true, "those": true, "it": true,
	"its": true, "i": true, "me": true, "my": true, "we": true, "our": true,
	"you": true, "your": true, "he": true, "him": true, "his": true,
	"she": true, "her": true, "they": true, "them": true, "their": true,
	"what": true, "which": true, "who": true, "whom": true, "when": true,
	"where": true, "why": true, "how": true, "there": true, "here": true,
}

// ExtractKeywords extracts meaningful keywords from text, filtering stop words
// and short tokens. Splits camelCase and snake_case identifiers.
// Returns deduplicated lowercase keywords.
func ExtractKeywords(text string) []string {
	if text == "" {
		return nil
	}

	// First split camelCase before lowercasing
	expanded := splitCamelCase(text)

	// Tokenize: split on non-alphanumeric boundaries (underscore is a separator now)
	words := strings.FieldsFunc(strings.ToLower(expanded), func(r rune) bool {
		return !unicode.IsLetter(r) && !unicode.IsDigit(r)
	})

	seen := make(map[string]bool)
	var keywords []string

	for _, w := range words {
		if len(w) < 3 {
			continue // skip very short tokens
		}
		if stopWords[w] {
			continue
		}
		if seen[w] {
			continue
		}
		seen[w] = true
		keywords = append(keywords, w)
	}

	return keywords
}

// splitCamelCase inserts spaces at camelCase boundaries.
// "handleRequest" → "handle Request", "getHTTPClient" → "get HTTP Client"
// Also replaces underscores with spaces for snake_case splitting.
func splitCamelCase(s string) string {
	var b strings.Builder
	runes := []rune(s)
	for i, r := range runes {
		if r == '_' {
			b.WriteRune(' ')
			continue
		}
		if i > 0 && unicode.IsUpper(r) {
			prev := runes[i-1]
			// Insert space before uppercase if previous was lowercase
			// or if previous was uppercase and next is lowercase (e.g., "HTTPClient" → "HTTP Client")
			if unicode.IsLower(prev) {
				b.WriteRune(' ')
			} else if unicode.IsUpper(prev) && i+1 < len(runes) && unicode.IsLower(runes[i+1]) {
				b.WriteRune(' ')
			}
		}
		b.WriteRune(r)
	}
	return b.String()
}

// timeSinceHours returns the number of hours elapsed since the given time.
func timeSinceHours(t time.Time) float64 {
	return time.Since(t).Hours()
}

// EstimateTokenCount returns an approximate token count for the given text.
// Uses the heuristic of ~4 characters per token, with a minimum of 1.
func EstimateTokenCount(text string) int {
	if len(text) == 0 {
		return 1 // minimum overhead
	}
	tokens := len(text)/4 + 1 // +1 for rounding and formatting overhead
	return tokens
}
