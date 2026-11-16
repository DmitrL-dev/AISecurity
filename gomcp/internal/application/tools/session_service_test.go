package tools

import (
	"context"
	"testing"

	"github.com/syntrex/gomcp/internal/domain/session"
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func newTestSessionService(t *testing.T) *SessionService {
	t.Helper()
	db, err := sqlite.OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { db.Close() })

	repo, err := sqlite.NewStateRepo(db)
	require.NoError(t, err)

	return NewSessionService(repo)
}

func TestSessionService_SaveState_LoadState(t *testing.T) {
	svc := newTestSessionService(t)
	ctx := context.Background()

	state := session.NewCognitiveStateVector("test-session")
	state.SetGoal("Build GoMCP", 0.3)
	state.AddFact("Go 1.25", "requirement", 1.0)

	require.NoError(t, svc.SaveState(ctx, state))

	loaded, checksum, err := svc.LoadState(ctx, "test-session", nil)
	require.NoError(t, err)
	require.NotNil(t, loaded)
	assert.NotEmpty(t, checksum)
	assert.Equal(t, "Build GoMCP", loaded.PrimaryGoal.Description)
}

func TestSessionService_ListSessions(t *testing.T) {
	svc := newTestSessionService(t)
	ctx := context.Background()

	s1 := session.NewCognitiveStateVector("s1")
	s2 := session.NewCognitiveStateVector("s2")
	require.NoError(t, svc.SaveState(ctx, s1))
	require.NoError(t, svc.SaveState(ctx, s2))

	sessions, err := svc.ListSessions(ctx)
	require.NoError(t, err)
	assert.Len(t, sessions, 2)
}

func TestSessionService_DeleteSession(t *testing.T) {
	svc := newTestSessionService(t)
	ctx := context.Background()

	state := session.NewCognitiveStateVector("to-delete")
	require.NoError(t, svc.SaveState(ctx, state))

	count, err := svc.DeleteSession(ctx, "to-delete")
	require.NoError(t, err)
	assert.Equal(t, 1, count)
}

func TestSessionService_RestoreOrCreate_New(t *testing.T) {
	svc := newTestSessionService(t)
	ctx := context.Background()

	state, restored, err := svc.RestoreOrCreate(ctx, "new-session")
	require.NoError(t, err)
	assert.False(t, restored)
	assert.Equal(t, "new-session", state.SessionID)
}

func TestSessionService_RestoreOrCreate_Existing(t *testing.T) {
	svc := newTestSessionService(t)
	ctx := context.Background()

	original := session.NewCognitiveStateVector("existing")
	original.SetGoal("Saved goal", 0.5)
	require.NoError(t, svc.SaveState(ctx, original))

	state, restored, err := svc.RestoreOrCreate(ctx, "existing")
	require.NoError(t, err)
	assert.True(t, restored)
	assert.Equal(t, "Saved goal", state.PrimaryGoal.Description)
}

func TestSessionService_GetCompactState(t *testing.T) {
	svc := newTestSessionService(t)
	ctx := context.Background()

	state := session.NewCognitiveStateVector("compact")
	state.SetGoal("Test compact", 0.5)
	state.AddFact("fact1", "requirement", 1.0)
	require.NoError(t, svc.SaveState(ctx, state))

	compact, err := svc.GetCompactState(ctx, "compact", 500)
	require.NoError(t, err)
	assert.Contains(t, compact, "Test compact")
	assert.Contains(t, compact, "fact1")
}

func TestSessionService_GetAuditLog(t *testing.T) {
	svc := newTestSessionService(t)
	ctx := context.Background()

	state := session.NewCognitiveStateVector("audited")
	require.NoError(t, svc.SaveState(ctx, state))

	log, err := svc.GetAuditLog(ctx, "audited", 10)
	require.NoError(t, err)
	assert.GreaterOrEqual(t, len(log), 1)
}
