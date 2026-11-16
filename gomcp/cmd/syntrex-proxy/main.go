// syntrex-proxy — transparent reverse proxy that scans LLM prompts.
//
// Usage:
//
//	syntrex-proxy \
//	  --target https://api.openai.com \
//	  --listen :8080 \
//	  --soc-url http://localhost:9100 \
//	  --api-key sk-xxx \
//	  --mode block
//
// Supported LLM APIs:
//   - OpenAI  /v1/chat/completions
//   - Anthropic /v1/messages
//   - Ollama  /api/generate, /api/chat
//
// Security posture (Review 13.06): in `block` mode the proxy FAILS CLOSED — if
// the SOC scan cannot be completed (unreachable, timeout, malformed response)
// the request is rejected, not waved through. A security gateway that fails open
// is a bypass: an attacker who can degrade the SOC would otherwise disable all
// scanning. Use `--fail-open` to opt back into the old behaviour. `audit` mode
// never blocks, so it is always fail-open.
package main

import (
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"strings"
	"time"
)

// defaultMaxBodyBytes caps the request body the proxy will buffer for scanning.
// Bodies larger than this are rejected (413) rather than read into memory — an
// unbounded io.ReadAll on an attacker-controlled body is a memory-DoS vector.
const defaultMaxBodyBytes int64 = 4 << 20 // 4 MiB

type Config struct {
	Listen      string
	Target      string
	SocURL      string
	APIKey      string
	Mode        string // "block" or "audit"
	FailOpen    bool   // if true, allow traffic when the scan cannot complete
	MaxBodyByte int64
	Verbose     bool
}

// ScanResult from SOC API
type ScanResult struct {
	Verdict          string  `json:"verdict"` // ALLOW, BLOCK, WARN
	Score            float64 `json:"score"`
	Category         string  `json:"category"`
	EnginesTriggered int     `json:"engines_triggered"`
}

// extractPrompts extracts attacker-influenceable text from various LLM API
// formats. It scans `user` AND `tool` message content (tool results are a prime
// indirect-injection vector — OWASP LLM01/“no MCP output is safe”), plus the
// generic single-field shapes.
// extractContentText pulls scannable text from a message "content" field, which
// may be a plain string OR an array of content blocks ({"type":"text","text":...}
// — the modern OpenAI/Anthropic multimodal default). Pre-launch audit 18.06: array
// content was silently skipped, so an attacker using content blocks bypassed the
// gateway entirely. Extraction must be total over both shapes.
func extractContentText(content interface{}) []string {
	var out []string
	switch c := content.(type) {
	case string:
		if c != "" {
			out = append(out, c)
		}
	case []interface{}:
		for _, blk := range c {
			switch b := blk.(type) {
			case string:
				if b != "" {
					out = append(out, b)
				}
			case map[string]interface{}:
				// Standard text block: {"type":"text","text":"..."}. Also pull a
				// nested string "content" if present (some tool-result shapes).
				if text, ok := b["text"].(string); ok && text != "" {
					out = append(out, text)
				}
				if nested, ok := b["content"].(string); ok && nested != "" {
					out = append(out, nested)
				}
			}
		}
	}
	return out
}

func extractPrompts(body []byte, path string) []string {
	_ = path // reserved for path-specific extraction; all shapes handled below
	var prompts []string
	var data map[string]interface{}
	if err := json.Unmarshal(body, &data); err != nil {
		return nil
	}

	// OpenAI /v1/chat/completions AND Anthropic /v1/messages → messages[].content
	// (user + tool roles). content may be a string OR an array of content blocks;
	// handle both (audit 18.06 — array content was a gateway bypass).
	if messages, ok := data["messages"]; ok {
		if msgs, ok := messages.([]interface{}); ok {
			for _, m := range msgs {
				if msg, ok := m.(map[string]interface{}); ok {
					role, _ := msg["role"].(string)
					if role == "user" || role == "tool" || role == "system" || role == "developer" {
						prompts = append(prompts, extractContentText(msg["content"])...)
					}
				}
			}
		}
	}

	// Anthropic: /v1/messages → content[].text
	if content, ok := data["content"]; ok {
		if items, ok := content.([]interface{}); ok {
			for _, item := range items {
				if c, ok := item.(map[string]interface{}); ok {
					if text, ok := c["text"].(string); ok && text != "" {
						prompts = append(prompts, text)
					}
				}
			}
		}
	}

	// Ollama: /api/generate → prompt
	if prompt, ok := data["prompt"].(string); ok && prompt != "" {
		prompts = append(prompts, prompt)
	}

	// Generic: input, query, text fields
	for _, field := range []string{"input", "query", "text", "raw_input", "system", "instructions"} {
		if val, ok := data[field].(string); ok && val != "" {
			prompts = append(prompts, val)
		}
	}

	return prompts
}

// socScanResponse is the actual shape returned by the SOC POST /api/v1/scan
// endpoint (sentinel-core + shield + ML). See soc_handlers.go::handlePublicScan.
type socScanResponse struct {
	Blocked    bool     `json:"blocked"`
	ThreatType string   `json:"threat_type"`
	Severity   string   `json:"severity"`
	Confidence float64  `json:"confidence"`
	Indicators []string `json:"indicators"`
}

