package tools

import (
	"context"
	"fmt"
	"github.com/stretchr/testify/require"
	"github.com/syntrex/gomcp/internal/domain/memory"
	"github.com/syntrex/gomcp/internal/infrastructure/cache"
	"path/filepath"
	"testing"
)

func TestL0ReadsDoNotTreatPartialCacheAsComplete(t *testing.T) {
	ctx := context.Background()
	base := newTestFactService(t)
	hot, err := cache.NewBoltCache(filepath.Join(t.TempDir(), "cache.db"))
	require.NoError(t, err)
	t.Cleanup(func() { _ = hot.Close() })
	svc := NewFactService(base.Store(), hot)
	a, err := svc.AddFact(ctx, AddFactParams{Content: "synthetic A", Level: int(memory.LevelProject)})
	require.NoError(t, err)
	require.NoError(t, hot.WarmUp(ctx, []*memory.Fact{a}))
	_, err = svc.AddFact(ctx, AddFactParams{Content: "synthetic B", Level: int(memory.LevelProject)})
	require.NoError(t, err)
	facts, err := svc.GetL0Facts(ctx)
	require.NoError(t, err)
	require.Len(t, facts, 2, "partial cache must not hide durable fact")
}

type l0FailingStore struct{ memory.FactStore }

func (s l0FailingStore) ListByLevel(context.Context, memory.HierLevel) ([]*memory.Fact, error) {
	return nil, fmt.Errorf("synthetic store failure")
}
func TestL0ReadDoesNotFallBackToCachedDataOnStoreFailure(t *testing.T) {
	ctx := context.Background()
	base := newTestFactService(t)
	hot, err := cache.NewBoltCache(filepath.Join(t.TempDir(), "cache.db"))
	require.NoError(t, err)
	t.Cleanup(func() { _ = hot.Close() })
	require.NoError(t, hot.WarmUp(ctx, []*memory.Fact{memory.NewFact("stale synthetic", memory.LevelProject, "", "")}))
	facts, err := NewFactService(l0FailingStore{base.Store()}, hot).GetL0Facts(ctx)
	require.Error(t, err)
	require.Empty(t, facts)
}
