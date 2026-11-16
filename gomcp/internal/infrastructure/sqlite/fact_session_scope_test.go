package sqlite

import (
	"context"
	"database/sql"
	"errors"
	"math"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/stretchr/testify/require"

	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
)

const (
	turnIDA     = "turn_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
	turnIDB     = "turn_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
	turnIDC     = "turn_cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
	requestRefA = "session-turn-request-v1:sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
	requestRefB = "session-turn-request-v1:sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
)

type failingFactRow struct {
	scanErr  error
	queryErr error
}

func (row failingFactRow) Scan(_ ...any) error { return row.scanErr }
func (row failingFactRow) Err() error          { return row.queryErr }

func TestFactRepoSessionMemoryUsesExactScopeAndSession(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := NewFactRepo(db)
	require.NoError(t, err)

	alpha := scopedCtx("tenant-a", "project-alpha")
	beta := scopedCtx("tenant-a", "project-beta")

	legacy := memory.NewFact("legacy empty session marker", memory.LevelProject, "session", "")
	legacy.Embedding = []float64{1, 0}
	require.NoError(t, repo.Add(alpha, legacy))

	alphaOne := memory.NewFact("alpha session one marker", memory.LevelProject, "session", "")
	alphaOne.Embedding = []float64{1, 0}
	require.NoError(t, repo.AddForSession(alpha, "session-one", alphaOne))

	alphaTwo := memory.NewFact("alpha session two marker", memory.LevelProject, "session", "")
	alphaTwo.Embedding = []float64{1, 0}
	require.NoError(t, repo.AddForSession(alpha, "session-two", alphaTwo))

	betaOne := memory.NewFact("beta session one marker", memory.LevelProject, "session", "")
	betaOne.Embedding = []float64{1, 0}
	require.NoError(t, repo.AddForSession(beta, "session-one", betaOne))

	keyword, err := repo.SearchForSession(alpha, "session-one", "marker", 20)
	require.NoError(t, err)
	require.Len(t, keyword, 1)
	require.Equal(t, alphaOne.ID, keyword[0].ID)
	require.Equal(t, "tenant-a", keyword[0].TenantID)
	require.Equal(t, "project-alpha", keyword[0].ProjectID)
	require.Equal(t, "session-one", keyword[0].SessionID)

	semantic, err := repo.SearchByVectorForSession(alpha, "session-one", []float64{1, 0}, 20)
	require.NoError(t, err)
	require.Len(t, semantic, 1)
	require.Equal(t, alphaOne.ID, semantic[0].ID)

	legacyDomain, err := repo.ListByDomain(alpha, "session", false)
	require.NoError(t, err)
	require.Len(t, legacyDomain, 1, "non-stale legacy domain listing must quarantine session rows")
	require.Equal(t, legacy.ID, legacyDomain[0].ID)

	betaKeyword, err := repo.SearchForSession(beta, "session-one", "marker", 20)
	require.NoError(t, err)
	require.Len(t, betaKeyword, 1)
	require.Equal(t, betaOne.ID, betaKeyword[0].ID)
}

func TestFactRepoSessionMemoryDoesNotDeduplicateAcrossSessions(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := NewFactRepo(db)
	require.NoError(t, err)
	ctx := scopedCtx("tenant-a", "project-alpha")

	one := memory.NewFact("same conversation text", memory.LevelProject, "session", "")
	two := memory.NewFact("same conversation text", memory.LevelProject, "session", "")
	require.NoError(t, repo.AddForSession(ctx, "session-one", one))
	require.NoError(t, repo.AddForSession(ctx, "session-two", two))
	require.NotEqual(t, one.ID, two.ID, "different sessions must retain different rows")

	oneFacts, err := repo.SearchForSession(ctx, "session-one", "conversation", 20)
	require.NoError(t, err)
	twoFacts, err := repo.SearchForSession(ctx, "session-two", "conversation", 20)
	require.NoError(t, err)
	require.Len(t, oneFacts, 1)
	require.Len(t, twoFacts, 1)
	require.Equal(t, one.ID, oneFacts[0].ID)
	require.Equal(t, two.ID, twoFacts[0].ID)
}

func TestFactRepoSessionTurnReceiptReconcilesAndRejectsConflicts(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := NewFactRepo(db)
	require.NoError(t, err)
	ctx := scopedCtx("tenant-a", "project-turns")

	first := memory.NewFact("same logical turn", memory.LevelDomain, "conversation", "chat")
	first.Source = "session_memory"
	first.Origin = memory.OriginDerived
	receipt, deduplicated, err := repo.AddTurnForSession(ctx, "session-one", turnIDA, first)
	require.NoError(t, err)
	require.False(t, deduplicated)
	require.Equal(t, 1, receipt.Version)
	require.Equal(t, turnIDA, receipt.TurnID)
	require.Equal(t, first.ID, receipt.FactID)
	require.Len(t, receipt.PayloadSHA256, 64)

	retry := memory.NewFact("same logical turn", memory.LevelDomain, "conversation", "chat")
	retry.Source = "session_memory"
	retry.Origin = memory.OriginDerived
	retryReceipt, deduplicated, err := repo.AddTurnForSession(ctx, "session-one", turnIDA, retry)
	require.NoError(t, err)
	require.True(t, deduplicated)
	require.Equal(t, receipt, retryReceipt)
	require.Equal(t, first.ID, retry.ID)

	conflict := memory.NewFact("different model output", memory.LevelDomain, "conversation", "chat")
	conflict.Source = "session_memory"
	conflict.Origin = memory.OriginDerived
	_, _, err = repo.AddTurnForSession(ctx, "session-one", turnIDA, conflict)
	require.ErrorIs(t, err, memory.ErrSessionTurnConflict)

	legitimateRepeat := memory.NewFact("same logical turn", memory.LevelDomain, "conversation", "chat")
	legitimateRepeat.Source = "session_memory"
	legitimateRepeat.Origin = memory.OriginDerived
	secondReceipt, deduplicated, err := repo.AddTurnForSession(ctx, "session-one", turnIDB, legitimateRepeat)
	require.NoError(t, err)
	require.False(t, deduplicated)
	require.NotEqual(t, first.ID, legitimateRepeat.ID)
	require.NotEqual(t, receipt.FactID, secondReceipt.FactID)

	var facts, receipts int
	require.NoError(t, repo.db.QueryRow(`SELECT COUNT(*) FROM hierarchical_facts
		WHERE tenant_id = ? AND project_id = ? AND session_id = ?`,
		"tenant-a", "project-turns", "session-one").Scan(&facts))
	require.NoError(t, repo.db.QueryRow(`SELECT COUNT(*) FROM session_turn_receipts
		WHERE tenant_id = ? AND project_id = ? AND session_id = ?`,
		"tenant-a", "project-turns", "session-one").Scan(&receipts))
	require.Equal(t, 2, facts)
	require.Equal(t, 2, receipts)

	gotReceipt, gotFact, err := repo.GetTurnForSession(ctx, "session-one", turnIDA)
	require.NoError(t, err)
	require.Equal(t, receipt, gotReceipt)
	require.Equal(t, first.ID, gotFact.ID)

	missingReceipt, missingFact, err := repo.GetTurnForSession(
		scopedCtx("tenant-a", "project-sibling"), "session-one", turnIDA,
	)
	require.NoError(t, err)
	require.Nil(t, missingReceipt)
	require.Nil(t, missingFact)
	var projects int
	require.NoError(t, repo.db.QueryRow(`SELECT COUNT(*) FROM rlm_projects
		WHERE tenant_id = ? AND project_id = ?`, "tenant-a", "project-sibling").Scan(&projects))
	require.Zero(t, projects, "read-only receipt lookup created a project")
}

func TestFactRepoReceiptBackedFactRejectsV33WriterUpdateAndDelete(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := NewFactRepo(db)
	require.NoError(t, err)
	ctx := scopedCtx("tenant-a", "project-v33-writer")

	fact := memory.NewFact("receipt-owned immutable payload", memory.LevelDomain, "conversation", "chat")
	fact.Source = "session_memory"
	fact.Origin = memory.OriginDerived
	receipt, deduplicated, err := repo.AddTurnForSession(ctx, "session-one", turnIDA, fact)
	require.NoError(t, err)
	require.False(t, deduplicated)

	// This is the mutation shape used by a pre-receipt writer when folding a duplicate.
	_, err = repo.db.Exec(`UPDATE hierarchical_facts SET origin = ?, confidence = ?
		WHERE id = ? AND tenant_id = ? AND project_id = ? AND session_id = ?`,
		string(memory.OriginExternal), 0.25, fact.ID,
		"tenant-a", "project-v33-writer", "session-one")
	require.ErrorContains(t, err, "receipt-backed session fact is immutable: update denied")

	// A stale cleanup or rollback in the old writer must not orphan the durable receipt either.
	_, err = repo.db.Exec(`DELETE FROM hierarchical_facts
		WHERE id = ? AND tenant_id = ? AND project_id = ? AND session_id = ?`,
		fact.ID, "tenant-a", "project-v33-writer", "session-one")
	require.ErrorContains(t, err, "receipt-backed session fact is immutable: delete denied")

	gotReceipt, gotFact, err := repo.GetTurnForSession(ctx, "session-one", turnIDA)
	require.NoError(t, err)
	require.Equal(t, receipt, gotReceipt)
	require.Equal(t, fact.ID, gotFact.ID)
	require.Equal(t, "receipt-owned immutable payload", gotFact.Content)
	require.Equal(t, memory.OriginDerived, gotFact.Origin)
	require.Equal(t, 1.0, gotFact.Confidence)

	// The invariant is scoped to receipt ownership: old unkeyed session rows remain writable.
	legacy := memory.NewFact("legacy mutable session payload", memory.LevelDomain, "conversation", "chat")
	legacy.Source = "session_memory"
	legacy.Origin = memory.OriginDerived
	require.NoError(t, repo.AddForSession(ctx, "session-one", legacy))
	result, err := repo.db.Exec(`UPDATE hierarchical_facts SET content = ? WHERE id = ?`,
		"legacy updated payload", legacy.ID)
	require.NoError(t, err)
	changed, err := result.RowsAffected()
	require.NoError(t, err)
	require.EqualValues(t, 1, changed)
	result, err = repo.db.Exec(`DELETE FROM hierarchical_facts WHERE id = ?`, legacy.ID)
	require.NoError(t, err)
	changed, err = result.RowsAffected()
	require.NoError(t, err)
	require.EqualValues(t, 1, changed)

	// Tenant erasure remains possible: remove the receipt first, then its fact in one transaction.
	tx, err := repo.db.SqlDB().BeginTx(context.Background(), nil)
	require.NoError(t, err)
	result, err = tx.Exec(`DELETE FROM session_turn_receipts
		WHERE tenant_id = ? AND project_id = ? AND session_id = ? AND turn_id = ?`,
		"tenant-a", "project-v33-writer", "session-one", turnIDA)
	require.NoError(t, err)
	changed, err = result.RowsAffected()
	require.NoError(t, err)
	require.EqualValues(t, 1, changed)
	result, err = tx.Exec(`DELETE FROM hierarchical_facts
		WHERE id = ? AND tenant_id = ? AND project_id = ? AND session_id = ?`,
		fact.ID, "tenant-a", "project-v33-writer", "session-one")
	require.NoError(t, err)
	changed, err = result.RowsAffected()
	require.NoError(t, err)
	require.EqualValues(t, 1, changed)
	require.NoError(t, tx.Commit())

	gotReceipt, gotFact, err = repo.GetTurnForSession(ctx, "session-one", turnIDA)
	require.NoError(t, err)
	require.Nil(t, gotReceipt)
	require.Nil(t, gotFact)
}

