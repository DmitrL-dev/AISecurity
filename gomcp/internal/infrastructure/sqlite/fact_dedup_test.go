package sqlite

import (
	"context"
	"testing"

	"github.com/syntrex/gomcp/internal/domain/memory"

	"github.com/stretchr/testify/require"
)

// Deduplication was added after measuring the live store on Global: 13 rows held 11 distinct
// statements. One sentence — «Owner prefers metric units in all reports.» — was there three
// times, written twice by an agent and once by the owner.
//
// That measurement is what these tests defend. The count is the least of it: duplicates crowd out
// distinct facts in any top-K recall, so a store that repeats itself retrieves less than one that
// does not, while reporting more.

func countFactRows(t *testing.T, repo *FactRepo, content string) int {
	t.Helper()
	var n int
	require.NoError(t, repo.db.QueryRow(
		`SELECT COUNT(*) FROM hierarchical_facts WHERE content = ?`, content).Scan(&n))
	return n
}

func storedOrigin(t *testing.T, repo *FactRepo, content string) string {
	t.Helper()
	var origin string
	require.NoError(t, repo.db.QueryRow(
		`SELECT origin FROM hierarchical_facts WHERE content = ?`, content).Scan(&origin))
	return origin
}

func TestIdenticalContentIsStoredOnce(t *testing.T) {
	repo := newTestFactRepo(t)
	ctx := context.Background()
	const content = "Owner prefers metric units in all reports."

	for i := 0; i < 3; i++ {
		f := memory.NewFact(content, memory.LevelDomain, "prefs", "")
		f.Origin = memory.OriginExternal
		require.NoError(t, repo.Add(ctx, f))
	}
	require.Equal(t, 1, countFactRows(t, repo, content),
		"three writes of the same sentence produced more than one row")
}

func TestFoldingKeepsTheMostTrustedOrigin(t *testing.T) {
	// The case measured live, in the order it actually happened: an agent wrote it twice, then the
	// owner said it themselves. Folding to the LEAST trusted origin would silently demote the
	// owner's standing instruction to reference material, which is how a writer could neutralise a
	// user instruction just by repeating it.
	repo := newTestFactRepo(t)
	ctx := context.Background()
	const content = "Owner prefers metric units in all reports."

	for _, origin := range []memory.Origin{
		memory.OriginExternal, memory.OriginExternal, memory.OriginUser,
	} {
		f := memory.NewFact(content, memory.LevelDomain, "prefs", "")
		f.Origin = origin
		require.NoError(t, repo.Add(ctx, f))
	}
	require.Equal(t, string(memory.OriginUser), storedOrigin(t, repo, content))
}

func TestFoldingKeepsTheMostTrustedOriginInEitherOrder(t *testing.T) {
	// Order must not decide trust. If the user speaks first, a later external restatement of the
	// same sentence must not take the row away from them.
	repo := newTestFactRepo(t)
	ctx := context.Background()
	const content = "Reports use metric units."

	for _, origin := range []memory.Origin{memory.OriginUser, memory.OriginExternal} {
		f := memory.NewFact(content, memory.LevelDomain, "prefs", "")
		f.Origin = origin
		require.NoError(t, repo.Add(ctx, f))
	}
	require.Equal(t, string(memory.OriginUser), storedOrigin(t, repo, content))
}

func TestTheCallerGetsTheIDOfTheRowThatExists(t *testing.T) {
	// Without this, a caller that folds holds an id no row has. Every later Get, Update or link by
	// that id fails, and it fails for a write the store reported as successful.
	repo := newTestFactRepo(t)
	ctx := context.Background()
	const content = "The gateway enforces on scan."

	first := memory.NewFact(content, memory.LevelDomain, "policy", "")
	require.NoError(t, repo.Add(ctx, first))

	second := memory.NewFact(content, memory.LevelDomain, "policy", "")
	originalID := second.ID
	require.NoError(t, repo.Add(ctx, second))

	require.NotEqual(t, originalID, second.ID, "the folded fact kept an id that was never inserted")
	require.Equal(t, first.ID, second.ID)

	got, err := repo.Get(ctx, second.ID)
	require.NoError(t, err, "the id handed back must be resolvable")
	require.Equal(t, content, got.Content)
}

func TestFoldingTakesTheHigherConfidence(t *testing.T) {
	repo := newTestFactRepo(t)
	ctx := context.Background()
	const content = "Alerts route to security@."

	high := memory.NewFact(content, memory.LevelDomain, "ops", "")
	high.Confidence = 0.9
	require.NoError(t, repo.Add(ctx, high))

	low := memory.NewFact(content, memory.LevelDomain, "ops", "")
	low.Confidence = 0.2
	require.NoError(t, repo.Add(ctx, low))

	var confidence float64
	require.NoError(t, repo.db.QueryRow(
		`SELECT confidence FROM hierarchical_facts WHERE content = ?`, content).Scan(&confidence))
	require.InDelta(t, 0.9, confidence, 0.0001,
		"a restatement eroded a fact the store was already sure of")
}

