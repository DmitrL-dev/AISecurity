package tools

import (
	"context"

	"github.com/syntrex/gomcp/internal/domain/crystal"
)

// CrystalService implements MCP tool logic for code crystal operations.
type CrystalService struct {
	store crystal.CrystalStore
}

// NewCrystalService creates a new CrystalService.
func NewCrystalService(store crystal.CrystalStore) *CrystalService {
	return &CrystalService{store: store}
}

// GetCrystal retrieves a crystal by path.
func (s *CrystalService) GetCrystal(ctx context.Context, path string) (*crystal.Crystal, error) {
	return s.store.Get(ctx, path)
}

// ListCrystals lists crystals matching a path pattern.
func (s *CrystalService) ListCrystals(ctx context.Context, pattern string, limit int) ([]*crystal.Crystal, error) {
	if limit <= 0 {
		limit = 50
	}
	return s.store.List(ctx, pattern, limit)
}

// SearchCrystals searches crystals by content/primitives.
func (s *CrystalService) SearchCrystals(ctx context.Context, query string, limit int) ([]*crystal.Crystal, error) {
	if limit <= 0 {
		limit = 20
	}
	return s.store.Search(ctx, query, limit)
}

// GetCrystalStats returns crystal store statistics.
func (s *CrystalService) GetCrystalStats(ctx context.Context) (*crystal.CrystalStats, error) {
	return s.store.Stats(ctx)
}

// Store returns the underlying CrystalStore for direct access.
func (s *CrystalService) Store() crystal.CrystalStore {
	return s.store
}
