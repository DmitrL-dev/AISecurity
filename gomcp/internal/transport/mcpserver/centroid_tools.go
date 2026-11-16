package mcpserver

import (
	"context"
	"fmt"

	"github.com/mark3labs/mcp-go/mcp"

	"github.com/syntrex/gomcp/internal/application/tools"
)

// registerCentroidTools registers Crystal A3 domain centroid MCP tools.
// All handlers are no-ops when CentroidService is not wired — the tools
// still register so introspection sees them, but they return a clear
// "centroid service not configured" message.
func (s *Server) registerCentroidTools() {
	s.mcp.AddTool(
		mcp.NewTool("recompute_centroids",
			mcp.WithDescription("Recompute domain centroids from live facts. With no domain, recomputes all."),
			mcp.WithString("domain", mcp.Description("Domain to recompute (omit for all)")),
		),
		s.handleRecomputeCentroids,
	)

	s.mcp.AddTool(
		mcp.NewTool("list_centroids",
			mcp.WithDescription("List all stored domain centroids with fact counts and update times."),
		),
		s.handleListCentroids,
	)

	s.mcp.AddTool(
		mcp.NewTool("search_domains",
			mcp.WithDescription("Two-stage retrieval: rank domains by cosine similarity to a query embedding."),
			mcp.WithString("query", mcp.Description("Free-text query (requires embedder)"), mcp.Required()),
			mcp.WithNumber("limit", mcp.Description("Max domains returned (default 10)")),
		),
		s.handleSearchDomains,
	)
}

func (s *Server) handleRecomputeCentroids(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	if s.centroidSvc == nil {
		return errorResult(fmt.Errorf("centroid service not configured")), nil
	}
	domain := req.GetString("domain", "")
	ctx = s.scopedContext(ctx)
	if domain != "" {
		c, err := s.centroidSvc.Recompute(ctx, domain)
		if err != nil {
			return errorResult(err), nil
		}
		if c == nil {
			return textResult(tools.ToJSON(map[string]string{
				"domain": domain,
				"status": "no_embeddings_available",
			})), nil
		}
		return textResult(tools.ToJSON(c)), nil
	}
	written, err := s.centroidSvc.RecomputeAll(ctx)
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(tools.ToJSON(map[string]int{"centroids_written": written})), nil
}

func (s *Server) handleListCentroids(ctx context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	if s.centroidSvc == nil {
		return errorResult(fmt.Errorf("centroid service not configured")), nil
	}
	all, err := s.centroidSvc.List(s.scopedContext(ctx))
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(tools.ToJSON(all)), nil
}

func (s *Server) handleSearchDomains(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	if s.centroidSvc == nil {
		return errorResult(fmt.Errorf("centroid service not configured")), nil
	}
	if s.embedder == nil {
		return errorResult(fmt.Errorf("embedder not configured")), nil
	}
	query := req.GetString("query", "")
	limit := req.GetInt("limit", 10)
	if query == "" {
		return errorResult(fmt.Errorf("query is required")), nil
	}
	ctx = s.scopedContext(ctx)
	vec, err := s.embedder.Embed(ctx, query)
	if err != nil {
		return errorResult(fmt.Errorf("embed query: %w", err)), nil
	}
	results, err := s.centroidSvc.SearchDomainsByVector(ctx, vec, limit)
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(tools.ToJSON(results)), nil
}
