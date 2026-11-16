package mcpserver

import (
	"context"
	"encoding/json"
	"net/http"
	"testing"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/stretchr/testify/require"

	"github.com/syntrex/gomcp/internal/application/resources"
	"github.com/syntrex/gomcp/internal/application/tools"
	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"
)

func TestProjectToolsExposeScopedProjectRegistry(t *testing.T) {
	scope := rlmscope.New("tenant-a", "project-alpha")
	srv, factRepo := newProjectTestServer(t, scope)
	ctx := rlmscope.WithScope(context.Background(), scope)

	fact := memory.NewFact("alpha project fact", memory.LevelProject, "backend", "")
	require.NoError(t, factRepo.Add(ctx, fact))

	currentResult, err := srv.handleCurrentProject(context.Background(), callToolReq("current_project", nil))
	require.NoError(t, err)
	require.False(t, currentResult.IsError)
	var current rlmscope.ProjectStats
	require.NoError(t, json.Unmarshal([]byte(extractText(t, currentResult)), &current))
	require.Equal(t, "tenant-a", current.Project.TenantID)
	require.Equal(t, "project-alpha", current.Project.ProjectID)
	require.Equal(t, 1, current.TotalFacts)

	createResult, err := srv.handleCreateProject(context.Background(), callToolReq("create_project", map[string]interface{}{
		"project_id": "project-beta",
		"name":       "Beta Project",
	}))
	require.NoError(t, err)
	require.False(t, createResult.IsError)

	listResult, err := srv.handleListProjects(context.Background(), callToolReq("list_projects", map[string]interface{}{
		"include_archived": false,
	}))
	require.NoError(t, err)
	require.False(t, listResult.IsError)
	var active []rlmscope.Project
	require.NoError(t, json.Unmarshal([]byte(extractText(t, listResult)), &active))
	require.ElementsMatch(t, []string{"project-alpha", "project-beta"}, projectToolIDs(active))

	archiveResult, err := srv.handleArchiveProject(context.Background(), callToolReq("archive_project", map[string]interface{}{
		"project_id": "project-beta",
	}))
	require.NoError(t, err)
	require.False(t, archiveResult.IsError)
	var archived rlmscope.Project
	require.NoError(t, json.Unmarshal([]byte(extractText(t, archiveResult)), &archived))
	require.Equal(t, rlmscope.ProjectStatusArchived, archived.Status)

	listResult, err = srv.handleListProjects(context.Background(), callToolReq("list_projects", map[string]interface{}{
		"include_archived": false,
	}))
	require.NoError(t, err)
	require.False(t, listResult.IsError)
	require.NoError(t, json.Unmarshal([]byte(extractText(t, listResult)), &active))
	require.ElementsMatch(t, []string{"project-alpha"}, projectToolIDs(active))

	listResult, err = srv.handleListProjects(context.Background(), callToolReq("list_projects", map[string]interface{}{
		"include_archived": true,
	}))
	require.NoError(t, err)
	require.False(t, listResult.IsError)
	var all []rlmscope.Project
	require.NoError(t, json.Unmarshal([]byte(extractText(t, listResult)), &all))
	require.ElementsMatch(t, []string{"project-alpha", "project-beta"}, projectToolIDs(all))

	activateResult, err := srv.handleActivateProject(context.Background(), callToolReq("activate_project", map[string]interface{}{
		"project_id": "project-beta",
	}))
	require.NoError(t, err)
	require.False(t, activateResult.IsError)
	var reactivated rlmscope.Project
	require.NoError(t, json.Unmarshal([]byte(extractText(t, activateResult)), &reactivated))
	require.Equal(t, rlmscope.ProjectStatusActive, reactivated.Status)
}

func TestProjectToolsRejectInvalidProjectID(t *testing.T) {
	srv, _ := newProjectTestServer(t, rlmscope.New("tenant-a", "project-alpha"))

	result, err := srv.handleCreateProject(context.Background(), callToolReq("create_project", map[string]interface{}{
		"project_id": "bad/project",
	}))
	require.NoError(t, err)
	require.True(t, result.IsError)
	require.Contains(t, extractText(t, result), "unsupported character")
}

