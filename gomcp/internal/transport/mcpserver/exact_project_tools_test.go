package mcpserver

import (
	"context"
	"encoding/json"
	"errors"
	"testing"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/stretchr/testify/require"

	"github.com/syntrex/gomcp/internal/application/tools"
	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
)

func TestExactMemoryToolsHaveDedicatedRollbackSafeSchemas(t *testing.T) {
	srv, _ := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
	require.ElementsMatch(t, []string{
		"store_project_fact_exact",
		"add_session_fact", "get_session_turn", "search_session_facts", "inspect_current_project", "project_fact_stats",
		"list_default_facts_page", "list_project_facts_page",
		"search_default_facts_page", "search_project_facts_page",
		"default_fact_stats_page", "project_fact_stats_page",
		"add_scoped_session_turn", "get_scoped_session_turn", "search_scoped_session_facts_page",
		"acquire_scoped_session_turn_claim", "begin_scoped_session_turn_execution",
		"get_default_causal_chain_bounded",
	}, memory.ExactProtocolToolNames())

	store := srv.mcp.GetTool("store_project_fact_exact")
	require.NotNil(t, store)
	require.NotNil(t, store.Handler)
	require.Equal(t, "object", store.Tool.InputSchema.Type)
	require.ElementsMatch(t, []string{"content", "level"}, store.Tool.InputSchema.Required)
	require.ElementsMatch(t, []string{"content", "level", "domain", "module", "origin"},
		mapKeys(store.Tool.InputSchema.Properties))

	add := srv.mcp.GetTool("add_session_fact")
	require.NotNil(t, add)
	require.NotNil(t, add.Handler)
	require.Equal(t, "object", add.Tool.InputSchema.Type)
	require.ElementsMatch(t, []string{"session_id", "content"}, add.Tool.InputSchema.Required)
	require.ElementsMatch(t,
		[]string{"session_id", "turn_id", "content", "level", "domain", "module", "code_ref", "origin"},
		mapKeys(add.Tool.InputSchema.Properties),
	)

	search := srv.mcp.GetTool("search_session_facts")
	require.NotNil(t, search)
	require.NotNil(t, search.Handler)
	require.Equal(t, "object", search.Tool.InputSchema.Type)
	require.ElementsMatch(t, []string{"session_id", "query"}, search.Tool.InputSchema.Required)
	require.ElementsMatch(t,
		[]string{"session_id", "query", "limit", "mode"},
		mapKeys(search.Tool.InputSchema.Properties),
	)

	getTurn := srv.mcp.GetTool("get_session_turn")
	require.NotNil(t, getTurn)
	require.NotNil(t, getTurn.Handler)
	require.ElementsMatch(t, []string{"session_id", "turn_id"}, getTurn.Tool.InputSchema.Required)
	require.ElementsMatch(t, []string{"session_id", "turn_id"}, mapKeys(getTurn.Tool.InputSchema.Properties))

	for _, name := range []string{"inspect_current_project", "project_fact_stats"} {
		tool := srv.mcp.GetTool(name)
		require.NotNil(t, tool, name)
		require.NotNil(t, tool.Handler, name)
		require.Equal(t, "object", tool.Tool.InputSchema.Type, name)
		require.Empty(t, tool.Tool.InputSchema.Required, name)
		require.Empty(t, tool.Tool.InputSchema.Properties, name)
	}

	for _, name := range []string{"list_default_facts_page", "list_project_facts_page"} {
		tool := srv.mcp.GetTool(name)
		require.NotNil(t, tool, name)
		require.NotNil(t, tool.Handler, name)
		require.Equal(t, "object", tool.Tool.InputSchema.Type, name)
		require.ElementsMatch(t, []string{"level", "max_fact_bytes"}, tool.Tool.InputSchema.Required, name)
		require.ElementsMatch(t, []string{"level", "max_fact_bytes", "cursor"}, mapKeys(tool.Tool.InputSchema.Properties), name)
	}

	for _, legacyName := range []string{"add_fact", "search_facts", "list_facts", "current_project", "fact_stats"} {
		require.NotNil(t, srv.mcp.GetTool(legacyName), "legacy tool %s must remain registered", legacyName)
	}
}

