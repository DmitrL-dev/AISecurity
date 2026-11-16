package sqlite

import (
	"context"
	"crypto/sha256"
	"database/sql"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"strconv"
	"strings"
	"time"

	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
)

// CentroidRepo implements memory.CentroidStore over the existing
// domain_centroids table (created by FactRepo.migrate). Its constructor owns
// only the versioned invalidation of historically unsafe derived rows.
type CentroidRepo struct {
	db *DB
}

const (
	centroidSessionIsolationVersionKey = "domain_centroids_session_isolation_version"
	centroidSessionIsolationCountKey   = "domain_centroids_session_isolation_rows_removed"
	centroidSessionIsolationVersion    = "2"
	centroidIntegrityColumn            = "session_isolation_sha256"
	centroidIntegrityDomain            = "spectorn/domain-centroid/session-isolation/v2"
)

// NewCentroidRepo returns a checked CentroidRepo. The domain_centroids and
// schema_info tables are created by FactRepo.migrate, so a FactRepo must be
// initialised on the same DB before this is used.
//
// Centroids are derived data and historically carried no fact/session lineage.
// Older builds could therefore persist a project-wide centroid computed from a
// session fact. The first constructor at this isolation version invalidates the
// entire derived cache transactionally. It also adds a backward-compatible
// integrity column: old writers omit it on INSERT and preserve a now-invalid
// digest on UPDATE, so a later fixed reader can reject downgrade-written rows.
func NewCentroidRepo(db *DB) (*CentroidRepo, error) {
	if db == nil || db.SqlDB() == nil {
		return nil, fmt.Errorf("centroid repo: database is required")
	}
	repo := &CentroidRepo{db: db}
	if err := repo.quarantineHistoricalSessionCentroids(context.Background()); err != nil {
		return nil, fmt.Errorf("centroid repo session-isolation migration: %w", err)
	}
	return repo, nil
}

func (r *CentroidRepo) quarantineHistoricalSessionCentroids(ctx context.Context) error {
	tx, err := r.db.SqlDB().BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("begin centroid quarantine: %w", err)
	}
	defer func() { _ = tx.Rollback() }()

	// INSERT OR IGNORE is the first write in the transaction. Besides recording
	// the version, it serialises concurrent initialisers before either one reads
	// migration state or invalidates the cache.
	result, err := tx.ExecContext(ctx, `INSERT OR IGNORE INTO schema_info (key, value) VALUES (?, ?)`,
		centroidSessionIsolationVersionKey, centroidSessionIsolationVersion)
	if err != nil {
		return fmt.Errorf("claim centroid quarantine version: %w", err)
	}
	inserted, err := result.RowsAffected()
	if err != nil {
		return fmt.Errorf("read centroid quarantine claim result: %w", err)
	}

	var version string
	if err := tx.QueryRowContext(ctx, `SELECT value FROM schema_info WHERE key = ?`,
		centroidSessionIsolationVersionKey).Scan(&version); err != nil {
		return fmt.Errorf("read centroid quarantine version: %w", err)
	}
	if version != centroidSessionIsolationVersion {
		return fmt.Errorf("unsupported centroid quarantine version %q", version)
	}
	if err := ensureCentroidIntegrityColumn(ctx, tx, inserted > 0); err != nil {
		return err
	}

	if inserted > 0 {
		deleted, err := tx.ExecContext(ctx, `DELETE FROM domain_centroids`)
		if err != nil {
			return fmt.Errorf("invalidate historical domain centroids: %w", err)
		}
		removed, err := deleted.RowsAffected()
		if err != nil {
			return fmt.Errorf("count invalidated historical domain centroids: %w", err)
		}
		if _, err := tx.ExecContext(ctx, `INSERT OR REPLACE INTO schema_info (key, value) VALUES (?, ?)`,
			centroidSessionIsolationCountKey, strconv.FormatInt(removed, 10)); err != nil {
			return fmt.Errorf("record invalidated historical domain centroids: %w", err)
		}
	} else {
		var rawCount string
		if err := tx.QueryRowContext(ctx, `SELECT value FROM schema_info WHERE key = ?`,
			centroidSessionIsolationCountKey).Scan(&rawCount); err != nil {
			return fmt.Errorf("read centroid quarantine audit count: %w", err)
		}
		removed, err := strconv.ParseInt(rawCount, 10, 64)
		if err != nil || removed < 0 {
			return fmt.Errorf("invalid centroid quarantine audit count %q", rawCount)
		}
	}

	if err := tx.Commit(); err != nil {
		return fmt.Errorf("commit centroid quarantine: %w", err)
	}
	return nil
}

