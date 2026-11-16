package tools

import (
	"context"
	"testing"

	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func newTestCrystalService(t *testing.T) *CrystalService {
	t.Helper()
	db, err := sqlite.OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { db.Close() })

	repo, err := sqlite.NewCrystalRepo(db)
	require.NoError(t, err)

	return NewCrystalService(repo)
}

func TestCrystalService_GetCrystal_NotFound(t *testing.T) {
	svc := newTestCrystalService(t)
	ctx := context.Background()

	_, err := svc.GetCrystal(ctx, "nonexistent/path.go")
	assert.Error(t, err)
}

func TestCrystalService_ListCrystals_Empty(t *testing.T) {
	svc := newTestCrystalService(t)
	ctx := context.Background()

	crystals, err := svc.ListCrystals(ctx, "", 10)
	require.NoError(t, err)
	assert.Empty(t, crystals)
}

func TestCrystalService_ListCrystals_DefaultLimit(t *testing.T) {
	svc := newTestCrystalService(t)
	ctx := context.Background()

	// limit <= 0 should default to 50.
	crystals, err := svc.ListCrystals(ctx, "", 0)
	require.NoError(t, err)
	assert.Empty(t, crystals)
}

func TestCrystalService_SearchCrystals_Empty(t *testing.T) {
	svc := newTestCrystalService(t)
	ctx := context.Background()

	crystals, err := svc.SearchCrystals(ctx, "nonexistent", 5)
	require.NoError(t, err)
	assert.Empty(t, crystals)
}

func TestCrystalService_SearchCrystals_DefaultLimit(t *testing.T) {
	svc := newTestCrystalService(t)
	ctx := context.Background()

	// limit <= 0 should default to 20.
	crystals, err := svc.SearchCrystals(ctx, "test", 0)
	require.NoError(t, err)
	assert.Empty(t, crystals)
}

func TestCrystalService_GetCrystalStats_Empty(t *testing.T) {
	svc := newTestCrystalService(t)
	ctx := context.Background()

	stats, err := svc.GetCrystalStats(ctx)
	require.NoError(t, err)
	assert.NotNil(t, stats)
	assert.Equal(t, 0, stats.TotalCrystals)
}
