package mcpserver

import (
	"context"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"net/http"
	"strings"
	"testing"
	"time"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/stretchr/testify/require"

	applicationtools "github.com/syntrex/gomcp/internal/application/tools"
	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
)

type factPagePreflightProbeStore struct {
	memory.FactStore
	err       error
	listCalls int
}

func (s *factPagePreflightProbeStore) ListByLevelPage(
	context.Context,
	memory.HierLevel,
	int,
	int64,
	int64,
	*memory.FactPageKey,
) (*memory.FactPage, error) {
	s.listCalls++
	return nil, s.err
}

func (s *factPagePreflightProbeStore) GetByLevelPageKey(
	context.Context,
	memory.HierLevel,
	int,
	int64,
	int64,
	memory.FactPageKey,
	int,
) (*memory.FactPageRecord, error) {
	return nil, s.err
}

func (s *factPagePreflightProbeStore) ReleaseFactPage(
	context.Context,
	memory.HierLevel,
	memory.FactPageKey,
) error {
	return s.err
}

func decodeStructuredResult[T any](t *testing.T, result *mcp.CallToolResult) T {
	t.Helper()
	require.NotNil(t, result)
	require.Empty(t, result.Content, "paged export must not duplicate structured data into text content")
	require.NotNil(t, result.StructuredContent)
	raw, err := json.Marshal(result.StructuredContent)
	require.NoError(t, err)
	var decoded T
	require.NoError(t, json.Unmarshal(raw, &decoded))
	return decoded
}

func decodeSingleFactFrame(t *testing.T, envelope factPageEnvelope) *memory.Fact {
	t.Helper()
	require.Len(t, envelope.Page.Frames, 1)
	frame := envelope.Page.Frames[0]
	require.Zero(t, frame.Offset)
	require.True(t, frame.Final)
	raw, err := base64.StdEncoding.DecodeString(frame.DataBase64)
	require.NoError(t, err)
	require.Len(t, raw, frame.TotalBytes)
	digest := sha256.Sum256(raw)
	require.Equal(t, hex.EncodeToString(digest[:]), frame.SHA256)
	var fact memory.Fact
	require.NoError(t, json.Unmarshal(raw, &fact))
	require.Equal(t, frame.FactID, fact.ID)
	return &fact
}

func addTransportPageFact(t *testing.T, repo interface {
	Add(context.Context, *memory.Fact) error
}, ctx context.Context, id, content string, createdAt time.Time) *memory.Fact {
	t.Helper()
	fact := memory.NewFact(content, memory.LevelProject, "paging", "")
	fact.ID = id
	fact.CreatedAt = createdAt
	fact.ValidFrom = createdAt
	fact.UpdatedAt = createdAt
	require.NoError(t, repo.Add(ctx, fact))
	return fact
}

