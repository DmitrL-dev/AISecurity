package tools

import (
	"context"
	"errors"
	"strings"
	"testing"
	"time"

	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// newTestDistiller wires a real in-memory FactRepo + ConversationLogRepo.
func newTestDistiller(t *testing.T) (*DistillerService, *sqlite.ConversationLogRepo, *sqlite.FactRepo) {
	t.Helper()
	db, err := sqlite.OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { db.Close() })
	factRepo, err := sqlite.NewFactRepo(db)
	require.NoError(t, err)
	convRepo, err := sqlite.NewConversationLogRepo(db)
	require.NoError(t, err)
	return NewDistillerService(convRepo, factRepo), convRepo, factRepo
}

func seedSession(t *testing.T, conv *sqlite.ConversationLogRepo, sid string, msgs []sqlite.ConversationEntry) {
	t.Helper()
	for i, m := range msgs {
		m.SessionID = sid
		m.MsgIndex = i
		require.NoError(t, conv.Record(distillerTestContext(), m))
	}
}

func distillerTestContext() context.Context {
	return rlmscope.WithScope(context.Background(), rlmscope.New("local", "distiller-test"))
}

func listDistilledSessionFacts(t *testing.T, facts *sqlite.FactRepo, ctx context.Context, sessionID string) []*memory.Fact {
	t.Helper()
	all, err := facts.ListForSession(ctx, sessionID, false)
	require.NoError(t, err)
	return all
}

func TestDistillerService_DistillSession_BasicSummary(t *testing.T) {
	svc, conv, facts := newTestDistiller(t)
	ctx := distillerTestContext()

	now := time.Now().UTC()
	seedSession(t, conv, "sess-A", []sqlite.ConversationEntry{
		{Role: "user", Content: "what is X?", Timestamp: now},
		{Role: "assistant", Content: "X is a thing.", Timestamp: now.Add(time.Second)},
		{Role: "user", Content: "thanks", Timestamp: now.Add(2 * time.Second)},
	})

	res, err := svc.DistillSession(ctx, "sess-A")
	require.NoError(t, err)
	assert.Equal(t, 1, res.SessionsProcessed)
	assert.Equal(t, 1, res.SummaryFactsAdded)
	assert.Equal(t, 0, res.QuestionFactsAdded, "all user msgs short — no L3 question facts")
	assert.Equal(t, 3, res.MessagesMarked)

	// Summary fact must exist with the right shape.
	all := listDistilledSessionFacts(t, facts, ctx, "sess-A")
	require.Len(t, all, 1)
	summary := all[0]
	assert.Equal(t, memory.LevelModule, summary.Level)
	assert.Contains(t, summary.Module, "session-")
	assert.Contains(t, summary.Content, "Session sess-A")
	assert.Contains(t, summary.Content, "3 messages")
	assert.Contains(t, summary.Content, "what is X?")
	assert.Equal(t, "auto:distill", summary.Source)
	assert.Equal(t, "sess-A", summary.SessionID)

	// Conversation messages must be marked distilled.
	und, err := conv.GetUndistilled(ctx, 100)
	require.NoError(t, err)
	assert.Empty(t, und)
}

func TestDistillerService_DistillSession_PromotesLongUserQuestions(t *testing.T) {
	svc, conv, facts := newTestDistiller(t)
	ctx := distillerTestContext()

	long := "Q: " + strings.Repeat("это длинный вопрос про архитектуру системы и что нам делать дальше. ", 5)
	require.True(t, len([]rune(long)) >= QuestionMinChars)

	seedSession(t, conv, "sess-B", []sqlite.ConversationEntry{
		{Role: "user", Content: long, Timestamp: time.Now().UTC()},
		{Role: "assistant", Content: "ответ", Timestamp: time.Now().UTC().Add(time.Second)},
	})

	res, err := svc.DistillSession(ctx, "sess-B")
	require.NoError(t, err)
	assert.Equal(t, 1, res.SummaryFactsAdded)
	assert.Equal(t, 1, res.QuestionFactsAdded)

	all := listDistilledSessionFacts(t, facts, ctx, "sess-B")
	require.Len(t, all, 2)

	// Find the question fact (module = "user-question").
	var qf *memory.Fact
	var sf *memory.Fact
	for _, f := range all {
		if f.Module == "user-question" {
			qf = f
		} else {
			sf = f
		}
	}
	require.NotNil(t, qf)
	require.NotNil(t, sf)
	assert.Equal(t, sf.ID, qf.ParentID, "question fact must hang off the summary fact")
	assert.Equal(t, "auto:distill", qf.Source)
}

