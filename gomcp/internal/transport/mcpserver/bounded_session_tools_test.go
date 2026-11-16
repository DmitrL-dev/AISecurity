package mcpserver

import (
	"context"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"strings"
	"testing"
	"time"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/stretchr/testify/require"

	applicationtools "github.com/syntrex/gomcp/internal/application/tools"
	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"
)

type collectedBoundedSessionSearch struct {
	order      []string
	serialized map[string][]byte
	pages      int
}

type boundedSessionNoPreflightStore struct {
	memory.FactStore
	memory.SessionFactStore
	keywordCalls int
	vectorCalls  int
}

func (s *boundedSessionNoPreflightStore) SearchForSession(
	context.Context,
	string,
	string,
	int,
) ([]*memory.Fact, error) {
	s.keywordCalls++
	return nil, fmt.Errorf("legacy session keyword search must not run")
}

func (s *boundedSessionNoPreflightStore) SearchByVectorForSession(
	context.Context,
	string,
	[]float64,
	int,
) ([]*memory.Fact, error) {
	s.vectorCalls++
	return nil, fmt.Errorf("legacy session vector search must not run")
}

type boundedSessionLegacySearchSpyStore struct {
	*sqlite.FactRepo
	keywordCalls int
	vectorCalls  int
}

func (s *boundedSessionLegacySearchSpyStore) SearchForSession(
	context.Context,
	string,
	string,
	int,
) ([]*memory.Fact, error) {
	s.keywordCalls++
	return nil, fmt.Errorf("bounded session search called legacy keyword search")
}

func (s *boundedSessionLegacySearchSpyStore) SearchByVectorForSession(
	context.Context,
	string,
	[]float64,
	int,
) ([]*memory.Fact, error) {
	s.vectorCalls++
	return nil, fmt.Errorf("bounded session search called legacy vector search")
}

type boundedSessionStoredLimitTestEnvelope struct {
	MemoryScope boundedSessionScope           `json:"memory_scope"`
	Error       boundedSearchStoredLimitError `json:"error"`
}

func boundedSessionTestRequestRef(char byte) string {
	return managedSessionRequestPrefix + strings.Repeat(string(char), sha256.Size*2)
}

func addManagedBoundedSessionFact(
	t *testing.T,
	repo *sqlite.FactRepo,
	ctx context.Context,
	sessionID, id, content string,
	createdAt time.Time,
) *memory.Fact {
	t.Helper()
	fact := memory.NewFact(content, memory.LevelDomain, "conversation", "chat")
	fact.ID = id
	fact.CodeRef = boundedSessionTestRequestRef('a')
	fact.Source = "session_memory"
	fact.Origin = memory.OriginDerived
	fact.CreatedAt = createdAt
	fact.ValidFrom = createdAt
	fact.UpdatedAt = createdAt
	require.NoError(t, repo.AddForSession(ctx, sessionID, fact))
	return fact
}

func newBoundedSessionRepoServer(
	t *testing.T,
	scope rlmscope.Scope,
) (*Server, *sqlite.FactRepo, *sqlite.DB) {
	t.Helper()
	db, err := sqlite.OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := sqlite.NewFactRepo(db)
	require.NoError(t, err)
	return &Server{
		facts: applicationtools.NewFactService(repo, nil),
		scope: scope,
	}, repo, db
}

func insertRawManagedSessionFacts(
	t *testing.T,
	db *sqlite.DB,
	tenantID, projectID, sessionID, idPrefix, content string,
	count int,
) {
	t.Helper()
	tx, err := db.SqlDB().Begin()
	require.NoError(t, err)
	defer func() { _ = tx.Rollback() }()
	stmt, err := tx.Prepare(`INSERT INTO hierarchical_facts
		(id, tenant_id, project_id, content, level, domain, module, code_ref,
		 created_at, valid_from, is_stale, is_archived, confidence, source, session_id, origin)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 1.0, ?, ?, ?)`)
	require.NoError(t, err)
	stamp := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC).Format(time.RFC3339Nano)
	for index := 0; index < count; index++ {
		id := idPrefix
		if count > 1 {
			id = fmt.Sprintf("%s-%05d", idPrefix, index)
		}
		_, err = stmt.Exec(
			id, tenantID, projectID, content, int(memory.LevelDomain),
			"conversation", "chat", boundedSessionTestRequestRef('a'),
			stamp, stamp, "session_memory", sessionID, string(memory.OriginDerived),
		)
		require.NoError(t, err)
	}
	require.NoError(t, stmt.Close())
	require.NoError(t, tx.Commit())
}

func requireBoundedSessionErrorCode(
	t *testing.T,
	result *mcp.CallToolResult,
	code string,
) boundedSessionErrorEnvelope {
	t.Helper()
	require.NotNil(t, result)
	require.True(t, result.IsError)
	require.Empty(t, result.Content, "bounded session errors must be structured-only")
	envelope := decodeStructuredResult[boundedSessionErrorEnvelope](t, result)
	require.Equal(t, code, envelope.Error.Code)
	return envelope
}

