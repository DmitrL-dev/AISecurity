package tools

import (
	"context"
	"fmt"

	"github.com/syntrex/gomcp/internal/domain/causal"
)

const (
	CausalChainMaxDepth       = causal.BoundedCausalMaxDepth
	CausalChainMaxNodes       = causal.BoundedCausalMaxNodes
	CausalChainMaxResultBytes = causal.BoundedCausalMaxResultBytes
)

// GetChainBounded uses only stores that explicitly implement a repository-
// enforced node bound. Falling back to GetChain here would reintroduce the
// unbounded materialization this protocol exists to prevent.
func (s *CausalService) GetChainBounded(
	ctx context.Context,
	query string,
	maxDepth, maxNodes, maxResultBytes int,
) (*causal.Chain, error) {
	if query == "" {
		return nil, fmt.Errorf("query is required")
	}
	if maxDepth != CausalChainMaxDepth {
		return nil, fmt.Errorf("max_depth must be %d", CausalChainMaxDepth)
	}
	if maxNodes < 1 || maxNodes > CausalChainMaxNodes {
		return nil, fmt.Errorf("max_nodes must be from 1 through %d", CausalChainMaxNodes)
	}
	if maxResultBytes < 1 || maxResultBytes > CausalChainMaxResultBytes {
		return nil, fmt.Errorf("max_result_bytes must be from 1 through %d", CausalChainMaxResultBytes)
	}
	store, ok := s.store.(causal.BoundedCausalStore)
	if !ok {
		return nil, fmt.Errorf("bounded causal lookup is unavailable")
	}
	return store.GetChainBounded(ctx, query, maxDepth, maxNodes, maxResultBytes)
}