func TestFactRepoSessionTurnRequestRefSeparatesDedupIdentityFromStoredPayload(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := NewFactRepo(db)
	require.NoError(t, err)
	ctx := scopedCtx("tenant-a", "project-turn-request-ref")

	first := memory.NewFact("bounded first assistant response", memory.LevelDomain, "conversation", "chat")
	first.CodeRef = requestRefA
	first.Source = "session_memory"
	first.Origin = memory.OriginDerived
	receipt, deduplicated, err := repo.AddTurnForSession(ctx, "session-one", turnIDA, first)
	require.NoError(t, err)
	require.False(t, deduplicated)
	require.Equal(t,
		sessionTurnPayloadSHA256(rlmscope.New("tenant-a", "project-turn-request-ref"), "session-one", first),
		receipt.PayloadSHA256,
		"receipt digest must continue to bind the full stored fact",
	)

	retry := memory.NewFact("same request, different bounded assistant response", memory.LevelDomain, "conversation", "chat")
	retry.CodeRef = requestRefA
	retry.Source = "session_memory"
	retry.Origin = memory.OriginDerived
	retryReceipt, deduplicated, err := repo.AddTurnForSession(ctx, "session-one", turnIDA, retry)
	require.NoError(t, err)
	require.True(t, deduplicated)
	require.Equal(t, receipt, retryReceipt)
	require.Equal(t, first.ID, retry.ID)
	require.Equal(t, first.Content, retry.Content, "dedup must return the originally stored fact")

	conflict := memory.NewFact("different request identity", memory.LevelDomain, "conversation", "chat")
	conflict.CodeRef = requestRefB
	conflict.Source = "session_memory"
	conflict.Origin = memory.OriginDerived
	_, _, err = repo.AddTurnForSession(ctx, "session-one", turnIDA, conflict)
	require.ErrorIs(t, err, memory.ErrSessionTurnConflict)

	malformedRef := "session-turn-request-v1:sha256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
	legacyFirst := memory.NewFact("legacy payload", memory.LevelDomain, "conversation", "chat")
	legacyFirst.CodeRef = malformedRef
	legacyFirst.Source = "session_memory"
	legacyFirst.Origin = memory.OriginDerived
	_, deduplicated, err = repo.AddTurnForSession(ctx, "session-one", turnIDB, legacyFirst)
	require.NoError(t, err)
	require.False(t, deduplicated)

	legacyRetry := memory.NewFact("changed legacy payload", memory.LevelDomain, "conversation", "chat")
	legacyRetry.CodeRef = malformedRef
	legacyRetry.Source = "session_memory"
	legacyRetry.Origin = memory.OriginDerived
	_, _, err = repo.AddTurnForSession(ctx, "session-one", turnIDB, legacyRetry)
	require.ErrorIs(t, err, memory.ErrSessionTurnConflict,
		"malformed carriers must retain full-fact fingerprint semantics")

	_, err = repo.db.Exec(`UPDATE hierarchical_facts SET content = ? WHERE id = ?`, "tampered", first.ID)
	require.ErrorContains(t, err, "receipt-backed session fact is immutable: update denied")
	_, _, err = repo.GetTurnForSession(ctx, "session-one", turnIDA)
	require.NoError(t, err)
	_, err = repo.db.Exec(`UPDATE session_turn_receipts SET payload_sha256 = ?
		WHERE tenant_id = ? AND project_id = ? AND session_id = ? AND turn_id = ?`,
		strings.Repeat("f", 64), "tenant-a", "project-turn-request-ref", "session-one", turnIDA)
	require.NoError(t, err)
	_, _, err = repo.GetTurnForSession(ctx, "session-one", turnIDA)
	require.ErrorIs(t, err, memory.ErrSessionTurnIntegrity,
		"request identity must not weaken receipt integrity over the stored fact")
}

func TestFactRepoCommittedSessionTurnReconcilesAfterProjectArchive(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := NewFactRepo(db)
	require.NoError(t, err)
	ctx := scopedCtx("tenant-a", "project-archived-retry")

	first := memory.NewFact("committed before archive", memory.LevelDomain, "conversation", "chat")
	first.Source = "session_memory"
	first.Origin = memory.OriginDerived
	receipt, deduplicated, err := repo.AddTurnForSession(ctx, "session-one", turnIDA, first)
	require.NoError(t, err)
	require.False(t, deduplicated)

	_, err = repo.db.Exec(`UPDATE rlm_projects SET status = ?
		WHERE tenant_id = ? AND project_id = ?`,
		rlmscope.ProjectStatusArchived, "tenant-a", "project-archived-retry")
	require.NoError(t, err)

	retry := memory.NewFact("committed before archive", memory.LevelDomain, "conversation", "chat")
	retry.Source = "session_memory"
	retry.Origin = memory.OriginDerived
	retryReceipt, deduplicated, err := repo.AddTurnForSession(ctx, "session-one", turnIDA, retry)
	require.NoError(t, err)
	require.True(t, deduplicated)
	require.Equal(t, receipt, retryReceipt)
	require.Equal(t, first.ID, retry.ID)

	newTurn := memory.NewFact("new write after archive", memory.LevelDomain, "conversation", "chat")
	newTurn.Source = "session_memory"
	newTurn.Origin = memory.OriginDerived
	_, _, err = repo.AddTurnForSession(ctx, "session-one", turnIDB, newTurn)
	require.ErrorContains(t, err, "archived")
}

