package mcpserver

import (
	"context"
	"encoding/json"
	"testing"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/stretchr/testify/require"

	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
)

type sessionMemoryEnvelope struct {
	MemoryScope struct {
		Version   int    `json:"version"`
		Kind      string `json:"kind"`
		TenantID  string `json:"tenant_id"`
		ProjectID string `json:"project_id"`
		SessionID string `json:"session_id"`
	} `json:"memory_scope"`
	TurnID       string                     `json:"turn_id,omitempty"`
	Found        bool                       `json:"found,omitempty"`
	TurnReceipt  *memory.SessionTurnReceipt `json:"turn_receipt,omitempty"`
	Deduplicated bool                       `json:"deduplicated,omitempty"`
	Fact         *memory.Fact               `json:"fact,omitempty"`
	Facts        []*memory.Fact             `json:"facts,omitempty"`
}

const testTurnID = "turn_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
const testTurnIDB = "turn_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"

func sessionToolReq(name string, args map[string]interface{}, tenantID, projectID string) mcp.CallToolRequest {
	req := callToolReq(name, args)
	req.Params.Meta = &mcp.Meta{AdditionalFields: map[string]any{
		"rlm_scope": map[string]any{
			"tenant_id":  tenantID,
			"project_id": projectID,
		},
	}}
	return req
}

func decodeSessionEnvelope(t *testing.T, result *mcp.CallToolResult) sessionMemoryEnvelope {
	t.Helper()
	var envelope sessionMemoryEnvelope
	require.NoError(t, json.Unmarshal([]byte(extractText(t, result)), &envelope))
	return envelope
}

func requireExactSessionEnvelopeShape(t *testing.T, result *mcp.CallToolResult, payloadKey string) {
	t.Helper()
	var raw map[string]json.RawMessage
	require.NoError(t, json.Unmarshal([]byte(extractText(t, result)), &raw))
	expectedFields := 2
	if payloadKey == "fact" {
		expectedFields = 4
		require.Contains(t, raw, "turn_receipt")
		require.Contains(t, raw, "deduplicated")
	}
	require.Len(t, raw, expectedFields)
	require.Contains(t, raw, "memory_scope")
	require.Contains(t, raw, payloadKey)

	var marker map[string]json.RawMessage
	require.NoError(t, json.Unmarshal(raw["memory_scope"], &marker))
	require.Len(t, marker, 5)
	for _, key := range []string{"version", "kind", "tenant_id", "project_id", "session_id"} {
		require.Contains(t, marker, key)
	}
}

func TestSessionMemoryToolsIsolateSessionsAndProjects(t *testing.T) {
	srv, _ := newProjectTestServer(t, rlmscope.New("tenant-a", "project-alpha"))
	ctx := context.Background()

	stores := []struct {
		project, session, content string
	}{
		{"project-alpha", "session-one", "alpha first marker"},
		{"project-alpha", "session-two", "alpha second marker"},
		{"project-beta", "session-one", "beta first marker"},
	}
	for _, tc := range stores {
		result, err := srv.handleAddSessionFact(ctx, sessionToolReq("add_session_fact", map[string]interface{}{
			"session_id": tc.session,
			"turn_id":    testTurnID,
			"content":    tc.content,
			"level":      float64(0),
		}, "tenant-a", tc.project))
		require.NoError(t, err)
		require.False(t, result.IsError, extractText(t, result))
		requireExactSessionEnvelopeShape(t, result, "fact")
		envelope := decodeSessionEnvelope(t, result)
		require.Equal(t, 1, envelope.MemoryScope.Version)
		require.Equal(t, "session", envelope.MemoryScope.Kind)
		require.Equal(t, tc.project, envelope.MemoryScope.ProjectID)
		require.Equal(t, tc.session, envelope.MemoryScope.SessionID)
		require.NotNil(t, envelope.Fact)
		require.Equal(t, tc.session, envelope.Fact.SessionID)
		require.NotNil(t, envelope.TurnReceipt)
		require.Equal(t, testTurnID, envelope.TurnReceipt.TurnID)
		require.Equal(t, envelope.Fact.ID, envelope.TurnReceipt.FactID)
	}

	for _, tc := range stores {
		result, err := srv.handleSearchSessionFacts(ctx, sessionToolReq("search_session_facts", map[string]interface{}{
			"session_id": tc.session,
			"query":      "marker",
			"mode":       "keyword",
		}, "tenant-a", tc.project))
		require.NoError(t, err)
		require.False(t, result.IsError, extractText(t, result))
		requireExactSessionEnvelopeShape(t, result, "facts")
		envelope := decodeSessionEnvelope(t, result)
		require.Equal(t, tc.project, envelope.MemoryScope.ProjectID)
		require.Equal(t, tc.session, envelope.MemoryScope.SessionID)
		require.Len(t, envelope.Facts, 1)
		require.Equal(t, tc.content, envelope.Facts[0].Content)
	}
}

