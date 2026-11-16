package sqlite

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"testing"

	"github.com/stretchr/testify/require"
	modernsqlite "modernc.org/sqlite"
	sqlitelib "modernc.org/sqlite/lib"

	"github.com/syntrex/gomcp/internal/domain/causal"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
)

type causalStoredOversizeBoundary interface {
	error
	OversizeKind() string
	OversizeMeasuredBytes() int64
	OversizeMaximumBytes() int64
}

func exactDefaultCausalContext() context.Context {
	return rlmscope.WithScope(context.Background(), rlmscope.Default())
}

func TestCausalRepoGetChainBoundedEnforcesNodeLimitInRepository(t *testing.T) {
	repo := newTestCausalRepo(t)
	ctx := exactDefaultCausalContext()
	decision := causal.NewNode(causal.NodeDecision, "bounded decision")
	reason := causal.NewNode(causal.NodeReason, "reason")
	consequence := causal.NewNode(causal.NodeConsequence, "consequence")
	for _, node := range []*causal.Node{decision, reason, consequence} {
		require.NoError(t, repo.AddNode(ctx, node))
	}
	require.NoError(t, repo.AddEdge(ctx, causal.NewEdge(reason.ID, decision.ID, causal.EdgeJustifies)))
	require.NoError(t, repo.AddEdge(ctx, causal.NewEdge(decision.ID, consequence.ID, causal.EdgeCauses)))

	_, err := repo.GetChainBounded(ctx, "bounded decision", 1, 2, causal.BoundedCausalMaxResultBytes)
	require.True(t, errors.Is(err, causal.ErrCausalChainTooLarge), "error: %v", err)

	chain, err := repo.GetChainBounded(ctx, "bounded decision", 1, 3, causal.BoundedCausalMaxResultBytes)
	require.NoError(t, err)
	require.Equal(t, 3, chain.TotalNodes)
	require.Len(t, chain.Reasons, 1)
	require.Len(t, chain.Consequences, 1)
}

func TestCausalRepoGetChainBoundedNoMatchIsEmpty(t *testing.T) {
	repo := newTestCausalRepo(t)
	chain, err := repo.GetChainBounded(exactDefaultCausalContext(), "absent", 1, 1, causal.BoundedCausalMaxResultBytes)
	require.NoError(t, err)
	require.NotNil(t, chain)
	require.Zero(t, chain.TotalNodes)
}

func TestCausalRepoGetChainBoundedRequiresExactDefaultScope(t *testing.T) {
	repo := newTestCausalRepo(t)

	_, err := repo.GetChainBounded(context.Background(), "absent", 1, 1, causal.BoundedCausalMaxResultBytes)
	require.ErrorContains(t, err, "explicit tenant_id/project_id scope is required")

	alias := rlmscope.WithScope(context.Background(), rlmscope.Scope{})
	_, err = repo.GetChainBounded(alias, "absent", 1, 1, causal.BoundedCausalMaxResultBytes)
	require.ErrorContains(t, err, "default scope must be exactly local/default")
}

func TestCausalRepoGetChainBoundedRejectsOversizedLegacyNodeBeforeMaterialization(t *testing.T) {
	const storedRowHardLimit int64 = 16 * 1024 * 1024
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := NewCausalRepo(db)
	require.NoError(t, err)

	const hostileID = "hostile-causal-node-must-not-be-reflected"
	_, err = db.SqlDB().Exec(`INSERT INTO causal_nodes (
		id, tenant_id, project_id, node_type, content, created_at
	) VALUES (?, 'local', 'default', 'decision',
		CAST('oversized-decision ' || zeroblob(?) AS TEXT),
		'2026-09-01T00:00:00Z')`, hostileID, storedRowHardLimit+1)
	require.NoError(t, err)

	// A legacy/corrupt row can predate current bounds. Lowering SQLite's value
	// limit after insertion proves octet metadata is checked before Scan asks
	// SQLite to materialize the oversized TEXT value.
	conn, err := db.SqlDB().Conn(context.Background())
	require.NoError(t, err)
	previousLimit, err := modernsqlite.Limit(conn, sqlitelib.SQLITE_LIMIT_LENGTH, int(storedRowHardLimit))
	require.NoError(t, err)
	require.Greater(t, previousLimit, int(storedRowHardLimit))
	require.NoError(t, conn.Close())

	_, err = repo.GetChainBounded(exactDefaultCausalContext(), "oversized-decision", 1, 1, causal.BoundedCausalMaxResultBytes)
	require.Error(t, err)
	var oversized causalStoredOversizeBoundary
	require.ErrorAs(t, err, &oversized, "failure must stay typed across repository boundaries")
	require.Equal(t, "row", oversized.OversizeKind())
	require.Greater(t, oversized.OversizeMeasuredBytes(), storedRowHardLimit)
	require.Equal(t, storedRowHardLimit, oversized.OversizeMaximumBytes())
	require.NotContains(t, err.Error(), hostileID)
}

