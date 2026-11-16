package contextengine

import (
	"context"
	"testing"

	"github.com/stretchr/testify/require"
	ctxdomain "github.com/syntrex/gomcp/internal/domain/context"
	"github.com/syntrex/gomcp/internal/domain/memory"
)

func TestL0RankingPreservesArchivedExclusionAndStalePenalty(t *testing.T) {
	store := newMockFactStore()
	active := memory.NewFact("active", memory.LevelProject, "", "")
	stale := memory.NewFact("stale", memory.LevelProject, "", "")
	stale.IsStale = true
	archived := memory.NewFact("archived", memory.LevelProject, "", "")
	archived.IsArchived = true
	for _, f := range []*memory.Fact{active, stale, archived} {
		require.NoError(t, store.Add(context.Background(), f))
	}
	provider := NewStoreFactProvider(store, &mockHotCache{l0Facts: []*memory.Fact{active}})
	raw, err := provider.GetL0Facts()
	require.NoError(t, err)
	require.Len(t, raw, 3)
	scorer := ctxdomain.NewRelevanceScorer(ctxdomain.DefaultEngineConfig())
	require.Zero(t, scorer.ScoreFact(archived, nil, 0))
	require.Greater(t, scorer.ScoreFact(stale, nil, 0), 0.0)
	ranked := scorer.RankFacts(raw, nil, nil)
	seen := map[string]bool{}
	for _, result := range ranked {
		seen[result.Fact.Content] = true
	}
	require.Equal(t, map[string]bool{"active": true, "stale": true}, seen)
	frame := New(ctxdomain.DefaultEngineConfig(), provider).BuildContext("synthetic_tool", nil)
	seen = map[string]bool{}
	for _, result := range frame.Facts {
		seen[result.Fact.Content] = true
	}
	require.Equal(t, map[string]bool{"active": true, "stale": true}, seen)
}
