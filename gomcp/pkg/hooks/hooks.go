// Package hooks provides lifecycle callbacks for MCP operations.
// Hooks enable interception and modification of requests/responses.
package hooks

import (
	"context"
	"encoding/json"
	"sync"
)

// Phase represents when a hook runs
type Phase string

const (
	PhaseBefore Phase = "before"
	PhaseAfter  Phase = "after"
	PhaseError  Phase = "error"
)

// Event represents a hookable event
type Event struct {
	Phase   Phase          `json:"phase"`
	Method  string         `json:"method"`
	Params  any            `json:"params,omitempty"`
	Result  any            `json:"result,omitempty"`
	Error   error          `json:"error,omitempty"`
	Context map[string]any `json:"context,omitempty"`
}

// Handler processes hook events
type Handler interface {
	Handle(ctx context.Context, event *Event) error
}

// HandlerFunc is a function adapter for Handler
type HandlerFunc func(ctx context.Context, event *Event) error

// Handle implements Handler
func (f HandlerFunc) Handle(ctx context.Context, event *Event) error {
	return f(ctx, event)
}

// Registry manages hooks
type Registry struct {
	hooks map[string][]hookEntry
	mu    sync.RWMutex
}

type hookEntry struct {
	phase   Phase
	handler Handler
	order   int
}

// NewRegistry creates a hook registry
func NewRegistry() *Registry {
	return &Registry{
		hooks: make(map[string][]hookEntry),
	}
}

// Register adds a hook for a method and phase
func (r *Registry) Register(method string, phase Phase, handler Handler) {
	r.RegisterWithOrder(method, phase, handler, 0)
}

// RegisterWithOrder adds a hook with execution order
func (r *Registry) RegisterWithOrder(method string, phase Phase, handler Handler, order int) {
	r.mu.Lock()
	defer r.mu.Unlock()

	key := method + ":" + string(phase)
	r.hooks[key] = append(r.hooks[key], hookEntry{
		phase:   phase,
		handler: handler,
		order:   order,
	})
}

// Execute runs all hooks for a method and phase
func (r *Registry) Execute(ctx context.Context, method string, phase Phase, event *Event) error {
	r.mu.RLock()
	key := method + ":" + string(phase)
	entries := r.hooks[key]
	r.mu.RUnlock()

	if len(entries) == 0 {
		return nil
	}

	event.Phase = phase
	event.Method = method

	for _, entry := range entries {
		if err := entry.handler.Handle(ctx, event); err != nil {
			return err
		}
	}

	return nil
}

// ExecuteBefore runs before hooks
func (r *Registry) ExecuteBefore(ctx context.Context, method string, params any) error {
	return r.Execute(ctx, method, PhaseBefore, &Event{Params: params})
}

// ExecuteAfter runs after hooks
func (r *Registry) ExecuteAfter(ctx context.Context, method string, result any) error {
	return r.Execute(ctx, method, PhaseAfter, &Event{Result: result})
}

// ExecuteError runs error hooks
func (r *Registry) ExecuteError(ctx context.Context, method string, err error) error {
	return r.Execute(ctx, method, PhaseError, &Event{Error: err})
}

// Clear removes all hooks
func (r *Registry) Clear() {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.hooks = make(map[string][]hookEntry)
}

// Count returns total number of registered hooks
func (r *Registry) Count() int {
	r.mu.RLock()
	defer r.mu.RUnlock()

	count := 0
	for _, entries := range r.hooks {
		count += len(entries)
	}
	return count
}

// Has checks if any hooks exist for method/phase
func (r *Registry) Has(method string, phase Phase) bool {
	r.mu.RLock()
	defer r.mu.RUnlock()

	key := method + ":" + string(phase)
	return len(r.hooks[key]) > 0
}

// Convenience hook types

// BeforeToolCall is called before tool execution
type BeforeToolCall struct {
	ToolName  string         `json:"toolName"`
	Arguments map[string]any `json:"arguments"`
}

// AfterToolCall is called after tool execution
type AfterToolCall struct {
	ToolName string `json:"toolName"`
	Result   any    `json:"result"`
	Duration int64  `json:"duration"` // nanoseconds
}

// BeforeResourceRead is called before reading a resource
type BeforeResourceRead struct {
	URI string `json:"uri"`
}

// AfterResourceRead is called after reading a resource
type AfterResourceRead struct {
	URI      string `json:"uri"`
	Contents any    `json:"contents"`
}

// BeforePromptGet is called before getting a prompt
type BeforePromptGet struct {
	Name      string         `json:"name"`
	Arguments map[string]any `json:"arguments"`
}

// AfterPromptGet is called after getting a prompt
type AfterPromptGet struct {
	Name     string `json:"name"`
	Messages any    `json:"messages"`
}

// ToJSON serializes event to JSON
func (e *Event) ToJSON() ([]byte, error) {
	return json.Marshal(e)
}

// Common method names
const (
	MethodToolsCall     = "tools/call"
	MethodResourcesRead = "resources/read"
	MethodPromptsGet    = "prompts/get"
	MethodInitialize    = "initialize"
	MethodPing          = "ping"
)

// Middleware wraps a handler with hook execution
func Middleware(registry *Registry) func(Handler) Handler {
	return func(next Handler) Handler {
		return HandlerFunc(func(ctx context.Context, event *Event) error {
			// Before
			if err := registry.ExecuteBefore(ctx, event.Method, event.Params); err != nil {
				return err
			}

			// Execute
			if err := next.Handle(ctx, event); err != nil {
				registry.ExecuteError(ctx, event.Method, err)
				return err
			}

			// After
			return registry.ExecuteAfter(ctx, event.Method, event.Result)
		})
	}
}
