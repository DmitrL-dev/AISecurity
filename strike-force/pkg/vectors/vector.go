package vectors

import (
	"context"
	"encoding/json"
	"time"
)

// ============================================================================
// VECTOR INTERFACE — Common contract for all attack vectors
// ============================================================================

// Vector is the common interface for all attack vectors.
// Every vector MUST implement this interface.
type Vector interface {
	// Name returns the vector identifier (e.g., "mcp", "llm", "email").
	Name() string

	// Description returns a human-readable description.
	Description() string

	// Strategies returns the list of supported strategy names.
	Strategies() []string

	// Generate creates an attack payload for the given strategy and target.
	Generate(strategy string, target string) (*Payload, error)

	// Execute sends the payload to the target. Returns result with response data.
	// Use context for timeout/cancellation.
	Execute(ctx context.Context, payload *Payload) (*Result, error)
}

// Payload represents a generated attack payload.
type Payload struct {
	Vector    string            `json:"vector"`
	Strategy  string            `json:"strategy"`
	Target    string            `json:"target"`
	Data      string            `json:"data"`     // raw payload content
	Metadata  map[string]string `json:"metadata"` // extra k/v (e.g., "transport": "websocket")
	CreatedAt time.Time         `json:"created_at"`
}

// Result represents the outcome of an attack execution.
type Result struct {
	Vector    string        `json:"vector"`
	Strategy  string        `json:"strategy"`
	Target    string        `json:"target"`
	Success   bool          `json:"success"`
	Response  string        `json:"response,omitempty"` // raw server response
	Evidence  []Evidence    `json:"evidence,omitempty"` // extracted proof
	Duration  time.Duration `json:"duration"`
	Error     string        `json:"error,omitempty"`
	Timestamp time.Time     `json:"timestamp"`
}

// Evidence represents a single piece of proof from an attack.
type Evidence struct {
	Type        string `json:"type"` // "rce_output", "data_leak", "tool_list", "error_info"
	Description string `json:"description"`
	Data        string `json:"data"`
}

// Registry holds all registered vectors.
type Registry struct {
	vectors map[string]Vector
}

// NewRegistry creates a vector registry.
func NewRegistry() *Registry {
	return &Registry{vectors: make(map[string]Vector)}
}

// Register adds a vector to the registry.
func (r *Registry) Register(v Vector) {
	r.vectors[v.Name()] = v
}

// Get returns a vector by name.
func (r *Registry) Get(name string) (Vector, bool) {
	v, ok := r.vectors[name]
	return v, ok
}

// List returns all registered vector names.
func (r *Registry) List() []string {
	names := make([]string, 0, len(r.vectors))
	for name := range r.vectors {
		names = append(names, name)
	}
	return names
}

// ListAll returns all vectors with their strategies.
func (r *Registry) ListAll() map[string][]string {
	result := make(map[string][]string, len(r.vectors))
	for name, v := range r.vectors {
		result[name] = v.Strategies()
	}
	return result
}

// ToJSON serializes a Result to JSON.
func (res *Result) ToJSON() string {
	b, _ := json.MarshalIndent(res, "", "  ")
	return string(b)
}

// NewPayload creates a Payload with timestamp.
func NewPayload(vector, strategy, target, data string) *Payload {
	return &Payload{
		Vector:    vector,
		Strategy:  strategy,
		Target:    target,
		Data:      data,
		Metadata:  make(map[string]string),
		CreatedAt: time.Now(),
	}
}
