package sqlite_test

import (
	"context"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"
)

func setupSynapseTest(t *testing.T) (*sqlite.SynapseRepo, *sqlite.FactRepo) {
	t.Helper()
	db, err := sqlite.OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { db.Close() })

	// FactRepo migration creates synapses table.
	factRepo, err := sqlite.NewFactRepo(db)
	require.NoError(t, err)

	synapseRepo := sqlite.NewSynapseRepo(db)
	return synapseRepo, factRepo
}

func setupSynapseProjectTest(t *testing.T) (*sqlite.SynapseRepo, *sqlite.FactRepo, *sqlite.ProjectRepo) {
	t.Helper()
	db, err := sqlite.OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { db.Close() })

	factRepo, err := sqlite.NewFactRepo(db)
	require.NoError(t, err)
	projectRepo, err := sqlite.NewProjectRepo(db)
	require.NoError(t, err)

	return sqlite.NewSynapseRepo(db), factRepo, projectRepo
}

func synapseCtx(tenantID, projectID string) context.Context {
	return rlmscope.WithScope(context.Background(), rlmscope.New(tenantID, projectID))
}

func TestSynapseRepo_CreateAndListPending(t *testing.T) {
	repo, factRepo := setupSynapseTest(t)
	ctx := context.Background()

	// Create two facts to link.
	f1 := memory.NewFact("Architecture overview", memory.LevelDomain, "arch", "")
	f2 := memory.NewFact("Security module design", memory.LevelDomain, "security", "")
	require.NoError(t, factRepo.Add(ctx, f1))
	require.NoError(t, factRepo.Add(ctx, f2))

	// Create synapse.
	id, err := repo.Create(ctx, f1.ID, f2.ID, 0.92)
	require.NoError(t, err)
	assert.Greater(t, id, int64(0))

	// List pending.
	pending, err := repo.ListPending(ctx, 10)
	require.NoError(t, err)
	require.Len(t, pending, 1)
	assert.Equal(t, f1.ID, pending[0].FactIDA)
	assert.Equal(t, f2.ID, pending[0].FactIDB)
	assert.InDelta(t, 0.92, pending[0].Confidence, 0.01)
	assert.Equal(t, "PENDING", string(pending[0].Status))
}

func TestSynapseRepoLegacySurfaceQuarantinesSessionEndpoints(t *testing.T) {
	db, err := sqlite.OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	factRepo, err := sqlite.NewFactRepo(db)
	require.NoError(t, err)
	repo := sqlite.NewSynapseRepo(db)
	ctx := synapseCtx("tenant-a", "project-alpha")

	legacyA := memory.NewFact("legacy A", memory.LevelModule, "legacy", "")
	legacyB := memory.NewFact("legacy B", memory.LevelModule, "legacy", "")
	require.NoError(t, factRepo.Add(ctx, legacyA))
	require.NoError(t, factRepo.Add(ctx, legacyB))
	sessionFact := memory.NewFact("private session endpoint", memory.LevelModule, "session", "")
	require.NoError(t, factRepo.AddForSession(ctx, "session-one", sessionFact))

	legacyID, err := repo.Create(ctx, legacyA.ID, legacyB.ID, 0.9)
	require.NoError(t, err)
	quarantinedID, err := repo.Create(ctx, legacyA.ID, legacyB.ID, 0.8)
	require.NoError(t, err)
	_, err = db.SqlDB().Exec(`UPDATE synapses SET fact_id_a = ? WHERE id = ?`, sessionFact.ID, quarantinedID)
	require.NoError(t, err, "simulate a pre-isolation synapse row")

	_, err = repo.Create(ctx, sessionFact.ID, legacyB.ID, 0.7)
	require.ErrorContains(t, err, "not found in scope")

	pendingFacts, err := repo.ListPending(ctx, 20)
	require.NoError(t, err)
	require.Len(t, pendingFacts, 1)
	require.Equal(t, legacyID, pendingFacts[0].ID)

	pending, verified, rejected, err := repo.Count(ctx)
	require.NoError(t, err)
	require.Equal(t, 1, pending)
	require.Zero(t, verified)
	require.Zero(t, rejected)

	exists, err := repo.Exists(ctx, sessionFact.ID, legacyB.ID)
	require.NoError(t, err)
	require.False(t, exists)
	require.ErrorContains(t, repo.Accept(ctx, quarantinedID), "not found or not PENDING")
}

