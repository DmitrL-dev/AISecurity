package mcpserver

import (
	"context"
	"encoding/json"
	"testing"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/sentinel-community/gomcp/internal/application/resources"
	"github.com/sentinel-community/gomcp/internal/application/tools"
	"github.com/sentinel-community/gomcp/internal/infrastructure/sqlite"
)

// newTestServer creates a fully-wired Server backed by in-memory SQLite databases.
func newTestServer(t *testing.T) *Server {
	t.Helper()

	factDB, err := sqlite.OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { factDB.Close() })

	stateDB, err := sqlite.OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { stateDB.Close() })

	causalDB, err := sqlite.OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { causalDB.Close() })

	crystalDB, err := sqlite.OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { crystalDB.Close() })

	factRepo, err := sqlite.NewFactRepo(factDB)
	require.NoError(t, err)

	stateRepo, err := sqlite.NewStateRepo(stateDB)
	require.NoError(t, err)

	causalRepo, err := sqlite.NewCausalRepo(causalDB)
	require.NoError(t, err)

	crystalRepo, err := sqlite.NewCrystalRepo(crystalDB)
	require.NoError(t, err)

	factSvc := tools.NewFactService(factRepo, nil)
	sessionSvc := tools.NewSessionService(stateRepo)
	causalSvc := tools.NewCausalService(causalRepo)
	crystalSvc := tools.NewCrystalService(crystalRepo)
	systemSvc := tools.NewSystemService(factRepo)
	resProv := resources.NewProvider(factRepo, stateRepo)

	return New(
		Config{Name: "test-gomcp", Version: "2.0.0-test"},
		factSvc, sessionSvc, causalSvc, crystalSvc, systemSvc, resProv,
	)
}

// callToolReq creates a mcp.CallToolRequest with given name and arguments.
func callToolReq(name string, args map[string]interface{}) mcp.CallToolRequest {
	var req mcp.CallToolRequest
	req.Params.Name = name
	req.Params.Arguments = args
	return req
}

// extractText extracts text from a CallToolResult.
func extractText(t *testing.T, result *mcp.CallToolResult) string {
	t.Helper()
	require.NotNil(t, result)
	require.NotEmpty(t, result.Content)
	tc, ok := result.Content[0].(mcp.TextContent)
	require.True(t, ok, "expected TextContent, got %T", result.Content[0])
	return tc.Text
}

// --- New / Config ---

func TestNew_CreatesServer(t *testing.T) {
	srv := newTestServer(t)
	require.NotNil(t, srv)
	require.NotNil(t, srv.mcp)
	require.NotNil(t, srv.MCPServer())
}

func TestNew_WithPyBridgeOption(t *testing.T) {
	srv := newTestServer(t)
	// Without pybridge option, pybridge should be nil.
	assert.Nil(t, srv.pybridge)
}

// --- Fact Tools ---

func TestHandleAddFact(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	req := callToolReq("add_fact", map[string]interface{}{
		"content": "Go is concurrent",
		"level":   float64(0),
		"domain":  "core",
		"module":  "runtime",
	})

	result, err := srv.handleAddFact(ctx, req)
	require.NoError(t, err)
	require.False(t, result.IsError)

	text := extractText(t, result)
	assert.Contains(t, text, "Go is concurrent")
	assert.Contains(t, text, "core")
}

func TestHandleAddFact_InvalidLevel(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	req := callToolReq("add_fact", map[string]interface{}{
		"content": "bad level",
		"level":   float64(99),
	})

	result, err := srv.handleAddFact(ctx, req)
	require.NoError(t, err)
	assert.True(t, result.IsError)
}

func TestHandleGetFact(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	// Add a fact first.
	addReq := callToolReq("add_fact", map[string]interface{}{
		"content": "test fact",
		"level":   float64(0),
	})
	addResult, err := srv.handleAddFact(ctx, addReq)
	require.NoError(t, err)

	// Extract ID from result.
	var fact map[string]interface{}
	require.NoError(t, json.Unmarshal([]byte(extractText(t, addResult)), &fact))
	factID := fact["id"].(string)

	// Get fact.
	getReq := callToolReq("get_fact", map[string]interface{}{"id": factID})
	result, err := srv.handleGetFact(ctx, getReq)
	require.NoError(t, err)
	assert.False(t, result.IsError)
	assert.Contains(t, extractText(t, result), "test fact")
}