func TestFactRepoSessionTurnReceiptIntegrityAndRollback(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := NewFactRepo(db)
	require.NoError(t, err)
	ctx := scopedCtx("tenant-a", "project-receipt-integrity")

	fact := memory.NewFact("receipt-bound payload", memory.LevelDomain, "conversation", "chat")
	fact.Source = "session_memory"
	fact.Origin = memory.OriginDerived
	_, _, err = repo.AddTurnForSession(ctx, "session-one", turnIDA, fact)
	require.NoError(t, err)
	_, err = repo.db.Exec(`UPDATE hierarchical_facts SET content = ? WHERE id = ?`, "tampered", fact.ID)
	require.ErrorContains(t, err, "receipt-backed session fact is immutable: update denied")
	_, _, err = repo.GetTurnForSession(ctx, "session-one", turnIDA)
	require.NoError(t, err)
	_, err = repo.db.Exec(`UPDATE session_turn_receipts SET payload_sha256 = ?
		WHERE tenant_id = ? AND project_id = ? AND session_id = ? AND turn_id = ?`,
		strings.Repeat("f", 64), "tenant-a", "project-receipt-integrity", "session-one", turnIDA)
	require.NoError(t, err)
	_, _, err = repo.GetTurnForSession(ctx, "session-one", turnIDA)
	require.True(t, errors.Is(err, memory.ErrSessionTurnIntegrity), err)

	invalid := memory.NewFact("must not commit invalid turn", memory.LevelDomain, "conversation", "chat")
	invalid.Source = "session_memory"
	invalid.Origin = memory.OriginDerived
	invalid.Confidence = math.NaN()
	_, _, err = repo.AddTurnForSession(ctx, "session-invalid", turnIDB, invalid)
	require.ErrorContains(t, err, "confidence must be finite")
	invalid.Confidence = 1
	invalid.Origin = memory.Origin("invented")
	_, _, err = repo.AddTurnForSession(ctx, "session-invalid", turnIDB, invalid)
	require.ErrorContains(t, err, "invalid fact origin")
	invalid.Origin = memory.OriginDerived
	invalid.Source = "genome"
	_, _, err = repo.AddTurnForSession(ctx, "session-invalid", turnIDB, invalid)
	require.ErrorContains(t, err, "genome metadata is not valid")
	invalid.Source = "session_memory"
	invalid.HitCount = 1
	_, _, err = repo.AddTurnForSession(ctx, "session-invalid", turnIDB, invalid)
	require.ErrorContains(t, err, "access counters are managed by the store")
	invalidTTL := memory.NewFact("must not commit lossy ttl json", memory.LevelDomain, "conversation", "chat")
	invalidTTL.Source = "session_memory"
	invalidTTL.Origin = memory.OriginDerived
	invalidTTL.TTL = &memory.TTLConfig{
		TTLSeconds: 60, RefreshTrigger: string([]byte{0xff}), OnExpire: memory.OnExpireArchive,
	}
	_, _, err = repo.AddTurnForSession(ctx, "session-invalid", turnIDB, invalidTTL)
	require.ErrorContains(t, err, "ttl refresh_trigger must be valid UTF-8")
	invalidTimestamp := time.Date(10000, time.January, 1, 0, 0, 0, 0, time.UTC)
	for _, testCase := range []struct {
		name   string
		mutate func(*memory.Fact)
	}{
		{name: "created_at", mutate: func(fact *memory.Fact) { fact.CreatedAt = invalidTimestamp }},
		{name: "valid_from", mutate: func(fact *memory.Fact) { fact.ValidFrom = invalidTimestamp }},
		{name: "valid_until", mutate: func(fact *memory.Fact) { fact.ValidUntil = &invalidTimestamp }},
	} {
		candidate := memory.NewFact("must not commit an unparseable timestamp", memory.LevelDomain, "conversation", "chat")
		candidate.Source = "session_memory"
		candidate.Origin = memory.OriginDerived
		testCase.mutate(candidate)
		_, _, err = repo.AddTurnForSession(ctx, "session-invalid", turnIDB, candidate)
		require.ErrorContains(t, err, testCase.name+" cannot round-trip as RFC3339Nano")
	}
	var invalidFacts, invalidReceipts int
	require.NoError(t, repo.db.QueryRow(`SELECT COUNT(*) FROM hierarchical_facts
		WHERE tenant_id = ? AND project_id = ? AND session_id = ?`,
		"tenant-a", "project-receipt-integrity", "session-invalid").Scan(&invalidFacts))
	require.NoError(t, repo.db.QueryRow(`SELECT COUNT(*) FROM session_turn_receipts
		WHERE tenant_id = ? AND project_id = ? AND session_id = ?`,
		"tenant-a", "project-receipt-integrity", "session-invalid").Scan(&invalidReceipts))
	require.Zero(t, invalidFacts)
	require.Zero(t, invalidReceipts)
	negativeZero := memory.NewFact("canonical zero confidence", memory.LevelDomain, "conversation", "chat")
	negativeZero.Source = "session_memory"
	negativeZero.Origin = memory.OriginDerived
	negativeZero.Confidence = math.Copysign(0, -1)
	zeroReceipt, deduplicated, err := repo.AddTurnForSession(
		ctx, "session-zero", turnIDB, negativeZero,
	)
	require.NoError(t, err)
	require.False(t, deduplicated)
	require.False(t, math.Signbit(negativeZero.Confidence))
	positiveZeroRetry := memory.NewFact("canonical zero confidence", memory.LevelDomain, "conversation", "chat")
	positiveZeroRetry.Source = "session_memory"
	positiveZeroRetry.Origin = memory.OriginDerived
	positiveZeroRetry.Confidence = 0
	retryReceipt, deduplicated, err := repo.AddTurnForSession(
		ctx, "session-zero", turnIDB, positiveZeroRetry,
	)
	require.NoError(t, err)
	require.True(t, deduplicated)
	require.Equal(t, zeroReceipt, retryReceipt)
	_, err = repo.db.Exec(`UPDATE session_turn_receipts SET created_at = 'not-a-time'
		WHERE tenant_id = ? AND project_id = ? AND session_id = ? AND turn_id = ?`,
		"tenant-a", "project-receipt-integrity", "session-zero", turnIDB)
	require.NoError(t, err)
	_, _, err = repo.GetTurnForSession(ctx, "session-zero", turnIDB)
	require.ErrorIs(t, err, memory.ErrSessionTurnIntegrity)
	unspecified := memory.NewFact("invalid stored origin must not reconcile", memory.LevelDomain, "conversation", "chat")
	unspecified.Source = "session_memory"
	unspecified.Origin = memory.OriginUnspecified
	_, _, err = repo.AddTurnForSession(ctx, "session-origin", turnIDA, unspecified)
	require.NoError(t, err)
	_, err = repo.db.Exec(`UPDATE hierarchical_facts SET origin = 'garbage' WHERE id = ?`, unspecified.ID)
	require.ErrorContains(t, err, "receipt-backed session fact is immutable: update denied")
	_, _, err = repo.GetTurnForSession(ctx, "session-origin", turnIDA)
	require.NoError(t, err)

	lifecycle := memory.NewFact("receipt binds lifecycle", memory.LevelDomain, "conversation", "chat")
	lifecycle.Source = "session_memory"
	lifecycle.Origin = memory.OriginDerived
	lifecycle.TTL = &memory.TTLConfig{
		TTLSeconds: 60, RefreshTrigger: "conversation", OnExpire: memory.OnExpireArchive,
	}
	expiresAt := time.Now().UTC().Add(time.Hour).Truncate(time.Nanosecond)
	lifecycle.ValidUntil = &expiresAt
	_, _, err = repo.AddTurnForSession(ctx, "session-two", turnIDC, lifecycle)
	require.NoError(t, err)

	lifecycleRetry := memory.NewFact("receipt binds lifecycle", memory.LevelDomain, "conversation", "chat")
	lifecycleRetry.Source = "session_memory"
	lifecycleRetry.Origin = memory.OriginDerived
	lifecycleRetry.TTL = &memory.TTLConfig{
		TTLSeconds: 120, RefreshTrigger: "conversation", OnExpire: memory.OnExpireArchive,
	}
	lifecycleRetry.ValidUntil = &expiresAt
	_, _, err = repo.AddTurnForSession(ctx, "session-two", turnIDC, lifecycleRetry)
	require.ErrorIs(t, err, memory.ErrSessionTurnConflict)

	_, err = repo.db.Exec(`UPDATE hierarchical_facts SET is_stale = 1 WHERE id = ?`, lifecycle.ID)
	require.ErrorContains(t, err, "receipt-backed session fact is immutable: update denied")
	_, _, err = repo.GetTurnForSession(ctx, "session-two", turnIDC)
	require.NoError(t, err)
	_, err = repo.db.Exec(`UPDATE hierarchical_facts SET is_stale = 0, created_at = 'not-a-time'
		WHERE id = ?`, lifecycle.ID)
	require.ErrorContains(t, err, "receipt-backed session fact is immutable: update denied")
	_, _, err = repo.GetTurnForSession(ctx, "session-two", turnIDC)
	require.NoError(t, err)
	_, err = repo.db.Exec(`UPDATE hierarchical_facts SET created_at = ?, confidence = NULL
		WHERE id = ?`, lifecycle.CreatedAt.UTC().Format(timeFormat), lifecycle.ID)
	require.ErrorContains(t, err, "receipt-backed session fact is immutable: update denied")
	_, _, err = repo.GetTurnForSession(ctx, "session-two", turnIDC)
	require.NoError(t, err)

	rollbackCtx := scopedCtx("tenant-a", "project-receipt-rollback")
	_, err = repo.db.Exec(`CREATE TRIGGER fail_session_turn_receipt
		BEFORE INSERT ON session_turn_receipts
		WHEN NEW.project_id = 'project-receipt-rollback'
		BEGIN SELECT RAISE(ABORT, 'forced receipt failure'); END`)
	require.NoError(t, err)
	rollbackFact := memory.NewFact("must roll back with receipt", memory.LevelDomain, "conversation", "chat")
	rollbackFact.Source = "session_memory"
	rollbackFact.Origin = memory.OriginDerived
	_, _, err = repo.AddTurnForSession(rollbackCtx, "session-one", turnIDB, rollbackFact)
	require.ErrorContains(t, err, "forced receipt failure")
	var projects, facts, receipts int
	require.NoError(t, repo.db.QueryRow(`SELECT COUNT(*) FROM rlm_projects WHERE project_id = ?`,
		"project-receipt-rollback").Scan(&projects))
	require.NoError(t, repo.db.QueryRow(`SELECT COUNT(*) FROM hierarchical_facts WHERE project_id = ?`,
		"project-receipt-rollback").Scan(&facts))
	require.NoError(t, repo.db.QueryRow(`SELECT COUNT(*) FROM session_turn_receipts WHERE project_id = ?`,
		"project-receipt-rollback").Scan(&receipts))
	require.Zero(t, projects)
	require.Zero(t, facts)
	require.Zero(t, receipts)
}

func TestSessionTurnReceiptLoadPreservesOperationalErrors(t *testing.T) {
	_, storedDataInvalid, err := scanFactDetailed(failingFactRow{scanErr: context.DeadlineExceeded})
	require.False(t, storedDataInvalid)
	require.ErrorIs(t, err, context.DeadlineExceeded)
	classified := sessionTurnFactLoadError(storedDataInvalid, err)
	require.ErrorIs(t, classified, context.DeadlineExceeded)
	require.NotErrorIs(t, classified, memory.ErrSessionTurnIntegrity)

	_, storedDataInvalid, err = scanFactDetailed(failingFactRow{scanErr: sql.ErrNoRows})
	require.False(t, storedDataInvalid)
	classified = sessionTurnFactLoadError(storedDataInvalid, err)
	require.ErrorIs(t, classified, memory.ErrSessionTurnIntegrity)

	conversionErr := errors.New("cannot scan NULL into float64")
	_, storedDataInvalid, err = scanFactDetailed(failingFactRow{scanErr: conversionErr})
	require.True(t, storedDataInvalid)
	classified = sessionTurnFactLoadError(storedDataInvalid, err)
	require.ErrorIs(t, classified, memory.ErrSessionTurnIntegrity)
}

func TestSessionTurnReceiptMalformedRowIsIntegrityFailure(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := NewFactRepo(db)
	require.NoError(t, err)
	ctx := scopedCtx("tenant-a", "project-malformed-receipt")
	fact := memory.NewFact("receipt row scan integrity", memory.LevelDomain, "conversation", "chat")
	fact.Source = "session_memory"
	fact.Origin = memory.OriginDerived
	receipt, _, err := repo.AddTurnForSession(ctx, "session-one", turnIDA, fact)
	require.NoError(t, err)

	_, err = db.Exec(`DROP TABLE session_turn_receipts`)
	require.NoError(t, err)
	_, err = db.Exec(`CREATE TABLE session_turn_receipts (
		tenant_id TEXT,
		project_id TEXT,
		session_id TEXT,
		turn_id TEXT,
		fact_id TEXT,
		payload_version INTEGER,
		payload_sha256 TEXT,
		created_at TEXT
	)`)
	require.NoError(t, err)
	_, err = db.Exec(`INSERT INTO session_turn_receipts
		(tenant_id, project_id, session_id, turn_id, fact_id,
		 payload_version, payload_sha256, created_at)
		VALUES (?, ?, ?, ?, ?, NULL, ?, ?)`,
		"tenant-a", "project-malformed-receipt", "session-one", turnIDA,
		fact.ID, receipt.PayloadSHA256, time.Now().UTC().Format(timeFormat))
	require.NoError(t, err)

	_, _, err = repo.GetTurnForSession(ctx, "session-one", turnIDA)
	require.ErrorIs(t, err, memory.ErrSessionTurnIntegrity)
}

