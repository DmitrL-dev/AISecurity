// Package completions provides auto-completion support for MCP 2025-11-25.
// Completions enable argument value suggestions for prompts and resources.
package completions

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"sync"
)

// CompletionRef identifies what to complete
type CompletionRef struct {
	Type string `json:"type"` // "ref/prompt" or "ref/resource"
	Name string `json:"name,omitempty"`
	URI  string `json:"uri,omitempty"`
}

// CompletionArg specifies the argument to complete
type CompletionArg struct {
	Name  string `json:"name"`
	Value string `json:"value"`
}

// Request is a completion request
type Request struct {
	Ref      CompletionRef `json:"ref"`
	Argument CompletionArg `json:"argument"`
}

// Completion represents a single completion value
type Completion struct {
	Values  []string `json:"values"`
	Total   int      `json:"total,omitempty"`
	HasMore bool     `json:"hasMore,omitempty"`
}

// Response is a completion response
type Response struct {
	Completion Completion `json:"completion"`
}

// Provider generates completions for a specific ref type
type Provider interface {
	Complete(ctx context.Context, req *Request) (*Response, error)
	Supports(ref CompletionRef) bool
}

// ProviderFunc is a function adapter for Provider
type ProviderFunc func(ctx context.Context, req *Request) (*Response, error)

// Complete implements Provider
func (f ProviderFunc) Complete(ctx context.Context, req *Request) (*Response, error) {
	return f(ctx, req)
}

// Supports implements Provider (always returns true)
func (f ProviderFunc) Supports(ref CompletionRef) bool {
	return true
}

// Manager manages completion providers
type Manager struct {
	providers []providerEntry
	mu        sync.RWMutex
}

type providerEntry struct {
	refType  string
	name     string
	provider Provider
}

// NewManager creates a completion manager
func NewManager() *Manager {
	return &Manager{
		providers: make([]providerEntry, 0),
	}
}

// RegisterProvider registers a completion provider
func (m *Manager) RegisterProvider(refType, name string, provider Provider) {
	m.mu.Lock()
	defer m.mu.Unlock()

	m.providers = append(m.providers, providerEntry{
		refType:  refType,
		name:     name,
		provider: provider,
	})
}

// Complete generates completions for a request
func (m *Manager) Complete(ctx context.Context, req *Request) (*Response, error) {
	if req == nil {
		return nil, ErrNilRequest
	}

	m.mu.RLock()
	defer m.mu.RUnlock()

	for _, entry := range m.providers {
		if entry.refType != "" && entry.refType != req.Ref.Type {
			continue
		}

		if entry.name != "" && entry.name != req.Ref.Name && entry.name != req.Ref.URI {
			continue
		}

		if entry.provider.Supports(req.Ref) {
			return entry.provider.Complete(ctx, req)
		}
	}

	// Return empty completion if no provider found
	return &Response{
		Completion: Completion{
			Values:  []string{},
			Total:   0,
			HasMore: false,
		},
	}, nil
}

// StaticProvider provides static completion values
type StaticProvider struct {
	values []string
}

// NewStaticProvider creates a static completion provider
func NewStaticProvider(values []string) *StaticProvider {
	return &StaticProvider{values: values}
}

// Complete implements Provider
func (p *StaticProvider) Complete(ctx context.Context, req *Request) (*Response, error) {
	prefix := req.Argument.Value
	var matches []string

	for _, v := range p.values {
		if strings.HasPrefix(v, prefix) {
			matches = append(matches, v)
		}
	}

	return &Response{
		Completion: Completion{
			Values:  matches,
			Total:   len(matches),
			HasMore: false,
		},
	}, nil
}

// Supports implements Provider
func (p *StaticProvider) Supports(ref CompletionRef) bool {
	return true
}

// PrefixProvider filters values by prefix
type PrefixProvider struct {
	valuesFn func() []string
}

// NewPrefixProvider creates a prefix-based provider
func NewPrefixProvider(fn func() []string) *PrefixProvider {
	return &PrefixProvider{valuesFn: fn}
}

// Complete implements Provider
func (p *PrefixProvider) Complete(ctx context.Context, req *Request) (*Response, error) {
	prefix := req.Argument.Value
	values := p.valuesFn()
	var matches []string

	for _, v := range values {
		if strings.HasPrefix(v, prefix) {
			matches = append(matches, v)
		}
	}

	return &Response{
		Completion: Completion{
			Values:  matches,
			Total:   len(matches),
			HasMore: false,
		},
	}, nil
}

// Supports implements Provider
func (p *PrefixProvider) Supports(ref CompletionRef) bool {
	return true
}

// ToJSON serializes response to JSON
func (r *Response) ToJSON() ([]byte, error) {
	return json.Marshal(r)
}

// Errors
var (
	ErrNilRequest = fmt.Errorf("request cannot be nil")
)

// Reference types
const (
	RefTypePrompt   = "ref/prompt"
	RefTypeResource = "ref/resource"
)

// JSON-RPC method name
const (
	MethodComplete = "completion/complete"
)
