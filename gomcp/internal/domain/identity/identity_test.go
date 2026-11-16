package identity

import (
	"testing"
)

// === Agent Identity Tests ===

func TestAgentIdentityValidation(t *testing.T) {
	tests := []struct {
		name    string
		agent   AgentIdentity
		wantErr error
	}{
		{
			"valid autonomous",
			AgentIdentity{AgentID: "a1", AgentName: "Test", CreatedBy: "admin", AgentType: AgentAutonomous},
			nil,
		},
		{
			"valid supervised",
			AgentIdentity{AgentID: "a2", AgentName: "Test", CreatedBy: "admin", AgentType: AgentSupervised},
			nil,
		},
		{
			"valid external",
			AgentIdentity{AgentID: "a3", AgentName: "Test", CreatedBy: "admin", AgentType: AgentExternal},
			nil,
		},
		{
			"missing agent_id",
			AgentIdentity{AgentName: "Test", CreatedBy: "admin", AgentType: AgentAutonomous},
			ErrMissingAgentID,
		},
		{
			"missing agent_name",
			AgentIdentity{AgentID: "a1", CreatedBy: "admin", AgentType: AgentAutonomous},
			ErrMissingAgentName,
		},
		{
			"missing created_by",
			AgentIdentity{AgentID: "a1", AgentName: "Test", AgentType: AgentAutonomous},
			ErrMissingCreatedBy,
		},
		{
			"invalid agent_type",
			AgentIdentity{AgentID: "a1", AgentName: "Test", CreatedBy: "admin", AgentType: "INVALID"},
			ErrInvalidAgentType,
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := tt.agent.Validate()
			if err != tt.wantErr {
				t.Errorf("Validate() = %v, want %v", err, tt.wantErr)
			}
		})
	}
}

func TestHasPermissionFailSafeClosed(t *testing.T) {
	agent := AgentIdentity{
		Capabilities: []ToolPermission{
			{ToolName: "web_search", Permissions: []Permission{PermRead}},
			{ToolName: "memory_store", Permissions: []Permission{PermRead, PermWrite}},
		},
	}

	// Allowed
	if !agent.HasPermission("web_search", PermRead) {
		t.Error("should allow READ on web_search")
	}
	if !agent.HasPermission("memory_store", PermWrite) {
		t.Error("should allow WRITE on memory_store")
	}

	// Deny: wrong permission on known tool
	if agent.HasPermission("web_search", PermWrite) {
		t.Error("should deny WRITE on web_search (insufficient_permissions)")
	}

	// Deny: unknown tool (fail-safe closed — SDD-003 M3)
	if agent.HasPermission("unknown_tool", PermRead) {
		t.Error("should deny READ on unknown_tool (fail-safe closed)")
	}
}

func TestHasTool(t *testing.T) {
	agent := AgentIdentity{
		Capabilities: []ToolPermission{
			{ToolName: "web_search", Permissions: []Permission{PermRead}},
		},
	}
	if !agent.HasTool("web_search") {
		t.Error("should have web_search")
	}
	if agent.HasTool("unknown") {
		t.Error("should not have unknown")
	}
}

func TestToolNames(t *testing.T) {
	agent := AgentIdentity{
		Capabilities: []ToolPermission{
			{ToolName: "a", Permissions: []Permission{PermRead}},
			{ToolName: "b", Permissions: []Permission{PermWrite}},
		},
	}
	names := agent.ToolNames()
	if len(names) != 2 {
		t.Fatalf("expected 2 tool names, got %d", len(names))
	}
}

// === Store Tests ===

func TestStoreRegisterAndGet(t *testing.T) {
	s := NewStore()
	agent := &AgentIdentity{
		AgentID:   "agent-01",
		AgentName: "Task Manager",
		CreatedBy: "admin@syntrex.pro",
		AgentType: AgentSupervised,
	}
	if err := s.Register(agent); err != nil {
		t.Fatalf("Register failed: %v", err)
	}

	got, err := s.Get("agent-01")
	if err != nil {
		t.Fatalf("Get failed: %v", err)
	}
	if got.AgentName != "Task Manager" {
		t.Errorf("got name %q, want %q", got.AgentName, "Task Manager")
	}
}

func TestStoreNotFound(t *testing.T) {
	s := NewStore()
	_, err := s.Get("nonexistent")
	if err != ErrAgentNotFound {
		t.Errorf("expected ErrAgentNotFound, got %v", err)
	}
}

func TestStoreDuplicateReject(t *testing.T) {
	s := NewStore()
	agent := &AgentIdentity{
		AgentID: "dup-01", AgentName: "A", CreatedBy: "admin", AgentType: AgentAutonomous,
	}
	_ = s.Register(agent)
	err := s.Register(agent)
	if err != ErrAgentExists {
		t.Errorf("expected ErrAgentExists, got %v", err)
	}
}

func TestStoreRemove(t *testing.T) {
	s := NewStore()
	_ = s.Register(&AgentIdentity{
		AgentID: "rm-01", AgentName: "A", CreatedBy: "admin", AgentType: AgentAutonomous,
	})
	if err := s.Remove("rm-01"); err != nil {
		t.Fatalf("Remove failed: %v", err)
	}
	if s.Count() != 0 {
		t.Error("expected 0 agents after removal")
	}
}

