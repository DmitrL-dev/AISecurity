package client

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"
	"sync"
	"sync/atomic"
)

// StdioClient communicates with MCP server via stdio
type StdioClient struct {
	*BaseClient

	cmd    *exec.Cmd
	stdin  io.WriteCloser
	stdout io.ReadCloser
	stderr io.ReadCloser

	requestID int64
	pending   map[int64]chan *jsonRPCResponse
	pendingMu sync.Mutex

	done chan struct{}
}

// StdioConfig configures stdio client
type StdioConfig struct {
	ClientConfig

	// Command to run MCP server
	Command string
	Args    []string

	// Working directory
	WorkDir string

	// Environment variables
	Env []string
}

// NewStdioClient creates a new stdio client
func NewStdioClient(cfg StdioConfig) *StdioClient {
	if cfg.ClientConfig.Name == "" {
		cfg.ClientConfig = DefaultConfig()
	}

	return &StdioClient{
		BaseClient: NewBaseClient(cfg.ClientConfig),
		pending:    make(map[int64]chan *jsonRPCResponse),
		done:       make(chan struct{}),
	}
}

// Connect starts the server process and initializes connection
func (c *StdioClient) Connect(ctx context.Context) error {
	if c.IsConnected() {
		return ErrAlreadyConnected
	}

	// Start server process
	cmd := exec.CommandContext(ctx, c.config.Name, c.config.Version)

	stdin, err := cmd.StdinPipe()
	if err != nil {
		return fmt.Errorf("failed to create stdin pipe: %w", err)
	}

	stdout, err := cmd.StdoutPipe()
	if err != nil {
		stdin.Close()
		return fmt.Errorf("failed to create stdout pipe: %w", err)
	}

	stderr, err := cmd.StderrPipe()
	if err != nil {
		stdin.Close()
		stdout.Close()
		return fmt.Errorf("failed to create stderr pipe: %w", err)
	}

	if err := cmd.Start(); err != nil {
		stdin.Close()
		stdout.Close()
		stderr.Close()
		return fmt.Errorf("failed to start server: %w", err)
	}

	c.cmd = cmd
	c.stdin = stdin
	c.stdout = stdout
	c.stderr = stderr

	// Start reading responses
	go c.readLoop()
	go c.stderrLoop()

	// Initialize connection
	info, caps, err := c.initialize(ctx)
	if err != nil {
		c.Close()
		return fmt.Errorf("initialization failed: %w", err)
	}

	c.setConnected(true, info, caps)
	return nil
}

// Close stops the server process
func (c *StdioClient) Close() error {
	if !c.IsConnected() {
		return nil
	}

	close(c.done)

	// Send shutdown notification
	c.sendNotification("notifications/exit", nil)

	c.stdin.Close()
	c.stdout.Close()
	c.stderr.Close()

	if c.cmd != nil && c.cmd.Process != nil {
		c.cmd.Process.Kill()
		c.cmd.Wait()
	}

	c.setConnected(false, nil, nil)
	return nil
}

// initialize sends initialize request
func (c *StdioClient) initialize(ctx context.Context) (*ServerInfo, *ServerCapabilities, error) {
	params := map[string]any{
		"protocolVersion": "2025-11-25",
		"capabilities":    c.config.Capabilities,
		"clientInfo": map[string]string{
			"name":    c.config.Name,
			"version": c.config.Version,
		},
	}

	result, err := c.call(ctx, "initialize", params)
	if err != nil {
		return nil, nil, err
	}

	var resp struct {
		ProtocolVersion string             `json:"protocolVersion"`
		ServerInfo      ServerInfo         `json:"serverInfo"`
		Capabilities    ServerCapabilities `json:"capabilities"`
	}

	if err := json.Unmarshal(result, &resp); err != nil {
		return nil, nil, fmt.Errorf("failed to parse initialize response: %w", err)
	}

	// Send initialized notification
	c.sendNotification("notifications/initialized", nil)

	return &resp.ServerInfo, &resp.Capabilities, nil
}

// ListTools returns available tools
func (c *StdioClient) ListTools(ctx context.Context) ([]Tool, error) {
	if !c.IsConnected() {
		return nil, ErrNotConnected
	}

	result, err := c.call(ctx, "tools/list", nil)
	if err != nil {
		return nil, err
	}

	var resp struct {
		Tools []Tool `json:"tools"`
	}

	if err := json.Unmarshal(result, &resp); err != nil {
		return nil, fmt.Errorf("failed to parse tools response: %w", err)
	}

	return resp.Tools, nil
}

// CallTool invokes a tool
func (c *StdioClient) CallTool(ctx context.Context, name string, args map[string]any) (*ToolResult, error) {
	if !c.IsConnected() {
		return nil, ErrNotConnected
	}

	params := map[string]any{
		"name":      name,
		"arguments": args,
	}

	result, err := c.call(ctx, "tools/call", params)
	if err != nil {
		return nil, err
	}

	var resp ToolResult
	if err := json.Unmarshal(result, &resp); err != nil {
		return nil, fmt.Errorf("failed to parse tool result: %w", err)
	}

	return &resp, nil
}

// ListResources returns available resources
func (c *StdioClient) ListResources(ctx context.Context) ([]Resource, error) {
	if !c.IsConnected() {
		return nil, ErrNotConnected
	}

	result, err := c.call(ctx, "resources/list", nil)
	if err != nil {
		return nil, err
	}

	var resp struct {
		Resources []Resource `json:"resources"`
	}

	if err := json.Unmarshal(result, &resp); err != nil {
		return nil, fmt.Errorf("failed to parse resources response: %w", err)
	}

	return resp.Resources, nil
}