func TestHandleGetFact_NotFound(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	req := callToolReq("get_fact", map[string]interface{}{"id": "nonexistent"})
	result, err := srv.handleGetFact(ctx, req)
	require.NoError(t, err)
	assert.True(t, result.IsError)
}

func TestHandleUpdateFact(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	// Add a fact.
	addResult, err := srv.handleAddFact(ctx, callToolReq("add_fact", map[string]interface{}{
		"content": "original content",
		"level":   float64(1),
		"domain":  "test",
	}))
	require.NoError(t, err)

	var fact map[string]interface{}
	require.NoError(t, json.Unmarshal([]byte(extractText(t, addResult)), &fact))
	factID := fact["id"].(string)

	// Update fact.
	updateReq := callToolReq("update_fact", map[string]interface{}{
		"id":      factID,
		"content": "updated content",
	})
	result, err := srv.handleUpdateFact(ctx, updateReq)
	require.NoError(t, err)
	assert.False(t, result.IsError)
	assert.Contains(t, extractText(t, result), "updated content")
}

func TestHandleUpdateFact_MarkStale(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	addResult, err := srv.handleAddFact(ctx, callToolReq("add_fact", map[string]interface{}{
		"content": "will be stale",
		"level":   float64(0),
	}))
	require.NoError(t, err)

	var fact map[string]interface{}
	require.NoError(t, json.Unmarshal([]byte(extractText(t, addResult)), &fact))

	result, err := srv.handleUpdateFact(ctx, callToolReq("update_fact", map[string]interface{}{
		"id":       fact["id"].(string),
		"is_stale": true,
	}))
	require.NoError(t, err)
	assert.False(t, result.IsError)
	assert.Contains(t, extractText(t, result), "true")
}

func TestHandleDeleteFact(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	addResult, err := srv.handleAddFact(ctx, callToolReq("add_fact", map[string]interface{}{
		"content": "to delete",
		"level":   float64(0),
	}))
	require.NoError(t, err)

	var fact map[string]interface{}
	require.NoError(t, json.Unmarshal([]byte(extractText(t, addResult)), &fact))

	result, err := srv.handleDeleteFact(ctx, callToolReq("delete_fact", map[string]interface{}{
		"id": fact["id"].(string),
	}))
	require.NoError(t, err)
	assert.False(t, result.IsError)
	assert.Contains(t, extractText(t, result), "deleted")
}

func TestHandleListFacts(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	// Add facts in different domains.
	_, _ = srv.handleAddFact(ctx, callToolReq("add_fact", map[string]interface{}{
		"content": "fact in backend",
		"level":   float64(0),
		"domain":  "backend",
	}))
	_, _ = srv.handleAddFact(ctx, callToolReq("add_fact", map[string]interface{}{
		"content": "fact in frontend",
		"level":   float64(1),
		"domain":  "frontend",
	}))

	// List by domain.
	result, err := srv.handleListFacts(ctx, callToolReq("list_facts", map[string]interface{}{
		"domain": "backend",
	}))
	require.NoError(t, err)
	assert.False(t, result.IsError)
	assert.Contains(t, extractText(t, result), "fact in backend")
	assert.NotContains(t, extractText(t, result), "fact in frontend")
}

func TestHandleListFacts_ByLevel(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	_, _ = srv.handleAddFact(ctx, callToolReq("add_fact", map[string]interface{}{
		"content": "L0 fact", "level": float64(0),
	}))
	_, _ = srv.handleAddFact(ctx, callToolReq("add_fact", map[string]interface{}{
		"content": "L1 fact", "level": float64(1),
	}))

	result, err := srv.handleListFacts(ctx, callToolReq("list_facts", map[string]interface{}{
		"level": float64(1),
	}))
	require.NoError(t, err)
	text := extractText(t, result)
	assert.Contains(t, text, "L1 fact")
	assert.NotContains(t, text, "L0 fact")
}