func TestStoreList(t *testing.T) {
	s := NewStore()
	_ = s.Register(&AgentIdentity{AgentID: "l1", AgentName: "A", CreatedBy: "admin", AgentType: AgentAutonomous})
	_ = s.Register(&AgentIdentity{AgentID: "l2", AgentName: "B", CreatedBy: "admin", AgentType: AgentSupervised})
	if len(s.List()) != 2 {
		t.Errorf("expected 2 agents, got %d", len(s.List()))
	}
}

// === Capability Check Tests ===

func TestCapabilityAllowed(t *testing.T) {
	s := NewStore()
	_ = s.Register(&AgentIdentity{
		AgentID: "cap-01", AgentName: "A", CreatedBy: "admin", AgentType: AgentAutonomous,
		Capabilities: []ToolPermission{
			{ToolName: "web_search", Permissions: []Permission{PermRead}},
		},
	})
	checker := NewCapabilityChecker(s)
	d := checker.Check("cap-01", "web_search", PermRead)
	if !d.Allowed {
		t.Errorf("expected allowed, got denied: %s", d.Reason)
	}
}

func TestCapabilityDeniedUnknownAgent(t *testing.T) {
	s := NewStore()
	checker := NewCapabilityChecker(s)
	d := checker.Check("ghost", "web_search", PermRead)
	if d.Allowed {
		t.Error("should deny unknown agent")
	}
	if d.Reason != "agent_not_found" {
		t.Errorf("expected reason agent_not_found, got %s", d.Reason)
	}
}

func TestCapabilityDeniedUnknownTool(t *testing.T) {
	s := NewStore()
	_ = s.Register(&AgentIdentity{
		AgentID: "cap-02", AgentName: "A", CreatedBy: "admin", AgentType: AgentAutonomous,
		Capabilities: []ToolPermission{
			{ToolName: "web_search", Permissions: []Permission{PermRead}},
		},
	})
	checker := NewCapabilityChecker(s)
	d := checker.Check("cap-02", "unknown_tool", PermRead)
	if d.Allowed {
		t.Error("should deny unknown tool (fail-safe closed)")
	}
	if d.Reason != "unknown_tool_for_agent" {
		t.Errorf("expected reason unknown_tool_for_agent, got %s", d.Reason)
	}
}

func TestCapabilityDeniedInsufficientPerms(t *testing.T) {
	s := NewStore()
	_ = s.Register(&AgentIdentity{
		AgentID: "cap-03", AgentName: "A", CreatedBy: "admin", AgentType: AgentAutonomous,
		Capabilities: []ToolPermission{
			{ToolName: "web_search", Permissions: []Permission{PermRead}},
		},
	})
	checker := NewCapabilityChecker(s)
	d := checker.Check("cap-03", "web_search", PermWrite)
	if d.Allowed {
		t.Error("should deny WRITE on READ-only tool")
	}
	if d.Reason != "insufficient_permissions" {
		t.Errorf("expected reason insufficient_permissions, got %s", d.Reason)
	}
}

func TestExternalAgentCannotExecute(t *testing.T) {
	s := NewStore()
	_ = s.Register(&AgentIdentity{
		AgentID: "ext-01", AgentName: "External", CreatedBy: "admin", AgentType: AgentExternal,
		Capabilities: []ToolPermission{
			{ToolName: "web_search", Permissions: []Permission{PermRead, PermExecute}},
		},
	})
	checker := NewCapabilityChecker(s)
	d := checker.CheckExternal("ext-01", "web_search", PermExecute)
	if d.Allowed {
		t.Error("external agents should never get EXECUTE permission")
	}
}

// === Namespaced Memory Tests ===

func TestNamespacedMemoryIsolation(t *testing.T) {
	m := NewNamespacedMemory()

	// Agent A stores a value
	m.Store("agent-a", "secret", "classified-data")

	// Agent A can read it
	val, ok := m.Get("agent-a", "secret")
	if !ok || val.(string) != "classified-data" {
		t.Error("agent-a should be able to read its own data")
	}

	// Agent B CANNOT read Agent A's data
	_, ok = m.Get("agent-b", "secret")
	if ok {
		t.Error("agent-b should NOT be able to read agent-a's data")
	}
}

func TestNamespacedMemoryKeys(t *testing.T) {
	m := NewNamespacedMemory()
	m.Store("agent-a", "key1", "v1")
	m.Store("agent-a", "key2", "v2")
	m.Store("agent-b", "key3", "v3")

	keysA := m.Keys("agent-a")
	if len(keysA) != 2 {
		t.Errorf("agent-a should have 2 keys, got %d", len(keysA))
	}

	keysB := m.Keys("agent-b")
	if len(keysB) != 1 {
		t.Errorf("agent-b should have 1 key, got %d", len(keysB))
	}
}

