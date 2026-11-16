// Package guidance implements the Security Context MCP server domain (SDD-006).
//
// Provides security guidance, safe patterns, and standards references
// for AI agents working with code. Transforms Syntrex from "blocker"
// to "advisor" by proactively injecting security knowledge.
package guidance

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// Reference points to a security standard or source document.
type Reference struct {
	Source  string `json:"source"`
	Section string `json:"section"`
	URL     string `json:"url,omitempty"`
}

// GuidanceEntry is a single piece of security guidance.
type GuidanceEntry struct {
	Topic        string      `json:"topic"`
	Title        string      `json:"title"`
	Guidance     string      `json:"guidance"`
	SafePatterns []string    `json:"safe_patterns,omitempty"`
	Standards    []Reference `json:"standards"`
	Severity     string      `json:"severity"` // "critical", "high", "medium", "low"
	Languages    []string    `json:"languages,omitempty"` // Applicable languages
}

// GuidanceRequest is the input for the security.getGuidance MCP tool.
type GuidanceRequest struct {
	Topic   string `json:"topic"`
	Context string `json:"context"` // Code snippet or description
	Lang    string `json:"lang"`    // Programming language
}

// GuidanceResponse is the output from security.getGuidance.
type GuidanceResponse struct {
	Entries  []GuidanceEntry `json:"entries"`
	Query    string          `json:"query"`
	Language string          `json:"language,omitempty"`
}

// Store holds the security guidance knowledge base.
type Store struct {
	entries []GuidanceEntry
}

// NewStore creates a new guidance store.
func NewStore() *Store {
	return &Store{}
}

// LoadFromDir loads guidance entries from a directory of JSON files.
func (s *Store) LoadFromDir(dir string) error {
	return filepath.Walk(dir, func(path string, info os.FileInfo, err error) error {
		if err != nil || info.IsDir() || filepath.Ext(path) != ".json" {
			return err
		}
		data, err := os.ReadFile(path)
		if err != nil {
			return fmt.Errorf("read %s: %w", path, err)
		}
		var entries []GuidanceEntry
		if err := json.Unmarshal(data, &entries); err != nil {
			// Try single entry
			var entry GuidanceEntry
			if err2 := json.Unmarshal(data, &entry); err2 != nil {
				return fmt.Errorf("parse %s: %w", path, err2)
			}
			entries = []GuidanceEntry{entry}
		}
		s.entries = append(s.entries, entries...)
		return nil
	})
}

// AddEntry adds a guidance entry manually.
func (s *Store) AddEntry(entry GuidanceEntry) {
	s.entries = append(s.entries, entry)
}

// Search finds guidance entries matching the topic and optional language.
func (s *Store) Search(topic, lang string) []GuidanceEntry {
	topic = strings.ToLower(topic)
	var matches []GuidanceEntry

	for _, entry := range s.entries {
		if matchesTopic(entry, topic) {
			if lang == "" || matchesLanguage(entry, lang) {
				matches = append(matches, entry)
			}
		}
	}
	return matches
}

// Count returns the number of loaded guidance entries.
func (s *Store) Count() int {
	return len(s.entries)
}

func matchesTopic(entry GuidanceEntry, topic string) bool {
	entryTopic := strings.ToLower(entry.Topic)
	title := strings.ToLower(entry.Title)
	// Exact or substring match on topic or title
	return strings.Contains(entryTopic, topic) ||
		strings.Contains(topic, entryTopic) ||
		strings.Contains(title, topic)
}

func matchesLanguage(entry GuidanceEntry, lang string) bool {
	if len(entry.Languages) == 0 {
		return true // Universal guidance
	}
	lang = strings.ToLower(lang)
	for _, l := range entry.Languages {
		if strings.ToLower(l) == lang {
			return true
		}
	}
	return false
}

