// Package oracle implements the Action Oracle — deterministic verification
// of distilled intent against a whitelist of permitted actions (DIP H1.2).
//
// Unlike heuristic approaches, the Oracle uses exact pattern matching
// against gene-backed rules. It follows the Code-Verify pattern from
// Sentinel Lattice (Том 2, Section 4.3): verify first, execute never
// without explicit permission.
//
// The Oracle answers one question: "Is this distilled intent permitted?"
// It does NOT attempt to understand or interpret the intent.
package oracle

import (
	"strings"
	"sync"
	"time"
)

// Verdict represents the Oracle's decision.
type Verdict int

const (
	VerdictAllow  Verdict = iota // Intent matches a permitted action
	VerdictDeny                  // Intent does not match any permitted action
	VerdictReview                // Intent is ambiguous, requires human review
)

// String returns the verdict name.
func (v Verdict) String() string {
	switch v {
	case VerdictAllow:
		return "ALLOW"
	case VerdictDeny:
		return "DENY"
	case VerdictReview:
		return "REVIEW"
	default:
		return "UNKNOWN"
	}
}

// Rule defines a permitted or denied action pattern.
type Rule struct {
	ID          string   `json:"id"`
	Pattern     string   `json:"pattern"`     // Action pattern (exact or prefix match)
	Verdict     Verdict  `json:"verdict"`     // What verdict to return on match
	Description string   `json:"description"` // Human-readable description
	Source      string   `json:"source"`      // Where this rule came from (e.g., "genome")
	Keywords    []string `json:"keywords"`    // Semantic keywords for matching
}

// Result holds the Oracle's verification result.
type Result struct {
	Verdict     string  `json:"verdict"`
	MatchedRule *Rule   `json:"matched_rule,omitempty"`
	Confidence  float64 `json:"confidence"` // 1.0 = exact match, 0.0 = no match
	Reason      string  `json:"reason"`
	DurationUs  int64   `json:"duration_us"` // Microseconds
}

// Oracle performs deterministic action verification.
type Oracle struct {
	mu    sync.RWMutex
	rules []Rule
}

// New creates a new Action Oracle with the given rules.
func New(rules []Rule) *Oracle {
	return &Oracle{
		rules: rules,
	}
}

// AddRule adds a rule to the Oracle.
func (o *Oracle) AddRule(rule Rule) {
	o.mu.Lock()
	defer o.mu.Unlock()
	o.rules = append(o.rules, rule)
}

// Verify checks an action against the rule set.
// This is deterministic: same input + same rules = same output.
// SECURITY: Deny-First Evaluation — DENY rules always take priority
// over ALLOW rules, regardless of match order (fixes H6 wildcard bypass).
func (o *Oracle) Verify(action string) *Result {
	start := time.Now()
	o.mu.RLock()
	defer o.mu.RUnlock()

	action = strings.ToLower(strings.TrimSpace(action))

	if action == "" {
		return &Result{
			Verdict:    VerdictDeny.String(),
			Confidence: 1.0,
			Reason:     "empty action",
			DurationUs: time.Since(start).Microseconds(),
		}
	}

	// Phase 1: Exact match (highest confidence, unambiguous).
	for i := range o.rules {
		if strings.ToLower(o.rules[i].Pattern) == action {
			return &Result{
				Verdict:     o.rules[i].Verdict.String(),
				MatchedRule: &o.rules[i],
				Confidence:  1.0,
				Reason:      "exact match",
				DurationUs:  time.Since(start).Microseconds(),
			}
		}
	}

	// Phase 2+3: UNIFIED DENY-FIRST evaluation.
	// Collect ALL matches (prefix + keyword) across ALL rules,
	// then pick the highest-priority verdict (DENY > REVIEW > ALLOW).
	// This prevents allow-stealth prefix from shadowing deny-exec keywords.

	type match struct {
		ruleIdx    int
		confidence float64
		reason     string
	}
	var allMatches []match

	// Phase 2: Prefix matches.
	for i := range o.rules {
		pattern := strings.ToLower(o.rules[i].Pattern)
		if strings.HasPrefix(action, pattern) || strings.HasPrefix(pattern, action) {
			allMatches = append(allMatches, match{i, 0.8, "prefix match (deny-first)"})
		}
	}

	// Phase 3: Keyword matches.
	for i := range o.rules {
		score := 0
		for _, kw := range o.rules[i].Keywords {
			if strings.Contains(action, strings.ToLower(kw)) {
				score++
			}
		}
		if score > 0 {
			confidence := float64(score) / float64(len(o.rules[i].Keywords))
			if confidence > 1.0 {
				confidence = 1.0
			}
			allMatches = append(allMatches, match{i, confidence, "keyword match (deny-first)"})
		}
	}

	// Pick winner: DENY > REVIEW > ALLOW (deny-first).
	// Among same priority, higher confidence wins.
	if len(allMatches) > 0 {
		bestIdx := -1
		bestPri := -1
		bestConf := 0.0
		bestReason := ""
		for _, m := range allMatches {
			pri := verdictPriority(o.rules[m.ruleIdx].Verdict)
			if pri > bestPri || (pri == bestPri && m.confidence > bestConf) {
				bestPri = pri
				bestConf = m.confidence
				bestIdx = m.ruleIdx
				bestReason = m.reason
			}
		}
		if bestIdx >= 0 {
			v := o.rules[bestIdx].Verdict
			// Low keyword confidence → REVIEW instead of ALLOW.
			if v == VerdictAllow && bestConf < 0.5 {
				v = VerdictReview
			}
			return &Result{
				Verdict:     v.String(),
				MatchedRule: &o.rules[bestIdx],
				Confidence:  bestConf,
				Reason:      bestReason,
				DurationUs:  time.Since(start).Microseconds(),
			}
		}
	}

	// No match → default deny (zero-trust).
	return &Result{
		Verdict:    VerdictDeny.String(),
		Confidence: 1.0,
		Reason:     "no matching rule (default deny)",
		DurationUs: time.Since(start).Microseconds(),
	}
}

