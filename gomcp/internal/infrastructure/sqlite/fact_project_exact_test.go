package sqlite

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/stretchr/testify/require"

	"github.com/syntrex/gomcp/internal/domain/memory"
)

func exactProjectTestFact(content, domain, module string, origin memory.Origin) *memory.Fact {
	fact := memory.NewFact(content, memory.LevelDomain, domain, module)
	fact.Source = "add_fact"
	fact.Origin = origin
	return fact
}

func TestFactRepoStoreProjectFactExactReturnsOnlyDurableRows(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := NewFactRepo(db)
	require.NoError(t, err)
	ctx := scopedCtx("tenant-a", "project-exact")

	incoming := exactProjectTestFact("durable exact fact", "billing", "invoice", memory.OriginUser)
	incomingID := incoming.ID
	stored, created, err := repo.StoreProjectFactExact(ctx, incoming)
	require.NoError(t, err)
	require.True(t, created)
	require.NotSame(t, incoming, stored)
	require.Equal(t, incomingID, stored.ID)
	require.Equal(t, "tenant-a", stored.TenantID)
	require.Equal(t, "project-exact", stored.ProjectID)
	require.Equal(t, "invoice", stored.Module)
	require.Equal(t, memory.OriginUser, stored.Origin)
	require.Empty(t, incoming.TenantID, "the caller-owned handle must not be stamped")
	require.Empty(t, incoming.ProjectID, "the caller-owned handle must not be stamped")

	const untouched = "2001-02-03T04:05:06Z"
	_, err = repo.db.Exec(`UPDATE rlm_projects SET last_accessed_at = ?
		WHERE tenant_id = ? AND project_id = ?`, untouched, "tenant-a", "project-exact")
	require.NoError(t, err)

	retry := exactProjectTestFact("durable exact fact", "billing", "invoice", memory.OriginUser)
	retryID := retry.ID
	replayed, created, err := repo.StoreProjectFactExact(ctx, retry)
	require.NoError(t, err)
	require.False(t, created)
	require.NotSame(t, retry, replayed)
	require.Equal(t, stored.ID, replayed.ID)
	require.Equal(t, retryID, retry.ID, "a replay must not rewrite the caller-owned id")
	var lastAccessed string
	require.NoError(t, repo.db.QueryRow(`SELECT last_accessed_at FROM rlm_projects
		WHERE tenant_id = ? AND project_id = ?`, "tenant-a", "project-exact").Scan(&lastAccessed))
	require.Equal(t, untouched, lastAccessed, "an equal collision must not touch the project")

	for name, conflict := range map[string]*memory.Fact{
		"module": exactProjectTestFact("durable exact fact", "billing", "ledger", memory.OriginUser),
		"origin": exactProjectTestFact("durable exact fact", "billing", "invoice", memory.OriginExternal),
	} {
		t.Run(name, func(t *testing.T) {
			_, created, err := repo.StoreProjectFactExact(ctx, conflict)
			require.ErrorIs(t, err, memory.ErrExactFactConflict)
			require.False(t, created)
		})
	}

	durable, err := repo.Get(ctx, stored.ID)
	require.NoError(t, err)
	require.Equal(t, "invoice", durable.Module)
	require.Equal(t, memory.OriginUser, durable.Origin)
	require.NoError(t, repo.db.QueryRow(`SELECT last_accessed_at FROM rlm_projects
		WHERE tenant_id = ? AND project_id = ?`, "tenant-a", "project-exact").Scan(&lastAccessed))
	require.Equal(t, untouched, lastAccessed, "a conflict must not touch the project")
	var rows int
	require.NoError(t, repo.db.QueryRow(`SELECT COUNT(*) FROM hierarchical_facts
		WHERE tenant_id = ? AND project_id = ?`, "tenant-a", "project-exact").Scan(&rows))
	require.Equal(t, 1, rows)
}

