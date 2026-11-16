package sqlite

import (
	"bytes"
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"testing"
	"time"

	"github.com/stretchr/testify/require"

	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
)

const (
	claimOwnerA = "claim_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
	claimOwnerB = "claim_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
	claimOwnerC = "claim_cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
)

func newTurnClaimRepo(t *testing.T) (*DB, *FactRepo) {
	t.Helper()
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := NewFactRepo(db)
	require.NoError(t, err)
	return db, repo
}

func TestSessionTurnClaimLeaseStealAndExecutionAreFailClosed(t *testing.T) {
	_, repo := newTurnClaimRepo(t)
	ctx := scopedCtx("tenant-a", "project-claims")

	first, err := repo.acquireSessionTurnClaimAt(
		ctx, "session-one", turnIDA, requestRefA, claimOwnerA, 1_000, 10*time.Second,
	)
	require.NoError(t, err)
	require.Equal(t, memory.SessionTurnClaimed, first.State)
	require.Equal(t, requestRefA, first.RequestRef)
	require.True(t, first.Owned)
	require.Equal(t, int64(1), first.Generation)
	require.Equal(t, int64(1_010), first.LeaseUntilUnix)

	busy, err := repo.acquireSessionTurnClaimAt(
		ctx, "session-one", turnIDA, requestRefA, claimOwnerB, 1_009, 10*time.Second,
	)
	require.NoError(t, err)
	require.Equal(t, memory.SessionTurnClaimed, busy.State)
	require.False(t, busy.Owned)
	require.Equal(t, int64(1), busy.Generation)

	wrongOwner, err := repo.beginSessionTurnExecutionAt(
		ctx, "session-one", turnIDA, requestRefA, claimOwnerB, 1_009, 100*time.Second,
	)
	require.NoError(t, err)
	require.Equal(t, memory.SessionTurnClaimed, wrongOwner.State)
	require.False(t, wrongOwner.Owned)

	expiredOwner, err := repo.beginSessionTurnExecutionAt(
		ctx, "session-one", turnIDA, requestRefA, claimOwnerA, 1_010, 100*time.Second,
	)
	require.NoError(t, err)
	require.Equal(t, memory.SessionTurnClaimed, expiredOwner.State)
	require.False(t, expiredOwner.Owned)

	stolen, err := repo.acquireSessionTurnClaimAt(
		ctx, "session-one", turnIDA, requestRefA, claimOwnerB, 1_010, 10*time.Second,
	)
	require.NoError(t, err)
	require.Equal(t, memory.SessionTurnClaimed, stolen.State)
	require.True(t, stolen.Owned)
	require.Equal(t, int64(2), stolen.Generation)

	lostOwner, err := repo.beginSessionTurnExecutionAt(
		ctx, "session-one", turnIDA, requestRefA, claimOwnerA, 1_011, 100*time.Second,
	)
	require.NoError(t, err)
	require.Equal(t, memory.SessionTurnClaimed, lostOwner.State)
	require.False(t, lostOwner.Owned)

	executing, err := repo.beginSessionTurnExecutionAt(
		ctx, "session-one", turnIDA, requestRefA, claimOwnerB, 1_012, 100*time.Second,
	)
	require.NoError(t, err)
	require.Equal(t, memory.SessionTurnExecuting, executing.State)
	require.True(t, executing.Owned)
	require.Equal(t, int64(1_112), executing.UncertaintyDeadlineUnix)

	// A lost transition acknowledgement can be retried by the same owner before
	// provider send; it does not create a second execution generation.
	idempotent, err := repo.beginSessionTurnExecutionAt(
		ctx, "session-one", turnIDA, requestRefA, claimOwnerB, 1_013, 100*time.Second,
	)
	require.NoError(t, err)
	require.Equal(t, executing.Generation, idempotent.Generation)
	require.Equal(t, executing.ExecutionStartedUnix, idempotent.ExecutionStartedUnix)
	require.True(t, idempotent.Owned)

	nonStealable, err := repo.acquireSessionTurnClaimAt(
		ctx, "session-one", turnIDA, requestRefA, claimOwnerC, 1_111, 10*time.Second,
	)
	require.NoError(t, err)
	require.Equal(t, memory.SessionTurnExecuting, nonStealable.State)
	require.False(t, nonStealable.Owned)
	require.Equal(t, executing.Generation, nonStealable.Generation)

	uncertain, err := repo.acquireSessionTurnClaimAt(
		ctx, "session-one", turnIDA, requestRefA, claimOwnerC, 1_112, 10*time.Second,
	)
	require.NoError(t, err)
	require.Equal(t, memory.SessionTurnUncertain, uncertain.State)
	require.False(t, uncertain.Owned)
	require.Equal(t, executing.Generation, uncertain.Generation)

	stillUncertain, err := repo.acquireSessionTurnClaimAt(
		ctx, "session-one", turnIDA, requestRefA, claimOwnerA, 9_999, 10*time.Second,
	)
	require.NoError(t, err)
	require.Equal(t, memory.SessionTurnUncertain, stillUncertain.State)
	require.False(t, stillUncertain.Owned)
}

