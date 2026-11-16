package sqlite

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"strings"
	"testing"
	"time"

	"github.com/stretchr/testify/require"
	modernsqlite "modernc.org/sqlite"
	sqlitelib "modernc.org/sqlite/lib"

	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
)

func newFactPageRepo(t *testing.T) (*DB, *FactRepo) {
	t.Helper()
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := NewFactRepo(db)
	require.NoError(t, err)
	return db, repo
}

func TestFactExportSequenceTriggerMigrationIsAdditiveAndIdempotent(t *testing.T) {
	db, repo := newFactPageRepo(t)
	require.NotNil(t, repo)
	var probeFacts, probeMappings int
	require.NoError(t, db.SqlDB().QueryRow(`SELECT COUNT(*) FROM hierarchical_facts`).Scan(&probeFacts))
	require.NoError(t, db.SqlDB().QueryRow(`SELECT COUNT(*) FROM fact_export_sequence`).Scan(&probeMappings))
	require.Zero(t, probeFacts, "the startup behavior probe must roll back its facts")
	require.Zero(t, probeMappings, "the startup behavior probe must roll back its mappings")

	var triggerSQL string
	require.NoError(t, db.SqlDB().QueryRow(`SELECT sql FROM sqlite_master
		WHERE type = 'trigger' AND name = 'fact_export_sequence_update_payload_v1'`).Scan(&triggerSQL))
	require.Contains(t, triggerSQL, "AFTER UPDATE OF")
	require.Contains(t, triggerSQL, "created_at")
	require.Contains(t, triggerSQL, "hit_count")

	var schemaVersionBefore int64
	require.NoError(t, db.SqlDB().QueryRow(`PRAGMA schema_version`).Scan(&schemaVersionBefore))
	secondRepo, err := NewFactRepo(db)
	require.NoError(t, err)
	require.NotNil(t, secondRepo)
	var schemaVersionAfter int64
	require.NoError(t, db.SqlDB().QueryRow(`PRAGMA schema_version`).Scan(&schemaVersionAfter))
	require.Equal(t, schemaVersionBefore, schemaVersionAfter,
		"a repeat migration must not DROP and recreate the live export trigger")

	var triggerCount int
	require.NoError(t, db.SqlDB().QueryRow(`SELECT COUNT(*) FROM sqlite_master
		WHERE type = 'trigger' AND name LIKE 'fact_export_sequence_update_payload%'`).Scan(&triggerCount))
	require.Equal(t, 1, triggerCount)
}

func TestFactExportSequenceStartupBehaviorRejectsInertSameNameTriggers(t *testing.T) {
	testCases := []struct {
		name, triggerName, createSQL, expected string
	}{
		{
			name:        "insert",
			triggerName: "fact_export_sequence_insert_v1",
			createSQL: `CREATE TRIGGER fact_export_sequence_insert_v1
				AFTER INSERT ON hierarchical_facts WHEN 0 BEGIN SELECT 1; END`,
			expected: "INSERT trigger did not create parent mapping",
		},
		{
			name:        "payload update including hit_count",
			triggerName: "fact_export_sequence_update_payload_v1",
			createSQL: `CREATE TRIGGER fact_export_sequence_update_payload_v1
				AFTER UPDATE ON hierarchical_facts WHEN 0 BEGIN SELECT 1; END`,
			expected: "payload UPDATE trigger kept sequence",
		},
		{
			name:        "partial payload update",
			triggerName: "fact_export_sequence_update_payload_v1",
			createSQL: `CREATE TRIGGER fact_export_sequence_update_payload_v1
				AFTER UPDATE OF hit_count ON hierarchical_facts
				BEGIN
					DELETE FROM fact_export_sequence WHERE fact_id = OLD.id;
					INSERT INTO fact_export_sequence(fact_id) VALUES (NEW.id);
				END`,
			expected: "payload UPDATE trigger kept sequence",
		},
		{
			name:        "delete",
			triggerName: "fact_export_sequence_delete_v1",
			createSQL: `CREATE TRIGGER fact_export_sequence_delete_v1
				AFTER DELETE ON hierarchical_facts WHEN 0 BEGIN SELECT 1; END`,
			expected: "DELETE trigger retained",
		},
		{
			name:        "parent boundary update",
			triggerName: "fact_export_sequence_parent_boundary_update_v1",
			createSQL: `CREATE TRIGGER fact_export_sequence_parent_boundary_update_v1
				AFTER UPDATE ON hierarchical_facts WHEN 0 BEGIN SELECT 1; END`,
			expected: "parent boundary trigger kept child sequence",
		},
	}

	for _, testCase := range testCases {
		t.Run(testCase.name, func(t *testing.T) {
			db, repo := newFactPageRepo(t)
			_, err := db.Exec(`DROP TRIGGER ` + testCase.triggerName)
			require.NoError(t, err)
			_, err = db.Exec(testCase.createSQL)
			require.NoError(t, err)
			_, err = db.Exec(`UPDATE schema_info SET value = '3.3.0' WHERE key = 'version'`)
			require.NoError(t, err)

			err = repo.migrate()
			require.ErrorContains(t, err, testCase.expected)
			var facts, mappings int
			require.NoError(t, db.SqlDB().QueryRow(`SELECT COUNT(*) FROM hierarchical_facts`).Scan(&facts))
			require.NoError(t, db.SqlDB().QueryRow(`SELECT COUNT(*) FROM fact_export_sequence`).Scan(&mappings))
			require.Zero(t, facts, "a failed startup probe must roll back its facts")
			require.Zero(t, mappings, "a failed startup probe must roll back its mappings")
			var version string
			require.NoError(t, db.SqlDB().QueryRow(`SELECT value FROM schema_info WHERE key = 'version'`).Scan(&version))
			require.Equal(t, "3.3.0", version, "failed validation must not advance the schema version")
		})
	}
}