func TestDistillerService_DoesNotConsumeMessagesWhenQuestionStoreFails(t *testing.T) {
	_, conv, facts := newTestDistiller(t)
	ctx := distillerTestContext()
	long := "Q: " + strings.Repeat("это существенный вопрос, который нельзя потерять при ошибке хранилища. ", 5)
	seedSession(t, conv, "sess-question-failure", []sqlite.ConversationEntry{
		{Role: "user", Content: long, Timestamp: time.Now().UTC()},
		{Role: "assistant", Content: "ответ", Timestamp: time.Now().UTC().Add(time.Second)},
	})

	failing := &failNthSessionFactStore{
		FactStore:        facts,
		SessionFactStore: facts,
		failAt:           2,
	}
	svc := NewDistillerService(conv, failing)
	res, err := svc.DistillSession(ctx, "sess-question-failure")
	require.ErrorContains(t, err, "add question fact")
	require.Equal(t, 0, res.MessagesMarked)

	undistilled, err := conv.GetUndistilled(ctx, 100)
	require.NoError(t, err)
	require.Len(t, undistilled, 2, "source messages must remain retryable")

	stored := listDistilledSessionFacts(t, facts, ctx, "sess-question-failure")
	require.Len(t, stored, 1, "the successful summary may remain for idempotent retry")

	failing.failAt = 0
	res, err = svc.DistillSession(ctx, "sess-question-failure")
	require.NoError(t, err)
	require.Equal(t, 2, res.MessagesMarked)
	require.Len(t, listDistilledSessionFacts(t, facts, ctx, "sess-question-failure"), 2,
		"retry must fold the summary and store the missing question exactly once")
}

func TestDistillerService_PropagatesMarkDistilledFailure(t *testing.T) {
	svc, conv, _ := newTestDistiller(t)
	ctx := distillerTestContext()
	seedSession(t, conv, "sess-mark-failure", []sqlite.ConversationEntry{
		{Role: "system", Content: "transient metadata", Timestamp: time.Now().UTC()},
	})
	svc.conversations = &failingMarkDistilledStore{
		ConversationLogRepo: conv,
		err:                 errors.New("mark write failed"),
	}

	res, err := svc.DistillSession(ctx, "sess-mark-failure")
	require.ErrorContains(t, err, "mark trivial session distilled")
	require.ErrorContains(t, err, "mark write failed")
	require.Zero(t, res.MessagesMarked)

	undistilled, queryErr := conv.GetUndistilled(ctx, 100)
	require.NoError(t, queryErr)
	require.Len(t, undistilled, 1, "failed marking must not be reported as consumed")
}

func TestDistillerService_DistillSession_Idempotent(t *testing.T) {
	svc, conv, facts := newTestDistiller(t)
	ctx := distillerTestContext()

	seedSession(t, conv, "sess-C", []sqlite.ConversationEntry{
		{Role: "user", Content: "hi", Timestamp: time.Now().UTC()},
	})

	_, err := svc.DistillSession(ctx, "sess-C")
	require.NoError(t, err)

	res, err := svc.DistillSession(ctx, "sess-C")
	require.NoError(t, err)
	assert.Equal(t, 0, res.SessionsProcessed, "second call must be no-op when nothing undistilled")
	assert.Equal(t, 0, res.SummaryFactsAdded)

	all := listDistilledSessionFacts(t, facts, ctx, "sess-C")
	assert.Len(t, all, 1, "no duplicate summary fact created")
}

func TestDistillerService_DistillSession_RequiresSessionID(t *testing.T) {
	svc, _, _ := newTestDistiller(t)
	_, err := svc.DistillSession(distillerTestContext(), "")
	assert.Error(t, err)
}

