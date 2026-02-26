package contextengine

import (
	"os"
	"path/filepath"
	"testing"

	ctxdomain "github.com/sentinel-community/gomcp/internal/domain/context"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestLoadConfig_FileNotExists(t *testing.T) {
	cfg, err := LoadConfig("/nonexistent/path/context.json")
	require.NoError(t, err)
	assert.Equal(t, ctxdomain.DefaultTokenBudget, cfg.TokenBudget)
	assert.True(t, cfg.Enabled)
	assert.NotEmpty(t, cfg.SkipTools)
}

func TestLoadConfig_ValidFile(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "context.json")

	content := `{
		"token_budget": 500,
		"max_facts": 15,
		"recency_weight": 0.3,
		"frequency_weight": 0.2,
		"level_weight": 0.25,
		"keyword_weight": 0.25,
		"decay_half_life_hours": 48,
		"enabled": true,
		"skip_tools": ["health", "version"]
	}`
	err := os.WriteFile(path, []byte(content), 0o644)
	require.NoError(t, err)

	cfg, err := LoadConfig(path)
	require.NoError(t, err)
	assert.Equal(t, 500, cfg.TokenBudget)
	assert.Equal(t, 15, cfg.MaxFacts)
	assert.Equal(t, 0.3, cfg.RecencyWeight)
	assert.Equal(t, 48.0, cfg.DecayHalfLifeHours)
	assert.True(t, cfg.Enabled)
	assert.Len(t, cfg.SkipTools, 2)
	assert.True(t, cfg.ShouldSkip("health"))
	assert.True(t, cfg.ShouldSkip("version"))
	assert.False(t, cfg.ShouldSkip("search_facts"))
}

func TestLoadConfig_InvalidJSON(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "context.json")

	err := os.WriteFile(path, []byte("{invalid json"), 0o644)
	require.NoError(t, err)

	_, err = LoadConfig(path)
	assert.Error(t, err)
}

func TestLoadConfig_InvalidConfig(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "context.json")

	content := `{"token_budget": 0, "max_facts": 5, "recency_weight": 0.5, "frequency_weight": 0.5, "level_weight": 0, "keyword_weight": 0, "decay_half_life_hours": 24, "enabled": true}`
	err := os.WriteFile(path, []byte(content), 0o644)
	require.NoError(t, err)

	_, err = LoadConfig(path)
	assert.Error(t, err, "should fail validation: token_budget=0")
}

func TestLoadConfig_OmittedSkipTools_UsesDefaults(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "context.json")

	content := `{
		"token_budget": 300,
		"max_facts": 10,
		"recency_weight": 0.25,
		"frequency_weight": 0.15,
		"level_weight": 0.30,
		"keyword_weight": 0.30,
		"decay_half_life_hours": 72,
		"enabled": true
	}`
	err := os.WriteFile(path, []byte(content), 0o644)
	require.NoError(t, err)

	cfg, err := LoadConfig(path)
	require.NoError(t, err)
	assert.NotEmpty(t, cfg.SkipTools, "omitted skip_tools should use defaults")
	assert.True(t, cfg.ShouldSkip("search_facts"))
}

func TestSaveDefaultConfig(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "context.json")

	err := SaveDefaultConfig(path)
	require.NoError(t, err)

	// Verify we can load what we saved
	cfg, err := LoadConfig(path)
	require.NoError(t, err)
	assert.Equal(t, ctxdomain.DefaultTokenBudget, cfg.TokenBudget)
	assert.True(t, cfg.Enabled)
}