func TestSessionTurnClaimBindsRequestRefInEveryState(t *testing.T) {
	_, repo := newTurnClaimRepo(t)
	ctx := scopedCtx("tenant-a", "project-claim-conflict")
	_, err := repo.acquireSessionTurnClaimAt(
		ctx, "session-one", turnIDA, requestRefA, claimOwnerA, 1_000, 10*time.Second,
	)
	require.NoError(t, err)

	_, err = repo.acquireSessionTurnClaimAt(
		ctx, "session-one", turnIDA, requestRefB, claimOwnerB, 1_001, 10*time.Second,
	)
	require.ErrorIs(t, err, memory.ErrSessionTurnConflict)
	_, err = repo.beginSessionTurnExecutionAt(
		ctx, "session-one", turnIDA, requestRefB, claimOwnerA, 1_001, 100*time.Second,
	)
	require.ErrorIs(t, err, memory.ErrSessionTurnConflict)
}

func TestSessionTurnClaimGenerationOverflowFailsClosed(t *testing.T) {
	db, repo := newTurnClaimRepo(t)
	ctx := scopedCtx("tenant-a", "project-claim-generation")
	_, err := repo.acquireSessionTurnClaimAt(
		ctx, "session-one", turnIDA, requestRefA, claimOwnerA, 1_000, 10*time.Second,
	)
	require.NoError(t, err)
	_, err = db.Exec(`UPDATE session_turn_claims
		SET generation = ?, lease_until_unix = ?
		WHERE tenant_id = ? AND project_id = ? AND session_id = ? AND turn_id = ?`,
		maxSessionTurnClaimGeneration, 1_000,
		"tenant-a", "project-claim-generation", "session-one", turnIDA)
	require.NoError(t, err)

	_, err = repo.acquireSessionTurnClaimAt(
		ctx, "session-one", turnIDA, requestRefA, claimOwnerB, 1_001, 10*time.Second,
	)
	require.ErrorIs(t, err, memory.ErrSessionTurnClaimIntegrity)
}

func TestStoredCompletedSessionTurnClaimFactIDIsBounded(t *testing.T) {
	for _, tc := range []struct {
		name    string
		factID  string
		wantErr bool
	}{
		{name: "one byte", factID: "f"},
		{name: "256 bytes", factID: strings.Repeat("f", 256)},
		{name: "empty", factID: "", wantErr: true},
		{name: "257 bytes", factID: strings.Repeat("f", 257), wantErr: true},
	} {
		t.Run(tc.name, func(t *testing.T) {
			stored := &storedSessionTurnClaim{
				requestRef:           requestRefA,
				state:                memory.SessionTurnCompleted,
				generation:           1,
				completedFactID:      sql.NullString{String: tc.factID, Valid: true},
				completedFactPresent: true,
				createdAt:            1,
				updatedAt:            1,
				schemaVersion:        sessionTurnClaimSchemaVersion,
			}
			err := validateStoredSessionTurnClaim(stored)
			if tc.wantErr {
				require.ErrorIs(t, err, memory.ErrSessionTurnClaimIntegrity)
				return
			}
			require.NoError(t, err)
		})
	}
}