func TestFactRepoStoreProjectFactExactClosesLegacyCallerHandleGap(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := NewFactRepo(db)
	require.NoError(t, err)
	ctx := scopedCtx("tenant-a", "project-handle-gap")

	seed := exactProjectTestFact("same legacy identity", "billing", "stored-module", memory.OriginExternal)
	require.NoError(t, repo.Add(ctx, seed))
	legacyRetry := exactProjectTestFact("same legacy identity", "billing", "incoming-module", memory.OriginExternal)
	require.NoError(t, repo.Add(ctx, legacyRetry))
	require.Equal(t, seed.ID, legacyRetry.ID)
	require.Equal(t, "incoming-module", legacyRetry.Module,
		"baseline: legacy Add leaves the caller-owned module on the folded handle")
	durable, err := repo.Get(ctx, seed.ID)
	require.NoError(t, err)
	require.Equal(t, "stored-module", durable.Module,
		"baseline: the legacy handle does not attest the durable module")

	exactRetry := exactProjectTestFact("same legacy identity", "billing", "incoming-module", memory.OriginExternal)
	returned, created, err := repo.StoreProjectFactExact(ctx, exactRetry)
	require.ErrorIs(t, err, memory.ErrExactFactConflict)
	require.False(t, created)
	require.Nil(t, returned)
	after, err := repo.Get(ctx, seed.ID)
	require.NoError(t, err)
	require.Equal(t, durable, after, "exact conflict must leave the durable row byte-for-byte unchanged")
}

func TestFactRepoStoreProjectFactExactIgnoresArchivedAndStaleRows(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := NewFactRepo(db)
	require.NoError(t, err)
	ctx := scopedCtx("tenant-a", "project-lifecycle")

	first, created, err := repo.StoreProjectFactExact(ctx,
		exactProjectTestFact("repeat after lifecycle", "ops", "worker", memory.OriginDerived))
	require.NoError(t, err)
	require.True(t, created)
	_, err = repo.db.Exec(`UPDATE hierarchical_facts SET is_archived = 1 WHERE id = ?`, first.ID)
	require.NoError(t, err)

	second, created, err := repo.StoreProjectFactExact(ctx,
		exactProjectTestFact("repeat after lifecycle", "ops", "worker", memory.OriginDerived))
	require.NoError(t, err)
	require.True(t, created, "an archived row is not a live legacy-key collision")
	require.NotEqual(t, first.ID, second.ID)
	_, err = repo.db.Exec(`UPDATE hierarchical_facts SET is_stale = 1 WHERE id = ?`, second.ID)
	require.NoError(t, err)

	third, created, err := repo.StoreProjectFactExact(ctx,
		exactProjectTestFact("repeat after lifecycle", "ops", "worker", memory.OriginDerived))
	require.NoError(t, err)
	require.True(t, created, "a stale row is not a live legacy-key collision")
	require.NotEqual(t, second.ID, third.ID)

	var total, live int
	require.NoError(t, repo.db.QueryRow(`SELECT COUNT(*),
		SUM(CASE WHEN is_archived = 0 AND is_stale = 0 THEN 1 ELSE 0 END)
		FROM hierarchical_facts WHERE tenant_id = ? AND project_id = ?
		  AND content = ? AND level = ? AND IFNULL(domain, '') = ?`,
		"tenant-a", "project-lifecycle", "repeat after lifecycle", int(memory.LevelDomain), "ops",
	).Scan(&total, &live))
	require.Equal(t, 3, total)
	require.Equal(t, 1, live)
}