func TestFactPageToolsUseExactScopeAndStructuredContentOnly(t *testing.T) {
	srv, repo := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
	stamp := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
	defaultCtx := rlmscope.WithScope(context.Background(), rlmscope.Default())
	alphaCtx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-alpha"))
	betaCtx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-beta"))
	defaultFact := addTransportPageFact(t, repo, defaultCtx, "default-fact", "default only", stamp)
	alphaFact := addTransportPageFact(t, repo, alphaCtx, "alpha-fact", "alpha only", stamp)
	addTransportPageFact(t, repo, betaCtx, "beta-fact", "beta must not leak", stamp)
	session := memory.NewFact("session must not leak", memory.LevelProject, "paging", "")
	session.ID = "session-fact"
	session.CreatedAt = stamp
	session.ValidFrom = stamp
	require.NoError(t, repo.AddForSession(alphaCtx, "session-one", session))

	defaultResult, err := srv.handleListDefaultFactsPage(context.Background(), callToolReq(
		"list_default_facts_page", map[string]interface{}{"level": 0, "max_fact_bytes": 1024 * 1024},
	))
	require.NoError(t, err)
	require.False(t, defaultResult.IsError)
	defaultEnvelope := decodeStructuredResult[factPageEnvelope](t, defaultResult)
	require.Equal(t, factPageMemoryScope{Version: 1, Kind: "project", TenantID: "local", ProjectID: "default"}, defaultEnvelope.MemoryScope)
	require.True(t, defaultEnvelope.Page.Done)
	require.EqualValues(t, 1, defaultEnvelope.Page.ExpectedCount)
	require.Equal(t, defaultFact.ID, decodeSingleFactFrame(t, defaultEnvelope).ID)

	projectResult, err := srv.handleListProjectFactsPage(context.Background(), sessionToolReq(
		"list_project_facts_page",
		map[string]interface{}{"level": 0, "max_fact_bytes": 1024 * 1024},
		"local", "project-alpha",
	))
	require.NoError(t, err)
	require.False(t, projectResult.IsError)
	projectEnvelope := decodeStructuredResult[factPageEnvelope](t, projectResult)
	require.Equal(t, factPageMemoryScope{Version: 1, Kind: "project", TenantID: "local", ProjectID: "project-alpha"}, projectEnvelope.MemoryScope)
	require.True(t, projectEnvelope.Page.Done)
	require.EqualValues(t, 1, projectEnvelope.Page.ExpectedCount)
	require.Equal(t, alphaFact.ID, decodeSingleFactFrame(t, projectEnvelope).ID)

	for name, req := range map[string]mcp.CallToolRequest{
		"missing meta": callToolReq("list_project_facts_page", map[string]interface{}{
			"level": 0, "max_fact_bytes": 1024 * 1024,
		}),
		"reserved default": sessionToolReq("list_project_facts_page", map[string]interface{}{
			"level": 0, "max_fact_bytes": 1024 * 1024,
		}, "local", "default"),
	} {
		t.Run(name, func(t *testing.T) {
			result, err := srv.handleListProjectFactsPage(context.Background(), req)
			require.NoError(t, err)
			require.True(t, result.IsError)
			errorEnvelope := decodeStructuredResult[factPageErrorEnvelope](t, result)
			require.Equal(t, "invalid_scope", errorEnvelope.Error.Code)
		})
	}
}

func TestFactPageToolsRejectStoredOversizeBeforePageMaterialization(t *testing.T) {
	for _, testCase := range []struct {
		name, id, content, expectedCode string
		scope                           rlmscope.Scope
		call                            func(*Server) (*mcp.CallToolResult, error)
	}{
		{
			name: "default identity", id: strings.Repeat("i", 257), content: "small",
			expectedCode: "stored_fact_identity_too_large", scope: rlmscope.Default(),
			call: func(srv *Server) (*mcp.CallToolResult, error) {
				return srv.handleListDefaultFactsPage(context.Background(), callToolReq(
					"list_default_facts_page",
					map[string]interface{}{"level": 0, "max_fact_bytes": factPageMaxFactBytes},
				))
			},
		},
		{
			name: "exact project variable row", id: "oversized-fact",
			content:      strings.Repeat("x", factPageMaxFactBytes+1),
			expectedCode: "stored_fact_too_large", scope: rlmscope.New("local", "project-alpha"),
			call: func(srv *Server) (*mcp.CallToolResult, error) {
				return srv.handleListProjectFactsPage(context.Background(), sessionToolReq(
					"list_project_facts_page",
					map[string]interface{}{"level": 0, "max_fact_bytes": factPageMaxFactBytes},
					"local", "project-alpha",
				))
			},
		},
	} {
		t.Run(testCase.name, func(t *testing.T) {
			srv, repo := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
			ctx := rlmscope.WithScope(context.Background(), testCase.scope)
			addTransportPageFact(t, repo, ctx, testCase.id, testCase.content,
				time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC))

			result, err := testCase.call(srv)
			require.NoError(t, err)
			require.True(t, result.IsError)
			envelope := decodeStructuredResult[boundedSearchStoredLimitEnvelope](t, result)
			require.Equal(t, testCase.expectedCode, envelope.Error.Code)
			switch testCase.expectedCode {
			case "stored_fact_identity_too_large":
				require.EqualValues(t, len(testCase.id), envelope.Error.StoredIdentityBytes)
				require.EqualValues(t, 256, envelope.Error.MaxStoredIdentityBytes)
			case "stored_fact_too_large":
				maxStored, valid := memory.FactPageMaxStoredVariableBytes(factPageMaxFactBytes)
				require.True(t, valid)
				require.Greater(t, envelope.Error.StoredVariableBytes, maxStored)
				require.Equal(t, maxStored, envelope.Error.MaxStoredVariableBytes)
			}
			wire, err := json.Marshal(result)
			require.NoError(t, err)
			require.Less(t, len(wire), 1<<20)
		})
	}
}