func TestDifferentLevelOrDomainIsNotADuplicate(t *testing.T) {
	// The same sentence at two levels is two claims about scope, not one fact written twice. L0
	// «project» and L1 «domain» say different things about how far the statement reaches.
	repo := newTestFactRepo(t)
	ctx := context.Background()
	const content = "Compression is measured on the corpus, not on one prompt."

	require.NoError(t, repo.Add(ctx, memory.NewFact(content, memory.LevelProject, "", "")))
	require.NoError(t, repo.Add(ctx, memory.NewFact(content, memory.LevelDomain, "metrics", "")))
	require.NoError(t, repo.Add(ctx, memory.NewFact(content, memory.LevelDomain, "release", "")))

	require.Equal(t, 3, countFactRows(t, repo, content))
}

func TestNegationIsNotFoldedIntoItsOpposite(t *testing.T) {
	// Why the match is exact rather than fuzzy. These two sentences are near-identical by any
	// similarity measure and mean opposite things; folding one into the other would delete an
	// instruction and report success.
	repo := newTestFactRepo(t)
	ctx := context.Background()

	require.NoError(t, repo.Add(ctx,
		memory.NewFact("Owner wants metric units in reports.", memory.LevelDomain, "prefs", "")))
	require.NoError(t, repo.Add(ctx,
		memory.NewFact("Owner does not want metric units in reports.", memory.LevelDomain, "prefs", "")))

	require.Equal(t, 1, countFactRows(t, repo, "Owner wants metric units in reports."))
	require.Equal(t, 1, countFactRows(t, repo, "Owner does not want metric units in reports."))
}

func TestAnArchivedRowIsNotAFoldTarget(t *testing.T) {
	// Folding a live write into an archived row would leave the content invisible to retrieval
	// while telling the writer it was stored — a write that reports success and remembers nothing.
	repo := newTestFactRepo(t)
	ctx := context.Background()
	const content = "Retired invariant."

	old := memory.NewFact(content, memory.LevelDomain, "history", "")
	require.NoError(t, repo.Add(ctx, old))
	_, err := repo.db.Exec(`UPDATE hierarchical_facts SET is_archived = 1 WHERE id = ?`, old.ID)
	require.NoError(t, err)

	fresh := memory.NewFact(content, memory.LevelDomain, "history", "")
	require.NoError(t, repo.Add(ctx, fresh))

	require.NotEqual(t, old.ID, fresh.ID)
	require.Equal(t, 2, countFactRows(t, repo, content))
}

func TestFoldingDoesNotCrossProjects(t *testing.T) {
	// Two tenants holding the same sentence are two facts. Folding across the scope boundary would
	// hand one tenant's row to another, which is a data leak wearing the costume of tidiness.
	//
	// The scope comes from the context, not from the fact: Add overwrites the fact's tenant and
	// project from the ambient scope, so a test that set the fields directly would silently be
	// writing both rows into the same project and passing for the wrong reason.
	repo := newTestFactRepo(t)
	const content = "Shared wording, separate owners."

	a := memory.NewFact(content, memory.LevelDomain, "prefs", "")
	require.NoError(t, repo.Add(scopedCtx("tenant-a", "proj-a"), a))

	b := memory.NewFact(content, memory.LevelDomain, "prefs", "")
	require.NoError(t, repo.Add(scopedCtx("tenant-b", "proj-b"), b))

	require.NotEqual(t, a.ID, b.ID)
	require.Equal(t, 2, countFactRows(t, repo, content))
}

func TestRetrievalReturnsDistinctFactsAfterDedup(t *testing.T) {
	// The reason dedup matters, stated as a measurement rather than as tidiness. Ten writes of one
	// sentence plus three distinct ones used to fill recall with repetitions of the same thing.
	repo := newTestFactRepo(t)
	ctx := context.Background()

	for i := 0; i < 10; i++ {
		require.NoError(t, repo.Add(ctx,
			memory.NewFact("Repeated sentence.", memory.LevelDomain, "prefs", "")))
	}
	for _, content := range []string{"Distinct one.", "Distinct two.", "Distinct three."} {
		require.NoError(t, repo.Add(ctx, memory.NewFact(content, memory.LevelDomain, "prefs", "")))
	}

	facts, err := repo.ListByDomain(ctx, "prefs", false)
	require.NoError(t, err)
	seen := map[string]bool{}
	for _, f := range facts {
		require.False(t, seen[f.Content], "recall returned %q twice", f.Content)
		seen[f.Content] = true
	}
	require.Len(t, seen, 4, "13 writes should be 4 distinct facts, all of them recallable")
}