func TestFactRepoStoreProjectFactExactRejectsArchivedProjectBeforeCollision(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := NewFactRepo(db)
	require.NoError(t, err)
	ctx := scopedCtx("tenant-a", "project-archived")

	stored, created, err := repo.StoreProjectFactExact(ctx,
		exactProjectTestFact("existing archived-project fact", "ops", "worker", memory.OriginExternal))
	require.NoError(t, err)
	require.True(t, created)
	const untouched = "2002-03-04T05:06:07Z"
	_, err = repo.db.Exec(`UPDATE rlm_projects
		SET status = ?, last_accessed_at = ? WHERE tenant_id = ? AND project_id = ?`,
		"archived", untouched, "tenant-a", "project-archived")
	require.NoError(t, err)

	for name, candidate := range map[string]*memory.Fact{
		"equal collision": exactProjectTestFact("existing archived-project fact", "ops", "worker", memory.OriginExternal),
		"new identity":    exactProjectTestFact("new archived-project fact", "ops", "worker", memory.OriginExternal),
	} {
		t.Run(name, func(t *testing.T) {
			_, created, err := repo.StoreProjectFactExact(ctx, candidate)
			require.ErrorIs(t, err, memory.ErrExactFactProjectArchived)
			require.False(t, created)
		})
	}

	var rows int
	require.NoError(t, repo.db.QueryRow(`SELECT COUNT(*) FROM hierarchical_facts
		WHERE tenant_id = ? AND project_id = ?`, "tenant-a", "project-archived").Scan(&rows))
	require.Equal(t, 1, rows)
	durable, err := repo.Get(ctx, stored.ID)
	require.NoError(t, err)
	require.Equal(t, "existing archived-project fact", durable.Content)
	var lastAccessed string
	require.NoError(t, repo.db.QueryRow(`SELECT last_accessed_at FROM rlm_projects
		WHERE tenant_id = ? AND project_id = ?`, "tenant-a", "project-archived").Scan(&lastAccessed))
	require.Equal(t, untouched, lastAccessed)
}

func TestFactRepoStoreProjectFactExactRollsBackFailedReloadValidation(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := NewFactRepo(db)
	require.NoError(t, err)
	_, err = repo.db.Exec(`CREATE TRIGGER corrupt_exact_project_insert
		AFTER INSERT ON hierarchical_facts
		WHEN NEW.content = 'corrupt exact insert'
		BEGIN
			DELETE FROM hierarchical_facts WHERE id = NEW.id;
		END`)
	require.NoError(t, err)

	ctx := scopedCtx("tenant-a", "project-rollback")
	incoming := exactProjectTestFact("corrupt exact insert", "ops", "expected", memory.OriginUser)
	_, created, err := repo.StoreProjectFactExact(ctx, incoming)
	require.ErrorIs(t, err, memory.ErrExactFactIntegrity)
	require.False(t, created)
	require.Empty(t, incoming.TenantID)

	var facts, projects int
	require.NoError(t, repo.db.QueryRow(`SELECT COUNT(*) FROM hierarchical_facts
		WHERE tenant_id = ? AND project_id = ?`, "tenant-a", "project-rollback").Scan(&facts))
	require.NoError(t, repo.db.QueryRow(`SELECT COUNT(*) FROM rlm_projects
		WHERE tenant_id = ? AND project_id = ?`, "tenant-a", "project-rollback").Scan(&projects))
	require.Zero(t, facts)
	require.Zero(t, projects, "the early project lock must roll back with the failed fact")
}

type exactProjectProcessResult struct {
	Fact      *memory.Fact `json:"fact,omitempty"`
	Created   bool         `json:"created"`
	ErrorCode string       `json:"error_code,omitempty"`
	Error     string       `json:"error,omitempty"`
}

