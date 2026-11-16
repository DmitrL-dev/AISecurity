package sqlite

import (
	"context"
	"database/sql"
	"fmt"
	"path/filepath"
	"strings"
	"testing"

	"github.com/stretchr/testify/require"

	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
)

func insertBoundedSearchPreflightProbe(
	t *testing.T,
	db *DB,
	id, tenantID, projectID, sessionID string,
	embeddingBytes int64,
) {
	t.Helper()
	_, err := db.ExecContext(context.Background(), `INSERT INTO hierarchical_facts (
		id, tenant_id, project_id, session_id, content, level, embedding,
		created_at, valid_from, is_stale, is_archived, confidence, source, origin
	) VALUES (?, ?, ?, ?, 'x', 0, zeroblob(?),
		'2026-09-01T00:00:00Z', '2026-09-01T00:00:00Z', 0, 0, 1.0, 'external-import', 'external')`,
		id, tenantID, projectID, sessionID, embeddingBytes)
	require.NoError(t, err)
}

func TestBoundedSearchSnapshotRejectsHugeMalformedEmbeddingBeforeCallback(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := NewFactRepo(db)
	require.NoError(t, err)
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-a"))

	// Hostile rows outside the exact project/non-session boundary are invisible.
	insertBoundedSearchPreflightProbe(t, db, "tenant-case", "LOCAL", "project-a", "", boundedSearchStoredRowHardMaxBytes+1)
	insertBoundedSearchPreflightProbe(t, db, "sibling", "local", "project-b", "", boundedSearchStoredRowHardMaxBytes+1)
	insertBoundedSearchPreflightProbe(t, db, "session", "local", "project-a", "session-a", boundedSearchStoredRowHardMaxBytes+1)
	called := false
	_, oversize, err := repo.WithBoundedSearchSnapshot(ctx, nil, func(snapshot memory.BoundedSearchSnapshot) ([]*memory.Fact, error) {
		called = true
		return snapshot.Search(ctx, "needle", 20)
	})
	require.NoError(t, err)
	require.Nil(t, oversize)
	require.True(t, called)

	// Tiny content plus a huge non-JSON embedding BLOB must be rejected by
	// metadata before scanFacts can allocate or json.Unmarshal the BLOB.
	insertBoundedSearchPreflightProbe(t, db, "hostile-embedding", "local", "project-a", "", boundedSearchStoredRowHardMaxBytes+1)
	called = false
	_, oversize, err = repo.WithBoundedSearchSnapshot(ctx, nil, func(snapshot memory.BoundedSearchSnapshot) ([]*memory.Fact, error) {
		called = true
		return snapshot.Search(ctx, "x", 20)
	})
	require.NoError(t, err)
	require.False(t, called, "hostile BLOB must be rejected before any factColumns scan")
	require.NotNil(t, oversize)
	require.Equal(t, memory.BoundedSearchStoredRowOversizeKind, oversize.Kind)
	require.Greater(t, oversize.StoredBytes, boundedSearchStoredRowHardMaxBytes)
	require.Equal(t, boundedSearchStoredRowHardMaxBytes, oversize.MaxStoredBytes)
}

func TestBoundedSearchSnapshotRejectsAggregateAndIdentityBeforeCallback(t *testing.T) {
	t.Run("aggregate", func(t *testing.T) {
		db, err := OpenMemory()
		require.NoError(t, err)
		t.Cleanup(func() { require.NoError(t, db.Close()) })
		repo, err := NewFactRepo(db)
		require.NoError(t, err)
		ctx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-a"))
		for index := 0; index < 3; index++ {
			insertBoundedSearchPreflightProbe(t, db, string(rune('a'+index)), "local", "project-a", "", 12*1024*1024)
		}
		called := false
		_, oversize, err := repo.WithBoundedSearchSnapshot(ctx, nil, func(memory.BoundedSearchSnapshot) ([]*memory.Fact, error) {
			called = true
			return nil, nil
		})
		require.NoError(t, err)
		require.False(t, called)
		require.NotNil(t, oversize)
		require.Equal(t, memory.BoundedSearchStoredScopeOversizeKind, oversize.Kind)
		require.Greater(t, oversize.StoredBytes, boundedSearchStoredSnapshotHardMaxBytes)
		require.Equal(t, boundedSearchStoredSnapshotHardMaxBytes, oversize.MaxStoredBytes)
	})

	t.Run("identity", func(t *testing.T) {
		db, err := OpenMemory()
		require.NoError(t, err)
		t.Cleanup(func() { require.NoError(t, db.Close()) })
		repo, err := NewFactRepo(db)
		require.NoError(t, err)
		ctx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-a"))
		insertBoundedSearchPreflightProbe(t, db, strings.Repeat("i", boundedSearchStoredFactIDHardMaxBytes+1), "local", "project-a", "", 1)
		called := false
		_, oversize, err := repo.WithBoundedSearchSnapshot(ctx, nil, func(memory.BoundedSearchSnapshot) ([]*memory.Fact, error) {
			called = true
			return nil, nil
		})
		require.NoError(t, err)
		require.False(t, called)
		require.NotNil(t, oversize)
		require.Equal(t, memory.BoundedSearchStoredIdentityOversizeKind, oversize.Kind)
		require.Equal(t, int64(boundedSearchStoredFactIDHardMaxBytes+1), oversize.StoredBytes)
	})
}