func TestLegacyOversizedCompletedFactIDFailsBeforeValueMaterialization(t *testing.T) {
	db, repo := newTurnClaimRepo(t)
	ctx := scopedCtx("tenant-a", "project-legacy-oversized-claim")
	oversizedFactID := strings.Repeat("legacy-oversized-fact-id", 100_000)

	_, err := db.Exec(`DROP TRIGGER ` + sessionTurnClaimFactIDInsertBoundTrigger)
	require.NoError(t, err)
	_, err = db.Exec(`PRAGMA ignore_check_constraints=ON`)
	require.NoError(t, err)
	_, err = db.Exec(`INSERT INTO session_turn_claims
		(tenant_id, project_id, session_id, turn_id, request_ref, state,
		 owner_token, generation, lease_until_unix, execution_started_unix,
		 uncertainty_deadline_unix, completed_fact_id, created_at_unix,
		 updated_at_unix, schema_version)
		VALUES (?, ?, ?, ?, ?, 'COMPLETED', NULL, 1, NULL, NULL, NULL, ?, 1, 1, 1)`,
		"tenant-a", "project-legacy-oversized-claim", "session-one", turnIDA,
		requestRefA, oversizedFactID)
	require.NoError(t, err)
	_, err = db.Exec(`PRAGMA ignore_check_constraints=OFF`)
	require.NoError(t, err)

	runtime.GC()
	var before, after runtime.MemStats
	runtime.ReadMemStats(&before)
	_, err = repo.acquireSessionTurnClaimAt(
		ctx, "session-one", turnIDA, requestRefA, claimOwnerA, 1_000, 10*time.Second,
	)
	runtime.ReadMemStats(&after)
	require.ErrorIs(t, err, memory.ErrSessionTurnClaimIntegrity)
	require.NotContains(t, err.Error(), "legacy-oversized-fact-id")
	require.Less(t, after.TotalAlloc-before.TotalAlloc, uint64(64<<10),
		"the bounded loader must not allocate the corrupt legacy identity")
}

func TestSessionTurnClaimSchemaRejectsOversizedCompletedFactIDAtomically(t *testing.T) {
	db, repo := newTurnClaimRepo(t)
	ctx := scopedCtx("tenant-a", "project-claim-bounded-fact")
	_, err := repo.acquireSessionTurnClaimAt(
		ctx, "session-one", turnIDA, requestRefA, claimOwnerA, 1_000, 10*time.Second,
	)
	require.NoError(t, err)

	fact := memory.NewFact("synthetic completed response", memory.LevelDomain, "conversation", "chat")
	fact.ID = strings.Repeat("f", 257)
	fact.CodeRef = requestRefA
	fact.Source = "session_memory"
	fact.Origin = memory.OriginDerived
	_, _, err = repo.AddTurnForSession(ctx, "session-one", turnIDA, fact)
	require.Error(t, err)

	var state string
	var completed sql.NullString
	require.NoError(t, db.QueryRow(`SELECT state, completed_fact_id
		FROM session_turn_claims
		WHERE tenant_id = ? AND project_id = ? AND session_id = ? AND turn_id = ?`,
		"tenant-a", "project-claim-bounded-fact", "session-one", turnIDA,
	).Scan(&state, &completed))
	require.Equal(t, string(memory.SessionTurnClaimed), state)
	require.False(t, completed.Valid)
	var facts, receipts int
	require.NoError(t, db.QueryRow(`SELECT COUNT(*) FROM hierarchical_facts
		WHERE tenant_id = ? AND project_id = ? AND session_id = ?`,
		"tenant-a", "project-claim-bounded-fact", "session-one").Scan(&facts))
	require.NoError(t, db.QueryRow(`SELECT COUNT(*) FROM session_turn_receipts
		WHERE tenant_id = ? AND project_id = ? AND session_id = ?`,
		"tenant-a", "project-claim-bounded-fact", "session-one").Scan(&receipts))
	require.Zero(t, facts)
	require.Zero(t, receipts)
}

