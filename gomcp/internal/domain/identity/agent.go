// Package identity implements Non-Human Identity (NHI) for AI agents (SDD-003).
//
// Each agent has a unique AgentIdentity with capabilities (tool permissions),
// constraints, and a delegation chain showing trust ancestry.
package identity

import "time"

// AgentType classifies the autonomy level of an agent.
type AgentType string

const (
	AgentAutonomous AgentType = "AUTONOMOUS" // Self-directed, no human in loop
	AgentSupervised AgentType = "SUPERVISED" // Human-in-the-loop for critical decisions
	AgentExternal   AgentType = "EXTERNAL"   // Third-party agent, minimal trust
)

// Permission represents an operation type for tool access control.
type Permission string

const (
	PermRead    Permission = "READ"
	PermWrite   Permission = "WRITE"
	PermExecute Permission = "EXECUTE"
	PermSend    Permission = "SEND"
)

// AgentIdentity represents a Non-Human Identity (NHI) for an AI agent.
type AgentIdentity struct {
	AgentID         string            `json:"agent_id"`
	AgentName       string            `json:"agent_name"`
	AgentType       AgentType         `json:"agent_type"`
	CreatedBy       string            `json:"created_by"`        // Human principal who deployed
	DelegationChain []DelegationLink  `json:"delegation_chain"`  // Trust ancestry chain
	Capabilities    []ToolPermission  `json:"capabilities"`      // Per-tool allowlists
	Constraints     AgentConstraints  `json:"constraints"`       // Operational limits
	Tags            map[string]string `json:"tags,omitempty"`    // Arbitrary metadata
	CreatedAt       time.Time         `json:"created_at"`
	LastSeenAt      time.Time         `json:"last_seen_at"`
}

// DelegationLink records one step in the trust delegation chain.
type DelegationLink struct {
	DelegatorID   string    `json:"delegator_id"`   // Who delegated
	DelegatorType string    `json:"delegator_type"` // "human" | "agent"
	Scope         string    `json:"scope"`          // What was delegated
	GrantedAt     time.Time `json:"granted_at"`
}

// ToolPermission defines what an agent is allowed to do with a specific tool.
type ToolPermission struct {
	ToolName    string       `json:"tool_name"`
	Permissions []Permission `json:"permissions"`
}

// AgentConstraints defines operational limits for an agent.
type AgentConstraints struct {
	MaxTokensPerTurn    int    `json:"max_tokens_per_turn,omitempty"`
	MaxToolCallsPerTurn int    `json:"max_tool_calls_per_turn,omitempty"`
	PIDetectionLevel    string `json:"pi_detection_level"` // "strict" | "standard" | "relaxed"
	AllowExternalComms  bool   `json:"allow_external_comms"`
}

// HasPermission checks if the agent has a specific permission for a specific tool.
// Returns false for unknown tools (fail-safe closed — SDD-003 M3).
func (a *AgentIdentity) HasPermission(toolName string, perm Permission) bool {
	for _, cap := range a.Capabilities {
		if cap.ToolName == toolName {
			for _, p := range cap.Permissions {
				if p == perm {
					return true
				}
			}
			return false // Tool known but permission not granted
		}
	}
	return false // Unknown tool → DENY (fail-safe closed)
}

// HasTool returns true if the agent has ANY permission for the specified tool.
func (a *AgentIdentity) HasTool(toolName string) bool {
	for _, cap := range a.Capabilities {
		if cap.ToolName == toolName {
			return len(cap.Permissions) > 0
		}
	}
	return false
}

// ToolNames returns the list of all tools this agent has access to.
func (a *AgentIdentity) ToolNames() []string {
	names := make([]string, 0, len(a.Capabilities))
	for _, cap := range a.Capabilities {
		names = append(names, cap.ToolName)
	}
	return names
}

// Validate checks required fields.
func (a *AgentIdentity) Validate() error {
	if a.AgentID == "" {
		return ErrMissingAgentID
	}
	if a.AgentName == "" {
		return ErrMissingAgentName
	}
	if a.CreatedBy == "" {
		return ErrMissingCreatedBy
	}
	switch a.AgentType {
	case AgentAutonomous, AgentSupervised, AgentExternal:
		// valid
	default:
		return ErrInvalidAgentType
	}
	return nil
}