func addPageFact(t *testing.T, repo *FactRepo, ctx context.Context, id, content string, level memory.HierLevel, createdAt time.Time) *memory.Fact {
	t.Helper()
	fact := memory.NewFact(content, level, "paging", "")
	fact.ID = id
	fact.CreatedAt = createdAt
	fact.ValidFrom = createdAt
	fact.UpdatedAt = createdAt
	require.NoError(t, repo.Add(ctx, fact))
	return fact
}

func TestFactRepoExactPageUsesScopedNonSessionKeysetWithoutGaps(t *testing.T) {
	_, repo := newFactPageRepo(t)
	alpha := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-alpha"))
	beta := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-beta"))
	stamp := time.Date(2026, 1, 2, 3, 4, 5, 123456789, time.UTC)

	for _, id := range []string{"fact-c", "fact-a", "fact-b"} {
		addPageFact(t, repo, alpha, id, "alpha "+id, memory.LevelProject, stamp)
	}
	addPageFact(t, repo, alpha, "wrong-level", "wrong level", memory.LevelDomain, stamp)
	addPageFact(t, repo, beta, "wrong-project", "wrong project", memory.LevelProject, stamp)
	session := memory.NewFact("session fact", memory.LevelProject, "paging", "")
	session.ID = "wrong-session"
	session.CreatedAt = stamp
	session.ValidFrom = stamp
	require.NoError(t, repo.AddForSession(alpha, "session-one", session))

	var (
		snapshot      int64
		expectedCount int64
		after         *memory.FactPageKey
		got           []string
	)
	for {
		page, err := repo.ListByLevelPage(
			alpha, memory.LevelProject, memory.FactPageMaxSerializedBytes, snapshot, expectedCount, after,
		)
		require.NoError(t, err)
		require.NotNil(t, page)
		require.NotNil(t, page.Fact)
		if snapshot == 0 {
			snapshot = page.Snapshot
			expectedCount = page.ExpectedCount
			require.Positive(t, snapshot)
			require.EqualValues(t, 3, expectedCount)
		} else {
			require.Equal(t, snapshot, page.Snapshot)
			require.Equal(t, expectedCount, page.ExpectedCount)
		}
		require.Equal(t, page.Key.ID, page.Fact.ID)
		require.Equal(t, "tenant-a", page.Fact.TenantID)
		require.Equal(t, "project-alpha", page.Fact.ProjectID)
		require.Empty(t, page.Fact.SessionID)
		got = append(got, page.Fact.ID)
		if !page.HasMore {
			break
		}
		key := page.Key
		after = &key
	}
	require.Equal(t, []string{"fact-a", "fact-b", "fact-c"}, got)

	_, err := repo.ListByLevelPage(
		context.Background(), memory.LevelProject, memory.FactPageMaxSerializedBytes, 0, 0, nil,
	)
	require.Error(t, err, "the exact paginator must not invent local/default for a missing scope")
}