func TestHandleSearchFacts(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	_, _ = srv.handleAddFact(ctx, callToolReq("add_fact", map[string]interface{}{
		"content": "Go goroutines are lightweight", "level": float64(0),
	}))
	_, _ = srv.handleAddFact(ctx, callToolReq("add_fact", map[string]interface{}{
		"content": "Python has GIL", "level": float64(0),
	}))

	result, err := srv.handleSearchFacts(ctx, callToolReq("search_facts", map[string]interface{}{
		"query": "goroutines", "limit": float64(10),
	}))
	require.NoError(t, err)
	text := extractText(t, result)
	assert.Contains(t, text, "goroutines")
	assert.NotContains(t, text, "GIL")
}

func TestHandleListDomains(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	_, _ = srv.handleAddFact(ctx, callToolReq("add_fact", map[string]interface{}{
		"content": "f1", "level": float64(0), "domain": "infra",
	}))
	_, _ = srv.handleAddFact(ctx, callToolReq("add_fact", map[string]interface{}{
		"content": "f2", "level": float64(0), "domain": "security",
	}))

	result, err := srv.handleListDomains(ctx, callToolReq("list_domains", nil))
	require.NoError(t, err)
	text := extractText(t, result)
	assert.Contains(t, text, "infra")
	assert.Contains(t, text, "security")
}

func TestHandleGetStaleFacts(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	// Add a fact and mark it stale.
	addResult, _ := srv.handleAddFact(ctx, callToolReq("add_fact", map[string]interface{}{
		"content": "stale fact", "level": float64(0),
	}))
	var fact map[string]interface{}
	_ = json.Unmarshal([]byte(extractText(t, addResult)), &fact)

	_, _ = srv.handleUpdateFact(ctx, callToolReq("update_fact", map[string]interface{}{
		"id": fact["id"].(string), "is_stale": true,
	}))

	result, err := srv.handleGetStaleFacts(ctx, callToolReq("get_stale_facts", map[string]interface{}{}))
	require.NoError(t, err)
	assert.Contains(t, extractText(t, result), "stale fact")
}

func TestHandleGetL0Facts(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	_, _ = srv.handleAddFact(ctx, callToolReq("add_fact", map[string]interface{}{
		"content": "project level", "level": float64(0),
	}))
	_, _ = srv.handleAddFact(ctx, callToolReq("add_fact", map[string]interface{}{
		"content": "domain level", "level": float64(1),
	}))

	result, err := srv.handleGetL0Facts(ctx, callToolReq("get_l0_facts", nil))
	require.NoError(t, err)
	text := extractText(t, result)
	assert.Contains(t, text, "project level")
	assert.NotContains(t, text, "domain level")
}

func TestHandleFactStats(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	_, _ = srv.handleAddFact(ctx, callToolReq("add_fact", map[string]interface{}{
		"content": "f1", "level": float64(0), "domain": "d1",
	}))
	_, _ = srv.handleAddFact(ctx, callToolReq("add_fact", map[string]interface{}{
		"content": "f2", "level": float64(1), "domain": "d2",
	}))

	result, err := srv.handleFactStats(ctx, callToolReq("fact_stats", nil))
	require.NoError(t, err)
	text := extractText(t, result)
	assert.Contains(t, text, "total_facts")
}

func TestHandleProcessExpired(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	result, err := srv.handleProcessExpired(ctx, callToolReq("process_expired", nil))
	require.NoError(t, err)
	assert.Contains(t, extractText(t, result), "Processed")
}

// --- Session Tools ---

