package tools

import (
	"context"
	"fmt"

	"github.com/syntrex/gomcp/internal/domain/causal"
)

// CausalService implements MCP tool logic for causal reasoning chains.
type CausalService struct {
	store causal.CausalStore
}

// NewCausalService creates a new CausalService.
func NewCausalService(store causal.CausalStore) *CausalService {
	return &CausalService{store: store}
}

// AddNodeParams holds parameters for the add_causal_node tool.
type AddNodeParams struct {
	NodeType string `json:"node_type"` // decision, reason, consequence, constraint, alternative, assumption
	Content  string `json:"content"`
}

// AddNode creates a new causal node.
func (s *CausalService) AddNode(ctx context.Context, params AddNodeParams) (*causal.Node, error) {
	nt := causal.NodeType(params.NodeType)
	if !nt.IsValid() {
		return nil, fmt.Errorf("invalid node type: %s", params.NodeType)
	}
	node := causal.NewNode(nt, params.Content)
	if err := s.store.AddNode(ctx, node); err != nil {
		return nil, err
	}
	return node, nil
}

// AddEdgeParams holds parameters for the add_causal_edge tool.
type AddEdgeParams struct {
	FromID   string `json:"from_id"`
	ToID     string `json:"to_id"`
	EdgeType string `json:"edge_type"` // justifies, causes, constrains
}

// AddEdge creates a new causal edge.
func (s *CausalService) AddEdge(ctx context.Context, params AddEdgeParams) (*causal.Edge, error) {
	et := causal.EdgeType(params.EdgeType)
	if !et.IsValid() {
		return nil, fmt.Errorf("invalid edge type: %s", params.EdgeType)
	}
	edge := causal.NewEdge(params.FromID, params.ToID, et)
	if err := s.store.AddEdge(ctx, edge); err != nil {
		return nil, err
	}
	return edge, nil
}

// GetChain retrieves a causal chain for a decision matching the query.
func (s *CausalService) GetChain(ctx context.Context, query string, maxDepth int) (*causal.Chain, error) {
	if maxDepth <= 0 {
		maxDepth = 3
	}
	return s.store.GetChain(ctx, query, maxDepth)
}

// GetStats returns causal store statistics.
func (s *CausalService) GetStats(ctx context.Context) (*causal.CausalStats, error) {
	return s.store.Stats(ctx)
}
