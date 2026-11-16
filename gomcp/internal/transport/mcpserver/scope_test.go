package mcpserver

import (
	"context"
	"net/http"
	"testing"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/stretchr/testify/require"

	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
)

func TestScopeForRequestUsesMetaArgumentsAndHeaders(t *testing.T) {
	srv := &Server{scope: rlmscope.New("tenant-a", "project-alpha")}

	req := callToolReq("x", map[string]interface{}{"project_id": "project-beta"})
	req.Params.Meta = &mcp.Meta{AdditionalFields: map[string]any{
		"rlm_scope": map[string]any{"tenant_id": "tenant-b"},
	}}
	sc, err := srv.scopeForRequest(req)
	require.NoError(t, err)
	require.Equal(t, "tenant-b", sc.TenantID)
	require.Equal(t, "project-beta", sc.ProjectID)

	req = callToolReq("x", nil)
	req.Header = http.Header{}
	req.Header.Set("X-RLM-Tenant-ID", "tenant-c")
	req.Header.Set("X-RLM-Project-ID", "project-gamma")
	sc, err = srv.scopeForRequest(req)
	require.NoError(t, err)
	require.Equal(t, "tenant-c", sc.TenantID)
	require.Equal(t, "project-gamma", sc.ProjectID)
}

func TestScopeForRequestRejectsInvalidScopeID(t *testing.T) {
	srv := &Server{scope: rlmscope.New("tenant-a", "project-alpha")}

	req := callToolReq("x", map[string]interface{}{"project_id": "bad/project"})
	_, err := srv.scopeForRequest(req)
	require.ErrorContains(t, err, "unsupported character")
}

// Pre-launch audit 20.06 (F1, HIGH): in hosted/locked mode a client-supplied
// tenant_id/project_id must NOT be able to override the operator-pinned scope
// (cross-tenant memory access). The default (unlocked) single-tenant server must
// still allow scope switching so the legitimate project-switch feature does not
// regress.
func TestScopeLockRejectsCrossTenantOverride(t *testing.T) {
	pinned := rlmscope.New("tenant-a", "project-alpha")
	locked := &Server{scope: pinned, locked: true}

	// Cross-tenant via tool argument -> rejected.
	_, err := locked.scopeForRequest(callToolReq("x", map[string]interface{}{"tenant_id": "tenant-b"}))
	require.Error(t, err)
	require.ErrorContains(t, err, "not permitted")

	// Cross-tenant via _meta.rlm_scope -> rejected.
	req := callToolReq("x", nil)
	req.Params.Meta = &mcp.Meta{AdditionalFields: map[string]any{
		"rlm_scope": map[string]any{"tenant_id": "tenant-b"},
	}}
	_, err = locked.scopeForRequest(req)
	require.Error(t, err)

	// Cross-tenant via header -> rejected.
	req = callToolReq("x", nil)
	req.Header = http.Header{}
	req.Header.Set("X-RLM-Tenant-ID", "tenant-b")
	_, err = locked.scopeForRequest(req)
	require.Error(t, err)

	// Cross-project within the pinned tenant is also locked in hosted mode.
	_, err = locked.scopeForRequest(callToolReq("x", map[string]interface{}{"project_id": "project-beta"}))
	require.Error(t, err)

	// Resource path is locked too (query-string override).
	rreq := mcp.ReadResourceRequest{}
	rreq.Params.URI = "rlm://facts?tenant_id=tenant-b&project_id=project-beta"
	_, err = locked.scopeForResource(rreq)
	require.Error(t, err)

	// No override -> pinned scope, allowed.
	sc, err := locked.scopeForRequest(callToolReq("x", nil))
	require.NoError(t, err)
	require.Equal(t, "tenant-a", sc.TenantID)
	require.Equal(t, "project-alpha", sc.ProjectID)

	// Override that matches the pinned scope -> allowed.
	sc, err = locked.scopeForRequest(callToolReq("x", map[string]interface{}{"tenant_id": "tenant-a", "project_id": "project-alpha"}))
	require.NoError(t, err)
	require.Equal(t, "tenant-a", sc.TenantID)

	// Default (unlocked) single-tenant server still switches scope freely.
	unlocked := &Server{scope: pinned}
	sc, err = unlocked.scopeForRequest(callToolReq("x", map[string]interface{}{"tenant_id": "tenant-b"}))
	require.NoError(t, err)
	require.Equal(t, "tenant-b", sc.TenantID)
}

func TestResourceScopeMiddlewareUsesTemplateArgumentsAndURIQuery(t *testing.T) {
	srv := &Server{scope: rlmscope.New("tenant-a", "project-alpha")}
	handler := srv.resourceScopeMiddleware()(func(ctx context.Context, req mcp.ReadResourceRequest) ([]mcp.ResourceContents, error) {
		sc := rlmscope.FromContext(ctx)
		return []mcp.ResourceContents{mcp.TextResourceContents{URI: req.Params.URI, Text: sc.String()}}, nil
	})

	req := mcp.ReadResourceRequest{}
	req.Params.URI = "rlm://scope/tenant-b/project-beta/facts"
	req.Params.Arguments = map[string]any{"tenant_id": "tenant-b", "project_id": "project-beta"}
	contents, err := handler(context.Background(), req)
	require.NoError(t, err)
	require.Equal(t, "tenant-b/project-beta", contents[0].(mcp.TextResourceContents).Text)

	req = mcp.ReadResourceRequest{}
	req.Params.URI = "rlm://facts?tenant_id=tenant-c&project_id=project-gamma"
	contents, err = handler(context.Background(), req)
	require.NoError(t, err)
	require.Equal(t, "tenant-c/project-gamma", contents[0].(mcp.TextResourceContents).Text)
}

// Pre-launch audit 20.06 (F2): the real mcp-go library delivers URI-template
// path variables as []string, so scoped-resource templates must read []string
// args (the template test above pre-seeds plain strings and masked this). Drive
// the []string form directly and assert the path scope is honored.
func TestScopeForResourceParsesTemplateStringSlices(t *testing.T) {
	srv := &Server{scope: rlmscope.New("tenant-a", "project-alpha")}
	req := mcp.ReadResourceRequest{}
	req.Params.URI = "rlm://scope/tenant-b/project-beta/facts"
	req.Params.Arguments = map[string]any{
		"tenant_id":  []string{"tenant-b"},
		"project_id": []string{"project-beta"},
	}
	sc, err := srv.scopeForResource(req)
	require.NoError(t, err)
	require.Equal(t, "tenant-b", sc.TenantID)
	require.Equal(t, "project-beta", sc.ProjectID)
}
