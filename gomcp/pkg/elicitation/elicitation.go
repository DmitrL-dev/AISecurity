// Package elicitation provides user input request support for MCP.
// Enables servers to request information from users via clients.
package elicitation

import (
	"context"
	"fmt"
	"sync"
)

// Request represents an elicitation request from server to client
type Request struct {
	RequestID string  `json:"requestId"`
	Message   string  `json:"message"`
	Schema    *Schema `json:"schema,omitempty"`
}

// Schema defines the expected response format
type Schema struct {
	Type        string              `json:"type"`
	Title       string              `json:"title,omitempty"`
	Description string              `json:"description,omitempty"`
	Properties  map[string]Property `json:"properties,omitempty"`
	Required    []string            `json:"required,omitempty"`
	Enum        []string            `json:"enum,omitempty"`
	Minimum     *float64            `json:"minimum,omitempty"`
	Maximum     *float64            `json:"maximum,omitempty"`
	Default     any                 `json:"default,omitempty"`
}

// Property defines a schema property
type Property struct {
	Type        string   `json:"type"`
	Title       string   `json:"title,omitempty"`
	Description string   `json:"description,omitempty"`
	Enum        []string `json:"enum,omitempty"`
	Default     any      `json:"default,omitempty"`
	MinLength   *int     `json:"minLength,omitempty"`
	MaxLength   *int     `json:"maxLength,omitempty"`
	Minimum     *float64 `json:"minimum,omitempty"`
	Maximum     *float64 `json:"maximum,omitempty"`
	Format      string   `json:"format,omitempty"`
}

// Response represents a user's response to an elicitation
type Response struct {
	RequestID string         `json:"requestId"`
	Action    Action         `json:"action"`
	Content   map[string]any `json:"content,omitempty"`
}

// Action represents the user's action
type Action string

const (
	ActionSubmit  Action = "submit"
	ActionCancel  Action = "cancel"
	ActionTimeout Action = "timeout"
)

// Handler processes elicitation requests
type Handler interface {
	// RequestInput asks user for input
	RequestInput(ctx context.Context, req *Request) (*Response, error)
}

// HandlerFunc is a function adapter for Handler
type HandlerFunc func(ctx context.Context, req *Request) (*Response, error)

// RequestInput implements Handler
func (f HandlerFunc) RequestInput(ctx context.Context, req *Request) (*Response, error) {
	return f(ctx, req)
}

// Manager manages elicitation handlers
type Manager struct {
	handler Handler
	pending map[string]chan *Response
	mu      sync.RWMutex
}

// NewManager creates an elicitation manager
func NewManager(handler Handler) *Manager {
	return &Manager{
		handler: handler,
		pending: make(map[string]chan *Response),
	}
}

// SetHandler sets the elicitation handler
func (m *Manager) SetHandler(h Handler) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.handler = h
}

// RequestInput sends an elicitation request
func (m *Manager) RequestInput(ctx context.Context, req *Request) (*Response, error) {
	m.mu.RLock()
	handler := m.handler
	m.mu.RUnlock()

	if handler == nil {
		return nil, ErrNoHandler
	}

	return handler.RequestInput(ctx, req)
}

// RegisterPending registers a pending request
func (m *Manager) RegisterPending(requestID string) <-chan *Response {
	m.mu.Lock()
	defer m.mu.Unlock()

	ch := make(chan *Response, 1)
	m.pending[requestID] = ch
	return ch
}

// ResolvePending resolves a pending request
func (m *Manager) ResolvePending(resp *Response) error {
	m.mu.Lock()
	ch, ok := m.pending[resp.RequestID]
	if ok {
		delete(m.pending, resp.RequestID)
	}
	m.mu.Unlock()

	if !ok {
		return ErrRequestNotFound
	}

	ch <- resp
	close(ch)
	return nil
}

// CancelPending cancels a pending request
func (m *Manager) CancelPending(requestID string) {
	m.mu.Lock()
	ch, ok := m.pending[requestID]
	if ok {
		delete(m.pending, requestID)
		ch <- &Response{
			RequestID: requestID,
			Action:    ActionCancel,
		}
		close(ch)
	}
	m.mu.Unlock()
}

// PendingCount returns number of pending requests
func (m *Manager) PendingCount() int {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return len(m.pending)
}

// Validate validates an elicitation request
func (req *Request) Validate() error {
	if req.RequestID == "" {
		return ErrEmptyRequestID
	}

	if req.Message == "" {
		return ErrEmptyMessage
	}

	return nil
}

// Validate validates a response against a schema
func (resp *Response) Validate(schema *Schema) error {
	if resp.Action == ActionCancel || resp.Action == ActionTimeout {
		return nil
	}

	if schema == nil {
		return nil
	}

	// Check required fields
	for _, required := range schema.Required {
		if _, ok := resp.Content[required]; !ok {
			return fmt.Errorf("missing required field: %s", required)
		}
	}

	return nil
}

// Errors
var (
	ErrNoHandler       = fmt.Errorf("no elicitation handler registered")
	ErrRequestNotFound = fmt.Errorf("pending request not found")
	ErrEmptyRequestID  = fmt.Errorf("requestId cannot be empty")
	ErrEmptyMessage    = fmt.Errorf("message cannot be empty")
)

// JSON-RPC method names
const (
	MethodElicit = "elicitation/create"
)

// Builder helpers

// TextInput creates a text input schema
func TextInput(title, description string) *Schema {
	return &Schema{
		Type:        "string",
		Title:       title,
		Description: description,
	}
}

// NumberInput creates a number input schema
func NumberInput(title, description string, min, max *float64) *Schema {
	return &Schema{
		Type:        "number",
		Title:       title,
		Description: description,
		Minimum:     min,
		Maximum:     max,
	}
}

// SelectInput creates a select/choice schema
func SelectInput(title, description string, options []string) *Schema {
	return &Schema{
		Type:        "string",
		Title:       title,
		Description: description,
		Enum:        options,
	}
}

// BooleanInput creates a boolean input schema
func BooleanInput(title, description string, defaultValue bool) *Schema {
	return &Schema{
		Type:        "boolean",
		Title:       title,
		Description: description,
		Default:     defaultValue,
	}
}

// ObjectInput creates an object input schema
func ObjectInput(title, description string, properties map[string]Property, required []string) *Schema {
	return &Schema{
		Type:        "object",
		Title:       title,
		Description: description,
		Properties:  properties,
		Required:    required,
	}
}

// MockHandler creates a mock handler for testing
func MockHandler(action Action, content map[string]any) Handler {
	return HandlerFunc(func(ctx context.Context, req *Request) (*Response, error) {
		return &Response{
			RequestID: req.RequestID,
			Action:    action,
			Content:   content,
		}, nil
	})
}
