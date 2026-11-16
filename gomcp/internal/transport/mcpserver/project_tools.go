package mcpserver

import (
	"context"
	"errors"
	"fmt"
	"strings"

	"github.com/mark3labs/mcp-go/mcp"

	"github.com/syntrex/gomcp/internal/application/tools"
	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
)

func (s *Server) registerProjectTools() {
	s.mcp.AddTool(
		mcp.NewTool("store_project_fact_exact",
			mcp.WithDescription("Store one exact non-session fact in an explicit non-default project. A live legacy-key collision is read-only when every accepted field matches and is otherwise a typed conflict."),
			mcp.WithString("content", mcp.Description("Fact content"), mcp.Required()),
			mcp.WithNumber("level", mcp.Description("Hierarchy level: 0=project, 1=domain, 2=module, 3=snippet"), mcp.Min(0), mcp.Max(3), mcp.MultipleOf(1), mcp.Required()),
			mcp.WithString("domain", mcp.Description("Domain category")),
			mcp.WithString("module", mcp.Description("Module name")),
			mcp.WithString("origin", mcp.Description("Content origin; omitted means external"), mcp.Enum("user", "derived", "external")),
		),
		s.handleStoreProjectFactExact,
	)

	s.mcp.AddTool(
		mcp.NewTool("use_project",
			mcp.WithDescription("Ensure an RLM tenant/project scope for this request. The server scope is not mutated; pass the same scope in _meta.rlm_scope or X-RLM headers on later calls."),
			mcp.WithString("tenant_id", mcp.Description("Tenant ID. Defaults to the server tenant.")),
			mcp.WithString("project_id", mcp.Description("Project ID: letters, numbers, dot, underscore, dash"), mcp.Required()),
			mcp.WithString("name", mcp.Description("Display name")),
		),
		s.handleUseProject,
	)

	s.mcp.AddTool(
		mcp.NewTool("current_project",
			mcp.WithDescription("Show the active RLM tenant/project scope and project stats."),
		),
		s.handleCurrentProject,
	)

	// Rollback-safe, read-only project confirmation for callers that require an
	// explicit scope. Unlike current_project this never Ensures or touches a
	// registry row and accepts authority only from _meta.rlm_scope.
	s.mcp.AddTool(
		mcp.NewTool("inspect_current_project",
			mcp.WithDescription("Confirm an existing RLM project without creating or touching it. Requires explicit _meta.rlm_scope."),
		),
		s.handleInspectCurrentProject,
	)

	s.mcp.AddTool(
		mcp.NewTool("project_fact_stats",
			mcp.WithDescription("Read non-session fact statistics for one exact non-default project. Requires explicit _meta.rlm_scope."),
		),
		s.handleProjectFactStats,
	)

	s.mcp.AddTool(
		mcp.NewTool("list_default_facts_page",
			mcp.WithDescription("Read one bounded base64-framed page of non-session facts from local/default. Scope headers, arguments, and _meta overrides are rejected."),
			mcp.WithNumber("level", mcp.Description("Exact hierarchy level (0-3)"), mcp.Min(0), mcp.Max(3), mcp.MultipleOf(1), mcp.Required()),
			mcp.WithNumber("max_fact_bytes", mcp.Description("Maximum serialized bytes accepted for one fact (1-16777216)"), mcp.Min(1), mcp.Max(16*1024*1024), mcp.MultipleOf(1), mcp.Required()),
			mcp.WithString("cursor", mcp.Description("Opaque continuation cursor returned by the previous page")),
		),
		s.handleListDefaultFactsPage,
	)

	s.mcp.AddTool(
		mcp.NewTool("list_project_facts_page",
			mcp.WithDescription("Read one bounded base64-framed page of non-session facts from an exact non-default project. Requires explicit _meta.rlm_scope."),
			mcp.WithNumber("level", mcp.Description("Exact hierarchy level (0-3)"), mcp.Min(0), mcp.Max(3), mcp.MultipleOf(1), mcp.Required()),
			mcp.WithNumber("max_fact_bytes", mcp.Description("Maximum serialized bytes accepted for one fact (1-16777216)"), mcp.Min(1), mcp.Max(16*1024*1024), mcp.MultipleOf(1), mcp.Required()),
			mcp.WithString("cursor", mcp.Description("Opaque continuation cursor returned by the previous page")),
		),
		s.handleListProjectFactsPage,
	)

	s.mcp.AddTool(
		mcp.NewTool("list_projects",
			mcp.WithDescription("List RLM projects for the current tenant."),
			mcp.WithBoolean("include_archived", mcp.Description("Include archived projects")),
		),
		s.handleListProjects,
	)

	s.mcp.AddTool(
		mcp.NewTool("create_project",
			mcp.WithDescription("Create or reactivate an RLM project in the current tenant."),
			mcp.WithString("project_id", mcp.Description("Project ID: letters, numbers, dot, underscore, dash"), mcp.Required()),
			mcp.WithString("name", mcp.Description("Display name")),
		),
		s.handleCreateProject,
	)

	s.mcp.AddTool(
		mcp.NewTool("archive_project",
			mcp.WithDescription("Archive an RLM project in the current tenant without deleting its data."),
			mcp.WithString("project_id", mcp.Description("Project ID to archive"), mcp.Required()),
		),
		s.handleArchiveProject,
	)

	s.mcp.AddTool(
		mcp.NewTool("activate_project",
			mcp.WithDescription("Reactivate an archived RLM project in the current tenant."),
			mcp.WithString("project_id", mcp.Description("Project ID to activate"), mcp.Required()),
		),
		s.handleActivateProject,
	)

	s.mcp.AddTool(
		mcp.NewTool("project_stats",
			mcp.WithDescription("Inspect one RLM project in the current tenant. Defaults to the active project."),
			mcp.WithString("project_id", mcp.Description("Project ID to inspect")),
		),
		s.handleProjectStats,
	)
}

