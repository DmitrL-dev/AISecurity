package scope

import (
	"context"
	"fmt"
	"strings"
)

const (
	DefaultTenantID  = "local"
	DefaultProjectID = "default"
)

// Scope identifies the tenant/project boundary for RLM data.
type Scope struct {
	TenantID  string `json:"tenant_id"`
	ProjectID string `json:"project_id"`
}

type contextKey struct{}

// New returns a normalized RLM scope.
func New(tenantID, projectID string) Scope {
	return Scope{TenantID: tenantID, ProjectID: projectID}.Normalize()
}

// Default returns the local single-project scope used for backward compatibility.
func Default() Scope {
	return Scope{TenantID: DefaultTenantID, ProjectID: DefaultProjectID}
}

// Normalize fills empty values with the local single-project defaults.
func (s Scope) Normalize() Scope {
	s.TenantID = strings.TrimSpace(s.TenantID)
	s.ProjectID = strings.TrimSpace(s.ProjectID)
	if s.TenantID == "" {
		s.TenantID = DefaultTenantID
	}
	if s.ProjectID == "" {
		s.ProjectID = DefaultProjectID
	}
	return s
}

// IsDefault reports whether the scope is the backward-compatible local scope.
func (s Scope) IsDefault() bool {
	s = s.Normalize()
	return s.TenantID == DefaultTenantID && s.ProjectID == DefaultProjectID
}

func (s Scope) String() string {
	s = s.Normalize()
	return fmt.Sprintf("%s/%s", s.TenantID, s.ProjectID)
}

// WithScope attaches an RLM scope to a context.
func WithScope(ctx context.Context, s Scope) context.Context {
	if ctx == nil {
		ctx = context.Background()
	}
	// Keep the caller's spelling in the private context value so exact-memory
	// boundaries can reject normalization aliases. Legacy readers still receive
	// the historical normalized value through Lookup and FromContext.
	return context.WithValue(ctx, contextKey{}, s)
}

// FromContext returns the RLM scope attached to ctx, or the local default.
func FromContext(ctx context.Context) Scope {
	if ctx == nil {
		return Default()
	}
	if s, ok := ctx.Value(contextKey{}).(Scope); ok {
		return s.Normalize()
	}
	return Default()
}

// Lookup returns the scope attached to ctx and whether it was explicitly set.
func Lookup(ctx context.Context) (Scope, bool) {
	if ctx == nil {
		return Scope{}, false
	}
	if s, ok := ctx.Value(contextKey{}).(Scope); ok {
		return s.Normalize(), true
	}
	return Scope{}, false
}

func lookupRaw(ctx context.Context) (Scope, bool) {
	if ctx == nil {
		return Scope{}, false
	}
	s, ok := ctx.Value(contextKey{}).(Scope)
	return s, ok
}

// ValidateID checks tenant/project identifiers used as storage scope keys.
func ValidateID(name, id string) error {
	id = strings.TrimSpace(id)
	if id == "" {
		return fmt.Errorf("%s is required", name)
	}
	if len(id) > 128 {
		return fmt.Errorf("%s is too long", name)
	}
	for _, r := range id {
		if r >= 'a' && r <= 'z' || r >= 'A' && r <= 'Z' || r >= '0' && r <= '9' ||
			r == '.' || r == '_' || r == '-' {
			continue
		}
		return fmt.Errorf("%s contains unsupported character %q", name, r)
	}
	return nil
}

// ValidateSessionID validates an exact conversation-memory session key.
//
// Tenant and project identifiers are normalized at the API boundary for backward
// compatibility. A session identifier is different: it is an exact third storage
// dimension, so silently trimming it would make two caller-visible values address
// the same memory. Reject surrounding whitespace instead.
func ValidateSessionID(id string) error {
	if id != strings.TrimSpace(id) {
		return fmt.Errorf("session_id must not contain surrounding whitespace")
	}
	return ValidateID("session_id", id)
}

