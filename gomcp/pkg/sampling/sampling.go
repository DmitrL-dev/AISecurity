// Package sampling provides LLM sampling/inference support for MCP.
// Enables servers to request AI-generated text from clients.
package sampling

import (
	"context"
	"encoding/json"
	"fmt"
	"sync"
)

// Message represents a conversation message
type Message struct {
	Role    Role    `json:"role"`
	Content Content `json:"content"`
}

// Role is the message sender role
type Role string

const (
	RoleUser      Role = "user"
	RoleAssistant Role = "assistant"
)

// Content represents message content
type Content struct {
	Type     string `json:"type"`
	Text     string `json:"text,omitempty"`
	Data     string `json:"data,omitempty"`
	MimeType string `json:"mimeType,omitempty"`
}

// TextContent creates text content
func TextContent(text string) Content {
	return Content{Type: "text", Text: text}
}

// ImageContent creates image content
func ImageContent(data, mimeType string) Content {
	return Content{Type: "image", Data: data, MimeType: mimeType}
}

// Request represents a sampling request
type Request struct {
	Messages         []Message         `json:"messages"`
	ModelPreferences *ModelPreferences `json:"modelPreferences,omitempty"`
	SystemPrompt     string            `json:"systemPrompt,omitempty"`
	IncludeContext   string            `json:"includeContext,omitempty"`
	Temperature      *float64          `json:"temperature,omitempty"`
	MaxTokens        int               `json:"maxTokens"`
	StopSequences    []string          `json:"stopSequences,omitempty"`
	Metadata         map[string]any    `json:"metadata,omitempty"`
}

// ModelPreferences specifies model selection hints
type ModelPreferences struct {
	Hints                []ModelHint `json:"hints,omitempty"`
	CostPriority         float64     `json:"costPriority,omitempty"`
	SpeedPriority        float64     `json:"speedPriority,omitempty"`
	IntelligencePriority float64     `json:"intelligencePriority,omitempty"`
}

// ModelHint suggests a specific model
type ModelHint struct {
	Name string `json:"name,omitempty"`
}

// Response represents a sampling response
type Response struct {
	Role       Role    `json:"role"`
	Content    Content `json:"content"`
	Model      string  `json:"model,omitempty"`
	StopReason string  `json:"stopReason,omitempty"`
}

// StopReason constants
const (
	StopReasonEndTurn      = "endTurn"
	StopReasonStopSequence = "stopSequence"
	StopReasonMaxTokens    = "maxTokens"
)

// Handler processes sampling requests
type Handler interface {
	// CreateMessage generates an AI response
	CreateMessage(ctx context.Context, req *Request) (*Response, error)
}

// HandlerFunc is a function adapter for Handler
type HandlerFunc func(ctx context.Context, req *Request) (*Response, error)

// CreateMessage implements Handler
func (f HandlerFunc) CreateMessage(ctx context.Context, req *Request) (*Response, error) {
	return f(ctx, req)
}

// Manager manages sampling handlers
type Manager struct {
	handler Handler
	mu      sync.RWMutex

	// Middleware
	middleware []Middleware
}

// Middleware wraps a handler
type Middleware func(Handler) Handler

// NewManager creates a sampling manager
func NewManager(handler Handler) *Manager {
	return &Manager{
		handler: handler,
	}
}

// Use adds middleware
func (m *Manager) Use(mw Middleware) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.middleware = append(m.middleware, mw)
}

// SetHandler sets the sampling handler
func (m *Manager) SetHandler(h Handler) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.handler = h
}

// CreateMessage processes a sampling request
func (m *Manager) CreateMessage(ctx context.Context, req *Request) (*Response, error) {
	m.mu.RLock()
	handler := m.handler
	middleware := m.middleware
	m.mu.RUnlock()

	if handler == nil {
		return nil, ErrNoHandler
	}

	// Apply middleware in reverse order
	h := handler
	for i := len(middleware) - 1; i >= 0; i-- {
		h = middleware[i](h)
	}

	return h.CreateMessage(ctx, req)
}

// Validate validates a sampling request
func (req *Request) Validate() error {
	if len(req.Messages) == 0 {
		return ErrNoMessages
	}

	if req.MaxTokens <= 0 {
		return ErrInvalidMaxTokens
	}

	for i, msg := range req.Messages {
		if msg.Role != RoleUser && msg.Role != RoleAssistant {
			return fmt.Errorf("invalid role in message %d: %s", i, msg.Role)
		}
	}

	return nil
}

// Errors
var (
	ErrNoHandler        = fmt.Errorf("no sampling handler registered")
	ErrNoMessages       = fmt.Errorf("messages cannot be empty")
	ErrInvalidMaxTokens = fmt.Errorf("maxTokens must be positive")
)

// JSON-RPC method names
const (
	MethodCreateMessage = "sampling/createMessage"
)

// ToJSON converts request to JSON
func (req *Request) ToJSON() ([]byte, error) {
	return json.Marshal(req)
}

// FromJSON parses request from JSON
func (req *Request) FromJSON(data []byte) error {
	return json.Unmarshal(data, req)
}

// LoggingMiddleware adds request/response logging
func LoggingMiddleware(logger func(string, ...any)) Middleware {
	return func(next Handler) Handler {
		return HandlerFunc(func(ctx context.Context, req *Request) (*Response, error) {
			logger("sampling request: messages=%d maxTokens=%d", len(req.Messages), req.MaxTokens)

			resp, err := next.CreateMessage(ctx, req)

			if err != nil {
				logger("sampling error: %v", err)
			} else {
				logger("sampling response: model=%s stopReason=%s", resp.Model, resp.StopReason)
			}

			return resp, err
		})
	}
}

// RateLimitMiddleware adds rate limiting
func RateLimitMiddleware(requestsPerMinute int) Middleware {
	// Simple token bucket implementation
	var (
		tokens   = requestsPerMinute
		tokensMu sync.Mutex
	)

	return func(next Handler) Handler {
		return HandlerFunc(func(ctx context.Context, req *Request) (*Response, error) {
			tokensMu.Lock()
			if tokens <= 0 {
				tokensMu.Unlock()
				return nil, ErrRateLimited
			}
			tokens--
			tokensMu.Unlock()

			return next.CreateMessage(ctx, req)
		})
	}
}

// ErrRateLimited indicates rate limit exceeded
var ErrRateLimited = fmt.Errorf("rate limit exceeded")

// MockHandler creates a mock sampling handler for testing
func MockHandler(response string, model string) Handler {
	return HandlerFunc(func(ctx context.Context, req *Request) (*Response, error) {
		return &Response{
			Role:       RoleAssistant,
			Content:    TextContent(response),
			Model:      model,
			StopReason: StopReasonEndTurn,
		}, nil
	})
}