func TestFactRepoSessionTurnReceiptMigrationValidatesExactShape(t *testing.T) {
	t.Run("pre v3.3 parent schema upgrades before receipt validation", func(t *testing.T) {
		db, err := OpenMemory()
		require.NoError(t, err)
		t.Cleanup(func() { require.NoError(t, db.Close()) })
		_, err = db.Exec(`CREATE TABLE hierarchical_facts (
			id TEXT PRIMARY KEY,
			tenant_id TEXT NOT NULL DEFAULT 'local',
			project_id TEXT NOT NULL DEFAULT 'default',
			content TEXT NOT NULL,
			level INTEGER NOT NULL DEFAULT 0,
			domain TEXT,
			module TEXT,
			code_ref TEXT,
			parent_id TEXT,
			embedding BLOB,
			ttl_config TEXT,
			created_at TEXT NOT NULL,
			valid_from TEXT NOT NULL,
			valid_until TEXT,
			is_stale INTEGER DEFAULT 0,
			is_archived INTEGER DEFAULT 0,
			confidence REAL DEFAULT 1.0,
			source TEXT DEFAULT 'unspecified',
			session_id TEXT,
			FOREIGN KEY (parent_id) REFERENCES hierarchical_facts(id)
		)`)
		require.NoError(t, err)
		_, err = db.Exec(`CREATE TABLE schema_info (key TEXT PRIMARY KEY, value TEXT)`)
		require.NoError(t, err)
		_, err = db.Exec(`INSERT INTO schema_info (key, value) VALUES ('version', '3.2.0')`)
		require.NoError(t, err)

		repo, err := NewFactRepo(db)
		require.NoError(t, err)
		var version string
		require.NoError(t, db.QueryRow(`SELECT value FROM schema_info WHERE key = 'version'`).Scan(&version))
		require.Equal(t, "3.4.0", version)
		for _, column := range []string{"origin", "hit_count", "last_accessed_at"} {
			var columns int
			require.NoError(t, db.QueryRow(`SELECT COUNT(*) FROM pragma_table_info('hierarchical_facts')
				WHERE name = ?`, column).Scan(&columns))
			require.Equal(t, 1, columns, "missing upgraded column %s", column)
		}
		var receipts, facts, mappings int
		require.NoError(t, db.QueryRow(`SELECT COUNT(*) FROM session_turn_receipts`).Scan(&receipts))
		require.NoError(t, db.QueryRow(`SELECT COUNT(*) FROM hierarchical_facts`).Scan(&facts))
		require.NoError(t, db.QueryRow(`SELECT COUNT(*) FROM fact_export_sequence`).Scan(&mappings))
		require.Zero(t, receipts)
		require.Zero(t, facts, "the post-ALTER startup probe must roll back its facts")
		require.Zero(t, mappings, "the post-ALTER startup probe must roll back its mappings")

		ctx := scopedCtx("tenant-a", "project-pre-v33")
		fact := memory.NewFact("pre-v3.3 hit_count export sequence", memory.LevelProject, "paging", "")
		require.NoError(t, repo.Add(ctx, fact))
		var beforeHitCount, afterHitCount int64
		require.NoError(t, db.QueryRow(`SELECT seq FROM fact_export_sequence WHERE fact_id = ?`, fact.ID).Scan(&beforeHitCount))
		_, err = db.Exec(`UPDATE hierarchical_facts SET hit_count = hit_count + 1 WHERE id = ?`, fact.ID)
		require.NoError(t, err)
		require.NoError(t, db.QueryRow(`SELECT seq FROM fact_export_sequence WHERE fact_id = ?`, fact.ID).Scan(&afterHitCount))
		require.Greater(t, afterHitCount, beforeHitCount,
			"the trigger created before the v3.3 ALTER must fire for hit_count afterwards")
		require.NoError(t, repo.Delete(ctx, fact.ID))
		require.NoError(t, db.QueryRow(`SELECT COUNT(*) FROM fact_export_sequence WHERE fact_id = ?`, fact.ID).Scan(&mappings))
		require.Zero(t, mappings)
	})

	t.Run("head v3.3 without receipt table upgrades", func(t *testing.T) {
		db, err := OpenMemory()
		require.NoError(t, err)
		t.Cleanup(func() { require.NoError(t, db.Close()) })
		repo, err := NewFactRepo(db)
		require.NoError(t, err)
		_, err = db.Exec(`DROP TABLE session_turn_receipts`)
		require.NoError(t, err)
		_, err = db.Exec(`UPDATE schema_info SET value = '3.3.0' WHERE key = 'version'`)
		require.NoError(t, err)

		require.NoError(t, repo.migrate())
		var version string
		require.NoError(t, db.QueryRow(`SELECT value FROM schema_info WHERE key = 'version'`).Scan(&version))
		require.Equal(t, "3.4.0", version)
		var payloadVersionColumns int
		require.NoError(t, db.QueryRow(`SELECT COUNT(*) FROM pragma_table_info('session_turn_receipts')
			WHERE name = 'payload_version' AND type = 'INTEGER' AND "notnull" = 1`).Scan(&payloadVersionColumns))
		require.Equal(t, 1, payloadVersionColumns)
		var probeFacts, probeReceipts int
		require.NoError(t, db.QueryRow(`SELECT COUNT(*) FROM hierarchical_facts`).Scan(&probeFacts))
		require.NoError(t, db.QueryRow(`SELECT COUNT(*) FROM session_turn_receipts`).Scan(&probeReceipts))
		require.Zero(t, probeFacts)
		require.Zero(t, probeReceipts)
	})

	t.Run("intermediate same-name table fails startup", func(t *testing.T) {
		db, err := OpenMemory()
		require.NoError(t, err)
		t.Cleanup(func() { require.NoError(t, db.Close()) })
		repo, err := NewFactRepo(db)
		require.NoError(t, err)
		_, err = db.Exec(`DROP TABLE session_turn_receipts`)
		require.NoError(t, err)
		_, err = db.Exec(`CREATE TABLE session_turn_receipts (
			tenant_id TEXT NOT NULL,
			project_id TEXT NOT NULL,
			session_id TEXT NOT NULL,
			turn_id TEXT NOT NULL,
			fact_id TEXT NOT NULL UNIQUE,
			fact_fingerprint TEXT NOT NULL,
			created_at TEXT NOT NULL,
			PRIMARY KEY (tenant_id, project_id, session_id, turn_id)
		)`)
		require.NoError(t, err)
		_, err = db.Exec(`UPDATE schema_info SET value = '3.3.0' WHERE key = 'version'`)
		require.NoError(t, err)

		err = repo.migrate()
		require.ErrorContains(t, err, "incompatible session_turn_receipts schema")
		var version string
		require.NoError(t, db.QueryRow(`SELECT value FROM schema_info WHERE key = 'version'`).Scan(&version))
		require.Equal(t, "3.3.0", version)
	})

	t.Run("partial parent index fails startup", func(t *testing.T) {
		db, err := OpenMemory()
		require.NoError(t, err)
		t.Cleanup(func() { require.NoError(t, db.Close()) })
		repo, err := NewFactRepo(db)
		require.NoError(t, err)
		_, err = db.Exec(`DROP INDEX idx_facts_exact_identity`)
		require.NoError(t, err)
		_, err = db.Exec(`CREATE UNIQUE INDEX idx_facts_exact_identity
			ON hierarchical_facts(tenant_id, project_id, session_id, id)
			WHERE session_id <> ''`)
		require.NoError(t, err)
		_, err = db.Exec(`UPDATE schema_info SET value = '3.3.0' WHERE key = 'version'`)
		require.NoError(t, err)

		err = repo.migrate()
		require.ErrorContains(t, err, "exact receipt parent identity must be unique")
		var version string
		require.NoError(t, db.QueryRow(`SELECT value FROM schema_info WHERE key = 'version'`).Scan(&version))
		require.Equal(t, "3.3.0", version)
	})

	t.Run("nocase scope columns fail startup", func(t *testing.T) {
		db, err := OpenMemory()
		require.NoError(t, err)
		t.Cleanup(func() { require.NoError(t, db.Close()) })
		repo, err := NewFactRepo(db)
		require.NoError(t, err)
		_, err = db.Exec(`DROP TABLE session_turn_receipts`)
		require.NoError(t, err)
		_, err = db.Exec(`CREATE TABLE session_turn_receipts (
			tenant_id TEXT COLLATE NOCASE NOT NULL,
			project_id TEXT NOT NULL,
			session_id TEXT NOT NULL CHECK (session_id <> ''),
			turn_id TEXT NOT NULL CHECK (
				length(turn_id) = 69 AND substr(turn_id, 1, 5) = 'turn_'
				AND substr(turn_id, 6) NOT GLOB '*[^0-9a-f]*'
			),
			fact_id TEXT NOT NULL,
			payload_version INTEGER NOT NULL CHECK (payload_version = 2),
			payload_sha256 TEXT NOT NULL CHECK (
				length(payload_sha256) = 64
				AND payload_sha256 NOT GLOB '*[^0-9a-f]*'
			),
			created_at TEXT NOT NULL,
			PRIMARY KEY (tenant_id, project_id, session_id, turn_id),
			UNIQUE (fact_id),
			FOREIGN KEY (tenant_id, project_id, session_id, fact_id)
				REFERENCES hierarchical_facts(tenant_id, project_id, session_id, id)
		)`)
		require.NoError(t, err)
		_, err = db.Exec(`UPDATE schema_info SET value = '3.3.0' WHERE key = 'version'`)
		require.NoError(t, err)

		err = repo.migrate()
		require.ErrorContains(t, err, "exact BINARY primary key required")
		var version string
		require.NoError(t, db.QueryRow(`SELECT value FROM schema_info WHERE key = 'version'`).Scan(&version))
		require.Equal(t, "3.3.0", version)
	})

	t.Run("commented out checks fail startup", func(t *testing.T) {
		db, err := OpenMemory()
		require.NoError(t, err)
		t.Cleanup(func() { require.NoError(t, db.Close()) })
		repo, err := NewFactRepo(db)
		require.NoError(t, err)
		_, err = db.Exec(`DROP TABLE session_turn_receipts`)
		require.NoError(t, err)
		_, err = db.Exec(`CREATE TABLE session_turn_receipts (
			tenant_id TEXT NOT NULL,
			project_id TEXT NOT NULL,
			session_id TEXT NOT NULL,
			turn_id TEXT NOT NULL,
			fact_id TEXT NOT NULL,
			payload_version INTEGER NOT NULL,
			payload_sha256 TEXT NOT NULL,
			created_at TEXT NOT NULL,
			-- CHECK (session_id <> '')
			-- CHECK (length(turn_id) = 69 AND substr(turn_id, 1, 5) = 'turn_'
			--        AND substr(turn_id, 6) NOT GLOB '*[^0-9a-f]*')
			-- CHECK (payload_version = 2)
			/* CHECK (length(payload_sha256) = 64
			   AND payload_sha256 NOT GLOB '*[^0-9a-f]*') */
			PRIMARY KEY (tenant_id, project_id, session_id, turn_id),
			UNIQUE (fact_id),
			FOREIGN KEY (tenant_id, project_id, session_id, fact_id)
				REFERENCES hierarchical_facts(tenant_id, project_id, session_id, id)
		)`)
		require.NoError(t, err)
		_, err = db.Exec(`UPDATE schema_info SET value = '3.3.0' WHERE key = 'version'`)
		require.NoError(t, err)

		err = repo.migrate()
		require.ErrorContains(t, err, "empty session_id constraint is not enforced")
		var version string
		require.NoError(t, db.QueryRow(`SELECT value FROM schema_info WHERE key = 'version'`).Scan(&version))
		require.Equal(t, "3.3.0", version)
	})

	t.Run("explicit binary primary key does not hide nocase column", func(t *testing.T) {
		db, err := OpenMemory()
		require.NoError(t, err)
		t.Cleanup(func() { require.NoError(t, db.Close()) })
		repo, err := NewFactRepo(db)
		require.NoError(t, err)
		_, err = db.Exec(`DROP TABLE session_turn_receipts`)
		require.NoError(t, err)
		_, err = db.Exec(`CREATE TABLE session_turn_receipts (
			tenant_id TEXT NOT NULL,
			project_id TEXT COLLATE NOCASE NOT NULL,
			session_id TEXT NOT NULL CHECK (session_id <> ''),
			turn_id TEXT NOT NULL CHECK (
				length(turn_id) = 69 AND substr(turn_id, 1, 5) = 'turn_'
				AND substr(turn_id, 6) NOT GLOB '*[^0-9a-f]*'
			),
			fact_id TEXT NOT NULL,
			payload_version INTEGER NOT NULL CHECK (payload_version = 2),
			payload_sha256 TEXT NOT NULL CHECK (
				length(payload_sha256) = 64
				AND payload_sha256 NOT GLOB '*[^0-9a-f]*'
			),
			created_at TEXT NOT NULL,
			PRIMARY KEY (
				tenant_id COLLATE BINARY,
				project_id COLLATE BINARY,
				session_id COLLATE BINARY,
				turn_id COLLATE BINARY
			),
			UNIQUE (fact_id),
			FOREIGN KEY (tenant_id, project_id, session_id, fact_id)
				REFERENCES hierarchical_facts(tenant_id, project_id, session_id, id)
		)`)
		require.NoError(t, err)
		_, err = db.Exec(`UPDATE schema_info SET value = '3.3.0' WHERE key = 'version'`)
		require.NoError(t, err)

		err = repo.migrate()
		require.ErrorContains(t, err, "exact BINARY key comparison required")
		var version string
		require.NoError(t, db.QueryRow(`SELECT value FROM schema_info WHERE key = 'version'`).Scan(&version))
		require.Equal(t, "3.3.0", version)
	})

	t.Run("uppercase check literals fail startup", func(t *testing.T) {
		db, err := OpenMemory()
		require.NoError(t, err)
		t.Cleanup(func() { require.NoError(t, db.Close()) })
		repo, err := NewFactRepo(db)
		require.NoError(t, err)
		_, err = db.Exec(`DROP TABLE session_turn_receipts`)
		require.NoError(t, err)
		_, err = db.Exec(`CREATE TABLE session_turn_receipts (
			tenant_id TEXT NOT NULL,
			project_id TEXT NOT NULL,
			session_id TEXT NOT NULL CHECK (session_id <> ''),
			turn_id TEXT NOT NULL CHECK (
				length(turn_id) = 69 AND substr(turn_id, 1, 5) = 'TURN_'
				AND substr(turn_id, 6) NOT GLOB '*[^0-9A-F]*'
			),
			fact_id TEXT NOT NULL,
			payload_version INTEGER NOT NULL CHECK (payload_version = 2),
			payload_sha256 TEXT NOT NULL CHECK (
				length(payload_sha256) = 64
				AND payload_sha256 NOT GLOB '*[^0-9A-F]*'
			),
			created_at TEXT NOT NULL,
			PRIMARY KEY (tenant_id, project_id, session_id, turn_id),
			UNIQUE (fact_id),
			FOREIGN KEY (tenant_id, project_id, session_id, fact_id)
				REFERENCES hierarchical_facts(tenant_id, project_id, session_id, id)
		)`)
		require.NoError(t, err)
		_, err = db.Exec(`UPDATE schema_info SET value = '3.3.0' WHERE key = 'version'`)
		require.NoError(t, err)

		err = repo.migrate()
		require.ErrorContains(t, err, "valid receipt rejected")
		var version string
		require.NoError(t, db.QueryRow(`SELECT value FROM schema_info WHERE key = 'version'`).Scan(&version))
		require.Equal(t, "3.3.0", version)
	})

	t.Run("extra unique constraint fails startup", func(t *testing.T) {
		db, err := OpenMemory()
		require.NoError(t, err)
		t.Cleanup(func() { require.NoError(t, db.Close()) })
		repo, err := NewFactRepo(db)
		require.NoError(t, err)
		_, err = db.Exec(`CREATE UNIQUE INDEX session_turn_receipts_scope_collapse
			ON session_turn_receipts(session_id, turn_id)`)
		require.NoError(t, err)
		_, err = db.Exec(`UPDATE schema_info SET value = '3.3.0' WHERE key = 'version'`)
		require.NoError(t, err)

		err = repo.migrate()
		require.ErrorContains(t, err, "exact unique constraints required")
		var version string
		require.NoError(t, db.QueryRow(`SELECT value FROM schema_info WHERE key = 'version'`).Scan(&version))
		require.Equal(t, "3.3.0", version)
	})

	t.Run("extra parent unique constraint fails startup", func(t *testing.T) {
		db, err := OpenMemory()
		require.NoError(t, err)
		t.Cleanup(func() { require.NoError(t, db.Close()) })
		repo, err := NewFactRepo(db)
		require.NoError(t, err)
		_, err = db.Exec(`CREATE UNIQUE INDEX hierarchical_facts_content_collapse
			ON hierarchical_facts(tenant_id, project_id, session_id, content)`)
		require.NoError(t, err)
		_, err = db.Exec(`UPDATE schema_info SET value = '3.3.0' WHERE key = 'version'`)
		require.NoError(t, err)

		err = repo.migrate()
		require.ErrorContains(t, err, "incompatible hierarchical_facts schema: exact unique constraints required")
		var version string
		require.NoError(t, db.QueryRow(`SELECT value FROM schema_info WHERE key = 'version'`).Scan(&version))
		require.Equal(t, "3.3.0", version)
	})

	t.Run("extra rejecting check fails startup", func(t *testing.T) {
		db, err := OpenMemory()
		require.NoError(t, err)
		t.Cleanup(func() { require.NoError(t, db.Close()) })
		repo, err := NewFactRepo(db)
		require.NoError(t, err)
		_, err = db.Exec(`DROP TABLE session_turn_receipts`)
		require.NoError(t, err)
		_, err = db.Exec(`CREATE TABLE session_turn_receipts (
			tenant_id TEXT NOT NULL,
			project_id TEXT NOT NULL,
			session_id TEXT NOT NULL CHECK (session_id <> ''),
			turn_id TEXT NOT NULL CHECK (
				length(turn_id) = 69 AND substr(turn_id, 1, 5) = 'turn_'
				AND substr(turn_id, 6) NOT GLOB '*[^0-9a-f]*'
			),
			fact_id TEXT NOT NULL,
			payload_version INTEGER NOT NULL CHECK (payload_version = 2),
			payload_sha256 TEXT NOT NULL CHECK (
				length(payload_sha256) = 64
				AND payload_sha256 NOT GLOB '*[^0-9a-f]*'
			),
			created_at TEXT NOT NULL,
			PRIMARY KEY (tenant_id, project_id, session_id, turn_id),
			UNIQUE (fact_id),
			CHECK (0),
			FOREIGN KEY (tenant_id, project_id, session_id, fact_id)
				REFERENCES hierarchical_facts(tenant_id, project_id, session_id, id)
		)`)
		require.NoError(t, err)
		_, err = db.Exec(`UPDATE schema_info SET value = '3.3.0' WHERE key = 'version'`)
		require.NoError(t, err)

		err = repo.migrate()
		require.ErrorContains(t, err, "valid receipt rejected")
		var version string
		require.NoError(t, db.QueryRow(`SELECT value FROM schema_info WHERE key = 'version'`).Scan(&version))
		require.Equal(t, "3.3.0", version)
	})

	for _, testCase := range []struct {
		name, dropSQL, createSQL, expected string
	}{
		{
			name:      "same-name inert UPDATE trigger fails startup",
			dropSQL:   "DROP TRIGGER " + sessionTurnFactUpdateTrigger,
			createSQL: "CREATE TRIGGER " + sessionTurnFactUpdateTrigger + " BEFORE UPDATE ON hierarchical_facts WHEN 0 BEGIN SELECT 1; END",
			expected:  "receipt-backed fact UPDATE is not immutable",
		},
		{
			name:      "same-name inert DELETE trigger fails startup",
			dropSQL:   "DROP TRIGGER " + sessionTurnFactDeleteTrigger,
			createSQL: "CREATE TRIGGER " + sessionTurnFactDeleteTrigger + " BEFORE DELETE ON hierarchical_facts WHEN 0 BEGIN SELECT 1; END",
			expected:  "receipt-backed fact DELETE is not immutable",
		},
	} {
		t.Run(testCase.name, func(t *testing.T) {
			db, err := OpenMemory()
			require.NoError(t, err)
			t.Cleanup(func() { require.NoError(t, db.Close()) })
			repo, err := NewFactRepo(db)
			require.NoError(t, err)
			_, err = db.Exec(testCase.dropSQL)
			require.NoError(t, err)
			_, err = db.Exec(testCase.createSQL)
			require.NoError(t, err)
			_, err = db.Exec(`UPDATE schema_info SET value = '3.3.0' WHERE key = 'version'`)
			require.NoError(t, err)

			err = repo.migrate()
			require.ErrorContains(t, err, testCase.expected)
			var foreignKeys int
			require.NoError(t, db.QueryRow(`PRAGMA foreign_keys`).Scan(&foreignKeys))
			require.Equal(t, 1, foreignKeys, "failed validation must restore foreign-key enforcement")
			var deferredForeignKeys int
			require.NoError(t, db.QueryRow(`PRAGMA defer_foreign_keys`).Scan(&deferredForeignKeys))
			require.Zero(t, deferredForeignKeys, "failed validation must roll back deferred constraints")
			var version string
			require.NoError(t, db.QueryRow(`SELECT value FROM schema_info WHERE key = 'version'`).Scan(&version))
			require.Equal(t, "3.3.0", version)
		})
	}
}