func TestRequiredMetaScopeRejectsNormalizationAliasesAndInvalidProjectPrefix(t *testing.T) {
	srv := &Server{scope: rlmscope.New("local", "project-alpha")}
	for name, ids := range map[string][2]string{
		"padded tenant":  {" local ", "project-alpha"},
		"leading space":  {"local", " project-alpha"},
		"trailing space": {"local", "project-alpha "},
		"leading dot":    {"local", ".project-alpha"},
		"leading dash":   {"local", "-project-alpha"},
		"leading under":  {"local", "_project-alpha"},
	} {
		t.Run(name, func(t *testing.T) {
			_, err := srv.requiredMetaScope(sessionToolReq(
				"inspect_current_project", nil, ids[0], ids[1]))
			require.Error(t, err)
		})
	}

	sc, err := srv.requiredMetaScope(sessionToolReq(
		"inspect_current_project", nil, "local", "project-alpha"))
	require.NoError(t, err)
	require.Equal(t, rlmscope.Scope{TenantID: "local", ProjectID: "project-alpha"}, sc)
}

func TestInspectCurrentProjectIsExactAndReadOnly(t *testing.T) {
	srv, factRepo := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-alpha"))
	fact := memory.NewFact("existing project marker", memory.LevelProject, "project", "")
	require.NoError(t, factRepo.Add(ctx, fact))

	before, err := srv.projectSvc.Stats(ctx, "project-alpha")
	require.NoError(t, err)
	require.NotNil(t, before.Project.LastAccessedAt)

	result, err := srv.handleInspectCurrentProject(context.Background(), sessionToolReq(
		"inspect_current_project", map[string]interface{}{
			"tenant_id": "evil-argument",
		}, "local", "project-alpha"))
	require.NoError(t, err)
	require.False(t, result.IsError, extractText(t, result))

	var envelope map[string]json.RawMessage
	require.NoError(t, json.Unmarshal([]byte(extractText(t, result)), &envelope))
	require.Len(t, envelope, 1)
	require.Contains(t, envelope, "project")
	var project map[string]string
	require.NoError(t, json.Unmarshal(envelope["project"], &project))
	require.Equal(t, map[string]string{
		"tenant_id":  "local",
		"project_id": "project-alpha",
	}, project)

	after, err := srv.projectSvc.Stats(ctx, "project-alpha")
	require.NoError(t, err)
	require.Equal(t, before.Project.LastAccessedAt, after.Project.LastAccessedAt,
		"read-only inspection must not touch the project")

	missing, err := srv.handleInspectCurrentProject(context.Background(), sessionToolReq(
		"inspect_current_project", nil, "local", "missing-project"))
	require.NoError(t, err)
	require.True(t, missing.IsError)
	require.Contains(t, extractText(t, missing), "project not found")
	_, err = srv.projectSvc.Stats(
		rlmscope.WithScope(context.Background(), rlmscope.New("local", "missing-project")),
		"missing-project",
	)
	require.ErrorContains(t, err, "project not found", "inspection must not Ensure a missing project")
}

func TestInspectCurrentProjectFailsClosedOnMetaAndBackendMismatch(t *testing.T) {
	stub := &inspectProjectStoreStub{stats: &rlmscope.ProjectStats{Project: &rlmscope.Project{
		TenantID: "local", ProjectID: "project-other",
	}}}
	srv := &Server{
		projectSvc: tools.NewProjectService(stub),
		scope:      rlmscope.New("local", "project-alpha"),
	}

	missing, err := srv.handleInspectCurrentProject(context.Background(), callToolReq("inspect_current_project", map[string]interface{}{
		"tenant_id": "local", "project_id": "project-alpha",
	}))
	require.NoError(t, err)
	require.True(t, missing.IsError)
	require.Contains(t, extractText(t, missing), "_meta.rlm_scope")
	require.Zero(t, stub.statsCalls)

	for _, projectID := range []string{"default", "DEFAULT"} {
		reserved, err := srv.handleInspectCurrentProject(context.Background(), sessionToolReq(
			"inspect_current_project", nil, "local", projectID))
		require.NoError(t, err)
		require.True(t, reserved.IsError)
		require.Contains(t, extractText(t, reserved), "reserved for legacy memory")
		require.Zero(t, stub.statsCalls, "reserved legacy scope must fail before project lookup")
	}

	mismatch, err := srv.handleInspectCurrentProject(context.Background(), sessionToolReq(
		"inspect_current_project", nil, "local", "project-alpha"))
	require.NoError(t, err)
	require.True(t, mismatch.IsError)
	require.Contains(t, extractText(t, mismatch), "scope mismatch")
	require.Equal(t, 1, stub.statsCalls)
	require.Equal(t, "project-alpha", stub.lastStatsProjectID)
	require.Zero(t, stub.ensureCalls)

	stub.statsErr = errors.New("backend unavailable")
	backendError, err := srv.handleInspectCurrentProject(context.Background(), sessionToolReq(
		"inspect_current_project", nil, "local", "project-alpha"))
	require.NoError(t, err)
	require.True(t, backendError.IsError)
	require.Contains(t, extractText(t, backendError), "backend unavailable")
	require.Zero(t, stub.ensureCalls)
}

