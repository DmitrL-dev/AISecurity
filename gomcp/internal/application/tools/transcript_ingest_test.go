package tools

import (
	"context"
	"strings"
	"testing"

	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func newTestConvRepo(t *testing.T) *sqlite.ConversationLogRepo {
	t.Helper()
	db, err := sqlite.OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { db.Close() })
	repo, err := sqlite.NewConversationLogRepo(db)
	require.NoError(t, err)
	return repo
}

const claudeFixture = `{"type":"permission-mode","permissionMode":"default","sessionId":"S1"}
{"type":"file-history-snapshot","messageId":"abc","snapshot":{}}
{"type":"user","sessionId":"S1","timestamp":"2026-05-08T10:00:00.000Z","uuid":"u1","message":{"role":"user","content":"привет"}}
{"type":"attachment","sessionId":"S1","attachment":{"type":"skill_listing"}}
{"type":"assistant","sessionId":"S1","timestamp":"2026-05-08T10:00:01.000Z","uuid":"a1","message":{"role":"assistant","content":[{"type":"text","text":"Здравствуй"},{"type":"tool_use","id":"t1","name":"Bash","input":{}},{"type":"text","text":"!"}]}}
{"type":"user","sessionId":"S1","timestamp":"2026-05-08T10:00:02.000Z","uuid":"u2","message":{"role":"user","content":"как дела"}}
{"type":"assistant","sessionId":"S1","timestamp":"2026-05-08T10:00:03.000Z","uuid":"a2","message":{"role":"assistant","content":[{"type":"text","text":""}]}}
`

func TestIngestReader_ParsesUserAndAssistant(t *testing.T) {
	repo := newTestConvRepo(t)
	ctx := context.Background()

	res, err := ingestReader(ctx, repo, strings.NewReader(claudeFixture), "")
	require.NoError(t, err)

	// Expected: 2 user + 1 assistant (the empty-text assistant is skipped).
	assert.Equal(t, "S1", res.SessionID)
	assert.Equal(t, 3, res.Inserted)
	// Skipped: permission-mode, file-history-snapshot, attachment, empty assistant = 4
	assert.Equal(t, 4, res.Skipped)
	assert.Equal(t, 0, res.Duplicates)

	got, err := repo.GetSession(ctx, "S1")
	require.NoError(t, err)
	require.Len(t, got, 3)

	// First message: user "привет"
	assert.Equal(t, "user", got[0].Role)
	assert.Equal(t, "привет", got[0].Content)
	assert.Equal(t, 0, got[0].MsgIndex)

	// Second message: assistant with two text blocks merged.
	assert.Equal(t, "assistant", got[1].Role)
	assert.Contains(t, got[1].Content, "Здравствуй")
	assert.Contains(t, got[1].Content, "!")
	assert.NotContains(t, got[1].Content, "tool_use", "non-text blocks must be dropped")
	assert.Equal(t, 1, got[1].MsgIndex)

	// Third message: second user.
	assert.Equal(t, "user", got[2].Role)
	assert.Equal(t, "как дела", got[2].Content)
	assert.Equal(t, 2, got[2].MsgIndex)

	// UUID metadata is captured.
	assert.Contains(t, got[0].Metadata, "u1")
}

func TestIngestReader_IsIdempotent(t *testing.T) {
	repo := newTestConvRepo(t)
	ctx := context.Background()

	_, err := ingestReader(ctx, repo, strings.NewReader(claudeFixture), "")
	require.NoError(t, err)

	res, err := ingestReader(ctx, repo, strings.NewReader(claudeFixture), "")
	require.NoError(t, err)
	assert.Equal(t, 0, res.Inserted, "second ingest must insert nothing new")
	assert.Equal(t, 3, res.Duplicates)

	got, err := repo.GetSession(ctx, "S1")
	require.NoError(t, err)
	assert.Len(t, got, 3, "no duplicates in DB")
}

func TestIngestReader_SessionOverride(t *testing.T) {
	repo := newTestConvRepo(t)
	ctx := context.Background()

	res, err := ingestReader(ctx, repo, strings.NewReader(claudeFixture), "OVERRIDE")
	require.NoError(t, err)
	assert.Equal(t, "OVERRIDE", res.SessionID)

	got, err := repo.GetSession(ctx, "OVERRIDE")
	require.NoError(t, err)
	assert.Len(t, got, 3)

	// Original sessionId in transcript must NOT have been used.
	got2, err := repo.GetSession(ctx, "S1")
	require.NoError(t, err)
	assert.Empty(t, got2)
}

func TestIngestReader_HandlesMalformedLines(t *testing.T) {
	repo := newTestConvRepo(t)
	ctx := context.Background()

	mixed := `not-json-at-all
{"type":"user","sessionId":"S2","message":{"role":"user","content":"valid"}}
{broken json
`
	res, err := ingestReader(ctx, repo, strings.NewReader(mixed), "")
	require.NoError(t, err, "malformed lines must not abort the whole ingest")
	assert.Equal(t, 1, res.Inserted)
	assert.Equal(t, 2, res.Skipped)
}

func TestIngestReader_StringContentForAssistant(t *testing.T) {
	// Some clients emit assistant content as a plain string. Must still parse.
	repo := newTestConvRepo(t)
	ctx := context.Background()

	doc := `{"type":"assistant","sessionId":"S3","message":{"role":"assistant","content":"plain string answer"}}` + "\n"
	res, err := ingestReader(ctx, repo, strings.NewReader(doc), "")
	require.NoError(t, err)
	assert.Equal(t, 1, res.Inserted)

	got, err := repo.GetSession(ctx, "S3")
	require.NoError(t, err)
	require.Len(t, got, 1)
	assert.Equal(t, "plain string answer", got[0].Content)
}