func TestFactRepoConcurrentSameTurnWritesReconcileOneReceipt(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := NewFactRepo(db)
	require.NoError(t, err)
	ctx := scopedCtx("tenant-a", "project-concurrent-turn")

	const writers = 24
	facts := make([]*memory.Fact, writers)
	receipts := make([]*memory.SessionTurnReceipt, writers)
	deduplicated := make([]bool, writers)
	errs := make([]error, writers)
	start := make(chan struct{})
	var wg sync.WaitGroup
	for i := 0; i < writers; i++ {
		fact := memory.NewFact("one logical concurrent turn", memory.LevelDomain, "conversation", "chat")
		fact.Source = "session_memory"
		fact.Origin = memory.OriginDerived
		facts[i] = fact
		wg.Add(1)
		go func(index int) {
			defer wg.Done()
			<-start
			receipts[index], deduplicated[index], errs[index] = repo.AddTurnForSession(
				ctx, "session-one", turnIDA, facts[index],
			)
		}(i)
	}
	close(start)
	wg.Wait()

	firstWrites := 0
	for i := range writers {
		require.NoErrorf(t, errs[i], "writer %d failed", i)
		require.NotNil(t, receipts[i])
		require.Equal(t, receipts[0], receipts[i])
		require.Equal(t, facts[0].ID, facts[i].ID)
		if !deduplicated[i] {
			firstWrites++
		}
	}
	require.Equal(t, 1, firstWrites)
	var factRows, receiptRows int
	require.NoError(t, repo.db.QueryRow(`SELECT COUNT(*) FROM hierarchical_facts
		WHERE tenant_id = ? AND project_id = ? AND session_id = ?`,
		"tenant-a", "project-concurrent-turn", "session-one").Scan(&factRows))
	require.NoError(t, repo.db.QueryRow(`SELECT COUNT(*) FROM session_turn_receipts
		WHERE tenant_id = ? AND project_id = ? AND session_id = ?`,
		"tenant-a", "project-concurrent-turn", "session-one").Scan(&receiptRows))
	require.Equal(t, 1, factRows)
	require.Equal(t, 1, receiptRows)
}

