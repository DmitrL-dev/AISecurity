package sqlite

import (
	"context"
	"testing"

	"github.com/sentinel-community/gomcp/internal/domain/session"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func newTestStateRepo(t *testing.T) *StateRepo {
	t.Helper()
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { db.Close() })

	repo, err := NewStateRepo(db)
	require.NoError(t, err)
	return repo
}

func TestStateRepo_Save_Load(t *testing.T) {
	repo := newTestStateRepo(t)
	ctx := context.Background()

	csv := session.NewCognitiveStateVector("test-session")
	csv.SetGoal("Build GoMCP", 0.3)
	csv.AddHypothesis("SQLite is fast enough")
	csv.AddDecision("Use mcp-go", "mature lib", []string{"custom"})
	csv.AddFact("Go 1.25", "requirement", 1.0)

	checksum := csv.Checksum()
	err := repo.Save(ctx, csv, checksum)
	require.NoError(t, err)

	loaded, gotChecksum, err := repo.Load(ctx, "test-session", nil)
	require.NoError(t, err)
	require.NotNil(t, loaded)

	assert.Equal(t, csv.SessionID, loaded.SessionID)
	assert.Equal(t, csv.Version, loaded.Version)
	assert.Equal(t, checksum, gotChecksum)
	require.NotNil(t, loaded.PrimaryGoal)
	assert.Equal(t, "Build GoMCP", loaded.PrimaryGoal.Description)
	assert.Len(t, loaded.Hypotheses, 1)
	assert.Len(t, loaded.Decisions, 1)
	assert.Len(t, loaded.Facts, 1)
}

func TestStateRepo_Save_Versioning(t *testing.T) {
	repo := newTestStateRepo(t)
	ctx := context.Background()

	csv := session.NewCognitiveStateVector("s1")
	csv.SetGoal("v1", 0.1)
	require.NoError(t, repo.Save(ctx, csv, csv.Checksum()))

	csv.BumpVersion()
	csv.SetGoal("v2", 0.5)
	require.NoError(t, repo.Save(ctx, csv, csv.Checksum()))

	// Load latest
	loaded, _, err := repo.Load(ctx, "s1", nil)
	require.NoError(t, err)
	assert.Equal(t, 2, loaded.Version)
	assert.Equal(t, "v2", loaded.PrimaryGoal.Description)

	// Load specific version
	v := 1
	loaded, _, err = repo.Load(ctx, "s1", &v)
	require.NoError(t, err)
	assert.Equal(t, 1, loaded.Version)
	assert.Equal(t, "v1", loaded.PrimaryGoal.Description)
}

func TestStateRepo_Load_NotFound(t *testing.T) {
	repo := newTestStateRepo(t)
	ctx := context.Background()

	loaded, _, err := repo.Load(ctx, "nonexistent", nil)
	assert.Error(t, err)
	assert.Nil(t, loaded)
}

func TestStateRepo_ListSessions(t *testing.T) {
	repo := newTestStateRepo(t)
	ctx := context.Background()

	s1 := session.NewCognitiveStateVector("session-1")
	s2 := session.NewCognitiveStateVector("session-2")
	require.NoError(t, repo.Save(ctx, s1, s1.Checksum()))
	require.NoError(t, repo.Save(ctx, s2, s2.Checksum()))

	sessions, err := repo.ListSessions(ctx)
	require.NoError(t, err)
	assert.Len(t, sessions, 2)
}

func TestStateRepo_DeleteSession(t *testing.T) {
	repo := newTestStateRepo(t)
	ctx := context.Background()

	csv := session.NewCognitiveStateVector("to-delete")
	require.NoError(t, repo.Save(ctx, csv, csv.Checksum()))

	csv.BumpVersion()
	require.NoError(t, repo.Save(ctx, csv, csv.Checksum()))

	count, err := repo.DeleteSession(ctx, "to-delete")
	require.NoError(t, err)
	assert.Equal(t, 2, count)

	loaded, _, err := repo.Load(ctx, "to-delete", nil)
	assert.Error(t, err)
	assert.Nil(t, loaded)
}

func TestStateRepo_AuditLog(t *testing.T) {
	repo := newTestStateRepo(t)
	ctx := context.Background()

	csv := session.NewCognitiveStateVector("audited")
	require.NoError(t, repo.Save(ctx, csv, csv.Checksum()))

	csv.BumpVersion()
	require.NoError(t, repo.Save(ctx, csv, csv.Checksum()))

	log, err := repo.GetAuditLog(ctx, "audited", 10)
	require.NoError(t, err)
	assert.GreaterOrEqual(t, len(log), 2)
	assert.Equal(t, "audited", log[0].SessionID)
}

func TestStateRepo_ComplexState_RoundTrip(t *testing.T) {
	repo := newTestStateRepo(t)
	ctx := context.Background()

	csv := session.NewCognitiveStateVector("complex")
	csv.SetGoal("Build full system", 0.7)
	csv.AddHypothesis("H1")
	csv.AddHypothesis("H2")
	csv.AddDecision("D1", "R1", []string{"A1", "A2"})
	csv.AddDecision("D2", "R2", nil)
	csv.AddFact("F1", "requirement", 0.9)
	csv.AddFact("F2", "decision", 1.0)
	csv.AddFact("F3", "context", 0.5)
	csv.OpenQuestions = []string{"Q1", "Q2", "Q3"}
	csv.ConfidenceMap["area1"] = 0.8
	csv.ConfidenceMap["area2"] = 0.3

	require.NoError(t, repo.Save(ctx, csv, csv.Checksum()))

	loaded, _, err := repo.Load(ctx, "complex", nil)
	require.NoError(t, err)

	assert.Equal(t, "Build full system", loaded.PrimaryGoal.Description)
	assert.Len(t, loaded.Hypotheses, 2)
	assert.Len(t, loaded.Decisions, 2)
	assert.Len(t, loaded.Facts, 3)
	assert.Len(t, loaded.OpenQuestions, 3)
	assert.InDelta(t, 0.8, loaded.ConfidenceMap["area1"], 0.001)
}