type projectExactFactStoreEnvelope struct {
	MemoryScope factPageMemoryScope `json:"memory_scope"`
	Fact        *memory.Fact        `json:"fact"`
	Created     bool                `json:"created"`
}

func exactOptionalStringArgument(arguments map[string]any, name string) (string, error) {
	raw, present := arguments[name]
	if !present {
		return "", nil
	}
	value, ok := raw.(string)
	if !ok {
		return "", fmt.Errorf("%s must be a string", name)
	}
	return value, nil
}

func (s *Server) handleStoreProjectFactExact(
	ctx context.Context,
	req mcp.CallToolRequest,
) (*mcp.CallToolResult, error) {
	explicitCtx, sc, err := s.explicitMetaScopeContext(ctx, req)
	if err != nil {
		return factPageErrorResult(nil, "invalid_scope", err.Error()), nil
	}
	if _, err := rlmscope.RequireExactProject(explicitCtx); err != nil {
		return factPageErrorResult(&sc, "invalid_scope", err.Error()), nil
	}

	arguments := req.GetArguments()
	for name := range arguments {
		switch name {
		case "content", "level", "domain", "module", "origin":
		default:
			return factPageErrorResult(&sc, "invalid_arguments", "request contains an unknown argument"), nil
		}
	}
	content, ok := arguments["content"].(string)
	if !ok || strings.TrimSpace(content) == "" {
		return factPageErrorResult(&sc, "invalid_arguments", "content must be a non-empty string"), nil
	}
	level, err := exactIntegerArgument(arguments, "level")
	if err != nil || level < 0 || level > 3 {
		return factPageErrorResult(&sc, "invalid_arguments", "level must be an integer from 0 through 3"), nil
	}
	domain, err := exactOptionalStringArgument(arguments, "domain")
	if err != nil {
		return factPageErrorResult(&sc, "invalid_arguments", err.Error()), nil
	}
	module, err := exactOptionalStringArgument(arguments, "module")
	if err != nil {
		return factPageErrorResult(&sc, "invalid_arguments", err.Error()), nil
	}
	origin, err := exactOptionalStringArgument(arguments, "origin")
	if err != nil {
		return factPageErrorResult(&sc, "invalid_arguments", err.Error()), nil
	}
	if origin != "" && origin != string(memory.OriginUser) &&
		origin != string(memory.OriginDerived) && origin != string(memory.OriginExternal) {
		return factPageErrorResult(&sc, "invalid_arguments", "origin must be user, derived, or external"), nil
	}

	stored, created, err := s.facts.StoreProjectFactExact(explicitCtx, tools.StoreProjectFactExactParams{
		Content: content,
		Level:   level,
		Domain:  domain,
		Module:  module,
		Origin:  origin,
	})
	if err != nil {
		switch {
		case errors.Is(err, memory.ErrExactFactConflict):
			return factPageErrorResult(&sc, "exact_fact_conflict", "a live fact with this legacy identity has different exact fields"), nil
		case errors.Is(err, memory.ErrExactFactProjectArchived):
			return factPageErrorResult(&sc, "project_not_writable", "the project is archived"), nil
		case errors.Is(err, memory.ErrExactFactIntegrity):
			return factPageErrorResult(&sc, "exact_fact_integrity", "the durable fact row failed exact validation"), nil
		default:
			return factPageErrorResult(&sc, "exact_fact_unavailable", "the exact project fact store is unavailable"), nil
		}
	}
	return structuredFactPageResult(projectExactFactStoreEnvelope{
		MemoryScope: factPageScope(sc),
		Fact:        stored,
		Created:     created,
	}, false), nil
}