func TestFactRepoConcurrentSameTurnAcrossConnectionsReconcilesOneReceipt(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "shared-turn-memory.db")
	dbOne, err := Open(dbPath)
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, dbOne.Close()) })
	repoOne, err := NewFactRepo(dbOne)
	require.NoError(t, err)

	dbTwo, err := Open(dbPath)
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, dbTwo.Close()) })
	repoTwo, err := NewFactRepo(dbTwo)
	require.NoError(t, err)

	ctx := scopedCtx("tenant-a", "project-two-connection-turn")
	factOne := memory.NewFact("same turn through two connections", memory.LevelDomain, "conversation", "chat")
	factOne.Source = "session_memory"
	factOne.Origin = memory.OriginDerived
	factTwo := memory.NewFact("same turn through two connections", memory.LevelDomain, "conversation", "chat")
	factTwo.Source = "session_memory"
	factTwo.Origin = memory.OriginDerived

	start := make(chan struct{})
	var receiptOne, receiptTwo *memory.SessionTurnReceipt
	var deduplicatedOne, deduplicatedTwo bool
	var errOne, errTwo error
	var wg sync.WaitGroup
	wg.Add(2)
	go func() {
		defer wg.Done()
		<-start
		receiptOne, deduplicatedOne, errOne = repoOne.AddTurnForSession(
			ctx, "session-one", turnIDA, factOne,
		)
	}()
	go func() {
		defer wg.Done()
		<-start
		receiptTwo, deduplicatedTwo, errTwo = repoTwo.AddTurnForSession(
			ctx, "session-one", turnIDA, factTwo,
		)
	}()
	close(start)
	wg.Wait()

	require.NoError(t, errOne)
	require.NoError(t, errTwo)
	require.Equal(t, receiptOne, receiptTwo)
	require.Equal(t, factOne.ID, factTwo.ID)
	require.NotEqual(t, deduplicatedOne, deduplicatedTwo)
	var factRows, receiptRows int
	require.NoError(t, repoOne.db.QueryRow(`SELECT COUNT(*) FROM hierarchical_facts
		WHERE tenant_id = ? AND project_id = ? AND session_id = ?`,
		"tenant-a", "project-two-connection-turn", "session-one").Scan(&factRows))
	require.NoError(t, repoOne.db.QueryRow(`SELECT COUNT(*) FROM session_turn_receipts
		WHERE tenant_id = ? AND project_id = ? AND session_id = ?`,
		"tenant-a", "project-two-connection-turn", "session-one").Scan(&receiptRows))
	require.Equal(t, 1, factRows)
	require.Equal(t, 1, receiptRows)
}

func TestFactRepoConcurrentIdenticalSessionWritesFoldToOneLiveRow(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := NewFactRepo(db)
	require.NoError(t, err)
	ctx := scopedCtx("tenant-a", "project-concurrent")

	const writers = 24
	facts := make([]*memory.Fact, writers)
	errs := make([]error, writers)
	start := make(chan struct{})
	var wg sync.WaitGroup
	for i := 0; i < writers; i++ {
		fact := memory.NewFact("one exact concurrent statement", memory.LevelDomain, "atomicity", "")
		fact.Origin = memory.OriginExternal
		fact.Confidence = 0.25
		if i == writers-1 {
			fact.Origin = memory.OriginUser
			fact.Confidence = 0.99
		}
		facts[i] = fact
		wg.Add(1)
		go func(index int) {
			defer wg.Done()
			<-start
			errs[index] = repo.AddForSession(ctx, "session-one", facts[index])
		}(i)
	}
	close(start)
	wg.Wait()

	for i, writeErr := range errs {
		require.NoErrorf(t, writeErr, "writer %d failed", i)
	}
	for i := 1; i < len(facts); i++ {
		require.Equal(t, facts[0].ID, facts[i].ID, "writer %d did not receive the surviving row id", i)
	}

	var rows int
	require.NoError(t, repo.db.QueryRow(`SELECT COUNT(*) FROM hierarchical_facts
		WHERE tenant_id = ? AND project_id = ? AND session_id = ?
		  AND content = ? AND level = ? AND IFNULL(domain, '') = ?
		  AND is_archived = 0 AND is_stale = 0`,
		"tenant-a", "project-concurrent", "session-one",
		"one exact concurrent statement", int(memory.LevelDomain), "atomicity",
	).Scan(&rows))
	require.Equal(t, 1, rows, "concurrent exact writes produced duplicate live rows")

	stored, err := repo.ListForSession(ctx, "session-one", false)
	require.NoError(t, err)
	require.Len(t, stored, 1)
	require.Equal(t, memory.OriginUser, stored[0].Origin)
	require.InDelta(t, 0.99, stored[0].Confidence, 0.0001)
}

func TestFactRepoConcurrentSessionWritesAcrossConnectionsFoldToOneLiveRow(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "shared-memory.db")
	dbOne, err := Open(dbPath)
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, dbOne.Close()) })
	repoOne, err := NewFactRepo(dbOne)
	require.NoError(t, err)

	dbTwo, err := Open(dbPath)
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, dbTwo.Close()) })
	repoTwo, err := NewFactRepo(dbTwo)
	require.NoError(t, err)

	ctx := scopedCtx("tenant-a", "project-two-connections")
	seed := memory.NewFact("pre-existing project seed", memory.LevelProject, "atomicity", "")
	require.NoError(t, repoOne.AddForSession(ctx, "session-one", seed))
	factOne := memory.NewFact("same write through two connections", memory.LevelDomain, "atomicity", "")
	factTwo := memory.NewFact("same write through two connections", memory.LevelDomain, "atomicity", "")
	start := make(chan struct{})
	var errOne, errTwo error
	var wg sync.WaitGroup
	wg.Add(2)
	go func() {
		defer wg.Done()
		<-start
		errOne = repoOne.AddForSession(ctx, "session-one", factOne)
	}()
	go func() {
		defer wg.Done()
		<-start
		errTwo = repoTwo.AddForSession(ctx, "session-one", factTwo)
	}()
	close(start)
	wg.Wait()

	require.NoError(t, errOne)
	require.NoError(t, errTwo)
	require.Equal(t, factOne.ID, factTwo.ID)
	var rows int
	require.NoError(t, repoOne.db.QueryRow(`SELECT COUNT(*) FROM hierarchical_facts
		WHERE tenant_id = ? AND project_id = ? AND session_id = ?
		  AND content = ? AND is_archived = 0 AND is_stale = 0`,
		"tenant-a", "project-two-connections", "session-one",
		"same write through two connections",
	).Scan(&rows))
	require.Equal(t, 1, rows)
}

func TestFactRepoSessionDedupKeepsDomainsSeparate(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := NewFactRepo(db)
	require.NoError(t, err)
	ctx := scopedCtx("tenant-a", "project-domains")

	left := memory.NewFact("same text in two domains", memory.LevelDomain, "left", "")
	right := memory.NewFact("same text in two domains", memory.LevelDomain, "right", "")
	require.NoError(t, repo.AddForSession(ctx, "session-one", left))
	require.NoError(t, repo.AddForSession(ctx, "session-one", right))
	require.NotEqual(t, left.ID, right.ID)

	stored, err := repo.ListForSession(ctx, "session-one", false)
	require.NoError(t, err)
	require.Len(t, stored, 2)
}

func TestFactRepoSessionKeywordTieKeepsNewestTurnsAboveLimit(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := NewFactRepo(db)
	require.NoError(t, err)
	ctx := scopedCtx("tenant-a", "project-recent-search")
	base := time.Date(2026, time.August, 1, 0, 0, 0, 0, time.UTC)

	const turns = 8
	written := make([]*memory.Fact, turns)
	for i := 0; i < turns; i++ {
		fact := memory.NewFact("conversation turn "+string(rune('a'+i)), memory.LevelSnippet, "chat", "")
		fact.CreatedAt = base.Add(time.Duration(i) * time.Minute)
		fact.ValidFrom = fact.CreatedAt
		written[i] = fact
		require.NoError(t, repo.AddForSession(ctx, "session-one", fact))
	}

	// Newer facts outside the exact session must not participate in ordering or consume the limit.
	sibling := memory.NewFact("conversation sibling newest", memory.LevelSnippet, "chat", "")
	sibling.CreatedAt = base.Add(24 * time.Hour)
	sibling.ValidFrom = sibling.CreatedAt
	require.NoError(t, repo.AddForSession(ctx, "session-two", sibling))

	got, err := repo.SearchForSession(ctx, "session-one", "conversation", 3)
	require.NoError(t, err)
	require.Len(t, got, 3)
	require.Equal(t, written[7].ID, got[0].ID)
	require.Equal(t, written[6].ID, got[1].ID)
	require.Equal(t, written[5].ID, got[2].ID)
}