// ValidateTurnID accepts only gateway-generated, content-free operation IDs.
// The exact grammar keeps arbitrary request text out of durable receipts and
// makes accidental use of a session/project identifier impossible.
func ValidateTurnID(id string) error {
	const prefix = "turn_"
	if len(id) != len(prefix)+64 || !strings.HasPrefix(id, prefix) {
		return fmt.Errorf("turn_id must match turn_[0-9a-f]{64}")
	}
	for _, char := range id[len(prefix):] {
		if !((char >= '0' && char <= '9') || (char >= 'a' && char <= 'f')) {
			return fmt.Errorf("turn_id must match turn_[0-9a-f]{64}")
		}
	}
	return nil
}

// ValidateExactProjectID applies the public scoped-memory project grammar.
// Unlike the legacy ValidateID path it rejects normalization aliases and
// requires the first byte to be an ASCII letter or digit.
func ValidateExactProjectID(id string) error {
	if id != strings.TrimSpace(id) {
		return fmt.Errorf("project_id must not contain surrounding whitespace")
	}
	if err := ValidateID("project_id", id); err != nil {
		return err
	}
	first := id[0]
	if !((first >= 'a' && first <= 'z') || (first >= 'A' && first <= 'Z') ||
		(first >= '0' && first <= '9')) {
		return fmt.Errorf("project_id must start with an ASCII letter or digit")
	}
	return nil
}

// Require returns an explicitly bound, valid tenant/project boundary. Unlike
// FromContext it never invents local/default when a caller forgot the scope.
func Require(ctx context.Context) (Scope, error) {
	sc, ok := Lookup(ctx)
	if !ok {
		return Scope{}, fmt.Errorf("explicit tenant_id/project_id scope is required")
	}
	if err := sc.Validate(); err != nil {
		return Scope{}, fmt.Errorf("invalid tenant_id/project_id scope: %w", err)
	}
	return sc, nil
}

// RequireExactProject returns an explicitly bound tenant/project boundary
// outside the backward-compatible legacy bucket. The case-insensitive
// "default" project is reserved and must not be used by exact memory APIs.
func RequireExactProject(ctx context.Context) (Scope, error) {
	sc, err := Require(ctx)
	if err != nil {
		return Scope{}, err
	}
	raw, ok := lookupRaw(ctx)
	if !ok {
		return Scope{}, fmt.Errorf("explicit tenant_id/project_id scope is required")
	}
	if raw.TenantID != strings.TrimSpace(raw.TenantID) {
		return Scope{}, fmt.Errorf("tenant_id must not contain surrounding whitespace")
	}
	if err := ValidateExactProjectID(raw.ProjectID); err != nil {
		return Scope{}, err
	}
	if strings.EqualFold(sc.ProjectID, DefaultProjectID) {
		return Scope{}, fmt.Errorf("project_id %q is reserved for legacy memory", sc.ProjectID)
	}
	return sc, nil
}

// RequireSessionProject returns an explicitly bound project that can host
// conversation memory.
func RequireSessionProject(ctx context.Context) (Scope, error) {
	sc, err := RequireExactProject(ctx)
	if err != nil {
		return Scope{}, fmt.Errorf("session memory: %w", err)
	}
	return sc, nil
}

// RequireSessionScope resolves the three exact dimensions required by
// conversation memory.
func RequireSessionScope(ctx context.Context, sessionID string) (Scope, error) {
	sc, err := RequireSessionProject(ctx)
	if err != nil {
		return Scope{}, err
	}
	if err := ValidateSessionID(sessionID); err != nil {
		return Scope{}, err
	}
	return sc, nil
}

// Validate checks both identifiers in a normalized scope.
func (s Scope) Validate() error {
	s = s.Normalize()
	if err := ValidateID("tenant_id", s.TenantID); err != nil {
		return err
	}
	return ValidateID("project_id", s.ProjectID)
}
