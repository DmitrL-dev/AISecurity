package postgres

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"time"

	"github.com/syntrex/gomcp/internal/domain/orchestrator"
)

// OrchestratorRepo provides PostgreSQL persistence for the data-capture flywheel
// (per-scan training samples). Implements domain/orchestrator.Repository. Tables
// are created via goose migrations (migrations/006_create_orchestrator_samples.sql),
// not inline DDL — mirrors pg SOCRepo.
type OrchestratorRepo struct {
	db *DB
}

// NewOrchestratorRepo creates a PostgreSQL-backed orchestrator-sample repository.
func NewOrchestratorRepo(db *DB) *OrchestratorRepo {
	return &OrchestratorRepo{db: db}
}

// Insert persists one captured sample.
func (r *OrchestratorRepo) Insert(s orchestrator.Sample) error {
	vecJSON, _ := json.Marshal(s.EngineVector)
	scoresJSON, _ := json.Marshal(s.EngineScores)
	aggJSON, _ := json.Marshal(s.Aggregate)
	var labeledAt *time.Time
	if s.LabeledAt != nil && !s.LabeledAt.IsZero() {
		labeledAt = s.LabeledAt
	}
	_, err := r.db.Pool().Exec(
		`INSERT INTO orchestrator_samples
		 (id, tenant_id, timestamp, prompt_hash, engine_vector, engine_scores, aggregate,
		  vector_complete, vector_schema, blocked, risk, threat_type, model_version,
		  label, label_source, labeled_at)
		 VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)`,
		s.ID, s.TenantID, s.Timestamp, s.PromptHash,
		string(vecJSON), string(scoresJSON), string(aggJSON),
		s.VectorComplete, s.VectorSchema, s.Blocked, s.Risk, s.ThreatType,
		s.ModelVersion, string(s.Label), s.LabelSource, labeledAt,
	)
	return err
}

// AttachLabel writes the label onto every UNLABELED sample for the tenant in
// [from, to]. Only empty-label rows are touched.
func (r *OrchestratorRepo) AttachLabel(tenantID string, from, to time.Time, label orchestrator.Label, source string) (int64, error) {
	if tenantID == "" {
		return 0, fmt.Errorf("attach label: empty tenant_id refused")
	}
	if !orchestrator.ValidLabel(label) {
		return 0, fmt.Errorf("attach label: invalid label %q", label)
	}
	now := time.Now()
	res, err := r.db.Pool().Exec(
		`UPDATE orchestrator_samples
		 SET label = $1, label_source = $2, labeled_at = $3
		 WHERE tenant_id = $4 AND label = '' AND timestamp >= $5 AND timestamp <= $6`,
		string(label), source, now, tenantID, from, to,
	)
	if err != nil {
		return 0, err
	}
	return res.RowsAffected()
}

// ExportLabeled returns the tenant's samples (newest first).
func (r *OrchestratorRepo) ExportLabeled(tenantID string, limit int, onlyLabeled bool) ([]orchestrator.Sample, error) {
	if tenantID == "" {
		return nil, fmt.Errorf("export: empty tenant_id refused")
	}
	if limit <= 0 {
		limit = 10000
	}
	const cols = `id, tenant_id, timestamp, prompt_hash, engine_vector, engine_scores, aggregate,
		 vector_complete, vector_schema, blocked, risk, threat_type, model_version,
		 label, label_source, labeled_at`
	var rows *sql.Rows
	var err error
	if onlyLabeled {
		rows, err = r.db.Pool().Query(
			`SELECT `+cols+` FROM orchestrator_samples
			 WHERE tenant_id = $1 AND label != '' ORDER BY timestamp DESC LIMIT $2`, tenantID, limit)
	} else {
		rows, err = r.db.Pool().Query(
			`SELECT `+cols+` FROM orchestrator_samples
			 WHERE tenant_id = $1 ORDER BY timestamp DESC LIMIT $2`, tenantID, limit)
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
	if err := r.db.Pool().QueryRow(
		"SELECT COUNT(*) FROM orchestrator_samples WHERE tenant_id = $1", tenantID,
	).Scan(&total); err != nil {
		return 0, 0, err
	}
	if err := r.db.Pool().QueryRow(
		"SELECT COUNT(*) FROM orchestrator_samples WHERE tenant_id = $1 AND label != ''", tenantID,
	).Scan(&labeled); err != nil {
		return 0, 0, err
	}
	return total, labeled, nil
}

// PurgeExpired deletes samples older than retentionDays.
func (r *OrchestratorRepo) PurgeExpired(retentionDays int) (int64, error) {
	cutoff := time.Now().AddDate(0, 0, -retentionDays)
	res, err := r.db.Pool().Exec("DELETE FROM orchestrator_samples WHERE timestamp < $1", cutoff)
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
	res, err := r.db.Pool().Exec("DELETE FROM orchestrator_samples WHERE tenant_id = $1", tenantID)
	if err != nil {
		return 0, fmt.Errorf("delete orchestrator samples by tenant: %w", err)
	}
	return res.RowsAffected()
}

func scanSamples(rows *sql.Rows) ([]orchestrator.Sample, error) {
	var out []orchestrator.Sample
	for rows.Next() {
		var s orchestrator.Sample
		var vecJSON, scoresJSON, aggJSON []byte
		var labeledAt sql.NullTime
		var label string
		if err := rows.Scan(&s.ID, &s.TenantID, &s.Timestamp, &s.PromptHash,
			&vecJSON, &scoresJSON, &aggJSON,
			&s.VectorComplete, &s.VectorSchema, &s.Blocked, &s.Risk, &s.ThreatType, &s.ModelVersion,
			&label, &s.LabelSource, &labeledAt); err != nil {
			return nil, err
		}
		s.Label = orchestrator.Label(label)
		if len(vecJSON) > 0 {
			json.Unmarshal(vecJSON, &s.EngineVector)
		}
		if len(scoresJSON) > 0 {
			json.Unmarshal(scoresJSON, &s.EngineScores)
		}
		if len(aggJSON) > 0 {
			json.Unmarshal(aggJSON, &s.Aggregate)
		}
		if labeledAt.Valid {
			t := labeledAt.Time
			s.LabeledAt = &t
		}
		out = append(out, s)
	}
	return out, rows.Err()
}