func TestProjectFactStatsHasExactScopeEnvelopeAndExcludesSessionFacts(t *testing.T) {
	srv, factRepo := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-alpha"))
	legacy := memory.NewFact("legacy project fact", memory.LevelProject, "legacy", "")
	require.NoError(t, factRepo.Add(ctx, legacy))
	sessionFact := memory.NewFact("private session fact", memory.LevelSnippet, "session-private", "")
	require.NoError(t, factRepo.AddForSession(ctx, "session-one", sessionFact))

	result, err := srv.handleProjectFactStats(context.Background(), sessionToolReq(
		"project_fact_stats", nil, "local", "project-alpha"))
	require.NoError(t, err)
	require.False(t, result.IsError, extractText(t, result))

	var envelope map[string]json.RawMessage
	require.NoError(t, json.Unmarshal([]byte(extractText(t, result)), &envelope))
	require.Len(t, envelope, 2)
	require.Contains(t, envelope, "memory_scope")
	require.Contains(t, envelope, "stats")

	var marker map[string]any
	require.NoError(t, json.Unmarshal(envelope["memory_scope"], &marker))
	require.Equal(t, map[string]any{
		"version":    float64(1),
		"kind":       "project",
		"tenant_id":  "local",
		"project_id": "project-alpha",
	}, marker)

	var stats memory.FactStoreStats
	require.NoError(t, json.Unmarshal(envelope["stats"], &stats))
	require.Equal(t, 1, stats.TotalFacts)
	require.Equal(t, 1, stats.LiveFacts)
	require.NotContains(t, stats.ByDomain, "session-private")

	var statsObject map[string]json.RawMessage
	require.NoError(t, json.Unmarshal(envelope["stats"], &statsObject))
	for _, key := range []string{
		"total_facts", "live_facts", "archived_count", "by_level", "by_domain", "by_origin",
		"stale_count", "with_embeddings", "gene_count", "cold_count",
	} {
		require.Contains(t, statsObject, key)
	}
	require.Len(t, statsObject, 10, "empty optional genome_hash must be the only omitted stats key")
}

func TestProjectFactStatsFailsClosedOnScopeProblems(t *testing.T) {
	srv, _ := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))

	missing, err := srv.handleProjectFactStats(context.Background(), callToolReq("project_fact_stats", nil))
	require.NoError(t, err)
	require.True(t, missing.IsError)
	require.Contains(t, extractText(t, missing), "_meta.rlm_scope")

	conflict := sessionToolReq("project_fact_stats", nil, "local", "project-alpha")
	conflict.Request.Params.Meta = &mcp.Meta{AdditionalFields: map[string]any{
		"rlm_scope": map[string]any{"tenant_id": "local", "project_id": "project-beta"},
	}}
	conflicting, err := srv.handleProjectFactStats(context.Background(), conflict)
	require.NoError(t, err)
	require.True(t, conflicting.IsError)
	require.Contains(t, extractText(t, conflicting), "conflicting _meta.rlm_scope")

	middlewareMismatch, err := srv.handleProjectFactStats(
		rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-beta")),
		sessionToolReq("project_fact_stats", nil, "local", "project-alpha"),
	)
	require.NoError(t, err)
	require.True(t, middlewareMismatch.IsError)
	require.Contains(t, extractText(t, middlewareMismatch), "does not match middleware scope")

	for _, projectID := range []string{"default", "DEFAULT"} {
		reserved, err := srv.handleProjectFactStats(context.Background(), sessionToolReq(
			"project_fact_stats", nil, "local", projectID))
		require.NoError(t, err)
		require.True(t, reserved.IsError)
		require.Contains(t, extractText(t, reserved), "reserved for legacy memory")
	}
}

