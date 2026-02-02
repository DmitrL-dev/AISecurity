// Package mcpv1 provides backward compatibility with MCP v1 (stdio/JSON-RPC).
package mcpv1

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"os"
	"sync"

	"github.com/sentinel-community/gomcp/pkg/supervisor"
)

// JSONRPCRequest is an MCP v1 JSON-RPC request
type JSONRPCRequest struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      interface{}     `json:"id"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}

// JSONRPCResponse is an MCP v1 JSON-RPC response
type JSONRPCResponse struct {
	JSONRPC string        `json:"jsonrpc"`
	ID      interface{}   `json:"id"`
	Result  interface{}   `json:"result,omitempty"`
	Error   *JSONRPCError `json:"error,omitempty"`
}

// JSONRPCError represents a JSON-RPC error
type JSONRPCError struct {
	Code    int         `json:"code"`
	Message string      `json:"message"`
	Data    interface{} `json:"data,omitempty"`
}

// Adapter bridges stdio JSON-RPC to GoMCP supervisor
type Adapter struct {
	supervisor *supervisor.Supervisor
	stdin      io.Reader
	stdout     io.Writer
	mu         sync.Mutex
}

// NewAdapter creates a new MCP v1 adapter
func NewAdapter(sup *supervisor.Supervisor) *Adapter {
	return &Adapter{
		supervisor: sup,
		stdin:      os.Stdin,
		stdout:     os.Stdout,
	}
}

// Run starts the stdio adapter loop
func (a *Adapter) Run(ctx context.Context) error {
	scanner := bufio.NewScanner(a.stdin)

	for scanner.Scan() {
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}

		line := scanner.Bytes()
		if len(line) == 0 {
			continue
		}

		var req JSONRPCRequest
		if err := json.Unmarshal(line, &req); err != nil {
			a.sendError(nil, -32700, "Parse error", err.Error())
			continue
		}

		go a.handleRequest(&req)
	}

	return scanner.Err()
}

// handleRequest processes a single JSON-RPC request
func (a *Adapter) handleRequest(req *JSONRPCRequest) {
	switch req.Method {
	case "initialize":
		a.handleInitialize(req)
	case "tools/list":
		a.handleListTools(req)
	case "tools/call":
		a.handleCallTool(req)
	case "ping":
		a.sendResult(req.ID, map[string]interface{}{})
	default:
		a.sendError(req.ID, -32601, "Method not found", req.Method)
	}
}

// handleInitialize responds to MCP initialize
func (a *Adapter) handleInitialize(req *JSONRPCRequest) {
	result := map[string]interface{}{
		"protocolVersion": "2025-11-25",
		"serverInfo": map[string]interface{}{
			"name":    "gomcp",
			"version": "0.1.0",
		},
		"capabilities": map[string]interface{}{
			"tools": map[string]interface{}{},
		},
	}
	a.sendResult(req.ID, result)
}

// handleListTools returns available tools
func (a *Adapter) handleListTools(req *JSONRPCRequest) {
	tools := a.supervisor.ListTools()

	mcpTools := make([]map[string]interface{}, 0, len(tools))
	for _, t := range tools {
		mcpTools = append(mcpTools, map[string]interface{}{
			"name":        t.Name,
			"description": t.Description,
			"inputSchema": t.InputSchema,
		})
	}

	a.sendResult(req.ID, map[string]interface{}{"tools": mcpTools})
}

// handleCallTool executes a tool
func (a *Adapter) handleCallTool(req *JSONRPCRequest) {
	var params struct {
		Name      string          `json:"name"`
		Arguments json.RawMessage `json:"arguments"`
	}

	if err := json.Unmarshal(req.Params, &params); err != nil {
		a.sendError(req.ID, -32602, "Invalid params", err.Error())
		return
	}

	call := &supervisor.ToolCall{
		RequestID: fmt.Sprintf("%v", req.ID),
		ToolName:  params.Name,
		Arguments: params.Arguments,
	}

	result := a.supervisor.CallTool(context.Background(), call)

	if result.Error != nil {
		a.sendError(req.ID, int(result.Error.Code), result.Error.Message, result.Error.Details)
		return
	}

	a.sendResult(req.ID, map[string]interface{}{
		"content": []map[string]interface{}{
			{
				"type": "text",
				"text": string(result.Output),
			},
		},
	})
}

// sendResult sends a successful response
func (a *Adapter) sendResult(id interface{}, result interface{}) {
	a.send(&JSONRPCResponse{
		JSONRPC: "2.0",
		ID:      id,
		Result:  result,
	})
}

// sendError sends an error response
func (a *Adapter) sendError(id interface{}, code int, message, data string) {
	a.send(&JSONRPCResponse{
		JSONRPC: "2.0",
		ID:      id,
		Error: &JSONRPCError{
			Code:    code,
			Message: message,
			Data:    data,
		},
	})
}

// send writes a response to stdout
func (a *Adapter) send(resp *JSONRPCResponse) {
	a.mu.Lock()
	defer a.mu.Unlock()

	data, err := json.Marshal(resp)
	if err != nil {
		log.Printf("Failed to marshal response: %v", err)
		return
	}

	a.stdout.Write(data)
	a.stdout.Write([]byte("\n"))
}