func TestFactRepoSessionVectorTieKeepsNewestTurnsAboveLimit(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := NewFactRepo(db)
	require.NoError(t, err)
	ctx := scopedCtx("tenant-a", "project-recent-vector-search")
	base := time.Date(2026, time.August, 1, 0, 0, 0, 0, time.UTC)

	const turns = 8
	written := make([]*memory.Fact, turns)
	for i := 0; i < turns; i++ {
		fact := memory.NewFact("semantic conversation turn "+string(rune('a'+i)), memory.LevelSnippet, "chat", "")
		fact.CreatedAt = base.Add(time.Duration(i) * time.Minute)
		fact.ValidFrom = fact.CreatedAt
		fact.Embedding = []float64{1, 0}
		written[i] = fact
		require.NoError(t, repo.AddForSession(ctx, "session-one", fact))
	}

	sibling := memory.NewFact("semantic sibling newest", memory.LevelSnippet, "chat", "")
	sibling.CreatedAt = base.Add(24 * time.Hour)
	sibling.ValidFrom = sibling.CreatedAt
	sibling.Embedding = []float64{1, 0}
	require.NoError(t, repo.AddForSession(ctx, "session-two", sibling))

	got, err := repo.SearchByVectorForSession(ctx, "session-one", []float64{1, 0}, 3)
	require.NoError(t, err)
	require.Len(t, got, 3)
	require.Equal(t, written[7].ID, got[0].ID)
	require.Equal(t, written[6].ID, got[1].ID)
	require.Equal(t, written[5].ID, got[2].ID)
}

func TestFactRepoLegacyKeywordTieOrderRemainsIDAscending(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := NewFactRepo(db)
	require.NoError(t, err)
	ctx := scopedCtx("tenant-a", "project-legacy-search-order")
	base := time.Date(2026, time.August, 1, 0, 0, 0, 0, time.UTC)

	newer := memory.NewFact("conversation newer", memory.LevelSnippet, "chat", "")
	newer.ID = "z-newer"
	newer.CreatedAt = base.Add(time.Hour)
	newer.ValidFrom = newer.CreatedAt
	require.NoError(t, repo.Add(ctx, newer))

	older := memory.NewFact("conversation older", memory.LevelSnippet, "chat", "")
	older.ID = "a-older"
	older.CreatedAt = base
	older.ValidFrom = older.CreatedAt
	require.NoError(t, repo.Add(ctx, older))

	got, err := repo.Search(ctx, "conversation", 2)
	require.NoError(t, err)
	require.Len(t, got, 2)
	require.Equal(t, older.ID, got[0].ID, "legacy equal-score ordering changed from ID ascending")
	require.Equal(t, newer.ID, got[1].ID)
}

func TestFactRepoSessionInsertFailureRollsBackProjectFactAndIndex(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := NewFactRepo(db)
	require.NoError(t, err)
	require.NoError(t, installFailingEmbeddingIndexTrigger(repo))

	ctx := scopedCtx("tenant-a", "project-rollback-new")
	fact := memory.NewFact("must roll back completely", memory.LevelDomain, "atomicity", "")
	fact.Origin = memory.OriginUser
	fact.Embedding = []float64{0.25, 0.75}
	original := *fact

	err = repo.AddForSession(ctx, "session-one", fact)
	require.ErrorContains(t, err, "forced embedding index failure")
	require.Equal(t, original, *fact, "a failed write mutated the caller's fact handle")

	var projects, facts, indexes int
	require.NoError(t, repo.db.QueryRow(`SELECT COUNT(*) FROM rlm_projects
		WHERE tenant_id = ? AND project_id = ?`, "tenant-a", "project-rollback-new").Scan(&projects))
	require.NoError(t, repo.db.QueryRow(`SELECT COUNT(*) FROM hierarchical_facts
		WHERE tenant_id = ? AND project_id = ?`, "tenant-a", "project-rollback-new").Scan(&facts))
	require.NoError(t, repo.db.QueryRow(`SELECT COUNT(*) FROM embeddings_index
		WHERE fact_id = ?`, fact.ID).Scan(&indexes))
	require.Zero(t, projects, "project creation escaped a failed fact transaction")
	require.Zero(t, facts, "fact row escaped a failed fact transaction")
	require.Zero(t, indexes, "embedding index escaped a failed fact transaction")
}

func TestFactRepoSessionFoldFailureRollsBackOriginEmbeddingIndexAndProjectTouch(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := NewFactRepo(db)
	require.NoError(t, err)
	ctx := scopedCtx("tenant-a", "project-rollback-fold")

	existing := memory.NewFact("duplicate whose merge must roll back", memory.LevelDomain, "atomicity", "")
	existing.Origin = memory.OriginExternal
	existing.Confidence = 0.2
	require.NoError(t, repo.AddForSession(ctx, "session-one", existing))

	const untouched = "2001-02-03T04:05:06Z"
	_, err = repo.db.Exec(`UPDATE rlm_projects SET last_accessed_at = ?
		WHERE tenant_id = ? AND project_id = ?`, untouched, "tenant-a", "project-rollback-fold")
	require.NoError(t, err)
	require.NoError(t, installFailingEmbeddingIndexTrigger(repo))

	incoming := memory.NewFact("duplicate whose merge must roll back", memory.LevelDomain, "atomicity", "")
	incoming.Origin = memory.OriginUser
	incoming.Confidence = 0.95
	incoming.Embedding = []float64{1, 0}
	original := *incoming

	err = repo.AddForSession(ctx, "session-one", incoming)
	require.ErrorContains(t, err, "forced embedding index failure")
	require.Equal(t, original, *incoming, "a failed fold leaked the uncommitted survivor state")

	var origin, lastAccessed string
	var confidence float64
	var embedding []byte
	require.NoError(t, repo.db.QueryRow(`SELECT origin, confidence, embedding
		FROM hierarchical_facts WHERE id = ?`, existing.ID).Scan(&origin, &confidence, &embedding))
	require.Equal(t, string(memory.OriginExternal), origin)
	require.InDelta(t, 0.2, confidence, 0.0001)
	require.Empty(t, embedding, "fact embedding escaped the rolled-back fold")
	require.NoError(t, repo.db.QueryRow(`SELECT last_accessed_at FROM rlm_projects
		WHERE tenant_id = ? AND project_id = ?`, "tenant-a", "project-rollback-fold").Scan(&lastAccessed))
	require.Equal(t, untouched, lastAccessed, "project touch escaped the rolled-back fold")

	var facts, indexes int
	require.NoError(t, repo.db.QueryRow(`SELECT COUNT(*) FROM hierarchical_facts
		WHERE tenant_id = ? AND project_id = ? AND session_id = ? AND content = ?`,
		"tenant-a", "project-rollback-fold", "session-one", incoming.Content).Scan(&facts))
	require.NoError(t, repo.db.QueryRow(`SELECT COUNT(*) FROM embeddings_index
		WHERE fact_id = ?`, existing.ID).Scan(&indexes))
	require.Equal(t, 1, facts)
	require.Zero(t, indexes)
}

func TestFoldExistingDuplicatesNeverMutatesExactSessionRows(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := NewFactRepo(db)
	require.NoError(t, err)
	ctx := scopedCtx("tenant-a", "project-startup-fold")

	first := memory.NewFact("historical exact duplicate", memory.LevelDomain, "atomicity", "")
	first.Origin = memory.OriginExternal
	first.Confidence = 0.2
	require.NoError(t, repo.AddForSession(ctx, "session-one", first))

	second := memory.NewFact("historical exact duplicate", memory.LevelDomain, "atomicity", "")
	second.Origin = memory.OriginUser
	second.Confidence = 0.9
	_, err = repo.db.Exec(`INSERT INTO hierarchical_facts
		(id, tenant_id, project_id, content, level, domain, created_at, valid_from,
		 is_stale, is_archived, confidence, source, session_id, origin)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?, ?, ?, ?)`,
		second.ID, "tenant-a", "project-startup-fold", second.Content, int(second.Level), second.Domain,
		second.CreatedAt.Format(timeFormat), second.ValidFrom.Format(timeFormat),
		second.Confidence, second.Source, "session-one", string(second.Origin),
	)
	require.NoError(t, err)

	folded, err := repo.FoldExistingDuplicates(ctx)
	require.NoError(t, err)
	require.Zero(t, folded, "legacy startup cleanup folded exact session rows")

	type storedState struct {
		origin     string
		confidence float64
		archived   int
	}
	states := make(map[string]storedState, 2)
	rows, err := repo.db.Query(`SELECT id, origin, confidence, is_archived
		FROM hierarchical_facts WHERE id IN (?, ?)`, first.ID, second.ID)
	require.NoError(t, err)
	defer rows.Close()
	for rows.Next() {
		var id string
		var state storedState
		require.NoError(t, rows.Scan(&id, &state.origin, &state.confidence, &state.archived))
		states[id] = state
	}
	require.NoError(t, rows.Err())
	require.Equal(t, storedState{origin: string(memory.OriginExternal), confidence: 0.2}, states[first.ID])
	require.Equal(t, storedState{origin: string(memory.OriginUser), confidence: 0.9}, states[second.ID])
}

func installFailingEmbeddingIndexTrigger(repo *FactRepo) error {
	_, err := repo.db.Exec(`CREATE TRIGGER fail_embedding_index_insert
		BEFORE INSERT ON embeddings_index
		BEGIN
			SELECT RAISE(ABORT, 'forced embedding index failure');
		END`)
	return err
}