func TestValidateProjectFactStatsRejectsMalformedCounts(t *testing.T) {
	valid := &memory.FactStoreStats{
		ByLevel:  map[memory.HierLevel]int{},
		ByDomain: map[string]int{},
		ByOrigin: map[memory.Origin]int{},
	}
	require.NoError(t, validateProjectFactStats(valid))

	negative := *valid
	negative.LiveFacts = -1
	require.ErrorContains(t, validateProjectFactStats(&negative), "live_facts must be nonnegative")

	missingMaps := *valid
	missingMaps.ByOrigin = nil
	require.ErrorContains(t, validateProjectFactStats(&missingMaps), "maps are missing")

	invalidLevel := *valid
	invalidLevel.TotalFacts = 1
	invalidLevel.ByLevel = map[memory.HierLevel]int{99: 1}
	require.ErrorContains(t, validateProjectFactStats(&invalidLevel), "invalid level")

	invalidOrigin := *valid
	invalidOrigin.TotalFacts = 1
	invalidOrigin.LiveFacts = 1
	invalidOrigin.ByLevel = map[memory.HierLevel]int{memory.LevelProject: 1}
	invalidOrigin.ByOrigin = map[memory.Origin]int{"forged": 1}
	require.ErrorContains(t, validateProjectFactStats(&invalidOrigin), "invalid origin")

	badLevelTotal := *valid
	badLevelTotal.TotalFacts = 2
	badLevelTotal.ByLevel = map[memory.HierLevel]int{memory.LevelProject: 1}
	require.ErrorContains(t, validateProjectFactStats(&badLevelTotal), "by_level total must equal")

	badOriginTotal := *valid
	badOriginTotal.TotalFacts = 2
	badOriginTotal.LiveFacts = 2
	badOriginTotal.ByLevel = map[memory.HierLevel]int{memory.LevelProject: 2}
	badOriginTotal.ByOrigin = map[memory.Origin]int{memory.OriginExternal: 1}
	require.ErrorContains(t, validateProjectFactStats(&badOriginTotal), "by_origin total must equal")

	overTotal := *valid
	overTotal.TotalFacts = 1
	overTotal.LiveFacts = 2
	require.ErrorContains(t, validateProjectFactStats(&overTotal), "live_facts exceeds total_facts")
}

func TestProjectFactStatsDoesNotAttestMalformedBackendStats(t *testing.T) {
	forged := &memory.FactStoreStats{
		TotalFacts: 1,
		LiveFacts:  1,
		ByLevel:    map[memory.HierLevel]int{99: 1},
		ByDomain:   map[string]int{},
		ByOrigin:   map[memory.Origin]int{memory.OriginExternal: 1},
	}
	srv := &Server{
		facts: tools.NewFactService(&forgedStatsFactStore{stats: forged}, nil),
		scope: rlmscope.New("local", "project-alpha"),
	}

	result, err := srv.handleProjectFactStats(context.Background(), sessionToolReq(
		"project_fact_stats", nil, "local", "project-alpha"))
	require.NoError(t, err)
	require.True(t, result.IsError)
	require.Contains(t, extractText(t, result), "invalid level")
	require.NotContains(t, extractText(t, result), "memory_scope",
		"malformed backend stats must never receive an exact success marker")
}

type forgedStatsFactStore struct {
	memory.FactStore
	stats *memory.FactStoreStats
}

func (s *forgedStatsFactStore) Stats(context.Context) (*memory.FactStoreStats, error) {
	return s.stats, nil
}

type inspectProjectStoreStub struct {
	stats              *rlmscope.ProjectStats
	statsErr           error
	statsCalls         int
	ensureCalls        int
	lastStatsProjectID string
}

func mapKeys[V any](values map[string]V) []string {
	keys := make([]string, 0, len(values))
	for key := range values {
		keys = append(keys, key)
	}
	return keys
}

func (s *inspectProjectStoreStub) Ensure(context.Context, rlmscope.Scope, string) (*rlmscope.Project, error) {
	s.ensureCalls++
	return nil, errors.New("unexpected Ensure")
}

func (s *inspectProjectStoreStub) Create(context.Context, string, string) (*rlmscope.Project, error) {
	return nil, errors.New("unexpected Create")
}