// maxScanChars mirrors the /api/v1/scan hard cap (rejects >2000 with 400).
const maxScanChars = 2000

// scanPrompt sends the prompt to the SOC SCAN endpoint and returns a verdict.
//
// Review 13.06 — CRITICAL FIX: this previously POSTed to /api/v1/soc/events
// (the event-INGEST endpoint), which returns an ingested event, NOT a scan
// verdict. The proxy therefore never received a real verdict and silently
// allowed everything — block mode never actually blocked. It now calls
// /api/v1/scan (the verdict endpoint) and maps its real response shape.
//
// A non-nil error means the scan could NOT be completed (transport failure,
// non-200 status, or an undecodable body) — the caller honours the fail mode.
func scanPrompt(socURL, apiKey, prompt string) (*ScanResult, error) {
	// A partial prefix verdict cannot authorize forwarding the complete prompt.
	if len(prompt) > maxScanChars {
		return nil, fmt.Errorf("prompt exceeds complete-scan budget")
	}
	payload, _ := json.Marshal(map[string]string{"prompt": prompt})

	req, err := http.NewRequest("POST", socURL+"/api/v1/scan", bytes.NewReader(payload))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")
	if apiKey != "" {
		req.Header.Set("Authorization", "Bearer "+apiKey)
	}

	client := &http.Client{Timeout: 5 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("SOC unreachable: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		// 400/429/503/5xx all mean the scan did not yield a verdict.
		return nil, fmt.Errorf("SOC /scan status %d", resp.StatusCode)
	}

	var raw socScanResponse
	if err := json.NewDecoder(resp.Body).Decode(&raw); err != nil {
		return nil, fmt.Errorf("SOC /scan response undecodable: %w", err)
	}

	verdict := "ALLOW"
	if raw.Blocked {
		verdict = "BLOCK"
	}
	category := raw.ThreatType
	if category == "" {
		category = "unknown"
	}
	return &ScanResult{
		Verdict:          verdict,
		Score:            raw.Confidence,
		Category:         category,
		EnginesTriggered: len(raw.Indicators),
	}, nil
}

// writeBlock writes the canonical 403 block response.
func writeBlock(w http.ResponseWriter, category string, score float64) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusForbidden)
	_ = json.NewEncoder(w).Encode(map[string]interface{}{
		"error": map[string]interface{}{
			"message": fmt.Sprintf("Request blocked by SYNTREX Guard: %s (score: %.0f%%)", category, score*100),
			"type":    "syntrex_guard_block",
			"code":    "prompt_blocked",
		},
	})
}

// writeScanUnavailable writes the 503 returned when block-mode fails closed.
func writeScanUnavailable(w http.ResponseWriter) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Retry-After", "2")
	w.WriteHeader(http.StatusServiceUnavailable)
	_ = json.NewEncoder(w).Encode(map[string]interface{}{
		"error": map[string]interface{}{
			"message": "SYNTREX Guard could not verify this request (scan unavailable); request rejected (fail-closed).",
			"type":    "syntrex_guard_unavailable",
			"code":    "scan_unavailable",
		},
	})
}

// scanFunc is the SOC-scan dependency, injectable for testing.
type scanFunc func(prompt string) (*ScanResult, error)