func (s *Server) handleUseProject(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	if s.projectSvc == nil {
		return errorResult(fmt.Errorf("project service not configured")), nil
	}
	sc, err := s.scopeForRequest(req)
	if err != nil {
		return errorResult(err), nil
	}
	if req.GetString("project_id", "") == "" {
		return errorResult(fmt.Errorf("project_id is required")), nil
	}
	project, err := s.projectSvc.Create(rlmscope.WithScope(ctx, sc), tools.CreateProjectParams{
		ProjectID: sc.ProjectID,
		Name:      req.GetString("name", ""),
	})
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(tools.ToJSON(map[string]any{
		"scope":   sc,
		"project": project,
	})), nil
}

func (s *Server) handleCurrentProject(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	if s.projectSvc == nil {
		return errorResult(fmt.Errorf("project service not configured")), nil
	}
	stats, err := s.projectSvc.Current(s.scopedContext(ctx))
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(tools.ToJSON(stats)), nil
}

func (s *Server) handleInspectCurrentProject(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	explicitCtx, sc, err := s.explicitMetaScopeContext(ctx, req)
	if err != nil {
		return errorResult(err), nil
	}
	if _, err := rlmscope.RequireExactProject(explicitCtx); err != nil {
		return errorResult(err), nil
	}
	if s.projectSvc == nil {
		return errorResult(fmt.Errorf("project service not configured")), nil
	}
	stats, err := s.projectSvc.Stats(explicitCtx, sc.ProjectID)
	if err != nil {
		return errorResult(err), nil
	}
	if stats == nil || stats.Project == nil {
		return errorResult(fmt.Errorf("project inspection returned no project")), nil
	}
	if stats.Project.TenantID != sc.TenantID || stats.Project.ProjectID != sc.ProjectID {
		return errorResult(fmt.Errorf("project inspection scope mismatch")), nil
	}
	return textResult(tools.ToJSON(map[string]any{
		"project": map[string]string{
			"tenant_id":  sc.TenantID,
			"project_id": sc.ProjectID,
		},
	})), nil
}

func (s *Server) handleProjectFactStats(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	explicitCtx, sc, err := s.explicitMetaScopeContext(ctx, req)
	if err != nil {
		return errorResult(err), nil
	}
	if _, err := rlmscope.RequireExactProject(explicitCtx); err != nil {
		return errorResult(err), nil
	}
	stats, err := s.facts.GetStats(explicitCtx)
	if err != nil {
		return errorResult(err), nil
	}
	if err := validateProjectFactStats(stats); err != nil {
		return errorResult(err), nil
	}
	return textResult(tools.ToJSON(map[string]any{
		"memory_scope": map[string]any{
			"version":    1,
			"kind":       "project",
			"tenant_id":  sc.TenantID,
			"project_id": sc.ProjectID,
		},
		"stats": stats,
	})), nil
}

