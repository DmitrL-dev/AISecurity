package mcpserver

import (
	"context"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"net/http"
	"sort"
	"strings"
	"testing"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/stretchr/testify/require"

	app "github.com/syntrex/gomcp/internal/application/tools"
	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
)

type forgedFactStatsPageStore struct {
	memory.FactStore
	page *memory.FactStatsPage
}

func (s *forgedFactStatsPageStore) FactStatsPage(
	context.Context,
	*memory.FactStatsPagePosition,
) (*memory.FactStatsPage, error) {
	return s.page, nil
}

func addTransportStatsFact(
	t *testing.T,
	repo interface {
		Add(context.Context, *memory.Fact) error
	},
	ctx context.Context,
	id, domain string,
) *memory.Fact {
	t.Helper()
	fact := memory.NewFact("bounded stats "+id, memory.LevelProject, domain, "")
	fact.ID = id
	fact.Origin = memory.OriginExternal
	require.NoError(t, repo.Add(ctx, fact))
	return fact
}

func TestFactStatsPageV2PacksHugeDomainsWithinHardCallAndResponseBounds(t *testing.T) {
	srv, repo := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-alpha"))

	wantDomains := make([]string, 0, 17)
	for index := 0; index < 17; index++ {
		domain := fmt.Sprintf("%02d-", index) + strings.Repeat("<>&\x01\n", 43_000)
		wantDomains = append(wantDomains, domain)
		addTransportStatsFact(t, repo, ctx, fmt.Sprintf("fact-%02d", index), domain)
	}
	session := memory.NewFact("session excluded", memory.LevelProject, "session-private", "")
	session.ID = "session-fact"
	session.Origin = memory.OriginUser
	require.NoError(t, repo.AddForSession(ctx, "session-one", session))

	var (
		cursor           string
		gotDomains       []string
		current          []byte
		currentDigest    string
		currentTotal     int
		expectedSnapshot string
		expectedOrdinal  int64
		expectedSegment  int64
		calls            int
	)
	for {
		args := map[string]interface{}{}
		if cursor != "" {
			args["cursor"] = cursor
		}
		result, err := srv.handleProjectFactStatsPage(context.Background(), sessionToolReq(
			"project_fact_stats_page", args, "local", "project-alpha",
		))
		require.NoError(t, err)
		require.False(t, result.IsError, "result: %#v", result.StructuredContent)
		wire, err := json.Marshal(result)
		require.NoError(t, err)
		require.Less(t, len(wire), 1<<20, "one MCP stats result must remain below one MiB")

		envelope := decodeStructuredResult[factStatsPageEnvelope](t, result)
		require.Equal(t, factStatsPageProtocolVersion, envelope.Page.Version)
		require.Equal(t, "base64-json-segments", envelope.Page.Encoding)
		require.Equal(t, memory.FactStatsPageFrameRawBytes, envelope.Page.FrameRawLimitBytes)
		require.Equal(t, memory.FactStatsPageMaxSegmentsPerPage, envelope.Page.MaxSegmentsPerPage)
		require.Equal(t, memory.FactStatsPageMaxCalls, envelope.Page.MaxCalls)
		require.Equal(t, calls, envelope.Page.CallIndex)
		require.EqualValues(t, 17, envelope.Page.ExpectedCount)
		require.NotEmpty(t, envelope.Page.DomainFrames)
		if calls == 0 {
			require.NotNil(t, envelope.Page.FixedStats)
			require.Equal(t, 17, envelope.Page.FixedStats.TotalFacts)
			require.True(t, validFactStatsWireSnapshotID(envelope.Page.SnapshotID))
			expectedSnapshot = envelope.Page.SnapshotID
			require.EqualValues(t, 17, envelope.Page.ExpectedRows)
		} else {
			require.Nil(t, envelope.Page.FixedStats)
			require.Equal(t, expectedSnapshot, envelope.Page.SnapshotID)
		}

		pageRaw := 0
		for _, frame := range envelope.Page.DomainFrames {
			frameJSON, err := json.Marshal(frame)
			require.NoError(t, err)
			var frameObject map[string]interface{}
			require.NoError(t, json.Unmarshal(frameJSON, &frameObject))
			require.Contains(t, frameObject, "segment_final",
				"v2 must distinguish a complete stored segment from a split wire frame")
			require.Equal(t, expectedSegment, frame.SegmentIndex)
			require.Equal(t, expectedOrdinal, frame.Ordinal)
			raw, err := base64.StdEncoding.DecodeString(frame.DataBase64)
			require.NoError(t, err)
			require.NotEmpty(t, raw)
			pageRaw += len(raw)
			require.Equal(t, len(current), frame.Offset)
			if len(current) == 0 {
				currentDigest = frame.SHA256
				currentTotal = frame.TotalBytes
			} else {
				require.Equal(t, currentDigest, frame.SHA256)
				require.Equal(t, currentTotal, frame.TotalBytes)
			}
			current = append(current, raw...)
			if frame.SegmentFinal {
				expectedSegment++
			}
			if frame.Final {
				require.Len(t, current, currentTotal)
				digest := sha256.Sum256(current)
				require.Equal(t, currentDigest, hex.EncodeToString(digest[:]))
				var entry memory.FactStatsDomain
				require.NoError(t, json.Unmarshal(current, &entry))
				require.Equal(t, 1, entry.Count)
				gotDomains = append(gotDomains, entry.Domain)
				current = nil
				currentDigest = ""
				currentTotal = 0
				expectedOrdinal++
			}
		}
		require.LessOrEqual(t, pageRaw, memory.FactStatsPageFrameRawBytes)
		calls++
		if envelope.Page.Done {
			require.Empty(t, envelope.Page.NextCursor)
			break
		}
		require.NotEmpty(t, envelope.Page.NextCursor)
		require.LessOrEqual(t, len(envelope.Page.NextCursor), factPageMaxCursorBytes)
		next, err := decodeFactStatsPageCursor(envelope.Page.NextCursor,
			rlmscope.New("local", "project-alpha"))
		require.NoError(t, err)
		require.Equal(t, expectedSegment, next.SegmentIndex)
		cursor = envelope.Page.NextCursor
	}

	require.LessOrEqual(t, calls, memory.FactStatsPageMaxCalls)
	require.Greater(t, calls, 1, "hostile escaping must exercise snapshot segmentation")
	require.EqualValues(t, 17, expectedOrdinal)
	sort.Strings(wantDomains)
	require.Equal(t, wantDomains, gotDomains)
}