func firstBoundedSessionSearchPage(
	t *testing.T,
	srv *Server,
	tenantID, projectID, sessionID, query string,
	limit, maxFactBytes int,
) boundedSessionSearchEnvelope {
	t.Helper()
	result, err := srv.handleSearchScopedSessionFactsPage(
		context.Background(),
		sessionToolReq("search_scoped_session_facts_page", map[string]interface{}{
			"session_id":     sessionID,
			"query":          query,
			"mode":           "keyword",
			"limit":          float64(limit),
			"max_fact_bytes": float64(maxFactBytes),
		}, tenantID, projectID),
	)
	require.NoError(t, err)
	require.False(t, result.IsError)
	require.Empty(t, result.Content, "bounded session pages must be structured-only")
	return decodeStructuredResult[boundedSessionSearchEnvelope](t, result)
}

func collectBoundedSessionSearch(
	t *testing.T,
	srv *Server,
	tenantID, projectID, sessionID, query string,
	limit, maxFactBytes int,
) collectedBoundedSessionSearch {
	t.Helper()
	collected := collectedBoundedSessionSearch{serialized: map[string][]byte{}}
	frameDigests := map[string]string{}
	frameTotals := map[string]int{}
	cursor := ""
	for pageNumber := 0; pageNumber < limit*40+40; pageNumber++ {
		arguments := map[string]interface{}{
			"session_id":     sessionID,
			"query":          query,
			"mode":           "keyword",
			"limit":          float64(limit),
			"max_fact_bytes": float64(maxFactBytes),
		}
		if cursor != "" {
			arguments["cursor"] = cursor
		}
		result, err := srv.handleSearchScopedSessionFactsPage(
			context.Background(),
			sessionToolReq("search_scoped_session_facts_page", arguments, tenantID, projectID),
		)
		require.NoError(t, err)
		require.False(t, result.IsError)
		require.Empty(t, result.Content, "bounded session pages must be structured-only")
		wire, err := json.Marshal(result)
		require.NoError(t, err)
		require.Less(t, len(wire), 1<<20, "each MCP page must remain below one MiB")

		envelope := decodeStructuredResult[boundedSessionSearchEnvelope](t, result)
		require.Equal(t, boundedSessionScope{
			Version: 1, Kind: "session", TenantID: tenantID,
			ProjectID: projectID, SessionID: sessionID,
		}, envelope.MemoryScope)
		require.Equal(t, boundedSessionProtocolVersion, envelope.Page.Version)
		require.Equal(t, factPageFrameRawBytes, envelope.Page.FrameRawLimitBytes)
		require.Equal(t, maxFactBytes, envelope.Page.MaxFactBytes)
		require.LessOrEqual(t, len(envelope.Page.NextCursor), boundedSessionMaxCursorBytes)
		require.Len(t, envelope.Page.Frames, 1)
		frame := envelope.Page.Frames[0]
		require.NotContains(t, frame.DataBase64, "\n")
		require.NotContains(t, frame.DataBase64, "\r")
		raw, err := base64.StdEncoding.DecodeString(frame.DataBase64)
		require.NoError(t, err)
		require.NotEmpty(t, raw)
		require.LessOrEqual(t, len(raw), factPageFrameRawBytes)
		if _, present := frameTotals[frame.FactID]; !present {
			collected.order = append(collected.order, frame.FactID)
			frameTotals[frame.FactID] = frame.TotalBytes
			frameDigests[frame.FactID] = frame.SHA256
		} else {
			require.Equal(t, frameTotals[frame.FactID], frame.TotalBytes)
			require.Equal(t, frameDigests[frame.FactID], frame.SHA256)
		}
		require.Equal(t, len(collected.serialized[frame.FactID]), frame.Offset)
		collected.serialized[frame.FactID] = append(collected.serialized[frame.FactID], raw...)
		if frame.Final {
			require.Len(t, collected.serialized[frame.FactID], frame.TotalBytes)
			digest := sha256.Sum256(collected.serialized[frame.FactID])
			require.Equal(t, frame.SHA256, hex.EncodeToString(digest[:]))
		}
		collected.pages++
		if envelope.Page.Done {
			require.Empty(t, envelope.Page.NextCursor)
			require.Len(t, collected.order, envelope.Page.ResultCount)
			return collected
		}
		require.NotEmpty(t, envelope.Page.NextCursor)
		cursor = envelope.Page.NextCursor
	}
	t.Fatal("bounded session search did not finish within the page cap")
	return collected
}

func TestBoundedSessionToolSchemasAreExactAndAdditive(t *testing.T) {
	srv, _ := newProjectTestServer(t, rlmscope.New("tenant-a", "project-alpha"))
	tests := map[string]struct {
		required []string
		fields   []string
	}{
		"add_scoped_session_turn": {
			required: []string{"session_id", "turn_id", "content", "request_ref"},
			fields:   []string{"session_id", "turn_id", "content", "request_ref"},
		},
		"get_scoped_session_turn": {
			required: []string{"session_id", "turn_id", "request_ref"},
			fields:   []string{"session_id", "turn_id", "request_ref"},
		},
		"search_scoped_session_facts_page": {
			required: []string{"session_id", "query", "mode", "limit", "max_fact_bytes"},
			fields:   []string{"session_id", "query", "mode", "limit", "max_fact_bytes", "cursor"},
		},
	}
	for name, expected := range tests {
		tool := srv.mcp.GetTool(name)
		require.NotNil(t, tool, name)
		require.NotNil(t, tool.Handler, name)
		require.Equal(t, "object", tool.Tool.InputSchema.Type, name)
		require.ElementsMatch(t, expected.required, tool.Tool.InputSchema.Required, name)
		require.ElementsMatch(t, expected.fields, mapKeys(tool.Tool.InputSchema.Properties), name)
	}
	for _, legacy := range []string{"add_session_fact", "get_session_turn", "search_session_facts"} {
		require.NotNil(t, srv.mcp.GetTool(legacy), "legacy tool %s must remain registered", legacy)
	}
}

