package mcpserver

import (
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/stretchr/testify/require"

	applicationtools "github.com/syntrex/gomcp/internal/application/tools"
	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
	"github.com/syntrex/gomcp/internal/domain/synapse"
	"github.com/syntrex/gomcp/internal/domain/vectorstore"
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"
)

type collectedBoundedSearch struct {
	order          []string
	serialized     map[string][]byte
	pages          int
	maxCursorBytes int
}

type boundedSearchPreflightProbeStore struct {
	memory.FactStore
	snapshot       memory.ExactBoundedSearchStore
	oversize       *memory.BoundedSearchStoredOversize
	oversizeOnCall int
	snapshotCalls  int
	callbackCalls  int
	factIDCalls    [][]string
}

type boundedSearchBlockingStore struct {
	memory.FactStore
	entered chan struct{}
	release chan struct{}
	once    sync.Once
}

func (s *boundedSearchBlockingStore) WithBoundedSearchSnapshot(
	ctx context.Context,
	_ []string,
	_ func(memory.BoundedSearchSnapshot) ([]*memory.Fact, error),
) ([]*memory.Fact, *memory.BoundedSearchStoredOversize, error) {
	select {
	case s.entered <- struct{}{}:
	case <-ctx.Done():
		return nil, nil, ctx.Err()
	}
	select {
	case <-s.release:
		return nil, nil, nil
	case <-ctx.Done():
		return nil, nil, ctx.Err()
	}
}

func (s *boundedSearchBlockingStore) unblock() {
	s.once.Do(func() { close(s.release) })
}

func (s *boundedSearchPreflightProbeStore) WithBoundedSearchSnapshot(
	ctx context.Context,
	factIDs []string,
	run func(memory.BoundedSearchSnapshot) ([]*memory.Fact, error),
) ([]*memory.Fact, *memory.BoundedSearchStoredOversize, error) {
	s.snapshotCalls++
	s.factIDCalls = append(s.factIDCalls, append([]string(nil), factIDs...))
	if s.oversize != nil && s.snapshotCalls == s.oversizeOnCall {
		return nil, s.oversize, nil
	}
	if s.snapshot == nil {
		return nil, nil, fmt.Errorf("unexpected bounded snapshot callback")
	}
	return s.snapshot.WithBoundedSearchSnapshot(ctx, factIDs, func(snapshot memory.BoundedSearchSnapshot) ([]*memory.Fact, error) {
		s.callbackCalls++
		return run(snapshot)
	})
}

func TestBoundedSearchContinuationLoadsOnlyTheCurrentFrozenFact(t *testing.T) {
	srv, repo := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-alpha"))
	stamp := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
	for _, id := range []string{"fact-a", "fact-b", "fact-c"} {
		addBoundedSearchFact(t, repo, ctx, id, "needle "+id, stamp)
	}
	store := &boundedSearchPreflightProbeStore{FactStore: repo, snapshot: repo}
	srv.facts = applicationtools.NewFactService(store, nil)
	first := firstProjectBoundedSearchPage(t, srv, "project-alpha", "needle", 20, 1024*1024)
	require.False(t, first.Page.Done)

	result, err := srv.handleSearchProjectFactsPage(context.Background(), sessionToolReq(
		"search_project_facts_page", map[string]interface{}{
			"query": "needle", "mode": "keyword", "limit": float64(20),
			"max_fact_bytes": float64(1024 * 1024), "cursor": first.Page.NextCursor,
		}, "local", "project-alpha",
	))
	require.NoError(t, err)
	require.False(t, result.IsError)
	require.Len(t, store.factIDCalls, 2)
	require.Nil(t, store.factIDCalls[0], "initial preflight must cover the exact scope")
	require.Equal(t, []string{"fact-b"}, store.factIDCalls[1],
		"continuation must read only its current frozen row")
}

func TestBoundedSearchAdmissionBoundsConcurrentInitialMaterialization(t *testing.T) {
	srv, repo := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
	store := &boundedSearchBlockingStore{
		FactStore: repo,
		entered:   make(chan struct{}, 3),
		release:   make(chan struct{}),
	}
	t.Cleanup(store.unblock)
	srv.facts = applicationtools.NewFactService(store, nil)
	type outcome struct {
		request int
		result  *mcp.CallToolResult
		err     error
	}
	results := make(chan outcome, 3)
	invoke := func(request int) {
		result, err := srv.handleSearchProjectFactsPage(context.Background(), sessionToolReq(
			"search_project_facts_page", map[string]interface{}{
				"query": "needle", "mode": "keyword", "limit": float64(100),
				"max_fact_bytes": float64(factPageMaxFactBytes),
			}, "local", "project-alpha",
		))
		results <- outcome{request: request, result: result, err: err}
	}
	go invoke(1)
	go invoke(2)
	for index := 0; index < 2; index++ {
		select {
		case <-store.entered:
		case <-time.After(2 * time.Second):
			t.Fatal("two admitted searches did not reach the bounded store")
		}
	}
	go invoke(3)

	select {
	case <-store.entered:
		store.unblock()
		for index := 0; index < 3; index++ {
			<-results
		}
		t.Fatal("third initial materialization reached the store without admission")
	case got := <-results:
		require.Equal(t, 3, got.request)
		require.NoError(t, got.err)
		requireBoundedSearchErrorCode(t, got.result, "search_capacity")
	case <-time.After(2 * time.Second):
		store.unblock()
		t.Fatal("third initial search neither rejected nor reached the store")
	}
	store.unblock()
	for index := 0; index < 2; index++ {
		got := <-results
		require.NoError(t, got.err)
		require.False(t, got.result.IsError)
	}
}