func TestAddSessionFactWithoutTurnIDPreservesLegacyContractAndStoreSemantics(t *testing.T) {
	srv, _ := newProjectTestServer(t, rlmscope.New("tenant-a", "project-alpha"))
	ctx := context.Background()
	args := map[string]interface{}{
		"session_id": "session-legacy",
		"content":    "legacy transport append marker",
		"level":      float64(1),
		"domain":     "conversation",
		"module":     "chat",
		"origin":     "derived",
	}

	first, err := srv.handleAddSessionFact(ctx, sessionToolReq(
		"add_session_fact", args, "tenant-a", "project-alpha"))
	require.NoError(t, err)
	require.False(t, first.IsError, extractText(t, first))
	second, err := srv.handleAddSessionFact(ctx, sessionToolReq(
		"add_session_fact", args, "tenant-a", "project-alpha"))
	require.NoError(t, err)
	require.False(t, second.IsError, extractText(t, second))

	var firstRaw, secondRaw map[string]json.RawMessage
	require.NoError(t, json.Unmarshal([]byte(extractText(t, first)), &firstRaw))
	require.NoError(t, json.Unmarshal([]byte(extractText(t, second)), &secondRaw))
	for _, raw := range []map[string]json.RawMessage{firstRaw, secondRaw} {
		require.Len(t, raw, 2, "legacy response must not gain receipt fields")
		require.Contains(t, raw, "memory_scope")
		require.Contains(t, raw, "fact")
		require.NotContains(t, raw, "turn_receipt")
		require.NotContains(t, raw, "deduplicated")
	}
	firstEnvelope := decodeSessionEnvelope(t, first)
	secondEnvelope := decodeSessionEnvelope(t, second)
	require.NotNil(t, firstEnvelope.Fact)
	require.NotNil(t, secondEnvelope.Fact)
	require.Equal(t, firstEnvelope.Fact.ID, secondEnvelope.Fact.ID,
		"legacy duplicate folding must remain unchanged")

	differentArgs := make(map[string]interface{}, len(args))
	for key, value := range args {
		differentArgs[key] = value
	}
	differentArgs["content"] = "different legacy transport marker"
	different, err := srv.handleAddSessionFact(ctx, sessionToolReq(
		"add_session_fact", differentArgs, "tenant-a", "project-alpha"))
	require.NoError(t, err)
	require.False(t, different.IsError, extractText(t, different))
	require.NotEqual(t, firstEnvelope.Fact.ID, decodeSessionEnvelope(t, different).Fact.ID)

	search, err := srv.handleSearchSessionFacts(ctx, sessionToolReq(
		"search_session_facts",
		map[string]interface{}{
			"session_id": "session-legacy", "query": "legacy transport", "mode": "keyword",
		},
		"tenant-a", "project-alpha"))
	require.NoError(t, err)
	require.False(t, search.IsError, extractText(t, search))
	require.Len(t, decodeSessionEnvelope(t, search).Facts, 2,
		"legacy writes remain unkeyed and use ordinary content folding")
}