func TestBoundedSessionTurnAddAndGetAreCompactStructuredAndRequestBound(t *testing.T) {
	srv, _ := newProjectTestServer(t, rlmscope.New("tenant-a", "project-alpha"))
	requestRef := boundedSessionTestRequestRef('a')
	content := "private managed turn\nwith <markup> and a second line"
	arguments := map[string]interface{}{
		"session_id":  "session-one",
		"turn_id":     testTurnID,
		"content":     content,
		"request_ref": requestRef,
	}

	first, err := srv.handleAddScopedSessionTurn(context.Background(), sessionToolReq(
		"add_scoped_session_turn", arguments, "tenant-a", "project-alpha",
	))
	require.NoError(t, err)
	require.False(t, first.IsError)
	require.Empty(t, first.Content)
	firstEnvelope := decodeStructuredResult[boundedSessionTurnEnvelope](t, first)
	require.Equal(t, boundedSessionScope{
		Version: 1, Kind: "session", TenantID: "tenant-a",
		ProjectID: "project-alpha", SessionID: "session-one",
	}, firstEnvelope.MemoryScope)
	require.True(t, firstEnvelope.Result.Found)
	require.False(t, firstEnvelope.Result.Deduplicated)
	require.NotNil(t, firstEnvelope.Result.TurnReceipt)
	require.Equal(t, testTurnID, firstEnvelope.Result.TurnReceipt.TurnID)
	require.Equal(t, firstEnvelope.Result.FactID, firstEnvelope.Result.TurnReceipt.FactID)
	digest := sha256.Sum256([]byte(content))
	require.Equal(t, hex.EncodeToString(digest[:]), firstEnvelope.Result.ContentSHA256)
	require.Equal(t, len(content), firstEnvelope.Result.ContentBytes)

	structured, err := json.Marshal(first.StructuredContent)
	require.NoError(t, err)
	require.NotContains(t, string(structured), "private managed turn")
	var rawEnvelope map[string]json.RawMessage
	require.NoError(t, json.Unmarshal(structured, &rawEnvelope))
	require.ElementsMatch(t, []string{"memory_scope", "result"}, mapKeys(rawEnvelope))
	var rawResult map[string]json.RawMessage
	require.NoError(t, json.Unmarshal(rawEnvelope["result"], &rawResult))
	require.ElementsMatch(t, []string{
		"version", "found", "deduplicated", "turn_receipt", "fact_id",
		"content_sha256", "content_bytes",
	}, mapKeys(rawResult))
	require.NotContains(t, rawResult, "content")

	retryArguments := map[string]interface{}{
		"session_id":  "session-one",
		"turn_id":     testTurnID,
		"content":     "changed retry projection that must not replace the committed turn",
		"request_ref": requestRef,
	}
	retry, err := srv.handleAddScopedSessionTurn(context.Background(), sessionToolReq(
		"add_scoped_session_turn", retryArguments, "tenant-a", "project-alpha",
	))
	require.NoError(t, err)
	require.False(t, retry.IsError)
	require.Empty(t, retry.Content)
	retryEnvelope := decodeStructuredResult[boundedSessionTurnEnvelope](t, retry)
	require.True(t, retryEnvelope.Result.Deduplicated)
	require.Equal(t, firstEnvelope.Result.FactID, retryEnvelope.Result.FactID)
	require.Equal(t, firstEnvelope.Result.TurnReceipt, retryEnvelope.Result.TurnReceipt)
	require.Equal(t, firstEnvelope.Result.ContentSHA256, retryEnvelope.Result.ContentSHA256)
	require.Equal(t, firstEnvelope.Result.ContentBytes, retryEnvelope.Result.ContentBytes)
	conflictingAdd, err := srv.handleAddScopedSessionTurn(context.Background(), sessionToolReq(
		"add_scoped_session_turn", map[string]interface{}{
			"session_id": "session-one", "turn_id": testTurnID,
			"content": content, "request_ref": boundedSessionTestRequestRef('b'),
		}, "tenant-a", "project-alpha",
	))
	require.NoError(t, err)
	requireBoundedSessionErrorCode(t, conflictingAdd, "turn_conflict")

	lookup, err := srv.handleGetScopedSessionTurn(context.Background(), sessionToolReq(
		"get_scoped_session_turn", map[string]interface{}{
			"session_id": "session-one", "turn_id": testTurnID, "request_ref": requestRef,
		}, "tenant-a", "project-alpha",
	))
	require.NoError(t, err)
	require.False(t, lookup.IsError)
	require.Empty(t, lookup.Content)
	lookupEnvelope := decodeStructuredResult[boundedSessionTurnEnvelope](t, lookup)
	require.True(t, lookupEnvelope.Result.Found)
	require.Equal(t, firstEnvelope.Result.FactID, lookupEnvelope.Result.FactID)
	lookupWire, err := json.Marshal(lookup.StructuredContent)
	require.NoError(t, err)
	require.NotContains(t, string(lookupWire), "private managed turn")
	require.NotContains(t, string(lookupWire), "changed retry projection")
	rawEnvelope = nil
	rawResult = nil
	require.NoError(t, json.Unmarshal(lookupWire, &rawEnvelope))
	require.NoError(t, json.Unmarshal(rawEnvelope["result"], &rawResult))
	require.ElementsMatch(t, []string{
		"version", "found", "deduplicated", "turn_receipt", "fact_id",
	}, mapKeys(rawResult))

	conflict, err := srv.handleGetScopedSessionTurn(context.Background(), sessionToolReq(
		"get_scoped_session_turn", map[string]interface{}{
			"session_id": "session-one", "turn_id": testTurnID,
			"request_ref": boundedSessionTestRequestRef('b'),
		}, "tenant-a", "project-alpha",
	))
	require.NoError(t, err)
	requireBoundedSessionErrorCode(t, conflict, "turn_conflict")

	missing, err := srv.handleGetScopedSessionTurn(context.Background(), sessionToolReq(
		"get_scoped_session_turn", map[string]interface{}{
			"session_id": "session-one", "turn_id": testTurnIDB,
			"request_ref": boundedSessionTestRequestRef('b'),
		}, "tenant-a", "project-alpha",
	))
	require.NoError(t, err)
	require.False(t, missing.IsError)
	require.Empty(t, missing.Content)
	require.False(t, decodeStructuredResult[boundedSessionTurnEnvelope](t, missing).Result.Found)
	missingWire, err := json.Marshal(missing.StructuredContent)
	require.NoError(t, err)
	rawEnvelope = nil
	rawResult = nil
	require.NoError(t, json.Unmarshal(missingWire, &rawEnvelope))
	require.NoError(t, json.Unmarshal(rawEnvelope["result"], &rawResult))
	require.ElementsMatch(t, []string{"version", "found", "deduplicated"}, mapKeys(rawResult))
}

