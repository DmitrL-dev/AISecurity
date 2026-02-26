// Package sqlite provides SQLite-based persistence using modernc.org/sqlite (pure Go, no CGO).
package sqlite

import (
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
	"sync"

	_ "modernc.org/sqlite"
)

// DB wraps a *sql.DB with SQLite-specific configuration.
type DB struct {
	db   *sql.DB
	path string
	mu   sync.RWMutex
}

// Open opens or creates an SQLite database at the given path.
// It applies WAL mode and recommended pragmas for performance.
func Open(path string) (*DB, error) {
	dir := filepath.Dir(path)
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return nil, fmt.Errorf("create db directory: %w", err)
	}

	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, fmt.Errorf("open sqlite: %w", err)
	}

	// Apply performance pragmas.
	pragmas := []string{
		"PRAGMA journal_mode=WAL",
		"PRAGMA synchronous=NORMAL",
		"PRAGMA cache_size=-64000", // 64MB
		"PRAGMA foreign_keys=ON",
		"PRAGMA busy_timeout=5000",
	}
	for _, p := range pragmas {
		if _, err := db.Exec(p); err != nil {
			db.Close()
			return nil, fmt.Errorf("exec pragma %q: %w", p, err)
		}
	}

	// Connection pool settings for SQLite (single writer).
	db.SetMaxOpenConns(1)
	db.SetMaxIdleConns(1)

	return &DB{db: db, path: path}, nil
}

// OpenMemory opens an in-memory SQLite database (for testing).
func OpenMemory() (*DB, error) {
	db, err := sql.Open("sqlite", ":memory:")
	if err != nil {
		return nil, fmt.Errorf("open in-memory sqlite: %w", err)
	}

	if _, err := db.Exec("PRAGMA foreign_keys=ON"); err != nil {
		db.Close()
		return nil, fmt.Errorf("enable foreign keys: %w", err)
	}

	return &DB{db: db, path: ":memory:"}, nil
}

// SqlDB returns the underlying *sql.DB.
func (d *DB) SqlDB() *sql.DB {
	return d.db
}

// Path returns the database file path.
func (d *DB) Path() string {
	return d.path
}

// Close closes the database connection.
func (d *DB) Close() error {
	return d.db.Close()
}

// Exec executes a query that doesn't return rows.
func (d *DB) Exec(query string, args ...any) (sql.Result, error) {
	d.mu.Lock()
	defer d.mu.Unlock()
	return d.db.Exec(query, args...)
}

// Query executes a query that returns rows.
func (d *DB) Query(query string, args ...any) (*sql.Rows, error) {
	d.mu.RLock()
	defer d.mu.RUnlock()
	return d.db.Query(query, args...)
}

// QueryRow executes a query that returns at most one row.
func (d *DB) QueryRow(query string, args ...any) *sql.Row {
	d.mu.RLock()
	defer d.mu.RUnlock()
	return d.db.QueryRow(query, args...)
}
