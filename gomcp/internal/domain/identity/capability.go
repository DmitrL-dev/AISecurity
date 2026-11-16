package identity

// CapabilityDecision represents the result of a capability check.
type CapabilityDecision struct {
	Allowed  bool   `json:"allowed"`
	AgentID  string `json:"agent_id"`
	ToolName string `json:"tool_name"`
	Reason   string `json:"reason"`
}

// CapabilityChecker verifies agent permissions against the identity store.
// Integrates with DIP Oracle — called before tool execution.
type CapabilityChecker struct {
	store *Store
}

// NewCapabilityChecker creates a capability checker backed by the identity store.
func NewCapabilityChecker(store *Store) *CapabilityChecker {
	return &CapabilityChecker{store: store}
}

// Check verifies that the agent has the required permission for the tool.
// Returns DENY for: unknown agent, unknown tool, missing permission (fail-safe closed).
func (c *CapabilityChecker) Check(agentID, toolName string, perm Permission) CapabilityDecision {
	agent, err := c.store.Get(agentID)
	if err != nil {
		return CapabilityDecision{
			Allowed:  false,
			AgentID:  agentID,
			ToolName: toolName,
			Reason:   "agent_not_found",
		}
	}

	if !agent.HasPermission(toolName, perm) {
		// Determine specific denial reason
		reason := "unknown_tool_for_agent"
		if agent.HasTool(toolName) {
			reason = "insufficient_permissions"
		}
		return CapabilityDecision{
			Allowed:  false,
			AgentID:  agentID,
			ToolName: toolName,
			Reason:   reason,
		}
	}

	// Update last seen timestamp
	_ = c.store.UpdateLastSeen(agentID)

	return CapabilityDecision{
		Allowed:  true,
		AgentID:  agentID,
		ToolName: toolName,
		Reason:   "allowed",
	}
}

// CheckExternal verifies capability for an EXTERNAL agent type.
// External agents have additional restrictions: no EXECUTE permission ever.
func (c *CapabilityChecker) CheckExternal(agentID, toolName string, perm Permission) CapabilityDecision {
	if perm == PermExecute {
		return CapabilityDecision{
			Allowed:  false,
			AgentID:  agentID,
			ToolName: toolName,
			Reason:   "external_agents_cannot_execute",
		}
	}
	return c.Check(agentID, toolName, perm)
}