func TestFactRepoExactPagePreservesRawNonCanonicalTimestampKey(t *testing.T) {
	db, repo := newFactPageRepo(t)
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-alpha"))
	fact := addPageFact(t, repo, ctx, "fact-raw-time", "raw timestamp", memory.LevelProject,
		time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC))

	const rawCreatedAt = "2026-01-02T03:04:05.000Z"
	_, err := db.SqlDB().Exec(`UPDATE hierarchical_facts SET created_at = ?
		WHERE tenant_id = ? AND project_id = ? AND id = ?`,
		rawCreatedAt, "tenant-a", "project-alpha", fact.ID)
	require.NoError(t, err)

	page, err := repo.ListByLevelPage(ctx, memory.LevelProject, memory.FactPageMaxSerializedBytes, 0, 0, nil)
	require.NoError(t, err)
	require.NotNil(t, page.Fact)
	require.Equal(t, rawCreatedAt, page.Key.CreatedAt)
	require.Equal(t, fact.ID, page.Key.ID)

	reloaded, err := repo.GetByLevelPageKey(
		ctx, memory.LevelProject, memory.FactPageMaxSerializedBytes,
		page.Snapshot, page.ExpectedCount, page.Key, 0,
	)
	require.NoError(t, err)
	require.True(t, reloaded.Final)
	var reloadedFact memory.Fact
	require.NoError(t, json.Unmarshal(reloaded.Data, &reloadedFact))
	require.Equal(t, fact.ID, reloadedFact.ID)
	require.Equal(t, time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC), reloadedFact.CreatedAt)

	canonicalized := page.Key
	canonicalized.CreatedAt = reloadedFact.CreatedAt.Format(time.RFC3339Nano)
	_, err = repo.GetByLevelPageKey(
		ctx, memory.LevelProject, memory.FactPageMaxSerializedBytes,
		page.Snapshot, page.ExpectedCount, canonicalized, 0,
	)
	require.ErrorIs(t, err, memory.ErrFactPageChanged,
		"a cursor must use the raw SQLite key instead of formatting the parsed time")
}

func TestFactRepoExactPagePreflightsOversizedStoredRowBeforeMaterialization(t *testing.T) {
	maxStoredRowBytes, valid := memory.FactPageMaxStoredVariableBytes(memory.FactPageMaxSerializedBytes)
	require.True(t, valid)
	for _, testCase := range []struct {
		name, id, content, kind string
		sqliteLimit, hardLimit  int
	}{
		{
			name: "identity", id: strings.Repeat("i", 257), content: "small",
			kind: memory.BoundedSearchStoredIdentityOversizeKind, hardLimit: 256,
		},
		{
			name: "variable row", id: "oversized-fact", content: strings.Repeat("x", 16*1024*1024+1),
			kind: memory.BoundedSearchStoredRowOversizeKind, sqliteLimit: 16 * 1024 * 1024,
			hardLimit: int(maxStoredRowBytes),
		},
	} {
		t.Run(testCase.name, func(t *testing.T) {
			db, repo := newFactPageRepo(t)
			ctx := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-alpha"))
			addPageFact(t, repo, ctx, testCase.id, testCase.content,
				memory.LevelProject, time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC))

			if testCase.sqliteLimit > 0 {
				conn, err := db.SqlDB().Conn(ctx)
				require.NoError(t, err)
				previousLimit, err := modernsqlite.Limit(conn, sqlitelib.SQLITE_LIMIT_LENGTH, testCase.sqliteLimit)
				require.NoError(t, err)
				require.Greater(t, previousLimit, testCase.sqliteLimit)
				require.NoError(t, conn.Close())
			}

			_, err := repo.ListByLevelPage(
				ctx, memory.LevelProject, memory.FactPageMaxSerializedBytes, 0, 0, nil,
			)
			var oversized *memory.FactPageStoredOversizeError
			require.ErrorAs(t, err, &oversized,
				"metadata preflight must reject the row before SQLite materializes the key or factColumns")
			require.Equal(t, testCase.kind, oversized.Measurement.Kind)
			require.Greater(t, oversized.Measurement.StoredBytes, int64(testCase.hardLimit))
			require.EqualValues(t, testCase.hardLimit, oversized.Measurement.MaxStoredBytes)
		})
	}

	t.Run("record reload pins caller cap", func(t *testing.T) {
		_, repo := newFactPageRepo(t)
		ctx := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-alpha"))
		addPageFact(t, repo, ctx, "reload-cap", strings.Repeat("\x01", 100*1024),
			memory.LevelProject, time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC))

		page, err := repo.ListByLevelPage(ctx, memory.LevelProject, 4*1024*1024, 0, 0, nil)
		require.NoError(t, err)
		_, err = repo.GetByLevelPageKey(
			ctx, memory.LevelProject, 512*1024, page.Snapshot, page.ExpectedCount, page.Key, 0,
		)
		require.ErrorIs(t, err, memory.ErrFactPageChanged)
	})
}

