package sqlite

import (
	"context"
	"database/sql"
	"fmt"
	"strings"
	"time"

	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
)

// ProjectRepo stores tenant-local RLM project registry records in memory_bridge_v2.db.
type ProjectRepo struct {
	db *DB
}

func NewProjectRepo(db *DB) (*ProjectRepo, error) {
	repo := &ProjectRepo{db: db}
	if err := repo.migrate(); err != nil {
		return nil, fmt.Errorf("project repo migrate: %w", err)
	}
	return repo, nil
}

func (r *ProjectRepo) migrate() error {
	stmts := []string{
		`CREATE TABLE IF NOT EXISTS rlm_projects (
			tenant_id TEXT NOT NULL,
			project_id TEXT NOT NULL,
			name TEXT NOT NULL DEFAULT '',
			status TEXT NOT NULL DEFAULT 'active',
			created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
			updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
			archived_at TEXT,
			last_accessed_at TEXT,
			PRIMARY KEY (tenant_id, project_id)
		)`,
		`CREATE INDEX IF NOT EXISTS idx_rlm_projects_tenant_status ON rlm_projects(tenant_id, status)`,
	}
	for _, stmt := range stmts {
		if _, err := r.db.Exec(stmt); err != nil {
			return err
		}
	}
	_, _ = r.db.Exec(`ALTER TABLE rlm_projects ADD COLUMN status TEXT NOT NULL DEFAULT 'active'`)
	_, _ = r.db.Exec(`ALTER TABLE rlm_projects ADD COLUMN archived_at TEXT`)
	_, _ = r.db.Exec(`ALTER TABLE rlm_projects ADD COLUMN last_accessed_at TEXT`)
	return nil
}

func (r *ProjectRepo) Ensure(ctx context.Context, sc rlmscope.Scope, name string) (*rlmscope.Project, error) {
	sc = sc.Normalize()
	ctx = rlmscope.WithScope(ctx, sc)
	now := time.Now().UTC().Format(timeFormat)
	if strings.TrimSpace(name) == "" {
		name = sc.ProjectID
	}
	if _, err := r.db.Exec(`INSERT OR IGNORE INTO rlm_projects
		(tenant_id, project_id, name, status, created_at, updated_at, last_accessed_at)
		VALUES (?, ?, ?, ?, ?, ?, ?)`,
		sc.TenantID, sc.ProjectID, name, rlmscope.ProjectStatusActive, now, now, now); err != nil {
		return nil, fmt.Errorf("ensure project: %w", err)
	}
	if _, err := r.db.Exec(`UPDATE rlm_projects SET last_accessed_at = ?
		WHERE tenant_id = ? AND project_id = ?`, now, sc.TenantID, sc.ProjectID); err != nil {
		return nil, fmt.Errorf("touch project: %w", err)
	}
	return r.Get(ctx, sc.ProjectID)
}

func (r *ProjectRepo) Create(ctx context.Context, projectID, name string) (*rlmscope.Project, error) {
	sc := rlmscope.FromContext(ctx)
	projectID = strings.TrimSpace(projectID)
	if strings.TrimSpace(name) == "" {
		name = projectID
	}
	now := time.Now().UTC().Format(timeFormat)
	if _, err := r.db.Exec(`INSERT INTO rlm_projects
		(tenant_id, project_id, name, status, created_at, updated_at, archived_at, last_accessed_at)
		VALUES (?, ?, ?, ?, ?, ?, NULL, ?)
		ON CONFLICT(tenant_id, project_id) DO UPDATE SET
			name = excluded.name,
			status = 'active',
			archived_at = NULL,
			updated_at = excluded.updated_at,
			last_accessed_at = excluded.last_accessed_at`,
		sc.TenantID, projectID, name, rlmscope.ProjectStatusActive, now, now, now); err != nil {
		return nil, fmt.Errorf("create project: %w", err)
	}
	return r.Get(ctx, projectID)
}

func (r *ProjectRepo) Get(ctx context.Context, projectID string) (*rlmscope.Project, error) {
	sc := rlmscope.FromContext(ctx)
	projectID = strings.TrimSpace(projectID)
	if projectID == "" {
		projectID = sc.ProjectID
	}
	row := r.db.QueryRow(`SELECT tenant_id, project_id, name, status, created_at, updated_at,
			archived_at, last_accessed_at
		FROM rlm_projects
		WHERE tenant_id = ? AND project_id = ?`, sc.TenantID, projectID)
	project, err := scanProject(row)
	if err != nil {
		return nil, err
	}
	if err := r.attachStats(ctx, project); err != nil {
		return nil, err
	}
	return project, nil
}

