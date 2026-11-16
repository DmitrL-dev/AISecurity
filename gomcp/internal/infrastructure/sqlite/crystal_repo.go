package sqlite

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"path/filepath"
	"strings"

	"github.com/syntrex/gomcp/internal/domain/crystal"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
)

// CrystalRepo implements crystal.CrystalStore using SQLite.
// Compatible with crystals.db schema.
type CrystalRepo struct {
	db *DB
}

// NewCrystalRepo creates a CrystalRepo and ensures the schema exists.
func NewCrystalRepo(db *DB) (*CrystalRepo, error) {
	repo := &CrystalRepo{db: db}
	if err := repo.migrate(); err != nil {
		return nil, fmt.Errorf("crystal repo migrate: %w", err)
	}
	return repo, nil
}

func (r *CrystalRepo) migrate() error {
	stmts := []string{
		`CREATE TABLE IF NOT EXISTS crystals (
			tenant_id TEXT NOT NULL DEFAULT 'local',
			project_id TEXT NOT NULL DEFAULT 'default',
			path TEXT NOT NULL,
			name TEXT,
			content BLOB,
			primitives_count INTEGER,
			token_count INTEGER,
			indexed_at REAL,
			source_mtime REAL,
			source_hash TEXT,
			last_validated REAL,
			human_confirmed INTEGER DEFAULT 0,
			PRIMARY KEY (tenant_id, project_id, path)
		)`,
		`CREATE TABLE IF NOT EXISTS metadata (
			key TEXT PRIMARY KEY,
			value TEXT
		)`,
		`CREATE INDEX IF NOT EXISTS idx_crystals_scope_path ON crystals(tenant_id, project_id, path)`,
		`CREATE INDEX IF NOT EXISTS idx_crystals_scope_indexed ON crystals(tenant_id, project_id, indexed_at)`,
		`CREATE INDEX IF NOT EXISTS idx_mtime ON crystals(source_mtime)`,
		`CREATE INDEX IF NOT EXISTS idx_indexed ON crystals(indexed_at)`,
	}
	for _, s := range stmts {
		if _, err := r.db.Exec(s); err != nil {
			return fmt.Errorf("exec migration: %w", err)
		}
	}
	_, _ = r.db.Exec(`ALTER TABLE crystals ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'local'`)
	_, _ = r.db.Exec(`ALTER TABLE crystals ADD COLUMN project_id TEXT NOT NULL DEFAULT 'default'`)
	if err := r.migrateScopeKey(); err != nil {
		return err
	}
	return nil
}

func (r *CrystalRepo) migrateScopeKey() error {
	var tableSQL string
	if err := r.db.QueryRow(`SELECT sql FROM sqlite_master WHERE type='table' AND name='crystals'`).Scan(&tableSQL); err != nil {
		return nil
	}
	if strings.Contains(tableSQL, "PRIMARY KEY (tenant_id, project_id, path)") {
		return nil
	}
	stmts := []string{
		`CREATE TABLE IF NOT EXISTS crystals_scoped (
			tenant_id TEXT NOT NULL DEFAULT 'local',
			project_id TEXT NOT NULL DEFAULT 'default',
			path TEXT NOT NULL,
			name TEXT,
			content BLOB,
			primitives_count INTEGER,
			token_count INTEGER,
			indexed_at REAL,
			source_mtime REAL,
			source_hash TEXT,
			last_validated REAL,
			human_confirmed INTEGER DEFAULT 0,
			PRIMARY KEY (tenant_id, project_id, path)
		)`,
		`INSERT OR IGNORE INTO crystals_scoped
			(tenant_id, project_id, path, name, content, primitives_count, token_count,
			 indexed_at, source_mtime, source_hash, last_validated, human_confirmed)
			SELECT COALESCE(tenant_id, 'local'), COALESCE(project_id, 'default'),
			       path, name, content, primitives_count, token_count,
			       indexed_at, source_mtime, source_hash, last_validated, human_confirmed
			FROM crystals`,
		`DROP TABLE crystals`,
		`ALTER TABLE crystals_scoped RENAME TO crystals`,
		`CREATE INDEX IF NOT EXISTS idx_crystals_scope_path ON crystals(tenant_id, project_id, path)`,
		`CREATE INDEX IF NOT EXISTS idx_crystals_scope_indexed ON crystals(tenant_id, project_id, indexed_at)`,
		`CREATE INDEX IF NOT EXISTS idx_mtime ON crystals(source_mtime)`,
		`CREATE INDEX IF NOT EXISTS idx_indexed ON crystals(indexed_at)`,
	}
	for _, stmt := range stmts {
		if _, err := r.db.Exec(stmt); err != nil {
			return fmt.Errorf("migrate crystals scope key: %w", err)
		}
	}
	return nil
}