// The cleanup for rows that predate deduplication. These tests write duplicates the way the old
// code did — straight INSERT, bypassing Add — because that is the state a live store is actually in.

func insertRaw(t *testing.T, repo *FactRepo, id, content, origin string, level int, confidence float64, createdAt string) {
	t.Helper()
	_, err := repo.db.Exec(`INSERT INTO hierarchical_facts
		(id, tenant_id, project_id, content, level, domain, created_at, valid_from,
		 is_stale, is_archived, confidence, source, origin)
		VALUES (?, 'local', 'default', ?, ?, 'prefs', ?, ?, 0, 0, ?, 'test', ?)`,
		id, content, level, createdAt, createdAt, confidence, origin)
	require.NoError(t, err)
}

func TestFoldExistingDuplicatesArchivesLosersAndKeepsTheOldest(t *testing.T) {
	repo := newTestFactRepo(t)
	ctx := context.Background()
	const content = "Owner prefers metric units in all reports."

	// The three rows measured on Global, in their real order and with their real origins.
	insertRaw(t, repo, "dup-1", content, "external", 1, 0.5, "2026-08-06T04:59:04Z")
	insertRaw(t, repo, "dup-2", content, "external", 1, 0.7, "2026-08-06T05:00:18Z")
	insertRaw(t, repo, "dup-3", content, "user", 1, 0.6, "2026-08-06T06:19:51Z")

	folded, err := repo.FoldExistingDuplicates(ctx)
	require.NoError(t, err)
	require.Equal(t, 2, folded)

	var live int
	require.NoError(t, repo.db.QueryRow(
		`SELECT COUNT(*) FROM hierarchical_facts WHERE content = ? AND is_archived = 0`,
		content).Scan(&live))
	require.Equal(t, 1, live, "the group should leave exactly one live row")

	var survivorOrigin string
	var survivorConf float64
	require.NoError(t, repo.db.QueryRow(
		`SELECT origin, confidence FROM hierarchical_facts WHERE id = 'dup-1'`).
		Scan(&survivorOrigin, &survivorConf))
	require.Equal(t, "user", survivorOrigin,
		"the owner said it; archiving their row must not archive their authorship")
	require.InDelta(t, 0.7, survivorConf, 0.0001, "the survivor takes the group's highest confidence")

	// Nothing was deleted. If this rule is wrong about a pair, the rows are still there.
	require.Equal(t, 3, countFactRows(t, repo, content))
}

func TestFoldExistingDuplicatesIsIdempotent(t *testing.T) {
	// It runs on every migrate, so a second pass must be a no-op. A pass that kept finding work
	// would archive a row on every startup until one was left standing by accident.
	repo := newTestFactRepo(t)
	ctx := context.Background()
	insertRaw(t, repo, "a", "Repeated.", "external", 1, 0.5, "2026-08-01T00:00:00Z")
	insertRaw(t, repo, "b", "Repeated.", "external", 1, 0.5, "2026-08-02T00:00:00Z")

	first, err := repo.FoldExistingDuplicates(ctx)
	require.NoError(t, err)
	require.Equal(t, 1, first)

	second, err := repo.FoldExistingDuplicates(ctx)
	require.NoError(t, err)
	require.Equal(t, 0, second, "a second pass found work that should not exist")
}

func TestFoldExistingDuplicatesLeavesDistinctFactsAlone(t *testing.T) {
	repo := newTestFactRepo(t)
	ctx := context.Background()
	insertRaw(t, repo, "x", "One thing.", "user", 1, 1.0, "2026-08-01T00:00:00Z")
	insertRaw(t, repo, "y", "Another thing.", "user", 1, 1.0, "2026-08-02T00:00:00Z")
	insertRaw(t, repo, "z", "One thing.", "user", 0, 1.0, "2026-08-03T00:00:00Z")

	folded, err := repo.FoldExistingDuplicates(ctx)
	require.NoError(t, err)
	require.Equal(t, 0, folded, "different content or level is not a duplicate")
}

func TestMigrateFoldsPreExistingDuplicatesAndRecordsHowMany(t *testing.T) {
	// The execution half. Adding FoldExistingDuplicates without a caller would reproduce exactly
	// the defect class this project keeps finding: a mechanism whose silence reads as health.
	repo := newTestFactRepo(t)
	insertRaw(t, repo, "m1", "Twice written.", "external", 1, 0.5, "2026-08-01T00:00:00Z")
	insertRaw(t, repo, "m2", "Twice written.", "user", 1, 0.5, "2026-08-02T00:00:00Z")

	require.NoError(t, repo.migrate())

	var live int
	require.NoError(t, repo.db.QueryRow(
		`SELECT COUNT(*) FROM hierarchical_facts WHERE content = 'Twice written.' AND is_archived = 0`).
		Scan(&live))
	require.Equal(t, 1, live, "migrate did not run the fold")

	var recorded string
	require.NoError(t, repo.db.QueryRow(
		`SELECT value FROM schema_info WHERE key = 'duplicates_folded_total'`).Scan(&recorded))
	require.Equal(t, "1", recorded, "the store should be able to say how many rows it shed")
}