func TestSessionTurnToolsReconcileAndExposeExactReadOnlyReceipts(t *testing.T) {
	srv, _ := newProjectTestServer(t, rlmscope.New("tenant-a", "project-alpha"))
	ctx := context.Background()
	args := map[string]interface{}{
		"session_id": "session-one",
		"turn_id":    testTurnID,
		"content":    "one durable conversation turn",
		"level":      float64(1),
		"domain":     "conversation",
		"module":     "chat",
		"origin":     "derived",
	}
	first, err := srv.handleAddSessionFact(ctx, sessionToolReq(
		"add_session_fact", args, "tenant-a", "project-alpha"))
	require.NoError(t, err)
	require.False(t, first.IsError, extractText(t, first))
	firstEnvelope := decodeSessionEnvelope(t, first)
	require.False(t, firstEnvelope.Deduplicated)
	require.NotNil(t, firstEnvelope.TurnReceipt)

	retry, err := srv.handleAddSessionFact(ctx, sessionToolReq(
		"add_session_fact", args, "tenant-a", "project-alpha"))
	require.NoError(t, err)
	require.False(t, retry.IsError, extractText(t, retry))
	retryEnvelope := decodeSessionEnvelope(t, retry)
	require.True(t, retryEnvelope.Deduplicated)
	require.Equal(t, firstEnvelope.TurnReceipt, retryEnvelope.TurnReceipt)
	require.Equal(t, firstEnvelope.Fact.ID, retryEnvelope.Fact.ID)

	lookup, err := srv.handleGetSessionTurn(ctx, sessionToolReq(
		"get_session_turn",
		map[string]interface{}{"session_id": "session-one", "turn_id": testTurnID},
		"tenant-a", "project-alpha"))
	require.NoError(t, err)
	require.False(t, lookup.IsError, extractText(t, lookup))
	var raw map[string]json.RawMessage
	require.NoError(t, json.Unmarshal([]byte(extractText(t, lookup)), &raw))
	require.Len(t, raw, 5)
	for _, key := range []string{"memory_scope", "turn_id", "found", "turn_receipt", "fact"} {
		require.Contains(t, raw, key)
	}
	lookupEnvelope := decodeSessionEnvelope(t, lookup)
	require.True(t, lookupEnvelope.Found)
	require.Equal(t, testTurnID, lookupEnvelope.TurnID)
	require.Equal(t, firstEnvelope.Fact.ID, lookupEnvelope.Fact.ID)

	missing, err := srv.handleGetSessionTurn(ctx, sessionToolReq(
		"get_session_turn",
		map[string]interface{}{"session_id": "session-one", "turn_id": testTurnIDB},
		"tenant-a", "project-alpha"))
	require.NoError(t, err)
	require.False(t, missing.IsError, extractText(t, missing))
	require.NoError(t, json.Unmarshal([]byte(extractText(t, missing)), &raw))
	require.JSONEq(t, "null", string(raw["turn_receipt"]))
	require.JSONEq(t, "null", string(raw["fact"]))
	missingEnvelope := decodeSessionEnvelope(t, missing)
	require.False(t, missingEnvelope.Found)

	conflictArgs := make(map[string]interface{}, len(args))
	for key, value := range args {
		conflictArgs[key] = value
	}
	conflictArgs["content"] = "different payload under the same turn id"
	conflict, err := srv.handleAddSessionFact(ctx, sessionToolReq(
		"add_session_fact", conflictArgs, "tenant-a", "project-alpha"))
	require.NoError(t, err)
	require.True(t, conflict.IsError)
	require.Contains(t, extractText(t, conflict), memory.ErrSessionTurnConflict.Error())
}

func TestSessionMemoryToolsMetaScopeOverridesMaliciousArguments(t *testing.T) {
	srv, _ := newProjectTestServer(t, rlmscope.New("tenant-a", "project-alpha"))
	ctx := context.Background()
	addSessionFact := srv.scopeMiddleware()(srv.handleAddSessionFact)
	searchSessionFacts := srv.scopeMiddleware()(srv.handleSearchSessionFacts)
	add := sessionToolReq("add_session_fact", map[string]interface{}{
		"tenant_id":  "tenant-evil",
		"project_id": "project-evil",
		"session_id": "session-one",
		"turn_id":    testTurnID,
		"content":    "authoritative meta marker",
		"level":      float64(0),
	}, "tenant-a", "project-alpha")
	result, err := addSessionFact(ctx, add)
	require.NoError(t, err)
	require.False(t, result.IsError, extractText(t, result))
	envelope := decodeSessionEnvelope(t, result)
	require.Equal(t, "tenant-a", envelope.Fact.TenantID)
	require.Equal(t, "project-alpha", envelope.Fact.ProjectID)

	alpha, err := searchSessionFacts(ctx, sessionToolReq("search_session_facts", map[string]interface{}{
		"session_id": "session-one", "query": "authoritative", "mode": "keyword",
	}, "tenant-a", "project-alpha"))
	require.NoError(t, err)
	require.Len(t, decodeSessionEnvelope(t, alpha).Facts, 1)

	evil, err := searchSessionFacts(ctx, sessionToolReq("search_session_facts", map[string]interface{}{
		"session_id": "session-one", "query": "authoritative", "mode": "keyword",
	}, "tenant-evil", "project-evil"))
	require.NoError(t, err)
	require.Empty(t, decodeSessionEnvelope(t, evil).Facts)
}