func TestBoundedSessionSearchRequiresStoredPreflightWithoutLegacyFallback(t *testing.T) {
	srv, repo, _ := newBoundedSessionRepoServer(t, rlmscope.New("tenant-a", "project-alpha"))
	store := &boundedSessionNoPreflightStore{FactStore: repo, SessionFactStore: repo}
	srv.facts = applicationtools.NewFactService(store, nil)

	result, err := srv.handleSearchScopedSessionFactsPage(context.Background(), sessionToolReq(
		"search_scoped_session_facts_page", map[string]interface{}{
			"session_id": "session-one", "query": "needle", "mode": "keyword",
			"limit": float64(20), "max_fact_bytes": float64(1024 * 1024),
		}, "tenant-a", "project-alpha",
	))
	require.NoError(t, err)
	requireBoundedSessionErrorCode(t, result, "search_unavailable")
	require.Zero(t, store.keywordCalls, "bounded wire must never call legacy all-row keyword search")
	require.Zero(t, store.vectorCalls, "bounded wire must never call legacy all-row vector search")
}

func TestBoundedSessionSearchModesNeverCallLegacyAllRowSearch(t *testing.T) {
	for _, mode := range []string{"keyword", "semantic", "hybrid"} {
		t.Run(mode, func(t *testing.T) {
			srv, repo, _ := newBoundedSessionRepoServer(t, rlmscope.New("tenant-a", "project-alpha"))
			ctx := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-alpha"))
			stamp := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
			fact := memory.NewFact("needle bounded", memory.LevelDomain, "conversation", "chat")
			fact.ID = "fact-a"
			fact.CodeRef = boundedSessionTestRequestRef('a')
			fact.Source = "session_memory"
			fact.Origin = memory.OriginDerived
			fact.CreatedAt = stamp
			fact.ValidFrom = stamp
			fact.UpdatedAt = stamp
			fact.Embedding = []float64{1}
			require.NoError(t, repo.AddForSession(ctx, "session-one", fact))
			store := &boundedSessionLegacySearchSpyStore{FactRepo: repo}
			service := applicationtools.NewFactService(store, nil)
			service.SetEmbedder(boundedSearchFakeEmbedder{})
			srv.facts = service

			result, err := srv.handleSearchScopedSessionFactsPage(context.Background(), sessionToolReq(
				"search_scoped_session_facts_page", map[string]interface{}{
					"session_id": "session-one", "query": "needle", "mode": mode,
					"limit": float64(20), "max_fact_bytes": float64(1024 * 1024),
				}, "tenant-a", "project-alpha",
			))
			require.NoError(t, err)
			require.False(t, result.IsError)
			require.Zero(t, store.keywordCalls)
			require.Zero(t, store.vectorCalls)
		})
	}
}

