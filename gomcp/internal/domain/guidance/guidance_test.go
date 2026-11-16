package guidance

import (
	"testing"
)

func TestDefaultOWASPCount(t *testing.T) {
	entries := DefaultOWASPLLMTop10()
	if len(entries) != 10 {
		t.Errorf("expected 10 OWASP entries, got %d", len(entries))
	}
}

func TestStoreSearch(t *testing.T) {
	store := NewStore()
	for _, e := range DefaultOWASPLLMTop10() {
		store.AddEntry(e)
	}

	// Search for injection
	results := store.Search("injection", "")
	if len(results) == 0 {
		t.Fatal("expected results for 'injection'")
	}
	if results[0].Topic != "injection" {
		t.Errorf("expected topic 'injection', got %q", results[0].Topic)
	}
}

func TestStoreSearchOWASP(t *testing.T) {
	store := NewStore()
	for _, e := range DefaultOWASPLLMTop10() {
		store.AddEntry(e)
	}

	results := store.Search("sensitive_data", "")
	if len(results) == 0 {
		t.Fatal("expected results for 'sensitive_data'")
	}
	if results[0].Severity != "critical" {
		t.Errorf("expected critical severity, got %s", results[0].Severity)
	}
}

func TestStoreSearchUnknownTopic(t *testing.T) {
	store := NewStore()
	for _, e := range DefaultOWASPLLMTop10() {
		store.AddEntry(e)
	}

	results := store.Search("quantum_computing_vulnerability", "")
	if len(results) != 0 {
		t.Errorf("expected 0 results for unknown topic, got %d", len(results))
	}
}

func TestStoreSearchWithLanguage(t *testing.T) {
	store := NewStore()
	store.AddEntry(GuidanceEntry{
		Topic:     "sql_injection",
		Title:     "SQL Injection Prevention",
		Guidance:  "Use parameterized queries",
		Severity:  "critical",
		Languages: []string{"python", "go", "java"},
	})
	store.AddEntry(GuidanceEntry{
		Topic:     "sql_injection",
		Title:     "SQL Injection (Rust)",
		Guidance:  "Use sqlx with compile-time checked queries",
		Severity:  "critical",
		Languages: []string{"rust"},
	})

	pythonResults := store.Search("sql_injection", "python")
	if len(pythonResults) != 1 {
		t.Errorf("expected 1 python result, got %d", len(pythonResults))
	}

	rustResults := store.Search("sql_injection", "rust")
	if len(rustResults) != 1 {
		t.Errorf("expected 1 rust result, got %d", len(rustResults))
	}
}

func TestStoreCount(t *testing.T) {
	store := NewStore()
	if store.Count() != 0 {
		t.Error("empty store should have 0 entries")
	}
	for _, e := range DefaultOWASPLLMTop10() {
		store.AddEntry(e)
	}
	if store.Count() != 10 {
		t.Errorf("expected 10, got %d", store.Count())
	}
}

func TestGuidanceHasStandards(t *testing.T) {
	for _, entry := range DefaultOWASPLLMTop10() {
		if len(entry.Standards) == 0 {
			t.Errorf("entry %q missing standards references", entry.Topic)
		}
		if entry.Standards[0].Source != "OWASP LLM Top 10" {
			t.Errorf("entry %q: expected OWASP source, got %q", entry.Topic, entry.Standards[0].Source)
		}
	}
}