func TestFactPageToolMapsStoredRowCountToCanonicalScopeLimit(t *testing.T) {
	srv, repo := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
	store := &factPagePreflightProbeStore{
		FactStore: repo,
		err: &memory.FactPageStoredOversizeError{Measurement: memory.BoundedSearchStoredOversize{
			Kind:          memory.BoundedSearchStoredRowCountOversizeKind,
			StoredRows:    10001,
			MaxStoredRows: 10000,
		}},
	}
	srv.facts = applicationtools.NewFactService(store, nil)

	result, err := srv.handleListProjectFactsPage(context.Background(), sessionToolReq(
		"list_project_facts_page",
		map[string]interface{}{"level": 0, "max_fact_bytes": factPageMaxFactBytes},
		"local", "project-alpha",
	))
	require.NoError(t, err)
	require.True(t, result.IsError)
	envelope := decodeStructuredResult[boundedSearchStoredLimitEnvelope](t, result)
	require.Equal(t, "stored_search_scope_too_large", envelope.Error.Code)
	require.EqualValues(t, 10001, envelope.Error.StoredRows)
	require.EqualValues(t, 10000, envelope.Error.MaxStoredRows)
	require.Equal(t, 1, store.listCalls)
}

func TestFactPageToolMapsSnapshotCapacityAndExpiry(t *testing.T) {
	scope := rlmscope.New("local", "project-alpha")

	t.Run("initial capacity", func(t *testing.T) {
		srv, repo := newProjectTestServer(t, scope)
		store := &factPagePreflightProbeStore{
			FactStore: repo,
			err: &memory.FactPageSnapshotCapacityError{
				ActiveSnapshots:    3,
				MaxActiveSnapshots: 2,
				ManifestBytes:      memory.FactPageMaxManifestBytes + 1,
				MaxManifestBytes:   memory.FactPageMaxManifestBytes,
			},
		}
		srv.facts = applicationtools.NewFactService(store, nil)

		result, err := srv.handleListProjectFactsPage(context.Background(), sessionToolReq(
			"list_project_facts_page",
			map[string]interface{}{"level": 0, "max_fact_bytes": 1024 * 1024},
			"local", "project-alpha",
		))
		require.NoError(t, err)
		require.True(t, result.IsError)
		envelope := decodeStructuredResult[factPageErrorEnvelope](t, result)
		require.Equal(t, "page_capacity", envelope.Error.Code)
	})

	t.Run("missing continuation snapshot", func(t *testing.T) {
		srv, repo := newProjectTestServer(t, scope)
		store := &factPagePreflightProbeStore{FactStore: repo, err: memory.ErrFactPageExpired}
		srv.facts = applicationtools.NewFactService(store, nil)
		key := memory.FactPageKey{
			CreatedAt:     "2026-01-02T03:04:05Z",
			ID:            "fact-a",
			SnapshotID:    strings.Repeat("a", memory.FactPageSnapshotIDBytes*2),
			Sequence:      1,
			Ordinal:       0,
			ExpiresAtUnix: time.Now().Add(time.Minute).Unix(),
			MaxCalls:      2,
		}
		cursor, err := encodeFactPageCursor(factPageCursor{
			Version:       factPageProtocolVersion,
			TenantID:      "local",
			ProjectID:     "project-alpha",
			Level:         0,
			MaxFactBytes:  1024 * 1024,
			Snapshot:      1,
			ExpectedCount: 1,
			After:         &key,
		})
		require.NoError(t, err)

		result, err := srv.handleListProjectFactsPage(context.Background(), sessionToolReq(
			"list_project_facts_page",
			map[string]interface{}{
				"level": 0, "max_fact_bytes": 1024 * 1024, "cursor": cursor,
			},
			"local", "project-alpha",
		))
		require.NoError(t, err)
		require.True(t, result.IsError)
		envelope := decodeStructuredResult[factPageErrorEnvelope](t, result)
		require.Equal(t, "page_expired", envelope.Error.Code)
		require.Equal(t, 1, store.listCalls)
	})
}