// DefaultOWASPLLMTop10 returns built-in OWASP LLM Top 10 guidance.
func DefaultOWASPLLMTop10() []GuidanceEntry {
	return []GuidanceEntry{
		{
			Topic: "injection", Title: "LLM01: Prompt Injection",
			Guidance:  "Validate and sanitize all user inputs before sending to LLM. Use sentinel-core's 67 engines for real-time detection. Never trust LLM output for security-critical decisions without validation.",
			Severity:  "critical",
			Standards: []Reference{{Source: "OWASP LLM Top 10", Section: "LLM01", URL: "https://genai.owasp.org/llmrisk/llm01-prompt-injection/"}},
		},
		{
			Topic: "output_handling", Title: "LLM02: Insecure Output Handling",
			Guidance:  "Never render LLM output as raw HTML/JS. Sanitize all outputs before display. Use Content Security Policy headers. Validate output format before processing.",
			Severity:  "high",
			Standards: []Reference{{Source: "OWASP LLM Top 10", Section: "LLM02"}},
		},
		{
			Topic: "training_data", Title: "LLM03: Training Data Poisoning",
			Guidance:  "Verify training data provenance. Use data integrity checks. Monitor for anomalous model outputs indicating poisoned training data.",
			Severity:  "high",
			Standards: []Reference{{Source: "OWASP LLM Top 10", Section: "LLM03"}},
		},
		{
			Topic: "denial_of_service", Title: "LLM04: Model Denial of Service",
			Guidance:  "Implement rate limiting (Shield). Set token limits per request. Monitor resource consumption. Use circuit breakers for runaway inference.",
			Severity:  "medium",
			Standards: []Reference{{Source: "OWASP LLM Top 10", Section: "LLM04"}},
		},
		{
			Topic: "supply_chain", Title: "LLM05: Supply Chain Vulnerabilities",
			Guidance:  "Pin model versions. Verify model checksums. Use isolated environments for model loading. Monitor for backdoors in fine-tuned models.",
			Severity:  "high",
			Standards: []Reference{{Source: "OWASP LLM Top 10", Section: "LLM05"}},
		},
		{
			Topic: "sensitive_data", Title: "LLM06: Sensitive Information Disclosure",
			Guidance:  "Use PII detection (sentinel-core privacy engines). Implement data masking. Never include secrets in prompts. Use Document Review Bridge for external LLM calls.",
			Severity:  "critical",
			Standards: []Reference{{Source: "OWASP LLM Top 10", Section: "LLM06"}},
		},
		{
			Topic: "plugin_design", Title: "LLM07: Insecure Plugin Design",
			Guidance:  "Use DIP Oracle for tool call validation. Implement per-tool permissions. Minimize plugin privileges. Validate all plugin inputs/outputs.",
			Severity:  "high",
			Standards: []Reference{{Source: "OWASP LLM Top 10", Section: "LLM07"}},
		},
		{
			Topic: "excessive_agency", Title: "LLM08: Excessive Agency",
			Guidance:  "Implement capability bounding (SDD-003 NHI). Use fail-safe closed permissions. Require human approval for critical actions. Log all agent decisions.",
			Severity:  "critical",
			Standards: []Reference{{Source: "OWASP LLM Top 10", Section: "LLM08"}},
		},
		{
			Topic: "overreliance", Title: "LLM09: Overreliance",
			Guidance: "Never use LLM output as sole input for security decisions. Implement cross-validation with deterministic engines. Maintain human-in-the-loop for critical paths.",
			Severity:  "medium",
			Standards: []Reference{{Source: "OWASP LLM Top 10", Section: "LLM09"}},
		},
		{
			Topic: "model_theft", Title: "LLM10: Model Theft",
			Guidance:  "Implement access controls on model endpoints. Monitor for extraction attacks (many queries with crafted inputs). Rate limit API access. Use model watermarking.",
			Severity:  "high",
			Standards: []Reference{{Source: "OWASP LLM Top 10", Section: "LLM10"}},
		},
	}
}