func TestSessionTurnReceiptCompletesClaimInSameTransaction(t *testing.T) {
	db, repo := newTurnClaimRepo(t)
	ctx := scopedCtx("tenant-a", "project-claim-complete")
	_, err := repo.acquireSessionTurnClaimAt(
		ctx, "session-one", turnIDA, requestRefA, claimOwnerA, 1_000, 10*time.Second,
	)
	require.NoError(t, err)
	_, err = repo.beginSessionTurnExecutionAt(
		ctx, "session-one", turnIDA, requestRefA, claimOwnerA, 1_001, 100*time.Second,
	)
	require.NoError(t, err)

	fact := memory.NewFact("accepted provider response", memory.LevelDomain, "conversation", "chat")
	fact.Source = "session_memory"
	fact.Origin = memory.OriginDerived
	fact.CodeRef = requestRefA
	receipt, deduplicated, err := repo.AddTurnForSession(ctx, "session-one", turnIDA, fact)
	require.NoError(t, err)
	require.False(t, deduplicated)

	var state string
	var owner sqlNullString
	var completedFact string
	require.NoError(t, db.QueryRow(`SELECT state, owner_token, completed_fact_id
		FROM session_turn_claims
		WHERE tenant_id = ? AND project_id = ? AND session_id = ? AND turn_id = ?`,
		"tenant-a", "project-claim-complete", "session-one", turnIDA,
	).Scan(&state, &owner, &completedFact))
	require.Equal(t, string(memory.SessionTurnCompleted), state)
	require.False(t, owner.Valid)
	require.Equal(t, receipt.FactID, completedFact)

	retry, err := repo.acquireSessionTurnClaimAt(
		ctx, "session-one", turnIDA, requestRefA, claimOwnerB, 1_002, 10*time.Second,
	)
	require.NoError(t, err)
	require.Equal(t, memory.SessionTurnCompleted, retry.State)
	require.False(t, retry.Owned)
	require.Equal(t, receipt.FactID, retry.CompletedFactID)
}

// sqlNullString keeps this test's raw schema assertion explicit without
// coupling the public claim type to nullable persistence details.
type sqlNullString struct {
	String string
	Valid  bool
}

func (value *sqlNullString) Scan(src any) error {
	if src == nil {
		value.String = ""
		value.Valid = false
		return nil
	}
	text, ok := src.(string)
	if !ok {
		return fmt.Errorf("expected nullable string, got %T", src)
	}
	value.String = text
	value.Valid = true
	return nil
}

func TestSessionTurnClaimReconcilesReceiptCommittedBeforeClaimSchemaUse(t *testing.T) {
	_, repo := newTurnClaimRepo(t)
	ctx := scopedCtx("tenant-a", "project-legacy-receipt")
	fact := memory.NewFact("receipt before dispatch claim", memory.LevelDomain, "conversation", "chat")
	fact.Source = "session_memory"
	fact.Origin = memory.OriginDerived
	fact.CodeRef = requestRefA
	receipt, _, err := repo.AddTurnForSession(ctx, "session-one", turnIDA, fact)
	require.NoError(t, err)

	claim, err := repo.acquireSessionTurnClaimAt(
		ctx, "session-one", turnIDA, requestRefA, claimOwnerA, 1_000, 10*time.Second,
	)
	require.NoError(t, err)
	require.Equal(t, memory.SessionTurnCompleted, claim.State)
	require.False(t, claim.Owned)
	require.Equal(t, receipt.FactID, claim.CompletedFactID)
}

func TestSessionTurnClaimStartupRejectsInertSameNameReceiptTrigger(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "inert-claim-trigger.db")
	db, err := Open(dbPath)
	require.NoError(t, err)
	_, err = NewFactRepo(db)
	require.NoError(t, err)
	_, err = db.Exec(`DROP TRIGGER ` + sessionTurnClaimReceiptTrigger)
	require.NoError(t, err)
	_, err = db.Exec(`CREATE TRIGGER ` + sessionTurnClaimReceiptTrigger + `
		AFTER INSERT ON session_turn_receipts BEGIN SELECT 1; END`)
	require.NoError(t, err)
	require.NoError(t, db.Close())

	reopened, err := Open(dbPath)
	require.NoError(t, err)
	defer reopened.Close()
	_, err = NewFactRepo(reopened)
	require.ErrorContains(t, err, "matching receipt did not complete claim")
}