func TestBoundedSessionSearchRejectsStoredHardLimitsBeforeRanking(t *testing.T) {
	tests := []struct {
		name       string
		idPrefix   string
		content    string
		count      int
		code       string
		assertWire func(*testing.T, boundedSearchStoredLimitError)
	}{
		{
			name: "identity above 256 bytes", idPrefix: strings.Repeat("i", 257),
			content: "needle", count: 1, code: "stored_fact_identity_too_large",
			assertWire: func(t *testing.T, got boundedSearchStoredLimitError) {
				require.Equal(t, int64(257), got.StoredIdentityBytes)
				require.Equal(t, int64(256), got.MaxStoredIdentityBytes)
			},
		},
		{
			name: "one variable row above 16 MiB", idPrefix: "oversized-row",
			content: "needle" + strings.Repeat("x", 16*1024*1024), count: 1,
			code: "stored_fact_too_large",
			assertWire: func(t *testing.T, got boundedSearchStoredLimitError) {
				require.Greater(t, got.StoredVariableBytes, int64(16*1024*1024))
				require.Equal(t, int64(16*1024*1024), got.MaxStoredVariableBytes)
			},
		},
		{
			name: "exact session aggregate above 32 MiB", idPrefix: "aggregate",
			content: "needle" + strings.Repeat("y", 11*1024*1024), count: 3,
			code: "stored_search_scope_too_large",
			assertWire: func(t *testing.T, got boundedSearchStoredLimitError) {
				require.Greater(t, got.StoredTotalBytes, int64(32*1024*1024))
				require.Equal(t, int64(32*1024*1024), got.MaxStoredTotalBytes)
			},
		},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			srv, _, db := newBoundedSessionRepoServer(t, rlmscope.New("tenant-a", "project-alpha"))
			insertRawManagedSessionFacts(
				t, db, "tenant-a", "project-alpha", "session-one", tc.idPrefix, tc.content, tc.count,
			)
			result, err := srv.handleSearchScopedSessionFactsPage(context.Background(), sessionToolReq(
				"search_scoped_session_facts_page", map[string]interface{}{
					"session_id": "session-one", "query": "needle", "mode": "keyword",
					"limit": float64(20), "max_fact_bytes": float64(factPageMaxFactBytes),
				}, "tenant-a", "project-alpha",
			))
			require.NoError(t, err)
			requireBoundedSessionErrorCode(t, result, tc.code)
			envelope := decodeStructuredResult[boundedSessionStoredLimitTestEnvelope](t, result)
			require.Equal(t, boundedSessionScope{
				Version: 1, Kind: "session", TenantID: "tenant-a",
				ProjectID: "project-alpha", SessionID: "session-one",
			}, envelope.MemoryScope)
			tc.assertWire(t, envelope.Error)
		})
	}
}

func TestBoundedSessionSearchRejectsMoreThanTenThousandExactRows(t *testing.T) {
	srv, _, db := newBoundedSessionRepoServer(t, rlmscope.New("tenant-a", "project-alpha"))
	// This fixture targets the session-search preflight only. The unrelated
	// export-sequence INSERT trigger performs child-maintenance work per row and
	// makes 10,001 synthetic inserts approach the package's race-test timeout.
	// The in-memory database is private to this test and never serves paging.
	_, err := db.Exec(`DROP TRIGGER fact_export_sequence_insert_v1`)
	require.NoError(t, err)
	insertRawManagedSessionFacts(
		t, db, "tenant-a", "project-alpha", "session-one", "many", "needle", 10_001,
	)
	result, err := srv.handleSearchScopedSessionFactsPage(context.Background(), sessionToolReq(
		"search_scoped_session_facts_page", map[string]interface{}{
			"session_id": "session-one", "query": "needle", "mode": "keyword",
			"limit": float64(20), "max_fact_bytes": float64(1024 * 1024),
		}, "tenant-a", "project-alpha",
	))
	require.NoError(t, err)
	requireBoundedSessionErrorCode(t, result, "search_unavailable")
}

func TestBoundedSessionSearchUsesExactTenantProjectAndSessionScope(t *testing.T) {
	srv, _ := newProjectTestServer(t, rlmscope.New("tenant-a", "project-alpha"))
	stores := []struct {
		tenant, project, session, content string
		turnID                            string
		requestRef                        string
	}{
		{"tenant-a", "project-alpha", "session-one", "needle alpha one", testTurnID, boundedSessionTestRequestRef('a')},
		{"tenant-a", "project-alpha", "session-two", "needle alpha two", testTurnID, boundedSessionTestRequestRef('b')},
		{"tenant-a", "project-beta", "session-one", "needle beta one", testTurnID, boundedSessionTestRequestRef('c')},
		{"tenant-b", "project-alpha", "session-one", "needle other tenant", testTurnID, boundedSessionTestRequestRef('d')},
	}
	for _, tc := range stores {
		result, err := srv.handleAddScopedSessionTurn(context.Background(), sessionToolReq(
			"add_scoped_session_turn", map[string]interface{}{
				"session_id": tc.session, "turn_id": tc.turnID,
				"content": tc.content, "request_ref": tc.requestRef,
			}, tc.tenant, tc.project,
		))
		require.NoError(t, err)
		require.False(t, result.IsError)
	}

	for _, tc := range stores {
		collected := collectBoundedSessionSearch(
			t, srv, tc.tenant, tc.project, tc.session, "needle", 20, 1024*1024,
		)
		require.Len(t, collected.order, 1)
		var fact boundedSessionRecallFact
		require.NoError(t, json.Unmarshal(collected.serialized[collected.order[0]], &fact))
		require.Equal(t, tc.tenant, fact.TenantID)
		require.Equal(t, tc.project, fact.ProjectID)
		require.Equal(t, tc.session, fact.SessionID)
		require.Equal(t, tc.content, fact.Content)
	}

	empty := firstBoundedSessionSearchPage(
		t, srv, "tenant-a", "project-alpha", "session-missing", "needle", 20, 1024*1024,
	)
	require.True(t, empty.Page.Done)
	require.Zero(t, empty.Page.ResultCount)
	require.Empty(t, empty.Page.Frames)

	missingMeta, err := srv.handleSearchScopedSessionFactsPage(context.Background(), callToolReq(
		"search_scoped_session_facts_page", map[string]interface{}{
			"session_id": "session-one", "query": "needle", "mode": "keyword",
			"limit": float64(20), "max_fact_bytes": float64(1024 * 1024),
		},
	))
	require.NoError(t, err)
	requireBoundedSessionErrorCode(t, missingMeta, "invalid_scope")

	middlewareMismatch, err := srv.handleSearchScopedSessionFactsPage(
		rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-beta")),
		sessionToolReq("search_scoped_session_facts_page", map[string]interface{}{
			"session_id": "session-one", "query": "needle", "mode": "keyword",
			"limit": float64(20), "max_fact_bytes": float64(1024 * 1024),
		}, "tenant-a", "project-alpha"),
	)
	require.NoError(t, err)
	requireBoundedSessionErrorCode(t, middlewareMismatch, "invalid_scope")
}