func (s *inspectProjectStoreStub) Get(context.Context, string) (*rlmscope.Project, error) {
	return nil, errors.New("unexpected Get")
}

func (s *inspectProjectStoreStub) List(context.Context, bool) ([]*rlmscope.Project, error) {
	return nil, errors.New("unexpected List")
}

func (s *inspectProjectStoreStub) Archive(context.Context, string) (*rlmscope.Project, error) {
	return nil, errors.New("unexpected Archive")
}

func (s *inspectProjectStoreStub) Activate(context.Context, string) (*rlmscope.Project, error) {
	return nil, errors.New("unexpected Activate")
}

func (s *inspectProjectStoreStub) Stats(_ context.Context, projectID string) (*rlmscope.ProjectStats, error) {
	s.statsCalls++
	s.lastStatsProjectID = projectID
	if s.statsErr != nil {
		return nil, s.statsErr
	}
	return s.stats, nil
}

type projectExactStoreTestEnvelope struct {
	MemoryScope struct {
		Version   int    `json:"version"`
		Kind      string `json:"kind"`
		TenantID  string `json:"tenant_id"`
		ProjectID string `json:"project_id"`
	} `json:"memory_scope"`
	Fact    *memory.Fact `json:"fact,omitempty"`
	Created bool         `json:"created"`
	Error   *struct {
		Code    string `json:"code"`
		Message string `json:"message"`
	} `json:"error,omitempty"`
}

type projectExactStoreErrorStub struct {
	memory.FactStore
	err error
}

func (s *projectExactStoreErrorStub) StoreProjectFactExact(
	context.Context,
	*memory.Fact,
) (*memory.Fact, bool, error) {
	return nil, false, s.err
}

func decodeProjectExactStoreResult(t *testing.T, result *mcp.CallToolResult) projectExactStoreTestEnvelope {
	t.Helper()
	require.NotNil(t, result)
	require.Empty(t, result.Content, "exact project store must be structured-only")
	payload, err := json.Marshal(result.StructuredContent)
	require.NoError(t, err)
	var envelope projectExactStoreTestEnvelope
	require.NoError(t, json.Unmarshal(payload, &envelope))
	return envelope
}

func TestStoreProjectFactExactReturnsDurableStructuredEnvelope(t *testing.T) {
	srv, repo := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
	request := func(module string) mcp.CallToolRequest {
		return sessionToolReq("store_project_fact_exact", map[string]interface{}{
			"content": "durable wire fact",
			"level":   float64(1),
			"domain":  "billing",
			"module":  module,
			"origin":  "user",
		}, "local", "project-alpha")
	}

	result, err := srv.handleStoreProjectFactExact(context.Background(), request("invoice"))
	require.NoError(t, err)
	require.False(t, result.IsError)
	created := decodeProjectExactStoreResult(t, result)
	require.True(t, created.Created)
	require.Nil(t, created.Error)
	require.NotNil(t, created.Fact)
	require.Equal(t, 1, created.MemoryScope.Version)
	require.Equal(t, "project", created.MemoryScope.Kind)
	require.Equal(t, "local", created.MemoryScope.TenantID)
	require.Equal(t, "project-alpha", created.MemoryScope.ProjectID)
	require.Equal(t, "invoice", created.Fact.Module)
	require.Equal(t, memory.OriginUser, created.Fact.Origin)
	require.Equal(t, "local", created.Fact.TenantID)
	require.Equal(t, "project-alpha", created.Fact.ProjectID)

	durable, err := repo.Get(
		rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-alpha")),
		created.Fact.ID,
	)
	require.NoError(t, err)
	require.Equal(t, created.Fact, durable, "wire fact must be the decoded durable row")

	result, err = srv.handleStoreProjectFactExact(context.Background(), request("invoice"))
	require.NoError(t, err)
	require.False(t, result.IsError)
	replayed := decodeProjectExactStoreResult(t, result)
	require.False(t, replayed.Created)
	require.Equal(t, created.Fact.ID, replayed.Fact.ID)
	require.Equal(t, durable, replayed.Fact)

	result, err = srv.handleStoreProjectFactExact(context.Background(), request("ledger"))
	require.NoError(t, err)
	require.True(t, result.IsError)
	conflict := decodeProjectExactStoreResult(t, result)
	require.NotNil(t, conflict.Error)
	require.Equal(t, "exact_fact_conflict", conflict.Error.Code)
	require.Nil(t, conflict.Fact)

	after, err := repo.Get(
		rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-alpha")),
		created.Fact.ID,
	)
	require.NoError(t, err)
	require.Equal(t, durable, after, "typed conflict must not mutate the durable row")

	_, err = srv.projectSvc.Archive(
		rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-alpha")),
		"project-alpha",
	)
	require.NoError(t, err)
	result, err = srv.handleStoreProjectFactExact(context.Background(), request("invoice"))
	require.NoError(t, err)
	require.True(t, result.IsError)
	archived := decodeProjectExactStoreResult(t, result)
	require.NotNil(t, archived.Error)
	require.Equal(t, "project_not_writable", archived.Error.Code)
}