func TestSessionTurnClaimStartupRejectsSameNameReceiptTriggerWithoutExactScope(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "broad-claim-trigger.db")
	db, err := Open(dbPath)
	require.NoError(t, err)
	_, err = NewFactRepo(db)
	require.NoError(t, err)
	_, err = db.Exec(`DROP TRIGGER ` + sessionTurnClaimReceiptTrigger)
	require.NoError(t, err)
	_, err = db.Exec(`CREATE TRIGGER ` + sessionTurnClaimReceiptTrigger + `
		AFTER INSERT ON session_turn_receipts
		BEGIN
			UPDATE session_turn_claims
			SET state = 'COMPLETED', owner_token = NULL, lease_until_unix = NULL,
				completed_fact_id = NEW.fact_id,
				updated_at_unix = CAST(strftime('%s', 'now') AS INTEGER)
			WHERE turn_id = NEW.turn_id
			  AND request_ref = (
				SELECT code_ref FROM hierarchical_facts
				WHERE tenant_id = NEW.tenant_id AND project_id = NEW.project_id
				  AND session_id = NEW.session_id AND id = NEW.fact_id
			  );
		END`)
	require.NoError(t, err)
	require.NoError(t, db.Close())

	reopened, err := Open(dbPath)
	require.NoError(t, err)
	defer reopened.Close()
	_, err = NewFactRepo(reopened)
	require.ErrorContains(t, err, "sibling scope")
}

func TestSessionTurnClaimStartupRejectsSameNameReceiptTriggerWithoutExactTurn(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "broad-turn-claim-trigger.db")
	db, err := Open(dbPath)
	require.NoError(t, err)
	_, err = NewFactRepo(db)
	require.NoError(t, err)
	_, err = db.Exec(`DROP TRIGGER ` + sessionTurnClaimReceiptTrigger)
	require.NoError(t, err)
	_, err = db.Exec(`CREATE TRIGGER ` + sessionTurnClaimReceiptTrigger + `
		AFTER INSERT ON session_turn_receipts
		BEGIN
			UPDATE session_turn_claims
			SET state = 'COMPLETED', owner_token = NULL, lease_until_unix = NULL,
				completed_fact_id = NEW.fact_id,
				updated_at_unix = CAST(strftime('%s', 'now') AS INTEGER)
			WHERE tenant_id = NEW.tenant_id
			  AND project_id = NEW.project_id
			  AND session_id = NEW.session_id
			  AND request_ref = (
				SELECT code_ref FROM hierarchical_facts
				WHERE tenant_id = NEW.tenant_id AND project_id = NEW.project_id
				  AND session_id = NEW.session_id AND id = NEW.fact_id
			  );
		END`)
	require.NoError(t, err)
	require.NoError(t, db.Close())

	reopened, err := Open(dbPath)
	require.NoError(t, err)
	defer reopened.Close()
	_, err = NewFactRepo(reopened)
	require.ErrorContains(t, err, "sibling turn")
}

func TestSessionTurnClaimStartupRejectsSameNameReceiptTriggerWithCaseFoldedScope(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "nocase-claim-trigger.db")
	db, err := Open(dbPath)
	require.NoError(t, err)
	_, err = NewFactRepo(db)
	require.NoError(t, err)
	_, err = db.Exec(`DROP TRIGGER ` + sessionTurnClaimReceiptTrigger)
	require.NoError(t, err)
	_, err = db.Exec(`CREATE TRIGGER ` + sessionTurnClaimReceiptTrigger + `
		AFTER INSERT ON session_turn_receipts
		BEGIN
			UPDATE session_turn_claims
			SET state = 'COMPLETED', owner_token = NULL, lease_until_unix = NULL,
				completed_fact_id = NEW.fact_id,
				updated_at_unix = CAST(strftime('%s', 'now') AS INTEGER)
			WHERE tenant_id = NEW.tenant_id COLLATE NOCASE
			  AND project_id = NEW.project_id COLLATE BINARY
			  AND session_id = NEW.session_id COLLATE BINARY
			  AND turn_id = NEW.turn_id COLLATE BINARY
			  AND request_ref = (
				SELECT code_ref FROM hierarchical_facts
				WHERE tenant_id = NEW.tenant_id AND project_id = NEW.project_id
				  AND session_id = NEW.session_id AND id = NEW.fact_id
			  );
		END`)
	require.NoError(t, err)
	require.NoError(t, db.Close())

	reopened, err := Open(dbPath)
	require.NoError(t, err)
	defer reopened.Close()
	_, err = NewFactRepo(reopened)
	require.ErrorContains(t, err, "case-variant scope")
}