func TestBoundedSessionSearchFramesAdversarialContentWithoutRawLinesOrGaps(t *testing.T) {
	srv, repo, _ := newBoundedSessionRepoServer(t, rlmscope.New("tenant-a", "project-alpha"))
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-alpha"))
	content := "needle " + strings.Repeat("</script><tag>&\n\r\x00\x01", 45_000)
	addManagedBoundedSessionFact(
		t, repo, ctx, "session-one", "adversarial-fact", content,
		time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC),
	)

	collected := collectBoundedSessionSearch(
		t, srv, "tenant-a", "project-alpha", "session-one", "needle", 20, 4*1024*1024,
	)
	require.Equal(t, []string{"adversarial-fact"}, collected.order)
	require.Greater(t, collected.pages, 1, "escaped content must span multiple 512 KiB frames")
	var decoded boundedSessionRecallFact
	require.NoError(t, json.Unmarshal(collected.serialized["adversarial-fact"], &decoded))
	require.Equal(t, content, decoded.Content)
	require.Equal(t, memory.LevelDomain, decoded.Level)
	require.Equal(t, memory.OriginDerived, decoded.Origin)
}

func TestBoundedSessionContinuationRevalidatesEveryFrozenFullFact(t *testing.T) {
	srv, repo, db := newBoundedSessionRepoServer(t, rlmscope.New("tenant-a", "project-alpha"))
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-alpha"))
	stamp := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
	addManagedBoundedSessionFact(t, repo, ctx, "session-one", "fact-a", "needle newest", stamp.Add(time.Minute))
	addManagedBoundedSessionFact(t, repo, ctx, "session-one", "fact-b", "needle older", stamp)
	first := firstBoundedSessionSearchPage(
		t, srv, "tenant-a", "project-alpha", "session-one", "needle", 20, 1024*1024,
	)
	require.False(t, first.Page.Done)
	require.Equal(t, "fact-a", first.Page.Frames[0].FactID)
	require.NotEmpty(t, first.Page.NextCursor)

	// created_at is deliberately absent from the compact frame, but affects tied
	// session ranking. Mutating the already-emitted first result must still make
	// the continuation fail, proving every frozen full Fact is revalidated.
	_, err := db.Exec(`UPDATE hierarchical_facts SET created_at = ?
		WHERE id = ? AND tenant_id = ? AND project_id = ? AND session_id = ?`,
		stamp.Add(-time.Hour).Format(time.RFC3339Nano),
		"fact-a", "tenant-a", "project-alpha", "session-one",
	)
	require.NoError(t, err)

	changed, err := srv.handleSearchScopedSessionFactsPage(context.Background(), sessionToolReq(
		"search_scoped_session_facts_page", map[string]interface{}{
			"session_id": "session-one", "query": "needle", "mode": "keyword",
			"limit": float64(20), "max_fact_bytes": float64(1024 * 1024),
			"cursor": first.Page.NextCursor,
		}, "tenant-a", "project-alpha",
	))
	require.NoError(t, err)
	requireBoundedSessionErrorCode(t, changed, "page_changed")
}

func TestBoundedSessionContinuationIgnoresPostFreezeInsert(t *testing.T) {
	srv, repo, _ := newBoundedSessionRepoServer(t, rlmscope.New("tenant-a", "project-alpha"))
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-alpha"))
	stamp := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
	addManagedBoundedSessionFact(t, repo, ctx, "session-one", "fact-a", "needle first", stamp.Add(time.Minute))
	addManagedBoundedSessionFact(t, repo, ctx, "session-one", "fact-b", "needle second", stamp)
	first := firstBoundedSessionSearchPage(
		t, srv, "tenant-a", "project-alpha", "session-one", "needle", 20, 1024*1024,
	)
	require.Equal(t, "fact-a", first.Page.Frames[0].FactID)
	require.False(t, first.Page.Done)

	addManagedBoundedSessionFact(
		t, repo, ctx, "session-one", "fact-new", "needle inserted after freeze", stamp.Add(2*time.Minute),
	)
	continued, err := srv.handleSearchScopedSessionFactsPage(context.Background(), sessionToolReq(
		"search_scoped_session_facts_page", map[string]interface{}{
			"session_id": "session-one", "query": "needle", "mode": "keyword",
			"limit": float64(20), "max_fact_bytes": float64(1024 * 1024),
			"cursor": first.Page.NextCursor,
		}, "tenant-a", "project-alpha",
	))
	require.NoError(t, err)
	require.False(t, continued.IsError)
	envelope := decodeStructuredResult[boundedSessionSearchEnvelope](t, continued)
	require.True(t, envelope.Page.Done)
	require.Equal(t, 2, envelope.Page.ResultCount)
	require.Equal(t, "fact-b", envelope.Page.Frames[0].FactID)
}

