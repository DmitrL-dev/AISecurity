package sqlite

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"path/filepath"
	"strings"

	"github.com/sentinel-community/gomcp/internal/domain/crystal"
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
			path TEXT PRIMARY KEY,
			name TEXT,
			content BLOB,
			primitives_count INTEGER,
			token_count INTEGER,
			indexed_at REAL,
			source_mtime REAL,
			source_hash TEXT,
			last_validated REAL,
			human_confirmed INTEGER DEFAULT 0
		)`,
		`CREATE TABLE IF NOT EXISTS metadata (
			key TEXT PRIMARY KEY,
			value TEXT
		)`,
		`CREATE INDEX IF NOT EXISTS idx_mtime ON crystals(source_mtime)`,
		`CREATE INDEX IF NOT EXISTS idx_indexed ON crystals(indexed_at)`,
	}
	for _, s := range stmts {
		if _, err := r.db.Exec(s); err != nil {
			return fmt.Errorf("exec migration: %w", err)
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
	sc := serializedCrystal{
		Path:        c.Path,
		Name:        c.Name,
		TokenCount:  c.TokenCount,
		ContentHash: c.ContentHash,
		Primitives:  c.Primitives,
	}
	blob, err := json.Marshal(sc)
	if err != nil {
		return fmt.Errorf("marshal crystal: %w", err)
	}

	_, err = r.db.Exec(`INSERT OR REPLACE INTO crystals
		(path, name, content, primitives_count, token_count,
		 indexed_at, source_mtime, source_hash, last_validated, human_confirmed)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		c.Path, c.Name, blob, c.PrimitivesCount, c.TokenCount,
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
	row := r.db.QueryRow(`SELECT path, name, content, primitives_count, token_count,
		indexed_at, source_mtime, source_hash, last_validated, human_confirmed
		FROM crystals WHERE path = ?`, path)

	var c crystal.Crystal
	var blob []byte
	var lastValidated sql.NullFloat64
	var humanConfirmed int

	err := row.Scan(&c.Path, &c.Name, &blob, &c.PrimitivesCount, &c.TokenCount,
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
	result, err := r.db.Exec(`DELETE FROM crystals WHERE path = ?`, path)
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

	var rows *sql.Rows
	var err error
	if pattern == "" {
		rows, err = r.db.Query(`SELECT path, name, content, primitives_count, token_count,
			indexed_at, source_mtime, source_hash, last_validated, human_confirmed
			FROM crystals ORDER BY indexed_at DESC LIMIT ?`, limit)
	} else {
		rows, err = r.db.Query(`SELECT path, name, content, primitives_count, token_count,
			indexed_at, source_mtime, source_hash, last_validated, human_confirmed
			FROM crystals WHERE path LIKE ? ORDER BY indexed_at DESC LIMIT ?`, pattern, limit)
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

	// Search in content BLOB (JSON text stored as BLOB) for primitive names/values.
	// CAST to TEXT required because SQLite LIKE doesn't match on raw BLOB.
	rows, err := r.db.Query(`SELECT path, name, content, primitives_count, token_count,
		indexed_at, source_mtime, source_hash, last_validated, human_confirmed
		FROM crystals WHERE CAST(content AS TEXT) LIKE ? OR name LIKE ? LIMIT ?`,
		"%"+query+"%", "%"+query+"%", limit)
	if err != nil {
		return nil, fmt.Errorf("search crystals: %w", err)
	}
	defer rows.Close()
	return scanCrystals(rows)
}

// Stats returns aggregate statistics.
func (r *CrystalRepo) Stats(ctx context.Context) (*crystal.CrystalStats, error) {
	stats := &crystal.CrystalStats{
		ByExtension: make(map[string]int),
	}

	row := r.db.QueryRow(`SELECT COUNT(*), COALESCE(SUM(primitives_count),0), COALESCE(SUM(token_count),0) FROM crystals`)
	if err := row.Scan(&stats.TotalCrystals, &stats.TotalPrimitives, &stats.TotalTokens); err != nil {
		return nil, err
	}

	// Count by file extension.
	rows, err := r.db.Query(`SELECT path FROM crystals`)
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

		err := rows.Scan(&c.Path, &c.Name, &blob, &c.PrimitivesCount, &c.TokenCount,
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
