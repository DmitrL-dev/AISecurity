package sqlite

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"runtime"
	"strings"
	"testing"
	"time"

	"github.com/stretchr/testify/require"

	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
)

func addStatsPageFact(
	t *testing.T,
	repo *FactRepo,
	ctx context.Context,
	id, domain string,
) *memory.Fact {
	t.Helper()
	fact := memory.NewFact("stats "+id, memory.LevelProject, domain, "")
	fact.ID = id
	fact.Origin = memory.OriginExternal
	require.NoError(t, repo.Add(ctx, fact))
	return fact
}

func fixedFromLegacyStats(stats *memory.FactStoreStats) *memory.FixedFactStoreStats {
	return &memory.FixedFactStoreStats{
		TotalFacts:     stats.TotalFacts,
		LiveFacts:      stats.LiveFacts,
		ArchivedCount:  stats.ArchivedCount,
		ByLevel:        stats.ByLevel,
		ByOrigin:       stats.ByOrigin,
		StaleCount:     stats.StaleCount,
		WithEmbeddings: stats.WithEmbeddings,
		GeneCount:      stats.GeneCount,
		ColdCount:      stats.ColdCount,
		GenomeHash:     stats.GenomeHash,
	}
}

func collectStatsSnapshotDomains(
	t *testing.T,
	repo *FactRepo,
	ctx context.Context,
	first *memory.FactStatsPage,
) []memory.FactStatsDomain {
	t.Helper()
	page := first
	var (
		entries         []memory.FactStatsDomain
		current         []byte
		currentDigest   string
		currentTotal    int
		expectedOrdinal int64
		calls           int
	)
	for {
		calls++
		require.LessOrEqual(t, calls, memory.FactStatsPageMaxCalls)
		for _, segment := range page.Segments {
			require.Equal(t, expectedOrdinal, segment.Ordinal)
			require.Equal(t, len(current), segment.Offset)
			if len(current) == 0 {
				currentDigest = segment.SHA256
				currentTotal = segment.TotalBytes
			} else {
				require.Equal(t, currentDigest, segment.SHA256)
				require.Equal(t, currentTotal, segment.TotalBytes)
			}
			current = append(current, segment.Data...)
			if segment.Final {
				require.Len(t, current, currentTotal)
				digest := sha256.Sum256(current)
				require.Equal(t, currentDigest, hex.EncodeToString(digest[:]))
				var entry memory.FactStatsDomain
				require.NoError(t, json.Unmarshal(current, &entry))
				entries = append(entries, entry)
				current = nil
				currentDigest = ""
				currentTotal = 0
				expectedOrdinal++
			}
		}
		if page.Done {
			break
		}
		var err error
		page, err = repo.FactStatsPage(ctx, &memory.FactStatsPagePosition{
			SnapshotID:       page.SnapshotID,
			ExpectedRows:     page.ExpectedRows,
			ExpectedDomains:  page.ExpectedDomains,
			ExpectedSegments: page.ExpectedSegments,
			SerializedBytes:  page.SerializedBytes,
			SegmentIndex:     page.NextSegmentIndex,
			SegmentOffset:    page.NextSegmentOffset,
		})
		require.NoError(t, err)
		require.Nil(t, page.Fixed)
	}
	require.Empty(t, current)
	require.Equal(t, first.ExpectedDomains, int64(len(entries)))
	return entries
}

func TestFactStatsPageMatchesLegacyFixedStatsAndWalksOrderedDomains(t *testing.T) {
	_, repo := newFactPageRepo(t)
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-alpha"))
	other := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-beta"))

	for _, pair := range [][2]string{{"fact-z", "zeta"}, {"fact-a", "alpha"}, {"fact-m", "middle"}, {"fact-empty", ""}} {
		addStatsPageFact(t, repo, ctx, pair[0], pair[1])
	}
	addStatsPageFact(t, repo, other, "wrong-project", "must-not-leak")
	session := memory.NewFact("session must not leak", memory.LevelProject, "session-private", "")
	session.ID = "session-fact"
	session.Origin = memory.OriginUser
	require.NoError(t, repo.AddForSession(ctx, "session-one", session))

	legacy, err := repo.Stats(ctx)
	require.NoError(t, err)
	first, err := repo.FactStatsPage(ctx, nil)
	require.NoError(t, err)
	require.EqualValues(t, 4, first.ExpectedRows)
	require.EqualValues(t, 3, first.ExpectedDomains)
	require.Equal(t, fixedFromLegacyStats(legacy), first.Fixed)
	require.True(t, validFactStatsSnapshotID(first.SnapshotID))

	// A post-snapshot insert, even one that sorts before the current domain,
	// does not enter the immutable walk.
	addStatsPageFact(t, repo, ctx, "fact-later", "000-later")
	entries := collectStatsSnapshotDomains(t, repo, ctx, first)
	domains := make([]string, 0, len(entries))
	for _, entry := range entries {
		domains = append(domains, entry.Domain)
	}
	require.Equal(t, []string{"alpha", "middle", "zeta"}, domains)
}

