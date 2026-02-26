// GoMCP v2 Smoke Test Client
// mcp-go v0.44.0 uses line-delimited JSON (one JSON object per line, no headers).
// Usage: go run smoke_test_client.go
package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

func main() {
	cwd, _ := os.Getwd()
	gomcpBin := filepath.Join(cwd, "gomcp.exe")
	rlmDir := os.Getenv("RLM_DIR")
	if rlmDir == "" {
		rlmDir = filepath.Join(cwd, "..", ".rlm")
	}
	bridgeScript := os.Getenv("BRIDGE_SCRIPT")
	if bridgeScript == "" {
		bridgeScript = filepath.Join(cwd, "scripts", "rlm_bridge.py")
	}

	// Check if bridge script exists to decide whether to test bridge tools
	hasBridge := false
	if _, err := os.Stat(bridgeScript); err == nil {
		hasBridge = true
	}

	fmt.Println("=== GoMCP v2 Smoke Test ===")
	fmt.Printf("Binary:  %s\n", gomcpBin)
	fmt.Printf("RLM dir: %s\n", rlmDir)
	fmt.Printf("Bridge:  %s (available=%v)\n\n", bridgeScript, hasBridge)

	args := []string{"-rlm-dir", rlmDir}
	if hasBridge {
		args = append(args, "-bridge-script", bridgeScript)
	}
	cmd := exec.Command(gomcpBin, args...)
	stdin, _ := cmd.StdinPipe()
	stdout, _ := cmd.StdoutPipe()
	cmd.Stderr = os.Stderr

	if err := cmd.Start(); err != nil {
		fmt.Fprintf(os.Stderr, "start: %v\n", err)
		os.Exit(1)
	}

	scanner := bufio.NewScanner(stdout)
	scanner.Buffer(make([]byte, 0, 4*1024*1024), 4*1024*1024)

	passed, failed := 0, 0

	type testCase struct {
		Label   string
		Msg     map[string]interface{}
		HasResp bool
	}

	tests := []testCase{
		{"initialize", map[string]interface{}{
			"jsonrpc": "2.0", "id": 1, "method": "initialize",
			"params": map[string]interface{}{
				"protocolVersion": "2024-11-05",
				"capabilities":    map[string]interface{}{},
				"clientInfo":      map[string]interface{}{"name": "smoke-test", "version": "1.0"},
			},
		}, true},
		{"initialized", map[string]interface{}{
			"jsonrpc": "2.0", "method": "notifications/initialized",
		}, false},
		{"tools/list", map[string]interface{}{
			"jsonrpc": "2.0", "id": 2, "method": "tools/list",
		}, true},
		{"health", map[string]interface{}{
			"jsonrpc": "2.0", "id": 3, "method": "tools/call",
			"params": map[string]interface{}{"name": "health", "arguments": map[string]interface{}{}},
		}, true},
		{"version", map[string]interface{}{
			"jsonrpc": "2.0", "id": 4, "method": "tools/call",
			"params": map[string]interface{}{"name": "version", "arguments": map[string]interface{}{}},
		}, true},
		{"fact_stats", map[string]interface{}{
			"jsonrpc": "2.0", "id": 5, "method": "tools/call",
			"params": map[string]interface{}{"name": "fact_stats", "arguments": map[string]interface{}{}},
		}, true},
		{"get_l0_facts", map[string]interface{}{
			"jsonrpc": "2.0", "id": 6, "method": "tools/call",
			"params": map[string]interface{}{"name": "get_l0_facts", "arguments": map[string]interface{}{}},
		}, true},
		{"search_facts(architecture)", map[string]interface{}{
			"jsonrpc": "2.0", "id": 7, "method": "tools/call",
			"params": map[string]interface{}{"name": "search_facts", "arguments": map[string]interface{}{"query": "architecture", "limit": 3}},
		}, true},
		{"list_domains", map[string]interface{}{
			"jsonrpc": "2.0", "id": 8, "method": "tools/call",
			"params": map[string]interface{}{"name": "list_domains", "arguments": map[string]interface{}{}},
		}, true},
		{"add_fact", map[string]interface{}{
			"jsonrpc": "2.0", "id": 9, "method": "tools/call",
			"params": map[string]interface{}{"name": "add_fact", "arguments": map[string]interface{}{
				"content": "GoMCP v2 smoke test passed at " + time.Now().Format(time.RFC3339),
				"level":   3, "domain": "testing", "module": "smoke-test",
			}},
		}, true},
		{"dashboard", map[string]interface{}{
			"jsonrpc": "2.0", "id": 10, "method": "tools/call",
			"params": map[string]interface{}{"name": "dashboard", "arguments": map[string]interface{}{}},
		}, true},
	}

	// Add Python bridge tests if bridge is available
	if hasBridge {
		bridgeTests := []testCase{
			{"check_python_bridge", map[string]interface{}{
				"jsonrpc": "2.0", "id": 11, "method": "tools/call",
				"params": map[string]interface{}{"name": "check_python_bridge", "arguments": map[string]interface{}{}},
			}, true},
			{"route_context", map[string]interface{}{
				"jsonrpc": "2.0", "id": 12, "method": "tools/call",
				"params": map[string]interface{}{"name": "route_context", "arguments": map[string]interface{}{"query": "find architecture decisions"}},
			}, true},
			{"enterprise_context", map[string]interface{}{
				"jsonrpc": "2.0", "id": 13, "method": "tools/call",
				"params": map[string]interface{}{"name": "enterprise_context", "arguments": map[string]interface{}{"max_tokens": 200}},
			}, true},
			{"semantic_search", map[string]interface{}{
				"jsonrpc": "2.0", "id": 14, "method": "tools/call",
				"params": map[string]interface{}{"name": "semantic_search", "arguments": map[string]interface{}{"query": "GoMCP architecture", "limit": 3}},
			}, true},
			{"compute_embedding", map[string]interface{}{
				"jsonrpc": "2.0", "id": 15, "method": "tools/call",
				"params": map[string]interface{}{"name": "compute_embedding", "arguments": map[string]interface{}{"text": "test embedding"}},
			}, true},
		}
		tests = append(tests, bridgeTests...)
	}

	for _, tc := range tests {
		body, _ := json.Marshal(tc.Msg)
		fmt.Printf(">> %-30s ", tc.Label)

		// Send: one line of JSON + newline (line-delimited protocol)
		if _, err := fmt.Fprintf(stdin, "%s\n", body); err != nil {
			fmt.Printf("FAIL (write: %v)\n", err)
			failed++
			continue
		}

		if !tc.HasResp {
			fmt.Println("(notification)")
			time.Sleep(100 * time.Millisecond)
			continue
		}

		// Read: one line of JSON
		if !scanner.Scan() {
			fmt.Printf("FAIL (no response: %v)\n", scanner.Err())
			failed++
			continue
		}
		line := scanner.Text()

		var parsed map[string]interface{}
		if err := json.Unmarshal([]byte(line), &parsed); err != nil {
			fmt.Printf("FAIL (parse: %v)\n", err)
			failed++
			continue
		}

		if errObj, ok := parsed["error"]; ok {
			fmt.Printf("FAIL: %v\n", errObj)
			failed++
			continue
		}

		// Special check: verify boot instructions in initialize response
		if tc.Label == "initialize" {
			if result, ok := parsed["result"].(map[string]interface{}); ok {
				if instructions, ok := result["instructions"].(string); ok && instructions != "" {
					fmt.Printf("OK\n")
					fmt.Printf("   Boot instructions: %d chars\n", len(instructions))
					hasAgent := strings.Contains(instructions, "[AGENT INSTRUCTIONS]")
					hasFacts := strings.Contains(instructions, "[PROJECT FACTS]")
					hasSession := strings.Contains(instructions, "[LAST SESSION]")
					fmt.Printf("   [AGENT INSTRUCTIONS]: %v\n", hasAgent)
					fmt.Printf("   [PROJECT FACTS]:      %v\n", hasFacts)
					fmt.Printf("   [LAST SESSION]:       %v\n", hasSession)
					if !hasAgent {
						fmt.Println("   WARNING: missing [AGENT INSTRUCTIONS] block")
					}
					passed++
					continue
				}
			}
			fmt.Printf("WARN: no boot instructions in initialize response\n")
			passed++ // still pass — instructions are optional if no L0 facts
			continue
		}

		display := line
		if len(display) > 200 {
			display = display[:200] + "..."
		}
		fmt.Printf("OK\n   %s\n", display)
		passed++
	}

	stdin.Close()
	cmd.Wait()

	fmt.Printf("\n=== Results: %d passed, %d failed ===\n", passed, failed)
	if failed > 0 {
		os.Exit(1)
	}
}