func TestSessionTurnClaimStartupRejectsPartialSameNameTable(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "partial-claim-table.db")
	db, err := Open(dbPath)
	require.NoError(t, err)
	_, err = db.Exec(`CREATE TABLE session_turn_claims (
		tenant_id TEXT NOT NULL,
		project_id TEXT NOT NULL,
		session_id TEXT NOT NULL,
		turn_id TEXT NOT NULL,
		PRIMARY KEY (tenant_id, project_id, session_id, turn_id)
	)`)
	require.NoError(t, err)
	_, err = NewFactRepo(db)
	require.Error(t, err)
	require.Contains(t, err.Error(), "session_turn_claims")
	require.NoError(t, db.Close())
}

func TestSessionTurnClaimClosedDatabaseBackupRestorePreservesExecution(t *testing.T) {
	root := t.TempDir()
	sourcePath := filepath.Join(root, "source.db")
	restoredPath := filepath.Join(root, "restored.db")
	db, err := Open(sourcePath)
	require.NoError(t, err)
	repo, err := NewFactRepo(db)
	require.NoError(t, err)
	ctx := scopedCtx("tenant-a", "project-backup-claim")
	_, err = repo.acquireSessionTurnClaimAt(
		ctx, "session-one", turnIDA, requestRefA, claimOwnerA, 1_000, 100*time.Second,
	)
	require.NoError(t, err)
	_, err = repo.beginSessionTurnExecutionAt(
		ctx, "session-one", turnIDA, requestRefA, claimOwnerA, 1_001, 100*time.Second,
	)
	require.NoError(t, err)
	require.NoError(t, db.Close())

	backupBytes, err := os.ReadFile(sourcePath)
	require.NoError(t, err)
	require.NoError(t, os.WriteFile(restoredPath, backupBytes, 0o600))
	restoredDB, err := Open(restoredPath)
	require.NoError(t, err)
	defer restoredDB.Close()
	restoredRepo, err := NewFactRepo(restoredDB)
	require.NoError(t, err)
	restored, err := restoredRepo.acquireSessionTurnClaimAt(
		ctx, "session-one", turnIDA, requestRefA, claimOwnerB, 1_002, 100*time.Second,
	)
	require.NoError(t, err)
	require.Equal(t, memory.SessionTurnExecuting, restored.State)
	require.False(t, restored.Owned)
}

func TestSessionTurnClaimWholeTenantErasureRemovesClaimHistory(t *testing.T) {
	tenantDir := filepath.Join(t.TempDir(), ".rlm-tenant-a")
	dbPath := filepath.Join(tenantDir, "memory_bridge_v2.db")
	db, err := Open(dbPath)
	require.NoError(t, err)
	repo, err := NewFactRepo(db)
	require.NoError(t, err)
	ctx := scopedCtx("tenant-a", "project-erasure-claim")
	_, err = repo.acquireSessionTurnClaimAt(
		ctx, "session-one", turnIDA, requestRefA, claimOwnerA, 1_000, 100*time.Second,
	)
	require.NoError(t, err)
	require.NoError(t, db.Close())
	require.NoError(t, os.RemoveAll(tenantDir))
	require.NoDirExists(t, tenantDir)

	recreatedDB, err := Open(dbPath)
	require.NoError(t, err)
	defer recreatedDB.Close()
	recreatedRepo, err := NewFactRepo(recreatedDB)
	require.NoError(t, err)
	fresh, err := recreatedRepo.acquireSessionTurnClaimAt(
		ctx, "session-one", turnIDA, requestRefA, claimOwnerB, 1_001, 100*time.Second,
	)
	require.NoError(t, err)
	require.Equal(t, memory.SessionTurnClaimed, fresh.State)
	require.True(t, fresh.Owned)
	require.Equal(t, int64(1), fresh.Generation)
}