func nonCanonicalRawURLAlias(t *testing.T, value string) string {
	t.Helper()
	require.NotEmpty(t, value)
	const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
	last := strings.IndexByte(alphabet, value[len(value)-1])
	require.NotEqual(t, -1, last)
	base := last &^ 3
	require.NotEqual(t, base+1, last, "canonical 32-byte base64url must use zero trailing bits")
	alias := value[:len(value)-1] + string(alphabet[base+1])
	original, err := base64.RawURLEncoding.DecodeString(value)
	require.NoError(t, err)
	aliased, err := base64.RawURLEncoding.DecodeString(alias)
	require.NoError(t, err)
	require.Equal(t, original, aliased)
	require.NotEqual(t, base64.RawURLEncoding.EncodeToString(aliased), alias)
	return alias
}

func TestBoundedSessionCursorRejectsMalleableAndMismatchedEncodings(t *testing.T) {
	srv, repo, _ := newBoundedSessionRepoServer(t, rlmscope.New("tenant-a", "project-alpha"))
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-alpha"))
	stamp := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
	addManagedBoundedSessionFact(t, repo, ctx, "session-one", "fact-a", "needle first", stamp.Add(time.Minute))
	addManagedBoundedSessionFact(t, repo, ctx, "session-one", "fact-b", "needle second", stamp)
	first := firstBoundedSessionSearchPage(
		t, srv, "tenant-a", "project-alpha", "session-one", "needle", 20, 1024*1024,
	)
	parts := strings.Split(first.Page.NextCursor, ".")
	require.Len(t, parts, 2)
	malleable := parts[0] + "." + nonCanonicalRawURLAlias(t, parts[1])

	tests := map[string]map[string]interface{}{
		"non-canonical signature": {
			"session_id": "session-one", "query": "needle", "mode": "keyword",
			"limit": float64(20), "max_fact_bytes": float64(1024 * 1024), "cursor": malleable,
		},
		"tampered": {
			"session_id": "session-one", "query": "needle", "mode": "keyword",
			"limit": float64(20), "max_fact_bytes": float64(1024 * 1024),
			"cursor": first.Page.NextCursor + "x",
		},
		"query mismatch": {
			"session_id": "session-one", "query": "different", "mode": "keyword",
			"limit": float64(20), "max_fact_bytes": float64(1024 * 1024),
			"cursor": first.Page.NextCursor,
		},
		"overlong": {
			"session_id": "session-one", "query": "needle", "mode": "keyword",
			"limit": float64(20), "max_fact_bytes": float64(1024 * 1024),
			"cursor": strings.Repeat("a", boundedSessionMaxCursorBytes+1),
		},
	}
	for name, arguments := range tests {
		t.Run(name, func(t *testing.T) {
			result, err := srv.handleSearchScopedSessionFactsPage(context.Background(), sessionToolReq(
				"search_scoped_session_facts_page", arguments, "tenant-a", "project-alpha",
			))
			require.NoError(t, err)
			requireBoundedSessionErrorCode(t, result, "invalid_cursor")
		})
	}
}

func TestBoundedSessionCursorFitsOneHundredMaximumLengthFrozenIDs(t *testing.T) {
	marker := boundedSessionScope{
		Version: 1, Kind: "session", TenantID: strings.Repeat("t", 128),
		ProjectID: strings.Repeat("p", 128), SessionID: strings.Repeat("s", 128),
	}
	cursor := boundedSessionSearchCursor{
		Version: boundedSessionProtocolVersion, MemoryScope: marker,
		QuerySHA256: strings.Repeat("a", sha256.Size*2), Mode: "keyword",
		Limit: 100, MaxFactBytes: factPageMaxFactBytes,
		ResultIndex: 99, IntraFactOffset: 1,
	}
	for index := 0; index < 100; index++ {
		prefix := fmt.Sprintf("%03d", index)
		cursor.Results = append(cursor.Results, boundedSessionCursorFact{
			FactID:         prefix + strings.Repeat("x", 256-len(prefix)),
			SHA256:         strings.Repeat("b", sha256.Size*2),
			StateSHA256:    strings.Repeat("c", sha256.Size*2),
			SerializedSize: factPageMaxFactBytes,
		})
	}
	token, err := encodeBoundedSessionCursor(cursor)
	require.NoError(t, err)
	require.LessOrEqual(t, len(token), boundedSessionMaxCursorBytes)
	decoded, err := decodeBoundedSessionCursor(
		token, marker, cursor.QuerySHA256, cursor.Mode, cursor.Limit, cursor.MaxFactBytes,
	)
	require.NoError(t, err)
	require.Equal(t, cursor, decoded)
}