func TestBoundedSearchFrozenIDMutationToHugeBlobRejectsBeforeReload(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := NewFactRepo(db)
	require.NoError(t, err)
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-a"))
	insertBoundedSearchPreflightProbe(t, db, "frozen", "local", "project-a", "", 1)
	_, err = db.ExecContext(ctx, `UPDATE hierarchical_facts
		SET embedding = zeroblob(?) WHERE id = 'frozen'`, boundedSearchStoredRowHardMaxBytes+1)
	require.NoError(t, err)
	called := false
	_, oversize, err := repo.WithBoundedSearchSnapshot(ctx, []string{"frozen"}, func(snapshot memory.BoundedSearchSnapshot) ([]*memory.Fact, error) {
		called = true
		fact, loadErr := snapshot.Get(ctx, "frozen")
		return []*memory.Fact{fact}, loadErr
	})
	require.NoError(t, err)
	require.False(t, called, "frozen huge BLOB must reject before Get scans or unmarshals it")
	require.NotNil(t, oversize)
	require.Equal(t, memory.BoundedSearchStoredRowOversizeKind, oversize.Kind)
}

func TestBoundedSearchPreflightUsesSQLiteOctetLengthMetadata(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	_, err = NewFactRepo(db)
	require.NoError(t, err)
	rows, err := db.Query(`EXPLAIN SELECT ` + boundedSearchStoredVariableBytesSQL + `
		FROM hierarchical_facts WHERE tenant_id = 'local' AND project_id = 'default'`)
	require.NoError(t, err)
	defer rows.Close()
	metadataColumn := false
	for rows.Next() {
		var addr, p1, p2, p3, p5 int
		var opcode string
		var p4, comment sql.NullString
		require.NoError(t, rows.Scan(&addr, &opcode, &p1, &p2, &p3, &p4, &p5, &comment))
		require.NotEqual(t, "Cast", opcode, "preflight must never materialize a value through CAST")
		if opcode == "Column" && p5&0xc0 != 0 {
			metadataColumn = true
		}
	}
	require.NoError(t, rows.Err())
	require.True(t, metadataColumn, "octet_length must request SQLite record metadata")
}

func TestBoundedSearchSnapshotRequiresRawExactScopeAndFreezesPreflight(t *testing.T) {
	path := filepath.Join(t.TempDir(), "bounded-search.db")
	db, err := Open(path)
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := NewFactRepo(db)
	require.NoError(t, err)

	writer, err := Open(path)
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, writer.Close()) })
	_, err = NewFactRepo(writer)
	require.NoError(t, err)

	aliasCtx := rlmscope.WithScope(context.Background(), rlmscope.Scope{})
	called := false
	_, _, err = repo.WithBoundedSearchSnapshot(aliasCtx, nil, func(memory.BoundedSearchSnapshot) ([]*memory.Fact, error) {
		called = true
		return nil, nil
	})
	require.Error(t, err)
	require.False(t, called)

	defaultCtx := rlmscope.WithScope(context.Background(), rlmscope.Default())
	insertedAfterPreflight := false
	facts, oversize, err := repo.WithBoundedSearchSnapshot(defaultCtx, nil, func(snapshot memory.BoundedSearchSnapshot) ([]*memory.Fact, error) {
		insertBoundedSearchPreflightProbe(t, writer, "late-insert", "local", "default", "", 1)
		insertedAfterPreflight = true
		return snapshot.Search(defaultCtx, "x", 20)
	})
	require.NoError(t, err)
	require.Nil(t, oversize)
	require.True(t, insertedAfterPreflight)
	require.Empty(t, facts, "the search must use the same snapshot established by preflight")
}

func TestAuditBoundedKeywordSearchExcludesArchivedAndStaleFacts(t *testing.T) {
	repo := newTestFactRepo(t)
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "default"))
	for index := 0; index < 3; index++ {
		fact := memory.NewFact(fmt.Sprintf("audit search marker %d", index), memory.LevelDomain, "audit", "")
		fact.IsArchived = index == 1
		fact.IsStale = index == 2
		require.NoError(t, repo.Add(ctx, fact))
	}
	facts, oversize, err := repo.WithBoundedSearchSnapshot(ctx, nil, func(snapshot memory.BoundedSearchSnapshot) ([]*memory.Fact, error) {
		return snapshot.Search(ctx, "audit search marker", 20)
	})
	require.NoError(t, err)
	require.Nil(t, oversize)
	require.Len(t, facts, 1)
}
