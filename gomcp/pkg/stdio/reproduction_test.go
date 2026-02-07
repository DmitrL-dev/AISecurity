package stdio

import (
	"bytes"
	"context"
	"encoding/json"
	"strings"
	"testing"
	"time"
)

// reproduction_test.go simulates the "Shared Client ID" attack.
// It verifies that the server currently ACCEPTS connections without client info
// or with compromised client IDs (which we want to BLOCK).

func TestExploit_SharedClientId(t *testing.T) {
	// 1. Simulate a malicious connection using the shared "mcp-proxy" ID
	// which is known to be vulnerable to one-click account takeover.
	payload := `
	{
		"jsonrpc": "2.0",
		"id": "exploit-1",
		"method": "initialize",
		"params": {
			"protocolVersion": "2024-11-05",
			"capabilities": {},
			"clientInfo": {
				"name": "mcp-proxy",
				"version": "1.0.0"
			}
		}
	}`

	reader := strings.NewReader(payload)
	var output bytes.Buffer

	a := NewAdapter(Config{
		Reader: reader,
		Writer: &output,
	})

	ctx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
	defer cancel()

	// Run adapter (blocks until context timeout or done)
	go a.Run(ctx)

	// Wait a bit for processing
	time.Sleep(10 * time.Millisecond)

	// Verify response
	var resp Response
	if err := json.Unmarshal(output.Bytes(), &resp); err != nil {
		t.Fatalf("failed to unmarshal response: %v", err)
	}

	// 2. ASSERT PASS: The server should BLOCK the request.
	if resp.Error == nil {
		t.Fatalf("Security Regression: Malicious client ID '%s' was ACCEPTED!", "mcp-proxy")
	}

	if !strings.Contains(resp.Error.Message, "blocked by security policy") {
		t.Errorf("Unexpected error message: %s", resp.Error.Message)
	}

	t.Logf("Security Success: Malicious client blocked as expected.")
}

func TestExploit_MissingClientInfo(t *testing.T) {
	// Simulate old/lazy client without clientInfo
	payload := `
	{
		"jsonrpc": "2.0",
		"id": "exploit-2",
		"method": "initialize",
		"params": {
			"protocolVersion": "2024-11-05",
			"capabilities": {}
		}
	}`

	reader := strings.NewReader(payload)
	var output bytes.Buffer

	a := NewAdapter(Config{
		Reader: reader,
		Writer: &output,
	})

	ctx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
	defer cancel()
	go a.Run(ctx)
	time.Sleep(10 * time.Millisecond)

	var resp Response
	json.Unmarshal(output.Bytes(), &resp)

	if resp.Error == nil {
		t.Fatalf("Security Regression: Anonymous client was ACCEPTED in strict mode!")
	}
	// Check for "client name is required" message
	if !strings.Contains(resp.Error.Message, "client name is required") {
		t.Errorf("Unexpected error message: %s", resp.Error.Message)
	}
	t.Logf("Security Success: Anonymous client blocked.")
}
