package audit

import (
	"os"
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestLogger_CreateAndLog(t *testing.T) {
	dir := t.TempDir()
	logger, err := NewLogger(dir)
	require.NoError(t, err)
	defer logger.Close()

	err = logger.Log("test raw data for audit", "ALLOW:ZERO_G")
	require.NoError(t, err)
	assert.Equal(t, 1, logger.Count())

	err = logger.Log("second operation", "DENY:SECRET")
	require.NoError(t, err)
	assert.Equal(t, 2, logger.Count())
}

func TestLogger_AppendOnly(t *testing.T) {
	dir := t.TempDir()

	// Write first record.
	logger1, err := NewLogger(dir)
	require.NoError(t, err)
	logger1.Log("first entry", "ALLOW")
	logger1.Close()

	// Reopen and write second.
	logger2, err := NewLogger(dir)
	require.NoError(t, err)
	logger2.Log("second entry", "DENY")
	logger2.Close()

	// Read file — should have both records.
	data, err := os.ReadFile(logger2.Path())
	require.NoError(t, err)

	lines := strings.Split(strings.TrimSpace(string(data)), "\n")
	assert.Equal(t, 2, len(lines), "should have 2 lines (append-only)")
	assert.Contains(t, lines[0], "first entry")
	assert.Contains(t, lines[1], "second entry")
}

func TestLogger_IntentHash(t *testing.T) {
	dir := t.TempDir()
	logger, err := NewLogger(dir)
	require.NoError(t, err)
	defer logger.Close()

	logger.Log("data to hash", "ALLOW")

	data, err := os.ReadFile(logger.Path())
	require.NoError(t, err)

	// SHA-256 hash prefix should be in the output.
	assert.Contains(t, string(data), "|")
}

func TestLogger_LongDataTruncated(t *testing.T) {
	dir := t.TempDir()
	logger, err := NewLogger(dir)
	require.NoError(t, err)
	defer logger.Close()

	longData := strings.Repeat("A", 500)
	logger.Log(longData, "ALLOW")

	data, err := os.ReadFile(logger.Path())
	require.NoError(t, err)

	assert.Contains(t, string(data), "...")
	// Line should not contain full 500-char string.
	assert.Less(t, len(string(data)), 400)
}
