package sqlite

import (
	"context"
	"fmt"
	"time"

	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
	"github.com/syntrex/gomcp/internal/domain/synapse"
)

const synapseColumns = `id, tenant_id, project_id, fact_id_a, fact_id_b, confidence, status, created_at`

// Session facts have no synapse surface. This correlated predicate keeps both
// endpoints inside the legacy non-session fact boundary for every read and
// mutation, including rows created before session isolation existed.
const legacySynapseFactsPredicate = `
	AND EXISTS (
		SELECT 1 FROM hierarchical_facts fact_a
		WHERE fact_a.id = synapses.fact_id_a
		  AND fact_a.tenant_id = synapses.tenant_id
		  AND fact_a.project_id = synapses.project_id
		  AND (fact_a.session_id IS NULL OR fact_a.session_id = '')
	)
	AND EXISTS (
		SELECT 1 FROM hierarchical_facts fact_b
		WHERE fact_b.id = synapses.fact_id_b
		  AND fact_b.tenant_id = synapses.tenant_id
		  AND fact_b.project_id = synapses.project_id
		  AND (fact_b.session_id IS NULL OR fact_b.session_id = '')
	)`

// SynapseRepo implements synapse.SynapseStore using SQLite.
type SynapseRepo struct {
	db *DB
}

// NewSynapseRepo creates a SynapseRepo (table created by FactRepo migration v3.3).
func NewSynapseRepo(db *DB) *SynapseRepo {
	return &SynapseRepo{db: db}
}

// Create inserts a new PENDING synapse.
func (r *SynapseRepo) Create(ctx context.Context, factIDA, factIDB string, confidence float64) (int64, error) {
	sc := rlmscope.FromContext(ctx)
	if err := r.ensureProjectWritable(sc); err != nil {
		return 0, err
	}
	if err := r.ensureFactsInScope(sc, factIDA, factIDB); err != nil {
		return 0, err
	}
	result, err := r.db.Exec(
		`INSERT INTO synapses (tenant_id, project_id, fact_id_a, fact_id_b, confidence, status, created_at)
		 VALUES (?, ?, ?, ?, ?, 'PENDING', ?)`,
		sc.TenantID, sc.ProjectID, factIDA, factIDB, confidence, time.Now().Format(timeFormat))
	if err != nil {
		return 0, fmt.Errorf("create synapse: %w", err)
	}
	id, _ := result.LastInsertId()
	return id, nil
}

func (r *SynapseRepo) ensureProjectWritable(sc rlmscope.Scope) error {
	sc = sc.Normalize()
	now := time.Now().UTC().Format(timeFormat)
	if _, err := r.db.Exec(`INSERT OR IGNORE INTO rlm_projects
		(tenant_id, project_id, name, status, created_at, updated_at, last_accessed_at)
		VALUES (?, ?, ?, ?, ?, ?, ?)`,
		sc.TenantID, sc.ProjectID, sc.ProjectID, rlmscope.ProjectStatusActive, now, now, now); err != nil {
		return fmt.Errorf("ensure rlm project: %w", err)
	}
	status := rlmscope.ProjectStatusActive
	if err := r.db.QueryRow(`SELECT status FROM rlm_projects
		WHERE tenant_id = ? AND project_id = ?`, sc.TenantID, sc.ProjectID).Scan(&status); err != nil {
		return fmt.Errorf("check rlm project status: %w", err)
	}
	if status == rlmscope.ProjectStatusArchived {
		return fmt.Errorf("project %s is archived; activate_project before writing", sc.String())
	}
	if _, err := r.db.Exec(`UPDATE rlm_projects SET last_accessed_at = ?
		WHERE tenant_id = ? AND project_id = ?`, now, sc.TenantID, sc.ProjectID); err != nil {
		return fmt.Errorf("touch rlm project: %w", err)
	}
	return nil
}

func (r *SynapseRepo) ensureFactsInScope(sc rlmscope.Scope, factIDA, factIDB string) error {
	for _, id := range []string{factIDA, factIDB} {
		var count int
		if err := r.db.QueryRow(
			`SELECT COUNT(*) FROM hierarchical_facts
			 WHERE id = ? AND tenant_id = ? AND project_id = ?
			   AND (session_id IS NULL OR session_id = '')`,
			id, sc.TenantID, sc.ProjectID,
		).Scan(&count); err != nil {
			return fmt.Errorf("check synapse fact scope: %w", err)
		}
		if count == 0 {
			return fmt.Errorf("fact %s not found in scope %s", id, sc.String())
		}
	}
	return nil
}

// ListPending returns synapses with status PENDING.
func (r *SynapseRepo) ListPending(ctx context.Context, limit int) ([]*synapse.Synapse, error) {
	if limit <= 0 {
		limit = 50
	}
	sc := rlmscope.FromContext(ctx)
	rows, err := r.db.Query(
		`SELECT `+synapseColumns+`
		 FROM synapses
		 WHERE tenant_id = ? AND project_id = ? AND status = 'PENDING'`+legacySynapseFactsPredicate+`
		 ORDER BY confidence DESC LIMIT ?`,
		sc.TenantID, sc.ProjectID, limit)
	if err != nil {
		return nil, fmt.Errorf("list pending: %w", err)
	}
	defer rows.Close()
	return scanSynapses(rows)
}

