package mcpserver

import (
	"context"
	"fmt"
	"net/http"
	"net/url"
	"strings"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"

	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
)

func (s *Server) scopeMiddleware() server.ToolHandlerMiddleware {
	return func(next server.ToolHandlerFunc) server.ToolHandlerFunc {
		return func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
			sc, err := s.scopeForRequest(req)
			if err != nil {
				return errorResult(err), nil
			}
			return next(rlmscope.WithScope(ctx, sc), req)
		}
	}
}

func (s *Server) resourceScopeMiddleware() server.ResourceHandlerMiddleware {
	return func(next server.ResourceHandlerFunc) server.ResourceHandlerFunc {
		return func(ctx context.Context, req mcp.ReadResourceRequest) ([]mcp.ResourceContents, error) {
			sc, err := s.scopeForResource(req)
			if err != nil {
				return nil, err
			}
			return next(rlmscope.WithScope(ctx, sc), req)
		}
	}
}

func (s *Server) scopedContext(ctxs ...context.Context) context.Context {
	ctx := context.Background()
	if len(ctxs) > 0 && ctxs[0] != nil {
		ctx = ctxs[0]
	}
	if sc, ok := rlmscope.Lookup(ctx); ok {
		return rlmscope.WithScope(ctx, sc)
	}
	return rlmscope.WithScope(ctx, s.scope)
}

func (s *Server) defaultScopeContext(ctx context.Context) (context.Context, rlmscope.Scope, error) {
	sc := rlmscope.Default()
	if _, err := s.enforceScopeLock(sc); err != nil {
		return nil, sc, err
	}
	return rlmscope.WithScope(ctx, sc), sc, nil
}

func (s *Server) scopeForRequest(req mcp.CallToolRequest) (rlmscope.Scope, error) {
	tenantID := ""
	projectID := ""

	readHeaderScope(req.Header, &tenantID, &projectID)
	readMapScope(req.GetArguments(), &tenantID, &projectID)
	if req.Params.Meta != nil {
		readMapScope(req.Params.Meta.AdditionalFields, &tenantID, &projectID)
	}
	if req.Request.Params.Meta != nil {
		readMapScope(req.Request.Params.Meta.AdditionalFields, &tenantID, &projectID)
	}

	sc, err := s.resolveScope(tenantID, projectID)
	if err != nil {
		return rlmscope.Scope{}, err
	}
	return s.enforceScopeLock(sc)
}

// requiredMetaScope returns the tenant/project boundary carried explicitly in
// _meta.rlm_scope. Dedicated exact-memory tools use this instead of the
// compatibility resolver because headers, arguments, and the server default are
// all broader/ambiguous authority sources for scoped reads and writes.
func (s *Server) requiredMetaScope(req mcp.CallToolRequest) (rlmscope.Scope, error) {
	var resolved *rlmscope.Scope
	metas := []*mcp.Meta{req.Params.Meta, req.Request.Params.Meta}
	for _, meta := range metas {
		if meta == nil || meta.AdditionalFields == nil {
			continue
		}
		raw, present := meta.AdditionalFields["rlm_scope"]
		if !present {
			continue
		}
		values, ok := raw.(map[string]any)
		if !ok {
			return rlmscope.Scope{}, fmt.Errorf("_meta.rlm_scope must be an object with tenant_id and project_id")
		}
		tenantID, tenantOK := values["tenant_id"].(string)
		projectID, projectOK := values["project_id"].(string)
		if !tenantOK || !projectOK || strings.TrimSpace(tenantID) == "" || strings.TrimSpace(projectID) == "" {
			return rlmscope.Scope{}, fmt.Errorf("_meta.rlm_scope.tenant_id and project_id are required for exact memory operations")
		}
		if tenantID != strings.TrimSpace(tenantID) {
			return rlmscope.Scope{}, fmt.Errorf("invalid _meta.rlm_scope: tenant_id must not contain surrounding whitespace")
		}
		if err := rlmscope.ValidateExactProjectID(projectID); err != nil {
			return rlmscope.Scope{}, fmt.Errorf("invalid _meta.rlm_scope: %w", err)
		}
		sc := rlmscope.Scope{TenantID: tenantID, ProjectID: projectID}
		if err := sc.Validate(); err != nil {
			return rlmscope.Scope{}, fmt.Errorf("invalid _meta.rlm_scope: %w", err)
		}
		if resolved != nil && *resolved != sc {
			return rlmscope.Scope{}, fmt.Errorf("conflicting _meta.rlm_scope values")
		}
		resolved = &sc
	}
	if resolved == nil {
		return rlmscope.Scope{}, fmt.Errorf("_meta.rlm_scope with tenant_id and project_id is required for exact memory operations")
	}
	return s.enforceScopeLock(*resolved)
}

func (s *Server) sessionMemoryContext(ctx context.Context, req mcp.CallToolRequest) (context.Context, error) {
	explicitCtx, _, err := s.explicitMetaScopeContext(ctx, req)
	return explicitCtx, err
}

