package sqlite

import (
	"context"
	"strings"
	"testing"

	"github.com/stretchr/testify/require"

	"github.com/syntrex/gomcp/internal/domain/memory"
)

func TestBoundedSessionContinuationSnapshotEnforcesFrozenFactAllowlist(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := NewFactRepo(db)
	require.NoError(t, err)
	ctx := scopedCtx("tenant-a", "project-frozen-session")

	allowed := memory.NewFact("needle allowed", memory.LevelDomain, "conversation", "chat")
	allowed.ID = "allowed-fact"
	allowed.Embedding = []float64{1}
	require.NoError(t, repo.AddForSession(ctx, "session-one", allowed))
	outside := memory.NewFact(
		"needle "+strings.Repeat("x", 16*1024*1024),
		memory.LevelDomain,
		"conversation",
		"chat",
	)
	outside.ID = "outside-fact"
	outside.Embedding = []float64{1}
	require.NoError(t, repo.AddForSession(ctx, "session-one", outside))

	tests := []struct {
		name string
		run  func(memory.BoundedSearchSnapshot) error
	}{
		{
			name: "get outside allowlist",
			run: func(snapshot memory.BoundedSearchSnapshot) error {
				_, err := snapshot.Get(context.Background(), outside.ID)
				return err
			},
		},
		{
			name: "keyword search after frozen preflight",
			run: func(snapshot memory.BoundedSearchSnapshot) error {
				_, err := snapshot.Search(context.Background(), "needle", 20)
				return err
			},
		},
		{
			name: "vector search after frozen preflight",
			run: func(snapshot memory.BoundedSearchSnapshot) error {
				_, err := snapshot.SearchByVector(context.Background(), []float64{1}, 20)
				return err
			},
		},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			callbackRan := false
			_, oversize, err := repo.WithBoundedSessionSearchSnapshot(
				ctx,
				"session-one",
				[]string{allowed.ID},
				func(snapshot memory.BoundedSearchSnapshot) ([]*memory.Fact, error) {
					callbackRan = true
					return nil, tc.run(snapshot)
				},
			)
			require.True(t, callbackRan)
			require.Nil(t, oversize, "only the small frozen fact is measured")
			require.Error(t, err)
		})
	}

	facts, oversize, err := repo.WithBoundedSessionSearchSnapshot(
		ctx,
		"session-one",
		[]string{allowed.ID},
		func(snapshot memory.BoundedSearchSnapshot) ([]*memory.Fact, error) {
			fact, err := snapshot.Get(context.Background(), allowed.ID)
			if err != nil {
				return nil, err
			}
			return []*memory.Fact{fact}, nil
		},
	)
	require.NoError(t, err)
	require.Nil(t, oversize)
	require.Len(t, facts, 1)
	require.Equal(t, allowed.ID, facts[0].ID)
}