func TestFactRepoParentHierarchyCannotCrossSessionBoundary(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := NewFactRepo(db)
	require.NoError(t, err)
	ctx := scopedCtx("tenant-a", "project-alpha")

	parent := memory.NewFact("session one parent", memory.LevelModule, "session", "")
	require.NoError(t, repo.AddForSession(ctx, "session-one", parent))

	sameSessionChild := memory.NewFact("session one child", memory.LevelSnippet, "session", "")
	sameSessionChild.ParentID = parent.ID
	require.NoError(t, repo.AddForSession(ctx, "session-one", sameSessionChild))

	otherSessionChild := memory.NewFact("session two child", memory.LevelSnippet, "session", "")
	otherSessionChild.ParentID = parent.ID
	require.ErrorContains(t, repo.AddForSession(ctx, "session-two", otherSessionChild), "exact memory boundary")

	legacyChild := memory.NewFact("legacy child", memory.LevelSnippet, "legacy", "")
	legacyChild.ParentID = parent.ID
	require.ErrorContains(t, repo.Add(ctx, legacyChild), "exact memory boundary")

	legacyParent := memory.NewFact("legacy parent", memory.LevelModule, "legacy", "")
	require.NoError(t, repo.Add(ctx, legacyParent))
	sessionChildOfLegacy := memory.NewFact("session child of legacy", memory.LevelSnippet, "session", "")
	sessionChildOfLegacy.ParentID = legacyParent.ID
	require.ErrorContains(t, repo.AddForSession(ctx, "session-one", sessionChildOfLegacy), "exact memory boundary")
}

func TestFactRepoReadSurfacesClearRawCrossBoundaryParents(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := NewFactRepo(db)
	require.NoError(t, err)
	ctx := scopedCtx("tenant-a", "project-parent-reads")

	legacyParent := memory.NewFact("legacy parent", memory.LevelModule, "parents", "")
	legacyChild := memory.NewFact("legacy child", memory.LevelSnippet, "parents", "")
	require.NoError(t, repo.Add(ctx, legacyParent))
	require.NoError(t, repo.Add(ctx, legacyChild))

	sessionParent := memory.NewFact("session one parent", memory.LevelModule, "parents", "")
	sessionChild := memory.NewFact("session child with raw legacy parent", memory.LevelSnippet, "parents", "")
	siblingChild := memory.NewFact("session child with raw sibling parent", memory.LevelSnippet, "parents", "")
	safeChild := memory.NewFact("session child with exact parent", memory.LevelSnippet, "parents", "")
	safeChild.ParentID = sessionParent.ID
	require.NoError(t, repo.AddForSession(ctx, "session-one", sessionParent))
	require.NoError(t, repo.AddForSession(ctx, "session-one", sessionChild))
	require.NoError(t, repo.AddForSession(ctx, "session-one", siblingChild))
	require.NoError(t, repo.AddForSession(ctx, "session-one", safeChild))

	siblingParent := memory.NewFact("session two parent", memory.LevelModule, "parents", "")
	require.NoError(t, repo.AddForSession(ctx, "session-two", siblingParent))

	// Historical/foreign writers could populate parent_id directly because its FK validates only
	// existence by id. These assignments deliberately bypass the repository write guard.
	_, err = repo.db.Exec(`UPDATE hierarchical_facts SET parent_id = ? WHERE id = ?`,
		legacyParent.ID, sessionChild.ID)
	require.NoError(t, err)
	_, err = repo.db.Exec(`UPDATE hierarchical_facts SET parent_id = ? WHERE id = ?`,
		siblingParent.ID, siblingChild.ID)
	require.NoError(t, err)
	_, err = repo.db.Exec(`UPDATE hierarchical_facts SET parent_id = ? WHERE id = ?`,
		sessionParent.ID, legacyChild.ID)
	require.NoError(t, err)

	sessionFacts, err := repo.ListForSession(ctx, "session-one", false)
	require.NoError(t, err)
	byID := make(map[string]*memory.Fact, len(sessionFacts))
	for _, fact := range sessionFacts {
		byID[fact.ID] = fact
	}
	require.Empty(t, byID[sessionChild.ID].ParentID,
		"an exact session read exposed a legacy parent id")
	require.Empty(t, byID[siblingChild.ID].ParentID,
		"an exact session read exposed a sibling-session parent id")
	require.Equal(t, sessionParent.ID, byID[safeChild.ID].ParentID,
		"an exact same-session parent was incorrectly removed")

	gotLegacyChild, err := repo.Get(ctx, legacyChild.ID)
	require.NoError(t, err)
	require.Empty(t, gotLegacyChild.ParentID,
		"a legacy read exposed a session parent id")
}

func TestFactRepoSessionMemoryFailsClosedWithoutExactBoundary(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := NewFactRepo(db)
	require.NoError(t, err)
	fact := memory.NewFact("must not persist", memory.LevelProject, "session", "")

	require.ErrorContains(t, repo.AddForSession(context.Background(), "session-one", fact), "explicit tenant_id/project_id")
	_, err = repo.SearchForSession(context.Background(), "session-one", "persist", 20)
	require.ErrorContains(t, err, "explicit tenant_id/project_id")
	require.ErrorContains(t, repo.AddForSession(scopedCtx("tenant-a", "project-alpha"), "", fact), "session_id is required")
	require.ErrorContains(t, repo.AddForSession(scopedCtx("tenant-a", "project-alpha"), "bad/session", fact), "unsupported character")
	_, err = repo.SearchForSession(scopedCtx("tenant-a", "project-alpha"), " session-one ", "persist", 20)
	require.ErrorContains(t, err, "surrounding whitespace")
}

func TestFactRepoSessionMemoryRejectsReservedDefaultProject(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := NewFactRepo(db)
	require.NoError(t, err)

	for _, projectID := range []string{"default", "DEFAULT", "DeFaUlT"} {
		ctx := scopedCtx("local", projectID)
		fact := memory.NewFact("must not persist", memory.LevelProject, "session", "")
		require.ErrorContains(t, repo.AddForSession(ctx, "session-one", fact), "reserved for legacy memory")
		_, err = repo.ListForSession(ctx, "session-one", false)
		require.ErrorContains(t, err, "reserved for legacy memory")
		_, err = repo.SearchForSession(ctx, "session-one", "persist", 20)
		require.ErrorContains(t, err, "reserved for legacy memory")
		_, err = repo.SearchByVectorForSession(ctx, "session-one", []float64{1, 0}, 20)
		require.ErrorContains(t, err, "reserved for legacy memory")
	}
}

func TestFactRepoGetExpiredQuarantinesSessionFacts(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := NewFactRepo(db)
	require.NoError(t, err)
	ctx := scopedCtx("tenant-a", "project-alpha")

	legacy := memory.NewFact("expired legacy fact", memory.LevelProject, "legacy", "")
	legacy.TTL = &memory.TTLConfig{TTLSeconds: 1, OnExpire: memory.OnExpireDelete}
	legacy.CreatedAt = time.Now().Add(-2 * time.Hour)
	legacy.ValidFrom = legacy.CreatedAt
	require.NoError(t, repo.Add(ctx, legacy))

	sessionFact := memory.NewFact("expired session fact", memory.LevelProject, "session", "")
	sessionFact.TTL = &memory.TTLConfig{TTLSeconds: 1, OnExpire: memory.OnExpireDelete}
	sessionFact.CreatedAt = time.Now().Add(-2 * time.Hour)
	sessionFact.ValidFrom = sessionFact.CreatedAt
	require.NoError(t, repo.AddForSession(ctx, "session-one", sessionFact))

	expired, err := repo.GetExpired(ctx)
	require.NoError(t, err)
	require.Len(t, expired, 1)
	require.Equal(t, legacy.ID, expired[0].ID)

	require.NoError(t, repo.Delete(ctx, expired[0].ID))
	sessionFacts, err := repo.ListForSession(ctx, "session-one", true)
	require.NoError(t, err)
	require.Len(t, sessionFacts, 1)
	require.Equal(t, sessionFact.ID, sessionFacts[0].ID)
}

func TestFactRepoLegacySurfacesCannotReadOrMutateSessionFacts(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := NewFactRepo(db)
	require.NoError(t, err)
	ctx := scopedCtx("tenant-a", "project-alpha")

	sessionFact := memory.NewFact("private session gene", memory.LevelProject, "session-private", "")
	sessionFact.Source = "genome"
	sessionFact.Embedding = []float64{1, 0}
	sessionFact.TTL = &memory.TTLConfig{TTLSeconds: 1, OnExpire: memory.OnExpireMarkStale}
	sessionFact.CreatedAt = time.Now().Add(-2 * time.Hour)
	sessionFact.ValidFrom = sessionFact.CreatedAt
	require.NoError(t, repo.AddForSession(ctx, "session-one", sessionFact))

	maliciousLegacyAdd := memory.NewFact("legacy API session injection", memory.LevelProject, "session", "")
	maliciousLegacyAdd.SessionID = "session-two"
	require.ErrorContains(t, repo.Add(ctx, maliciousLegacyAdd), "dedicated session memory API")

	_, err = repo.Get(ctx, sessionFact.ID)
	require.Error(t, err)
	genes, err := repo.ListGenes(ctx)
	require.NoError(t, err)
	require.Empty(t, genes)

	stats, err := repo.Stats(ctx)
	require.NoError(t, err)
	require.Zero(t, stats.TotalFacts)
	require.Zero(t, stats.GeneCount)
	require.Zero(t, stats.WithEmbeddings)
	require.Empty(t, stats.ByDomain)

	require.ErrorContains(t, repo.Update(ctx, sessionFact), "dedicated session memory API")
	stripped := *sessionFact
	stripped.SessionID = ""
	stripped.Content = "legacy overwrite attempt"
	require.ErrorContains(t, repo.Update(ctx, &stripped), "not found")
	require.ErrorContains(t, repo.TouchFact(ctx, sessionFact.ID), "not found")
	require.ErrorContains(t, repo.RefreshTTL(ctx, sessionFact.ID), "not found")
	require.ErrorContains(t, repo.Delete(ctx, sessionFact.ID), "not found")

	stored, err := repo.ListForSession(ctx, "session-one", true)
	require.NoError(t, err)
	require.Len(t, stored, 1)
	require.Equal(t, "private session gene", stored[0].Content)
	require.Equal(t, 0, stored[0].HitCount)
	require.Equal(t, sessionFact.CreatedAt.Unix(), stored[0].CreatedAt.Unix())

	var indexed int
	require.NoError(t, repo.db.QueryRow(`SELECT COUNT(*) FROM embeddings_index WHERE fact_id = ?`, sessionFact.ID).Scan(&indexed))
	require.Equal(t, 1, indexed, "legacy delete must not remove a session fact's embedding index")
}
