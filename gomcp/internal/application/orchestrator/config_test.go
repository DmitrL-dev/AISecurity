package orchestrator

import (
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestLoadConfigFromFile_Defaults(t *testing.T) {
	// Non-existent file → defaults.
	cfg := LoadConfigFromFile("/nonexistent/config.json")
	assert.Equal(t, 5*time.Minute, cfg.HeartbeatInterval)
	assert.Equal(t, 30, cfg.JitterPercent)
	assert.InDelta(t, 0.8, cfg.EntropyThreshold, 0.001)
	assert.Equal(t, 100, cfg.MaxSyncBatchSize)
}

func TestLoadConfigFromFile_Custom(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "config.json")
	err := os.WriteFile(path, []byte(`{
		"heartbeat_interval_sec": 60,
		"jitter_percent": 10,
		"entropy_threshold": 0.5,
		"max_sync_batch_size": 50
	}`), 0o644)
	require.NoError(t, err)

	cfg := LoadConfigFromFile(path)
	assert.Equal(t, 60*time.Second, cfg.HeartbeatInterval)
	assert.Equal(t, 10, cfg.JitterPercent)
	assert.InDelta(t, 0.5, cfg.EntropyThreshold, 0.001)
	assert.Equal(t, 50, cfg.MaxSyncBatchSize)
}

func TestLoadConfigFromFile_InvalidJSON(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "bad.json")
	os.WriteFile(path, []byte(`{invalid}`), 0o644)

	cfg := LoadConfigFromFile(path)
	// Should return defaults on invalid JSON.
	assert.Equal(t, 5*time.Minute, cfg.HeartbeatInterval)
}

func TestWriteDefaultConfig(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "config.json")

	err := WriteDefaultConfig(path)
	require.NoError(t, err)

	cfg := LoadConfigFromFile(path)
	assert.Equal(t, 5*time.Minute, cfg.HeartbeatInterval)
	assert.Equal(t, 30, cfg.JitterPercent)
}

func TestLoadConfigFromFile_PartialOverride(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "partial.json")
	os.WriteFile(path, []byte(`{"heartbeat_interval_sec": 120}`), 0o644)

	cfg := LoadConfigFromFile(path)
	assert.Equal(t, 120*time.Second, cfg.HeartbeatInterval)
	// Other fields should be defaults.
	assert.Equal(t, 30, cfg.JitterPercent)
	assert.InDelta(t, 0.8, cfg.EntropyThreshold, 0.001)
}