func (r *ProjectRepo) List(ctx context.Context, includeArchived bool) ([]*rlmscope.Project, error) {
	sc := rlmscope.FromContext(ctx)
	query := `SELECT tenant_id, project_id, name, status, created_at, updated_at,
			archived_at, last_accessed_at
		FROM rlm_projects
		WHERE tenant_id = ?`
	args := []any{sc.TenantID}
	if !includeArchived {
		query += ` AND status != ?`
		args = append(args, rlmscope.ProjectStatusArchived)
	}
	query += ` ORDER BY updated_at DESC, project_id ASC`
	rows, err := r.db.Query(query, args...)
	if err != nil {
		return nil, fmt.Errorf("list projects: %w", err)
	}

	var projects []*rlmscope.Project
	for rows.Next() {
		project, err := scanProject(rows)
		if err != nil {
			return nil, err
		}
		projects = append(projects, project)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	if err := rows.Close(); err != nil {
		return nil, err
	}
	for _, project := range projects {
		if err := r.attachStats(ctx, project); err != nil {
			return nil, err
		}
	}
	return projects, nil
}

func (r *ProjectRepo) Archive(ctx context.Context, projectID string) (*rlmscope.Project, error) {
	return r.setStatus(ctx, projectID, rlmscope.ProjectStatusArchived)
}

func (r *ProjectRepo) Activate(ctx context.Context, projectID string) (*rlmscope.Project, error) {
	return r.setStatus(ctx, projectID, rlmscope.ProjectStatusActive)
}

func (r *ProjectRepo) Stats(ctx context.Context, projectID string) (*rlmscope.ProjectStats, error) {
	project, err := r.Get(ctx, projectID)
	if err != nil {
		return nil, err
	}
	return &rlmscope.ProjectStats{
		Project:        project,
		TotalFacts:     project.FactCount,
		GeneCount:      project.GeneCount,
		StaleCount:     project.StaleCount,
		ArchivedCount:  project.ArchivedCount,
		DomainCount:    project.DomainCount,
		WithEmbeddings: project.WithEmbeddings,
		LastFactAt:     project.LastFactAt,
	}, nil
}

func (r *ProjectRepo) setStatus(ctx context.Context, projectID, status string) (*rlmscope.Project, error) {
	sc := rlmscope.FromContext(ctx)
	projectID = strings.TrimSpace(projectID)
	if projectID == "" {
		return nil, fmt.Errorf("project_id is required")
	}
	now := time.Now().UTC().Format(timeFormat)
	var result sql.Result
	var err error
	if status == rlmscope.ProjectStatusArchived {
		result, err = r.db.Exec(`UPDATE rlm_projects
			SET status = ?, archived_at = ?, updated_at = ?
			WHERE tenant_id = ? AND project_id = ?`,
			status, now, now, sc.TenantID, projectID)
	} else {
		result, err = r.db.Exec(`UPDATE rlm_projects
			SET status = ?, archived_at = NULL, updated_at = ?
			WHERE tenant_id = ? AND project_id = ?`,
			status, now, sc.TenantID, projectID)
	}
	if err != nil {
		return nil, fmt.Errorf("set project status: %w", err)
	}
	n, _ := result.RowsAffected()
	if n == 0 {
		return nil, fmt.Errorf("project %s not found", projectID)
	}
	return r.Get(ctx, projectID)
}

func (r *ProjectRepo) attachStats(ctx context.Context, project *rlmscope.Project) error {
	if project == nil {
		return nil
	}
	var lastFact sql.NullString
	err := r.db.QueryRow(`SELECT
			COUNT(*),
			COALESCE(SUM(CASE WHEN source = 'genome' THEN 1 ELSE 0 END), 0),
			COALESCE(SUM(CASE WHEN is_stale = 1 THEN 1 ELSE 0 END), 0),
			COALESCE(SUM(CASE WHEN is_archived = 1 THEN 1 ELSE 0 END), 0),
			COUNT(DISTINCT CASE WHEN domain IS NOT NULL AND domain != '' THEN domain END),
			COALESCE(SUM(CASE WHEN embedding IS NOT NULL THEN 1 ELSE 0 END), 0),
			MAX(created_at)
		FROM hierarchical_facts
		WHERE tenant_id = ? AND project_id = ?
		  AND (session_id IS NULL OR session_id = '')`,
		project.TenantID, project.ProjectID,
	).Scan(&project.FactCount, &project.GeneCount, &project.StaleCount,
		&project.ArchivedCount, &project.DomainCount, &project.WithEmbeddings, &lastFact)
	if err != nil {
		return fmt.Errorf("project stats: %w", err)
	}
	project.LastFactAt = parseNullTime(lastFact)
	return nil
}

func scanProject(scanner interface {
	Scan(...any) error
}) (*rlmscope.Project, error) {
	var project rlmscope.Project
	var createdAt, updatedAt string
	var archivedAt, lastAccessedAt sql.NullString
	if err := scanner.Scan(&project.TenantID, &project.ProjectID, &project.Name, &project.Status,
		&createdAt, &updatedAt, &archivedAt, &lastAccessedAt); err != nil {
		if err == sql.ErrNoRows {
			return nil, fmt.Errorf("project not found")
		}
		return nil, fmt.Errorf("scan project: %w", err)
	}
	project.CreatedAt = parseTime(createdAt)
	project.UpdatedAt = parseTime(updatedAt)
	project.ArchivedAt = parseNullTime(archivedAt)
	project.LastAccessedAt = parseNullTime(lastAccessedAt)
	if project.Status == "" {
		project.Status = rlmscope.ProjectStatusActive
	}
	return &project, nil
}

func parseTime(value string) time.Time {
	for _, layout := range []string{timeFormat, time.RFC3339Nano, "2006-01-02 15:04:05"} {
		t, err := time.Parse(layout, value)
		if err == nil {
			return t
		}
	}
	return time.Time{}
}

func parseNullTime(value sql.NullString) *time.Time {
	if !value.Valid || strings.TrimSpace(value.String) == "" {
		return nil
	}
	t := parseTime(value.String)
	if t.IsZero() {
		return nil
	}
	return &t
}