func TestFactStatsPageScopeCursorAndSnapshotFailuresAreFailClosed(t *testing.T) {
	srv, repo := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
	defaultCtx := rlmscope.WithScope(context.Background(), rlmscope.Default())
	alphaCtx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-alpha"))
	addTransportStatsFact(t, repo, defaultCtx, "default-fact", "default-domain")
	addTransportStatsFact(t, repo, alphaCtx, "alpha-a", "alpha")
	addTransportStatsFact(t, repo, alphaCtx, "alpha-b", "beta-"+strings.Repeat("b", 2*memory.FactStatsPageFrameRawBytes))
	addTransportStatsFact(t, repo, alphaCtx, "alpha-c", "gamma")

	defaultResult, err := srv.handleDefaultFactStatsPage(context.Background(), callToolReq(
		"default_fact_stats_page", map[string]interface{}{},
	))
	require.NoError(t, err)
	require.False(t, defaultResult.IsError)
	defaultEnvelope := decodeStructuredResult[factStatsPageEnvelope](t, defaultResult)
	require.Equal(t, "default", defaultEnvelope.MemoryScope.ProjectID)
	require.Equal(t, 1, defaultEnvelope.Page.FixedStats.TotalFacts)

	for name, mutate := range map[string]func(*mcp.CallToolRequest){
		"header": func(req *mcp.CallToolRequest) {
			req.Header = http.Header{"x-rlm-project-id": []string{"default"}}
		},
		"argument": func(req *mcp.CallToolRequest) {
			req.Params.Arguments.(map[string]interface{})["tenant_id"] = "local"
		},
		"meta": func(req *mcp.CallToolRequest) {
			req.Params.Meta = &mcp.Meta{AdditionalFields: map[string]interface{}{
				"rlm_scope": map[string]interface{}{"tenant_id": "local", "project_id": "default"},
			}}
		},
	} {
		t.Run("default override "+name, func(t *testing.T) {
			req := callToolReq("default_fact_stats_page", map[string]interface{}{})
			mutate(&req)
			result, err := srv.handleDefaultFactStatsPage(context.Background(), req)
			require.NoError(t, err)
			require.True(t, result.IsError)
			require.Equal(t, "scope_override_forbidden",
				decodeStructuredResult[factPageErrorEnvelope](t, result).Error.Code)
		})
	}

	for name, req := range map[string]mcp.CallToolRequest{
		"missing meta": callToolReq("project_fact_stats_page", map[string]interface{}{}),
		"reserved default": sessionToolReq(
			"project_fact_stats_page", map[string]interface{}{}, "local", "default"),
		"case folded default": sessionToolReq(
			"project_fact_stats_page", map[string]interface{}{}, "local", "DEFAULT"),
	} {
		t.Run(name, func(t *testing.T) {
			result, err := srv.handleProjectFactStatsPage(context.Background(), req)
			require.NoError(t, err)
			require.True(t, result.IsError)
			require.Equal(t, "invalid_scope",
				decodeStructuredResult[factPageErrorEnvelope](t, result).Error.Code)
		})
	}

	firstResult, err := srv.handleProjectFactStatsPage(context.Background(), sessionToolReq(
		"project_fact_stats_page", map[string]interface{}{}, "local", "project-alpha",
	))
	require.NoError(t, err)
	require.False(t, firstResult.IsError)
	first := decodeStructuredResult[factStatsPageEnvelope](t, firstResult)
	require.NotEmpty(t, first.Page.NextCursor)
	require.Equal(t, 0, first.Page.CallIndex)

	for name, req := range map[string]mcp.CallToolRequest{
		"tampered": sessionToolReq("project_fact_stats_page", map[string]interface{}{
			"cursor": first.Page.NextCursor + "x",
		}, "local", "project-alpha"),
		"different scope": sessionToolReq("project_fact_stats_page", map[string]interface{}{
			"cursor": first.Page.NextCursor,
		}, "local", "project-beta"),
		"overlong": sessionToolReq("project_fact_stats_page", map[string]interface{}{
			"cursor": strings.Repeat("x", factPageMaxCursorBytes+1),
		}, "local", "project-alpha"),
	} {
		t.Run("invalid cursor "+name, func(t *testing.T) {
			result, err := srv.handleProjectFactStatsPage(context.Background(), req)
			require.NoError(t, err)
			require.True(t, result.IsError)
			require.Equal(t, "invalid_cursor",
				decodeStructuredResult[factPageErrorEnvelope](t, result).Error.Code)
		})
	}

	decoded, err := decodeFactStatsPageCursor(first.Page.NextCursor, rlmscope.New("local", "project-alpha"))
	require.NoError(t, err)
	decoded.CallIndex = 0
	nonProgress, err := encodeFactStatsPageCursor(decoded)
	require.NoError(t, err)
	nonProgressResult, err := srv.handleProjectFactStatsPage(context.Background(), sessionToolReq(
		"project_fact_stats_page", map[string]interface{}{"cursor": nonProgress}, "local", "project-alpha",
	))
	require.NoError(t, err)
	require.True(t, nonProgressResult.IsError)
	require.Equal(t, "invalid_cursor",
		decodeStructuredResult[factPageErrorEnvelope](t, nonProgressResult).Error.Code)

	// Later source inserts are invisible because continuation reads only the
	// immutable materialized snapshot.
	addTransportStatsFact(t, repo, alphaCtx, "later-insert", "000-later")
	secondResult, err := srv.handleProjectFactStatsPage(context.Background(), sessionToolReq(
		"project_fact_stats_page", map[string]interface{}{"cursor": first.Page.NextCursor}, "local", "project-alpha",
	))
	require.NoError(t, err)
	require.False(t, secondResult.IsError, "result: %#v", secondResult.StructuredContent)
	second := decodeStructuredResult[factStatsPageEnvelope](t, secondResult)
	require.Equal(t, first.Page.SnapshotID, second.Page.SnapshotID)
	require.NotEmpty(t, second.Page.NextCursor)

	// A concurrent initial request must not replace this scope's active snapshot.
	// The original signed cursor remains usable by its in-flight walk.
	replacement, err := srv.handleProjectFactStatsPage(context.Background(), sessionToolReq(
		"project_fact_stats_page", map[string]interface{}{}, "local", "project-alpha",
	))
	require.NoError(t, err)
	require.True(t, replacement.IsError)
	require.Equal(t, "stats_snapshot_busy",
		decodeStructuredResult[factPageErrorEnvelope](t, replacement).Error.Code)
	changedResult, err := srv.handleProjectFactStatsPage(context.Background(), sessionToolReq(
		"project_fact_stats_page", map[string]interface{}{"cursor": second.Page.NextCursor}, "local", "project-alpha",
	))
	require.NoError(t, err)
	require.False(t, changedResult.IsError)
}