func TestSessionMemoryToolsFailClosedWithoutCompleteMetaOrSession(t *testing.T) {
	srv, _ := newProjectTestServer(t, rlmscope.New("tenant-a", "project-alpha"))
	ctx := context.Background()

	missingMeta, err := srv.handleAddSessionFact(ctx, callToolReq("add_session_fact", map[string]interface{}{
		"tenant_id": "tenant-a", "project_id": "project-alpha",
		"session_id": "session-one", "turn_id": testTurnID,
		"content": "must not persist", "level": float64(0),
	}))
	require.NoError(t, err)
	require.True(t, missingMeta.IsError)
	require.Contains(t, extractText(t, missingMeta), "_meta.rlm_scope")

	partial := callToolReq("search_session_facts", map[string]interface{}{
		"session_id": "session-one", "query": "persist",
	})
	partial.Params.Meta = &mcp.Meta{AdditionalFields: map[string]any{
		"rlm_scope": map[string]any{"tenant_id": "tenant-a"},
	}}
	partialResult, err := srv.handleSearchSessionFacts(ctx, partial)
	require.NoError(t, err)
	require.True(t, partialResult.IsError)
	require.Contains(t, extractText(t, partialResult), "project_id")

	invalidSession, err := srv.handleAddSessionFact(ctx, sessionToolReq("add_session_fact", map[string]interface{}{
		"session_id": "bad/session", "turn_id": testTurnID,
		"content": "must not persist", "level": float64(0),
	}, "tenant-a", "project-alpha"))
	require.NoError(t, err)
	require.True(t, invalidSession.IsError)
	require.Contains(t, extractText(t, invalidSession), "unsupported character")

	missingSession, err := srv.handleSearchSessionFacts(ctx, sessionToolReq("search_session_facts", map[string]interface{}{
		"query": "must not recall",
	}, "tenant-a", "project-alpha"))
	require.NoError(t, err)
	require.True(t, missingSession.IsError)
	require.Contains(t, extractText(t, missingSession), "session_id is required")

	for _, projectID := range []string{"default", "DEFAULT"} {
		reservedAdd, err := srv.handleAddSessionFact(ctx, sessionToolReq("add_session_fact", map[string]interface{}{
			"session_id": "session-one", "turn_id": testTurnID,
			"content": "must not persist", "level": float64(0),
		}, "local", projectID))
		require.NoError(t, err)
		require.True(t, reservedAdd.IsError)
		require.Contains(t, extractText(t, reservedAdd), "reserved for legacy memory")

		reservedSearch, err := srv.handleSearchSessionFacts(ctx, sessionToolReq("search_session_facts", map[string]interface{}{
			"session_id": "session-one", "query": "persist",
		}, "local", projectID))
		require.NoError(t, err)
		require.True(t, reservedSearch.IsError)
		require.Contains(t, extractText(t, reservedSearch), "reserved for legacy memory")
	}
}

func TestSessionMemoryFactsAreQuarantinedFromLegacyFactTools(t *testing.T) {
	srv, _ := newProjectTestServer(t, rlmscope.New("tenant-a", "project-alpha"))
	ctx := context.Background()
	stored, err := srv.handleAddSessionFact(ctx, sessionToolReq("add_session_fact", map[string]interface{}{
		"session_id": "session-one",
		"turn_id":    testTurnID,
		"content":    "session-only quarantine marker",
		"level":      float64(0),
	}, "tenant-a", "project-alpha"))
	require.NoError(t, err)
	require.False(t, stored.IsError, extractText(t, stored))
	fact := decodeSessionEnvelope(t, stored).Fact
	require.NotNil(t, fact)

	legacySearch, err := srv.handleSearchFacts(ctx, callToolReq("search_facts", map[string]interface{}{
		"query": "quarantine", "mode": "keyword",
	}))
	require.NoError(t, err)
	require.NotContains(t, extractText(t, legacySearch), "session-only")

	legacyList, err := srv.handleListFacts(ctx, callToolReq("list_facts", map[string]interface{}{
		"level": float64(0),
	}))
	require.NoError(t, err)
	require.NotContains(t, extractText(t, legacyList), "session-only")

	legacyGet, err := srv.handleGetFact(ctx, callToolReq("get_fact", map[string]interface{}{
		"id": fact.ID,
	}))
	require.NoError(t, err)
	require.True(t, legacyGet.IsError)

	empty, err := srv.handleSearchSessionFacts(ctx, sessionToolReq("search_session_facts", map[string]interface{}{
		"session_id": "session-missing", "query": "quarantine", "mode": "keyword",
	}, "tenant-a", "project-alpha"))
	require.NoError(t, err)
	var raw map[string]json.RawMessage
	require.NoError(t, json.Unmarshal([]byte(extractText(t, empty)), &raw))
	require.JSONEq(t, `[]`, string(raw["facts"]))
}