// serializedCrystal is the JSON structure stored in the content BLOB.
type serializedCrystal struct {
	Path        string              `json:"path"`
	Name        string              `json:"name"`
	TokenCount  int                 `json:"token_count"`
	ContentHash string              `json:"content_hash"`
	Primitives  []crystal.Primitive `json:"primitives"`
}

// Upsert inserts or replaces a crystal.
func (r *CrystalRepo) Upsert(ctx context.Context, c *crystal.Crystal) error {
	rlmScope := rlmscope.FromContext(ctx)
	c.TenantID = rlmScope.TenantID
	c.ProjectID = rlmScope.ProjectID
	stored := serializedCrystal{
		Path:        c.Path,
		Name:        c.Name,
		TokenCount:  c.TokenCount,
		ContentHash: c.ContentHash,
		Primitives:  c.Primitives,
	}
	blob, err := json.Marshal(stored)
	if err != nil {
		return fmt.Errorf("marshal crystal: %w", err)
	}

	_, err = r.db.Exec(`INSERT OR REPLACE INTO crystals
		(tenant_id, project_id, path, name, content, primitives_count, token_count,
		 indexed_at, source_mtime, source_hash, last_validated, human_confirmed)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		c.TenantID, c.ProjectID, c.Path, c.Name, blob, c.PrimitivesCount, c.TokenCount,
		c.IndexedAt, c.SourceMtime, c.SourceHash,
		c.LastValidated, boolToInt(c.HumanConfirmed),
	)
	if err != nil {
		return fmt.Errorf("upsert crystal: %w", err)
	}
	return nil
}

// Get retrieves a crystal by path.
func (r *CrystalRepo) Get(ctx context.Context, path string) (*crystal.Crystal, error) {
	sc := rlmscope.FromContext(ctx)
	row := r.db.QueryRow(`SELECT tenant_id, project_id, path, name, content, primitives_count, token_count,
		indexed_at, source_mtime, source_hash, last_validated, human_confirmed
		FROM crystals WHERE tenant_id = ? AND project_id = ? AND path = ?`,
		sc.TenantID, sc.ProjectID, path)

	var c crystal.Crystal
	var blob []byte
	var lastValidated sql.NullFloat64
	var humanConfirmed int

	err := row.Scan(&c.TenantID, &c.ProjectID, &c.Path, &c.Name, &blob, &c.PrimitivesCount, &c.TokenCount,
		&c.IndexedAt, &c.SourceMtime, &c.SourceHash, &lastValidated, &humanConfirmed)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, fmt.Errorf("crystal %s not found", path)
		}
		return nil, fmt.Errorf("scan crystal: %w", err)
	}

	if lastValidated.Valid {
		c.LastValidated = lastValidated.Float64
	}
	c.HumanConfirmed = humanConfirmed != 0

	if len(blob) > 0 {
		var sc serializedCrystal
		if err := json.Unmarshal(blob, &sc); err != nil {
			return nil, fmt.Errorf("unmarshal crystal content: %w", err)
		}
		c.Primitives = sc.Primitives
		c.ContentHash = sc.ContentHash
	}

	return &c, nil
}

// Delete removes a crystal by path.
func (r *CrystalRepo) Delete(ctx context.Context, path string) error {
	sc := rlmscope.FromContext(ctx)
	result, err := r.db.Exec(`DELETE FROM crystals
		WHERE tenant_id = ? AND project_id = ? AND path = ?`,
		sc.TenantID, sc.ProjectID, path)
	if err != nil {
		return fmt.Errorf("delete crystal: %w", err)
	}
	n, _ := result.RowsAffected()
	if n == 0 {
		return fmt.Errorf("crystal %s not found", path)
	}
	return nil
}

// List returns crystals matching a path pattern. Empty pattern returns all.
func (r *CrystalRepo) List(ctx context.Context, pattern string, limit int) ([]*crystal.Crystal, error) {
	if limit <= 0 {
		limit = 100
	}

	sc := rlmscope.FromContext(ctx)
	var rows *sql.Rows
	var err error
	if pattern == "" {
		rows, err = r.db.Query(`SELECT tenant_id, project_id, path, name, content, primitives_count, token_count,
			indexed_at, source_mtime, source_hash, last_validated, human_confirmed
			FROM crystals WHERE tenant_id = ? AND project_id = ?
			ORDER BY indexed_at DESC LIMIT ?`, sc.TenantID, sc.ProjectID, limit)
	} else {
		rows, err = r.db.Query(`SELECT tenant_id, project_id, path, name, content, primitives_count, token_count,
			indexed_at, source_mtime, source_hash, last_validated, human_confirmed
			FROM crystals WHERE tenant_id = ? AND project_id = ? AND path LIKE ?
			ORDER BY indexed_at DESC LIMIT ?`, sc.TenantID, sc.ProjectID, pattern, limit)
	}
	if err != nil {
		return nil, fmt.Errorf("list crystals: %w", err)
	}
	defer rows.Close()
	return scanCrystals(rows)
}

// Search searches crystal primitives by name/value containing query.
func (r *CrystalRepo) Search(ctx context.Context, query string, limit int) ([]*crystal.Crystal, error) {
	if limit <= 0 {
		limit = 50
	}

	sc := rlmscope.FromContext(ctx)
	// Search in content BLOB (JSON text stored as BLOB) for primitive names/values.
	// CAST to TEXT required because SQLite LIKE doesn't match on raw BLOB.
	rows, err := r.db.Query(`SELECT tenant_id, project_id, path, name, content, primitives_count, token_count,
		indexed_at, source_mtime, source_hash, last_validated, human_confirmed
		FROM crystals
		WHERE tenant_id = ? AND project_id = ? AND (CAST(content AS TEXT) LIKE ? OR name LIKE ?)
		LIMIT ?`,
		sc.TenantID, sc.ProjectID, "%"+query+"%", "%"+query+"%", limit)
	if err != nil {
		return nil, fmt.Errorf("search crystals: %w", err)
	}
	defer rows.Close()
	return scanCrystals(rows)
}

// Stats returns aggregate statistics.
func (r *CrystalRepo) Stats(ctx context.Context) (*crystal.CrystalStats, error) {
	sc := rlmscope.FromContext(ctx)
	stats := &crystal.CrystalStats{
		ByExtension: make(map[string]int),
	}

	row := r.db.QueryRow(`SELECT COUNT(*), COALESCE(SUM(primitives_count),0), COALESCE(SUM(token_count),0)
		FROM crystals WHERE tenant_id = ? AND project_id = ?`, sc.TenantID, sc.ProjectID)
	if err := row.Scan(&stats.TotalCrystals, &stats.TotalPrimitives, &stats.TotalTokens); err != nil {
		return nil, err
	}

	// Count by file extension.
	rows, err := r.db.Query(`SELECT path FROM crystals WHERE tenant_id = ? AND project_id = ?`,
		sc.TenantID, sc.ProjectID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	for rows.Next() {
		var p string
		if err := rows.Scan(&p); err != nil {
			return nil, err
		}
		ext := strings.ToLower(filepath.Ext(p))
		if ext == "" {
			ext = "(no ext)"
		}
		stats.ByExtension[ext]++
	}
	return stats, rows.Err()
}

func scanCrystals(rows *sql.Rows) ([]*crystal.Crystal, error) {
	var result []*crystal.Crystal
	for rows.Next() {
		var c crystal.Crystal
		var blob []byte
		var lastValidated sql.NullFloat64
		var humanConfirmed int

		err := rows.Scan(&c.TenantID, &c.ProjectID, &c.Path, &c.Name, &blob, &c.PrimitivesCount, &c.TokenCount,
			&c.IndexedAt, &c.SourceMtime, &c.SourceHash, &lastValidated, &humanConfirmed)
		if err != nil {
			return nil, fmt.Errorf("scan crystal row: %w", err)
		}

		if lastValidated.Valid {
			c.LastValidated = lastValidated.Float64
		}
		c.HumanConfirmed = humanConfirmed != 0

		if len(blob) > 0 {
			var sc serializedCrystal
			if err := json.Unmarshal(blob, &sc); err != nil {
				return nil, fmt.Errorf("unmarshal crystal content: %w", err)
			}
			c.Primitives = sc.Primitives
			c.ContentHash = sc.ContentHash
		}

		result = append(result, &c)
	}
	return result, rows.Err()
}

// Ensure CrystalRepo implements crystal.CrystalStore.
var _ crystal.CrystalStore = (*CrystalRepo)(nil)