func TestFactStatsPageCursorRejectsUnboundedPinsBeforeRepositoryRead(t *testing.T) {
	srv, _ := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
	base := factStatsPageCursor{
		Version:          factStatsPageProtocolVersion,
		TenantID:         "local",
		ProjectID:        "project-alpha",
		SnapshotID:       strings.Repeat("a", memory.FactStatsPageSnapshotIDBytes*2),
		ExpectedRows:     1,
		ExpectedCount:    1,
		ExpectedSegments: 1,
		SerializedBytes:  1,
		SegmentIndex:     0,
		CallIndex:        1,
	}
	for name, mutate := range map[string]func(*factStatsPageCursor){
		"serialized bytes": func(cursor *factStatsPageCursor) {
			cursor.SerializedBytes = memory.FactStatsPageMaxSerializedDomainScopeBytes + 1
		},
		"domain count": func(cursor *factStatsPageCursor) {
			cursor.ExpectedRows = memory.FactStatsPageMaxDomains + 1
			cursor.ExpectedCount = memory.FactStatsPageMaxDomains + 1
			cursor.ExpectedSegments = memory.FactStatsPageMaxDomains + 1
		},
		"call count": func(cursor *factStatsPageCursor) {
			cursor.CallIndex = memory.FactStatsPageMaxCalls
		},
	} {
		t.Run(name, func(t *testing.T) {
			cursor := base
			mutate(&cursor)
			token, err := encodeFactStatsPageCursor(cursor)
			require.NoError(t, err)
			result, err := srv.handleProjectFactStatsPage(context.Background(), sessionToolReq(
				"project_fact_stats_page", map[string]interface{}{"cursor": token},
				"local", "project-alpha",
			))
			require.NoError(t, err)
			require.True(t, result.IsError)
			require.Equal(t, "invalid_cursor",
				decodeStructuredResult[factPageErrorEnvelope](t, result).Error.Code)
		})
	}

	rowLimit := boundedSearchStoredOversizedResult(rlmscope.New("local", "project-alpha"),
		&memory.BoundedSearchStoredOversize{
			Kind:          memory.BoundedSearchStoredRowCountOversizeKind,
			StoredRows:    10_001,
			MaxStoredRows: memory.FactStatsPageMaxDomains,
		})
	rowEnvelope := decodeStructuredResult[boundedSearchStoredLimitEnvelope](t, rowLimit)
	require.Equal(t, "stored_search_scope_too_large", rowEnvelope.Error.Code)
	require.EqualValues(t, 10_001, rowEnvelope.Error.StoredRows)
}