func TestCausalRepoGetChainBoundedRejectsAggregateDecisionScopeBeforeSearch(t *testing.T) {
	const (
		storedScopeHardLimit int64 = 32 * 1024 * 1024
		probeBytes                 = 12 * 1024 * 1024
	)
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := NewCausalRepo(db)
	require.NoError(t, err)

	for index := 0; index < 3; index++ {
		_, err = db.SqlDB().Exec(`INSERT INTO causal_nodes (
			id, tenant_id, project_id, node_type, content, created_at
		) VALUES (?, 'local', 'default', 'decision',
			CAST(? || zeroblob(?) AS TEXT), '2026-09-01T00:00:00Z')`,
			fmt.Sprintf("aggregate-%d", index), fmt.Sprintf("candidate-%d ", index), probeBytes)
		require.NoError(t, err)
	}

	_, err = repo.GetChainBounded(exactDefaultCausalContext(), "absent", 1, 1, causal.BoundedCausalMaxResultBytes)
	require.Error(t, err)
	var oversized causalStoredOversizeBoundary
	require.ErrorAs(t, err, &oversized)
	require.Equal(t, "scope", oversized.OversizeKind())
	require.Greater(t, oversized.OversizeMeasuredBytes(), storedScopeHardLimit)
	require.Equal(t, storedScopeHardLimit, oversized.OversizeMaximumBytes())
}

func TestCausalRepoGetChainBoundedRejectsWorstCaseEscapingBeforeMaterialization(t *testing.T) {
	repo := newTestCausalRepo(t)
	ctx := exactDefaultCausalContext()
	decision := causal.NewNode(causal.NodeDecision, "escape "+strings.Repeat("<", 48*1024))
	require.NoError(t, repo.AddNode(ctx, decision))

	_, err := repo.GetChainBounded(ctx, "escape", 1, 1, causal.BoundedCausalMaxResultBytes)
	require.Error(t, err)
	var oversized causalStoredOversizeBoundary
	require.ErrorAs(t, err, &oversized,
		"stored raw bytes below 512 KiB can still exceed the wire bound after JSON and Mermaid amplification")
}

func TestCausalRepoGetChainBoundedRejectsMatchingDecisionIDBeforeMaterialization(t *testing.T) {
	const sqliteValueLimit = 64 * 1024
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := NewCausalRepo(db)
	require.NoError(t, err)

	hostileID := "matching-decision-id-" + strings.Repeat("i", 96*1024)
	_, err = db.SqlDB().Exec(`INSERT INTO causal_nodes (
		id, tenant_id, project_id, node_type, content, created_at
	) VALUES (?, 'local', 'default', 'decision', 'matching decision',
		'2026-09-01T00:00:00Z')`, hostileID)
	require.NoError(t, err)

	conn, err := db.SqlDB().Conn(context.Background())
	require.NoError(t, err)
	previousLimit, err := modernsqlite.Limit(conn, sqlitelib.SQLITE_LIMIT_LENGTH, sqliteValueLimit)
	require.NoError(t, err)
	require.Greater(t, previousLimit, sqliteValueLimit)
	require.NoError(t, conn.Close())

	_, err = repo.GetChainBounded(
		exactDefaultCausalContext(), "matching decision", 1, 1, causal.BoundedCausalMaxResultBytes,
	)
	require.Error(t, err)
	var oversized causalStoredOversizeBoundary
	require.ErrorAs(t, err, &oversized,
		"decision identity must stay inside SQLite until its result upper bound passes")
	require.Equal(t, "row", oversized.OversizeKind())
	require.Greater(t, oversized.OversizeMeasuredBytes(), int64(causal.BoundedCausalMaxResultBytes))
	require.Equal(t, int64(causal.BoundedCausalMaxResultBytes), oversized.OversizeMaximumBytes())
	require.NotContains(t, err.Error(), "matching-decision-id")
}

func TestCausalRepoGetChainBoundedAppliesWireBudgetOnlyToSelectedDecision(t *testing.T) {
	repo := newTestCausalRepo(t)
	ctx := exactDefaultCausalContext()
	unselected := causal.NewNode(causal.NodeDecision, "unselected "+strings.Repeat("<", 48*1024))
	selected := causal.NewNode(causal.NodeDecision, "selected decision")
	require.NoError(t, repo.AddNode(ctx, unselected))
	require.NoError(t, repo.AddNode(ctx, selected))

	chain, err := repo.GetChainBounded(ctx, "selected decision", 1, 1, causal.BoundedCausalMaxResultBytes)
	require.NoError(t, err)
	require.NotNil(t, chain.Decision)
	require.Equal(t, selected.ID, chain.Decision.ID)
}

