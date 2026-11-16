package sqlite

import (
	"context"
	"testing"

	"github.com/syntrex/gomcp/internal/domain/memory"

	"github.com/stretchr/testify/require"
)

// Origin has to survive the round trip, and the migration has to be honest about rows that
// predate it. Both are places where a trust field quietly becomes decoration.

func TestOriginSurvivesTheRoundTrip(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { db.Close() })
	repo, err := NewFactRepo(db)
	require.NoError(t, err)
	ctx := context.Background()

	for _, origin := range []memory.Origin{
		memory.OriginBuiltin, memory.OriginUser, memory.OriginDerived,
		memory.OriginExternal, memory.OriginUnspecified,
	} {
		f := memory.NewFact("content for "+string(origin), memory.LevelModule, "d", "m")
		f.Origin = origin
		require.NoError(t, repo.Add(ctx, f), "add %s", origin)

		got, err := repo.Get(ctx, f.ID)
		require.NoError(t, err)
		require.Equalf(t, origin, got.Origin,
			"origin did not survive storage; a trust field that resets on read is decoration")
	}
}

func TestOriginSurvivesUpdate(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { db.Close() })
	repo, err := NewFactRepo(db)
	require.NoError(t, err)
	ctx := context.Background()

	f := memory.NewFact("original", memory.LevelModule, "d", "m")
	f.Origin = memory.OriginExternal
	require.NoError(t, repo.Add(ctx, f))

	// The update path had no `origin` column in its SET list at first. An UPDATE that silently
	// dropped it would have let any edit launder an external fact into whatever the column
	// happened to default to — a privilege escalation performed by an ordinary write.
	f.Content = "edited"
	require.NoError(t, repo.Update(ctx, f))
	got, err := repo.Get(ctx, f.ID)
	require.NoError(t, err)
	require.Equal(t, memory.OriginExternal, got.Origin, "update lost the origin")
	require.Equal(t, "edited", got.Content)
}

func TestARowWrittenBeforeTheColumnExistedReadsAsUnspecified(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { db.Close() })
	repo, err := NewFactRepo(db)
	require.NoError(t, err)
	ctx := context.Background()

	f := memory.NewFact("legacy row", memory.LevelModule, "d", "m")
	f.Origin = memory.OriginUser
	require.NoError(t, repo.Add(ctx, f))

	// Simulate what an older database holds: the column present but empty, or holding a value
	// this build does not know. Neither may be read as OriginUser — that is the fail-safe
	// direction, and reading it optimistically is the defect this whole field replaces.
	for _, stored := range []string{"", "manual", "trusted", "USER"} {
		_, err = db.Exec(`UPDATE hierarchical_facts SET origin = ? WHERE id = ?`, stored, f.ID)
		require.NoError(t, err)
		got, err := repo.Get(ctx, f.ID)
		require.NoError(t, err)
		require.Equalf(t, memory.OriginUnspecified, got.Origin,
			"stored origin %q was read as %q; an unrecognised value must degrade to unspecified",
			stored, got.Origin)
	}
}

func TestCompressFactsInheritsTheLeastTrustedInput(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { db.Close() })
	repo, err := NewFactRepo(db)
	require.NoError(t, err)
	ctx := context.Background()

	trusted := memory.NewFact("a preference the user stated", memory.LevelModule, "prefs", "m")
	trusted.Origin = memory.OriginUser
	require.NoError(t, repo.Add(ctx, trusted))

	tainted := memory.NewFact("text that arrived from a document", memory.LevelModule, "prefs", "m")
	tainted.Origin = memory.OriginExternal
	require.NoError(t, repo.Add(ctx, tainted))

	summaryID, err := repo.CompressFacts(ctx, []string{trusted.ID, tainted.ID}, "combined summary")
	require.NoError(t, err)

	summary, err := repo.Get(ctx, summaryID)
	require.NoError(t, err)
	// Not OriginDerived. «Derived» says how the fact was made, not how far it may be trusted:
	// a summary of external content still carries that content's imperative, and pinning
	// consolidations at derived would launder external text upward on every pass — a slow,
	// automatic privilege escalation.
	require.Equal(t, memory.OriginExternal, summary.Origin,
		"consolidation must inherit the least trusted input")
}
