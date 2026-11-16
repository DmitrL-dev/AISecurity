package sqlite

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"time"

	"github.com/syntrex/gomcp/internal/domain/orchestrator"
)

// OrchestratorRepo provides SQLite persistence for the data-capture flywheel:
// per-scan training samples (engine confidence features + verdict + an
// attachable analyst label). Tenant-scoped on every query (mirrors SOCRepo).
type OrchestratorRepo struct {
	db *DB
}

// NewOrchestratorRepo creates and initializes the orchestrator_samples table.
func NewOrchestratorRepo(db *DB) (*OrchestratorRepo, error) {
	repo := &OrchestratorRepo{db: db}
	if err := repo.migrate(); err != nil {
		return nil, fmt.Errorf("orchestrator_repo: migrate: %w", err)
	}
	return repo, nil
}

func (r *OrchestratorRepo) migrate() error {
	ddl := []string{
		`CREATE TABLE IF NOT EXISTS orchestrator_samples (
			id              TEXT PRIMARY KEY,
			tenant_id       TEXT NOT NULL DEFAULT '',
			timestamp       TEXT NOT NULL,
			prompt_hash     TEXT NOT NULL DEFAULT '',
			engine_vector   TEXT NOT NULL DEFAULT '[]',
			engine_scores   TEXT NOT NULL DEFAULT '{}',
			aggregate       TEXT NOT NULL DEFAULT '{}',
			vector_complete INTEGER NOT NULL DEFAULT 0,
			vector_schema   TEXT NOT NULL DEFAULT '',
			blocked         INTEGER NOT NULL DEFAULT 0,
			risk            REAL NOT NULL DEFAULT 0.0,
			threat_type     TEXT NOT NULL DEFAULT '',
			model_version   TEXT NOT NULL DEFAULT '',
			label           TEXT NOT NULL DEFAULT '',
			label_source    TEXT NOT NULL DEFAULT '',
			labeled_at      TEXT
		)`,
		`CREATE INDEX IF NOT EXISTS idx_orch_samples_tenant ON orchestrator_samples(tenant_id)`,
		`CREATE INDEX IF NOT EXISTS idx_orch_samples_ts ON orchestrator_samples(timestamp)`,
		// Composite index for the label-attach join (tenant + time window over
		// still-unlabeled rows) and for tenant-scoped labeled export.
		`CREATE INDEX IF NOT EXISTS idx_orch_samples_tenant_ts ON orchestrator_samples(tenant_id, timestamp)`,
		`CREATE INDEX IF NOT EXISTS idx_orch_samples_tenant_label ON orchestrator_samples(tenant_id, label)`,
	}
	for _, q := range ddl {
		if _, err := r.db.Exec(q); err != nil {
			return fmt.Errorf("exec %q: %w", q[:40], err)
		}
	}
	return nil
}

