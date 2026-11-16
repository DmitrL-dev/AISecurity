package contextengine

import (
	"context"
	"github.com/stretchr/testify/require"
	"github.com/syntrex/gomcp/internal/domain/memory"
	"testing"
)

func TestL0ProviderDoesNotTreatPartialCacheAsComplete(t *testing.T) {
	store := newMockFactStore()
	a := memory.NewFact("synthetic A", memory.LevelProject, "", "")
	b := memory.NewFact("synthetic B", memory.LevelProject, "", "")
	require.NoError(t, store.Add(context.Background(), a))
	require.NoError(t, store.Add(context.Background(), b))
	provider := NewStoreFactProvider(store, &mockHotCache{l0Facts: []*memory.Fact{a}})
	facts, err := provider.GetL0Facts()
	require.NoError(t, err)
	require.Len(t, facts, 2, "partial cache must not hide durable fact")
}