func TestFactStatsPageRejectsNonExactBackendContinuationPosition(t *testing.T) {
	encoded, err := json.Marshal(memory.FactStatsDomain{Domain: "alpha", Count: 1})
	require.NoError(t, err)
	digest := sha256.Sum256(encoded)
	for name, next := range map[string]struct {
		index int64
		done  bool
	}{
		"repeated segment": {index: 0, done: false},
		"skipped segment":  {index: 2, done: true},
	} {
		t.Run(name, func(t *testing.T) {
			srv, repo := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
			srv.facts = app.NewFactService(&forgedFactStatsPageStore{
				FactStore: repo,
				page: &memory.FactStatsPage{
					SnapshotID:       strings.Repeat("a", memory.FactStatsPageSnapshotIDBytes*2),
					ExpectedRows:     1,
					ExpectedDomains:  1,
					ExpectedSegments: 2,
					SerializedBytes:  int64(len(encoded)),
					Fixed: &memory.FixedFactStoreStats{
						TotalFacts: 1,
						LiveFacts:  1,
						ByLevel:    map[memory.HierLevel]int{memory.LevelProject: 1},
						ByOrigin:   map[memory.Origin]int{memory.OriginExternal: 1},
					},
					Segments: []memory.FactStatsDomainSegment{{
						SegmentIndex: 0,
						Ordinal:      0,
						SHA256:       hex.EncodeToString(digest[:]),
						TotalBytes:   len(encoded),
						StoredBytes:  len(encoded),
						Data:         encoded,
						SegmentFinal: true,
						Final:        true,
					}},
					NextSegmentIndex: next.index,
					Done:             next.done,
				},
			}, nil)
			result, err := srv.handleProjectFactStatsPage(context.Background(), sessionToolReq(
				"project_fact_stats_page", map[string]interface{}{}, "local", "project-alpha",
			))
			require.NoError(t, err)
			require.True(t, result.IsError)
			require.Equal(t, "page_scope_mismatch",
				decodeStructuredResult[factPageErrorEnvelope](t, result).Error.Code)
		})
	}
}