func TestHandleSaveState_LoadState(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	// Save state.
	stateJSON := `{"goals": [{"description": "test"}]}`
	saveResult, err := srv.handleSaveState(ctx, callToolReq("save_state", map[string]interface{}{
		"session_id": "test-session",
		"state_json": stateJSON,
	}))
	require.NoError(t, err)
	assert.False(t, saveResult.IsError)
	assert.Contains(t, extractText(t, saveResult), "State saved")

	// Load state.
	loadResult, err := srv.handleLoadState(ctx, callToolReq("load_state", map[string]interface{}{
		"session_id": "test-session",
	}))
	require.NoError(t, err)
	assert.False(t, loadResult.IsError)
	assert.Contains(t, extractText(t, loadResult), "checksum")
}

func TestHandleSaveState_InvalidJSON(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	result, err := srv.handleSaveState(ctx, callToolReq("save_state", map[string]interface{}{
		"session_id": "bad-json",
		"state_json": "not json",
	}))
	require.NoError(t, err)
	assert.True(t, result.IsError)
	assert.Contains(t, extractText(t, result), "invalid state JSON")
}

func TestHandleListSessions(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	// Create sessions.
	_, _ = srv.handleSaveState(ctx, callToolReq("save_state", map[string]interface{}{
		"session_id": "s1", "state_json": "{}",
	}))
	_, _ = srv.handleSaveState(ctx, callToolReq("save_state", map[string]interface{}{
		"session_id": "s2", "state_json": "{}",
	}))

	result, err := srv.handleListSessions(ctx, callToolReq("list_sessions", nil))
	require.NoError(t, err)
	assert.False(t, result.IsError)
}

func TestHandleDeleteSession(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	_, _ = srv.handleSaveState(ctx, callToolReq("save_state", map[string]interface{}{
		"session_id": "to-delete", "state_json": "{}",
	}))

	result, err := srv.handleDeleteSession(ctx, callToolReq("delete_session", map[string]interface{}{
		"session_id": "to-delete",
	}))
	require.NoError(t, err)
	assert.Contains(t, extractText(t, result), "Deleted")
}

func TestHandleRestoreOrCreate_New(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	result, err := srv.handleRestoreOrCreate(ctx, callToolReq("restore_or_create", map[string]interface{}{
		"session_id": "brand-new",
	}))
	require.NoError(t, err)
	assert.False(t, result.IsError)
	assert.Contains(t, extractText(t, result), "created")
}

func TestHandleRestoreOrCreate_Existing(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	// Create first.
	_, _ = srv.handleRestoreOrCreate(ctx, callToolReq("restore_or_create", map[string]interface{}{
		"session_id": "existing",
	}))

	// Restore.
	result, err := srv.handleRestoreOrCreate(ctx, callToolReq("restore_or_create", map[string]interface{}{
		"session_id": "existing",
	}))
	require.NoError(t, err)
	assert.Contains(t, extractText(t, result), "restored")
}

func TestHandleGetCompactState(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	// Create session first.
	_, _ = srv.handleRestoreOrCreate(ctx, callToolReq("restore_or_create", map[string]interface{}{
		"session_id": "compact-test",
	}))

	result, err := srv.handleGetCompactState(ctx, callToolReq("get_compact_state", map[string]interface{}{
		"session_id": "compact-test", "max_tokens": float64(500),
	}))
	require.NoError(t, err)
	assert.False(t, result.IsError)
}

func TestHandleGetAuditLog(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	_, _ = srv.handleSaveState(ctx, callToolReq("save_state", map[string]interface{}{
		"session_id": "audited", "state_json": "{}",
	}))

	result, err := srv.handleGetAuditLog(ctx, callToolReq("get_audit_log", map[string]interface{}{
		"session_id": "audited", "limit": float64(10),
	}))
	require.NoError(t, err)
	assert.False(t, result.IsError)
}

// --- Causal Tools ---

func TestHandleAddCausalNode(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	result, err := srv.handleAddCausalNode(ctx, callToolReq("add_causal_node", map[string]interface{}{
		"node_type": "decision",
		"content":   "Use Go for performance",
	}))
	require.NoError(t, err)
	assert.False(t, result.IsError)
	text := extractText(t, result)
	assert.Contains(t, text, "decision")
	assert.Contains(t, text, "Use Go for performance")
}

