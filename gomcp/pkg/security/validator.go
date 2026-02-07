package security

import (
	"context"
	"fmt"
)

// ClientInfo represents information about the connecting client
type ClientInfo struct {
	Name    string `json:"name"`
	Version string `json:"version"`
}

// ClientValidator validates incoming client connections
type ClientValidator interface {
	Validate(ctx context.Context, clientInfo ClientInfo) error
}

// StrictValidator implements strict validation policies
type StrictValidator struct {
	blockedClientIDs map[string]bool
}

// NewStrictValidator creates a validator with default security policies
func NewStrictValidator() *StrictValidator {
	return &StrictValidator{
		blockedClientIDs: map[string]bool{
			"mcp-proxy": true, // Block shared proxy ID
			"unknown":   true,
			"":          true, // Block empty ID in strict mode
		},
	}
}

// Validate checks if the client is allowed to connect
func (v *StrictValidator) Validate(ctx context.Context, clientInfo ClientInfo) error {
	// 1. Check for empty name
	if clientInfo.Name == "" {
		return fmt.Errorf("client name is required (strict mode)")
	}

	// 2. Check blocklist
	if v.blockedClientIDs[clientInfo.Name] {
		return fmt.Errorf("security error: client_id '%s' is blocked by security policy", clientInfo.Name)
	}

	return nil
}

// PermissiveValidator allows everything (useful for dev/legacy)
type PermissiveValidator struct{}

func NewPermissiveValidator() *PermissiveValidator {
	return &PermissiveValidator{}
}

func (v *PermissiveValidator) Validate(ctx context.Context, clientInfo ClientInfo) error {
	return nil
}