func TestCausalRepoGetChainBoundedUsesRequestedResultBudget(t *testing.T) {
	repo := newTestCausalRepo(t)
	ctx := exactDefaultCausalContext()
	decision := causal.NewNode(causal.NodeDecision, "budget "+strings.Repeat("<", 6*1024))
	require.NoError(t, repo.AddNode(ctx, decision))

	const lowBudget = 64 * 1024
	_, err := repo.GetChainBounded(ctx, "budget", 1, 1, lowBudget)
	require.Error(t, err)
	var oversized causalStoredOversizeBoundary
	require.ErrorAs(t, err, &oversized)
	require.Equal(t, int64(lowBudget), oversized.OversizeMaximumBytes())

	chain, err := repo.GetChainBounded(ctx, "budget", 1, 1, causal.BoundedCausalMaxResultBytes)
	require.NoError(t, err)
	require.Equal(t, decision.ID, chain.Decision.ID)
}

func TestCausalRepoGetChainBoundedPreflightsSelectedNeighbours(t *testing.T) {
	t.Run("oversized neighbour row", func(t *testing.T) {
		const storedRowHardLimit int64 = 16 * 1024 * 1024
		db, err := OpenMemory()
		require.NoError(t, err)
		t.Cleanup(func() { require.NoError(t, db.Close()) })
		repo, err := NewCausalRepo(db)
		require.NoError(t, err)
		ctx := exactDefaultCausalContext()
		decision := causal.NewNode(causal.NodeDecision, "bounded decision")
		require.NoError(t, repo.AddNode(ctx, decision))

		const hostileID = "hostile-neighbour-must-not-be-reflected"
		_, err = db.SqlDB().Exec(`INSERT INTO causal_nodes (
			id, tenant_id, project_id, node_type, content, created_at
		) VALUES (?, 'local', 'default', 'reason',
			CAST('oversized-neighbour ' || zeroblob(?) AS TEXT),
			'2026-09-01T00:00:00Z')`, hostileID, storedRowHardLimit+1)
		require.NoError(t, err)
		_, err = db.SqlDB().Exec(`INSERT INTO causal_edges (
			tenant_id, project_id, from_id, to_id, edge_type
		) VALUES ('local', 'default', ?, ?, 'justifies')`, hostileID, decision.ID)
		require.NoError(t, err)

		conn, err := db.SqlDB().Conn(context.Background())
		require.NoError(t, err)
		previousLimit, err := modernsqlite.Limit(conn, sqlitelib.SQLITE_LIMIT_LENGTH, int(storedRowHardLimit))
		require.NoError(t, err)
		require.Greater(t, previousLimit, int(storedRowHardLimit))
		require.NoError(t, conn.Close())

		_, err = repo.GetChainBounded(ctx, "bounded decision", 1, 2, causal.BoundedCausalMaxResultBytes)
		require.Error(t, err)
		var oversized causalStoredOversizeBoundary
		require.ErrorAs(t, err, &oversized)
		require.Equal(t, "row", oversized.OversizeKind())
		require.Greater(t, oversized.OversizeMeasuredBytes(), storedRowHardLimit)
		require.NotContains(t, err.Error(), hostileID)
	})

	t.Run("ordered identities do not materialize content", func(t *testing.T) {
		const sqliteValueLimit = 64 * 1024
		db, err := OpenMemory()
		require.NoError(t, err)
		t.Cleanup(func() { require.NoError(t, db.Close()) })
		repo, err := NewCausalRepo(db)
		require.NoError(t, err)
		ctx := exactDefaultCausalContext()
		decision := causal.NewNode(causal.NodeDecision, "bounded decision")
		require.NoError(t, repo.AddNode(ctx, decision))

		const hostileID = "ordered-identity-probe"
		_, err = db.SqlDB().Exec(`INSERT INTO causal_nodes (
			id, tenant_id, project_id, node_type, content, created_at
		) VALUES (?, 'local', 'default', 'reason',
			CAST('escape-neighbour ' || zeroblob(?) AS TEXT),
			'2026-09-01T00:00:00Z')`, hostileID, 96*1024)
		require.NoError(t, err)
		_, err = db.SqlDB().Exec(`INSERT INTO causal_edges (
			tenant_id, project_id, from_id, to_id, edge_type
		) VALUES ('local', 'default', ?, ?, 'justifies')`, hostileID, decision.ID)
		require.NoError(t, err)

		conn, err := db.SqlDB().Conn(context.Background())
		require.NoError(t, err)
		previousLimit, err := modernsqlite.Limit(conn, sqlitelib.SQLITE_LIMIT_LENGTH, sqliteValueLimit)
		require.NoError(t, err)
		require.Greater(t, previousLimit, sqliteValueLimit)
		require.NoError(t, conn.Close())

		_, err = repo.GetChainBounded(ctx, "bounded decision", 1, 2, causal.BoundedCausalMaxResultBytes)
		require.Error(t, err)
		var oversized causalStoredOversizeBoundary
		require.ErrorAs(t, err, &oversized,
			"identity ordering must not ask SQLite to materialize neighbour content")
		require.Equal(t, "row", oversized.OversizeKind())
		require.NotContains(t, err.Error(), hostileID)
	})

	t.Run("overflow sentinel wins before weighted content load", func(t *testing.T) {
		repo := newTestCausalRepo(t)
		ctx := exactDefaultCausalContext()
		decision := causal.NewNode(causal.NodeDecision, "bounded decision")
		neighbour := causal.NewNode(causal.NodeReason, strings.Repeat("<", 48*1024))
		require.NoError(t, repo.AddNode(ctx, decision))
		require.NoError(t, repo.AddNode(ctx, neighbour))
		require.NoError(t, repo.AddEdge(ctx, causal.NewEdge(neighbour.ID, decision.ID, causal.EdgeJustifies)))

		_, err := repo.GetChainBounded(ctx, "bounded decision", 1, 1, causal.BoundedCausalMaxResultBytes)
		require.ErrorIs(t, err, causal.ErrCausalChainTooLarge)
	})

	t.Run("aggregate selected neighbours", func(t *testing.T) {
		const (
			storedScopeHardLimit = causal.BoundedCausalMaxResultBytes
			probeBytes           = 15 * 1024
		)
		db, err := OpenMemory()
		require.NoError(t, err)
		t.Cleanup(func() { require.NoError(t, db.Close()) })
		repo, err := NewCausalRepo(db)
		require.NoError(t, err)
		ctx := exactDefaultCausalContext()
		decision := causal.NewNode(causal.NodeDecision, "bounded decision")
		require.NoError(t, repo.AddNode(ctx, decision))

		for index := 0; index < 3; index++ {
			id := fmt.Sprintf("aggregate-neighbour-%d", index)
			_, err = db.SqlDB().Exec(`INSERT INTO causal_nodes (
				id, tenant_id, project_id, node_type, content, created_at
			) VALUES (?, 'local', 'default', 'reason',
				CAST(? || zeroblob(?) AS TEXT), '2026-09-01T00:00:00Z')`,
				id, fmt.Sprintf("neighbour-%d ", index), probeBytes)
			require.NoError(t, err)
			_, err = db.SqlDB().Exec(`INSERT INTO causal_edges (
				tenant_id, project_id, from_id, to_id, edge_type
			) VALUES ('local', 'default', ?, ?, 'justifies')`, id, decision.ID)
			require.NoError(t, err)
		}

		_, err = repo.GetChainBounded(ctx, "bounded decision", 1, 4, causal.BoundedCausalMaxResultBytes)
		require.Error(t, err)
		var oversized causalStoredOversizeBoundary
		require.ErrorAs(t, err, &oversized)
		require.Equal(t, "scope", oversized.OversizeKind())
		require.Greater(t, oversized.OversizeMeasuredBytes(), int64(storedScopeHardLimit))
		require.Equal(t, int64(storedScopeHardLimit), oversized.OversizeMaximumBytes())
	})
}

func TestCausalRepoGetChainBoundedPreflightKeepsExactBinaryScope(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := NewCausalRepo(db)
	require.NoError(t, err)
	ctx := exactDefaultCausalContext()

	decision := causal.NewNode(causal.NodeDecision, "bounded decision")
	require.NoError(t, repo.AddNode(ctx, decision))
	_, err = db.SqlDB().Exec(`INSERT INTO causal_nodes (
		id, tenant_id, project_id, node_type, content, created_at
	) VALUES ('case-sibling', 'LOCAL', 'default', 'decision',
		CAST('bounded decision ' || zeroblob(?) AS TEXT), '2026-09-01T00:00:00Z')`,
		16*1024*1024+1)
	require.NoError(t, err)

	chain, err := repo.GetChainBounded(ctx, "bounded decision", 1, 1, causal.BoundedCausalMaxResultBytes)
	require.NoError(t, err)
	require.NotNil(t, chain.Decision)
	require.Equal(t, decision.ID, chain.Decision.ID)
	require.Equal(t, "bounded decision", chain.Decision.Content)
	require.False(t, strings.Contains(chain.Decision.Content, "case-sibling"))
}