func TestBoundedSearchCapacityRejectsBeforeStoredSnapshotAndMarshal(t *testing.T) {
	dummyOwner := &Server{}
	results := []boundedSearchCursorFact{{
		FactID: "capacity-fact", SHA256: strings.Repeat("a", 64), SerializedSize: 1,
	}}
	created := make([]*boundedSearchSnapshot, 0, boundedSearchMaxActiveSnapshots)
	for {
		snapshot, err := processBoundedSearchSnapshots.register(
			dummyOwner, rlmscope.New("capacity", "project"), strings.Repeat("b", 64),
			"keyword", 100, factPageMaxFactBytes, results,
		)
		if err != nil {
			var capacity *boundedSearchSnapshotCapacityError
			require.ErrorAs(t, err, &capacity)
			break
		}
		created = append(created, snapshot)
	}
	t.Cleanup(func() {
		for _, snapshot := range created {
			processBoundedSearchSnapshots.close(snapshot)
		}
	})

	srv, repo := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-alpha"))
	addBoundedSearchFact(t, repo, ctx, "fact-a", "needle payload", time.Now().UTC())
	store := &boundedSearchPreflightProbeStore{FactStore: repo, snapshot: repo}
	srv.facts = applicationtools.NewFactService(store, nil)
	result, err := srv.handleSearchProjectFactsPage(context.Background(), sessionToolReq(
		"search_project_facts_page", map[string]interface{}{
			"query": "needle", "mode": "keyword", "limit": float64(100),
			"max_fact_bytes": float64(factPageMaxFactBytes),
		}, "local", "project-alpha",
	))
	require.NoError(t, err)
	requireBoundedSearchErrorCode(t, result, "search_capacity")
	require.Zero(t, store.snapshotCalls,
		"capacity must be reserved before SearchFactsBoundedSnapshot materializes rows")
}

func TestBoundedSearchContinuationMaterializesLargeFactOnlyOnce(t *testing.T) {
	srv, repo := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-alpha"))
	content := "needle " + strings.Repeat("x", factPageFrameRawBytes*2+32*1024)
	addBoundedSearchFact(t, repo, ctx, "fact-large", content, time.Now().UTC())
	store := &boundedSearchPreflightProbeStore{FactStore: repo, snapshot: repo}
	srv.facts = applicationtools.NewFactService(store, nil)
	page := firstProjectBoundedSearchPage(t, srv, "project-alpha", "needle", 20, 4*1024*1024)
	require.False(t, page.Page.Done)
	for continuation := 0; continuation < 2; continuation++ {
		result, err := srv.handleSearchProjectFactsPage(context.Background(), sessionToolReq(
			"search_project_facts_page", map[string]interface{}{
				"query": "needle", "mode": "keyword", "limit": float64(20),
				"max_fact_bytes": float64(4 * 1024 * 1024), "cursor": page.Page.NextCursor,
			}, "local", "project-alpha",
		))
		require.NoError(t, err)
		require.False(t, result.IsError)
		page = decodeStructuredResult[boundedSearchEnvelope](t, result)
	}
	require.True(t, page.Page.Done)
	require.Equal(t, 1, store.snapshotCalls,
		"the authoritative frozen payload must be reused across every frame")
}

func TestBoundedSearchContinuationRejectsAReplayedCursor(t *testing.T) {
	srv, repo := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-alpha"))
	stamp := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
	for _, id := range []string{"fact-a", "fact-b", "fact-c"} {
		addBoundedSearchFact(t, repo, ctx, id, "needle "+id, stamp)
	}
	first := firstProjectBoundedSearchPage(t, srv, "project-alpha", "needle", 20, 1024*1024)
	request := sessionToolReq(
		"search_project_facts_page", map[string]interface{}{
			"query": "needle", "mode": "keyword", "limit": float64(20),
			"max_fact_bytes": float64(1024 * 1024), "cursor": first.Page.NextCursor,
		}, "local", "project-alpha",
	)

	firstUse, err := srv.handleSearchProjectFactsPage(context.Background(), request)
	require.NoError(t, err)
	require.False(t, firstUse.IsError)
	replay, err := srv.handleSearchProjectFactsPage(context.Background(), request)
	require.NoError(t, err)
	requireBoundedSearchErrorCode(t, replay, "invalid_cursor")
}

func TestBoundedSearchContinuationRejectsAnotherServerInTheSameProcess(t *testing.T) {
	issuer, repo := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-alpha"))
	stamp := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
	addBoundedSearchFact(t, repo, ctx, "fact-a", "needle first", stamp)
	addBoundedSearchFact(t, repo, ctx, "fact-b", "needle second", stamp)
	first := firstProjectBoundedSearchPage(t, issuer, "project-alpha", "needle", 20, 1024*1024)

	foreign, _ := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
	result, err := foreign.handleSearchProjectFactsPage(context.Background(), sessionToolReq(
		"search_project_facts_page", map[string]interface{}{
			"query": "needle", "mode": "keyword", "limit": float64(20),
			"max_fact_bytes": float64(1024 * 1024), "cursor": first.Page.NextCursor,
		}, "local", "project-alpha",
	))
	require.NoError(t, err)
	requireBoundedSearchErrorCode(t, result, "invalid_cursor")
}

func TestBoundedSearchContinuationRejectsExpiredSnapshotBeforeBackendRead(t *testing.T) {
	now := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
	processBoundedSearchSnapshots.mu.Lock()
	previousClock := processBoundedSearchSnapshots.now
	processBoundedSearchSnapshots.now = func() time.Time { return now }
	processBoundedSearchSnapshots.mu.Unlock()
	t.Cleanup(func() {
		processBoundedSearchSnapshots.mu.Lock()
		processBoundedSearchSnapshots.now = previousClock
		processBoundedSearchSnapshots.mu.Unlock()
		processBoundedSearchSnapshots.cleanupExpired(time.Now().Add(24 * time.Hour).Unix())
	})

	srv, repo := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-alpha"))
	addBoundedSearchFact(t, repo, ctx, "fact-a", "needle first", now)
	addBoundedSearchFact(t, repo, ctx, "fact-b", "needle second", now)
	store := &boundedSearchPreflightProbeStore{FactStore: repo, snapshot: repo}
	srv.facts = applicationtools.NewFactService(store, nil)
	first := firstProjectBoundedSearchPage(t, srv, "project-alpha", "needle", 20, 1024*1024)
	require.False(t, first.Page.Done)
	now = now.Add(time.Duration(boundedSearchSnapshotTTLSeconds+1) * time.Second)

	result, err := srv.handleSearchProjectFactsPage(context.Background(), sessionToolReq(
		"search_project_facts_page", map[string]interface{}{
			"query": "needle", "mode": "keyword", "limit": float64(20),
			"max_fact_bytes": float64(1024 * 1024), "cursor": first.Page.NextCursor,
		}, "local", "project-alpha",
	))
	require.NoError(t, err)
	requireBoundedSearchErrorCode(t, result, "page_expired")
	require.Equal(t, 1, store.snapshotCalls, "expired cursors must not reach SQLite")
}