type turnClaimHelperResult struct {
	Claim *memory.SessionTurnClaim `json:"claim,omitempty"`
	Error string                   `json:"error,omitempty"`
}

func TestSessionTurnClaimProcessHelper(t *testing.T) {
	if os.Getenv("SPECTORN_TURN_CLAIM_HELPER") != "1" {
		t.Skip("subprocess helper")
	}
	dbPath := os.Getenv("SPECTORN_TURN_CLAIM_DB")
	owner := os.Getenv("SPECTORN_TURN_CLAIM_OWNER")
	operation := os.Getenv("SPECTORN_TURN_CLAIM_OPERATION")
	now, err := strconv.ParseInt(os.Getenv("SPECTORN_TURN_CLAIM_NOW"), 10, 64)
	if err != nil {
		fmt.Printf("{\"error\":%q}\n", err.Error())
		os.Exit(0)
	}
	db, err := Open(dbPath)
	if err != nil {
		fmt.Printf("{\"error\":%q}\n", err.Error())
		os.Exit(0)
	}
	repo, err := NewFactRepo(db)
	if err != nil {
		fmt.Printf("{\"error\":%q}\n", err.Error())
		os.Exit(0)
	}
	if readyPath, gatePath := os.Getenv("SPECTORN_TURN_CLAIM_READY"), os.Getenv("SPECTORN_TURN_CLAIM_GATE"); readyPath != "" || gatePath != "" {
		if readyPath == "" || gatePath == "" {
			fmt.Println(`{"error":"incomplete process barrier"}`)
			os.Exit(0)
		}
		if err := os.WriteFile(readyPath, []byte("ready"), 0o600); err != nil {
			fmt.Printf("{\"error\":%q}\n", err.Error())
			os.Exit(0)
		}
		deadline := time.Now().Add(5 * time.Second)
		for {
			if _, err := os.Stat(gatePath); err == nil {
				break
			} else if !os.IsNotExist(err) {
				fmt.Printf("{\"error\":%q}\n", err.Error())
				os.Exit(0)
			}
			if time.Now().After(deadline) {
				fmt.Println(`{"error":"process barrier timeout"}`)
				os.Exit(0)
			}
			time.Sleep(time.Millisecond)
		}
	}
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-process-claim"))
	claim, err := repo.acquireSessionTurnClaimAt(
		ctx, "session-one", turnIDA, requestRefA, owner, now, 100*time.Second,
	)
	if err == nil && operation == "acquire_begin" && claim.Owned {
		claim, err = repo.beginSessionTurnExecutionAt(
			ctx, "session-one", turnIDA, requestRefA, owner, now+1, 100*time.Second,
		)
	}
	result := turnClaimHelperResult{Claim: claim}
	if err != nil {
		result.Error = err.Error()
	}
	encoded, _ := json.Marshal(result)
	fmt.Println(string(encoded))
	// Do not Close: process exit is the crash boundary under test. SQLite must
	// leave the durable EXECUTING row while releasing process-local locks.
	os.Exit(0)
}

func newTurnClaimHelperCommand(
	dbPath, owner, operation string,
	now int64,
	readyPath, gatePath string,
) *exec.Cmd {
	command := exec.Command(os.Args[0], "-test.run=^TestSessionTurnClaimProcessHelper$")
	command.Env = append(os.Environ(),
		"SPECTORN_TURN_CLAIM_HELPER=1",
		"SPECTORN_TURN_CLAIM_DB="+dbPath,
		"SPECTORN_TURN_CLAIM_OWNER="+owner,
		"SPECTORN_TURN_CLAIM_OPERATION="+operation,
		fmt.Sprintf("SPECTORN_TURN_CLAIM_NOW=%d", now),
		"SPECTORN_TURN_CLAIM_READY="+readyPath,
		"SPECTORN_TURN_CLAIM_GATE="+gatePath,
	)
	return command
}