func TestSynapseRepo_AcceptAndListVerified(t *testing.T) {
	repo, factRepo := setupSynapseTest(t)
	ctx := context.Background()

	f1 := memory.NewFact("fact A", memory.LevelModule, "test", "")
	f2 := memory.NewFact("fact B", memory.LevelModule, "test", "")
	require.NoError(t, factRepo.Add(ctx, f1))
	require.NoError(t, factRepo.Add(ctx, f2))

	id, err := repo.Create(ctx, f1.ID, f2.ID, 0.88)
	require.NoError(t, err)

	// Accept.
	require.NoError(t, repo.Accept(ctx, id))

	// Should no longer be in pending.
	pending, _ := repo.ListPending(ctx, 10)
	assert.Empty(t, pending)

	// Should be in verified.
	verified, err := repo.ListVerified(ctx)
	require.NoError(t, err)
	require.Len(t, verified, 1)
	assert.Equal(t, "VERIFIED", string(verified[0].Status))
}

func TestSynapseRepo_Reject(t *testing.T) {
	repo, factRepo := setupSynapseTest(t)
	ctx := context.Background()

	f1 := memory.NewFact("fact X", memory.LevelProject, "", "")
	f2 := memory.NewFact("fact Y", memory.LevelProject, "", "")
	require.NoError(t, factRepo.Add(ctx, f1))
	require.NoError(t, factRepo.Add(ctx, f2))

	id, err := repo.Create(ctx, f1.ID, f2.ID, 0.50)
	require.NoError(t, err)

	require.NoError(t, repo.Reject(ctx, id))

	pending, _ := repo.ListPending(ctx, 10)
	assert.Empty(t, pending)

	verified, _ := repo.ListVerified(ctx)
	assert.Empty(t, verified)
}

func TestSynapseRepo_Count(t *testing.T) {
	repo, factRepo := setupSynapseTest(t)
	ctx := context.Background()

	f1 := memory.NewFact("a", memory.LevelProject, "", "")
	f2 := memory.NewFact("b", memory.LevelProject, "", "")
	f3 := memory.NewFact("c", memory.LevelProject, "", "")
	require.NoError(t, factRepo.Add(ctx, f1))
	require.NoError(t, factRepo.Add(ctx, f2))
	require.NoError(t, factRepo.Add(ctx, f3))

	id1, _ := repo.Create(ctx, f1.ID, f2.ID, 0.90)
	id2, _ := repo.Create(ctx, f1.ID, f3.ID, 0.85)
	_, _ = repo.Create(ctx, f2.ID, f3.ID, 0.40)

	_ = repo.Accept(ctx, id1)
	_ = repo.Reject(ctx, id2)

	pending, verified, rejected, err := repo.Count(ctx)
	require.NoError(t, err)
	assert.Equal(t, 1, pending)
	assert.Equal(t, 1, verified)
	assert.Equal(t, 1, rejected)
}

func TestSynapseRepo_Exists(t *testing.T) {
	repo, factRepo := setupSynapseTest(t)
	ctx := context.Background()

	f1 := memory.NewFact("p", memory.LevelProject, "", "")
	f2 := memory.NewFact("q", memory.LevelProject, "", "")
	require.NoError(t, factRepo.Add(ctx, f1))
	require.NoError(t, factRepo.Add(ctx, f2))

	// No synapse yet.
	exists, err := repo.Exists(ctx, f1.ID, f2.ID)
	require.NoError(t, err)
	assert.False(t, exists)

	// Create one.
	_, _ = repo.Create(ctx, f1.ID, f2.ID, 0.95)

	// Should exist in both directions.
	exists, _ = repo.Exists(ctx, f1.ID, f2.ID)
	assert.True(t, exists)

	exists, _ = repo.Exists(ctx, f2.ID, f1.ID)
	assert.True(t, exists, "bidirectional check should work")
}

func TestSynapseRepo_AcceptNonPending_Fails(t *testing.T) {
	repo, factRepo := setupSynapseTest(t)
	ctx := context.Background()

	f1 := memory.NewFact("m", memory.LevelProject, "", "")
	f2 := memory.NewFact("n", memory.LevelProject, "", "")
	require.NoError(t, factRepo.Add(ctx, f1))
	require.NoError(t, factRepo.Add(ctx, f2))

	id, _ := repo.Create(ctx, f1.ID, f2.ID, 0.80)
	_ = repo.Accept(ctx, id)

	// Trying to accept again should fail.
	err := repo.Accept(ctx, id)
	assert.Error(t, err)
}

