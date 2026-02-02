// Package client provides MCP client implementations for Go.
// Supports multiple transports: stdio, HTTP, gRPC, SSE.
package client

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"sync"
	"time"
)

// Client interface for MCP communication
type Client interface {
	// Connection management
	Connect(ctx context.Context) error
	Close() error
	IsConnected() bool

	// Server info
	ServerInfo() *ServerInfo
	Capabilities() *ServerCapabilities

	// Tools
	ListTools(ctx context.Context) ([]Tool, error)
	CallTool(ctx context.Context, name string, args map[string]any) (*ToolResult, error)

	// Resources
	ListResources(ctx context.Context) ([]Resource, error)
	ReadResource(ctx context.Context, uri string) (*ResourceContent, error)

	// Prompts
	ListPrompts(ctx context.Context) ([]Prompt, error)
	GetPrompt(ctx context.Context, name string, args map[string]string) (*PromptResult, error)

	// Sampling (MCP spec)
	CreateSample(ctx context.Context, req *SamplingRequest) (*SamplingResponse, error)

	// Notifications
	OnNotification(handler NotificationHandler)
}

// NotificationHandler handles server notifications
type NotificationHandler func(method string, params json.RawMessage)

// ServerInfo contains server metadata
type ServerInfo struct {
	Name            string `json:"name"`
	Version         string `json:"version"`
	ProtocolVersion string `json:"protocolVersion"`
}

// ServerCapabilities describes what the server supports
type ServerCapabilities struct {
	Tools     *ToolCapabilities     `json:"tools,omitempty"`
	Resources *ResourceCapabilities `json:"resources,omitempty"`
	Prompts   *PromptCapabilities   `json:"prompts,omitempty"`
	Sampling  *SamplingCapabilities `json:"sampling,omitempty"`
}

// ToolCapabilities describes tool support
type ToolCapabilities struct {
	ListChanged bool `json:"listChanged,omitempty"`
}

// ResourceCapabilities describes resource support
type ResourceCapabilities struct {
	Subscribe   bool `json:"subscribe,omitempty"`
	ListChanged bool `json:"listChanged,omitempty"`
}

// PromptCapabilities describes prompt support
type PromptCapabilities struct {
	ListChanged bool `json:"listChanged,omitempty"`
}

// SamplingCapabilities describes sampling support
type SamplingCapabilities struct{}

// Tool represents an MCP tool
type Tool struct {
	Name        string         `json:"name"`
	Description string         `json:"description,omitempty"`
	InputSchema map[string]any `json:"inputSchema,omitempty"`
}

// ToolResult is the result of a tool call
type ToolResult struct {
	Content []ContentItem `json:"content"`
	IsError bool          `json:"isError,omitempty"`
}

// ContentItem represents content in results
type ContentItem struct {
	Type     string `json:"type"` // "text", "image", "resource"
	Text     string `json:"text,omitempty"`
	Data     string `json:"data,omitempty"`
	MimeType string `json:"mimeType,omitempty"`
	URI      string `json:"uri,omitempty"`
}

// Resource represents an MCP resource
type Resource struct {
	URI         string `json:"uri"`
	Name        string `json:"name"`
	Description string `json:"description,omitempty"`
	MimeType    string `json:"mimeType,omitempty"`
}

// ResourceContent contains resource data
type ResourceContent struct {
	URI      string `json:"uri"`
	MimeType string `json:"mimeType,omitempty"`
	Text     string `json:"text,omitempty"`
	Blob     string `json:"blob,omitempty"`
}

// Prompt represents an MCP prompt
type Prompt struct {
	Name        string           `json:"name"`
	Description string           `json:"description,omitempty"`
	Arguments   []PromptArgument `json:"arguments,omitempty"`
}

// PromptArgument describes a prompt argument
type PromptArgument struct {
	Name        string `json:"name"`
	Description string `json:"description,omitempty"`
	Required    bool   `json:"required,omitempty"`
}

// PromptResult is the result of getting a prompt
type PromptResult struct {
	Description string          `json:"description,omitempty"`
	Messages    []PromptMessage `json:"messages"`
}

// PromptMessage is a message in a prompt
type PromptMessage struct {
	Role    string      `json:"role"` // "user", "assistant"
	Content ContentItem `json:"content"`
}

// SamplingRequest for LLM sampling
type SamplingRequest struct {
	Messages         []SamplingMessage `json:"messages"`
	ModelPreferences *ModelPreferences `json:"modelPreferences,omitempty"`
	SystemPrompt     string            `json:"systemPrompt,omitempty"`
	MaxTokens        int               `json:"maxTokens"`
	Temperature      float64           `json:"temperature,omitempty"`
	StopSequences    []string          `json:"stopSequences,omitempty"`
}