// Insert persists one captured sample.
func (r *OrchestratorRepo) Insert(s orchestrator.Sample) error {
	vecJSON, _ := json.Marshal(s.EngineVector)
	scoresJSON, _ := json.Marshal(s.EngineScores)
	aggJSON, _ := json.Marshal(s.Aggregate)
	var labeledAt *string
	if s.LabeledAt != nil && !s.LabeledAt.IsZero() {
		t := s.LabeledAt.Format(time.RFC3339Nano)
		labeledAt = &t
	}
	_, err := r.db.Exec(
		`INSERT INTO orchestrator_samples
		 (id, tenant_id, timestamp, prompt_hash, engine_vector, engine_scores, aggregate,
		  vector_complete, vector_schema, blocked, risk, threat_type, model_version,
		  label, label_source, labeled_at)
		 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		s.ID, s.TenantID, s.Timestamp.Format(time.RFC3339Nano), s.PromptHash,
		string(vecJSON), string(scoresJSON), string(aggJSON),
		b2i(s.VectorComplete), s.VectorSchema, b2i(s.Blocked), s.Risk, s.ThreatType,
		s.ModelVersion, string(s.Label), s.LabelSource, labeledAt,
	)
	return err
}

// AttachLabel writes the label onto every UNLABELED sample for the tenant in
// [from, to]. Only rows with an empty label are touched, so an earlier (and
// typically more specific) disposition is never overwritten by a later coarse one.
func (r *OrchestratorRepo) AttachLabel(tenantID string, from, to time.Time, label orchestrator.Label, source string) (int64, error) {
	if tenantID == "" {
		return 0, fmt.Errorf("attach label: empty tenant_id refused")
	}
	if !orchestrator.ValidLabel(label) {
		return 0, fmt.Errorf("attach label: invalid label %q", label)
	}
	now := time.Now().Format(time.RFC3339Nano)
	res, err := r.db.Exec(
		`UPDATE orchestrator_samples
		 SET label = ?, label_source = ?, labeled_at = ?
		 WHERE tenant_id = ? AND label = '' AND timestamp >= ? AND timestamp <= ?`,
		string(label), source, now, tenantID,
		from.Format(time.RFC3339Nano), to.Format(time.RFC3339Nano),
	)
	if err != nil {
		return 0, err
	}
	return res.RowsAffected()
}

// ExportLabeled returns the tenant's samples (newest first). onlyLabeled=true
// (the default export path) restricts to rows that carry a label.
func (r *OrchestratorRepo) ExportLabeled(tenantID string, limit int, onlyLabeled bool) ([]orchestrator.Sample, error) {
	if tenantID == "" {
		return nil, fmt.Errorf("export: empty tenant_id refused")
	}
	if limit <= 0 {
		limit = 10000
	}
	var rows *sql.Rows
	var err error
	if onlyLabeled {
		rows, err = r.db.Query(
			`SELECT id, tenant_id, timestamp, prompt_hash, engine_vector, engine_scores, aggregate,
			 vector_complete, vector_schema, blocked, risk, threat_type, model_version,
			 label, label_source, labeled_at
			 FROM orchestrator_samples
			 WHERE tenant_id = ? AND label != '' ORDER BY timestamp DESC LIMIT ?`, tenantID, limit)
	} else {
		rows, err = r.db.Query(
			`SELECT id, tenant_id, timestamp, prompt_hash, engine_vector, engine_scores, aggregate,
			 vector_complete, vector_schema, blocked, risk, threat_type, model_version,
			 label, label_source, labeled_at
			 FROM orchestrator_samples
			 WHERE tenant_id = ? ORDER BY timestamp DESC LIMIT ?`, tenantID, limit)
	}
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	return scanSamples(rows)
}

// CountSamples returns (total, labeled) for the tenant.
func (r *OrchestratorRepo) CountSamples(tenantID string) (int64, int64, error) {
	if tenantID == "" {
		return 0, 0, fmt.Errorf("count: empty tenant_id refused")
	}
	var total, labeled int64
	if err := r.db.QueryRow(
		"SELECT COUNT(*) FROM orchestrator_samples WHERE tenant_id = ?", tenantID,
	).Scan(&total); err != nil {
		return 0, 0, err
	}
	if err := r.db.QueryRow(
		"SELECT COUNT(*) FROM orchestrator_samples WHERE tenant_id = ? AND label != ''", tenantID,
	).Scan(&labeled); err != nil {
		return 0, 0, err
	}
	return total, labeled, nil
}

// PurgeExpired deletes samples older than retentionDays.
func (r *OrchestratorRepo) PurgeExpired(retentionDays int) (int64, error) {
	cutoff := time.Now().AddDate(0, 0, -retentionDays).Format(time.RFC3339)
	res, err := r.db.Exec("DELETE FROM orchestrator_samples WHERE timestamp < ?", cutoff)
	if err != nil {
		return 0, fmt.Errorf("purge orchestrator samples: %w", err)
	}
	return res.RowsAffected()
}

// DeleteByTenant erases all of a tenant's samples (GDPR Art.17).
func (r *OrchestratorRepo) DeleteByTenant(tenantID string) (int64, error) {
	if tenantID == "" {
		return 0, fmt.Errorf("delete by tenant: empty tenant_id refused")
	}
	res, err := r.db.Exec("DELETE FROM orchestrator_samples WHERE tenant_id = ?", tenantID)
	if err != nil {
		return 0, fmt.Errorf("delete orchestrator samples by tenant: %w", err)
	}
	return res.RowsAffected()
}

func scanSamples(rows *sql.Rows) ([]orchestrator.Sample, error) {
	var out []orchestrator.Sample
	for rows.Next() {
		var s orchestrator.Sample
		var ts string
		var vecJSON, scoresJSON, aggJSON string
		var vectorComplete, blocked int
		var labeledAt sql.NullString
		var label string
		if err := rows.Scan(&s.ID, &s.TenantID, &ts, &s.PromptHash,
			&vecJSON, &scoresJSON, &aggJSON,
			&vectorComplete, &s.VectorSchema, &blocked, &s.Risk, &s.ThreatType, &s.ModelVersion,
			&label, &s.LabelSource, &labeledAt); err != nil {
			return nil, err
		}
		s.Timestamp, _ = time.Parse(time.RFC3339Nano, ts)
		s.VectorComplete = vectorComplete != 0
		s.Blocked = blocked != 0
		s.Label = orchestrator.Label(label)
		if vecJSON != "" && vecJSON != "[]" {
			json.Unmarshal([]byte(vecJSON), &s.EngineVector)
		}
		if scoresJSON != "" && scoresJSON != "{}" {
			json.Unmarshal([]byte(scoresJSON), &s.EngineScores)
		}
		if aggJSON != "" && aggJSON != "{}" {
			json.Unmarshal([]byte(aggJSON), &s.Aggregate)
		}
		if labeledAt.Valid && labeledAt.String != "" {
			t, _ := time.Parse(time.RFC3339Nano, labeledAt.String)
			s.LabeledAt = &t
		}
		out = append(out, s)
	}
	return out, rows.Err()
}

func b2i(b bool) int {
	if b {
		return 1
	}
	return 0
}
