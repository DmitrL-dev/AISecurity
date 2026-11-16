package tools

import (
	"context"
	"testing"
	"time"

	"github.com/syntrex/gomcp/internal/domain/memory"
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func newTestDecayService(t *testing.T) (*DecayService, *sqlite.FactRepo) {
	t.Helper()
	db, err := sqlite.OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { db.Close() })
	repo, err := sqlite.NewFactRepo(db)
	require.NoError(t, err)
	return NewDecayService(repo), repo
}

func TestDecayService_Plan_ArchiveWhenParentExists(t *testing.T) {
	svc, repo := newTestDecayService(t)
	ctx := context.Background()

	parent := memory.NewFact("parent summary", memory.LevelModule, "conversation", "session-X")
	require.NoError(t, repo.Add(ctx, parent))

	child := memory.NewFact("child detail", memory.LevelModule, "conversation", "user-question")
	child.ParentID = parent.ID
	require.NoError(t, repo.Add(ctx, child))

	plan := svc.Plan(ctx, []*memory.Fact{child})
	assert.Len(t, plan.Archive, 1)
	assert.Equal(t, child.ID, plan.Archive[0].ID)
	assert.Empty(t, plan.Stale)
	assert.Contains(t, plan.Domains, "conversation")
}

func TestDecayService_Plan_StaleWhenNoParent(t *testing.T) {
	svc, repo := newTestDecayService(t)
	ctx := context.Background()

	orphan := memory.NewFact("orphan", memory.LevelDomain, "untracked", "")
	require.NoError(t, repo.Add(ctx, orphan))

	plan := svc.Plan(ctx, []*memory.Fact{orphan})
	assert.Empty(t, plan.Archive)
	require.Len(t, plan.Stale, 1)
	assert.Equal(t, orphan.ID, plan.Stale[0].ID)
}

func TestDecayService_Plan_StaleWhenParentMissing(t *testing.T) {
	svc, _ := newTestDecayService(t)
	ctx := context.Background()

	// We don't persist the fact — Plan() only needs to check whether the
	// parent_id resolves in the store, and the FK constraint would block
	// the insert anyway. This tests the "dangling reference" branch.
	child := memory.NewFact("dangling child", memory.LevelDomain, "broken", "")
	child.ParentID = "ghost-parent-id"

	plan := svc.Plan(ctx, []*memory.Fact{child})
	assert.Empty(t, plan.Archive)
	require.Len(t, plan.Stale, 1, "missing-parent fact must fall through to stale, not archive")
}

func TestDecayService_Apply_ArchivesAndMarksStale(t *testing.T) {
	svc, repo := newTestDecayService(t)
	ctx := context.Background()

	parent := memory.NewFact("p", memory.LevelDomain, "d1", "")
	require.NoError(t, repo.Add(ctx, parent))

	child := memory.NewFact("c", memory.LevelDomain, "d1", "")
	child.ParentID = parent.ID
	require.NoError(t, repo.Add(ctx, child))

	orphan := memory.NewFact("o", memory.LevelDomain, "d2", "")
	require.NoError(t, repo.Add(ctx, orphan))

	plan := svc.Plan(ctx, []*memory.Fact{child, orphan})
	res, err := svc.Apply(ctx, plan)
	require.NoError(t, err)
	assert.Equal(t, 2, res.Considered)
	assert.Equal(t, 1, res.Archived)
	assert.Equal(t, 1, res.Staled)

	// Verify state in store.
	gotChild, _ := repo.Get(ctx, child.ID)
	require.NotNil(t, gotChild)
	assert.True(t, gotChild.IsArchived)
	assert.False(t, gotChild.IsStale, "archive does not also imply stale")

	gotOrphan, _ := repo.Get(ctx, orphan.ID)
	require.NotNil(t, gotOrphan)
	assert.True(t, gotOrphan.IsStale)
	assert.False(t, gotOrphan.IsArchived)
}