func validateProjectFactStats(stats *memory.FactStoreStats) error {
	if stats == nil {
		return fmt.Errorf("project fact stats are missing")
	}
	if stats.ByLevel == nil || stats.ByDomain == nil || stats.ByOrigin == nil {
		return fmt.Errorf("project fact stats maps are missing")
	}
	counts := map[string]int{
		"total_facts":     stats.TotalFacts,
		"live_facts":      stats.LiveFacts,
		"archived_count":  stats.ArchivedCount,
		"stale_count":     stats.StaleCount,
		"with_embeddings": stats.WithEmbeddings,
		"gene_count":      stats.GeneCount,
		"cold_count":      stats.ColdCount,
	}
	for name, count := range counts {
		if count < 0 {
			return fmt.Errorf("project fact stats %s must be nonnegative", name)
		}
	}
	for name, count := range map[string]int{
		"live_facts":      stats.LiveFacts,
		"archived_count":  stats.ArchivedCount,
		"stale_count":     stats.StaleCount,
		"with_embeddings": stats.WithEmbeddings,
		"gene_count":      stats.GeneCount,
		"cold_count":      stats.ColdCount,
	} {
		if count > stats.TotalFacts {
			return fmt.Errorf("project fact stats %s exceeds total_facts", name)
		}
	}

	levelTotal := 0
	for level, count := range stats.ByLevel {
		if !level.IsValid() {
			return fmt.Errorf("project fact stats by_level contains invalid level %d", level)
		}
		if count < 0 {
			return fmt.Errorf("project fact stats by_level[%d] must be nonnegative", level)
		}
		if count > stats.TotalFacts-levelTotal {
			return fmt.Errorf("project fact stats by_level total exceeds total_facts")
		}
		levelTotal += count
	}
	if levelTotal != stats.TotalFacts {
		return fmt.Errorf("project fact stats by_level total must equal total_facts")
	}
	for domain, count := range stats.ByDomain {
		if count < 0 {
			return fmt.Errorf("project fact stats by_domain[%q] must be nonnegative", domain)
		}
	}
	originTotal := 0
	for origin, count := range stats.ByOrigin {
		if !origin.IsValid() {
			return fmt.Errorf("project fact stats by_origin contains invalid origin %q", origin)
		}
		if count < 0 {
			return fmt.Errorf("project fact stats by_origin[%q] must be nonnegative", origin)
		}
		if count > stats.LiveFacts-originTotal {
			return fmt.Errorf("project fact stats by_origin total exceeds live_facts")
		}
		originTotal += count
	}
	if originTotal != stats.LiveFacts {
		return fmt.Errorf("project fact stats by_origin total must equal live_facts")
	}
	return nil
}

func (s *Server) handleListProjects(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	if s.projectSvc == nil {
		return errorResult(fmt.Errorf("project service not configured")), nil
	}
	projects, err := s.projectSvc.List(s.scopedContext(ctx), req.GetBool("include_archived", false))
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(tools.ToJSON(projects)), nil
}

func (s *Server) handleCreateProject(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	if s.projectSvc == nil {
		return errorResult(fmt.Errorf("project service not configured")), nil
	}
	project, err := s.projectSvc.Create(s.scopedContext(ctx), tools.CreateProjectParams{
		ProjectID: req.GetString("project_id", ""),
		Name:      req.GetString("name", ""),
	})
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(tools.ToJSON(project)), nil
}

func (s *Server) handleArchiveProject(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	if s.projectSvc == nil {
		return errorResult(fmt.Errorf("project service not configured")), nil
	}
	project, err := s.projectSvc.Archive(s.scopedContext(ctx), req.GetString("project_id", ""))
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(tools.ToJSON(project)), nil
}

func (s *Server) handleActivateProject(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	if s.projectSvc == nil {
		return errorResult(fmt.Errorf("project service not configured")), nil
	}
	project, err := s.projectSvc.Activate(s.scopedContext(ctx), req.GetString("project_id", ""))
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(tools.ToJSON(project)), nil
}

func (s *Server) handleProjectStats(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	if s.projectSvc == nil {
		return errorResult(fmt.Errorf("project service not configured")), nil
	}
	stats, err := s.projectSvc.Stats(s.scopedContext(ctx), req.GetString("project_id", ""))
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(tools.ToJSON(stats)), nil
}