func decodeTurnClaimHelperOutput(t *testing.T, output []byte) *memory.SessionTurnClaim {
	t.Helper()
	var result turnClaimHelperResult
	require.NoError(t, json.Unmarshal([]byte(strings.TrimSpace(string(output))), &result), string(output))
	require.Empty(t, result.Error)
	require.NotNil(t, result.Claim)
	return result.Claim
}

func runTurnClaimHelper(
	t *testing.T,
	dbPath, owner, operation string,
	now int64,
) *memory.SessionTurnClaim {
	t.Helper()
	command := newTurnClaimHelperCommand(dbPath, owner, operation, now, "", "")
	output, err := command.CombinedOutput()
	require.NoError(t, err, string(output))
	return decodeTurnClaimHelperOutput(t, output)
}

func TestSessionTurnClaimSurvivesProcessCrashAndNeverStealsExecution(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "process-crash-claim.db")
	db, err := Open(dbPath)
	require.NoError(t, err)
	_, err = NewFactRepo(db)
	require.NoError(t, err)
	require.NoError(t, db.Close())

	executing := runTurnClaimHelper(t, dbPath, claimOwnerA, "acquire_begin", 1_000)
	require.Equal(t, memory.SessionTurnExecuting, executing.State)
	require.True(t, executing.Owned)

	afterCrash := runTurnClaimHelper(t, dbPath, claimOwnerB, "acquire", 1_002)
	require.Equal(t, memory.SessionTurnExecuting, afterCrash.State)
	require.False(t, afterCrash.Owned)
	require.Equal(t, executing.Generation, afterCrash.Generation)

	stale := runTurnClaimHelper(t, dbPath, claimOwnerC, "acquire", 1_101)
	require.Equal(t, memory.SessionTurnUncertain, stale.State)
	require.False(t, stale.Owned)
	require.Equal(t, executing.Generation, stale.Generation)
}

func TestSessionTurnClaimOnlyOneProcessOwnsFreshClaim(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "process-race-claim.db")
	db, err := Open(dbPath)
	require.NoError(t, err)
	_, err = NewFactRepo(db)
	require.NoError(t, err)
	require.NoError(t, db.Close())

	readyA := filepath.Join(filepath.Dir(dbPath), "ready-a")
	readyB := filepath.Join(filepath.Dir(dbPath), "ready-b")
	gate := filepath.Join(filepath.Dir(dbPath), "gate")
	owners := []string{claimOwnerA, claimOwnerB}
	readyPaths := []string{readyA, readyB}
	commands := make([]*exec.Cmd, 2)
	outputs := make([]bytes.Buffer, 2)
	for index := range commands {
		commands[index] = newTurnClaimHelperCommand(
			dbPath, owners[index], "acquire", 2_000, readyPaths[index], gate,
		)
		commands[index].Stdout = &outputs[index]
		commands[index].Stderr = &outputs[index]
		require.NoError(t, commands[index].Start())
		deadline := time.Now().Add(5 * time.Second)
		for {
			if _, err := os.Stat(readyPaths[index]); err == nil {
				break
			} else if !os.IsNotExist(err) {
				require.NoError(t, err)
			}
			require.True(t, time.Now().Before(deadline), "child %d did not reach process barrier", index)
			time.Sleep(time.Millisecond)
		}
	}
	require.NoError(t, os.WriteFile(gate, []byte("go"), 0o600))
	outcomes := make([]*memory.SessionTurnClaim, 2)
	for index, command := range commands {
		require.NoError(t, command.Wait(), outputs[index].String())
		outcomes[index] = decodeTurnClaimHelperOutput(t, outputs[index].Bytes())
	}

	owned := 0
	for _, outcome := range outcomes {
		require.Equal(t, memory.SessionTurnClaimed, outcome.State)
		if outcome.Owned {
			owned++
		}
	}
	require.Equal(t, 1, owned)
}