func TestDefaultFactPageRejectsEveryScopeOverrideCarrier(t *testing.T) {
	srv, _ := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
	base := func() mcp.CallToolRequest {
		return callToolReq("list_default_facts_page", map[string]interface{}{
			"level": 0, "max_fact_bytes": 1024,
		})
	}
	tests := map[string]func(*mcp.CallToolRequest){
		"case-insensitive header": func(req *mcp.CallToolRequest) {
			req.Header = http.Header{"x-rlm-project-id": []string{"default"}}
		},
		"argument": func(req *mcp.CallToolRequest) {
			req.Params.Arguments.(map[string]interface{})["tenant_id"] = "local"
		},
		"nested argument": func(req *mcp.CallToolRequest) {
			req.Params.Arguments.(map[string]interface{})["rlm_scope"] = map[string]interface{}{
				"tenant_id": "local", "project_id": "default",
			}
		},
		"call params meta": func(req *mcp.CallToolRequest) {
			req.Params.Meta = &mcp.Meta{AdditionalFields: map[string]interface{}{
				"rlm_scope": map[string]interface{}{"tenant_id": "local", "project_id": "default"},
			}}
		},
		"embedded request meta": func(req *mcp.CallToolRequest) {
			req.Request.Params.Meta = &mcp.Meta{AdditionalFields: map[string]interface{}{
				"scope": map[string]interface{}{"tenant_id": "local", "project_id": "default"},
			}}
		},
	}
	for name, mutate := range tests {
		t.Run(name, func(t *testing.T) {
			req := base()
			mutate(&req)
			result, err := srv.handleListDefaultFactsPage(context.Background(), req)
			require.NoError(t, err)
			require.True(t, result.IsError)
			envelope := decodeStructuredResult[factPageErrorEnvelope](t, result)
			require.Equal(t, "scope_override_forbidden", envelope.Error.Code)
			require.NotNil(t, envelope.MemoryScope)
			require.Equal(t, "local", envelope.MemoryScope.TenantID)
			require.Equal(t, "default", envelope.MemoryScope.ProjectID)
		})
	}
}

