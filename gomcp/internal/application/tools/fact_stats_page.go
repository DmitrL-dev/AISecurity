package tools

import (
	"context"
	"fmt"

	"github.com/syntrex/gomcp/internal/domain/memory"
)

// GetFactStatsPage returns one bounded exact-scope aggregate step without
// changing the legacy GetStats path.
func (s *FactService) GetFactStatsPage(
	ctx context.Context,
	position *memory.FactStatsPagePosition,
) (*memory.FactStatsPage, error) {
	store, ok := s.store.(memory.ExactFactStatsPageStore)
	if !ok {
		return nil, fmt.Errorf("exact fact stats pagination is unavailable for this store")
	}
	return store.FactStatsPage(ctx, position)
}