func TestSynapseRepo_ArchivedProjectRejectsWrites(t *testing.T) {
	repo, factRepo, projectRepo := setupSynapseProjectTest(t)
	ctx := synapseCtx("tenant-a", "archived-project")

	f1 := memory.NewFact("fact A", memory.LevelProject, "test", "")
	f2 := memory.NewFact("fact B", memory.LevelProject, "test", "")
	f3 := memory.NewFact("fact C", memory.LevelProject, "test", "")
	require.NoError(t, factRepo.Add(ctx, f1))
	require.NoError(t, factRepo.Add(ctx, f2))
	require.NoError(t, factRepo.Add(ctx, f3))

	id, err := repo.Create(ctx, f1.ID, f2.ID, 0.80)
	require.NoError(t, err)
	_, err = projectRepo.Archive(ctx, "archived-project")
	require.NoError(t, err)

	_, err = repo.Create(ctx, f2.ID, f3.ID, 0.70)
	require.ErrorContains(t, err, "is archived")
	require.ErrorContains(t, repo.Accept(ctx, id), "is archived")
	require.ErrorContains(t, repo.Reject(ctx, id), "is archived")

	pending, err := repo.ListPending(ctx, 10)
	require.NoError(t, err)
	require.Len(t, pending, 1)

	_, err = projectRepo.Activate(ctx, "archived-project")
	require.NoError(t, err)
	require.NoError(t, repo.Accept(ctx, id))
}

func TestSynapseRepo_ScopeIsolation(t *testing.T) {
	repo, factRepo := setupSynapseTest(t)
	ctxA := synapseCtx("tenant-a", "project-alpha")
	ctxB := synapseCtx("tenant-b", "project-alpha")

	a1 := memory.NewFact("alpha one", memory.LevelProject, "scope", "")
	a2 := memory.NewFact("alpha two", memory.LevelProject, "scope", "")
	b1 := memory.NewFact("bravo one", memory.LevelProject, "scope", "")
	b2 := memory.NewFact("bravo two", memory.LevelProject, "scope", "")
	require.NoError(t, factRepo.Add(ctxA, a1))
	require.NoError(t, factRepo.Add(ctxA, a2))
	require.NoError(t, factRepo.Add(ctxB, b1))
	require.NoError(t, factRepo.Add(ctxB, b2))

	idA, err := repo.Create(ctxA, a1.ID, a2.ID, 0.91)
	require.NoError(t, err)
	idB, err := repo.Create(ctxB, b1.ID, b2.ID, 0.87)
	require.NoError(t, err)
	assert.NotEqual(t, idA, idB)

	_, err = repo.Create(ctxA, a1.ID, b1.ID, 0.99)
	require.Error(t, err, "synapse creation must reject cross-scope fact IDs")

	pendingA, err := repo.ListPending(ctxA, 10)
	require.NoError(t, err)
	require.Len(t, pendingA, 1)
	assert.Equal(t, idA, pendingA[0].ID)
	assert.Equal(t, "tenant-a", pendingA[0].TenantID)

	pendingB, err := repo.ListPending(ctxB, 10)
	require.NoError(t, err)
	require.Len(t, pendingB, 1)
	assert.Equal(t, idB, pendingB[0].ID)
	assert.Equal(t, "tenant-b", pendingB[0].TenantID)

	require.Error(t, repo.Accept(ctxB, idA), "tenant B must not accept tenant A synapse by ID")
	require.NoError(t, repo.Accept(ctxA, idA))

	verifiedA, err := repo.ListVerified(ctxA)
	require.NoError(t, err)
	require.Len(t, verifiedA, 1)
	assert.Equal(t, idA, verifiedA[0].ID)

	verifiedB, err := repo.ListVerified(ctxB)
	require.NoError(t, err)
	assert.Empty(t, verifiedB)

	pending, verified, rejected, err := repo.Count(ctxA)
	require.NoError(t, err)
	assert.Equal(t, 0, pending)
	assert.Equal(t, 1, verified)
	assert.Equal(t, 0, rejected)

	pending, verified, rejected, err = repo.Count(ctxB)
	require.NoError(t, err)
	assert.Equal(t, 1, pending)
	assert.Equal(t, 0, verified)
	assert.Equal(t, 0, rejected)

	exists, err := repo.Exists(ctxA, a1.ID, a2.ID)
	require.NoError(t, err)
	assert.True(t, exists)
	exists, err = repo.Exists(ctxB, a1.ID, a2.ID)
	require.NoError(t, err)
	assert.False(t, exists)

	require.NoError(t, factRepo.Delete(ctxA, a1.ID))
	verifiedA, err = repo.ListVerified(ctxA)
	require.NoError(t, err)
	assert.Empty(t, verifiedA, "deleting an alpha fact must remove alpha synapses")

	pendingB, err = repo.ListPending(ctxB, 10)
	require.NoError(t, err)
	require.Len(t, pendingB, 1, "deleting alpha fact must not remove bravo synapses")
}