func TestScopeMiddlewareRoutesToolCallsByRequestScope(t *testing.T) {
	scope := rlmscope.New("tenant-a", "project-alpha")
	srv, _ := newProjectTestServer(t, scope)
	addFact := srv.scopeMiddleware()(srv.handleAddFact)
	listFacts := srv.scopeMiddleware()(srv.handleListFacts)
	currentProject := srv.scopeMiddleware()(srv.handleCurrentProject)

	alphaAdd, err := addFact(context.Background(), callToolReq("add_fact", map[string]interface{}{
		"content": "alpha-only fact",
		"level":   float64(0),
		"domain":  "scope",
	}))
	require.NoError(t, err)
	require.False(t, alphaAdd.IsError)

	betaReq := callToolReq("add_fact", map[string]interface{}{
		"content": "beta-only fact",
		"level":   float64(0),
		"domain":  "scope",
	})
	betaReq.Params.Meta = &mcp.Meta{AdditionalFields: map[string]any{
		"rlm_scope": map[string]any{
			"tenant_id":  "tenant-a",
			"project_id": "project-beta",
		},
	}}
	betaAdd, err := addFact(context.Background(), betaReq)
	require.NoError(t, err)
	require.False(t, betaAdd.IsError)

	alphaList, err := listFacts(context.Background(), callToolReq("list_facts", map[string]interface{}{}))
	require.NoError(t, err)
	require.False(t, alphaList.IsError)
	var alphaFacts []memory.Fact
	require.NoError(t, json.Unmarshal([]byte(extractText(t, alphaList)), &alphaFacts))
	require.Len(t, alphaFacts, 1)
	require.Equal(t, "alpha-only fact", alphaFacts[0].Content)

	betaListReq := callToolReq("list_facts", map[string]interface{}{})
	betaListReq.Header = http.Header{}
	betaListReq.Header.Set("X-RLM-Tenant-ID", "tenant-a")
	betaListReq.Header.Set("X-RLM-Project-ID", "project-beta")
	betaList, err := listFacts(context.Background(), betaListReq)
	require.NoError(t, err)
	require.False(t, betaList.IsError)
	var betaFacts []memory.Fact
	require.NoError(t, json.Unmarshal([]byte(extractText(t, betaList)), &betaFacts))
	require.Len(t, betaFacts, 1)
	require.Equal(t, "beta-only fact", betaFacts[0].Content)

	current, err := currentProject(context.Background(), betaListReq)
	require.NoError(t, err)
	require.False(t, current.IsError)
	var stats rlmscope.ProjectStats
	require.NoError(t, json.Unmarshal([]byte(extractText(t, current)), &stats))
	require.Equal(t, "project-beta", stats.Project.ProjectID)
	require.Equal(t, 1, stats.TotalFacts)
}

func TestUseProjectEnsuresRequestScopedProject(t *testing.T) {
	srv, _ := newProjectTestServer(t, rlmscope.New("tenant-a", "project-alpha"))
	useProject := srv.scopeMiddleware()(srv.handleUseProject)

	req := callToolReq("use_project", map[string]interface{}{
		"tenant_id":  "tenant-b",
		"project_id": "project-gamma",
		"name":       "Gamma Project",
	})
	result, err := useProject(context.Background(), req)
	require.NoError(t, err)
	require.False(t, result.IsError)

	var payload struct {
		Scope   rlmscope.Scope   `json:"scope"`
		Project rlmscope.Project `json:"project"`
	}
	require.NoError(t, json.Unmarshal([]byte(extractText(t, result)), &payload))
	require.Equal(t, "tenant-b", payload.Scope.TenantID)
	require.Equal(t, "project-gamma", payload.Scope.ProjectID)
	require.Equal(t, "Gamma Project", payload.Project.Name)
}

func newProjectTestServer(t *testing.T, scope rlmscope.Scope) (*Server, *sqlite.FactRepo) {
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
	projectRepo, err := sqlite.NewProjectRepo(factDB)
	require.NoError(t, err)
	projectSvc := tools.NewProjectService(projectRepo)

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
	resProv := resources.NewProvider(factRepo, stateRepo).WithScope(scope)

	return New(
		Config{Name: "test-gomcp", Version: "2.0.0-test"},
		factSvc, sessionSvc, causalSvc, crystalSvc, systemSvc, resProv,
		WithScope(scope),
		WithProjectService(projectSvc),
	), factRepo
}

func projectToolIDs(projects []rlmscope.Project) []string {
	ids := make([]string, 0, len(projects))
	for _, project := range projects {
		ids = append(ids, project.ProjectID)
	}
	return ids
}