func TestStoreProjectFactExactStrictArgumentsAndScope(t *testing.T) {
	tests := map[string]struct {
		request mcp.CallToolRequest
		code    string
	}{
		"missing exact meta": {
			request: callToolReq("store_project_fact_exact", map[string]interface{}{
				"content": "fact", "level": float64(1),
			}),
			code: "invalid_scope",
		},
		"default project": {
			request: sessionToolReq("store_project_fact_exact", map[string]interface{}{
				"content": "fact", "level": float64(1),
			}, "local", "default"),
			code: "invalid_scope",
		},
		"unknown argument": {
			request: sessionToolReq("store_project_fact_exact", map[string]interface{}{
				"content": "fact", "level": float64(1), "code_ref": "main.go:1",
			}, "local", "project-alpha"),
			code: "invalid_arguments",
		},
		"scope argument": {
			request: sessionToolReq("store_project_fact_exact", map[string]interface{}{
				"content": "fact", "level": float64(1), "project_id": "project-other",
			}, "local", "project-alpha"),
			code: "invalid_arguments",
		},
		"fractional level": {
			request: sessionToolReq("store_project_fact_exact", map[string]interface{}{
				"content": "fact", "level": 1.5,
			}, "local", "project-alpha"),
			code: "invalid_arguments",
		},
		"whitespace content": {
			request: sessionToolReq("store_project_fact_exact", map[string]interface{}{
				"content": " \t\n", "level": float64(1),
			}, "local", "project-alpha"),
			code: "invalid_arguments",
		},
		"wrong optional type": {
			request: sessionToolReq("store_project_fact_exact", map[string]interface{}{
				"content": "fact", "level": float64(1), "module": true,
			}, "local", "project-alpha"),
			code: "invalid_arguments",
		},
		"invalid origin": {
			request: sessionToolReq("store_project_fact_exact", map[string]interface{}{
				"content": "fact", "level": float64(1), "origin": "builtin",
			}, "local", "project-alpha"),
			code: "invalid_arguments",
		},
	}

	for name, test := range tests {
		t.Run(name, func(t *testing.T) {
			srv, repo := newProjectTestServer(t, rlmscope.New("local", "project-alpha"))
			result, err := srv.handleStoreProjectFactExact(context.Background(), test.request)
			require.NoError(t, err)
			require.True(t, result.IsError)
			envelope := decodeProjectExactStoreResult(t, result)
			require.NotNil(t, envelope.Error)
			require.Equal(t, test.code, envelope.Error.Code)
			stats, err := repo.Stats(rlmscope.WithScope(
				context.Background(), rlmscope.New("local", "project-alpha")))
			require.NoError(t, err)
			require.Zero(t, stats.TotalFacts)
		})
	}
}

func TestStoreProjectFactExactMapsIntegrityErrorWithoutTextFallback(t *testing.T) {
	srv := &Server{
		facts: tools.NewFactService(&projectExactStoreErrorStub{err: memory.ErrExactFactIntegrity}, nil),
		scope: rlmscope.New("local", "project-alpha"),
	}
	result, err := srv.handleStoreProjectFactExact(context.Background(), sessionToolReq(
		"store_project_fact_exact",
		map[string]interface{}{
			"content": "integrity failure", "level": float64(1), "origin": "external",
		},
		"local", "project-alpha",
	))
	require.NoError(t, err)
	require.True(t, result.IsError)
	envelope := decodeProjectExactStoreResult(t, result)
	require.NotNil(t, envelope.Error)
	require.Equal(t, "exact_fact_integrity", envelope.Error.Code)
}