func TestFactRepoExactPagePreflightBoundsWholeSnapshot(t *testing.T) {
	t.Run("stored bytes", func(t *testing.T) {
		db, repo := newFactPageRepo(t)
		ctx := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-alpha"))
		stamp := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC).Format(time.RFC3339Nano)
		for index := 0; index < 13; index++ {
			_, err := db.SqlDB().Exec(`INSERT INTO hierarchical_facts (
				id, tenant_id, project_id, content, level, embedding, created_at, valid_from
			) VALUES (?, ?, ?, ?, ?, zeroblob(?), ?, ?)`,
				fmt.Sprintf("scope-large-%d", index), "tenant-a", "project-alpha", "small",
				int(memory.LevelProject), 2600*1024, stamp, stamp,
			)
			require.NoError(t, err)
		}

		_, err := repo.ListByLevelPage(
			ctx, memory.LevelProject, memory.FactPageMaxSerializedBytes, 0, 0, nil,
		)
		var oversized *memory.FactPageStoredOversizeError
		require.ErrorAs(t, err, &oversized)
		require.Equal(t, memory.BoundedSearchStoredScopeOversizeKind, oversized.Measurement.Kind)
		require.Greater(t, oversized.Measurement.StoredBytes, int64(32*1024*1024))
		require.EqualValues(t, 32*1024*1024, oversized.Measurement.MaxStoredBytes)
	})

	t.Run("row count", func(t *testing.T) {
		db, repo := newFactPageRepo(t)
		ctx := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-alpha"))
		stamp := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC).Format(time.RFC3339Nano)
		_, err := db.SqlDB().Exec(`DROP TRIGGER fact_export_sequence_insert_v1`)
		require.NoError(t, err)
		_, err = db.SqlDB().Exec(`WITH RECURSIVE ids(value) AS (
			VALUES(1) UNION ALL SELECT value + 1 FROM ids WHERE value < 10001
		)
		INSERT INTO hierarchical_facts (
			id, tenant_id, project_id, content, level, created_at, valid_from
		)
		SELECT printf('fact-%05d', value), ?, ?, 'small', ?, ?, ? FROM ids`,
			"tenant-a", "project-alpha", int(memory.LevelProject), stamp, stamp,
		)
		require.NoError(t, err)
		_, err = db.SqlDB().Exec(`INSERT INTO fact_export_sequence(fact_id)
			SELECT id FROM hierarchical_facts ORDER BY id`)
		require.NoError(t, err)

		_, err = repo.ListByLevelPage(
			ctx, memory.LevelProject, memory.FactPageMaxSerializedBytes, 0, 0, nil,
		)
		var oversized *memory.FactPageStoredOversizeError
		require.ErrorAs(t, err, &oversized)
		require.Equal(t, memory.BoundedSearchStoredRowCountOversizeKind, oversized.Measurement.Kind)
		require.EqualValues(t, 10001, oversized.Measurement.StoredRows)
		require.EqualValues(t, 10000, oversized.Measurement.MaxStoredRows)
	})
}

