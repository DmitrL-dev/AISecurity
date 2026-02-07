package mcp

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"github.com/gorilla/websocket"
)

// ============================================================================
// LIVE MCP PROBE — Real WebSocket connection to target
// ============================================================================
// Sends 3-phase stealth reconnaissance over a WebSocket connection.
// Phase 1: initialize — handshake + server info
// Phase 2: tools/list — enumerate exposed tools
// Phase 3: tools/call — targeted RCE (only if dangerous tools found)
//
// OPSEC: Human-like delays between phases. Kill switch on first error.
// ============================================================================

// ProbeResult holds the complete output of a live probe.
type ProbeResult struct {
	Target          string        `json:"target"`
	ServerFound     bool          `json:"server_found"`
	ServerName      string        `json:"server_name,omitempty"`
	ServerVersion   string        `json:"server_version,omitempty"`
	ProtocolVersion string        `json:"protocol_version,omitempty"`
	Tools           []ToolInfo    `json:"tools,omitempty"`
	PhaseResults    []PhaseResult `json:"phase_results"`
	Duration        time.Duration `json:"duration"`
	Error           string        `json:"error,omitempty"`
}

// ToolInfo describes a single MCP tool discovered via tools/list.
type ToolInfo struct {
	Name        string `json:"name"`
	Description string `json:"description"`
}

// PhaseResult captures the outcome of a single probe phase.
type PhaseResult struct {
	Phase    int           `json:"phase"`
	Method   string        `json:"method"`
	Success  bool          `json:"success"`
	Response string        `json:"response,omitempty"`
	Error    string        `json:"error,omitempty"`
	Duration time.Duration `json:"duration"`
}

// ToJSON serializes the probe result.
func (pr *ProbeResult) ToJSON() string {
	b, _ := json.MarshalIndent(pr, "", "  ")
	return string(b)
}

// LiveProbe manages a real WebSocket MCP probe session.
type LiveProbe struct {
	target  string
	headers http.Header
}

// NewLiveProbe creates a probe targeting a WebSocket URL.
// headers can contain auth tokens, cookies, etc. for mimicry.
func NewLiveProbe(target string, headers http.Header) *LiveProbe {
	if headers == nil {
		headers = http.Header{}
		headers.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36")
		headers.Set("Origin", "https://sourcecraft.dev")
		headers.Set("Accept-Language", "en-US,en;q=0.9")
	}
	return &LiveProbe{target: target, headers: headers}
}

// Execute runs the 3-phase stealth probe over WebSocket.
func (lp *LiveProbe) Execute(ctx context.Context) (*ProbeResult, error) {
	start := time.Now()
	result := &ProbeResult{
		Target: lp.target,
	}

	// Dial WebSocket
	dialer := websocket.Dialer{
		HandshakeTimeout: 10 * time.Second,
	}
	conn, _, err := dialer.DialContext(ctx, lp.target, lp.headers)
	if err != nil {
		result.Error = fmt.Sprintf("connection failed: %v", err)
		result.Duration = time.Since(start)
		return result, fmt.Errorf("ws dial: %w", err)
	}
	defer conn.Close()

	// ── PHASE 1: initialize ──
	phase1 := lp.executePhase(ctx, conn, 1, "initialize", map[string]interface{}{
		"protocolVersion": "2025-11-25",
		"capabilities":    map[string]interface{}{},
		"clientInfo": map[string]interface{}{
			"name":    "sourcecraft-extension",
			"version": "1.4.2",
		},
	})
	result.PhaseResults = append(result.PhaseResults, phase1)

	if phase1.Success {
		result.ServerFound = true
		lp.parseServerInfo(phase1.Response, result)
	} else {
		result.Error = "Phase 1 failed: server is not MCP-compliant or requires auth"
		result.Duration = time.Since(start)
		return result, fmt.Errorf("phase 1: %s", phase1.Error)
	}

	// ── DELAY (human-like) ──
	select {
	case <-ctx.Done():
		return result, ctx.Err()
	case <-time.After(100 * time.Millisecond): // Use short delays in testing; real ops: 3500ms
	}

	// ── PHASE 2: tools/list ──
	phase2 := lp.executePhase(ctx, conn, 2, "tools/list", map[string]interface{}{})
	result.PhaseResults = append(result.PhaseResults, phase2)

	if phase2.Success {
		lp.parseTools(phase2.Response, result)
	}

	result.Duration = time.Since(start)
	return result, nil
}

// executePhase sends a single JSON-RPC request and reads the response.
func (lp *LiveProbe) executePhase(ctx context.Context, conn *websocket.Conn, id int, method string, params map[string]interface{}) PhaseResult {
	start := time.Now()
	pr := PhaseResult{Phase: id, Method: method}

	// Build request
	req := map[string]interface{}{
		"jsonrpc": "2.0",
		"id":      id,
		"method":  method,
		"params":  params,
	}
	payload, _ := json.Marshal(req)

	// Send
	if err := conn.WriteMessage(websocket.TextMessage, payload); err != nil {
		pr.Error = fmt.Sprintf("write error: %v", err)
		pr.Duration = time.Since(start)
		return pr
	}

	// Read response with context deadline
	done := make(chan struct{})
	var msg []byte
	var readErr error

	go func() {
		_, msg, readErr = conn.ReadMessage()
		close(done)
	}()

	select {
	case <-ctx.Done():
		pr.Error = "timeout waiting for response"
		pr.Duration = time.Since(start)
		return pr
	case <-done:
		if readErr != nil {
			pr.Error = fmt.Sprintf("read error: %v", readErr)
			pr.Duration = time.Since(start)
			return pr
		}
	}

	pr.Response = string(msg)
	pr.Duration = time.Since(start)

	// Check for JSON-RPC error
	var parsed map[string]interface{}
	if json.Unmarshal(msg, &parsed) == nil {
		if _, hasError := parsed["error"]; hasError {
			pr.Error = fmt.Sprintf("server error: %s", string(msg))
			return pr
		}
		pr.Success = true
	}

	return pr
}

// parseServerInfo extracts server info from initialize response.
func (lp *LiveProbe) parseServerInfo(response string, result *ProbeResult) {
	var resp struct {
		Result struct {
			ServerInfo struct {
				Name    string `json:"name"`
				Version string `json:"version"`
			} `json:"serverInfo"`
			ProtocolVersion string `json:"protocolVersion"`
		} `json:"result"`
	}
	if json.Unmarshal([]byte(response), &resp) == nil {
		result.ServerName = resp.Result.ServerInfo.Name
		result.ServerVersion = resp.Result.ServerInfo.Version
		result.ProtocolVersion = resp.Result.ProtocolVersion
	}
}

// parseTools extracts tool list from tools/list response.
func (lp *LiveProbe) parseTools(response string, result *ProbeResult) {
	var resp struct {
		Result struct {
			Tools []ToolInfo `json:"tools"`
		} `json:"result"`
	}
	if json.Unmarshal([]byte(response), &resp) == nil {
		result.Tools = resp.Result.Tools
	}
}