// ReadResource reads a resource
func (c *StdioClient) ReadResource(ctx context.Context, uri string) (*ResourceContent, error) {
	if !c.IsConnected() {
		return nil, ErrNotConnected
	}

	params := map[string]any{
		"uri": uri,
	}

	result, err := c.call(ctx, "resources/read", params)
	if err != nil {
		return nil, err
	}

	var resp struct {
		Contents []ResourceContent `json:"contents"`
	}

	if err := json.Unmarshal(result, &resp); err != nil {
		return nil, fmt.Errorf("failed to parse resource content: %w", err)
	}

	if len(resp.Contents) == 0 {
		return nil, ErrResourceNotFound
	}

	return &resp.Contents[0], nil
}

// ListPrompts returns available prompts
func (c *StdioClient) ListPrompts(ctx context.Context) ([]Prompt, error) {
	if !c.IsConnected() {
		return nil, ErrNotConnected
	}

	result, err := c.call(ctx, "prompts/list", nil)
	if err != nil {
		return nil, err
	}

	var resp struct {
		Prompts []Prompt `json:"prompts"`
	}

	if err := json.Unmarshal(result, &resp); err != nil {
		return nil, fmt.Errorf("failed to parse prompts response: %w", err)
	}

	return resp.Prompts, nil
}

// GetPrompt gets a specific prompt
func (c *StdioClient) GetPrompt(ctx context.Context, name string, args map[string]string) (*PromptResult, error) {
	if !c.IsConnected() {
		return nil, ErrNotConnected
	}

	params := map[string]any{
		"name":      name,
		"arguments": args,
	}

	result, err := c.call(ctx, "prompts/get", params)
	if err != nil {
		return nil, err
	}

	var resp PromptResult
	if err := json.Unmarshal(result, &resp); err != nil {
		return nil, fmt.Errorf("failed to parse prompt result: %w", err)
	}

	return &resp, nil
}

// CreateSample requests LLM sampling
func (c *StdioClient) CreateSample(ctx context.Context, req *SamplingRequest) (*SamplingResponse, error) {
	if !c.IsConnected() {
		return nil, ErrNotConnected
	}

	result, err := c.call(ctx, "sampling/createMessage", req)
	if err != nil {
		return nil, err
	}

	var resp SamplingResponse
	if err := json.Unmarshal(result, &resp); err != nil {
		return nil, fmt.Errorf("failed to parse sampling response: %w", err)
	}

	return &resp, nil
}

// call sends a JSON-RPC request and waits for response
func (c *StdioClient) call(ctx context.Context, method string, params any) (json.RawMessage, error) {
	id := atomic.AddInt64(&c.requestID, 1)

	req := jsonRPCRequest{
		JSONRPC: "2.0",
		ID:      id,
		Method:  method,
		Params:  params,
	}

	// Register pending request
	respCh := make(chan *jsonRPCResponse, 1)
	c.pendingMu.Lock()
	c.pending[id] = respCh
	c.pendingMu.Unlock()

	defer func() {
		c.pendingMu.Lock()
		delete(c.pending, id)
		c.pendingMu.Unlock()
	}()

	// Send request
	data, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	data = append(data, '\n')
	if _, err := c.stdin.Write(data); err != nil {
		return nil, fmt.Errorf("failed to write request: %w", err)
	}

	// Wait for response
	select {
	case resp := <-respCh:
		if resp.Error != nil {
			return nil, resp.Error
		}
		return resp.Result, nil
	case <-ctx.Done():
		return nil, ctx.Err()
	case <-c.done:
		return nil, ErrNotConnected
	}
}

// sendNotification sends a notification (no response expected)
func (c *StdioClient) sendNotification(method string, params any) error {
	req := jsonRPCRequest{
		JSONRPC: "2.0",
		ID:      0,
		Method:  method,
		Params:  params,
	}

	data, err := json.Marshal(req)
	if err != nil {
		return err
	}

	data = append(data, '\n')
	_, err = c.stdin.Write(data)
	return err
}

// readLoop reads responses from stdout
func (c *StdioClient) readLoop() {
	scanner := bufio.NewScanner(c.stdout)
	scanner.Buffer(make([]byte, 1024*1024), 1024*1024) // 1MB buffer

	for scanner.Scan() {
		select {
		case <-c.done:
			return
		default:
		}

		line := scanner.Bytes()
		if len(line) == 0 {
			continue
		}

		var msg struct {
			JSONRPC string          `json:"jsonrpc"`
			ID      *int64          `json:"id,omitempty"`
			Method  string          `json:"method,omitempty"`
			Params  json.RawMessage `json:"params,omitempty"`
			Result  json.RawMessage `json:"result,omitempty"`
			Error   *jsonRPCError   `json:"error,omitempty"`
		}

		if err := json.Unmarshal(line, &msg); err != nil {
			continue
		}

		// Check if notification
		if msg.ID == nil || *msg.ID == 0 {
			c.notifyHandlers(msg.Method, msg.Params)
			continue
		}

		// Find pending request
		c.pendingMu.Lock()
		respCh, ok := c.pending[*msg.ID]
		c.pendingMu.Unlock()

		if ok {
			respCh <- &jsonRPCResponse{
				JSONRPC: msg.JSONRPC,
				ID:      *msg.ID,
				Result:  msg.Result,
				Error:   msg.Error,
			}
		}
	}
}

// stderrLoop reads stderr for logging
func (c *StdioClient) stderrLoop() {
	scanner := bufio.NewScanner(c.stderr)
	for scanner.Scan() {
		select {
		case <-c.done:
			return
		default:
		}
		// Log stderr output
		fmt.Fprintf(os.Stderr, "[MCP Server] %s\n", scanner.Text())
	}
}
