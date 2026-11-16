package sqlite

import (
	"context"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func newTestConversationRepo(t *testing.T) *ConversationLogRepo {
	t.Helper()
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { db.Close() })

	repo, err := NewConversationLogRepo(db)
	require.NoError(t, err)
	return repo
}

func TestConversationLogRepo_RecordAndGetSession(t *testing.T) {
	repo := newTestConversationRepo(t)
	ctx := context.Background()

	now := time.Now().UTC()
	require.NoError(t, repo.Record(ctx, ConversationEntry{
		SessionID: "sess-1", Role: "user", Content: "hello", MsgIndex: 0, Timestamp: now,
	}))
	require.NoError(t, repo.Record(ctx, ConversationEntry{
		SessionID: "sess-1", Role: "assistant", Content: "hi back", MsgIndex: 1, Timestamp: now.Add(time.Second),
	}))
	require.NoError(t, repo.Record(ctx, ConversationEntry{
		SessionID: "sess-2", Role: "user", Content: "other session", MsgIndex: 0, Timestamp: now,
	}))

	got, err := repo.GetSession(ctx, "sess-1")
	require.NoError(t, err)
	require.Len(t, got, 2)
	assert.Equal(t, "user", got[0].Role)
	assert.Equal(t, "hello", got[0].Content)
	assert.Equal(t, "assistant", got[1].Role)
	assert.Equal(t, 1, got[1].MsgIndex)
}

func TestConversationLogRepo_RecordIsIdempotent(t *testing.T) {
	repo := newTestConversationRepo(t)
	ctx := context.Background()

	entry := ConversationEntry{SessionID: "s", Role: "user", Content: "x", MsgIndex: 0}
	require.NoError(t, repo.Record(ctx, entry))
	// Same (session_id, msg_index) — must be silently ignored.
	require.NoError(t, repo.Record(ctx, entry))

	got, err := repo.GetSession(ctx, "s")
	require.NoError(t, err)
	assert.Len(t, got, 1, "duplicate (session_id, msg_index) must not create a second row")
}

func TestConversationLogRepo_Record_ValidationErrors(t *testing.T) {
	repo := newTestConversationRepo(t)
	ctx := context.Background()

	err := repo.Record(ctx, ConversationEntry{SessionID: "", Role: "user", Content: "x"})
	assert.Error(t, err, "empty session_id must error")

	err = repo.Record(ctx, ConversationEntry{SessionID: "s", Role: "", Content: "x"})
	assert.Error(t, err, "empty role must error")
}

func TestConversationLogRepo_RecordBatch(t *testing.T) {
	repo := newTestConversationRepo(t)
	ctx := context.Background()

	now := time.Now().UTC()
	batch := []ConversationEntry{
		{SessionID: "b", Role: "user", Content: "1", MsgIndex: 0, Timestamp: now},
		{SessionID: "b", Role: "assistant", Content: "2", MsgIndex: 1, Timestamp: now},
		{SessionID: "b", Role: "user", Content: "3", MsgIndex: 2, Timestamp: now},
	}

	n, err := repo.RecordBatch(ctx, batch)
	require.NoError(t, err)
	assert.Equal(t, 3, n)

	// Re-running the same batch must report 0 new inserts (all duplicates).
	n, err = repo.RecordBatch(ctx, batch)
	require.NoError(t, err)
	assert.Equal(t, 0, n)

	got, err := repo.GetSession(ctx, "b")
	require.NoError(t, err)
	assert.Len(t, got, 3)
}

func TestConversationLogRepo_RecordBatch_EmptyIsNoop(t *testing.T) {
	repo := newTestConversationRepo(t)
	n, err := repo.RecordBatch(context.Background(), nil)
	require.NoError(t, err)
	assert.Equal(t, 0, n)
}

func TestConversationLogRepo_Undistilled_And_MarkDistilled(t *testing.T) {
	repo := newTestConversationRepo(t)
	ctx := context.Background()

	now := time.Now().UTC()
	for i := 0; i < 5; i++ {
		require.NoError(t, repo.Record(ctx, ConversationEntry{
			SessionID: "s", Role: "user", Content: "msg",
			MsgIndex: i, Timestamp: now.Add(time.Duration(i) * time.Second),
		}))
	}

	und, err := repo.GetUndistilled(ctx, 100)
	require.NoError(t, err)
	require.Len(t, und, 5)

	ids := []int64{und[0].ID, und[1].ID}
	require.NoError(t, repo.MarkDistilled(ctx, ids))

	und2, err := repo.GetUndistilled(ctx, 100)
	require.NoError(t, err)
	assert.Len(t, und2, 3, "two should now be distilled, three remain")
}

func TestConversationLogRepo_GetUndistilled_RespectsLimit(t *testing.T) {
	repo := newTestConversationRepo(t)
	ctx := context.Background()
	for i := 0; i < 10; i++ {
		_ = repo.Record(ctx, ConversationEntry{
			SessionID: "x", Role: "user", Content: "m", MsgIndex: i,
		})
	}
	und, err := repo.GetUndistilled(ctx, 4)
	require.NoError(t, err)
	assert.Len(t, und, 4)
}

func TestConversationLogRepo_Prune_OnlyDistilled(t *testing.T) {
	repo := newTestConversationRepo(t)
	ctx := context.Background()

	old := time.Now().UTC().Add(-48 * time.Hour)
	require.NoError(t, repo.Record(ctx, ConversationEntry{
		SessionID: "p", Role: "user", Content: "old-distilled", MsgIndex: 0, Timestamp: old, Distilled: true,
	}))
	require.NoError(t, repo.Record(ctx, ConversationEntry{
		SessionID: "p", Role: "user", Content: "old-undistilled", MsgIndex: 1, Timestamp: old, Distilled: false,
	}))
	require.NoError(t, repo.Record(ctx, ConversationEntry{
		SessionID: "p", Role: "user", Content: "fresh-distilled", MsgIndex: 2,
		Timestamp: time.Now().UTC(), Distilled: true,
	}))

	deleted, err := repo.Prune(ctx, 24*time.Hour)
	require.NoError(t, err)
	assert.Equal(t, int64(1), deleted, "only the old AND distilled entry should be pruned")

	remaining, err := repo.GetSession(ctx, "p")
	require.NoError(t, err)
	assert.Len(t, remaining, 2)
}

func TestConversationLogRepo_Stats(t *testing.T) {
	repo := newTestConversationRepo(t)
	ctx := context.Background()

	type seed struct {
		sid string
		idx int
	}
	for _, s := range []seed{{"a", 0}, {"a", 1}, {"b", 0}, {"b", 1}, {"b", 2}} {
		require.NoError(t, repo.Record(ctx, ConversationEntry{
			SessionID: s.sid, Role: "user", Content: "m", MsgIndex: s.idx,
		}))
	}

	stats, err := repo.Stats(ctx)
	require.NoError(t, err)
	assert.Equal(t, 5, stats.TotalMessages)
	assert.Equal(t, 2, stats.TotalSessions)
	assert.Equal(t, 5, stats.UndistilledRows)
}