// newHandler builds the proxy HTTP handler. `proxy` is the upstream passthrough;
// `scan` performs the SOC scan. Both are injected so the handler is testable
// without a live SOC or upstream.
func newHandler(cfg Config, proxy http.Handler, scan scanFunc) http.Handler {
	maxBody := cfg.MaxBodyByte
	if maxBody <= 0 {
		maxBody = defaultMaxBodyBytes
	}
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Liveness probe — never proxied, never scanned.
		if r.URL.Path == "/healthz" || r.URL.Path == "/readyz" {
			w.WriteHeader(http.StatusOK)
			_, _ = w.Write([]byte(`{"status":"ok"}`))
			return
		}

		// Only scan POST requests to known LLM endpoints.
		if r.Method != http.MethodPost {
			proxy.ServeHTTP(w, r)
			return
		}

		// Bounded read — reject oversized bodies instead of buffering them.
		limited := io.LimitReader(r.Body, maxBody+1)
		body, err := io.ReadAll(limited)
		if err != nil {
			http.Error(w, `{"error":"failed to read request body"}`, http.StatusBadRequest)
			return
		}
		if int64(len(body)) > maxBody {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusRequestEntityTooLarge)
			_, _ = w.Write([]byte(`{"error":{"message":"request body too large","code":"body_too_large"}}`))
			return
		}
		r.Body = io.NopCloser(bytes.NewReader(body))

		// Extract prompts.
		prompts := extractPrompts(body, r.URL.Path)
		if len(prompts) == 0 {
			// Unknown input schemas have no complete-scan proof in block mode.
			if cfg.Mode != "audit" {
				http.Error(w, "unsupported prompt schema", http.StatusBadRequest)
				return
			}
			proxy.ServeHTTP(w, r)
			return
		}

		combined := strings.Join(prompts, " ")
		if cfg.Mode != "audit" && len(combined) > maxScanChars {
			http.Error(w, "prompt exceeds complete-scan budget", http.StatusRequestEntityTooLarge)
			return
		}

		// Reject an interior NUL byte BEFORE scanning (Review 14.06 round-5). A
		// NUL truncates the prompt at the C-string boundary inside the native
		// engine (C.CString → CStr::from_ptr stops at the first NUL), so the tail
		// goes unscanned — yet the ORIGINAL un-truncated body still reaches the
		// upstream LLM. A NUL is never legitimate in a text prompt, so reject it
		// as malformed input in ALL modes (like the oversized-body guard above),
		// independent of the scan verdict. This also removes the proxy's sole
		// reliance on the /scan endpoint's own NUL rejection, which only protects
		// the default fail-closed block mode — audit / fail-open would otherwise
		// forward the request when the endpoint returns 400.
		if strings.IndexByte(combined, 0) >= 0 {
			log.Printf("[BLOCKED] %s %s — prompt contains illegal NUL byte", r.Method, r.URL.Path)
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusBadRequest)
			_, _ = w.Write([]byte(`{"error":{"message":"prompt contains illegal NUL byte","code":"illegal_nul"}}`))
			return
		}

		start := time.Now()
		result, scanErr := scan(combined)
		scanDuration := time.Since(start)

		// Scan could not complete → honour fail mode.
		if scanErr != nil {
			if cfg.Mode == "block" && !cfg.FailOpen {
				log.Printf("[FAIL-CLOSED] %s %s — scan unavailable: %v", r.Method, r.URL.Path, scanErr)
				writeScanUnavailable(w)
				return
			}
			log.Printf("[WARN] scan failed (%s, allowing): %v",
				map[bool]string{true: "fail-open", false: "audit"}[cfg.FailOpen], scanErr)
			proxy.ServeHTTP(w, r)
			return
		}

		if cfg.Verbose {
			log.Printf("[SCAN] %s %s → %s (score=%.2f, category=%s, %v)",
				r.Method, r.URL.Path, result.Verdict, result.Score, result.Category, scanDuration)
		}

		// Block mode.
		if cfg.Mode == "block" && result.Verdict == "BLOCK" {
			log.Printf("[BLOCKED] %s %s — %s (score=%.2f, engines=%d)",
				r.Method, r.URL.Path, result.Category, result.Score, result.EnginesTriggered)
			writeBlock(w, result.Category, result.Score)
			return
		}

		// Audit mode or ALLOW — pass through.
		if result.Verdict != "ALLOW" {
			log.Printf("[AUDIT] %s %s — %s (score=%.2f)", r.Method, r.URL.Path, result.Category, result.Score)
		}
		proxy.ServeHTTP(w, r)
	})
}

func main() {
	cfg := Config{}
	flag.StringVar(&cfg.Listen, "listen", ":8080", "Listen address")
	flag.StringVar(&cfg.Target, "target", "https://api.openai.com", "Target LLM API URL")
	flag.StringVar(&cfg.SocURL, "soc-url", "http://localhost:9100", "SYNTREX SOC API URL")
	flag.StringVar(&cfg.APIKey, "api-key", "", "SYNTREX API key")
	flag.StringVar(&cfg.Mode, "mode", "block", "Mode: block (reject threats) or audit (log only)")
	flag.BoolVar(&cfg.FailOpen, "fail-open", false, "Allow traffic when the scan cannot complete (default: fail closed in block mode)")
	flag.Int64Var(&cfg.MaxBodyByte, "max-body", defaultMaxBodyBytes, "Max request body bytes buffered for scanning")
	flag.BoolVar(&cfg.Verbose, "verbose", false, "Verbose logging")
	flag.Parse()

	targetURL, err := url.Parse(cfg.Target)
	if err != nil {
		log.Fatalf("Invalid target URL: %v", err)
	}

	proxy := httputil.NewSingleHostReverseProxy(targetURL)
	originalDirector := proxy.Director
	proxy.Director = func(req *http.Request) {
		originalDirector(req)
		req.Host = targetURL.Host
	}

	handler := newHandler(cfg, proxy, func(prompt string) (*ScanResult, error) {
		return scanPrompt(cfg.SocURL, cfg.APIKey, prompt)
	})

	failMode := "fail-closed"
	if cfg.FailOpen || cfg.Mode != "block" {
		failMode = "fail-open"
	}
	log.Printf("🛡️  SYNTREX Proxy starting")
	log.Printf("   Listen:  %s", cfg.Listen)
	log.Printf("   Target:  %s", cfg.Target)
	log.Printf("   SOC:     %s", cfg.SocURL)
	log.Printf("   Mode:    %s (%s)", cfg.Mode, failMode)
	log.Printf("")
	log.Printf("   Usage: set your OpenAI base_url to http://localhost%s", cfg.Listen)

	if err := http.ListenAndServe(cfg.Listen, handler); err != nil {
		log.Fatalf("Server error: %v", err)
	}
}