// SamplingMessage is a message for sampling
type SamplingMessage struct {
	Role    string      `json:"role"`
	Content ContentItem `json:"content"`
}

// ModelPreferences for sampling
type ModelPreferences struct {
	Hints                []ModelHint `json:"hints,omitempty"`
	CostPriority         float64     `json:"costPriority,omitempty"`
	SpeedPriority        float64     `json:"speedPriority,omitempty"`
	IntelligencePriority float64     `json:"intelligencePriority,omitempty"`
}

// ModelHint suggests a model
type ModelHint struct {
	Name string `json:"name,omitempty"`
}

// SamplingResponse from LLM
type SamplingResponse struct {
	Role       string      `json:"role"`
	Content    ContentItem `json:"content"`
	Model      string      `json:"model"`
	StopReason string      `json:"stopReason,omitempty"`
}

// ClientConfig configures a client
type ClientConfig struct {
	// Client info
	Name    string
	Version string

	// Timeouts
	ConnectTimeout time.Duration
	RequestTimeout time.Duration

	// Retry settings
	MaxRetries    int
	RetryInterval time.Duration

	// Capabilities to request
	Capabilities *ClientCapabilities
}

// ClientCapabilities describes what the client supports
type ClientCapabilities struct {
	Sampling *SamplingCapabilities `json:"sampling,omitempty"`
	Roots    *RootsCapabilities    `json:"roots,omitempty"`
}

// RootsCapabilities for filesystem roots
type RootsCapabilities struct {
	ListChanged bool `json:"listChanged,omitempty"`
}

// DefaultConfig returns sensible defaults
func DefaultConfig() ClientConfig {
	return ClientConfig{
		Name:           "gomcp-client",
		Version:        "1.0.0",
		ConnectTimeout: 30 * time.Second,
		RequestTimeout: 60 * time.Second,
		MaxRetries:     3,
		RetryInterval:  1 * time.Second,
		Capabilities:   &ClientCapabilities{},
	}
}

// Errors
var (
	ErrNotConnected     = errors.New("client not connected")
	ErrAlreadyConnected = errors.New("client already connected")
	ErrConnectionFailed = errors.New("connection failed")
	ErrTimeout          = errors.New("request timeout")
	ErrToolNotFound     = errors.New("tool not found")
	ErrResourceNotFound = errors.New("resource not found")
	ErrPromptNotFound   = errors.New("prompt not found")
	ErrInvalidResponse  = errors.New("invalid response")
)

// BaseClient provides common client functionality
type BaseClient struct {
	config       ClientConfig
	serverInfo   *ServerInfo
	capabilities *ServerCapabilities

	mu        sync.RWMutex
	connected bool
	handlers  []NotificationHandler
}

// NewBaseClient creates a new base client
func NewBaseClient(config ClientConfig) *BaseClient {
	return &BaseClient{
		config:   config,
		handlers: make([]NotificationHandler, 0),
	}
}

// IsConnected returns connection status
func (c *BaseClient) IsConnected() bool {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.connected
}

// ServerInfo returns server metadata
func (c *BaseClient) ServerInfo() *ServerInfo {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.serverInfo
}

// Capabilities returns server capabilities
func (c *BaseClient) Capabilities() *ServerCapabilities {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.capabilities
}

// OnNotification registers a notification handler
func (c *BaseClient) OnNotification(handler NotificationHandler) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.handlers = append(c.handlers, handler)
}

// setConnected updates connection state
func (c *BaseClient) setConnected(connected bool, info *ServerInfo, caps *ServerCapabilities) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.connected = connected
	c.serverInfo = info
	c.capabilities = caps
}

// notifyHandlers sends notification to all handlers
func (c *BaseClient) notifyHandlers(method string, params json.RawMessage) {
	c.mu.RLock()
	handlers := make([]NotificationHandler, len(c.handlers))
	copy(handlers, c.handlers)
	c.mu.RUnlock()

	for _, h := range handlers {
		h(method, params)
	}
}

// JSON-RPC types
type jsonRPCRequest struct {
	JSONRPC string `json:"jsonrpc"`
	ID      int64  `json:"id"`
	Method  string `json:"method"`
	Params  any    `json:"params,omitempty"`
}

type jsonRPCResponse struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      int64           `json:"id"`
	Result  json.RawMessage `json:"result,omitempty"`
	Error   *jsonRPCError   `json:"error,omitempty"`
}

type jsonRPCError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
	Data    any    `json:"data,omitempty"`
}

func (e *jsonRPCError) Error() string {
	return fmt.Sprintf("RPC error %d: %s", e.Code, e.Message)
}