func TestFactStatsPageKeepsExactBinaryScopeOnLegacyNoCaseSchema(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo := &FactRepo{db: db}

	// Legacy or externally altered databases may inherit NOCASE from stored
	// columns. The bounded protocol must still compare every scope and export
	// identity byte-for-byte instead of silently folding a sibling project in.
	_, err = db.Exec(`CREATE TABLE hierarchical_facts (
		id TEXT COLLATE NOCASE NOT NULL,
		tenant_id TEXT COLLATE NOCASE NOT NULL,
		project_id TEXT COLLATE NOCASE NOT NULL,
		content TEXT NOT NULL,
		level INTEGER NOT NULL,
		domain TEXT,
		embedding BLOB,
		created_at TEXT NOT NULL,
		is_stale INTEGER NOT NULL DEFAULT 0,
		is_archived INTEGER NOT NULL DEFAULT 0,
		source TEXT NOT NULL,
		origin TEXT NOT NULL,
		hit_count INTEGER NOT NULL DEFAULT 0,
		session_id TEXT COLLATE NOCASE
	)`)
	require.NoError(t, err)
	_, err = db.Exec(`CREATE TABLE fact_export_sequence (
		seq INTEGER PRIMARY KEY AUTOINCREMENT,
		fact_id TEXT COLLATE NOCASE NOT NULL
	)`)
	require.NoError(t, err)
	_, err = db.Exec(`CREATE TABLE fact_stats_page_snapshots (
		snapshot_id TEXT COLLATE BINARY PRIMARY KEY,
		tenant_id TEXT COLLATE BINARY NOT NULL,
		project_id TEXT COLLATE BINARY NOT NULL,
		expected_rows INTEGER NOT NULL,
		expected_domains INTEGER NOT NULL,
		expected_segments INTEGER NOT NULL,
		serialized_bytes INTEGER NOT NULL,
		expires_at_unix INTEGER NOT NULL,
		UNIQUE (tenant_id, project_id)
	)`)
	require.NoError(t, err)
	_, err = db.Exec(`CREATE TABLE fact_stats_page_snapshot_segments (
		snapshot_id TEXT COLLATE BINARY NOT NULL,
		segment_index INTEGER NOT NULL,
		ordinal INTEGER NOT NULL,
		sha256 TEXT COLLATE BINARY NOT NULL,
		total_bytes INTEGER NOT NULL,
		offset_bytes INTEGER NOT NULL,
		data BLOB NOT NULL,
		is_final INTEGER NOT NULL,
		PRIMARY KEY (snapshot_id, segment_index),
		FOREIGN KEY (snapshot_id) REFERENCES fact_stats_page_snapshots(snapshot_id)
			ON DELETE CASCADE
	)`)
	require.NoError(t, err)

	_, err = db.Exec(`INSERT INTO hierarchical_facts
		(id, tenant_id, project_id, content, level, domain, created_at,
		 source, origin, session_id)
	VALUES
		('fact-a', 'tenant-a', 'project-alpha', 'a', 0, 'alpha',
		 '2026-01-02T03:04:05Z', 'test', 'external', ''),
		('fact-b', 'tenant-a', 'project-alpha', 'b', 0, 'beta',
		 '2026-01-02T03:04:05Z', 'test', 'external', ''),
		('FACT-A', 'TENANT-A', 'PROJECT-ALPHA', 'sibling', 0, 'must-not-leak',
		 '2026-01-02T03:04:05Z', 'test', 'external', '')`)
	require.NoError(t, err)
	_, err = db.Exec(`INSERT INTO fact_export_sequence(fact_id)
		VALUES ('fact-a'), ('fact-b'), ('FACT-A')`)
	require.NoError(t, err)

	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-alpha"))
	page, err := repo.FactStatsPage(ctx, nil)
	require.NoError(t, err)
	require.EqualValues(t, 2, page.ExpectedRows)
	require.EqualValues(t, 2, page.ExpectedDomains)
	require.Equal(t, 2, page.Fixed.TotalFacts)
	require.Equal(t, []memory.FactStatsDomain{
		{Domain: "alpha", Count: 1}, {Domain: "beta", Count: 1},
	}, collectStatsSnapshotDomains(t, repo, ctx, page))
}

