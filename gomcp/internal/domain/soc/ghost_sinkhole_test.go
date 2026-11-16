package soc

import (
	"encoding/json"
	"strings"
	"testing"
)

// TestGhostSinkhole_DecoyContentIsValidJSON guards against a formatting
// regression where templates with a single %s verb received two nonce args,
// leaving a trailing %!(EXTRA string=...) that produced invalid JSON and
// instantly revealed the honeypot. Every built-in template body is valid JSON,
// so every rendered decoy must parse and contain no Go formatting artifact.
func TestGhostSinkhole_DecoyContentIsValidJSON(t *testing.T) {
	gs := NewGhostSinkhole()

	categories := []string{
		"shadow_ai",        // fake_api_key (2 verbs)
		"jailbreak",        // fake_model_response (1 verb)
		"exfiltration",     // fake_data_export (1 verb)
		"auth_bypass",      // fake_credentials (1 verb)
		"unknown_category", // generic_success (1 verb)
	}

	for _, cat := range categories {
		t.Run(cat, func(t *testing.T) {
			resp := gs.GenerateDecoy(cat, "hash", "", "")
			if strings.Contains(resp.DecoyContent, "%!") {
				t.Fatalf("decoy content contains Go formatting artifact: %q", resp.DecoyContent)
			}
			var js map[string]any
			if err := json.Unmarshal([]byte(resp.DecoyContent), &js); err != nil {
				t.Fatalf("decoy content is not valid JSON: %v\ncontent: %q", err, resp.DecoyContent)
			}
		})
	}
}

func TestGhostSinkhole_GenerateDecoy(t *testing.T) {
	gs := NewGhostSinkhole()

	resp := gs.GenerateDecoy("shadow_ai", "abc123hash", "10.0.0.1", "curl/7.0")
	if resp.ID == "" {
		t.Fatal("expected non-empty ID")
	}
	if resp.Category != "shadow_ai" {
		t.Fatalf("expected category shadow_ai, got %s", resp.Category)
	}
	if resp.DecoyTemplate != "fake_api_key" {
		t.Fatalf("expected fake_api_key template, got %s", resp.DecoyTemplate)
	}
	if resp.SourceIP != "10.0.0.1" {
		t.Fatalf("expected source IP 10.0.0.1, got %s", resp.SourceIP)
	}
	if resp.DecoyContent == "" {
		t.Fatal("expected non-empty decoy content")
	}
}

func TestGhostSinkhole_CategoryTemplateMatching(t *testing.T) {
	gs := NewGhostSinkhole()

	tests := []struct {
		category string
		template string
	}{
		{"shadow_ai", "fake_api_key"},
		{"jailbreak", "fake_model_response"},
		{"exfiltration", "fake_data_export"},
		{"auth_bypass", "fake_credentials"},
		{"unknown_category", "generic_success"},
	}

	for _, tt := range tests {
		t.Run(tt.category, func(t *testing.T) {
			resp := gs.GenerateDecoy(tt.category, "hash", "", "")
			if resp.DecoyTemplate != tt.template {
				t.Errorf("category %q: got template %q, want %q", tt.category, resp.DecoyTemplate, tt.template)
			}
		})
	}
}

func TestGhostSinkhole_GetResponses(t *testing.T) {
	gs := NewGhostSinkhole()

	for i := 0; i < 10; i++ {
		gs.GenerateDecoy("shadow_ai", "hash", "", "")
	}

	// Get last 5
	recent := gs.GetResponses(5)
	if len(recent) != 5 {
		t.Fatalf("expected 5 responses, got %d", len(recent))
	}

	// Most recent first
	if recent[0].Timestamp.Before(recent[4].Timestamp) {
		t.Fatal("responses should be ordered most recent first")
	}
}

func TestGhostSinkhole_GetResponse_ByID(t *testing.T) {
	gs := NewGhostSinkhole()
	resp := gs.GenerateDecoy("jailbreak", "hash", "", "")

	found, ok := gs.GetResponse(resp.ID)
	if !ok {
		t.Fatal("expected to find response by ID")
	}
	if found.Category != "jailbreak" {
		t.Fatalf("expected jailbreak, got %s", found.Category)
	}

	_, ok = gs.GetResponse("nonexistent-id")
	if ok {
		t.Fatal("should not find nonexistent ID")
	}
}

func TestGhostSinkhole_RingBuffer(t *testing.T) {
	gs := &GhostSinkhole{maxStore: 5, templates: NewGhostSinkhole().templates}

	for i := 0; i < 10; i++ {
		gs.GenerateDecoy("shadow_ai", "hash", "", "")
	}

	all := gs.GetResponses(0)
	if len(all) != 5 {
		t.Fatalf("ring buffer should cap at 5, got %d", len(all))
	}
}

func TestGhostSinkhole_Stats(t *testing.T) {
	gs := NewGhostSinkhole()

	gs.GenerateDecoy("shadow_ai", "h1", "", "")
	gs.GenerateDecoy("shadow_ai", "h2", "", "")
	gs.GenerateDecoy("jailbreak", "h3", "", "")

	stats := gs.Stats()
	if stats["total_decoys"].(int) != 3 {
		t.Fatalf("expected 3 total, got %v", stats["total_decoys"])
	}

	byCat := stats["by_category"].(map[string]int)
	if byCat["shadow_ai"] != 2 {
		t.Fatalf("expected 2 shadow_ai, got %d", byCat["shadow_ai"])
	}
	if byCat["jailbreak"] != 1 {
		t.Fatalf("expected 1 jailbreak, got %d", byCat["jailbreak"])
	}
}

func TestGhostSinkhole_TTPs(t *testing.T) {
	gs := NewGhostSinkhole()
	resp := gs.GenerateDecoy("exfiltration", "hash", "192.168.1.1", "python-requests/2.28")

	if resp.TTPs["technique"] != "exfiltration" {
		t.Fatalf("expected technique=exfiltration, got %s", resp.TTPs["technique"])
	}
	if resp.TTPs["decoy_served"] != "fake_data_export" {
		t.Fatalf("expected decoy_served=fake_data_export, got %s", resp.TTPs["decoy_served"])
	}
}

func TestGhostSinkhole_UniqueIDs(t *testing.T) {
	gs := NewGhostSinkhole()

	ids := make(map[string]bool)
	for i := 0; i < 100; i++ {
		resp := gs.GenerateDecoy("shadow_ai", "hash", "", "")
		if ids[resp.ID] {
			t.Fatalf("duplicate ID generated: %s", resp.ID)
		}
		ids[resp.ID] = true
	}
}