// Accept transitions a synapse to VERIFIED.
func (r *SynapseRepo) Accept(ctx context.Context, id int64) error {
	sc := rlmscope.FromContext(ctx)
	if err := r.ensureProjectWritable(sc); err != nil {
		return err
	}
	result, err := r.db.Exec(`UPDATE synapses SET status = 'VERIFIED'
		WHERE id = ? AND tenant_id = ? AND project_id = ? AND status = 'PENDING'`+legacySynapseFactsPredicate,
		id, sc.TenantID, sc.ProjectID)
	if err != nil {
		return fmt.Errorf("accept synapse: %w", err)
	}
	n, _ := result.RowsAffected()
	if n == 0 {
		return fmt.Errorf("synapse %d not found or not PENDING", id)
	}
	return nil
}

// Reject transitions a synapse to REJECTED.
func (r *SynapseRepo) Reject(ctx context.Context, id int64) error {
	sc := rlmscope.FromContext(ctx)
	if err := r.ensureProjectWritable(sc); err != nil {
		return err
	}
	result, err := r.db.Exec(`UPDATE synapses SET status = 'REJECTED'
		WHERE id = ? AND tenant_id = ? AND project_id = ? AND status = 'PENDING'`+legacySynapseFactsPredicate,
		id, sc.TenantID, sc.ProjectID)
	if err != nil {
		return fmt.Errorf("reject synapse: %w", err)
	}
	n, _ := result.RowsAffected()
	if n == 0 {
		return fmt.Errorf("synapse %d not found or not PENDING", id)
	}
	return nil
}

// ListVerified returns all VERIFIED synapses.
func (r *SynapseRepo) ListVerified(ctx context.Context) ([]*synapse.Synapse, error) {
	sc := rlmscope.FromContext(ctx)
	rows, err := r.db.Query(
		`SELECT `+synapseColumns+`
		 FROM synapses
		 WHERE tenant_id = ? AND project_id = ? AND status = 'VERIFIED'`+legacySynapseFactsPredicate+`
		 ORDER BY confidence DESC`,
		sc.TenantID, sc.ProjectID)
	if err != nil {
		return nil, fmt.Errorf("list verified: %w", err)
	}
	defer rows.Close()
	return scanSynapses(rows)
}

// Count returns synapse counts by status.
func (r *SynapseRepo) Count(ctx context.Context) (pending, verified, rejected int, err error) {
	sc := rlmscope.FromContext(ctx)
	row := r.db.QueryRow(`SELECT
		COALESCE(SUM(CASE WHEN status='PENDING' THEN 1 ELSE 0 END), 0),
		COALESCE(SUM(CASE WHEN status='VERIFIED' THEN 1 ELSE 0 END), 0),
		COALESCE(SUM(CASE WHEN status='REJECTED' THEN 1 ELSE 0 END), 0)
		FROM synapses
		WHERE tenant_id = ? AND project_id = ?`+legacySynapseFactsPredicate,
		sc.TenantID, sc.ProjectID)
	err = row.Scan(&pending, &verified, &rejected)
	if err != nil {
		return 0, 0, 0, fmt.Errorf("count synapses: %w", err)
	}
	return
}

// Exists checks if a synapse exists between two facts (either direction).
func (r *SynapseRepo) Exists(ctx context.Context, factIDA, factIDB string) (bool, error) {
	sc := rlmscope.FromContext(ctx)
	var count int
	row := r.db.QueryRow(
		`SELECT COUNT(*) FROM synapses
		 WHERE tenant_id = ? AND project_id = ?
		   AND ((fact_id_a = ? AND fact_id_b = ?) OR (fact_id_a = ? AND fact_id_b = ?))`+legacySynapseFactsPredicate,
		sc.TenantID, sc.ProjectID, factIDA, factIDB, factIDB, factIDA)
	if err := row.Scan(&count); err != nil {
		return false, fmt.Errorf("exists synapse: %w", err)
	}
	return count > 0, nil
}

// Ensure SynapseRepo implements synapse.SynapseStore.
var _ synapse.SynapseStore = (*SynapseRepo)(nil)

func scanSynapses(rows interface {
	Next() bool
	Scan(...any) error
	Err() error
}) ([]*synapse.Synapse, error) {
	var result []*synapse.Synapse
	for rows.Next() {
		var s synapse.Synapse
		var status, createdAt string
		if err := rows.Scan(&s.ID, &s.TenantID, &s.ProjectID, &s.FactIDA, &s.FactIDB, &s.Confidence, &status, &createdAt); err != nil {
			return nil, fmt.Errorf("scan synapse: %w", err)
		}
		s.Status = synapse.Status(status)
		s.CreatedAt, _ = time.Parse(timeFormat, createdAt)
		result = append(result, &s)
	}
	// rows.Err() surfaces an iteration error (e.g. the query/connection failing
	// mid-scan); without it a truncated result set is returned as if complete.
	return result, rows.Err()
}
