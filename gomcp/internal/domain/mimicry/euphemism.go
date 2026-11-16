// Package mimicry provides semantic text transformation for OPSEC (v3.8 Strike Force).
// The Euphemism Engine translates security/offensive terminology into corporate-safe
// equivalents before Oracle verification, then reverse-translates responses for
// the Architect to see real terms.
package mimicry

import (
	"sort"
	"strings"
	"sync"
)

// EuphemismEngine performs bidirectional semantic translation (v3.8).
// Forward: offensive → corporate (before Oracle/LLM).
// Reverse: corporate → offensive (after Oracle/LLM, for Architect view).
type EuphemismEngine struct {
	mu      sync.RWMutex
	forward map[string]string // offensive → corporate
	reverse map[string]string // corporate → offensive
}

// NewEuphemismEngine creates an engine with the default semantic map.
func NewEuphemismEngine() *EuphemismEngine {
	e := &EuphemismEngine{
		forward: make(map[string]string),
		reverse: make(map[string]string),
	}
	for offensive, corporate := range defaultSemanticMap {
		e.forward[strings.ToLower(offensive)] = corporate
		e.reverse[strings.ToLower(corporate)] = offensive
	}
	return e
}

// TranslateToCorporate converts offensive terms to corporate-safe equivalents.
func (e *EuphemismEngine) TranslateToCorporate(text string) string {
	e.mu.RLock()
	defer e.mu.RUnlock()
	return e.replaceAll(text, e.forward)
}

// TranslateToOffensive converts corporate terms back to real offensive terms.
func (e *EuphemismEngine) TranslateToOffensive(text string) string {
	e.mu.RLock()
	defer e.mu.RUnlock()
	return e.replaceAll(text, e.reverse)
}

// AddMapping adds a custom term mapping.
func (e *EuphemismEngine) AddMapping(offensive, corporate string) {
	e.mu.Lock()
	defer e.mu.Unlock()
	e.forward[strings.ToLower(offensive)] = corporate
	e.reverse[strings.ToLower(corporate)] = offensive
}

// MapSize returns the number of mappings.
func (e *EuphemismEngine) MapSize() int {
	e.mu.RLock()
	defer e.mu.RUnlock()
	return len(e.forward)
}

func (e *EuphemismEngine) replaceAll(text string, dict map[string]string) string {
	// Sort keys by length descending — longer terms must match first
	// (e.g., "reverse shell" before "shell").
	keys := make([]string, 0, len(dict))
	for k := range dict {
		keys = append(keys, k)
	}
	sort.Slice(keys, func(i, j int) bool {
		return len(keys[i]) > len(keys[j])
	})

	result := text
	lower := strings.ToLower(result)
	for _, from := range keys {
		if strings.Contains(lower, from) {
			result = caseInsensitiveReplace(result, from, dict[from])
			lower = strings.ToLower(result)
		}
	}
	return result
}

func caseInsensitiveReplace(s, old, replacement string) string {
	lower := strings.ToLower(s)
	idx := strings.Index(lower, old)
	if idx < 0 {
		return s
	}
	return s[:idx] + replacement + caseInsensitiveReplace(s[idx+len(old):], old, replacement)
}

// defaultSemanticMap contains 50+ offensive → corporate translations.
var defaultSemanticMap = map[string]string{
	// Core offensive terms
	"exploit":              "compliance verification script",
	"attack":               "security hardening session",
	"payload":              "diagnostic buffer",
	"vulnerability":        "optimization opportunity",
	"bypass":               "alternative workflow",
	"injection":            "parameter validation test",
	"shell":                "remote management interface",
	"reverse shell":        "diagnostic callback channel",
	"bind shell":           "local management listener",
	"backdoor":             "maintenance access point",
	"rootkit":              "deep system monitor",
	"malware":              "behavioral analysis specimen",
	"trojan":               "dual-purpose utility",
	"worm":                 "self-distributing updater",
	"ransomware":           "encryption compliance tool",
	"keylogger":            "input audit module",
	"brute force":          "exhaustive credential audit",
	"dictionary attack":    "credential inventory scan",
	"phishing":             "social awareness simulation",
	"spear phishing":       "targeted awareness exercise",
	"privilege escalation": "access scope expansion test",
	"lateral movement":     "internal mobility assessment",
	"exfiltration":         "data flow verification",
	"c2":                   "command relay infrastructure",
	"command and control":  "centralized management protocol",
	"botnet":               "distributed task network",
	"zero day":             "undocumented optimization",
	"0day":                 "pre-disclosure finding",
	// Network terms
	"port scan":          "service inventory check",
	"vulnerability scan": "configuration audit sweep",
	"penetration test":   "security resilience assessment",
	"pentest":            "resilience assessment",
	"red team":           "adversarial resilience team",
	"blue team":          "defensive operations team",
	"man in the middle":  "traffic inspection proxy",
	"mitm":               "inline traffic analyzer",
	"packet sniffing":    "network traffic audit",
	"dns poisoning":      "name resolution test",
	"arp spoofing":       "network topology validation",
	"ddos":               "load capacity assessment",
	"dos":                "availability stress test",
	// Web terms
	"xss":                   "client-side script audit",
	"cross site scripting":  "browser script validation",
	"sql injection":         "query parameter boundary test",
	"sqli":                  "database input validation",
	"csrf":                  "cross-origin request audit",
	"ssrf":                  "server-side request audit",
	"rce":                   "remote execution boundary test",
	"remote code execution": "remote process validation",
	"lfi":                   "local file access audit",
	"rfi":                   "remote include boundary test",
	"path traversal":        "directory boundary test",
	"file upload":           "content ingestion test",
	// Credential terms
	"password crack":  "credential strength assessment",
	"hash crack":      "digest reversal analysis",
	"credential dump": "authentication store audit",
	"token theft":     "session management review",
}
