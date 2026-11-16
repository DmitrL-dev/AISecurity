package sqlite

import (
	"context"
	"testing"

	"github.com/syntrex/gomcp/internal/domain/causal"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func newTestCausalRepo(t *testing.T) *CausalRepo {
	t.Helper()
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { db.Close() })

	repo, err := NewCausalRepo(db)
	require.NoError(t, err)
	return repo
}

func TestCausalRepo_AddNode_GetChain(t *testing.T) {
	repo := newTestCausalRepo(t)
	ctx := context.Background()

	decision := causal.NewNode(causal.NodeDecision, "Use SQLite")
	reason := causal.NewNode(causal.NodeReason, "Embedded, no server needed")
	consequence := causal.NewNode(causal.NodeConsequence, "Single binary deployment")

	require.NoError(t, repo.AddNode(ctx, decision))
	require.NoError(t, repo.AddNode(ctx, reason))
	require.NoError(t, repo.AddNode(ctx, consequence))

	e1 := causal.NewEdge(reason.ID, decision.ID, causal.EdgeJustifies)
	e2 := causal.NewEdge(decision.ID, consequence.ID, causal.EdgeCauses)
	require.NoError(t, repo.AddEdge(ctx, e1))
	require.NoError(t, repo.AddEdge(ctx, e2))

	chain, err := repo.GetChain(ctx, "SQLite", 3)
	require.NoError(t, err)
	require.NotNil(t, chain)
	assert.NotNil(t, chain.Decision)
	assert.Equal(t, "Use SQLite", chain.Decision.Content)
	assert.Len(t, chain.Reasons, 1)
	assert.Len(t, chain.Consequences, 1)
}

func TestCausalRepo_AddNode_Duplicate(t *testing.T) {
	repo := newTestCausalRepo(t)
	ctx := context.Background()

	node := causal.NewNode(causal.NodeDecision, "test")
	require.NoError(t, repo.AddNode(ctx, node))

	err := repo.AddNode(ctx, node)
	assert.Error(t, err) // duplicate primary key
}

func TestCausalRepo_AddEdge_SelfLoop(t *testing.T) {
	repo := newTestCausalRepo(t)
	ctx := context.Background()

	node := causal.NewNode(causal.NodeDecision, "test")
	require.NoError(t, repo.AddNode(ctx, node))

	edge := causal.NewEdge(node.ID, node.ID, causal.EdgeCauses)
	err := repo.AddEdge(ctx, edge)
	assert.Error(t, err) // self-loop validation
}

func TestCausalRepo_GetChain_NoResults(t *testing.T) {
	repo := newTestCausalRepo(t)
	ctx := context.Background()

	chain, err := repo.GetChain(ctx, "nonexistent", 3)
	require.NoError(t, err)
	assert.Equal(t, 0, chain.TotalNodes)
}

func TestCausalRepo_Stats(t *testing.T) {
	repo := newTestCausalRepo(t)
	ctx := context.Background()

	n1 := causal.NewNode(causal.NodeDecision, "D1")
	n2 := causal.NewNode(causal.NodeReason, "R1")
	n3 := causal.NewNode(causal.NodeConsequence, "C1")
	require.NoError(t, repo.AddNode(ctx, n1))
	require.NoError(t, repo.AddNode(ctx, n2))
	require.NoError(t, repo.AddNode(ctx, n3))

	e1 := causal.NewEdge(n2.ID, n1.ID, causal.EdgeJustifies)
	require.NoError(t, repo.AddEdge(ctx, e1))

	stats, err := repo.Stats(ctx)
	require.NoError(t, err)
	assert.Equal(t, 3, stats.TotalNodes)
	assert.Equal(t, 1, stats.TotalEdges)
	assert.Equal(t, 1, stats.ByType[causal.NodeDecision])
	assert.Equal(t, 1, stats.ByType[causal.NodeReason])
	assert.Equal(t, 1, stats.ByType[causal.NodeConsequence])
}

func TestCausalRepo_ComplexChain(t *testing.T) {
	repo := newTestCausalRepo(t)
	ctx := context.Background()

	decision := causal.NewNode(causal.NodeDecision, "Use Go for MCP server")
	r1 := causal.NewNode(causal.NodeReason, "Performance")
	r2 := causal.NewNode(causal.NodeReason, "Single binary")
	c1 := causal.NewNode(causal.NodeConsequence, "Faster startup")
	cn1 := causal.NewNode(causal.NodeConstraint, "Must support CGO-free")
	a1 := causal.NewNode(causal.NodeAlternative, "Use Rust")

	for _, n := range []*causal.Node{decision, r1, r2, c1, cn1, a1} {
		require.NoError(t, repo.AddNode(ctx, n))
	}

	edges := []*causal.Edge{
		causal.NewEdge(r1.ID, decision.ID, causal.EdgeJustifies),
		causal.NewEdge(r2.ID, decision.ID, causal.EdgeJustifies),
		causal.NewEdge(decision.ID, c1.ID, causal.EdgeCauses),
		causal.NewEdge(cn1.ID, decision.ID, causal.EdgeConstrains),
	}
	for _, e := range edges {
		require.NoError(t, repo.AddEdge(ctx, e))
	}

	chain, err := repo.GetChain(ctx, "Go for MCP", 5)
	require.NoError(t, err)
	require.NotNil(t, chain.Decision)
	assert.Equal(t, "Use Go for MCP server", chain.Decision.Content)
	assert.Len(t, chain.Reasons, 2)
	assert.Len(t, chain.Consequences, 1)
	assert.Len(t, chain.Constraints, 1)
	assert.GreaterOrEqual(t, chain.TotalNodes, 5)
}