func TestBoundedSearchContinuationEnforcesSnapshotWorkBudgetBeforeBackendRead(t *testing.T) {
	for name, exhaust := range map[string]func(*boundedSearchSnapshot){
		"calls": func(snapshot *boundedSearchSnapshot) {
			snapshot.maxCalls = snapshot.callsUsed
		},
		"bytes": func(snapshot *boundedSearchSnapshot) {
			snapshot.maxBytes = snapshot.bytesEmitted
		},
	} {
		t.Run(name, func(t *testing.T) {
			srv, repo := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
			ctx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-alpha"))
			stamp := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
			addBoundedSearchFact(t, repo, ctx, "fact-a", "needle first", stamp)
			addBoundedSearchFact(t, repo, ctx, "fact-b", "needle second", stamp)
			store := &boundedSearchPreflightProbeStore{FactStore: repo, snapshot: repo}
			srv.facts = applicationtools.NewFactService(store, nil)
			first := firstProjectBoundedSearchPage(t, srv, "project-alpha", "needle", 20, 1024*1024)

			queryDigest := sha256.Sum256([]byte("needle"))
			cursor, err := decodeBoundedSearchCursor(
				first.Page.NextCursor, rlmscope.New("local", "project-alpha"),
				hex.EncodeToString(queryDigest[:]), "keyword", 20, 1024*1024,
			)
			require.NoError(t, err)
			processBoundedSearchSnapshots.mu.Lock()
			snapshot := processBoundedSearchSnapshots.snapshots[cursor.SnapshotID]
			require.NotNil(t, snapshot)
			processBoundedSearchSnapshots.mu.Unlock()
			snapshot.mu.Lock()
			exhaust(snapshot)
			snapshot.mu.Unlock()

			result, err := srv.handleSearchProjectFactsPage(context.Background(), sessionToolReq(
				"search_project_facts_page", map[string]interface{}{
					"query": "needle", "mode": "keyword", "limit": float64(20),
					"max_fact_bytes": float64(1024 * 1024), "cursor": first.Page.NextCursor,
				}, "local", "project-alpha",
			))
			require.NoError(t, err)
			requireBoundedSearchErrorCode(t, result, "search_work_limit_exceeded")
			require.Equal(t, 1, store.snapshotCalls, "exhausted work must not reach SQLite")
		})
	}
}

type boundedSearchNoPreflightStore struct {
	memory.FactStore
	searchCalls int
}

type boundedSearchSynapseSpy struct {
	synapse.SynapseStore
	listVerifiedCalls int
}

func (s *boundedSearchSynapseSpy) ListVerified(context.Context) ([]*synapse.Synapse, error) {
	s.listVerifiedCalls++
	return nil, fmt.Errorf("bounded search must not call the unbounded synapse store")
}

type boundedSearchFakeEmbedder struct{}

func (boundedSearchFakeEmbedder) Embed(context.Context, string) ([]float64, error) {
	return []float64{1}, nil
}

func (boundedSearchFakeEmbedder) Dimension() int               { return 1 }
func (boundedSearchFakeEmbedder) Name() string                 { return "bounded-search-test" }
func (boundedSearchFakeEmbedder) Mode() vectorstore.OracleMode { return vectorstore.OracleModeFull }

func (s *boundedSearchNoPreflightStore) Search(
	context.Context,
	string,
	int,
) ([]*memory.Fact, error) {
	s.searchCalls++
	return nil, fmt.Errorf("legacy search must not run without a preflight capability")
}

func addBoundedSearchFact(
	t *testing.T,
	repo *sqlite.FactRepo,
	ctx context.Context,
	id, content string,
	createdAt time.Time,
) *memory.Fact {
	t.Helper()
	fact := memory.NewFact(content, memory.LevelProject, "bounded-search", "")
	fact.ID = id
	fact.CreatedAt = createdAt
	fact.ValidFrom = createdAt
	fact.UpdatedAt = createdAt
	require.NoError(t, repo.Add(ctx, fact))
	return fact
}

