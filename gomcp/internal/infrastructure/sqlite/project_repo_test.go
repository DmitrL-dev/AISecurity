package sqlite

import (
	"testing"

	"github.com/stretchr/testify/require"

	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
)

func TestProjectRepo_IsolatesTenantProjectsAndLifecycle(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { db.Close() })

	factRepo, err := NewFactRepo(db)
	require.NoError(t, err)
	projectRepo, err := NewProjectRepo(db)
	require.NoError(t, err)

	ctxAlpha := scopedCtx("tenant-a", "project-alpha")
	ctxBeta := scopedCtx("tenant-a", "project-beta")
	ctxOtherTenant := scopedCtx("tenant-b", "project-alpha")

	alphaProject, err := projectRepo.Ensure(ctxAlpha, rlmscope.FromContext(ctxAlpha), "")
	require.NoError(t, err)
	require.Equal(t, "tenant-a", alphaProject.TenantID)
	require.Equal(t, "project-alpha", alphaProject.ProjectID)

	betaProject, err := projectRepo.Create(ctxAlpha, "project-beta", "Beta Project")
	require.NoError(t, err)
	require.Equal(t, "Beta Project", betaProject.Name)

	_, err = projectRepo.Ensure(ctxOtherTenant, rlmscope.FromContext(ctxOtherTenant), "Other Tenant Alpha")
	require.NoError(t, err)

	gene := memory.NewFact("alpha genome fact", memory.LevelProject, "backend", "")
	gene.Source = "genome"
	gene.Embedding = []float64{0.1, 0.2}
	require.NoError(t, factRepo.Add(ctxAlpha, gene))

	stale := memory.NewFact("alpha stale fact", memory.LevelDomain, "backend", "")
	stale.IsStale = true
	require.NoError(t, factRepo.Add(ctxAlpha, stale))

	archived := memory.NewFact("alpha archived fact", memory.LevelModule, "frontend", "")
	archived.IsArchived = true
	require.NoError(t, factRepo.Add(ctxAlpha, archived))

	sessionFact := memory.NewFact("alpha private session fact", memory.LevelSnippet, "session-private", "")
	sessionFact.Source = "genome"
	sessionFact.IsStale = true
	sessionFact.IsArchived = true
	sessionFact.Embedding = []float64{0.9, 0.1}
	require.NoError(t, factRepo.AddForSession(ctxAlpha, "session-one", sessionFact))

	betaFact := memory.NewFact("beta isolated fact", memory.LevelProject, "backend", "")
	require.NoError(t, factRepo.Add(ctxBeta, betaFact))

	stats, err := projectRepo.Stats(ctxAlpha, "project-alpha")
	require.NoError(t, err)
	require.Equal(t, "project-alpha", stats.Project.ProjectID)
	require.Equal(t, 3, stats.TotalFacts)
	require.Equal(t, 1, stats.GeneCount)
	require.Equal(t, 1, stats.StaleCount)
	require.Equal(t, 1, stats.ArchivedCount)
	require.Equal(t, 2, stats.DomainCount)
	require.Equal(t, 1, stats.WithEmbeddings)
	require.NotNil(t, stats.LastFactAt)

	tenantProjects, err := projectRepo.List(ctxAlpha, false)
	require.NoError(t, err)
	require.ElementsMatch(t, []string{"project-alpha", "project-beta"}, projectIDs(tenantProjects))

	otherTenantProjects, err := projectRepo.List(ctxOtherTenant, false)
	require.NoError(t, err)
	require.ElementsMatch(t, []string{"project-alpha"}, projectIDs(otherTenantProjects))
	require.Equal(t, "Other Tenant Alpha", otherTenantProjects[0].Name)

	archivedProject, err := projectRepo.Archive(ctxAlpha, "project-beta")
	require.NoError(t, err)
	require.Equal(t, rlmscope.ProjectStatusArchived, archivedProject.Status)
	require.NotNil(t, archivedProject.ArchivedAt)

	activeProjects, err := projectRepo.List(ctxAlpha, false)
	require.NoError(t, err)
	require.ElementsMatch(t, []string{"project-alpha"}, projectIDs(activeProjects))

	allProjects, err := projectRepo.List(ctxAlpha, true)
	require.NoError(t, err)
	require.ElementsMatch(t, []string{"project-alpha", "project-beta"}, projectIDs(allProjects))

	reactivated, err := projectRepo.Activate(ctxAlpha, "project-beta")
	require.NoError(t, err)
	require.Equal(t, rlmscope.ProjectStatusActive, reactivated.Status)
	require.Nil(t, reactivated.ArchivedAt)
}

func TestFactRepo_ArchivedProjectRejectsWrites(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { db.Close() })

	factRepo, err := NewFactRepo(db)
	require.NoError(t, err)
	projectRepo, err := NewProjectRepo(db)
	require.NoError(t, err)

	ctx := scopedCtx("tenant-a", "archive-me")
	fact := memory.NewFact("original", memory.LevelProject, "backend", "")
	require.NoError(t, factRepo.Add(ctx, fact))
	_, err = projectRepo.Archive(ctx, "archive-me")
	require.NoError(t, err)

	got, err := factRepo.Get(ctx, fact.ID)
	require.NoError(t, err)
	require.Equal(t, "original", got.Content)

	err = factRepo.Add(ctx, memory.NewFact("blocked add", memory.LevelProject, "backend", ""))
	require.ErrorContains(t, err, "is archived")

	got.Content = "blocked update"
	err = factRepo.Update(ctx, got)
	require.ErrorContains(t, err, "is archived")

	err = factRepo.TouchFact(ctx, fact.ID)
	require.ErrorContains(t, err, "is archived")

	err = factRepo.Delete(ctx, fact.ID)
	require.ErrorContains(t, err, "is archived")

	_, err = projectRepo.Activate(ctx, "archive-me")
	require.NoError(t, err)
	require.NoError(t, factRepo.Add(ctx, memory.NewFact("allowed after activation", memory.LevelProject, "backend", "")))
}

func TestFactRepo_SeedProjectsFromFactsRestoresRegistry(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { db.Close() })

	factRepo, err := NewFactRepo(db)
	require.NoError(t, err)
	projectRepo, err := NewProjectRepo(db)
	require.NoError(t, err)

	ctx := scopedCtx("tenant-a", "legacy-project")
	require.NoError(t, factRepo.Add(ctx, memory.NewFact("legacy fact", memory.LevelProject, "legacy", "")))
	_, err = db.Exec(`DELETE FROM rlm_projects WHERE tenant_id = ? AND project_id = ?`, "tenant-a", "legacy-project")
	require.NoError(t, err)

	projects, err := projectRepo.List(ctx, true)
	require.NoError(t, err)
	require.Empty(t, projects)

	require.NoError(t, factRepo.seedProjectsFromFacts())

	projects, err = projectRepo.List(ctx, true)
	require.NoError(t, err)
	require.Len(t, projects, 1)
	require.Equal(t, "legacy-project", projects[0].ProjectID)
	require.Equal(t, rlmscope.ProjectStatusActive, projects[0].Status)
}

func projectIDs(projects []*rlmscope.Project) []string {
	ids := make([]string, 0, len(projects))
	for _, project := range projects {
		ids = append(ids, project.ProjectID)
	}
	return ids
}