func TestHandleAddCausalNode_InvalidType(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	result, err := srv.handleAddCausalNode(ctx, callToolReq("add_causal_node", map[string]interface{}{
		"node_type": "invalid_type",
		"content":   "bad",
	}))
	require.NoError(t, err)
	assert.True(t, result.IsError)
}

func TestHandleAddCausalEdge(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	// Add two nodes.
	r1, _ := srv.handleAddCausalNode(ctx, callToolReq("add_causal_node", map[string]interface{}{
		"node_type": "decision", "content": "Choose Go",
	}))
	r2, _ := srv.handleAddCausalNode(ctx, callToolReq("add_causal_node", map[string]interface{}{
		"node_type": "reason", "content": "Performance matters",
	}))

	var n1, n2 map[string]interface{}
	_ = json.Unmarshal([]byte(extractText(t, r1)), &n1)
	_ = json.Unmarshal([]byte(extractText(t, r2)), &n2)

	result, err := srv.handleAddCausalEdge(ctx, callToolReq("add_causal_edge", map[string]interface{}{
		"from_id":   n2["id"].(string),
		"to_id":     n1["id"].(string),
		"edge_type": "justifies",
	}))
	require.NoError(t, err)
	assert.False(t, result.IsError)
	assert.Contains(t, extractText(t, result), "justifies")
}

func TestHandleAddCausalEdge_InvalidType(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	result, err := srv.handleAddCausalEdge(ctx, callToolReq("add_causal_edge", map[string]interface{}{
		"from_id": "a", "to_id": "b", "edge_type": "bad_type",
	}))
	require.NoError(t, err)
	assert.True(t, result.IsError)
}

func TestHandleGetCausalChain(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	// Add a decision node.
	_, _ = srv.handleAddCausalNode(ctx, callToolReq("add_causal_node", map[string]interface{}{
		"node_type": "decision", "content": "Use mcp-go library",
	}))

	result, err := srv.handleGetCausalChain(ctx, callToolReq("get_causal_chain", map[string]interface{}{
		"query": "mcp-go", "max_depth": float64(3),
	}))
	require.NoError(t, err)
	assert.False(t, result.IsError)
}

func TestHandleCausalStats(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	_, _ = srv.handleAddCausalNode(ctx, callToolReq("add_causal_node", map[string]interface{}{
		"node_type": "decision", "content": "test decision",
	}))

	result, err := srv.handleCausalStats(ctx, callToolReq("causal_stats", nil))
	require.NoError(t, err)
	assert.False(t, result.IsError)
	assert.Contains(t, extractText(t, result), "total_nodes")
}

// --- Crystal Tools ---

func TestHandleSearchCrystals(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	// Empty search — should return empty list, not error.
	result, err := srv.handleSearchCrystals(ctx, callToolReq("search_crystals", map[string]interface{}{
		"query": "nonexistent", "limit": float64(5),
	}))
	require.NoError(t, err)
	assert.False(t, result.IsError)
}

func TestHandleGetCrystal_NotFound(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	result, err := srv.handleGetCrystal(ctx, callToolReq("get_crystal", map[string]interface{}{
		"path": "nonexistent/file.go",
	}))
	require.NoError(t, err)
	assert.True(t, result.IsError)
}

func TestHandleListCrystals(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	result, err := srv.handleListCrystals(ctx, callToolReq("list_crystals", map[string]interface{}{
		"pattern": "", "limit": float64(10),
	}))
	require.NoError(t, err)
	assert.False(t, result.IsError)
}

func TestHandleCrystalStats(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	result, err := srv.handleCrystalStats(ctx, callToolReq("crystal_stats", nil))
	require.NoError(t, err)
	assert.False(t, result.IsError)
	assert.Contains(t, extractText(t, result), "total_crystals")
}

// --- System Tools ---

func TestHandleHealth(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	result, err := srv.handleHealth(ctx, callToolReq("health", nil))
	require.NoError(t, err)
	assert.False(t, result.IsError)
	text := extractText(t, result)
	assert.Contains(t, text, "healthy")
	assert.Contains(t, text, "go_version")
}

