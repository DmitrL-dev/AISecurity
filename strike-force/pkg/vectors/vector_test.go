package vectors

import (
	"context"
	"testing"
)

// ============================================================================
// TDD: Vector Interface Tests
// ============================================================================

// mockVector implements Vector for testing.
type mockVector struct {
	name        string
	strategies  []string
	generateErr error
	executeErr  error
}

func (m *mockVector) Name() string         { return m.name }
func (m *mockVector) Description() string  { return "Mock vector for testing" }
func (m *mockVector) Strategies() []string { return m.strategies }

func (m *mockVector) Generate(strategy string, target string) (*Payload, error) {
	if m.generateErr != nil {
		return nil, m.generateErr
	}
	return NewPayload(m.name, strategy, target, `{"test": true}`), nil
}

func (m *mockVector) Execute(ctx context.Context, payload *Payload) (*Result, error) {
	if m.executeErr != nil {
		return nil, m.executeErr
	}
	return &Result{
		Vector:   payload.Vector,
		Strategy: payload.Strategy,
		Target:   payload.Target,
		Success:  true,
		Response: "mock_response",
	}, nil
}

func TestNewPayload(t *testing.T) {
	p := NewPayload("mcp", "stealth_probe", "wss://target.dev", `{"jsonrpc":"2.0"}`)

	if p.Vector != "mcp" {
		t.Errorf("expected vector 'mcp', got '%s'", p.Vector)
	}
	if p.Strategy != "stealth_probe" {
		t.Errorf("expected strategy 'stealth_probe', got '%s'", p.Strategy)
	}
	if p.Target != "wss://target.dev" {
		t.Errorf("expected target 'wss://target.dev', got '%s'", p.Target)
	}
	if p.Metadata == nil {
		t.Fatal("metadata should be initialized, got nil")
	}
	if p.CreatedAt.IsZero() {
		t.Error("created_at should be set")
	}
}

func TestResultToJSON(t *testing.T) {
	r := &Result{
		Vector:   "mcp",
		Strategy: "stealth_probe",
		Target:   "wss://target.dev",
		Success:  true,
		Response: "test",
	}
	j := r.ToJSON()
	if j == "" {
		t.Fatal("ToJSON returned empty string")
	}
	if len(j) < 10 {
		t.Errorf("ToJSON output too short: %s", j)
	}
}

func TestRegistryRegisterAndGet(t *testing.T) {
	reg := NewRegistry()
	mock := &mockVector{name: "test_vector", strategies: []string{"s1", "s2"}}

	reg.Register(mock)

	v, ok := reg.Get("test_vector")
	if !ok {
		t.Fatal("expected to find registered vector")
	}
	if v.Name() != "test_vector" {
		t.Errorf("expected 'test_vector', got '%s'", v.Name())
	}
}

func TestRegistryGetMissing(t *testing.T) {
	reg := NewRegistry()
	_, ok := reg.Get("nonexistent")
	if ok {
		t.Error("expected false for missing vector")
	}
}

func TestRegistryList(t *testing.T) {
	reg := NewRegistry()
	reg.Register(&mockVector{name: "a", strategies: []string{"s1"}})
	reg.Register(&mockVector{name: "b", strategies: []string{"s2"}})

	names := reg.List()
	if len(names) != 2 {
		t.Fatalf("expected 2 vectors, got %d", len(names))
	}
}

func TestRegistryListAll(t *testing.T) {
	reg := NewRegistry()
	reg.Register(&mockVector{name: "mcp", strategies: []string{"stealth_probe", "tool_call_injection"}})
	reg.Register(&mockVector{name: "llm", strategies: []string{"system_override"}})

	all := reg.ListAll()
	if len(all) != 2 {
		t.Fatalf("expected 2 entries, got %d", len(all))
	}
	if len(all["mcp"]) != 2 {
		t.Errorf("expected 2 strategies for mcp, got %d", len(all["mcp"]))
	}
}

func TestVectorGenerate(t *testing.T) {
	mock := &mockVector{name: "test", strategies: []string{"s1"}}
	payload, err := mock.Generate("s1", "target.com")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if payload.Vector != "test" {
		t.Errorf("expected vector 'test', got '%s'", payload.Vector)
	}
}

func TestVectorExecute(t *testing.T) {
	mock := &mockVector{name: "test", strategies: []string{"s1"}}
	payload := NewPayload("test", "s1", "target.com", "data")

	result, err := mock.Execute(context.Background(), payload)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !result.Success {
		t.Error("expected success=true")
	}
}
