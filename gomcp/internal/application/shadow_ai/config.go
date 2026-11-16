package shadow_ai

import (
	"fmt"
	"log/slog"
	"os"
	"time"

	yaml "gopkg.in/yaml.v3"
)

// DefaultConfigPath is the conventional on-disk location of the plugin config.
const DefaultConfigPath = "deploy/policies/shadow_ai_plugins.yaml"

// LoadIntegrationConfig reads the Shadow-AI plugin configuration from a YAML file.
//
// Security: secrets MUST NOT be written into the YAML. Instead, config values may
// reference environment variables with ${ENV_VAR} (or $ENV_VAR) syntax, which are
// expanded from the process environment before parsing. An unset variable expands
// to the empty string, which leaves the corresponding plugin un-credentialed —
// LoadPlugins/Initialize then reject it (e.g. "api_url required"), so it stays in
// honest detect_only mode rather than silently "enforcing".
//
// Honest-empty default: a missing file is NOT an error. It returns a zero-plugin
// detect_only config so the subsystem boots empty (no enforcement, no fake data)
// until an operator provides creds. Any other read/parse error IS returned.
func LoadIntegrationConfig(path string) (*IntegrationConfig, error) {
	if path == "" {
		path = DefaultConfigPath
	}

	raw, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			slog.Info("shadow-ai: plugin config not found, running detect_only (no enforcement)",
				"path", path)
			return defaultIntegrationConfig(), nil
		}
		return nil, fmt.Errorf("shadow-ai: read config %q: %w", path, err)
	}

	// Expand ${ENV_VAR}/$ENV_VAR references so secrets live in the environment,
	// not in the file. os.Expand leaves unknown vars as "" (honest-empty creds).
	expanded := os.Expand(string(raw), os.Getenv)

	var cfg IntegrationConfig
	if err := yaml.Unmarshal([]byte(expanded), &cfg); err != nil {
		return nil, fmt.Errorf("shadow-ai: parse config %q: %w", path, err)
	}

	if cfg.FallbackStrategy == "" {
		cfg.FallbackStrategy = "detect_only"
	}
	if cfg.HealthCheckInterval <= 0 {
		cfg.HealthCheckInterval = 30 * time.Second
	}

	return &cfg, nil
}

// defaultIntegrationConfig returns the honest-empty baseline: zero plugins,
// detect_only fallback, 30s health-check interval.
func defaultIntegrationConfig() *IntegrationConfig {
	return &IntegrationConfig{
		Plugins:             nil,
		FallbackStrategy:    "detect_only",
		HealthCheckInterval: 30 * time.Second,
	}
}
