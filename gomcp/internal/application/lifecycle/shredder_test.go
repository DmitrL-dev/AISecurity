package lifecycle

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestShredSQLite(t *testing.T) {
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "test.db")

	// Create fake SQLite file with magic header.
	header := []byte("SQLite format 3\x00")
	data := make([]byte, 4096)
	copy(data, header)

	require.NoError(t, os.WriteFile(dbPath, data, 0644))

	// Verify magic exists.
	content, _ := os.ReadFile(dbPath)
	assert.Equal(t, "SQLite format 3", string(content[:15]))

	// Shred.
	err := ShredSQLite(dbPath)
	assert.NoError(t, err)

	// Verify magic is destroyed.
	content, _ = os.ReadFile(dbPath)
	assert.NotEqual(t, "SQLite format 3", string(content[:15]),
		"SQLite header should be shredded")
	assert.Len(t, content, 4096, "file size should not change")
}

func TestShredBoltDB(t *testing.T) {
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "cache.db")

	// Create fake BoltDB file.
	data := make([]byte, 8192) // 2 pages
	copy(data, []byte("BOLT\x00\x00"))
	require.NoError(t, os.WriteFile(dbPath, data, 0644))

	err := ShredBoltDB(dbPath)
	assert.NoError(t, err)

	content, _ := os.ReadFile(dbPath)
	assert.NotEqual(t, "BOLT", string(content[:4]),
		"BoltDB header should be shredded")
}

func TestShredAll(t *testing.T) {
	dir := t.TempDir()

	// Create directory structure.
	memDir := filepath.Join(dir, "memory")
	os.MkdirAll(memDir, 0755)

	// Create fake databases.
	os.WriteFile(filepath.Join(memDir, "memory_bridge_v2.db"),
		make([]byte, 4096), 0644)
	os.WriteFile(filepath.Join(dir, "cache.db"),
		make([]byte, 8192), 0644)

	errs := ShredAll(dir)
	assert.Empty(t, errs, "should shred without errors")
}

func TestShred_NonexistentFile(t *testing.T) {
	err := ShredSQLite("/nonexistent/path/db.sqlite")
	assert.Error(t, err, "should error on nonexistent file")
}