func TestBoundedSessionArgumentsAndOversizedFactFailWithBoundedStructuredErrors(t *testing.T) {
	srv, repo, _ := newBoundedSessionRepoServer(t, rlmscope.New("tenant-a", "project-alpha"))
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-alpha"))
	fact := addManagedBoundedSessionFact(
		t, repo, ctx, "session-one", "fact-a", "needle bounded",
		time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC),
	)
	compact, err := compactManagedSessionFact(ctx, "session-one", fact)
	require.NoError(t, err)
	serialized, err := json.Marshal(compact)
	require.NoError(t, err)

	oversized, err := srv.handleSearchScopedSessionFactsPage(context.Background(), sessionToolReq(
		"search_scoped_session_facts_page", map[string]interface{}{
			"session_id": "session-one", "query": "needle", "mode": "keyword",
			"limit": float64(100), "max_fact_bytes": float64(len(serialized) - 1),
		}, "tenant-a", "project-alpha",
	))
	require.NoError(t, err)
	errorEnvelope := requireBoundedSessionErrorCode(t, oversized, "fact_too_large")
	require.Equal(t, "fact-a", errorEnvelope.Error.FactID)
	require.Equal(t, len(serialized), errorEnvelope.Error.FactBytes)
	require.Equal(t, len(serialized)-1, errorEnvelope.Error.MaxFactBytes)

	for name, arguments := range map[string]map[string]interface{}{
		"limit above maximum": {
			"session_id": "session-one", "query": "needle", "mode": "keyword",
			"limit": float64(101), "max_fact_bytes": float64(factPageMaxFactBytes),
		},
		"fact bound above maximum": {
			"session_id": "session-one", "query": "needle", "mode": "keyword",
			"limit": float64(100), "max_fact_bytes": float64(factPageMaxFactBytes + 1),
		},
		"fractional limit": {
			"session_id": "session-one", "query": "needle", "mode": "keyword",
			"limit": 1.5, "max_fact_bytes": float64(factPageMaxFactBytes),
		},
		"unknown argument": {
			"session_id": "session-one", "query": "needle", "mode": "keyword",
			"limit": float64(100), "max_fact_bytes": float64(factPageMaxFactBytes), "extra": true,
		},
	} {
		t.Run(name, func(t *testing.T) {
			result, err := srv.handleSearchScopedSessionFactsPage(context.Background(), sessionToolReq(
				"search_scoped_session_facts_page", arguments, "tenant-a", "project-alpha",
			))
			require.NoError(t, err)
			requireBoundedSessionErrorCode(t, result, "invalid_arguments")
		})
	}

	longUnknown := map[string]interface{}{
		"session_id": "session-one", "query": "needle", "mode": "keyword",
		"limit": float64(100), "max_fact_bytes": float64(factPageMaxFactBytes),
		strings.Repeat("unknown", 20_000): true,
	}
	boundedError, err := srv.handleSearchScopedSessionFactsPage(context.Background(), sessionToolReq(
		"search_scoped_session_facts_page", longUnknown, "tenant-a", "project-alpha",
	))
	require.NoError(t, err)
	requireBoundedSessionErrorCode(t, boundedError, "invalid_arguments")
	boundedErrorWire, err := json.Marshal(boundedError)
	require.NoError(t, err)
	require.Less(t, len(boundedErrorWire), 4096, "unknown argument names must not be reflected into responses")

	tooLargeContent, err := srv.handleAddScopedSessionTurn(context.Background(), sessionToolReq(
		"add_scoped_session_turn", map[string]interface{}{
			"session_id": "session-one", "turn_id": testTurnID,
			"content":     strings.Repeat("x", boundedSessionMaxContentBytes+1),
			"request_ref": boundedSessionTestRequestRef('a'),
		}, "tenant-a", "project-alpha",
	))
	require.NoError(t, err)
	requireBoundedSessionErrorCode(t, tooLargeContent, "invalid_arguments")
}

func TestLegacySessionSearchTextGoldenIsUnchangedByBoundedSessionSearch(t *testing.T) {
	srv, repo, _ := newBoundedSessionRepoServer(t, rlmscope.New("tenant-a", "project-alpha"))
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-alpha"))
	addManagedBoundedSessionFact(
		t, repo, ctx, "session-one", "legacy-fact", "needle legacy contract",
		time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC),
	)
	legacyRequest := sessionToolReq("search_session_facts", map[string]interface{}{
		"session_id": "session-one", "query": "needle", "mode": "keyword", "limit": float64(20),
	}, "tenant-a", "project-alpha")

	before, err := srv.handleSearchSessionFacts(context.Background(), legacyRequest)
	require.NoError(t, err)
	require.False(t, before.IsError)
	require.Nil(t, before.StructuredContent)
	beforeText := extractText(t, before)
	require.Contains(t, beforeText, "needle legacy contract")

	bounded := firstBoundedSessionSearchPage(
		t, srv, "tenant-a", "project-alpha", "session-one", "needle", 20, 1024*1024,
	)
	require.True(t, bounded.Page.Done)
	after, err := srv.handleSearchSessionFacts(context.Background(), legacyRequest)
	require.NoError(t, err)
	require.False(t, after.IsError)
	require.Nil(t, after.StructuredContent)
	require.Equal(t, beforeText, extractText(t, after))
}