func TestFactRepoStoreProjectFactExactProcessHelper(t *testing.T) {
	if os.Getenv("SPECTORN_PROJECT_EXACT_HELPER") != "1" {
		t.Skip("subprocess helper")
	}
	result := exactProjectProcessResult{}
	db, err := Open(os.Getenv("SPECTORN_PROJECT_EXACT_DB"))
	if err == nil {
		var repo *FactRepo
		repo, err = NewFactRepo(db)
		if err == nil {
			readyPath := os.Getenv("SPECTORN_PROJECT_EXACT_READY")
			gatePath := os.Getenv("SPECTORN_PROJECT_EXACT_GATE")
			if readyPath == "" || gatePath == "" {
				err = fmt.Errorf("incomplete exact project process barrier")
			} else if err = os.WriteFile(readyPath, []byte("ready"), 0o600); err == nil {
				deadline := time.Now().Add(10 * time.Second)
				for {
					if _, statErr := os.Stat(gatePath); statErr == nil {
						break
					} else if !os.IsNotExist(statErr) {
						err = statErr
						break
					}
					if time.Now().After(deadline) {
						err = fmt.Errorf("exact project process barrier timeout")
						break
					}
					time.Sleep(time.Millisecond)
				}
			}
			if err == nil {
				ctx := scopedCtx("tenant-a", os.Getenv("SPECTORN_PROJECT_EXACT_PROJECT"))
				fact := exactProjectTestFact(
					os.Getenv("SPECTORN_PROJECT_EXACT_CONTENT"),
					"race",
					os.Getenv("SPECTORN_PROJECT_EXACT_MODULE"),
					memory.OriginDerived,
				)
				result.Fact, result.Created, err = repo.StoreProjectFactExact(ctx, fact)
			}
		}
	}
	if err != nil {
		result.Error = err.Error()
		switch {
		case errors.Is(err, memory.ErrExactFactConflict):
			result.ErrorCode = "exact_fact_conflict"
		case errors.Is(err, memory.ErrExactFactIntegrity):
			result.ErrorCode = "exact_fact_integrity"
		default:
			result.ErrorCode = "other"
		}
	}
	encoded, _ := json.Marshal(result)
	fmt.Println(string(encoded))
	os.Exit(0)
}

func newExactProjectProcessCommand(
	dbPath, projectID, content, module, readyPath, gatePath string,
) *exec.Cmd {
	command := exec.Command(os.Args[0], "-test.run=^TestFactRepoStoreProjectFactExactProcessHelper$")
	command.Env = append(os.Environ(),
		"SPECTORN_PROJECT_EXACT_HELPER=1",
		"SPECTORN_PROJECT_EXACT_DB="+dbPath,
		"SPECTORN_PROJECT_EXACT_PROJECT="+projectID,
		"SPECTORN_PROJECT_EXACT_CONTENT="+content,
		"SPECTORN_PROJECT_EXACT_MODULE="+module,
		"SPECTORN_PROJECT_EXACT_READY="+readyPath,
		"SPECTORN_PROJECT_EXACT_GATE="+gatePath,
	)
	return command
}

func runExactProjectProcesses(
	t *testing.T,
	dbPath, projectID, content string,
	modules [2]string,
) [2]exactProjectProcessResult {
	t.Helper()
	tmpDir := filepath.Dir(dbPath)
	gatePath := filepath.Join(tmpDir, "exact-project-gate")
	var commands [2]*exec.Cmd
	var outputs [2]bytes.Buffer
	for index := range commands {
		readyPath := filepath.Join(tmpDir, fmt.Sprintf("exact-project-ready-%d", index))
		commands[index] = newExactProjectProcessCommand(
			dbPath, projectID, content, modules[index], readyPath, gatePath,
		)
		commands[index].Stdout = &outputs[index]
		commands[index].Stderr = &outputs[index]
		require.NoError(t, commands[index].Start())
		deadline := time.Now().Add(10 * time.Second)
		for {
			if _, err := os.Stat(readyPath); err == nil {
				break
			} else if !os.IsNotExist(err) {
				require.NoError(t, err)
			}
			require.True(t, time.Now().Before(deadline), "child %d did not reach process barrier", index)
			time.Sleep(time.Millisecond)
		}
	}
	require.NoError(t, os.WriteFile(gatePath, []byte("go"), 0o600))

	var outcomes [2]exactProjectProcessResult
	for index, command := range commands {
		require.NoError(t, command.Wait(), outputs[index].String())
		require.NoError(t, json.Unmarshal([]byte(strings.TrimSpace(outputs[index].String())), &outcomes[index]), outputs[index].String())
	}
	return outcomes
}

func initializeExactProjectProcessDB(t *testing.T, dbPath string) {
	t.Helper()
	db, err := Open(dbPath)
	require.NoError(t, err)
	_, err = NewFactRepo(db)
	require.NoError(t, err)
	require.NoError(t, db.Close())
}

