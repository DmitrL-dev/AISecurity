package sqlite

import (
	"context"
	"crypto/sha256"
	"testing"
	"time"

	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// newTestCentroidRepo opens an in-memory DB, runs FactRepo migrations
// (which create domain_centroids), and returns a fresh CentroidRepo.
func newTestCentroidRepo(t *testing.T) *CentroidRepo {
	t.Helper()
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { db.Close() })
	_, err = NewFactRepo(db)
	require.NoError(t, err)
	repo, err := NewCentroidRepo(db)
	require.NoError(t, err)
	return repo
}

func TestNewCentroidRepoQuarantinesHistoricalDerivedRowsOnce(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	_, err = NewFactRepo(db)
	require.NoError(t, err)

	_, err = db.Exec(`INSERT INTO domain_centroids
		(tenant_id, project_id, domain, centroid, fact_count, updated_at)
		VALUES ('local', 'project-alpha', 'private-session-domain', '[1,0]', 1, ?)`,
		time.Now().UTC().Format(time.RFC3339Nano))
	require.NoError(t, err)

	repo, err := NewCentroidRepo(db)
	require.NoError(t, err)
	historical, err := repo.GetAll(rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-alpha")))
	require.NoError(t, err)
	require.Empty(t, historical, "historically session-derived centroids must not reach legacy reads")

	var version, removed string
	require.NoError(t, db.QueryRow(`SELECT value FROM schema_info WHERE key = ?`,
		centroidSessionIsolationVersionKey).Scan(&version))
	require.NoError(t, db.QueryRow(`SELECT value FROM schema_info WHERE key = ?`,
		centroidSessionIsolationCountKey).Scan(&removed))
	require.Equal(t, centroidSessionIsolationVersion, version)
	require.Equal(t, "1", removed)

	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-alpha"))
	require.NoError(t, repo.Upsert(ctx, &memory.Centroid{
		Domain: "rebuilt-legacy-domain", Vector: []float64{0, 1}, FactCount: 1,
	}))
	reopened, err := NewCentroidRepo(db)
	require.NoError(t, err)
	rebuilt, err := reopened.GetAll(ctx)
	require.NoError(t, err)
	require.Len(t, rebuilt, 1, "the version marker must preserve safely rebuilt centroids")
	require.Equal(t, "rebuilt-legacy-domain", rebuilt[0].Domain)
}

func TestNewCentroidRepoQuarantineRollsBackAndSurfacesMigrationErrors(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	_, err = NewFactRepo(db)
	require.NoError(t, err)

	_, err = db.Exec(`INSERT INTO domain_centroids
		(tenant_id, project_id, domain, centroid, fact_count, updated_at)
		VALUES ('local', 'default', 'must-survive-failed-migration', '[1]', 1, ?)`,
		time.Now().UTC().Format(time.RFC3339Nano))
	require.NoError(t, err)
	_, err = db.Exec(`CREATE TRIGGER fail_centroid_quarantine_audit
		BEFORE INSERT ON schema_info
		WHEN NEW.key = '` + centroidSessionIsolationCountKey + `'
		BEGIN SELECT RAISE(ABORT, 'forced centroid quarantine audit failure'); END`)
	require.NoError(t, err)

	_, err = NewCentroidRepo(db)
	require.ErrorContains(t, err, "forced centroid quarantine audit failure")

	var centroidCount, markerCount, integrityColumnCount int
	require.NoError(t, db.QueryRow(`SELECT COUNT(*) FROM domain_centroids`).Scan(&centroidCount))
	require.NoError(t, db.QueryRow(`SELECT COUNT(*) FROM schema_info WHERE key = ?`,
		centroidSessionIsolationVersionKey).Scan(&markerCount))
	require.NoError(t, db.QueryRow(`SELECT COUNT(*) FROM pragma_table_info('domain_centroids')
		WHERE name = ?`, centroidIntegrityColumn).Scan(&integrityColumnCount))
	require.Equal(t, 1, centroidCount, "failed migration must roll back cache deletion")
	require.Zero(t, markerCount, "failed migration must not leave a false completion marker")
	require.Zero(t, integrityColumnCount, "failed migration must roll back the schema change")
}

func TestCentroidRepoRejectsDowngradeInsertUntilFixedRecompute(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	_, err = NewFactRepo(db)
	require.NoError(t, err)
	// Only the schema is needed here: the old writer inserts directly.
	_, err = NewCentroidRepo(db)
	require.NoError(t, err)

	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-alpha"))
	oldUpdated := time.Date(2026, time.August, 1, 1, 2, 3, 0, time.UTC).Format(time.RFC3339Nano)
	_, err = db.Exec(`INSERT INTO domain_centroids
		(tenant_id, project_id, domain, centroid, fact_count, updated_at)
		VALUES (?, ?, ?, ?, ?, ?)`,
		"local", "project-alpha", "downgrade-insert", []byte(`[1,0]`), 1, oldUpdated)
	require.NoError(t, err)

	// Model a forward upgrade after the old writer exits. The completed marker
	// preserves valid cache rows, while the row-level digest rejects this one.
	repo, err := NewCentroidRepo(db)
	require.NoError(t, err)
	got, err := repo.Get(ctx, "downgrade-insert")
	require.Nil(t, got)
	require.ErrorContains(t, err, "centroid integrity check failed")
	_, err = repo.GetAll(ctx)
	require.ErrorContains(t, err, "centroid integrity check failed")

	// Recompute repairs the row through the fixed Upsert path.
	require.NoError(t, repo.Upsert(ctx, &memory.Centroid{
		Domain: "downgrade-insert", Vector: []float64{0, 1}, FactCount: 2,
		UpdatedAt: time.Date(2026, time.August, 2, 1, 2, 3, 0, time.UTC),
	}))
	got, err = repo.Get(ctx, "downgrade-insert")
	require.NoError(t, err)
	require.NotNil(t, got)
	require.Equal(t, 2, got.FactCount)
	require.Equal(t, []float64{0, 1}, got.Vector)
}

func TestCentroidRepoRejectsDowngradeUpdateThatPreservesStaleDigest(t *testing.T) {
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	_, err = NewFactRepo(db)
	require.NoError(t, err)
	repo, err := NewCentroidRepo(db)
	require.NoError(t, err)

	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-alpha"))
	require.NoError(t, repo.Upsert(ctx, &memory.Centroid{
		Domain: "downgrade-update", Vector: []float64{1, 0}, FactCount: 1,
		UpdatedAt: time.Date(2026, time.August, 1, 1, 2, 3, 0, time.UTC),
	}))
	var digestBefore string
	require.NoError(t, db.QueryRow(`SELECT session_isolation_sha256 FROM domain_centroids
		WHERE tenant_id = ? AND project_id = ? AND domain = ?`,
		"local", "project-alpha", "downgrade-update").Scan(&digestBefore))
	require.NotEmpty(t, digestBefore)

	// This is the old Upsert shape: it changes every derived value but knows
	// nothing about the new column, so the previous digest survives the conflict.
	oldUpdated := time.Date(2026, time.August, 3, 1, 2, 3, 0, time.UTC).Format(time.RFC3339Nano)
	_, err = db.Exec(`INSERT INTO domain_centroids
			(tenant_id, project_id, domain, centroid, fact_count, updated_at)
			VALUES (?, ?, ?, ?, ?, ?)
			ON CONFLICT(tenant_id, project_id, domain) DO UPDATE SET
				centroid = excluded.centroid,
				fact_count = excluded.fact_count,
				updated_at = excluded.updated_at`,
		"local", "project-alpha", "downgrade-update", []byte(`[0,1]`), 7, oldUpdated)
	require.NoError(t, err)
	var digestAfter string
	require.NoError(t, db.QueryRow(`SELECT session_isolation_sha256 FROM domain_centroids
		WHERE tenant_id = ? AND project_id = ? AND domain = ?`,
		"local", "project-alpha", "downgrade-update").Scan(&digestAfter))
	require.Equal(t, digestBefore, digestAfter, "old update unexpectedly repaired the integrity digest")

	repo, err = NewCentroidRepo(db)
	require.NoError(t, err)
	got, err := repo.Get(ctx, "downgrade-update")
	require.Nil(t, got)
	require.ErrorContains(t, err, "centroid integrity check failed")

	require.NoError(t, repo.Upsert(ctx, &memory.Centroid{
		Domain: "downgrade-update", Vector: []float64{0, 1}, FactCount: 7,
		UpdatedAt: time.Date(2026, time.August, 4, 1, 2, 3, 0, time.UTC),
	}))
	got, err = repo.Get(ctx, "downgrade-update")
	require.NoError(t, err)
	require.NotNil(t, got)
	require.Equal(t, 7, got.FactCount)
}

func TestCentroidIntegrityHashBindsEveryPersistedField(t *testing.T) {
	base := centroidIntegrityHash("tenant-a", "project-a", "domain-a", []byte(`[1,0]`), 3, "2026-08-01T01:02:03Z")
	require.Len(t, base, sha256.Size*2)
	require.Equal(t, base,
		centroidIntegrityHash("tenant-a", "project-a", "domain-a", []byte(`[1,0]`), 3, "2026-08-01T01:02:03Z"),
		"identical persisted fields produced a different digest")

	variants := map[string]string{
		"tenant":     centroidIntegrityHash("tenant-b", "project-a", "domain-a", []byte(`[1,0]`), 3, "2026-08-01T01:02:03Z"),
		"project":    centroidIntegrityHash("tenant-a", "project-b", "domain-a", []byte(`[1,0]`), 3, "2026-08-01T01:02:03Z"),
		"domain":     centroidIntegrityHash("tenant-a", "project-a", "domain-b", []byte(`[1,0]`), 3, "2026-08-01T01:02:03Z"),
		"vector":     centroidIntegrityHash("tenant-a", "project-a", "domain-a", []byte(`[0,1]`), 3, "2026-08-01T01:02:03Z"),
		"fact_count": centroidIntegrityHash("tenant-a", "project-a", "domain-a", []byte(`[1,0]`), 4, "2026-08-01T01:02:03Z"),
		"updated_at": centroidIntegrityHash("tenant-a", "project-a", "domain-a", []byte(`[1,0]`), 3, "2026-08-02T01:02:03Z"),
	}
	for field, variant := range variants {
		require.NotEqualf(t, base, variant, "%s is not bound into the centroid digest", field)
	}
}

func TestCentroidRepo_Upsert_AndGet(t *testing.T) {
	repo := newTestCentroidRepo(t)
	ctx := context.Background()

	c := &memory.Centroid{
		Domain:    "alpha",
		Vector:    []float64{0.5, 0.5, 0.5},
		FactCount: 7,
		UpdatedAt: time.Date(2026, 5, 8, 10, 0, 0, 0, time.UTC),
	}
	require.NoError(t, repo.Upsert(ctx, c))

	got, err := repo.Get(ctx, "alpha")
	require.NoError(t, err)
	require.NotNil(t, got)
	assert.Equal(t, "alpha", got.Domain)
	assert.Equal(t, 7, got.FactCount)
	assert.InDeltaSlice(t, []float64{0.5, 0.5, 0.5}, got.Vector, 1e-9)
}

func TestCentroidRepo_Get_NotFoundReturnsNil(t *testing.T) {
	repo := newTestCentroidRepo(t)
	got, err := repo.Get(context.Background(), "nope")
	require.NoError(t, err)
	assert.Nil(t, got)
}

func TestCentroidRepo_Upsert_ReplacesExisting(t *testing.T) {
	repo := newTestCentroidRepo(t)
	ctx := context.Background()

	require.NoError(t, repo.Upsert(ctx, &memory.Centroid{Domain: "d", Vector: []float64{1, 0}, FactCount: 2}))
	require.NoError(t, repo.Upsert(ctx, &memory.Centroid{Domain: "d", Vector: []float64{0, 1}, FactCount: 5}))

	got, err := repo.Get(ctx, "d")
	require.NoError(t, err)
	require.NotNil(t, got)
	assert.Equal(t, 5, got.FactCount)
	assert.InDeltaSlice(t, []float64{0, 1}, got.Vector, 1e-9)
}

func TestCentroidRepo_GetAll_Sorted(t *testing.T) {
	repo := newTestCentroidRepo(t)
	ctx := context.Background()

	for _, d := range []string{"gamma", "alpha", "beta"} {
		require.NoError(t, repo.Upsert(ctx, &memory.Centroid{Domain: d, Vector: []float64{1}, FactCount: 1}))
	}

	all, err := repo.GetAll(ctx)
	require.NoError(t, err)
	require.Len(t, all, 3)
	assert.Equal(t, "alpha", all[0].Domain)
	assert.Equal(t, "beta", all[1].Domain)
	assert.Equal(t, "gamma", all[2].Domain)
}

func TestCentroidRepo_Delete(t *testing.T) {
	repo := newTestCentroidRepo(t)
	ctx := context.Background()

	require.NoError(t, repo.Upsert(ctx, &memory.Centroid{Domain: "x", Vector: []float64{1}, FactCount: 1}))
	require.NoError(t, repo.Delete(ctx, "x"))

	got, err := repo.Get(ctx, "x")
	require.NoError(t, err)
	assert.Nil(t, got)

	// Deleting absent is a no-op.
	require.NoError(t, repo.Delete(ctx, "absent"))
}

func TestCentroidRepo_RemoveAbsent(t *testing.T) {
	repo := newTestCentroidRepo(t)
	ctx := context.Background()

	for _, d := range []string{"keep1", "drop1", "keep2", "drop2"} {
		require.NoError(t, repo.Upsert(ctx, &memory.Centroid{Domain: d, Vector: []float64{1}, FactCount: 1}))
	}

	require.NoError(t, repo.RemoveAbsent(ctx, []string{"keep1", "keep2"}))

	all, err := repo.GetAll(ctx)
	require.NoError(t, err)
	require.Len(t, all, 2)
	domains := []string{all[0].Domain, all[1].Domain}
	assert.Contains(t, domains, "keep1")
	assert.Contains(t, domains, "keep2")
}

func TestCentroidRepo_RemoveAbsent_EmptyKeepClearsAll(t *testing.T) {
	repo := newTestCentroidRepo(t)
	ctx := context.Background()

	require.NoError(t, repo.Upsert(ctx, &memory.Centroid{Domain: "x", Vector: []float64{1}, FactCount: 1}))
	require.NoError(t, repo.Upsert(ctx, &memory.Centroid{Domain: "y", Vector: []float64{1}, FactCount: 1}))

	require.NoError(t, repo.RemoveAbsent(ctx, nil))

	all, err := repo.GetAll(ctx)
	require.NoError(t, err)
	assert.Empty(t, all)
}

func TestCentroidRepo_Upsert_RequiresDomain(t *testing.T) {
	repo := newTestCentroidRepo(t)
	err := repo.Upsert(context.Background(), &memory.Centroid{Vector: []float64{1}, FactCount: 1})
	assert.Error(t, err)
}