func TestFactPageSplitsEscapedFactAndKeepsEveryWireResponseBounded(t *testing.T) {
	srv, repo := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-alpha"))
	content := strings.Repeat("<>&\x01\n", 80_000)
	fact := addTransportPageFact(t, repo, ctx, "large-fact", content,
		time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC))

	const maxFactBytes = 4 * 1024 * 1024
	var (
		cursor        string
		reconstructed []byte
		digest        string
		total         int
		frames        int
	)
	for {
		args := map[string]interface{}{"level": 0, "max_fact_bytes": maxFactBytes}
		if cursor != "" {
			args["cursor"] = cursor
		}
		result, err := srv.handleListProjectFactsPage(context.Background(), sessionToolReq(
			"list_project_facts_page", args, "local", "project-alpha",
		))
		require.NoError(t, err)
		require.False(t, result.IsError)
		wire, err := json.Marshal(result)
		require.NoError(t, err)
		require.Less(t, len(wire), 1<<20, "one MCP result must remain below one MiB")
		envelope := decodeStructuredResult[factPageEnvelope](t, result)
		require.Len(t, envelope.Page.Frames, 1)
		frame := envelope.Page.Frames[0]
		raw, err := base64.StdEncoding.DecodeString(frame.DataBase64)
		require.NoError(t, err)
		require.LessOrEqual(t, len(raw), factPageFrameRawBytes)
		require.Equal(t, len(reconstructed), frame.Offset)
		if frames == 0 {
			digest = frame.SHA256
			total = frame.TotalBytes
		} else {
			require.Equal(t, digest, frame.SHA256)
			require.Equal(t, total, frame.TotalBytes)
		}
		reconstructed = append(reconstructed, raw...)
		frames++
		if envelope.Page.Done {
			require.Empty(t, envelope.Page.NextCursor)
			break
		}
		require.NotEmpty(t, envelope.Page.NextCursor)
		cursor = envelope.Page.NextCursor
	}
	require.Greater(t, frames, 1)
	require.Len(t, reconstructed, total)
	actualDigest := sha256.Sum256(reconstructed)
	require.Equal(t, digest, hex.EncodeToString(actualDigest[:]))
	var decoded memory.Fact
	require.NoError(t, json.Unmarshal(reconstructed, &decoded))
	require.Equal(t, fact.ID, decoded.ID)
	require.Equal(t, content, decoded.Content)
}

func TestFactPageCursorIsBoundAndMutationFailsClosed(t *testing.T) {
	srv, repo := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-alpha"))
	stamp := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
	addTransportPageFact(t, repo, ctx, "fact-a", "first", stamp)
	future := addTransportPageFact(t, repo, ctx, "fact-z", "future", stamp)
	firstResult, err := srv.handleListProjectFactsPage(context.Background(), sessionToolReq(
		"list_project_facts_page", map[string]interface{}{"level": 0, "max_fact_bytes": 1024 * 1024},
		"local", "project-alpha",
	))
	require.NoError(t, err)
	require.False(t, firstResult.IsError)
	first := decodeStructuredResult[factPageEnvelope](t, firstResult)
	require.False(t, first.Page.Done)
	require.NotEmpty(t, first.Page.NextCursor)
	scope := rlmscope.New("local", "project-alpha")
	decodedCursor, err := decodeFactPageCursor(first.Page.NextCursor, scope, 0, 1024*1024)
	require.NoError(t, err)
	decodedCursor.After = nil
	decodedCursor.Fact = nil
	nonProgressCursor, err := encodeFactPageCursor(decodedCursor)
	require.NoError(t, err)

	for name, req := range map[string]mcp.CallToolRequest{
		"tampered": sessionToolReq("list_project_facts_page", map[string]interface{}{
			"level": 0, "max_fact_bytes": 1024 * 1024, "cursor": first.Page.NextCursor + "x",
		}, "local", "project-alpha"),
		"different level": sessionToolReq("list_project_facts_page", map[string]interface{}{
			"level": 1, "max_fact_bytes": 1024 * 1024, "cursor": first.Page.NextCursor,
		}, "local", "project-alpha"),
		"different bound": sessionToolReq("list_project_facts_page", map[string]interface{}{
			"level": 0, "max_fact_bytes": 1024*1024 - 1, "cursor": first.Page.NextCursor,
		}, "local", "project-alpha"),
		"different scope": sessionToolReq("list_project_facts_page", map[string]interface{}{
			"level": 0, "max_fact_bytes": 1024 * 1024, "cursor": first.Page.NextCursor,
		}, "local", "project-beta"),
		"signed nonprogress": sessionToolReq("list_project_facts_page", map[string]interface{}{
			"level": 0, "max_fact_bytes": 1024 * 1024, "cursor": nonProgressCursor,
		}, "local", "project-alpha"),
	} {
		t.Run(name, func(t *testing.T) {
			result, err := srv.handleListProjectFactsPage(context.Background(), req)
			require.NoError(t, err)
			require.True(t, result.IsError)
			envelope := decodeStructuredResult[factPageErrorEnvelope](t, result)
			require.Equal(t, "invalid_cursor", envelope.Error.Code)
		})
	}

	future.Content = "future changed"
	require.NoError(t, repo.Update(ctx, future))
	changed, err := srv.handleListProjectFactsPage(context.Background(), sessionToolReq(
		"list_project_facts_page", map[string]interface{}{
			"level": 0, "max_fact_bytes": 1024 * 1024, "cursor": first.Page.NextCursor,
		}, "local", "project-alpha",
	))
	require.NoError(t, err)
	require.True(t, changed.IsError)
	changedEnvelope := decodeStructuredResult[factPageErrorEnvelope](t, changed)
	require.Equal(t, "page_changed", changedEnvelope.Error.Code)
}