func TestFactRepoExactPagePreflightPinsWorstCaseJSONExpansion(t *testing.T) {
	const maxFactBytes = 1024 * 1024
	maxStoredRowBytes, valid := memory.FactPageMaxStoredVariableBytes(maxFactBytes)
	require.True(t, valid)

	t.Run("control bytes below derived cap", func(t *testing.T) {
		_, repo := newFactPageRepo(t)
		ctx := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-alpha"))
		addPageFact(t, repo, ctx, "control-safe",
			strings.Repeat("\x01", int(maxStoredRowBytes)-1024), memory.LevelProject,
			time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC))

		page, err := repo.ListByLevelPage(ctx, memory.LevelProject, maxFactBytes, 0, 0, nil)
		require.NoError(t, err)
		serialized, err := json.Marshal(page.Fact)
		require.NoError(t, err)
		require.LessOrEqual(t, len(serialized), maxFactBytes)
	})

	t.Run("control bytes above derived cap", func(t *testing.T) {
		_, repo := newFactPageRepo(t)
		ctx := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-alpha"))
		addPageFact(t, repo, ctx, "control-oversized",
			strings.Repeat("\x01", int(maxStoredRowBytes)), memory.LevelProject,
			time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC))

		_, err := repo.ListByLevelPage(ctx, memory.LevelProject, maxFactBytes, 0, 0, nil)
		var oversized *memory.FactPageStoredOversizeError
		require.ErrorAs(t, err, &oversized)
		require.Equal(t, memory.BoundedSearchStoredRowOversizeKind, oversized.Measurement.Kind)
		require.Equal(t, maxStoredRowBytes, oversized.Measurement.MaxStoredBytes)
	})

	for _, testCase := range []struct {
		name   string
		margin int64
		passes bool
	}{
		{name: "embedding exponents below derived cap", margin: -16 * 1024, passes: true},
		{name: "embedding exponents above derived cap", margin: 16 * 1024, passes: false},
	} {
		t.Run(testCase.name, func(t *testing.T) {
			db, repo := newFactPageRepo(t)
			ctx := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-alpha"))
			stamp := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
			fact := memory.NewFact("x", memory.LevelProject, "paging", "")
			fact.ID = "embedding-exponents"
			fact.CreatedAt = stamp
			fact.ValidFrom = stamp
			fact.UpdatedAt = stamp
			fact.Embedding = make([]float64, int((maxStoredRowBytes+testCase.margin)/7))
			for index := range fact.Embedding {
				fact.Embedding[index] = 1e-300
			}
			require.NoError(t, repo.Add(ctx, fact))

			var storedBytes int64
			require.NoError(t, db.SqlDB().QueryRow(`SELECT `+boundedSearchStoredVariableBytesSQL+`
				FROM hierarchical_facts WHERE id = ?`, fact.ID).Scan(&storedBytes))
			page, err := repo.ListByLevelPage(ctx, memory.LevelProject, maxFactBytes, 0, 0, nil)
			if testCase.passes {
				require.LessOrEqual(t, storedBytes, maxStoredRowBytes)
				require.NoError(t, err)
				serialized, marshalErr := json.Marshal(page.Fact)
				require.NoError(t, marshalErr)
				require.LessOrEqual(t, len(serialized), maxFactBytes)
				return
			}
			require.Greater(t, storedBytes, maxStoredRowBytes)
			var oversized *memory.FactPageStoredOversizeError
			require.ErrorAs(t, err, &oversized)
			require.Equal(t, memory.BoundedSearchStoredRowOversizeKind, oversized.Measurement.Kind)
		})
	}
}

