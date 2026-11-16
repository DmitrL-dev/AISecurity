package mcpserver

import (
	"context"
	"testing"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/stretchr/testify/require"

	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
)

type defaultOnlyToolCase struct {
	name string
	call func() (*mcp.CallToolResult, error)
}

func defaultOnlyToolCases(srv *Server, ctx context.Context) []defaultOnlyToolCase {
	return []defaultOnlyToolCase{
		{
			name: "fact list",
			call: func() (*mcp.CallToolResult, error) {
				return srv.handleListDefaultFactsPage(ctx, callToolReq(
					"list_default_facts_page",
					map[string]interface{}{"level": 0, "max_fact_bytes": 1024},
				))
			},
		},
		{
			name: "fact stats",
			call: func() (*mcp.CallToolResult, error) {
				return srv.handleDefaultFactStatsPage(ctx, callToolReq(
					"default_fact_stats_page", map[string]interface{}{},
				))
			},
		},
		{
			name: "causal chain",
			call: func() (*mcp.CallToolResult, error) {
				return srv.handleGetDefaultCausalChainBounded(ctx, callToolReq(
					"get_default_causal_chain_bounded",
					map[string]interface{}{
						"query": "decision", "max_depth": 1, "max_nodes": 10,
						"max_result_bytes": boundedCausalMaxResultBytes,
					},
				))
			},
		},
	}
}

func requireDefaultOnlyToolScopeError(t *testing.T, name string, result *mcp.CallToolResult) {
	t.Helper()
	require.True(t, result.IsError)
	if name == "causal chain" {
		envelope := decodeStructuredResult[boundedCausalErrorEnvelope](t, result)
		require.Equal(t, "scope_override_forbidden", envelope.Error.Code)
		return
	}
	envelope := decodeStructuredResult[factPageErrorEnvelope](t, result)
	require.Equal(t, "scope_override_forbidden", envelope.Error.Code)
}

func TestLockedNonDefaultServerRejectsDefaultOnlyTools(t *testing.T) {
	pinned := rlmscope.New("tenant-a", "project-alpha")
	srv, _ := newProjectTestServer(t, pinned)
	srv.locked = true
	ctx := rlmscope.WithScope(context.Background(), pinned)

	for _, testCase := range defaultOnlyToolCases(srv, ctx) {
		t.Run(testCase.name, func(t *testing.T) {
			result, err := testCase.call()
			require.NoError(t, err)
			requireDefaultOnlyToolScopeError(t, testCase.name, result)
		})
	}
}

func TestUnlockedNonDefaultServerAllowsDefaultOnlyTools(t *testing.T) {
	pinned := rlmscope.New("tenant-a", "project-alpha")
	srv, _ := newProjectTestServer(t, pinned)
	ctx := rlmscope.WithScope(context.Background(), pinned)

	for _, testCase := range defaultOnlyToolCases(srv, ctx) {
		t.Run(testCase.name, func(t *testing.T) {
			result, err := testCase.call()
			require.NoError(t, err)
			require.False(t, result.IsError, "result: %#v", result.StructuredContent)
		})
	}
}

func TestLockedDefaultServerAllowsDefaultOnlyTools(t *testing.T) {
	pinned := rlmscope.Default()
	srv, _ := newProjectTestServer(t, pinned)
	srv.locked = true
	ctx := rlmscope.WithScope(context.Background(), pinned)

	for _, testCase := range defaultOnlyToolCases(srv, ctx) {
		t.Run(testCase.name, func(t *testing.T) {
			result, err := testCase.call()
			require.NoError(t, err)
			require.False(t, result.IsError, "result: %#v", result.StructuredContent)
		})
	}
}
