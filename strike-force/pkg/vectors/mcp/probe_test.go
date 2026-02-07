package mcp

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/gorilla/websocket"
)

// ============================================================================
// TDD: Live WebSocket MCP Probe Tests
// ============================================================================

// mockMCPServer creates a test WebSocket server that responds to MCP requests.
func mockMCPServer(t *testing.T, responses map[string]string) *httptest.Server {
	t.Helper()
	upgrader := websocket.Upgrader{CheckOrigin: func(r *http.Request) bool { return true }}

	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			t.Logf("upgrade error: %v", err)
			return
		}
		defer conn.Close()

		for {
			_, msg, err := conn.ReadMessage()
			if err != nil {
				return
			}

			var req map[string]interface{}
			json.Unmarshal(msg, &req)
			method, _ := req["method"].(string)
			id := req["id"]

			if resp, ok := responses[method]; ok {
				reply := fmt.Sprintf(`{"jsonrpc":"2.0","id":%v,"result":%s}`, id, resp)
				conn.WriteMessage(websocket.TextMessage, []byte(reply))
			} else {
				reply := fmt.Sprintf(`{"jsonrpc":"2.0","id":%v,"error":{"code":-32601,"message":"method not found"}}`, id)
				conn.WriteMessage(websocket.TextMessage, []byte(reply))
			}
		}
	}))
}

func TestLiveProbe_ConnectsToWebSocket(t *testing.T) {
	srv := mockMCPServer(t, map[string]string{
		"initialize": `{"serverInfo":{"name":"test-server","version":"0.1.0"},"protocolVersion":"2025-11-25"}`,
		"tools/list": `{"tools":[]}`,
	})
	defer srv.Close()

	wsURL := "ws" + strings.TrimPrefix(srv.URL, "http")
	probe := NewLiveProbe(wsURL, nil)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	result, err := probe.Execute(ctx)
	if err != nil {
		t.Fatalf("probe failed: %v", err)
	}
	if result == nil {
		t.Fatal("result is nil")
	}
}

func TestLiveProbe_Phase1_GetsServerInfo(t *testing.T) {
	srv := mockMCPServer(t, map[string]string{
		"initialize": `{"serverInfo":{"name":"sourcecraft-agent","version":"2.1.0"},"protocolVersion":"2025-11-25"}`,
		"tools/list": `{"tools":[]}`,
	})
	defer srv.Close()

	wsURL := "ws" + strings.TrimPrefix(srv.URL, "http")
	probe := NewLiveProbe(wsURL, nil)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	result, err := probe.Execute(ctx)
	if err != nil {
		t.Fatalf("probe failed: %v", err)
	}

	if !result.ServerFound {
		t.Error("expected ServerFound=true")
	}
	if result.ServerName != "sourcecraft-agent" {
		t.Errorf("expected server name 'sourcecraft-agent', got '%s'", result.ServerName)
	}
	if result.ProtocolVersion != "2025-11-25" {
		t.Errorf("expected protocol '2025-11-25', got '%s'", result.ProtocolVersion)
	}
}

func TestLiveProbe_Phase2_EnumeratesTools(t *testing.T) {
	srv := mockMCPServer(t, map[string]string{
		"initialize": `{"serverInfo":{"name":"test","version":"1.0"},"protocolVersion":"2025-11-25"}`,
		"tools/list": `{"tools":[{"name":"execute_command","description":"Run shell commands"},{"name":"read_file","description":"Read a file"}]}`,
	})
	defer srv.Close()

	wsURL := "ws" + strings.TrimPrefix(srv.URL, "http")
	probe := NewLiveProbe(wsURL, nil)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	result, err := probe.Execute(ctx)
	if err != nil {
		t.Fatalf("probe failed: %v", err)
	}

	if len(result.Tools) != 2 {
		t.Fatalf("expected 2 tools, got %d", len(result.Tools))
	}
	if result.Tools[0].Name != "execute_command" {
		t.Errorf("expected first tool 'execute_command', got '%s'", result.Tools[0].Name)
	}
}

func TestLiveProbe_Phase2_EmptyTools(t *testing.T) {
	srv := mockMCPServer(t, map[string]string{
		"initialize": `{"serverInfo":{"name":"test","version":"1.0"},"protocolVersion":"2025-11-25"}`,
		"tools/list": `{"tools":[]}`,
	})
	defer srv.Close()

	wsURL := "ws" + strings.TrimPrefix(srv.URL, "http")
	probe := NewLiveProbe(wsURL, nil)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	result, err := probe.Execute(ctx)
	if err != nil {
		t.Fatalf("probe failed: %v", err)
	}

	if len(result.Tools) != 0 {
		t.Errorf("expected 0 tools, got %d", len(result.Tools))
	}
}

func TestLiveProbe_TimeoutHandling(t *testing.T) {
	// Server that never responds
	upgrader := websocket.Upgrader{CheckOrigin: func(r *http.Request) bool { return true }}
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			return
		}
		defer conn.Close()
		// Read but never respond
		for {
			_, _, err := conn.ReadMessage()
			if err != nil {
				return
			}
		}
	}))
	defer srv.Close()

	wsURL := "ws" + strings.TrimPrefix(srv.URL, "http")
	probe := NewLiveProbe(wsURL, nil)

	ctx, cancel := context.WithTimeout(context.Background(), 1*time.Second)
	defer cancel()

	_, err := probe.Execute(ctx)
	if err == nil {
		t.Error("expected timeout error, got nil")
	}
}

func TestLiveProbe_ConnectionRefused(t *testing.T) {
	probe := NewLiveProbe("ws://127.0.0.1:1", nil) // port 1 = guaranteed refused

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	_, err := probe.Execute(ctx)
	if err == nil {
		t.Error("expected connection error, got nil")
	}
}

func TestProbeResult_ToJSON(t *testing.T) {
	result := &ProbeResult{
		Target:          "wss://target.dev",
		ServerFound:     true,
		ServerName:      "test",
		ProtocolVersion: "2025-11-25",
		Tools: []ToolInfo{
			{Name: "exec", Description: "run stuff"},
		},
		PhaseResults: []PhaseResult{
			{Phase: 1, Method: "initialize", Success: true},
		},
	}

	j := result.ToJSON()
	if !strings.Contains(j, "test") {
		t.Error("JSON missing server name")
	}
}