func TestFactStatsPageUpdateAndDeleteDoNotChangeMaterializedSnapshot(t *testing.T) {
	for _, mutation := range []string{"update", "delete"} {
		t.Run(mutation, func(t *testing.T) {
			_, repo := newFactPageRepo(t)
			ctx := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-alpha"))
			addStatsPageFact(t, repo, ctx, "fact-a", "alpha")
			beta := "beta-" + strings.Repeat("b", memory.FactStatsPageFrameRawBytes+1024)
			victim := addStatsPageFact(t, repo, ctx, "fact-b", beta)
			first, err := repo.FactStatsPage(ctx, nil)
			require.NoError(t, err)
			require.False(t, first.Done, "large aggregate must exercise a continuation")

			switch mutation {
			case "update":
				victim.Domain = "changed"
				victim.UpdatedAt = time.Now()
				require.NoError(t, repo.Update(ctx, victim))
			case "delete":
				require.NoError(t, repo.Delete(ctx, victim.ID))
			}
			entries := collectStatsSnapshotDomains(t, repo, ctx, first)
			require.Equal(t, []memory.FactStatsDomain{
				{Domain: "alpha", Count: 1}, {Domain: beta, Count: 1},
			}, entries)
		})
	}
}

func TestFactStatsPageRejectsOversizedStoredDomainBeforeMaterialization(t *testing.T) {
	_, repo := newFactPageRepo(t)
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-alpha"))
	addStatsPageFact(t, repo, ctx, "oversized-domain",
		strings.Repeat("x", int(memory.FactStatsPageStoredDomainHardMaxBytes)+1))

	runtime.GC()
	var before, after runtime.MemStats
	runtime.ReadMemStats(&before)
	_, err := repo.FactStatsPage(ctx, nil)
	runtime.ReadMemStats(&after)
	require.Less(t, after.TotalAlloc-before.TotalAlloc, uint64(128<<10),
		"stats paging must not allocate the oversized stored domain")
	require.ErrorContains(t, err, "stored fact stats")
	var oversized *memory.FactStatsPageStoredOversize
	require.ErrorAs(t, err, &oversized)
	require.Equal(t, memory.BoundedSearchStoredRowOversizeKind, oversized.Measurement.Kind)
	require.Greater(t, oversized.Measurement.StoredBytes, memory.FactStatsPageStoredDomainHardMaxBytes)
	require.Equal(t, memory.FactStatsPageStoredDomainHardMaxBytes, oversized.Measurement.MaxStoredBytes)
}

func TestFactStatsPageRejectsOversizedStoredDomainAggregateBeforeGrouping(t *testing.T) {
	_, repo := newFactPageRepo(t)
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-alpha"))
	for index := 0; index < 13; index++ {
		prefix := fmt.Sprintf("%02d-", index)
		domain := prefix + strings.Repeat("x",
			int(memory.FactStatsPageStoredDomainHardMaxBytes)-len(prefix))
		addStatsPageFact(t, repo, ctx, fmt.Sprintf("aggregate-%d", index), domain)
	}

	_, err := repo.FactStatsPage(ctx, nil)
	require.ErrorContains(t, err, "stored fact stats")
	var oversized *memory.FactStatsPageStoredOversize
	require.ErrorAs(t, err, &oversized)
	require.Equal(t, memory.BoundedSearchStoredScopeOversizeKind, oversized.Measurement.Kind)
	require.Greater(t, oversized.Measurement.StoredBytes, memory.FactStatsPageStoredDomainScopeHardMaxBytes)
	require.Equal(t, memory.FactStatsPageStoredDomainScopeHardMaxBytes, oversized.Measurement.MaxStoredBytes)
}

