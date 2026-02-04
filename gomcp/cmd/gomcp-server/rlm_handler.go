// Package main provides the GoMCP server entry point.
// This file implements RLMToolHandler that bridges stdio adapter to Python worker.
package main

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/sentinel-community/gomcp/pkg/pythonbridge"
	"github.com/sentinel-community/gomcp/pkg/stdio"
)

// RLMToolHandler implements stdio.ToolHandler by delegating to Python bridge
type RLMToolHandler struct {
	bridge *pythonbridge.Bridge
}

// NewRLMToolHandler creates a handler with Python bridge
func NewRLMToolHandler(bridge *pythonbridge.Bridge) *RLMToolHandler {
	return &RLMToolHandler{bridge: bridge}
}

// ListTools returns all available RLM tools
func (h *RLMToolHandler) ListTools() []stdio.ToolDefinition {
	return []stdio.ToolDefinition{
		{Name: "rlm_status", Description: "Get RLM server status and index info"},
		{Name: "rlm_health_check", Description: "Health check for Memory Bridge"},
		{Name: "rlm_discover_project", Description: "Smart cold start discovery for new projects"},
		{Name: "rlm_discover_deep", Description: "Deep discovery using multiple extractors"},
		{Name: "rlm_enterprise_context", Description: "One-call enterprise context with auto-discovery"},
		{Name: "rlm_route_context", Description: "Semantic routing to get only relevant facts"},
		{Name: "rlm_search_facts", Description: "Hybrid search across facts"},
		{Name: "rlm_get_hierarchy_stats", Description: "Get statistics about the hierarchical memory store"},
		{Name: "rlm_get_facts_by_domain", Description: "Get all facts for a specific domain"},
		{Name: "rlm_list_domains", Description: "List all discovered domains"},
		{Name: "rlm_add_hierarchical_fact", Description: "Add fact with hierarchical levels (L0-L3)"},
		{Name: "rlm_approve_fact", Description: "Approve and store an extracted fact"},
		{Name: "rlm_delete_fact", Description: "Delete a fact from the store"},
		{Name: "rlm_extract_facts", Description: "Auto-extract facts from git diff or file changes"},
		{Name: "rlm_get_pending_candidates", Description: "Get pending fact candidates awaiting approval"},
		{Name: "rlm_approve_all_candidates", Description: "Approve all pending fact candidates"},
		{Name: "rlm_index_embeddings", Description: "Generate embeddings for all facts without embeddings"},
		{Name: "rlm_consolidate_facts", Description: "Consolidate granular facts into higher-level summaries"},
		{Name: "rlm_record_causal_decision", Description: "Record a decision with full causal context"},
		{Name: "rlm_get_causal_chain", Description: "Query reasoning history for a decision"},
		{Name: "rlm_start_session", Description: "Start a new session or restore existing one"},
		{Name: "rlm_sync_state", Description: "Save current cognitive state to persistent storage"},
		{Name: "rlm_restore_state", Description: "Restore cognitive state for a session"},
		{Name: "rlm_list_sessions", Description: "List all saved sessions"},
		{Name: "rlm_auto_inject", Description: "Get optimized context for automatic injection"},
		{Name: "rlm_reindex", Description: "Reindex project or specific path"},
		{Name: "rlm_validate", Description: "Validate index freshness and cross-references"},
		{Name: "rlm_query", Description: "Search in loaded context"},
		{Name: "rlm_memory", Description: "Manage H-MEM hierarchical memory"},
		{Name: "rlm_analyze", Description: "Deep analysis through C³ crystals"},
		{Name: "rlm_load_context", Description: "Load a file or directory into context"},
		{Name: "rlm_list_contexts", Description: "List all loaded contexts"},
		{Name: "rlm_session_stats", Description: "Get real-time session statistics"},
		{Name: "rlm_settings", Description: "Get or set RLM settings"},
	}
}

// CallTool executes a tool via Python bridge
func (h *RLMToolHandler) CallTool(ctx context.Context, name string, args json.RawMessage) (json.RawMessage, error) {
	if h.bridge == nil {
		return nil, fmt.Errorf("python bridge not initialized")
	}

	if !h.bridge.IsRunning() {
		if err := h.bridge.Start(ctx); err != nil {
			return nil, fmt.Errorf("failed to start python bridge: %w", err)
		}
	}

	// Parse arguments
	var params map[string]any
	if len(args) > 0 && string(args) != "null" {
		if err := json.Unmarshal(args, &params); err != nil {
			return nil, fmt.Errorf("invalid arguments: %w", err)
		}
	}
	if params == nil {
		params = make(map[string]any)
	}

	// Call Python bridge
	resp, err := h.bridge.Call(ctx, name, params)
	if err != nil {
		return nil, err
	}

	if !resp.Success {
		return nil, fmt.Errorf("%s", resp.Error)
	}

	// Return result as JSON
	result, err := json.Marshal(resp.Result)
	if err != nil {
		return nil, fmt.Errorf("marshal result: %w", err)
	}

	return result, nil
}