func TestDecayService_Apply_RecomputesCentroids(t *testing.T) {
	svc, repo := newTestDecayService(t)
	ctx := context.Background()

	// Wire in a centroid service over the same DB.
	db, err := sqlite.OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { db.Close() })
	freshRepo, err := sqlite.NewFactRepo(db)
	require.NoError(t, err)
	centroidRepo, err := sqlite.NewCentroidRepo(db)
	require.NoError(t, err)
	centroidSvc := NewCentroidService(freshRepo, centroidRepo)

	// Seed: two embed-bearing facts in the same domain. Decay one.
	parent := memory.NewFact("p", memory.LevelDomain, "alpha", "")
	parent.Embedding = []float64{1, 0}
	require.NoError(t, freshRepo.Add(ctx, parent))

	child := memory.NewFact("c", memory.LevelDomain, "alpha", "")
	child.ParentID = parent.ID
	child.Embedding = []float64{0, 1}
	require.NoError(t, freshRepo.Add(ctx, child))

	// Build initial centroid (2 contributing facts).
	c0, err := centroidSvc.Recompute(ctx, "alpha")
	require.NoError(t, err)
	require.NotNil(t, c0)
	assert.Equal(t, 2, c0.FactCount)

	// Decay-via-Apply.
	decay := NewDecayService(freshRepo)
	decay.SetCentroidService(centroidSvc)
	plan := decay.Plan(ctx, []*memory.Fact{child})
	res, err := decay.Apply(ctx, plan)
	require.NoError(t, err)
	assert.Equal(t, 1, res.Archived)
	assert.GreaterOrEqual(t, res.CentroidsKept, 1, "centroid for alpha should still exist")

	// New centroid must reflect that only 1 fact contributes now.
	c1, err := centroidSvc.Recompute(ctx, "alpha")
	require.NoError(t, err)
	require.NotNil(t, c1)
	assert.Equal(t, 1, c1.FactCount)

	// Silence unused-variable warning for the original repo (different DB).
	_ = svc
	_ = repo
}

func TestDecayService_Decay_DryRun_DoesNotMutate(t *testing.T) {
	svc, repo := newTestDecayService(t)
	ctx := context.Background()

	old := memory.NewFact("old", memory.LevelDomain, "x", "")
	old.CreatedAt = time.Now().AddDate(0, 0, -120) // 120 days ago
	old.ValidFrom = old.CreatedAt
	require.NoError(t, repo.Add(ctx, old))

	res, err := svc.Decay(ctx, 90*24*time.Hour, true)
	require.NoError(t, err)
	assert.True(t, res.DryRun)
	assert.Equal(t, 1, res.Considered)
	assert.Equal(t, 1, res.Staled)

	// Original must remain untouched.
	got, _ := repo.Get(ctx, old.ID)
	require.NotNil(t, got)
	assert.False(t, got.IsStale)
	assert.False(t, got.IsArchived)
}

func TestDecayService_Decay_AppliesWhenNotDryRun(t *testing.T) {
	svc, repo := newTestDecayService(t)
	ctx := context.Background()

	old := memory.NewFact("old", memory.LevelDomain, "x", "")
	old.CreatedAt = time.Now().AddDate(0, 0, -120)
	old.ValidFrom = old.CreatedAt
	require.NoError(t, repo.Add(ctx, old))

	res, err := svc.Decay(ctx, 90*24*time.Hour, false)
	require.NoError(t, err)
	assert.False(t, res.DryRun)
	assert.Equal(t, 1, res.Staled)

	got, _ := repo.Get(ctx, old.ID)
	require.NotNil(t, got)
	assert.True(t, got.IsStale)
}

func TestDecayService_Decay_SkipsRecentFacts(t *testing.T) {
	svc, repo := newTestDecayService(t)
	ctx := context.Background()

	// Newer than the underlying GetColdFacts 30-day floor — must not appear.
	recent := memory.NewFact("recent", memory.LevelDomain, "x", "")
	recent.CreatedAt = time.Now().AddDate(0, 0, -10)
	recent.ValidFrom = recent.CreatedAt
	require.NoError(t, repo.Add(ctx, recent))

	res, err := svc.Decay(ctx, 90*24*time.Hour, false)
	require.NoError(t, err)
	assert.Equal(t, 0, res.Considered)
}

func TestDecayService_Plan_NilFactSafe(t *testing.T) {
	svc, _ := newTestDecayService(t)
	plan := svc.Plan(context.Background(), []*memory.Fact{nil, nil})
	assert.Empty(t, plan.Archive)
	assert.Empty(t, plan.Stale)
}