func ensureCentroidIntegrityColumn(ctx context.Context, tx *sql.Tx, mayCreate bool) error {
	var (
		columnType  string
		notNull     int
		defaultExpr sql.NullString
	)
	err := tx.QueryRowContext(ctx, `SELECT type, "notnull", dflt_value
		FROM pragma_table_info('domain_centroids') WHERE name = ?`, centroidIntegrityColumn,
	).Scan(&columnType, &notNull, &defaultExpr)
	if err == sql.ErrNoRows {
		if !mayCreate {
			return fmt.Errorf("centroid integrity column is missing after completed quarantine")
		}
		if _, err := tx.ExecContext(ctx, `ALTER TABLE domain_centroids
			ADD COLUMN session_isolation_sha256 TEXT NOT NULL DEFAULT ''`); err != nil {
			return fmt.Errorf("add centroid integrity column: %w", err)
		}
		return nil
	}
	if err != nil {
		return fmt.Errorf("inspect centroid integrity column: %w", err)
	}
	if !strings.EqualFold(strings.TrimSpace(columnType), "TEXT") || notNull != 1 ||
		!defaultExpr.Valid || strings.TrimSpace(defaultExpr.String) != "''" {
		return fmt.Errorf("centroid integrity column has unsupported schema")
	}
	return nil
}

// Get returns the centroid for a single domain or nil if not present.
func (r *CentroidRepo) Get(ctx context.Context, domain string) (*memory.Centroid, error) {
	sc := rlmscope.FromContext(ctx)
	row := r.db.QueryRow(
		`SELECT tenant_id, project_id, domain, centroid, fact_count, updated_at,
		        session_isolation_sha256
		 FROM domain_centroids
		 WHERE tenant_id = ? AND project_id = ? AND domain = ?`,
		sc.TenantID, sc.ProjectID, domain)
	c, err := scanCentroid(row)
	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("get centroid: %w", err)
	}
	return c, nil
}

// GetAll returns every stored centroid.
func (r *CentroidRepo) GetAll(ctx context.Context) ([]*memory.Centroid, error) {
	sc := rlmscope.FromContext(ctx)
	rows, err := r.db.Query(
		`SELECT tenant_id, project_id, domain, centroid, fact_count, updated_at,
		        session_isolation_sha256
		 FROM domain_centroids
		 WHERE tenant_id = ? AND project_id = ?
		 ORDER BY domain ASC`, sc.TenantID, sc.ProjectID)
	if err != nil {
		return nil, fmt.Errorf("get all centroids: %w", err)
	}
	defer rows.Close()

	var out []*memory.Centroid
	for rows.Next() {
		centroid, err := scanCentroid(rows)
		if err != nil {
			return nil, fmt.Errorf("scan centroid row: %w", err)
		}
		out = append(out, centroid)
	}
	return out, rows.Err()
}

// Upsert inserts or replaces a centroid for a domain.
func (r *CentroidRepo) Upsert(ctx context.Context, c *memory.Centroid) error {
	if c == nil || c.Domain == "" {
		return fmt.Errorf("centroid: domain is required")
	}
	sc := rlmscope.FromContext(ctx)
	blob, err := json.Marshal(c.Vector)
	if err != nil {
		return fmt.Errorf("encode centroid vector: %w", err)
	}
	updated := c.UpdatedAt
	if updated.IsZero() {
		updated = time.Now().UTC()
	}
	updatedText := updated.UTC().Format(time.RFC3339Nano)
	integrity := centroidIntegrityHash(sc.TenantID, sc.ProjectID, c.Domain, blob, c.FactCount, updatedText)
	_, err = r.db.Exec(
		`INSERT INTO domain_centroids
			(tenant_id, project_id, domain, centroid, fact_count, updated_at, session_isolation_sha256)
			VALUES (?, ?, ?, ?, ?, ?, ?)
			ON CONFLICT(tenant_id, project_id, domain) DO UPDATE SET
				centroid = excluded.centroid,
				fact_count = excluded.fact_count,
				updated_at = excluded.updated_at,
				session_isolation_sha256 = excluded.session_isolation_sha256`,
		sc.TenantID, sc.ProjectID, c.Domain, blob, c.FactCount, updatedText, integrity)
	if err != nil {
		return fmt.Errorf("upsert centroid: %w", err)
	}
	return nil
}

