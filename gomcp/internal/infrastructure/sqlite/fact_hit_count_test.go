package sqlite

import (
	"context"
	"testing"

	"github.com/syntrex/gomcp/internal/domain/memory"

	"github.com/stretchr/testify/require"
)

// `hit_count` had a writer and no reader.
//
// TouchFact incremented it on every context access, a migration created it, an index covered it, and
// `Fact.HitCount` was declared in the domain type as «v3.3: context access counter». Nothing ever put
// the column into that field: `factColumns` did not list it, so every fact loaded from the store
// carried HitCount = 0 no matter how often it had been used. The only reader of the column was the
// GC's `hit_count = 0` predicate, which needs the value but never returns it.
//
// The visible consequence was in ranking. The relevance scorer weights frequency at 0.15 and scales it
// against a ceiling of 100 accesses — a ceiling that only means something across sessions — while the
// counts it actually read came from a map created empty in the engine's constructor. So a fact used
// ninety times over months scored on frequency exactly like one never used, every time the process
// restarted, and an MCP server restarts constantly.
//
// These tests pin the read path. Both scanners are exercised on purpose: one column list feeds a
// singular `scanFact` and a plural `scanFacts`, and updating only one of them fails at runtime with a
// column-count error rather than at build time.

func TestHitCountSurvivesTheReadPath(t *testing.T) {
	repo := newTestFactRepo(t)
	ctx := context.Background()

	fact := memory.NewFact("The gateway runs three legs on spectorn-ru.", memory.LevelDomain, "ops", "")
	require.NoError(t, repo.Add(ctx, fact))

	const accesses = 3
	for i := 0; i < accesses; i++ {
		require.NoError(t, repo.TouchFact(ctx, fact.ID))
	}

	// Singular scanner.
	got, err := repo.Get(ctx, fact.ID)
	require.NoError(t, err)
	require.Equal(t, accesses, got.HitCount,
		"Get must report the accesses the database recorded, not zero")

	// Plural scanner, same column list.
	listed, err := repo.ListByLevel(ctx, memory.LevelDomain)
	require.NoError(t, err)
	var seen bool
	for _, f := range listed {
		if f.ID == fact.ID {
			seen = true
			require.Equal(t, accesses, f.HitCount,
				"the list scanner must read the same column as the singular one")
		}
	}
	require.True(t, seen, "the stored fact must appear in its level listing")
}

func TestAnUntouchedFactReadsAsZeroRatherThanFailing(t *testing.T) {
	// The column is added by an ALTER on databases that predate it, so existing rows hold NULL.
	// COALESCE in the column list is what keeps that from becoming a scan error on every read of an
	// older store — worth a test, because a NULL is invisible in a fresh one.
	repo := newTestFactRepo(t)
	ctx := context.Background()

	fact := memory.NewFact("Never accessed, still readable.", memory.LevelDomain, "ops", "")
	require.NoError(t, repo.Add(ctx, fact))
	_, err := repo.db.Exec(`UPDATE hierarchical_facts SET hit_count = NULL WHERE id = ?`, fact.ID)
	require.NoError(t, err)

	got, err := repo.Get(ctx, fact.ID)
	require.NoError(t, err, "a NULL counter must read as zero, not break the row")
	require.Equal(t, 0, got.HitCount)
}

func TestUpdateDoesNotResetTheAccessCounter(t *testing.T) {
	// Update writes an explicit column list that omits hit_count, so editing a fact's content keeps
	// its history. That is current behaviour rather than a stated intention, which is why it is pinned:
	// adding hit_count to that SET list would silently zero the counter on every edit.
	repo := newTestFactRepo(t)
	ctx := context.Background()

	fact := memory.NewFact("Original wording.", memory.LevelDomain, "ops", "")
	require.NoError(t, repo.Add(ctx, fact))
	require.NoError(t, repo.TouchFact(ctx, fact.ID))
	require.NoError(t, repo.TouchFact(ctx, fact.ID))

	stored, err := repo.Get(ctx, fact.ID)
	require.NoError(t, err)
	stored.Content = "Revised wording."
	require.NoError(t, repo.Update(ctx, stored))

	after, err := repo.Get(ctx, fact.ID)
	require.NoError(t, err)
	require.Equal(t, "Revised wording.", after.Content)
	require.Equal(t, 2, after.HitCount, "an edit is not a reason to forget how often a fact was used")
}
