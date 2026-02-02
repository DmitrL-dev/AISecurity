package client

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"sync/atomic"
	"time"
)

// HTTPClient communicates with MCP server via HTTP REST API
type HTTPClient struct {
	*BaseClient

	baseURL    string
	httpClient *http.Client
	requestID  int64

	// Auth
	authToken string
	tenantID  string
}

// HTTPConfig configures HTTP client
type HTTPConfig struct {
	ClientConfig

	// Server URL
	BaseURL string

	// Auth token (JWT)
	AuthToken string

	// Tenant ID for multi-tenancy
	TenantID string

	// TLS settings
	InsecureSkipVerify bool
}

// NewHTTPClient creates a new HTTP client
func NewHTTPClient(cfg HTTPConfig) *HTTPClient {
	if cfg.ClientConfig.Name == "" {
		cfg.ClientConfig = DefaultConfig()
	}

	return &HTTPClient{
		BaseClient: NewBaseClient(cfg.ClientConfig),
		baseURL:    cfg.BaseURL,
		authToken:  cfg.AuthToken,
		tenantID:   cfg.TenantID,
		httpClient: &http.Client{
			Timeout: cfg.RequestTimeout,
		},
	}
}

// Connect initializes the HTTP connection
func (c *HTTPClient) Connect(ctx context.Context) error {
	if c.IsConnected() {
		return ErrAlreadyConnected
	}

	// Health check
	resp, err := c.doRequest(ctx, http.MethodGet, "/health", nil)
	if err != nil {
		return fmt.Errorf("health check failed: %w", err)
	}
	resp.Body.Close()

	// Initialize
	info, caps, err := c.initialize(ctx)
	if err != nil {
		return fmt.Errorf("initialization failed: %w", err)
	}

	c.setConnected(true, info, caps)
	return nil
}

// Close disconnects
func (c *HTTPClient) Close() error {
	c.setConnected(false, nil, nil)
	return nil
}

// initialize sends initialize request
func (c *HTTPClient) initialize(ctx context.Context) (*ServerInfo, *ServerCapabilities, error) {
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

	return &resp.ServerInfo, &resp.Capabilities, nil
}

// ListTools returns available tools
func (c *HTTPClient) ListTools(ctx context.Context) ([]Tool, error) {
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
func (c *HTTPClient) CallTool(ctx context.Context, name string, args map[string]any) (*ToolResult, error) {
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
func (c *HTTPClient) ListResources(ctx context.Context) ([]Resource, error) {
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
func (c *HTTPClient) ReadResource(ctx context.Context, uri string) (*ResourceContent, error) {
	if !c.IsConnected() {
		return nil, ErrNotConnected
	}

	params := map[string]any{"uri": uri}

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
func (c *HTTPClient) ListPrompts(ctx context.Context) ([]Prompt, error) {
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
func (c *HTTPClient) GetPrompt(ctx context.Context, name string, args map[string]string) (*PromptResult, error) {
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
func (c *HTTPClient) CreateSample(ctx context.Context, req *SamplingRequest) (*SamplingResponse, error) {
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

// call sends a JSON-RPC request via HTTP POST
func (c *HTTPClient) call(ctx context.Context, method string, params any) (json.RawMessage, error) {
	id := atomic.AddInt64(&c.requestID, 1)

	req := jsonRPCRequest{
		JSONRPC: "2.0",
		ID:      id,
		Method:  method,
		Params:  params,
	}

	data, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	resp, err := c.doRequest(ctx, http.MethodPost, "/rpc", bytes.NewReader(data))
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	var rpcResp jsonRPCResponse
	if err := json.Unmarshal(body, &rpcResp); err != nil {
		return nil, fmt.Errorf("failed to parse response: %w", err)
	}

	if rpcResp.Error != nil {
		return nil, rpcResp.Error
	}

	return rpcResp.Result, nil
}

// doRequest performs HTTP request with auth headers
func (c *HTTPClient) doRequest(ctx context.Context, method, path string, body io.Reader) (*http.Response, error) {
	url := c.baseURL + path

	req, err := http.NewRequestWithContext(ctx, method, url, body)
	if err != nil {
		return nil, err
	}

	req.Header.Set("Content-Type", "application/json")

	if c.authToken != "" {
		req.Header.Set("Authorization", "Bearer "+c.authToken)
	}

	if c.tenantID != "" {
		req.Header.Set("X-Tenant-ID", c.tenantID)
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, err
	}

	if resp.StatusCode >= 400 {
		body, _ := io.ReadAll(resp.Body)
		resp.Body.Close()
		return nil, fmt.Errorf("HTTP %d: %s", resp.StatusCode, string(body))
	}

	return resp, nil
}

// SetAuthToken updates the auth token
func (c *HTTPClient) SetAuthToken(token string) {
	c.authToken = token
}

// SetTenantID updates the tenant ID
func (c *HTTPClient) SetTenantID(id string) {
	c.tenantID = id
}

// WithTimeout returns a context with request timeout
func (c *HTTPClient) WithTimeout(ctx context.Context) (context.Context, context.CancelFunc) {
	timeout := c.config.RequestTimeout
	if timeout == 0 {
		timeout = 60 * time.Second
	}
	return context.WithTimeout(ctx, timeout)
}