func TestFactPageCurrentMultiFrameMutationFailsClosed(t *testing.T) {
	srv, repo := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-alpha"))
	fact := addTransportPageFact(t, repo, ctx, "large-fact", strings.Repeat("x", 600*1024),
		time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC))

	firstResult, err := srv.handleListProjectFactsPage(context.Background(), sessionToolReq(
		"list_project_facts_page",
		map[string]interface{}{"level": 0, "max_fact_bytes": 4 * 1024 * 1024},
		"local", "project-alpha",
	))
	require.NoError(t, err)
	require.False(t, firstResult.IsError)
	first := decodeStructuredResult[factPageEnvelope](t, firstResult)
	require.False(t, first.Page.Done)
	require.Len(t, first.Page.Frames, 1)
	require.False(t, first.Page.Frames[0].Final)

	fact.Content = strings.Repeat("y", 600*1024)
	require.NoError(t, repo.Update(ctx, fact))
	changed, err := srv.handleListProjectFactsPage(context.Background(), sessionToolReq(
		"list_project_facts_page",
		map[string]interface{}{
			"level": 0, "max_fact_bytes": 4 * 1024 * 1024,
			"cursor": first.Page.NextCursor,
		},
		"local", "project-alpha",
	))
	require.NoError(t, err)
	require.True(t, changed.IsError)
	envelope := decodeStructuredResult[factPageErrorEnvelope](t, changed)
	require.Equal(t, "page_changed", envelope.Error.Code)
}

func TestFactPageReportsExactOversizedByteCountAndLegacyListIsUnchanged(t *testing.T) {
	srv, repo := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-alpha"))
	fact := addTransportPageFact(t, repo, ctx, "fact-a", "legacy and bounded contract",
		time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC))
	stored, err := repo.Get(ctx, fact.ID)
	require.NoError(t, err)
	serialized, err := json.Marshal(stored)
	require.NoError(t, err)

	for attempt := 0; attempt < 3; attempt++ {
		oversized, err := srv.handleListProjectFactsPage(context.Background(), sessionToolReq(
			"list_project_facts_page", map[string]interface{}{"level": 0, "max_fact_bytes": 1},
			"local", "project-alpha",
		))
		require.NoError(t, err)
		require.True(t, oversized.IsError)
		overflow := decodeStructuredResult[factPageErrorEnvelope](t, oversized)
		require.Equal(t, "fact_too_large", overflow.Error.Code,
			"terminal oversize must release its manifest instead of exhausting capacity")
		require.Equal(t, fact.ID, overflow.Error.FactID)
		require.Equal(t, len(serialized), overflow.Error.FactBytes)
		require.Equal(t, 1, overflow.Error.MaxFactBytes)
	}

	legacyFacts, err := repo.ListByLevel(ctx, memory.LevelProject)
	require.NoError(t, err)
	legacy, err := srv.handleListFacts(context.Background(), callToolReq(
		"list_facts", map[string]interface{}{"level": float64(0)},
	))
	require.NoError(t, err)
	require.False(t, legacy.IsError)
	require.Nil(t, legacy.StructuredContent)
	require.Len(t, legacy.Content, 1)
	require.Equal(t, applicationtools.ToJSON(legacyFacts), extractText(t, legacy))
}