func TestNamespacedMemoryCount(t *testing.T) {
	m := NewNamespacedMemory()
	m.Store("a", "k1", "v1")
	m.Store("a", "k2", "v2")
	m.Store("b", "k1", "v1")

	if m.Count("a") != 2 {
		t.Errorf("agent a should have 2 entries, got %d", m.Count("a"))
	}
	if m.Count("b") != 1 {
		t.Errorf("agent b should have 1 entry, got %d", m.Count("b"))
	}
}

// TestNamespacedMemorySeparatorConfusion is a SECURITY regression: agentIDs
// and keys are arbitrary caller-supplied strings that may contain the "::"
// namespace separator. A naive "agentID::key" scheme lets one agent read,
// overwrite, or enumerate another agent's namespace (M4 isolation bypass).
func TestNamespacedMemorySeparatorConfusion(t *testing.T) {
	m := NewNamespacedMemory()

	// Agent "a::b" writes a private value.
	m.Store("a::b", "secret", "owned-by-a::b")
	// Agent "a" must NOT be able to read it by crafting key "b::secret".
	if v, ok := m.Get("a", "b::secret"); ok {
		t.Errorf("cross-agent read via separator confusion: got %v", v)
	}

	// Agent "a" writes its own value; agent "a::b" must not clobber/read it.
	m.Store("a", "b::x", "owned-by-a")
	if v, ok := m.Get("a::b", "x"); ok {
		t.Errorf("cross-agent read of agent-a data via confusion: got %v", v)
	}
	// Agent "a"'s own value must be intact (not overwritten by "a::b").
	if v, ok := m.Get("a", "b::x"); !ok || v.(string) != "owned-by-a" {
		t.Errorf("agent-a's own value corrupted: got %v ok=%v", v, ok)
	}

	// Keys()/Count() must not leak the OTHER agent's entries.
	if got := m.Count("a"); got != 1 {
		t.Errorf("Count(a) should be 1 (only agent-a's entry), got %d", got)
	}
	for _, k := range m.Keys("a") {
		if k == "secret" {
			t.Errorf("Keys(a) leaked agent-(a::b)'s key %q", k)
		}
	}
	if got := m.Count("a::b"); got != 1 {
		t.Errorf("Count(a::b) should be 1, got %d", got)
	}
}

func TestNamespacedMemoryDelete(t *testing.T) {
	m := NewNamespacedMemory()
	m.Store("a", "key", "val")
	m.Delete("a", "key")
	_, ok := m.Get("a", "key")
	if ok {
		t.Error("key should be deleted")
	}
}

// === Context Pinning Tests ===

func TestSecurityEventsPinned(t *testing.T) {
	messages := []Message{
		{Role: "user", Content: "hello", TokenCount: 100},
		{Role: "security", Content: "injection detected", TokenCount: 50, IsPinned: true, EventType: "injection_detected"},
		{Role: "user", Content: "more chat", TokenCount: 100},
		{Role: "security", Content: "permission denied", TokenCount: 50, IsPinned: true, EventType: "permission_denied"},
		{Role: "user", Content: "latest chat", TokenCount: 100},
	}

	// Total = 400 tokens, budget = 200
	trimmed := TrimContext(messages, 200)

	// Both security events MUST survive
	secCount := 0
	for _, m := range trimmed {
		if m.IsPinned {
			secCount++
		}
	}
	if secCount != 2 {
		t.Errorf("expected 2 pinned security events to survive, got %d", secCount)
	}
}

func TestNonSecurityEventsTrimmed(t *testing.T) {
	messages := []Message{
		{Role: "user", Content: "old msg 1", TokenCount: 100},
		{Role: "user", Content: "old msg 2", TokenCount: 100},
		{Role: "user", Content: "old msg 3", TokenCount: 100},
		{Role: "security", Content: "pinned event", TokenCount: 50, IsPinned: true},
		{Role: "user", Content: "newest msg", TokenCount: 100},
	}

	// Total = 450, budget = 200
	// Pinned = 50, remaining budget = 150 → keep newest msg (100), not enough for old msgs
	trimmed := TrimContext(messages, 200)

	totalTokens := 0
	for _, m := range trimmed {
		totalTokens += m.TokenCount
	}
	if totalTokens > 200 {
		t.Errorf("trimmed context exceeds budget: %d > 200", totalTokens)
	}
}

func TestPinnedByEventType(t *testing.T) {
	if !IsPinnedEvent("injection_detected") {
		t.Error("injection_detected should be pinned")
	}
	if !IsPinnedEvent("credential_access_blocked") {
		t.Error("credential_access_blocked should be pinned")
	}
	if !IsPinnedEvent("genai_credential_access") {
		t.Error("genai_credential_access should be pinned")
	}
	if IsPinnedEvent("normal_chat") {
		t.Error("normal_chat should NOT be pinned")
	}
}

func TestTrimContextWithinBudget(t *testing.T) {
	messages := []Message{
		{Role: "user", Content: "hello", TokenCount: 50},
		{Role: "assistant", Content: "hi", TokenCount: 50},
	}
	// Within budget — no trimming
	trimmed := TrimContext(messages, 1000)
	if len(trimmed) != 2 {
		t.Errorf("expected 2 messages (within budget), got %d", len(trimmed))
	}
}