func TestTheDedupLookupUsesAnIndex(t *testing.T) {
	// foldIntoDuplicate runs on every Add. Without an index covering content, SQLite falls back to
	// the (tenant, project, level) index and compares content row by row — thousands of row reads
	// per write on a store of any size, which would make deduplication cost more than the
	// duplicates it removes. EXPLAIN QUERY PLAN is the only way to check this rather than assume it.
	repo := newTestFactRepo(t)

	rows, err := repo.db.Query(`EXPLAIN QUERY PLAN
		SELECT id, origin, confidence FROM hierarchical_facts
		WHERE tenant_id = ? AND project_id = ? AND content = ? AND level = ?
		  AND IFNULL(domain, '') = IFNULL(?, '')
		  AND is_archived = 0 AND is_stale = 0
		ORDER BY created_at ASC LIMIT 1`, "local", "default", "x", 1, nil)
	require.NoError(t, err)
	defer rows.Close()

	var plan string
	for rows.Next() {
		var id, parent, notused int
		var detail string
		require.NoError(t, rows.Scan(&id, &parent, &notused, &detail))
		plan += detail + "\n"
	}
	require.NoError(t, rows.Err())

	require.Contains(t, plan, "idx_facts_dedup",
		"the duplicate lookup is not using the dedup index; plan was:\n"+plan)
	require.NotContains(t, plan, "SCAN hierarchical_facts",
		"the duplicate lookup degraded to a full table scan; plan was:\n"+plan)
}

func TestFoldingKeepsTheFirstEmbedding(t *testing.T) {
	// Deduplication keys on content, level and domain — not on the embedding. That is deliberate: an
	// embedding is a function of the text, so identical text with a different vector means the
	// embedder changed, not that there are two facts. The first row's vector survives, because the
	// later writer computed its vector from the same sentence and has nothing new to say about it.
	//
	// Written down because it surfaced as a test failure elsewhere rather than as a decision:
	// fact_repo_search_test.go stored five facts all named "f" with five different vectors, which
	// this rule collapses to one. Real data cannot produce that shape; a fixture can.
	repo := newTestFactRepo(t)
	ctx := context.Background()
	const content = "The gateway terminates TLS at nginx."

	first := memory.NewFact(content, memory.LevelDomain, "network", "")
	first.Embedding = []float64{1, 0}
	require.NoError(t, repo.Add(ctx, first))

	second := memory.NewFact(content, memory.LevelDomain, "network", "")
	second.Embedding = []float64{0, 1}
	require.NoError(t, repo.Add(ctx, second))

	require.Equal(t, 1, countFactRows(t, repo, content))
	require.Equal(t, first.ID, second.ID)

	stored, err := repo.Get(ctx, first.ID)
	require.NoError(t, err)
	require.Equal(t, []float64{1, 0}, stored.Embedding,
		"the surviving row should keep the embedding it was stored with")
}

func TestFoldingAdoptsAnEmbeddingWhereThereWasNone(t *testing.T) {
	// The edge this deduplication opened in itself. A fact stored while the embedder was unavailable
	// keeps a NULL vector; the same sentence stored later WITH a vector folds into that row, and
	// without this the fact stays permanently invisible to semantic search while both writers were
	// told it was stored — the exact shape of defect the deduplication exists to remove.
	repo := newTestFactRepo(t)
	ctx := context.Background()
	const content = "Certificate renewal runs from certbot on the host."

	blind := memory.NewFact(content, memory.LevelDomain, "network", "")
	require.Empty(t, blind.Embedding, "this case is about a fact stored with no vector")
	require.NoError(t, repo.Add(ctx, blind))

	sighted := memory.NewFact(content, memory.LevelDomain, "network", "")
	sighted.Embedding = []float64{0.25, 0.5}
	require.NoError(t, repo.Add(ctx, sighted))

	require.Equal(t, 1, countFactRows(t, repo, content))
	stored, err := repo.Get(ctx, blind.ID)
	require.NoError(t, err)
	require.Equal(t, []float64{0.25, 0.5}, stored.Embedding,
		"the surviving row should have adopted the vector it did not have")

	// And the search index too, or the vector exists on the row and nothing can find it.
	var indexed int
	require.NoError(t, repo.db.QueryRow(
		`SELECT COUNT(*) FROM embeddings_index WHERE fact_id = ?`, blind.ID).Scan(&indexed))
	require.Equal(t, 1, indexed, "the embeddings index was not updated on adoption")
}