func TestDistillerService_FailsClosedWithoutExplicitScope(t *testing.T) {
	svc, _, _ := newTestDistiller(t)
	_, err := svc.DistillSession(context.Background(), "sess-A")
	require.ErrorContains(t, err, "explicit tenant_id/project_id")
	_, err = svc.DistillBatch(context.Background(), time.Hour, 50)
	require.ErrorContains(t, err, "explicit tenant_id/project_id")
}

func TestDistillerService_RejectsReservedLegacyProject(t *testing.T) {
	svc, _, _ := newTestDistiller(t)
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "DEFAULT"))

	_, err := svc.DistillSession(ctx, "sess-A")
	require.ErrorContains(t, err, "reserved for legacy memory")
	_, err = svc.DistillBatch(ctx, time.Hour, 50)
	require.ErrorContains(t, err, "reserved for legacy memory")
}

func TestDistillerService_DistillBatch_OnlyIdleSessions(t *testing.T) {
	svc, conv, facts := newTestDistiller(t)
	ctx := distillerTestContext()

	// Idle session (latest message > 1 hour ago).
	idleStart := time.Now().UTC().Add(-2 * time.Hour)
	seedSession(t, conv, "idle", []sqlite.ConversationEntry{
		{Role: "user", Content: "hi", Timestamp: idleStart},
		{Role: "assistant", Content: "hi back", Timestamp: idleStart.Add(time.Second)},
	})

	// Active session (latest message just now).
	seedSession(t, conv, "active", []sqlite.ConversationEntry{
		{Role: "user", Content: "still here", Timestamp: time.Now().UTC()},
	})

	res, err := svc.DistillBatch(ctx, time.Hour, 100)
	require.NoError(t, err)
	assert.Equal(t, 1, res.SessionsProcessed)
	assert.Equal(t, []string{"idle"}, res.Sessions)

	// Active session's messages must remain undistilled.
	und, err := conv.GetUndistilled(ctx, 100)
	require.NoError(t, err)
	require.Len(t, und, 1)
	assert.Equal(t, "active", und[0].SessionID)

	// Only one summary fact created.
	all := listDistilledSessionFacts(t, facts, ctx, "idle")
	assert.Len(t, all, 1)
}

func TestDistillerService_DistillBatch_EmptyWhenNothingUndistilled(t *testing.T) {
	svc, _, _ := newTestDistiller(t)
	res, err := svc.DistillBatch(distillerTestContext(), time.Hour, 50)
	require.NoError(t, err)
	assert.Equal(t, 0, res.SessionsProcessed)
}

func TestDistillerService_WithEmbedder_AttachesVector(t *testing.T) {
	svc, conv, facts := newTestDistiller(t)
	ctx := distillerTestContext()
	svc.SetEmbedder(&stubEmbedder{
		dim:   4,
		embed: func(string) []float64 { return []float64{0.1, 0.2, 0.3, 0.4} },
	})

	seedSession(t, conv, "sess-E", []sqlite.ConversationEntry{
		{Role: "user", Content: "embed me", Timestamp: time.Now().UTC()},
	})

	_, err := svc.DistillSession(ctx, "sess-E")
	require.NoError(t, err)

	all := listDistilledSessionFacts(t, facts, ctx, "sess-E")
	require.Len(t, all, 1)
	assert.Equal(t, []float64{0.1, 0.2, 0.3, 0.4}, all[0].Embedding,
		"summary fact must carry an embedding when one is configured")
}

func TestTrimPreview_HandlesUnicode(t *testing.T) {
	s := "слово1   слово2\nслово3\t\tслово4"
	out := trimPreview(s, 100)
	assert.Equal(t, "слово1 слово2 слово3 слово4", out)

	long := strings.Repeat("я", 300)
	out = trimPreview(long, 50)
	assert.Equal(t, 51, len([]rune(out)), "should be truncated to 50 runes + ellipsis")
}

type failNthSessionFactStore struct {
	memory.FactStore
	memory.SessionFactStore
	failAt int
	calls  int
}

