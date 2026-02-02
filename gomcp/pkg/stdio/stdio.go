// Package stdio provides a stdio-based MCP v1 compatible adapter.
package stdio

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"sync"
	"time"
)

// Message types for MCP v1 protocol
const (
	MessageTypeRequest  = "request"
	MessageTypeResponse = "response"
	MessageTypeNotify   = "notify"
)

// Request is the MCP v1 request format
type Request struct {
	ID      string          `json:"id"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
	JSONRPC string          `json:"jsonrpc"`
}

// Response is the MCP v1 response format
type Response struct {
	ID      string          `json:"id"`
	Result  json.RawMessage `json:"result,omitempty"`
	Error   *ResponseError  `json:"error,omitempty"`
	JSONRPC string          `json:"jsonrpc"`
}

// ResponseError for JSON-RPC errors
type ResponseError struct {
	Code    int             `json:"code"`
	Message string          `json:"message"`
	Data    json.RawMessage `json:"data,omitempty"`
}

// Standard JSON-RPC error codes
const (
	CodeParseError     = -32700
	CodeInvalidRequest = -32600
	CodeMethodNotFound = -32601
	CodeInvalidParams  = -32602
	CodeInternalError  = -32603
)

// ToolsListResult for tools/list response
type ToolsListResult struct {
	Tools []ToolDefinition `json:"tools"`
}

// ToolDefinition describes a tool
type ToolDefinition struct {
	Name        string          `json:"name"`
	Description string          `json:"description,omitempty"`
	InputSchema json.RawMessage `json:"inputSchema,omitempty"`
}

// ToolCallParams for tools/call request
type ToolCallParams struct {
	Name      string          `json:"name"`
	Arguments json.RawMessage `json:"arguments,omitempty"`
}

// ToolCallResult for tools/call response
type ToolCallResult struct {
	Content []ContentItem `json:"content"`
	IsError bool          `json:"isError,omitempty"`
}

// ContentItem in tool results
type ContentItem struct {
	Type string `json:"type"`
	Text string `json:"text,omitempty"`
}

// ToolHandler is the interface for tool execution
type ToolHandler interface {
	ListTools() []ToolDefinition
	CallTool(ctx context.Context, name string, args json.RawMessage) (json.RawMessage, error)
}

// Adapter handles stdio communication
type Adapter struct {
	handler ToolHandler
	reader  *bufio.Reader
	writer  io.Writer
	mu      sync.Mutex

	// Configuration
	serverName    string
	serverVersion string

	// State
	running bool
	done    chan struct{}
}

// Config for the stdio adapter
type Config struct {
	Handler       ToolHandler
	Reader        io.Reader
	Writer        io.Writer
	ServerName    string
	ServerVersion string
}

// NewAdapter creates a new stdio adapter
func NewAdapter(cfg Config) *Adapter {
	reader := cfg.Reader
	if reader == nil {
		reader = os.Stdin
	}
	writer := cfg.Writer
	if writer == nil {
		writer = os.Stdout
	}

	name := cfg.ServerName
	if name == "" {
		name = "gomcp"
	}
	version := cfg.ServerVersion
	if version == "" {
		version = "1.0.0"
	}

	return &Adapter{
		handler:       cfg.Handler,
		reader:        bufio.NewReader(reader),
		writer:        writer,
		serverName:    name,
		serverVersion: version,
		done:          make(chan struct{}),
	}
}

// Run starts the adapter and blocks until stopped
func (a *Adapter) Run(ctx context.Context) error {
	a.running = true
	defer func() { a.running = false }()

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-a.done:
			return nil
		default:
			if err := a.processOne(); err != nil {
				if err == io.EOF {
					return nil
				}
				// Log error but continue
				continue
			}
		}
	}
}

// Stop stops the adapter
func (a *Adapter) Stop() {
	select {
	case <-a.done:
		// Already closed
	default:
		close(a.done)
	}
}

// IsRunning returns whether the adapter is running
func (a *Adapter) IsRunning() bool {
	return a.running
}

func (a *Adapter) processOne() error {
	line, err := a.reader.ReadBytes('\n')
	if err != nil {
		return err
	}

	var req Request
	if err := json.Unmarshal(line, &req); err != nil {
		a.sendError("", CodeParseError, "Parse error", nil)
		return nil
	}

	if req.JSONRPC != "2.0" {
		a.sendError(req.ID, CodeInvalidRequest, "Invalid JSON-RPC version", nil)
		return nil
	}

	resp := a.handleRequest(&req)
	return a.sendResponse(resp)
}

func (a *Adapter) handleRequest(req *Request) *Response {
	switch req.Method {
	case "initialize":
		return a.handleInitialize(req)
	case "tools/list":
		return a.handleToolsList(req)
	case "tools/call":
		return a.handleToolsCall(req)
	case "ping":
		return a.handlePing(req)
	case "shutdown":
		return a.handleShutdown(req)
	default:
		return &Response{
			ID:      req.ID,
			JSONRPC: "2.0",
			Error: &ResponseError{
				Code:    CodeMethodNotFound,
				Message: fmt.Sprintf("Method not found: %s", req.Method),
			},
		}
	}
}

func (a *Adapter) handleInitialize(req *Request) *Response {
	result := map[string]interface{}{
		"protocolVersion": "2025-11-25",
		"serverInfo": map[string]string{
			"name":    a.serverName,
			"version": a.serverVersion,
		},
		"capabilities": map[string]interface{}{
			"tools": map[string]bool{
				"listChanged": false,
			},
		},
	}

	data, _ := json.Marshal(result)
	return &Response{
		ID:      req.ID,
		JSONRPC: "2.0",
		Result:  data,
	}
}

func (a *Adapter) handleToolsList(req *Request) *Response {
	var tools []ToolDefinition

	if a.handler != nil {
		tools = a.handler.ListTools()
	}

	if tools == nil {
		tools = []ToolDefinition{}
	}

	result := ToolsListResult{Tools: tools}
	data, _ := json.Marshal(result)
	return &Response{
		ID:      req.ID,
		JSONRPC: "2.0",
		Result:  data,
	}
}

func (a *Adapter) handleToolsCall(req *Request) *Response {
	var params ToolCallParams
	if err := json.Unmarshal(req.Params, &params); err != nil {
		return &Response{
			ID:      req.ID,
			JSONRPC: "2.0",
			Error: &ResponseError{
				Code:    CodeInvalidParams,
				Message: "Invalid params: " + err.Error(),
			},
		}
	}

	if a.handler == nil {
		return &Response{
			ID:      req.ID,
			JSONRPC: "2.0",
			Error: &ResponseError{
				Code:    CodeInternalError,
				Message: "No handler configured",
			},
		}
	}

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	result, err := a.handler.CallTool(ctx, params.Name, params.Arguments)
	if err != nil {
		errorResult := ToolCallResult{
			Content: []ContentItem{{Type: "text", Text: err.Error()}},
			IsError: true,
		}
		data, _ := json.Marshal(errorResult)
		return &Response{
			ID:      req.ID,
			JSONRPC: "2.0",
			Result:  data,
		}
	}

	successResult := ToolCallResult{
		Content: []ContentItem{{Type: "text", Text: string(result)}},
	}
	data, _ := json.Marshal(successResult)
	return &Response{
		ID:      req.ID,
		JSONRPC: "2.0",
		Result:  data,
	}
}

func (a *Adapter) handlePing(req *Request) *Response {
	result, _ := json.Marshal(map[string]string{"status": "pong"})
	return &Response{
		ID:      req.ID,
		JSONRPC: "2.0",
		Result:  result,
	}
}

func (a *Adapter) handleShutdown(req *Request) *Response {
	go func() {
		time.Sleep(100 * time.Millisecond)
		a.Stop()
	}()
	result, _ := json.Marshal(map[string]bool{"success": true})
	return &Response{
		ID:      req.ID,
		JSONRPC: "2.0",
		Result:  result,
	}
}

func (a *Adapter) sendResponse(resp *Response) error {
	a.mu.Lock()
	defer a.mu.Unlock()

	data, err := json.Marshal(resp)
	if err != nil {
		return err
	}

	_, err = fmt.Fprintf(a.writer, "%s\n", data)
	return err
}

func (a *Adapter) sendError(id string, code int, message string, data json.RawMessage) error {
	return a.sendResponse(&Response{
		ID:      id,
		JSONRPC: "2.0",
		Error: &ResponseError{
			Code:    code,
			Message: message,
			Data:    data,
		},
	})
}