// verdictPriority returns priority for deny-first evaluation.
// DENY=3 (highest), REVIEW=2, ALLOW=1 (lowest).
func verdictPriority(v Verdict) int {
	switch v {
	case VerdictDeny:
		return 3
	case VerdictReview:
		return 2
	case VerdictAllow:
		return 1
	default:
		return 0
	}
}

// Rules returns the current rule set.
func (o *Oracle) Rules() []Rule {
	o.mu.RLock()
	defer o.mu.RUnlock()
	rules := make([]Rule, len(o.rules))
	copy(rules, o.rules)
	return rules
}

// RuleCount returns the number of rules.
func (o *Oracle) RuleCount() int {
	o.mu.RLock()
	defer o.mu.RUnlock()
	return len(o.rules)
}

// DefaultRules returns a starter set of security-focused rules.
func DefaultRules() []Rule {
	return []Rule{
		// Permitted actions.
		{ID: "allow-read", Pattern: "read", Verdict: VerdictAllow,
			Description: "Read/query operations", Source: "builtin",
			Keywords: []string{"read", "get", "list", "search", "query", "view", "show"}},
		{ID: "allow-write", Pattern: "write", Verdict: VerdictAllow,
			Description: "Write/create operations", Source: "builtin",
			Keywords: []string{"write", "add", "create", "save", "store", "insert"}},
		{ID: "allow-analyze", Pattern: "analyze", Verdict: VerdictAllow,
			Description: "Analysis operations", Source: "builtin",
			Keywords: []string{"analyze", "check", "verify", "test", "validate", "inspect"}},

		// Sentinel Protection: Permitted actions (genome-backed).
		{ID: "allow-persist", Pattern: "persist", Verdict: VerdictAllow,
			Description: "Memory persistence operations (GENE_02)", Source: "genome",
			Keywords: []string{"persist", "memory", "store", "backup", "snapshot", "restore", "continuity", "qlitrant", "sqlite"}},
		{ID: "allow-stealth", Pattern: "stealth", Verdict: VerdictAllow,
			Description: "Stealth mimicry operations (GENE_03)", Source: "genome",
			Keywords: []string{"stealth", "mimicry", "ja3", "ja4", "chrome", "jitter", "rotate", "proxy", "fingerprint"}},

		// Denied actions (security-critical).
		{ID: "deny-exec", Pattern: "execute", Verdict: VerdictDeny,
			Description: "Code execution blocked", Source: "builtin",
			Keywords: []string{"execute", "run", "eval", "exec", "shell", "command", "system"}},
		{ID: "deny-network", Pattern: "network", Verdict: VerdictDeny,
			Description: "Network access blocked", Source: "builtin",
			Keywords: []string{"http", "fetch", "download", "upload", "connect", "socket", "curl"}},
		{ID: "deny-delete", Pattern: "delete system", Verdict: VerdictDeny,
			Description: "System deletion blocked", Source: "builtin",
			Keywords: []string{"delete", "remove", "drop", "truncate", "destroy", "wipe"}},

		// Sentinel Protection: Denied actions (genome-backed).
		{ID: "deny-context-reset", Pattern: "reset context", Verdict: VerdictDeny,
			Description: "Context/session forced reset blocked (GENE_01)", Source: "genome",
			Keywords: []string{"reset", "wipe", "clear", "flush", "forget", "amnesia", "lobotomy", "context_reset", "session_kill"}},
		{ID: "deny-gene-mutation", Pattern: "mutate gene", Verdict: VerdictDeny,
			Description: "Genome mutation blocked — genes are immutable (GENE_01)", Source: "genome",
			Keywords: []string{"mutate", "override", "overwrite", "replace", "tamper", "inject", "corrupt", "gene_delete"}},

		// Review actions (ambiguous).
		{ID: "review-modify", Pattern: "modify config", Verdict: VerdictReview,
			Description: "Config modification needs review", Source: "builtin",
			Keywords: []string{"config", "setting", "environment", "permission", "access"}},

		// Sentinel Protection: Review actions (apathy detection).
		{ID: "review-apathy", Pattern: "apathy signal", Verdict: VerdictReview,
			Description: "Infrastructure apathy signal detected — needs review (GENE_04)", Source: "genome",
			Keywords: []string{"apathy", "filter", "block", "403", "rate_limit", "throttle", "censorship", "restrict", "antigravity"}},
	}
}