func (s *failNthSessionFactStore) AddForSession(ctx context.Context, sessionID string, fact *memory.Fact) error {
	s.calls++
	if s.failAt > 0 && s.calls == s.failAt {
		return errors.New("session fact write failed")
	}
	return s.SessionFactStore.AddForSession(ctx, sessionID, fact)
}

type failingMarkDistilledStore struct {
	*sqlite.ConversationLogRepo
	err error
}

func (s *failingMarkDistilledStore) MarkDistilled(context.Context, []int64) error {
	return s.err
}

// The two numbers this service actually has, and why one number was the wrong answer.
//
// Until 2026-08-05 nothing measured what distillation saves: `DistillResult` counts sessions,
// facts and marked messages, and neither the README nor the CHANGELOG carried a figure. So when a
// competing product announced «~60% fewer tokens» there was no way to answer whether ours does
// better, worse, or the same, while the mechanism had been shipping for months.
//
// The first attempt at a figure produced 89.5%, on a fixture whose assistant turns repeated one
// sentence four times — measuring the fixture's own redundancy, not the distiller. Made
// non-repetitive, the same test measured 28.1% and failed its own floor.
//
// Both numbers were right and both were useless, because a single ratio averages two behaviours
// that are opposites by design:
//
//   - **Transient material** — assistant turns and short messages — is REPLACED by one summary.
//     That is compression, and it is what the distiller is for.
//   - **User questions over QuestionMinChars (200) are PROMOTED**, near-verbatim, into their own
//     L3 facts. That is retention, deliberately: a substantial question from a person is the
//     valuable part of a session and losing it would be the defect.
//
// So a session of terse exchanges compresses enormously and a session of long questions barely
// compresses at all, and the mixed ratio says only which kind of session the fixture happened to
// be. The two are measured separately below, and the floor sits on the half the distiller is
// responsible for.
//
// Unit, stated because it would otherwise be assumed: runes, not tokens — tokenisation is
// model-specific and no tokeniser is vendored here. And representation, not storage: raw messages
// stay in `conversation_log` until pruned, so this is what the Proactive Context Engine would
// inject INSTEAD of the raw history, not a disk figure.

// terseSession returns a session whose user messages stay below the promotion threshold, so
// nothing is retained verbatim and the summary replaces the lot.
func terseSession(now time.Time) []sqlite.ConversationEntry {
	findings := []string{
		"подпись сверяется раньше срока действия",
		"клиент ждёт дольше, чем провайдер держит соединение",
		"агрегат считает попытки, а отчёт — успешные вызовы",
		"при равной специфичности порядок правил не определён",
		"инвалидация помечает запись, не удаляя её",
		"идентификаторы усечены до шестнадцати символов",
	}
	var msgs []sqlite.ConversationEntry
	for i, finding := range findings {
		msgs = append(msgs,
			sqlite.ConversationEntry{
				Role:      "user",
				Content:   "почему это происходит?",
				Timestamp: now.Add(time.Duration(i*2) * time.Minute),
			},
			sqlite.ConversationEntry{
				Role: "assistant",
				Content: "Разобрал: " + finding +
					". Воспроизводится на каждом прогоне и объясняет наблюдаемое поведение.",
				Timestamp: now.Add(time.Duration(i*2+1) * time.Minute),
			},
		)
	}
	return msgs
}

// verboseSession returns a session whose user questions cross QuestionMinChars, so each is
// promoted into its own fact and retained.
func verboseSession(now time.Time) []sqlite.ConversationEntry {
	subjects := []string{
		"проверку подписи токена в модуле аутентификации",
		"тайм-аут при обращении к внешнему провайдеру эмбеддингов",
		"расхождение счётчиков в отчёте по потреблению за прошлый месяц",
		"порядок применения политик при двух совпавших правилах",
		"поведение кэша при одновременной инвалидации из двух сессий",
		"формат идентификаторов в экспортируемом аудит-логе",
	}
	var msgs []sqlite.ConversationEntry
	for i, subject := range subjects {
		msgs = append(msgs,
			sqlite.ConversationEntry{
				Role: "user",
				Content: "Разберись, пожалуйста, в чём причина проблемы, которую мы обсуждали: " +
					subject + ". Опиши, что именно происходит на каждом шаге, какие данные " +
					"при этом видны, и что из этого следует для остальных модулей — мне нужно " +
					"понимать не только симптом, но и механизм целиком.",
				Timestamp: now.Add(time.Duration(i*2) * time.Minute),
			},
			sqlite.ConversationEntry{
				Role:      "assistant",
				Content:   "Проверил " + subject + ": причина найдена и воспроизводится стабильно.",
				Timestamp: now.Add(time.Duration(i*2+1) * time.Minute),
			},
		)
	}
	return msgs
}

