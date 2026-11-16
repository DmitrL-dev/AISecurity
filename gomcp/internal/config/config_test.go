package config

import (
	"os"
	"path/filepath"
	"testing"
)

func TestDefaultConfig(t *testing.T) {
	cfg := DefaultConfig()

	if cfg.Server.Port != 9100 {
		t.Fatalf("default port should be 9100, got %d", cfg.Server.Port)
	}
	if cfg.RBAC.Enabled {
		t.Fatal("RBAC should be disabled by default")
	}
	if cfg.Sovereign.Enabled {
		t.Fatal("Sovereign should be disabled by default")
	}
	if cfg.SOC.ClusterEnabled != true {
		t.Fatal("clustering should be enabled by default")
	}
	if cfg.Logging.Level != "info" {
		t.Fatalf("default log level should be info, got %s", cfg.Logging.Level)
	}
}

func TestConfig_Validate_InvalidPort(t *testing.T) {
	cfg := DefaultConfig()
	cfg.Server.Port = 0
	if err := cfg.Validate(); err == nil {
		t.Fatal("should reject port 0")
	}
	cfg.Server.Port = 99999
	if err := cfg.Validate(); err == nil {
		t.Fatal("should reject port 99999")
	}
}

func TestConfig_AirGapEnforcement(t *testing.T) {
	cfg := DefaultConfig()
	cfg.Sovereign.Enabled = true
	cfg.Sovereign.Mode = "airgap"

	if err := cfg.Validate(); err != nil {
		t.Fatalf("airgap config should validate: %v", err)
	}

	if !cfg.Sovereign.DisableExternalAPI {
		t.Fatal("airgap should force DisableExternalAPI=true")
	}
	if !cfg.Sovereign.DisableTelemetry {
		t.Fatal("airgap should force DisableTelemetry=true")
	}
	if !cfg.Sovereign.LocalModelsOnly {
		t.Fatal("airgap should force LocalModelsOnly=true")
	}
}

func TestConfig_Load_YAML(t *testing.T) {
	yaml := `
server:
  port: 9200
  rate_limit_per_min: 50
soc:
  data_dir: /var/syntrex
  cluster_enabled: true
rbac:
  enabled: true
  keys:
    - key: test-key-123
      role: admin
      name: CI Key
sovereign:
  enabled: true
  mode: restricted
  encrypt_at_rest: true
  data_retention_days: 30
p2p:
  enabled: true
  peers:
    - id: soc-2
      name: Site-B
      endpoint: http://soc-b:9100
      trust: full
logging:
  level: debug
  access_log: true
`
	dir := t.TempDir()
	path := filepath.Join(dir, "spectorn.yaml")
	os.WriteFile(path, []byte(yaml), 0644)

	cfg, err := Load(path)
	if err != nil {
		t.Fatalf("load failed: %v", err)
	}

	if cfg.Server.Port != 9200 {
		t.Fatalf("expected port 9200, got %d", cfg.Server.Port)
	}
	if cfg.Server.RateLimitPerMin != 50 {
		t.Fatalf("expected rate 50, got %d", cfg.Server.RateLimitPerMin)
	}
	if !cfg.RBAC.Enabled {
		t.Fatal("RBAC should be enabled")
	}
	if len(cfg.RBAC.Keys) != 1 || cfg.RBAC.Keys[0].Role != "admin" {
		t.Fatal("should have 1 admin key")
	}
	if !cfg.Sovereign.Enabled || cfg.Sovereign.Mode != "restricted" {
		t.Fatal("sovereign should be restricted")
	}
	if !cfg.Sovereign.EncryptAtRest {
		t.Fatal("encrypt_at_rest should be true")
	}
	if cfg.Sovereign.DataRetentionDays != 30 {
		t.Fatalf("retention should be 30, got %d", cfg.Sovereign.DataRetentionDays)
	}
	if len(cfg.P2P.Peers) != 1 || cfg.P2P.Peers[0].Trust != "full" {
		t.Fatal("should have 1 full-trust peer")
	}
	if cfg.Logging.Level != "debug" {
		t.Fatalf("expected debug, got %s", cfg.Logging.Level)
	}
}

func TestConfig_IsSovereign(t *testing.T) {
	cfg := DefaultConfig()
	if cfg.IsSovereign() {
		t.Fatal("default should not be sovereign")
	}
	cfg.Sovereign.Enabled = true
	if !cfg.IsSovereign() {
		t.Fatal("should be sovereign when enabled")
	}
}

func TestConfig_IsAirGapped(t *testing.T) {
	cfg := DefaultConfig()
	cfg.Sovereign.Enabled = true
	cfg.Sovereign.Mode = "restricted"
	if cfg.IsAirGapped() {
		t.Fatal("restricted is not air-gapped")
	}
	cfg.Sovereign.Mode = "airgap"
	cfg.Validate()
	if !cfg.IsAirGapped() {
		t.Fatal("should be air-gapped")
	}
}