func collectProjectBoundedSearch(
	t *testing.T,
	srv *Server,
	tenantID, projectID, query, mode string,
	limit, maxFactBytes int,
) collectedBoundedSearch {
	t.Helper()
	collected := collectedBoundedSearch{serialized: map[string][]byte{}}
	frameDigests := map[string]string{}
	frameTotals := map[string]int{}
	cursor := ""
	for pageNumber := 0; pageNumber < limit*40+40; pageNumber++ {
		arguments := map[string]interface{}{
			"query":          query,
			"mode":           mode,
			"limit":          float64(limit),
			"max_fact_bytes": float64(maxFactBytes),
		}
		if cursor != "" {
			arguments["cursor"] = cursor
		}
		result, err := srv.handleSearchProjectFactsPage(context.Background(), sessionToolReq(
			"search_project_facts_page", arguments, tenantID, projectID,
		))
		require.NoError(t, err)
		require.False(t, result.IsError)
		wire, err := json.Marshal(result)
		require.NoError(t, err)
		require.Less(t, len(wire), 1<<20, "every MCP result must remain below one MiB")

		envelope := decodeStructuredResult[boundedSearchEnvelope](t, result)
		require.Equal(t, factPageMemoryScope{
			Version: 1, Kind: "project", TenantID: tenantID, ProjectID: projectID,
		}, envelope.MemoryScope)
		require.Equal(t, boundedSearchProtocolVersion, envelope.Page.Version)
		require.Equal(t, factPageFrameRawBytes, envelope.Page.FrameRawLimitBytes)
		require.Equal(t, maxFactBytes, envelope.Page.MaxFactBytes)
		require.LessOrEqual(t, len(envelope.Page.NextCursor), boundedSearchMaxCursorBytes)
		if len(envelope.Page.NextCursor) > collected.maxCursorBytes {
			collected.maxCursorBytes = len(envelope.Page.NextCursor)
		}
		require.Len(t, envelope.Page.Frames, 1, "each non-empty page carries exactly one frame")
		frame := envelope.Page.Frames[0]
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
		require.Equal(t, len(collected.serialized[frame.FactID]), frame.Offset,
			"frame offsets must have no gaps or overlaps")
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
	t.Fatal("bounded search did not finish within the page cap")
	return collected
}

func firstProjectBoundedSearchPage(
	t *testing.T,
	srv *Server,
	projectID, query string,
	limit, maxFactBytes int,
) boundedSearchEnvelope {
	t.Helper()
	result, err := srv.handleSearchProjectFactsPage(context.Background(), sessionToolReq(
		"search_project_facts_page", map[string]interface{}{
			"query": query, "mode": "keyword", "limit": float64(limit),
			"max_fact_bytes": float64(maxFactBytes),
		}, "local", projectID,
	))
	require.NoError(t, err)
	require.False(t, result.IsError)
	return decodeStructuredResult[boundedSearchEnvelope](t, result)
}

func requireBoundedSearchErrorCode(t *testing.T, result *mcp.CallToolResult, code string) factPageErrorEnvelope {
	t.Helper()
	require.NotNil(t, result)
	require.True(t, result.IsError)
	envelope := decodeStructuredResult[factPageErrorEnvelope](t, result)
	require.Equal(t, code, envelope.Error.Code)
	return envelope
}

func TestBoundedSearchToolSchemasAreExactAndAdditive(t *testing.T) {
	srv, _ := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
	if srv.mcp.GetTool("search_default_facts_page") == nil {
		srv.registerBoundedSearchTools()
	}
	for _, name := range []string{"search_default_facts_page", "search_project_facts_page"} {
		tool := srv.mcp.GetTool(name)
		require.NotNil(t, tool, name)
		require.NotNil(t, tool.Handler, name)
		require.Equal(t, "object", tool.Tool.InputSchema.Type, name)
		require.ElementsMatch(t, []string{"query", "mode", "limit", "max_fact_bytes"}, tool.Tool.InputSchema.Required, name)
		require.ElementsMatch(t, []string{"query", "mode", "limit", "max_fact_bytes", "cursor"}, mapKeys(tool.Tool.InputSchema.Properties), name)
	}
	require.NotNil(t, srv.mcp.GetTool("search_facts"), "legacy search must remain registered")
}

func TestBoundedSearchUsesDefaultOrExactProjectScope(t *testing.T) {
	srv, repo := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
	stamp := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
	defaultCtx := rlmscope.WithScope(context.Background(), rlmscope.Default())
	alphaCtx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-alpha"))
	betaCtx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-beta"))
	addBoundedSearchFact(t, repo, defaultCtx, "default-fact", "needle default", stamp)
	addBoundedSearchFact(t, repo, alphaCtx, "alpha-fact", "needle alpha", stamp)
	addBoundedSearchFact(t, repo, betaCtx, "beta-fact", "needle beta", stamp)
	sessionFact := memory.NewFact("needle session must not leak", memory.LevelProject, "bounded-search", "")
	sessionFact.ID = "session-fact"
	sessionFact.CreatedAt = stamp
	sessionFact.ValidFrom = stamp
	require.NoError(t, repo.AddForSession(alphaCtx, "session-one", sessionFact))

	defaultResult, err := srv.handleSearchDefaultFactsPage(alphaCtx, callToolReq(
		"search_default_facts_page", map[string]interface{}{
			"query": "needle", "mode": "keyword", "limit": float64(20),
			"max_fact_bytes": float64(1024 * 1024),
		},
	))
	require.NoError(t, err)
	require.False(t, defaultResult.IsError)
	defaultEnvelope := decodeStructuredResult[boundedSearchEnvelope](t, defaultResult)
	require.Equal(t, "default", defaultEnvelope.MemoryScope.ProjectID)
	require.Equal(t, "default-fact", defaultEnvelope.Page.Frames[0].FactID)
	require.True(t, defaultEnvelope.Page.Done)

	project := collectProjectBoundedSearch(t, srv, "local", "project-alpha", "needle", "keyword", 20, 1024*1024)
	require.Equal(t, []string{"alpha-fact"}, project.order)

	baseDefault := func() mcp.CallToolRequest {
		return callToolReq("search_default_facts_page", map[string]interface{}{
			"query": "needle", "mode": "keyword", "limit": float64(20),
			"max_fact_bytes": float64(1024 * 1024),
		})
	}
	spoofs := map[string]func(*mcp.CallToolRequest){
		"header": func(req *mcp.CallToolRequest) {
			req.Header = http.Header{"x-rlm-project-id": []string{"default"}}
		},
		"argument": func(req *mcp.CallToolRequest) {
			req.Params.Arguments.(map[string]interface{})["project_id"] = "default"
		},
		"params meta": func(req *mcp.CallToolRequest) {
			req.Params.Meta = &mcp.Meta{AdditionalFields: map[string]interface{}{
				"rlm_scope": map[string]interface{}{"tenant_id": "local", "project_id": "default"},
			}}
		},
		"embedded meta": func(req *mcp.CallToolRequest) {
			req.Request.Params.Meta = &mcp.Meta{AdditionalFields: map[string]interface{}{
				"scope": map[string]interface{}{"tenant_id": "local", "project_id": "default"},
			}}
		},
	}
	for name, spoof := range spoofs {
		t.Run("default rejects "+name, func(t *testing.T) {
			req := baseDefault()
			spoof(&req)
			result, err := srv.handleSearchDefaultFactsPage(alphaCtx, req)
			require.NoError(t, err)
			errorEnvelope := requireBoundedSearchErrorCode(t, result, "scope_override_forbidden")
			require.NotNil(t, errorEnvelope.MemoryScope)
			require.Equal(t, "default", errorEnvelope.MemoryScope.ProjectID)
		})
	}

	for name, req := range map[string]mcp.CallToolRequest{
		"missing meta": callToolReq("search_project_facts_page", map[string]interface{}{
			"query": "needle", "mode": "keyword", "limit": float64(20),
			"max_fact_bytes": float64(1024 * 1024),
		}),
		"reserved default": sessionToolReq("search_project_facts_page", map[string]interface{}{
			"query": "needle", "mode": "keyword", "limit": float64(20),
			"max_fact_bytes": float64(1024 * 1024),
		}, "local", "default"),
	} {
		t.Run("project rejects "+name, func(t *testing.T) {
			result, err := srv.handleSearchProjectFactsPage(context.Background(), req)
			require.NoError(t, err)
			requireBoundedSearchErrorCode(t, result, "invalid_scope")
		})
	}
}

func TestBoundedSearchSplitsHTMLAndControlBytesWithoutGapsInRankedOrder(t *testing.T) {
	srv, repo := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-alpha"))
	stamp := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
	addBoundedSearchFact(t, repo, ctx, "fact-a", "needle first", stamp)
	largeContent := "needle " + strings.Repeat("<>&\x01\n", 80_000)
	addBoundedSearchFact(t, repo, ctx, "fact-b", largeContent, stamp)
	addBoundedSearchFact(t, repo, ctx, "fact-c", "needle third", stamp)

	collected := collectProjectBoundedSearch(t, srv, "local", "project-alpha", "needle", "keyword", 20, 4*1024*1024)
	// All three hold the whole query. BM25 normalises by length in words, and
	// the 400 KB fact has one word («needle»; the rest is markup bytes), so it
	// ranks first; the two-word facts follow by ID. It is still delivered whole.
	require.Equal(t, []string{"fact-b", "fact-a", "fact-c"}, collected.order)
	require.Greater(t, collected.pages, 3, "the escaped fact must span multiple 512 KiB frames")
	var decoded memory.Fact
	require.NoError(t, json.Unmarshal(collected.serialized["fact-b"], &decoded))
	require.Equal(t, largeContent, decoded.Content)
}

func TestBoundedSearchFreezesTwentyAndOneHundredLargeRankedResults(t *testing.T) {
	srv, repo := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-alpha"))
	stamp := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
	for index := 0; index < 100; index++ {
		id := fmt.Sprintf("fact-%03d", index)
		content := fmt.Sprintf("needle ranked payload %03d %s", index, strings.Repeat("x", 12*1024))
		addBoundedSearchFact(t, repo, ctx, id, content, stamp)
	}

	for _, limit := range []int{20, 100} {
		t.Run(fmt.Sprintf("limit_%d", limit), func(t *testing.T) {
			collected := collectProjectBoundedSearch(t, srv, "local", "project-alpha", "needle", "keyword", limit, 1024*1024)
			require.Len(t, collected.order, limit)
			require.Equal(t, limit, collected.pages)
			for index, id := range collected.order {
				require.Equal(t, fmt.Sprintf("fact-%03d", index), id)
			}
			require.LessOrEqual(t, collected.maxCursorBytes, boundedSearchMaxCursorBytes)
		})
	}
}

func TestBoundedSearchContinuationDetectsFrozenMutationButIgnoresInsert(t *testing.T) {
	for _, operation := range []string{"update", "delete"} {
		t.Run(operation, func(t *testing.T) {
			srv, repo := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
			ctx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-alpha"))
			stamp := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
			addBoundedSearchFact(t, repo, ctx, "fact-a", "needle first", stamp)
			future := addBoundedSearchFact(t, repo, ctx, "fact-b", "needle future", stamp)
			first := firstProjectBoundedSearchPage(t, srv, "project-alpha", "needle", 20, 1024*1024)
			require.False(t, first.Page.Done)
			require.NotEmpty(t, first.Page.NextCursor)
			if operation == "update" {
				future.Content = "needle future changed"
				require.NoError(t, repo.Update(ctx, future))
			} else {
				require.NoError(t, repo.Delete(ctx, future.ID))
			}
			result, err := srv.handleSearchProjectFactsPage(context.Background(), sessionToolReq(
				"search_project_facts_page", map[string]interface{}{
					"query": "needle", "mode": "keyword", "limit": float64(20),
					"max_fact_bytes": float64(1024 * 1024), "cursor": first.Page.NextCursor,
				}, "local", "project-alpha",
			))
			require.NoError(t, err)
			requireBoundedSearchErrorCode(t, result, "page_changed")
		})
	}

	t.Run("insert is ignored", func(t *testing.T) {
		srv, repo := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
		ctx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-alpha"))
		stamp := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
		addBoundedSearchFact(t, repo, ctx, "fact-a", "needle first", stamp)
		addBoundedSearchFact(t, repo, ctx, "fact-b", "needle second", stamp)
		first := firstProjectBoundedSearchPage(t, srv, "project-alpha", "needle", 20, 1024*1024)
		addBoundedSearchFact(t, repo, ctx, "fact-000-new", "needle inserted after freeze", stamp)

		result, err := srv.handleSearchProjectFactsPage(context.Background(), sessionToolReq(
			"search_project_facts_page", map[string]interface{}{
				"query": "needle", "mode": "keyword", "limit": float64(20),
				"max_fact_bytes": float64(1024 * 1024), "cursor": first.Page.NextCursor,
			}, "local", "project-alpha",
		))
		require.NoError(t, err)
		require.False(t, result.IsError)
		continued := decodeStructuredResult[boundedSearchEnvelope](t, result)
		require.True(t, continued.Page.Done)
		require.Equal(t, 2, continued.Page.ResultCount)
		require.Equal(t, "fact-b", continued.Page.Frames[0].FactID)
	})
}

func TestBoundedSearchRejectsInvalidMismatchedUnknownAndNonprogressCursors(t *testing.T) {
	srv, repo := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-alpha"))
	stamp := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
	addBoundedSearchFact(t, repo, ctx, "fact-a", "needle first", stamp)
	addBoundedSearchFact(t, repo, ctx, "fact-b", "needle second", stamp)
	first := firstProjectBoundedSearchPage(t, srv, "project-alpha", "needle", 20, 1024*1024)

	queryDigest := sha256.Sum256([]byte("needle"))
	decoded, err := decodeBoundedSearchCursor(
		first.Page.NextCursor, rlmscope.New("local", "project-alpha"),
		hex.EncodeToString(queryDigest[:]), "keyword", 20, 1024*1024,
	)
	require.NoError(t, err)
	decoded.ResultIndex = 0
	decoded.IntraFactOffset = 0
	nonprogress, err := encodeBoundedSearchCursor(decoded)
	require.NoError(t, err)

	validCursor, err := decodeBoundedSearchCursor(
		first.Page.NextCursor, rlmscope.New("local", "project-alpha"),
		hex.EncodeToString(queryDigest[:]), "keyword", 20, 1024*1024,
	)
	require.NoError(t, err)
	canonical, err := json.Marshal(validCursor)
	require.NoError(t, err)
	unknownPayload := append(append([]byte{}, canonical[:len(canonical)-1]...), []byte(`,"unknown":true}`)...)
	mac := hmac.New(sha256.New, factPageCursorMACKey)
	_, _ = mac.Write(unknownPayload)
	unknown := base64.RawURLEncoding.EncodeToString(unknownPayload) + "." +
		base64.RawURLEncoding.EncodeToString(mac.Sum(nil))
	foreignMAC := hmac.New(sha256.New, []byte("foreign-process-cursor-key"))
	_, _ = foreignMAC.Write(canonical)
	foreignProcess := base64.RawURLEncoding.EncodeToString(canonical) + "." +
		base64.RawURLEncoding.EncodeToString(foreignMAC.Sum(nil))

	tests := map[string]map[string]interface{}{
		"tampered": {
			"query": "needle", "mode": "keyword", "limit": float64(20),
			"max_fact_bytes": float64(1024 * 1024), "cursor": first.Page.NextCursor + "x",
		},
		"query mismatch": {
			"query": "different", "mode": "keyword", "limit": float64(20),
			"max_fact_bytes": float64(1024 * 1024), "cursor": first.Page.NextCursor,
		},
		"limit mismatch": {
			"query": "needle", "mode": "keyword", "limit": float64(19),
			"max_fact_bytes": float64(1024 * 1024), "cursor": first.Page.NextCursor,
		},
		"signed nonprogress": {
			"query": "needle", "mode": "keyword", "limit": float64(20),
			"max_fact_bytes": float64(1024 * 1024), "cursor": nonprogress,
		},
		"signed unknown field": {
			"query": "needle", "mode": "keyword", "limit": float64(20),
			"max_fact_bytes": float64(1024 * 1024), "cursor": unknown,
		},
		"foreign process key": {
			"query": "needle", "mode": "keyword", "limit": float64(20),
			"max_fact_bytes": float64(1024 * 1024), "cursor": foreignProcess,
		},
		"overlong": {
			"query": "needle", "mode": "keyword", "limit": float64(20),
			"max_fact_bytes": float64(1024 * 1024), "cursor": strings.Repeat("a", boundedSearchMaxCursorBytes+1),
		},
	}
	for name, arguments := range tests {
		t.Run(name, func(t *testing.T) {
			result, err := srv.handleSearchProjectFactsPage(context.Background(), sessionToolReq(
				"search_project_facts_page", arguments, "local", "project-alpha",
			))
			require.NoError(t, err)
			requireBoundedSearchErrorCode(t, result, "invalid_cursor")
		})
	}
}

func TestBoundedSearchValidatesExactArgumentsAndReportsTypedOversizedFact(t *testing.T) {
	srv, repo := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-alpha"))
	stamp := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
	fact := addBoundedSearchFact(t, repo, ctx, "fact-a", "needle bounded", stamp)

	base := func() map[string]interface{} {
		return map[string]interface{}{
			"query": "needle", "mode": "keyword", "limit": float64(20),
			"max_fact_bytes": float64(1024 * 1024),
		}
	}
	tests := map[string]func(map[string]interface{}){
		"unknown":     func(args map[string]interface{}) { args["extra"] = true },
		"empty query": func(args map[string]interface{}) { args["query"] = " \t" },
		"query byte cap": func(args map[string]interface{}) {
			args["query"] = strings.Repeat("界", boundedSearchMaxQueryBytes/3+1)
		},
		"invalid mode":   func(args map[string]interface{}) { args["mode"] = "other" },
		"fraction limit": func(args map[string]interface{}) { args["limit"] = 1.5 },
		"zero limit":     func(args map[string]interface{}) { args["limit"] = float64(0) },
		"large limit":    func(args map[string]interface{}) { args["limit"] = float64(101) },
		"zero max":       func(args map[string]interface{}) { args["max_fact_bytes"] = float64(0) },
		"large max":      func(args map[string]interface{}) { args["max_fact_bytes"] = float64(factPageMaxFactBytes + 1) },
	}
	for name, mutate := range tests {
		t.Run(name, func(t *testing.T) {
			arguments := base()
			mutate(arguments)
			result, err := srv.handleSearchProjectFactsPage(context.Background(), sessionToolReq(
				"search_project_facts_page", arguments, "local", "project-alpha",
			))
			require.NoError(t, err)
			requireBoundedSearchErrorCode(t, result, "invalid_arguments")
		})
	}

	hugeUnknown := strings.Repeat("untrusted-key-", 70_000)
	hugeUnknownArgs := base()
	hugeUnknownArgs[hugeUnknown] = true
	hugeUnknownResult, err := srv.handleSearchProjectFactsPage(context.Background(), sessionToolReq(
		"search_project_facts_page", hugeUnknownArgs, "local", "project-alpha",
	))
	require.NoError(t, err)
	requireBoundedSearchErrorCode(t, hugeUnknownResult, "invalid_arguments")
	hugeUnknownWire, err := json.Marshal(hugeUnknownResult)
	require.NoError(t, err)
	require.Less(t, len(hugeUnknownWire), 1<<20)
	require.NotContains(t, string(hugeUnknownWire), "untrusted-key-")

	maxQuery := base()
	maxQuery["query"] = strings.Repeat("a ", boundedSearchMaxQueryBytes/2)
	maxQueryResult, err := srv.handleSearchProjectFactsPage(context.Background(), sessionToolReq(
		"search_project_facts_page", maxQuery, "local", "project-alpha",
	))
	require.NoError(t, err)
	require.False(t, maxQueryResult.IsError, "the UTF-8 byte cap is inclusive")
	require.True(t, decodeStructuredResult[boundedSearchEnvelope](t, maxQueryResult).Page.Done)

	stored, err := repo.Get(ctx, fact.ID)
	require.NoError(t, err)
	serialized, err := json.Marshal(stored)
	require.NoError(t, err)
	oversizedArgs := base()
	oversizedArgs["max_fact_bytes"] = float64(len(serialized) - 1)
	oversized, err := srv.handleSearchProjectFactsPage(context.Background(), sessionToolReq(
		"search_project_facts_page", oversizedArgs, "local", "project-alpha",
	))
	require.NoError(t, err)
	errorEnvelope := requireBoundedSearchErrorCode(t, oversized, "fact_too_large")
	require.Equal(t, fact.ID, errorEnvelope.Error.FactID)
	require.Equal(t, len(serialized), errorEnvelope.Error.FactBytes)
	require.Equal(t, len(serialized)-1, errorEnvelope.Error.MaxFactBytes)
}

func TestBoundedSearchRejectsQueryWorkBeforeSnapshotForDefaultAndProject(t *testing.T) {
	tooManyTerms := make([]string, 65)
	for index := range tooManyTerms {
		tooManyTerms[index] = fmt.Sprintf("term%03d", index)
	}
	tests := map[string]string{
		"distinct terms":   strings.Join(tooManyTerms, " "),
		"normalized bytes": strings.Repeat("界", 1366),
	}
	for endpoint, invoke := range map[string]func(*Server, string) (*mcp.CallToolResult, error){
		"default": func(srv *Server, query string) (*mcp.CallToolResult, error) {
			return srv.handleSearchDefaultFactsPage(context.Background(), callToolReq(
				"search_default_facts_page", map[string]interface{}{
					"query": query, "mode": "keyword", "limit": float64(20),
					"max_fact_bytes": float64(1024 * 1024),
				},
			))
		},
		"project": func(srv *Server, query string) (*mcp.CallToolResult, error) {
			return srv.handleSearchProjectFactsPage(context.Background(), sessionToolReq(
				"search_project_facts_page", map[string]interface{}{
					"query": query, "mode": "keyword", "limit": float64(20),
					"max_fact_bytes": float64(1024 * 1024),
				}, "local", "project-alpha",
			))
		},
	} {
		for name, query := range tests {
			t.Run(endpoint+"/"+name, func(t *testing.T) {
				srv, repo := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
				store := &boundedSearchPreflightProbeStore{FactStore: repo, snapshot: repo}
				srv.facts = applicationtools.NewFactService(store, nil)

				result, err := invoke(srv, query)
				require.NoError(t, err)
				requireBoundedSearchErrorCode(t, result, "query_work_limit_exceeded")
				require.Zero(t, store.snapshotCalls,
					"query work must be bounded before opening the SQLite snapshot")
			})
		}
	}
}

func TestBoundedSemanticSearchDoesNotApplyKeywordTermBudget(t *testing.T) {
	terms := make([]string, 65)
	for index := range terms {
		terms[index] = fmt.Sprintf("semantic%03d", index)
	}
	srv, repo := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
	store := &boundedSearchPreflightProbeStore{FactStore: repo, snapshot: repo}
	service := applicationtools.NewFactService(store, nil)
	service.SetEmbedder(boundedSearchFakeEmbedder{})
	srv.facts = service

	result, err := srv.handleSearchProjectFactsPage(context.Background(), sessionToolReq(
		"search_project_facts_page", map[string]interface{}{
			"query": strings.Join(terms, " "), "mode": "semantic", "limit": float64(20),
			"max_fact_bytes": float64(1024 * 1024),
		}, "local", "project-alpha",
	))
	require.NoError(t, err)
	require.False(t, result.IsError)
	require.True(t, decodeStructuredResult[boundedSearchEnvelope](t, result).Page.Done)
	require.Equal(t, 1, store.snapshotCalls)
}

func TestBoundedSearchSnapshotRejectsStoredOversizeBeforeMaterialization(t *testing.T) {
	srv, repo := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
	store := &boundedSearchPreflightProbeStore{
		FactStore:      repo,
		snapshot:       repo,
		oversizeOnCall: 1,
		oversize: &memory.BoundedSearchStoredOversize{
			Kind:           memory.BoundedSearchStoredRowOversizeKind,
			StoredBytes:    int64(factPageMaxFactBytes + 4096),
			MaxStoredBytes: int64(factPageMaxFactBytes),
		},
	}
	srv.facts = applicationtools.NewFactService(store, nil)
	result, err := srv.handleSearchProjectFactsPage(context.Background(), sessionToolReq(
		"search_project_facts_page", map[string]interface{}{
			"query": "needle", "mode": "keyword", "limit": float64(20),
			"max_fact_bytes": float64(factPageMaxFactBytes),
		}, "local", "project-alpha",
	))
	require.NoError(t, err)
	require.True(t, result.IsError)
	envelope := decodeStructuredResult[boundedSearchStoredLimitEnvelope](t, result)
	require.Equal(t, "stored_fact_too_large", envelope.Error.Code)
	require.Equal(t, int64(factPageMaxFactBytes+4096), envelope.Error.StoredVariableBytes)
	require.Equal(t, int64(factPageMaxFactBytes), envelope.Error.MaxStoredVariableBytes)
	require.Zero(t, store.callbackCalls, "oversize must be rejected before materialization")
	wire, err := json.Marshal(result)
	require.NoError(t, err)
	require.Less(t, len(wire), 1<<20)
}

func TestBoundedSearchFailsClosedWithoutStoredRowPreflightCapability(t *testing.T) {
	srv, repo := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
	store := &boundedSearchNoPreflightStore{FactStore: repo}
	srv.facts = applicationtools.NewFactService(store, nil)
	result, err := srv.handleSearchProjectFactsPage(context.Background(), sessionToolReq(
		"search_project_facts_page", map[string]interface{}{
			"query": "needle", "mode": "keyword", "limit": float64(20),
			"max_fact_bytes": float64(factPageMaxFactBytes),
		}, "local", "project-alpha",
	))
	require.NoError(t, err)
	requireBoundedSearchErrorCode(t, result, "search_unavailable")
	require.Zero(t, store.searchCalls)
}

func TestBoundedSearchContinuationStoredOversizeIsPageChanged(t *testing.T) {
	srv, repo := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-alpha"))
	stamp := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
	addBoundedSearchFact(t, repo, ctx, "fact-a", "needle first", stamp)
	addBoundedSearchFact(t, repo, ctx, "fact-b", "needle second", stamp)
	store := &boundedSearchPreflightProbeStore{
		FactStore:      repo,
		snapshot:       repo,
		oversizeOnCall: 2,
		oversize: &memory.BoundedSearchStoredOversize{
			Kind:           memory.BoundedSearchStoredRowOversizeKind,
			StoredBytes:    16*1024*1024 + 1,
			MaxStoredBytes: 16 * 1024 * 1024,
		},
	}
	srv.facts = applicationtools.NewFactService(store, nil)
	first := firstProjectBoundedSearchPage(t, srv, "project-alpha", "needle", 20, 1024*1024)
	require.False(t, first.Page.Done)
	result, err := srv.handleSearchProjectFactsPage(context.Background(), sessionToolReq(
		"search_project_facts_page", map[string]interface{}{
			"query": "needle", "mode": "keyword", "limit": float64(20),
			"max_fact_bytes": float64(1024 * 1024), "cursor": first.Page.NextCursor,
		}, "local", "project-alpha",
	))
	require.NoError(t, err)
	requireBoundedSearchErrorCode(t, result, "page_changed")
	require.Equal(t, 1, store.callbackCalls, "continuation oversize must reject before its callback")
}

func TestBoundedHybridSearchNeverCallsUnboundedSynapseExpansion(t *testing.T) {
	for _, withEmbedder := range []bool{false, true} {
		t.Run(fmt.Sprintf("embedder_%t", withEmbedder), func(t *testing.T) {
			srv, repo := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
			ctx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-alpha"))
			stamp := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
			addBoundedSearchFact(t, repo, ctx, "fact-a", "needle base", stamp)
			spy := &boundedSearchSynapseSpy{}
			service := applicationtools.NewFactService(repo, nil).WithSynapseStore(spy)
			if withEmbedder {
				service.SetEmbedder(boundedSearchFakeEmbedder{})
			}
			srv.facts = service
			result, err := srv.handleSearchProjectFactsPage(context.Background(), sessionToolReq(
				"search_project_facts_page", map[string]interface{}{
					"query": "needle", "mode": "hybrid", "limit": float64(20),
					"max_fact_bytes": float64(1024 * 1024),
				}, "local", "project-alpha",
			))
			require.NoError(t, err)
			require.False(t, result.IsError)
			require.Zero(t, spy.listVerifiedCalls)
		})
	}
}

func TestLegacySearchFactsTextGoldenIsUnchangedByBoundedSearch(t *testing.T) {
	srv, repo := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-alpha"))
	stamp := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
	addBoundedSearchFact(t, repo, ctx, "legacy-a", "needle legacy", stamp)
	legacyRequest := callToolReq("search_facts", map[string]interface{}{
		"query": "needle", "mode": "keyword", "limit": float64(20),
	})

	before, err := srv.handleSearchFacts(ctx, legacyRequest)
	require.NoError(t, err)
	require.False(t, before.IsError)
	require.Nil(t, before.StructuredContent)
	const golden = `[
  {
    "id": "legacy-a",
    "tenant_id": "local",
    "project_id": "project-alpha",
    "content": "needle legacy",
    "level": 0,
    "domain": "bounded-search",
    "is_stale": false,
    "is_archived": false,
    "is_gene": false,
    "confidence": 1,
    "source": "unspecified",
    "origin": "unspecified",
    "hit_count": 0,
    "last_accessed_at": "0001-01-01T00:00:00Z",
    "created_at": "2026-01-02T03:04:05Z",
    "valid_from": "2026-01-02T03:04:05Z",
    "updated_at": "2026-01-02T03:04:05Z"
  }
]`
	require.Equal(t, golden, extractText(t, before))

	bounded := firstProjectBoundedSearchPage(t, srv, "project-alpha", "needle", 20, 1024*1024)
	require.True(t, bounded.Page.Done)
	after, err := srv.handleSearchFacts(ctx, legacyRequest)
	require.NoError(t, err)
	require.False(t, after.IsError)
	require.Nil(t, after.StructuredContent)
	require.Equal(t, golden, extractText(t, after))
}
