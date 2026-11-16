package shadow_ai

import (
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestLoadIntegrationConfig_MissingFileIsHonestEmpty(t *testing.T) {
	cfg, err := LoadIntegrationConfig(filepath.Join(t.TempDir(), "does-not-exist.yaml"))
	if err != nil {
		t.Fatalf("missing file must NOT error, got: %v", err)
	}
	if cfg == nil {
		t.Fatal("expected a default config, got nil")
	}
	if len(cfg.Plugins) != 0 {
		t.Errorf("expected zero plugins (honest-empty), got %d", len(cfg.Plugins))
	}
	if cfg.FallbackStrategy != "detect_only" {
		t.Errorf("expected detect_only default, got %q", cfg.FallbackStrategy)
	}
	if cfg.HealthCheckInterval != 30*time.Second {
		t.Errorf("expected 30s default interval, got %v", cfg.HealthCheckInterval)
	}
}

func TestLoadIntegrationConfig_EnvExpansionAndParse(t *testing.T) {
	t.Setenv("TEST_CP_KEY", "secret-from-env")

	yaml := `
fallback_strategy: detect_only
health_check_interval: 45s
plugins:
  - type: firewall
    vendor: checkpoint
    enabled: true
    config:
      api_url: https://mgmt.example.com
      api_key: ${TEST_CP_KEY}
  - type: edr
    vendor: crowdstrike
    enabled: false
    config:
      client_id: ${TEST_MISSING_VAR}
`
	path := filepath.Join(t.TempDir(), "plugins.yaml")
	if err := os.WriteFile(path, []byte(yaml), 0o600); err != nil {
		t.Fatalf("write: %v", err)
	}

	cfg, err := LoadIntegrationConfig(path)
	if err != nil {
		t.Fatalf("load: %v", err)
	}
	if cfg.HealthCheckInterval != 45*time.Second {
		t.Errorf("expected 45s, got %v", cfg.HealthCheckInterval)
	}
	if len(cfg.Plugins) != 2 {
		t.Fatalf("expected 2 plugin entries, got %d", len(cfg.Plugins))
	}

	// ${TEST_CP_KEY} must be expanded from the environment.
	if got := cfg.Plugins[0].Config["api_key"]; got != "secret-from-env" {
		t.Errorf("expected expanded api_key, got %v", got)
	}
	// An unset var expands to "" (honest-empty creds → plugin would be rejected).
	// YAML parses an empty scalar as nil; cfgString normalizes both nil and ""
	// to "" — that normalized empty value is the contract the loader guarantees.
	if got := cfgString(cfg.Plugins[1].Config, "client_id"); got != "" {
		t.Errorf("expected empty client_id for unset var, got %q", got)
	}
}

// TestLoadIntegrationConfig_EmptyConfigYieldsNoEnforcement proves the loader +
// registry produce ZERO enforcement plugins for the honest-empty default, so a
// freshly-wired controller runs in detect_only with no fabricated enforcement.
func TestLoadIntegrationConfig_EmptyConfigYieldsNoEnforcement(t *testing.T) {
	cfg, err := LoadIntegrationConfig(filepath.Join(t.TempDir(), "absent.yaml"))
	if err != nil {
		t.Fatalf("load: %v", err)
	}
	ctrl := NewShadowAIController()
	if err := ctrl.Configure(cfg); err != nil {
		t.Fatalf("configure: %v", err)
	}
	if n := ctrl.Registry().PluginCount(); n != 0 {
		t.Fatalf("expected 0 enforcement plugins (detect_only), got %d", n)
	}
}