func TestFactStatsPageStoredAndSerializedOversizeReturnTypedBoundedErrors(t *testing.T) {
	t.Run("stored domain", func(t *testing.T) {
		srv, repo := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
		ctx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-alpha"))
		const canary = "stored-domain-canary"
		oversizedDomain := strings.Repeat(canary,
			int(memory.FactStatsPageStoredDomainHardMaxBytes)/len(canary)+1)
		addTransportStatsFact(t, repo, ctx, "oversized-domain", oversizedDomain)

		result, err := srv.handleProjectFactStatsPage(context.Background(), sessionToolReq(
			"project_fact_stats_page", map[string]interface{}{}, "local", "project-alpha",
		))
		require.NoError(t, err)
		require.True(t, result.IsError)
		require.Empty(t, result.Content)
		envelope := decodeStructuredResult[boundedSearchStoredLimitEnvelope](t, result)
		require.Equal(t, "stored_fact_too_large", envelope.Error.Code)
		require.Greater(t, envelope.Error.StoredVariableBytes, memory.FactStatsPageStoredDomainHardMaxBytes)
		wire, err := json.Marshal(result)
		require.NoError(t, err)
		require.Less(t, len(wire), 4096)
		require.NotContains(t, string(wire), canary)
	})

	t.Run("serialized scope", func(t *testing.T) {
		srv, repo := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
		ctx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-alpha"))
		const canary = "serialized-scope-canary"
		for index := 0; index < 6; index++ {
			domain := fmt.Sprintf("%d-%s", index, canary) + strings.Repeat("<", 1<<20)
			addTransportStatsFact(t, repo, ctx, fmt.Sprintf("escape-%d", index), domain)
		}
		result, err := srv.handleProjectFactStatsPage(context.Background(), sessionToolReq(
			"project_fact_stats_page", map[string]interface{}{}, "local", "project-alpha",
		))
		require.NoError(t, err)
		require.True(t, result.IsError)
		require.Empty(t, result.Content)
		envelope := decodeStructuredResult[factStatsResultLimitEnvelope](t, result)
		require.Equal(t, "stats_result_too_large", envelope.Error.Code)
		require.Greater(t, envelope.Error.SerializedBytes, memory.FactStatsPageMaxSerializedDomainScopeBytes)
		require.Equal(t, memory.FactStatsPageMaxSerializedDomainScopeBytes,
			envelope.Error.MaxSerializedBytes)
		wire, err := json.Marshal(result)
		require.NoError(t, err)
		require.Less(t, len(wire), 4096)
		require.NotContains(t, string(wire), canary)
	})
}

