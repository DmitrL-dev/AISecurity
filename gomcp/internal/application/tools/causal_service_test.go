package tools

import (
	"context"
	"testing"

	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func newTestCausalService(t *testing.T) *CausalService {
	t.Helper()
	db, err := sqlite.OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { db.Close() })

	repo, err := sqlite.NewCausalRepo(db)
	require.NoError(t, err)

	return NewCausalService(repo)
}

func TestCausalService_AddNode(t *testing.T) {
	svc := newTestCausalService(t)
	ctx := context.Background()

	node, err := svc.AddNode(ctx, AddNodeParams{
		NodeType: "decision",
		Content:  "Use Go for performance",
	})
	require.NoError(t, err)
	require.NotNil(t, node)
	assert.Equal(t, "decision", string(node.Type))
	assert.Equal(t, "Use Go for performance", node.Content)
	assert.NotEmpty(t, node.ID)
}

func TestCausalService_AddNode_InvalidType(t *testing.T) {
	svc := newTestCausalService(t)
	ctx := context.Background()

	_, err := svc.AddNode(ctx, AddNodeParams{
		NodeType: "invalid_type",
		Content:  "bad",
	})
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "invalid node type")
}

func TestCausalService_AddNode_AllTypes(t *testing.T) {
	svc := newTestCausalService(t)
	ctx := context.Background()

	types := []string{"decision", "reason", "consequence", "constraint", "alternative", "assumption"}
	for _, nt := range types {
		node, err := svc.AddNode(ctx, AddNodeParams{NodeType: nt, Content: "test " + nt})
		require.NoError(t, err, "type %s should be valid", nt)
		assert.Equal(t, nt, string(node.Type))
	}
}

func TestCausalService_AddEdge(t *testing.T) {
	svc := newTestCausalService(t)
	ctx := context.Background()

	n1, err := svc.AddNode(ctx, AddNodeParams{NodeType: "decision", Content: "Choose Go"})
	require.NoError(t, err)
	n2, err := svc.AddNode(ctx, AddNodeParams{NodeType: "reason", Content: "Performance"})
	require.NoError(t, err)

	edge, err := svc.AddEdge(ctx, AddEdgeParams{
		FromID:   n2.ID,
		ToID:     n1.ID,
		EdgeType: "justifies",
	})
	require.NoError(t, err)
	assert.Equal(t, n2.ID, edge.FromID)
	assert.Equal(t, n1.ID, edge.ToID)
	assert.Equal(t, "justifies", string(edge.Type))
}

func TestCausalService_AddEdge_InvalidType(t *testing.T) {
	svc := newTestCausalService(t)
	ctx := context.Background()

	_, err := svc.AddEdge(ctx, AddEdgeParams{
		FromID: "a", ToID: "b", EdgeType: "bad_type",
	})
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "invalid edge type")
}

func TestCausalService_AddEdge_AllTypes(t *testing.T) {
	svc := newTestCausalService(t)
	ctx := context.Background()

	n1, _ := svc.AddNode(ctx, AddNodeParams{NodeType: "decision", Content: "d1"})
	n2, _ := svc.AddNode(ctx, AddNodeParams{NodeType: "reason", Content: "r1"})

	edgeTypes := []string{"justifies", "causes", "constrains"}
	for _, et := range edgeTypes {
		edge, err := svc.AddEdge(ctx, AddEdgeParams{FromID: n2.ID, ToID: n1.ID, EdgeType: et})
		require.NoError(t, err, "edge type %s should be valid", et)
		assert.Equal(t, et, string(edge.Type))
	}
}

func TestCausalService_GetChain(t *testing.T) {
	svc := newTestCausalService(t)
	ctx := context.Background()

	_, _ = svc.AddNode(ctx, AddNodeParams{NodeType: "decision", Content: "Use mcp-go library"})

	chain, err := svc.GetChain(ctx, "mcp-go", 3)
	require.NoError(t, err)
	require.NotNil(t, chain)
}

func TestCausalService_GetChain_DefaultDepth(t *testing.T) {
	svc := newTestCausalService(t)
	ctx := context.Background()

	_, _ = svc.AddNode(ctx, AddNodeParams{NodeType: "decision", Content: "test default depth"})

	// maxDepth <= 0 should default to 3.
	chain, err := svc.GetChain(ctx, "test", 0)
	require.NoError(t, err)
	require.NotNil(t, chain)
}

func TestCausalService_GetStats(t *testing.T) {
	svc := newTestCausalService(t)
	ctx := context.Background()

	_, _ = svc.AddNode(ctx, AddNodeParams{NodeType: "decision", Content: "d1"})
	_, _ = svc.AddNode(ctx, AddNodeParams{NodeType: "reason", Content: "r1"})

	stats, err := svc.GetStats(ctx)
	require.NoError(t, err)
	assert.Equal(t, 2, stats.TotalNodes)
}

func TestCausalService_GetStats_Empty(t *testing.T) {
	svc := newTestCausalService(t)
	ctx := context.Background()

	stats, err := svc.GetStats(ctx)
	require.NoError(t, err)
	assert.Equal(t, 0, stats.TotalNodes)
}