func TestFactRepoExactPageContinuationDoesNotRescanDeliveredRows(t *testing.T) {
	_, repo := newFactPageRepo(t)
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-alpha"))
	stamp := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
	delivered := addPageFact(t, repo, ctx, "fact-a", "first", memory.LevelProject, stamp)
	addPageFact(t, repo, ctx, "fact-b", "second", memory.LevelProject, stamp)

	first, err := repo.ListByLevelPage(
		ctx, memory.LevelProject, memory.FactPageMaxSerializedBytes, 0, 0, nil,
	)
	require.NoError(t, err)
	require.Equal(t, delivered.ID, first.Fact.ID)
	require.True(t, first.HasMore)

	delivered.Content = "already delivered row changed"
	require.NoError(t, repo.Update(ctx, delivered))

	second, err := repo.ListByLevelPage(
		ctx, memory.LevelProject, memory.FactPageMaxSerializedBytes,
		first.Snapshot, first.ExpectedCount, &first.Key,
	)
	require.NoError(t, err,
		"continuation must validate only its immutable manifest item, not rescan delivered rows")
	require.Equal(t, "fact-b", second.Fact.ID)
	require.False(t, second.HasMore)
}

func TestFactRepoExactPageReloadUsesCachedSerialization(t *testing.T) {
	db, repo := newFactPageRepo(t)
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-alpha"))
	addPageFact(t, repo, ctx, "large-fact", strings.Repeat("x", 600*1024),
		memory.LevelProject, time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC))

	page, err := repo.ListByLevelPage(ctx, memory.LevelProject, 4*1024*1024, 0, 0, nil)
	require.NoError(t, err)
	require.Equal(t, "large-fact", page.Fact.ID)

	conn, err := db.SqlDB().Conn(ctx)
	require.NoError(t, err)
	previousLimit, err := modernsqlite.Limit(conn, sqlitelib.SQLITE_LIMIT_LENGTH, 64*1024)
	require.NoError(t, err)
	require.Greater(t, previousLimit, 64*1024)
	require.NoError(t, conn.Close())

	reloaded, err := repo.GetByLevelPageKey(
		ctx, memory.LevelProject, 4*1024*1024,
		page.Snapshot, page.ExpectedCount, page.Key, memory.FactPageFrameRawBytes,
	)
	require.NoError(t, err,
		"an in-progress fact must use the canonical bytes cached after its first bounded materialization")
	require.Equal(t, "large-fact", reloaded.FactID)
	require.Equal(t, memory.FactPageFrameRawBytes, reloaded.Offset)
}

func TestFactRepoExactPagePreflightKeepsFrozenContinuationClosed(t *testing.T) {
	t.Run("post-freeze insert stays outside snapshot", func(t *testing.T) {
		_, repo := newFactPageRepo(t)
		ctx := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-alpha"))
		stamp := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
		addPageFact(t, repo, ctx, "fact-a", "first", memory.LevelProject, stamp)
		addPageFact(t, repo, ctx, "fact-b", "second", memory.LevelProject, stamp)

		first, err := repo.ListByLevelPage(
			ctx, memory.LevelProject, memory.FactPageMaxSerializedBytes, 0, 0, nil,
		)
		require.NoError(t, err)
		require.Equal(t, "fact-a", first.Fact.ID)
		addPageFact(t, repo, ctx, "late-oversized", strings.Repeat("x", 16*1024*1024+1),
			memory.LevelProject, stamp.Add(-time.Hour))

		second, err := repo.ListByLevelPage(
			ctx, memory.LevelProject, memory.FactPageMaxSerializedBytes,
			first.Snapshot, first.ExpectedCount, &first.Key,
		)
		require.NoError(t, err)
		require.Equal(t, "fact-b", second.Fact.ID)
		require.False(t, second.HasMore)
	})

	t.Run("frozen row mutation fails closed", func(t *testing.T) {
		_, repo := newFactPageRepo(t)
		ctx := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-alpha"))
		stamp := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
		addPageFact(t, repo, ctx, "fact-a", "first", memory.LevelProject, stamp)
		future := addPageFact(t, repo, ctx, "fact-b", "second", memory.LevelProject, stamp)

		first, err := repo.ListByLevelPage(
			ctx, memory.LevelProject, memory.FactPageMaxSerializedBytes, 0, 0, nil,
		)
		require.NoError(t, err)
		future.Content = strings.Repeat("x", 16*1024*1024+1)
		require.NoError(t, repo.Update(ctx, future))

		_, err = repo.ListByLevelPage(
			ctx, memory.LevelProject, memory.FactPageMaxSerializedBytes,
			first.Snapshot, first.ExpectedCount, &first.Key,
		)
		require.ErrorIs(t, err, memory.ErrFactPageChanged)
	})
}