func TestFactStatsPageRejectsMoreThanTenThousandDistinctDomains(t *testing.T) {
	db, repo := newFactPageRepo(t)
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-alpha"))
	_, err := db.Exec(`DROP TRIGGER fact_export_sequence_insert_v1`)
	require.NoError(t, err)
	_, err = db.Exec(`WITH RECURSIVE sequence(value) AS (
		VALUES(0)
		UNION ALL
		SELECT value + 1 FROM sequence WHERE value < 10000
	)
	INSERT INTO hierarchical_facts
		(id, tenant_id, project_id, content, level, domain, module,
		 created_at, valid_from, source, origin)
	SELECT printf('stats-domain-%05d', value), 'tenant-a', 'project-alpha',
		'x', 0, printf('domain-%05d', value), '',
		'2026-01-02T03:04:05Z', '2026-01-02T03:04:05Z', 'test', 'external'
	FROM sequence`)
	require.NoError(t, err)
	_, err = db.Exec(`INSERT INTO fact_export_sequence(fact_id)
		SELECT id FROM hierarchical_facts
		WHERE tenant_id = 'tenant-a' AND project_id = 'project-alpha'`)
	require.NoError(t, err)

	_, err = repo.FactStatsPage(ctx, nil)
	require.ErrorContains(t, err, "stored fact stats")
	var oversized *memory.FactStatsPageStoredOversize
	require.ErrorAs(t, err, &oversized)
	require.Equal(t, memory.BoundedSearchStoredRowCountOversizeKind, oversized.Measurement.Kind)
	require.EqualValues(t, 10_001, oversized.Measurement.StoredRows)
	require.Equal(t, memory.FactStatsPageMaxDomains, oversized.Measurement.MaxStoredRows)
}

func TestFactStatsPageKeepsActiveScopeAndCapsGlobalSnapshots(t *testing.T) {
	_, repo := newFactPageRepo(t)
	contexts := make([]context.Context, 3)
	for index := range contexts {
		contexts[index] = rlmscope.WithScope(context.Background(),
			rlmscope.New("tenant-a", fmt.Sprintf("project-%d", index)))
		addStatsPageFact(t, repo, contexts[index], fmt.Sprintf("capacity-%d", index),
			fmt.Sprintf("%d-", index)+strings.Repeat("x", memory.FactStatsPageFrameRawBytes+1024))
	}

	first, err := repo.FactStatsPage(contexts[0], nil)
	require.NoError(t, err)
	require.False(t, first.Done)
	second, err := repo.FactStatsPage(contexts[1], nil)
	require.NoError(t, err)
	require.False(t, second.Done)

	_, err = repo.FactStatsPage(contexts[0], nil)
	var busy *memory.FactStatsPageSnapshotBusy
	require.ErrorAs(t, err, &busy)
	_, err = repo.FactStatsPage(contexts[2], nil)
	var capacity *memory.FactStatsPageSnapshotCapacity
	require.ErrorAs(t, err, &capacity)
	require.Equal(t, memory.FactStatsPageMaxActiveSnapshots, capacity.ActiveSnapshots)
	require.Equal(t, memory.FactStatsPageMaxActiveSnapshots, capacity.MaxActiveSnapshots)
	require.LessOrEqual(t, capacity.ActiveSerializedBytes,
		memory.FactStatsPageMaxActiveSnapshotBytes)
	require.LessOrEqual(t, capacity.ActiveSegments,
		memory.FactStatsPageMaxActiveSnapshotSegments)

	// Completing one walk releases its process-wide slot immediately.
	require.Len(t, collectStatsSnapshotDomains(t, repo, contexts[0], first), 1)
	third, err := repo.FactStatsPage(contexts[2], nil)
	require.NoError(t, err)
	require.False(t, third.Done)
}

func TestFactStatsPageCompletedWalkReleasesSnapshotAndOldCursorFailsClosed(t *testing.T) {
	db, repo := newFactPageRepo(t)
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-alpha"))
	addStatsPageFact(t, repo, ctx, "release", "large-"+
		strings.Repeat("x", memory.FactStatsPageFrameRawBytes+1024))
	first, err := repo.FactStatsPage(ctx, nil)
	require.NoError(t, err)
	require.False(t, first.Done)
	position := memory.FactStatsPagePosition{
		SnapshotID:       first.SnapshotID,
		ExpectedRows:     first.ExpectedRows,
		ExpectedDomains:  first.ExpectedDomains,
		ExpectedSegments: first.ExpectedSegments,
		SerializedBytes:  first.SerializedBytes,
		SegmentIndex:     first.NextSegmentIndex,
		SegmentOffset:    first.NextSegmentOffset,
	}
	last, err := repo.FactStatsPage(ctx, &position)
	require.NoError(t, err)
	require.True(t, last.Done)
	var active int64
	require.NoError(t, db.QueryRow(`SELECT COUNT(*) FROM fact_stats_page_snapshots`).Scan(&active))
	require.Zero(t, active)
	_, err = repo.FactStatsPage(ctx, &position)
	require.True(t, errors.Is(err, memory.ErrFactStatsPageChanged))
}