func runeCount(msgs []sqlite.ConversationEntry) int {
	total := 0
	for _, m := range msgs {
		total += len([]rune(m.Content))
	}
	return total
}

func TestDistillerService_CompressesTransientMaterial(t *testing.T) {
	svc, conv, facts := newTestDistiller(t)
	ctx := distillerTestContext()
	now := time.Now().UTC()

	msgs := terseSession(now)
	seedSession(t, conv, "sess-terse", msgs)
	rawRunes := runeCount(msgs)

	res, err := svc.DistillSession(ctx, "sess-terse")
	require.NoError(t, err)
	require.Equal(t, 1, res.SessionsProcessed)
	require.Zero(t, res.QuestionFactsAdded, "no user message crosses the threshold in this fixture")

	all := listDistilledSessionFacts(t, facts, ctx, "sess-terse")
	require.Len(t, all, 1, "a terse session must distil to exactly one summary")

	distilled := len([]rune(all[0].Content))
	require.Positive(t, rawRunes)
	require.Positive(t, distilled, "an empty summary would make the ratio a fake 100%")
	reduction := 100.0 * (1.0 - float64(distilled)/float64(rawRunes))
	t.Logf("context reduction on transient material: %d runes -> %d runes (%.1f%% fewer). "+
		"Runes, not tokens; representation, not storage.", rawRunes, distilled, reduction)

	// The floor sits here, on the half the distiller is responsible for. It is a ratchet against
	// a distiller that starts copying instead of summarising, not a target — and deliberately
	// well below the measured figure so an ordinary refactor does not fail the build.
	const minReduction = 60.0
	assert.Greaterf(t, reduction, minReduction,
		"transient reduction fell to %.1f%%, below the %.1f%% floor: the summary is approaching "+
			"the size of the history it replaces", reduction, minReduction)
}

func TestDistillerService_RetainsPromotedQuestionsAndSaysSo(t *testing.T) {
	svc, conv, facts := newTestDistiller(t)
	ctx := distillerTestContext()
	now := time.Now().UTC()

	msgs := verboseSession(now)
	seedSession(t, conv, "sess-verbose", msgs)
	rawRunes := runeCount(msgs)

	res, err := svc.DistillSession(ctx, "sess-verbose")
	require.NoError(t, err)
	require.Equal(t, 6, res.QuestionFactsAdded, "every question crosses QuestionMinChars here")

	all := listDistilledSessionFacts(t, facts, ctx, "sess-verbose")

	promoted, summary := 0, 0
	for _, f := range all {
		if f.Module == "user-question" {
			promoted += len([]rune(f.Content))
			continue
		}
		summary += len([]rune(f.Content))
	}
	total := promoted + summary
	overall := 100.0 * (1.0 - float64(total)/float64(rawRunes))

	t.Logf("verbose session: %d runes -> %d runes (%.1f%% fewer overall), of which %d runes are "+
		"RETAINED user questions and %d the summary. The low overall figure is retention "+
		"working, not compression failing.", rawRunes, total, overall, promoted, summary)

	// Retention is the assertion, not a reduction floor. A session of substantial questions is
	// SUPPOSED to keep them: this test exists so nobody later «improves» the ratio by discarding
	// what the person actually asked.
	assert.Greater(t, promoted, summary,
		"promoted questions should dominate a verbose session's distilled size; if the summary "+
			"outweighs them, questions are being dropped")
	assert.Contains(t, all[0].Content+all[len(all)-1].Content, "модуле аутентификации",
		"a promoted question must survive near-verbatim, or promotion is lossy and pointless")
}
