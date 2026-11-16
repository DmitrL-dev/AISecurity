package scope

import (
	"context"
	"fmt"
)

// RequireExactDefault accepts only an explicitly bound raw local/default
// scope. Unlike Require, it rejects empty or whitespace-normalized aliases.
func RequireExactDefault(ctx context.Context) (Scope, error) {
	raw, ok := lookupRaw(ctx)
	if !ok {
		return Scope{}, fmt.Errorf("explicit tenant_id/project_id scope is required")
	}
	if raw.TenantID != DefaultTenantID || raw.ProjectID != DefaultProjectID {
		return Scope{}, fmt.Errorf("default scope must be exactly %s/%s", DefaultTenantID, DefaultProjectID)
	}
	return Default(), nil
}