func TestFactRepoExactPageDetectsDeleteMaxInsertAndFutureMutation(t *testing.T) {
	t.Run("delete max sequence then insert", func(t *testing.T) {
		db, repo := newFactPageRepo(t)
		ctx := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-alpha"))
		stamp := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
		first := addPageFact(t, repo, ctx, "fact-a", "first", memory.LevelProject, stamp)
		deleted := addPageFact(t, repo, ctx, "fact-z", "deleted max", memory.LevelProject, stamp)

		page, err := repo.ListByLevelPage(
			ctx, memory.LevelProject, memory.FactPageMaxSerializedBytes, 0, 0, nil,
		)
		require.NoError(t, err)
		require.Equal(t, first.ID, page.Fact.ID)
		require.True(t, page.HasMore)
		require.NoError(t, repo.Delete(ctx, deleted.ID))
		inserted := addPageFact(t, repo, ctx, "fact-new", "backdated replacement", memory.LevelProject, stamp.Add(-time.Hour))

		var insertedSequence int64
		require.NoError(t, db.SqlDB().QueryRow(`SELECT seq FROM fact_export_sequence WHERE fact_id = ?`, inserted.ID).Scan(&insertedSequence))
		require.Greater(t, insertedSequence, page.Snapshot,
			"AUTOINCREMENT must not reuse the deleted maximum sequence")

		_, err = repo.ListByLevelPage(
			ctx, memory.LevelProject, memory.FactPageMaxSerializedBytes,
			page.Snapshot, page.ExpectedCount, &page.Key,
		)
		require.Error(t, err)
		require.True(t, errors.Is(err, memory.ErrFactPageChanged), err)
	})

	t.Run("update a future row", func(t *testing.T) {
		_, repo := newFactPageRepo(t)
		ctx := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-alpha"))
		stamp := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
		first := addPageFact(t, repo, ctx, "fact-a", "first", memory.LevelProject, stamp)
		future := addPageFact(t, repo, ctx, "fact-z", "future", memory.LevelProject, stamp)

		page, err := repo.ListByLevelPage(
			ctx, memory.LevelProject, memory.FactPageMaxSerializedBytes, 0, 0, nil,
		)
		require.NoError(t, err)
		require.Equal(t, first.ID, page.Fact.ID)
		require.True(t, page.HasMore)

		future.Content = "future changed after the snapshot"
		require.NoError(t, repo.Update(ctx, future))
		_, err = repo.ListByLevelPage(
			ctx, memory.LevelProject, memory.FactPageMaxSerializedBytes,
			page.Snapshot, page.ExpectedCount, &page.Key,
		)
		require.ErrorIs(t, err, memory.ErrFactPageChanged)
	})

	t.Run("move a parent outside the child boundary", func(t *testing.T) {
		db, repo := newFactPageRepo(t)
		ctx := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-alpha"))
		stamp := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
		parent := addPageFact(t, repo, ctx, "parent", "parent", memory.LevelProject, stamp)
		child := memory.NewFact("child", memory.LevelDomain, "paging", "")
		child.ID = "child"
		child.ParentID = parent.ID
		child.CreatedAt = stamp
		child.ValidFrom = stamp
		require.NoError(t, repo.Add(ctx, child))

		page, err := repo.ListByLevelPage(
			ctx, memory.LevelDomain, memory.FactPageMaxSerializedBytes, 0, 0, nil,
		)
		require.NoError(t, err)
		require.NotNil(t, page.Fact)
		require.Equal(t, parent.ID, page.Fact.ParentID)

		_, err = db.SqlDB().Exec(`UPDATE hierarchical_facts SET project_id = ? WHERE id = ?`,
			"project-beta", parent.ID)
		require.NoError(t, err)
		_, err = repo.GetByLevelPageKey(
			ctx, memory.LevelDomain, memory.FactPageMaxSerializedBytes,
			page.Snapshot, page.ExpectedCount, page.Key, 0,
		)
		require.ErrorIs(t, err, memory.ErrFactPageChanged,
			"a parent boundary move changes the child's serialized parent_id and must invalidate the snapshot")
	})
}