// Delete removes a centroid by domain. No-op if absent.
func (r *CentroidRepo) Delete(ctx context.Context, domain string) error {
	sc := rlmscope.FromContext(ctx)
	_, err := r.db.Exec(`DELETE FROM domain_centroids
		WHERE tenant_id = ? AND project_id = ? AND domain = ?`,
		sc.TenantID, sc.ProjectID, domain)
	if err != nil {
		return fmt.Errorf("delete centroid: %w", err)
	}
	return nil
}

// RemoveAbsent deletes centroids whose domain is not in the keep list.
func (r *CentroidRepo) RemoveAbsent(ctx context.Context, keep []string) error {
	sc := rlmscope.FromContext(ctx)
	if len(keep) == 0 {
		_, err := r.db.Exec(`DELETE FROM domain_centroids WHERE tenant_id = ? AND project_id = ?`,
			sc.TenantID, sc.ProjectID)
		if err != nil {
			return fmt.Errorf("clear centroids: %w", err)
		}
		return nil
	}
	placeholders := make([]string, len(keep))
	args := make([]interface{}, len(keep))
	for i, d := range keep {
		placeholders[i] = "?"
		args[i] = d
	}
	q := `DELETE FROM domain_centroids
		WHERE tenant_id = ? AND project_id = ? AND domain NOT IN (` + strings.Join(placeholders, ",") + `)`
	scopedArgs := append([]interface{}{sc.TenantID, sc.ProjectID}, args...)
	if _, err := r.db.Exec(q, scopedArgs...); err != nil {
		return fmt.Errorf("remove absent centroids: %w", err)
	}
	return nil
}

type centroidScanner interface {
	Scan(dest ...any) error
}

func scanCentroid(row centroidScanner) (*memory.Centroid, error) {
	var (
		tenantID, projectID, domain string
		blob                        []byte
		factCount                   int
		updated                     string
		integrity                   string
	)
	if err := row.Scan(&tenantID, &projectID, &domain, &blob, &factCount, &updated, &integrity); err != nil {
		return nil, err
	}
	expected := centroidIntegrityHash(tenantID, projectID, domain, blob, factCount, updated)
	if integrity == "" || integrity != expected {
		return nil, fmt.Errorf("centroid integrity check failed for %s/%s/%s", tenantID, projectID, domain)
	}
	var vec []float64
	if len(blob) > 0 {
		if err := json.Unmarshal(blob, &vec); err != nil {
			return nil, fmt.Errorf("decode centroid: %w", err)
		}
	}
	ts, _ := time.Parse(time.RFC3339Nano, updated)
	if ts.IsZero() {
		ts, _ = time.Parse(time.RFC3339, updated)
	}
	return &memory.Centroid{Domain: domain, Vector: vec, FactCount: factCount, UpdatedAt: ts}, nil
}

func centroidIntegrityHash(tenantID, projectID, domain string, vector []byte, factCount int, updated string) string {
	payload := make([]byte, 0, len(centroidIntegrityDomain)+len(tenantID)+len(projectID)+len(domain)+len(vector)+len(updated)+56)
	for _, field := range [][]byte{
		[]byte(centroidIntegrityDomain),
		[]byte(tenantID),
		[]byte(projectID),
		[]byte(domain),
		vector,
		[]byte(updated),
	} {
		var size [8]byte
		binary.BigEndian.PutUint64(size[:], uint64(len(field)))
		payload = append(payload, size[:]...)
		payload = append(payload, field...)
	}
	var count [8]byte
	binary.BigEndian.PutUint64(count[:], uint64(int64(factCount)))
	payload = append(payload, count[:]...)
	digest := sha256.Sum256(payload)
	return hex.EncodeToString(digest[:])
}