func TestFactRepoStoreProjectFactExactTwoProcessesSamePayload(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "exact-project-same.db")
	initializeExactProjectProcessDB(t, dbPath)
	outcomes := runExactProjectProcesses(
		t, dbPath, "project-two-process-same", "same concurrent exact fact", [2]string{"worker", "worker"},
	)

	require.Empty(t, outcomes[0].Error)
	require.Empty(t, outcomes[1].Error)
	require.NotEqual(t, outcomes[0].Created, outcomes[1].Created)
	require.NotNil(t, outcomes[0].Fact)
	require.NotNil(t, outcomes[1].Fact)
	require.Equal(t, outcomes[0].Fact.ID, outcomes[1].Fact.ID)

	db, err := Open(dbPath)
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	var rows int
	require.NoError(t, db.QueryRow(`SELECT COUNT(*) FROM hierarchical_facts
		WHERE tenant_id = ? AND project_id = ? AND content = ? AND is_archived = 0 AND is_stale = 0`,
		"tenant-a", "project-two-process-same", "same concurrent exact fact").Scan(&rows))
	require.Equal(t, 1, rows)
}

func TestFactRepoStoreProjectFactExactTwoProcessesConflict(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "exact-project-conflict.db")
	initializeExactProjectProcessDB(t, dbPath)
	outcomes := runExactProjectProcesses(
		t, dbPath, "project-two-process-conflict", "conflicting concurrent exact fact",
		[2]string{"worker-a", "worker-b"},
	)

	successes := 0
	conflicts := 0
	var winner *memory.Fact
	for _, outcome := range outcomes {
		switch {
		case outcome.Error == "":
			successes++
			require.True(t, outcome.Created)
			require.NotNil(t, outcome.Fact)
			winner = outcome.Fact
		case outcome.ErrorCode == "exact_fact_conflict":
			conflicts++
			require.False(t, outcome.Created)
			require.Nil(t, outcome.Fact)
		default:
			require.Empty(t, outcome.Error)
		}
	}
	require.Equal(t, 1, successes)
	require.Equal(t, 1, conflicts)
	require.NotNil(t, winner)
	require.Contains(t, []string{"worker-a", "worker-b"}, winner.Module)

	db, err := Open(dbPath)
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	var rows int
	var durableModule string
	require.NoError(t, db.QueryRow(`SELECT COUNT(*), MIN(module) FROM hierarchical_facts
		WHERE tenant_id = ? AND project_id = ? AND content = ? AND is_archived = 0 AND is_stale = 0`,
		"tenant-a", "project-two-process-conflict", "conflicting concurrent exact fact").Scan(&rows, &durableModule))
	require.Equal(t, 1, rows)
	require.Equal(t, winner.Module, durableModule, "the losing process must not mutate the winner")
}

func TestFactRepoStoreProjectFactExactRejectsAmbiguousLegacyIdentity(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := NewFactRepo(db)
	require.NoError(t, err)
	ctx := scopedCtx("tenant-a", "project-ambiguous")

	now := time.Now().UTC().Format(timeFormat)
	for _, id := range []string{"legacy-one", "legacy-two"} {
		_, err := repo.db.Exec(`INSERT INTO hierarchical_facts
			(id, tenant_id, project_id, content, level, domain, module, created_at, valid_from,
			 is_stale, is_archived, confidence, source, origin)
			VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 1, 'add_fact', 'external')`,
			id, "tenant-a", "project-ambiguous", "ambiguous legacy fact", int(memory.LevelDomain),
			"race", "worker", now, now)
		require.NoError(t, err)
	}

	_, created, err := repo.StoreProjectFactExact(ctx,
		exactProjectTestFact("ambiguous legacy fact", "race", "worker", memory.OriginExternal))
	require.ErrorIs(t, err, memory.ErrExactFactIntegrity)
	require.False(t, created)
	var rows int
	require.NoError(t, repo.db.QueryRow(`SELECT COUNT(*) FROM hierarchical_facts
		WHERE tenant_id = ? AND project_id = ? AND content = ?`,
		"tenant-a", "project-ambiguous", "ambiguous legacy fact").Scan(&rows))
	require.Equal(t, 2, rows)
}