func TestLegacyFactStatsTextGoldensAreUnchanged(t *testing.T) {
	const emptyStatsGolden = `{
  "total_facts": 0,
  "live_facts": 0,
  "archived_count": 0,
  "by_level": {},
  "by_domain": {},
  "by_origin": {},
  "stale_count": 0,
  "with_embeddings": 0,
  "gene_count": 0,
  "cold_count": 0
}`
	defaultServer := newTestServer(t)
	beforeDefault, err := defaultServer.handleFactStats(context.Background(), callToolReq("fact_stats", nil))
	require.NoError(t, err)
	require.Equal(t, emptyStatsGolden, extractText(t, beforeDefault))
	boundedDefault, err := defaultServer.handleDefaultFactStatsPage(context.Background(), callToolReq(
		"default_fact_stats_page", map[string]interface{}{},
	))
	require.NoError(t, err)
	require.False(t, boundedDefault.IsError)
	require.True(t, decodeStructuredResult[factStatsPageEnvelope](t, boundedDefault).Page.Done)
	afterDefault, err := defaultServer.handleFactStats(context.Background(), callToolReq("fact_stats", nil))
	require.NoError(t, err)
	require.Equal(t, emptyStatsGolden, extractText(t, afterDefault))

	const emptyProjectStatsGolden = `{
  "memory_scope": {
    "kind": "project",
    "project_id": "project-alpha",
    "tenant_id": "local",
    "version": 1
  },
  "stats": {
    "total_facts": 0,
    "live_facts": 0,
    "archived_count": 0,
    "by_level": {},
    "by_domain": {},
    "by_origin": {},
    "stale_count": 0,
    "with_embeddings": 0,
    "gene_count": 0,
    "cold_count": 0
  }
}`
	projectServer, _ := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
	projectRequest := sessionToolReq("project_fact_stats", nil, "local", "project-alpha")
	beforeProject, err := projectServer.handleProjectFactStats(context.Background(), projectRequest)
	require.NoError(t, err)
	require.Equal(t, emptyProjectStatsGolden, extractText(t, beforeProject))
	boundedProject, err := projectServer.handleProjectFactStatsPage(context.Background(), sessionToolReq(
		"project_fact_stats_page", map[string]interface{}{}, "local", "project-alpha",
	))
	require.NoError(t, err)
	require.False(t, boundedProject.IsError)
	require.True(t, decodeStructuredResult[factStatsPageEnvelope](t, boundedProject).Page.Done)
	afterProject, err := projectServer.handleProjectFactStats(context.Background(), projectRequest)
	require.NoError(t, err)
	require.Equal(t, emptyProjectStatsGolden, extractText(t, afterProject))
}

func TestBoundedStatsToolSchemasAreAdditiveAndExact(t *testing.T) {
	srv, _ := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
	if srv.mcp.GetTool("default_fact_stats_page") == nil {
		srv.registerBoundedStatsTools()
	}
	for _, name := range []string{"default_fact_stats_page", "project_fact_stats_page"} {
		tool := srv.mcp.GetTool(name)
		require.NotNil(t, tool, name)
		require.NotNil(t, tool.Handler, name)
		require.Empty(t, tool.Tool.InputSchema.Required, name)
		require.ElementsMatch(t, []string{"cursor"}, mapKeys(tool.Tool.InputSchema.Properties), name)
		require.True(t, memory.IsExactProtocolTool(name), name)
	}
	for _, legacy := range []string{"fact_stats", "project_fact_stats"} {
		require.NotNil(t, srv.mcp.GetTool(legacy), legacy)
	}
}