// explicitMetaScopeContext binds only the scope carried in _meta.rlm_scope.
// It is shared by rollback-safe memory tools whose authority must never come
// from legacy headers, arguments, or the server's compatibility default.
func (s *Server) explicitMetaScopeContext(ctx context.Context, req mcp.CallToolRequest) (context.Context, rlmscope.Scope, error) {
	sc, err := s.requiredMetaScope(req)
	if err != nil {
		return nil, rlmscope.Scope{}, err
	}
	if middlewareScope, ok := rlmscope.Lookup(ctx); ok && middlewareScope != sc {
		return nil, rlmscope.Scope{}, fmt.Errorf("explicit _meta.rlm_scope does not match middleware scope")
	}
	return rlmscope.WithScope(ctx, sc), sc, nil
}

func (s *Server) scopeForResource(req mcp.ReadResourceRequest) (rlmscope.Scope, error) {
	tenantID := ""
	projectID := ""

	readHeaderScope(req.Header, &tenantID, &projectID)
	readMapScope(req.Params.Arguments, &tenantID, &projectID)
	readURIQueryScope(req.Params.URI, &tenantID, &projectID)

	sc, err := s.resolveScope(tenantID, projectID)
	if err != nil {
		return rlmscope.Scope{}, err
	}
	return s.enforceScopeLock(sc)
}

// resolveScope fills any unset tenant/project from the server's pinned scope and
// validates the result. It does NOT authorize the scope — see enforceScopeLock.
func (s *Server) resolveScope(tenantID, projectID string) (rlmscope.Scope, error) {
	if strings.TrimSpace(tenantID) == "" && strings.TrimSpace(projectID) == "" {
		return s.scope.Normalize(), nil
	}
	base := s.scope.Normalize()
	if strings.TrimSpace(tenantID) == "" {
		tenantID = base.TenantID
	}
	if strings.TrimSpace(projectID) == "" {
		projectID = base.ProjectID
	}
	sc := rlmscope.New(tenantID, projectID)
	if err := sc.Validate(); err != nil {
		return rlmscope.Scope{}, err
	}
	return sc, nil
}

// enforceScopeLock rejects a client-supplied scope that differs from the
// server's pinned scope when the server runs locked (hosted multi-tenant mode).
// This closes the cross-tenant access path: without it, a tenant_id/project_id
// in a tool argument, _meta, or header would override the operator-pinned scope
// and reach another tenant's rows in the shared memory DB. In the default
// (unlocked) single-tenant deployment the client is trusted and may switch
// scope (e.g. across its own projects).
func (s *Server) enforceScopeLock(sc rlmscope.Scope) (rlmscope.Scope, error) {
	if s.locked && sc != s.scope.Normalize() {
		return rlmscope.Scope{}, fmt.Errorf("scope override is not permitted: server is locked to a single tenant/project (hosted mode)")
	}
	return sc, nil
}

func readHeaderScope(header http.Header, tenantID, projectID *string) {
	if header == nil {
		return
	}
	setIfPresent(tenantID, header.Get("X-GoMCP-Tenant-ID"))
	setIfPresent(projectID, header.Get("X-GoMCP-Project-ID"))
	setIfPresent(tenantID, header.Get("X-RLM-Tenant-ID"))
	setIfPresent(projectID, header.Get("X-RLM-Project-ID"))
}

func readMapScope(values map[string]any, tenantID, projectID *string) {
	if len(values) == 0 {
		return
	}
	setIfPresent(tenantID, mapString(values, "tenant_id"))
	setIfPresent(projectID, mapString(values, "project_id"))
	setIfPresent(tenantID, mapString(values, "rlm_tenant_id"))
	setIfPresent(projectID, mapString(values, "rlm_project_id"))

	for _, key := range []string{"rlm_scope", "gomcp_scope", "scope"} {
		if nested, ok := values[key].(map[string]any); ok {
			readMapScope(nested, tenantID, projectID)
		}
	}
}

func readURIQueryScope(rawURI string, tenantID, projectID *string) {
	parsed, err := url.Parse(rawURI)
	if err != nil {
		return
	}
	values := parsed.Query()
	setIfPresent(tenantID, values.Get("tenant_id"))
	setIfPresent(projectID, values.Get("project_id"))
	setIfPresent(tenantID, values.Get("rlm_tenant_id"))
	setIfPresent(projectID, values.Get("rlm_project_id"))
}

func mapString(values map[string]any, key string) string {
	raw, ok := values[key]
	if !ok {
		return ""
	}
	switch v := raw.(type) {
	case string:
		return v
	case []string:
		// mcp-go populates URI-template path variables (e.g. the {tenant_id}
		// segment of rlm://scope/{tenant_id}/{project_id}/...) as []string, not
		// string. Without this case the scoped-resource templates silently drop
		// their path scope and fall back to the server default.
		for _, item := range v {
			if strings.TrimSpace(item) != "" {
				return item
			}
		}
	case []any:
		for _, item := range v {
			if str, ok := item.(string); ok && strings.TrimSpace(str) != "" {
				return str
			}
		}
	}
	return ""
}

func resourceArgString(req mcp.ReadResourceRequest, key string) string {
	return mapString(req.Params.Arguments, key)
}

func setIfPresent(target *string, value string) {
	if trimmed := strings.TrimSpace(value); trimmed != "" {
		*target = trimmed
	}
}