func TestHandleVersion(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	result, err := srv.handleVersion(ctx, callToolReq("version", nil))
	require.NoError(t, err)
	text := extractText(t, result)
	assert.Contains(t, text, "version")
	assert.Contains(t, text, "go_version")
}

func TestHandleDashboard(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	_, _ = srv.handleAddFact(ctx, callToolReq("add_fact", map[string]interface{}{
		"content": "dashboard fact", "level": float64(0),
	}))

	result, err := srv.handleDashboard(ctx, callToolReq("dashboard", nil))
	require.NoError(t, err)
	text := extractText(t, result)
	assert.Contains(t, text, "health")
	assert.Contains(t, text, "fact_stats")
}

// --- Resources ---

func TestRegisterResources_NilProvider(t *testing.T) {
	factDB, err := sqlite.OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { factDB.Close() })

	stateDB, err := sqlite.OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { stateDB.Close() })

	causalDB, err := sqlite.OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { causalDB.Close() })

	crystalDB, err := sqlite.OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { crystalDB.Close() })

	factRepo, _ := sqlite.NewFactRepo(factDB)
	stateRepo, _ := sqlite.NewStateRepo(stateDB)
	causalRepo, _ := sqlite.NewCausalRepo(causalDB)
	crystalRepo, _ := sqlite.NewCrystalRepo(crystalDB)

	factSvc := tools.NewFactService(factRepo, nil)
	sessionSvc := tools.NewSessionService(stateRepo)
	causalSvc := tools.NewCausalService(causalRepo)
	crystalSvc := tools.NewCrystalService(crystalRepo)
	systemSvc := tools.NewSystemService(factRepo)

	// nil resource provider — should not panic.
	srv := New(
		Config{Name: "test", Version: "1.0"},
		factSvc, sessionSvc, causalSvc, crystalSvc, systemSvc, nil,
	)
	require.NotNil(t, srv)
}

// --- Helpers ---

func TestExtractSessionID(t *testing.T) {
	tests := []struct {
		uri      string
		expected string
	}{
		{"rlm://state/my-session", "my-session"},
		{"rlm://state/default", "default"},
		{"rlm://state/", "default"},
		{"rlm://state", "default"},
		{"bad-uri", "default"},
	}
	for _, tt := range tests {
		t.Run(tt.uri, func(t *testing.T) {
			assert.Equal(t, tt.expected, extractSessionID(tt.uri))
		})
	}
}

func TestTextResult(t *testing.T) {
	r := textResult("hello world")
	require.NotNil(t, r)
	require.Len(t, r.Content, 1)
	tc, ok := r.Content[0].(mcp.TextContent)
	require.True(t, ok)
	assert.Equal(t, "hello world", tc.Text)
	assert.Equal(t, "text", tc.Type)
	assert.False(t, r.IsError)
}

func TestErrorResult(t *testing.T) {
	r := errorResult(assert.AnError)
	require.NotNil(t, r)
	require.Len(t, r.Content, 1)
	tc, ok := r.Content[0].(mcp.TextContent)
	require.True(t, ok)
	assert.Contains(t, tc.Text, "Error:")
	assert.True(t, r.IsError)
}

// --- Python Bridge Tools (without bridge) ---

func TestRegisterPythonBridgeTools_NoBridge(t *testing.T) {
	srv := newTestServer(t)
	// Without pybridge, no python tools registered — server should still work fine.
	require.NotNil(t, srv.MCPServer())
	assert.Nil(t, srv.pybridge)
}

func TestHandleLoadState_WithVersion(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	// Create session.
	_, _ = srv.handleSaveState(ctx, callToolReq("save_state", map[string]interface{}{
		"session_id": "versioned", "state_json": "{}",
	}))

	// Load with specific version.
	result, err := srv.handleLoadState(ctx, callToolReq("load_state", map[string]interface{}{
		"session_id": "versioned",
		"version":    float64(1),
	}))
	require.NoError(t, err)
	assert.False(t, result.IsError)
}
