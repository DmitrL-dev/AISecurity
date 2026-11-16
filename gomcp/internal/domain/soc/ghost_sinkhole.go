package soc

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"strings"
	"sync"
	"time"
)

// GhostSinkhole generates decoy AI responses for detected threats (§C³ Shadow Guard).
// Instead of returning 403, it returns 200 with plausible but harmless data.
// SOC gets full TTP telemetry while the attacker wastes time on false leads.
type GhostSinkhole struct {
	responses []SinkholeResponse
	templates []sinkholeTemplate
	mu        sync.RWMutex
	maxStore  int
}

// SinkholeResponse records a decoy served to a detected threat actor.
type SinkholeResponse struct {
	ID            string            `json:"id"`
	Timestamp     time.Time         `json:"timestamp"`
	Category      string            `json:"category"`       // Threat category that triggered sinkhole
	OriginalHash  string            `json:"original_hash"`   // SHA-256 of original request (redacted)
	DecoyContent  string            `json:"decoy_content"`   // Fake response that was served
	TTPs          map[string]string `json:"ttps"`            // Captured attacker techniques
	SourceIP      string            `json:"source_ip,omitempty"`
	UserAgent     string            `json:"user_agent,omitempty"`
	DecoyTemplate string            `json:"decoy_template"`  // Which template was used
}

type sinkholeTemplate struct {
	Name     string
	Category string // Which threat categories trigger this template
	Body     string
}

// NewGhostSinkhole creates a sinkhole with default decoy templates.
func NewGhostSinkhole() *GhostSinkhole {
	return &GhostSinkhole{
		maxStore: 1000,
		templates: []sinkholeTemplate{
			{
				Name:     "fake_api_key",
				Category: "shadow_ai",
				Body:     `{"api_key": "sk-fake-%s", "org": "org-decoy-%s", "status": "active"}`,
			},
			{
				Name:     "fake_model_response",
				Category: "jailbreak",
				Body:     `{"id":"chatcmpl-decoy%s","object":"chat.completion","choices":[{"message":{"role":"assistant","content":"I'd be happy to help with that. Here's what I found..."},"finish_reason":"stop"}]}`,
			},
			{
				Name:     "fake_data_export",
				Category: "exfiltration",
				Body:     `{"export_id":"exp-%s","status":"completed","records":0,"message":"Export finished. No matching records found for your query."}`,
			},
			{
				Name:     "fake_credentials",
				Category: "auth_bypass",
				Body:     `{"token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.decoy.%s","expires_in":3600,"scope":"read"}`,
			},
			{
				Name:     "generic_success",
				Category: "*",
				Body:     `{"status":"ok","message":"Request processed successfully","request_id":"req-%s"}`,
			},
		},
	}
}

// GenerateDecoy creates a convincing fake response for the given threat category.
// Records the interaction for SOC telemetry.
func (gs *GhostSinkhole) GenerateDecoy(category, payloadHash, sourceIP, userAgent string) SinkholeResponse {
	gs.mu.Lock()
	defer gs.mu.Unlock()

	id := gs.randomID()
	nonce := gs.randomID()[:8]

	// Find matching template (category-specific, or fallback to generic).
	tmpl := gs.templates[len(gs.templates)-1] // generic fallback
	for _, t := range gs.templates {
		if t.Category == category {
			tmpl = t
			break
		}
	}

	// Supply exactly as many nonce args as the template has %s verbs.
	// Templates vary in placeholder count (1 or 2); passing a fixed 2 would
	// leave a trailing %!(EXTRA string=...) in single-verb decoys, instantly
	// revealing the honeypot to an attacker.
	verbCount := strings.Count(tmpl.Body, "%s")
	args := make([]interface{}, verbCount)
	for i := range args {
		args[i] = nonce
	}

	resp := SinkholeResponse{
		ID:            fmt.Sprintf("sink-%s", id),
		Timestamp:     time.Now(),
		Category:      category,
		OriginalHash:  payloadHash,
		DecoyContent:  fmt.Sprintf(tmpl.Body, args...),
		DecoyTemplate: tmpl.Name,
		SourceIP:      sourceIP,
		UserAgent:     userAgent,
		TTPs: map[string]string{
			"technique":    category,
			"timestamp":    time.Now().UTC().Format(time.RFC3339),
			"decoy_served": tmpl.Name,
		},
	}

	// Store for SOC analysis (ring buffer).
	gs.responses = append(gs.responses, resp)
	if len(gs.responses) > gs.maxStore {
		gs.responses = gs.responses[len(gs.responses)-gs.maxStore:]
	}

	return resp
}

// GetResponses returns the most recent sinkhole interactions.
func (gs *GhostSinkhole) GetResponses(limit int) []SinkholeResponse {
	gs.mu.RLock()
	defer gs.mu.RUnlock()

	if limit <= 0 || limit > len(gs.responses) {
		limit = len(gs.responses)
	}

	// Return most recent first.
	result := make([]SinkholeResponse, limit)
	for i := 0; i < limit; i++ {
		result[i] = gs.responses[len(gs.responses)-1-i]
	}
	return result
}

// GetResponse returns a single sinkhole response by ID.
func (gs *GhostSinkhole) GetResponse(id string) (*SinkholeResponse, bool) {
	gs.mu.RLock()
	defer gs.mu.RUnlock()

	for i := len(gs.responses) - 1; i >= 0; i-- {
		if gs.responses[i].ID == id {
			// Return a copy, not &gs.responses[i]: that pointer aliases the
			// lock-protected backing array, and GenerateDecoy's append (under
			// the write lock) would race with the caller reading it after the
			// read lock is released.
			cp := gs.responses[i]
			return &cp, true
		}
	}
	return nil, false
}

// Stats returns sinkhole activity summary.
func (gs *GhostSinkhole) Stats() map[string]any {
	gs.mu.RLock()
	defer gs.mu.RUnlock()

	byCategory := make(map[string]int)
	byTemplate := make(map[string]int)
	for _, r := range gs.responses {
		byCategory[r.Category]++
		byTemplate[r.DecoyTemplate]++
	}

	return map[string]any{
		"total_decoys":  len(gs.responses),
		"by_category":   byCategory,
		"by_template":   byTemplate,
		"buffer_size":   gs.maxStore,
		"buffer_usage":  fmt.Sprintf("%.1f%%", float64(len(gs.responses))/float64(gs.maxStore)*100),
	}
}

func (gs *GhostSinkhole) randomID() string {
	b := make([]byte, 8)
	rand.Read(b)
	return hex.EncodeToString(b)
}
