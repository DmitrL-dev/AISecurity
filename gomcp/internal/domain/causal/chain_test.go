package causal

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestNodeType_IsValid(t *testing.T) {
	assert.True(t, NodeDecision.IsValid())
	assert.True(t, NodeReason.IsValid())
	assert.True(t, NodeConsequence.IsValid())
	assert.True(t, NodeConstraint.IsValid())
	assert.True(t, NodeAlternative.IsValid())
	assert.False(t, NodeType("invalid").IsValid())
}

func TestEdgeType_IsValid(t *testing.T) {
	assert.True(t, EdgeJustifies.IsValid())
	assert.True(t, EdgeCauses.IsValid())
	assert.True(t, EdgeConstrains.IsValid())
	assert.False(t, EdgeType("invalid").IsValid())
}

func TestNewNode(t *testing.T) {
	n := NewNode(NodeDecision, "Use SQLite for storage")

	assert.NotEmpty(t, n.ID)
	assert.Equal(t, NodeDecision, n.Type)
	assert.Equal(t, "Use SQLite for storage", n.Content)
	assert.False(t, n.CreatedAt.IsZero())
}

func TestNewNode_UniqueIDs(t *testing.T) {
	n1 := NewNode(NodeDecision, "a")
	n2 := NewNode(NodeDecision, "b")
	assert.NotEqual(t, n1.ID, n2.ID)
}

func TestNode_Validate(t *testing.T) {
	tests := []struct {
		name    string
		node    *Node
		wantErr bool
	}{
		{"valid", NewNode(NodeDecision, "content"), false},
		{"empty ID", &Node{ID: "", Type: NodeDecision, Content: "x"}, true},
		{"empty content", &Node{ID: "x", Type: NodeDecision, Content: ""}, true},
		{"invalid type", &Node{ID: "x", Type: "bad", Content: "x"}, true},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := tt.node.Validate()
			if tt.wantErr {
				assert.Error(t, err)
			} else {
				assert.NoError(t, err)
			}
		})
	}
}

func TestNewEdge(t *testing.T) {
	e := NewEdge("from1", "to1", EdgeJustifies)

	assert.NotEmpty(t, e.ID)
	assert.Equal(t, "from1", e.FromID)
	assert.Equal(t, "to1", e.ToID)
	assert.Equal(t, EdgeJustifies, e.Type)
}

func TestEdge_Validate(t *testing.T) {
	tests := []struct {
		name    string
		edge    *Edge
		wantErr bool
	}{
		{"valid", NewEdge("a", "b", EdgeCauses), false},
		{"empty from", &Edge{ID: "x", FromID: "", ToID: "b", Type: EdgeCauses}, true},
		{"empty to", &Edge{ID: "x", FromID: "a", ToID: "", Type: EdgeCauses}, true},
		{"invalid type", &Edge{ID: "x", FromID: "a", ToID: "b", Type: "bad"}, true},
		{"self-loop", &Edge{ID: "x", FromID: "a", ToID: "a", Type: EdgeCauses}, true},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := tt.edge.Validate()
			if tt.wantErr {
				assert.Error(t, err)
			} else {
				assert.NoError(t, err)
			}
		})
	}
}

func TestChain_Empty(t *testing.T) {
	c := &Chain{}
	assert.Nil(t, c.Decision)
	assert.Empty(t, c.Reasons)
	assert.Equal(t, 0, c.TotalNodes)
}

func TestChain_WithData(t *testing.T) {
	decision := NewNode(NodeDecision, "Use Go")
	reason := NewNode(NodeReason, "Performance")
	consequence := NewNode(NodeConsequence, "Single binary")

	chain := &Chain{
		Decision:     decision,
		Reasons:      []*Node{reason},
		Consequences: []*Node{consequence},
		TotalNodes:   3,
	}

	require.NotNil(t, chain.Decision)
	assert.Equal(t, "Use Go", chain.Decision.Content)
	assert.Len(t, chain.Reasons, 1)
	assert.Len(t, chain.Consequences, 1)
	assert.Equal(t, 3, chain.TotalNodes)
}

func TestChain_ToMermaid(t *testing.T) {
	decision := NewNode(NodeDecision, "Use Go")
	decision.ID = "d1"
	reason := NewNode(NodeReason, "Performance")
	reason.ID = "r1"

	chain := &Chain{
		Decision:   decision,
		Reasons:    []*Node{reason},
		TotalNodes: 2,
	}

	mermaid := chain.ToMermaid()
	assert.Contains(t, mermaid, "graph TD")
	assert.Contains(t, mermaid, "Use Go")
	assert.Contains(t, mermaid, "Performance")
}

func TestCausalStats_Zero(t *testing.T) {
	stats := &CausalStats{
		ByType: make(map[NodeType]int),
	}
	assert.Equal(t, 0, stats.TotalNodes)
	assert.Equal(t, 0, stats.TotalEdges)
}
