package config

import (
	"fmt"
	"os"
	"time"

	"gopkg.in/yaml.v3"
)

// Config is the root configuration loaded from spectorn.yaml (§19.3, §21).
type Config struct {
	Server     ServerConfig     `yaml:"server"`
	SOC        SOCConfig        `yaml:"soc"`
	RBAC       RBACConfig       `yaml:"rbac"`
	Webhooks   []WebhookConfig  `yaml:"webhooks"`
	ThreatIntel ThreatIntelConfig `yaml:"threat_intel"`
	Sovereign  SovereignConfig  `yaml:"sovereign"`
	P2P        P2PConfig        `yaml:"p2p"`
	Logging    LoggingConfig    `yaml:"logging"`
}

// ServerConfig defines HTTP server settings.
type ServerConfig struct {
	Port              int           `yaml:"port"`
	ReadTimeout       time.Duration `yaml:"read_timeout"`
	WriteTimeout      time.Duration `yaml:"write_timeout"`
	RateLimitPerMin   int           `yaml:"rate_limit_per_min"`
	CORSAllowOrigins  []string      `yaml:"cors_allow_origins"`
}

// SOCConfig defines SOC pipeline settings (§7).
type SOCConfig struct {
	DataDir          string `yaml:"data_dir"`
	MaxEventsPerHour int    `yaml:"max_events_per_hour"`
	ClusterEnabled   bool   `yaml:"cluster_enabled"`
	ClusterEps       float64 `yaml:"cluster_eps"`
	ClusterMinPts    int    `yaml:"cluster_min_pts"`
	KillChainEnabled bool   `yaml:"kill_chain_enabled"`
	SSEBufferSize    int    `yaml:"sse_buffer_size"`
}

// RBACConfig defines API key authentication (§17).
type RBACConfig struct {
	Enabled bool       `yaml:"enabled"`
	Keys    []KeyEntry `yaml:"keys"`
}

// KeyEntry is a pre-configured API key.
type KeyEntry struct {
	Key  string `yaml:"key"`
	Role string `yaml:"role"`
	Name string `yaml:"name"`
}

// WebhookConfig defines a SOAR webhook (§15).
type WebhookConfig struct {
	ID      string            `yaml:"id"`
	URL     string            `yaml:"url"`
	Events  []string          `yaml:"events"`
	Headers map[string]string `yaml:"headers"`
	Active  bool              `yaml:"active"`
	Retries int               `yaml:"retries"`
}

// ThreatIntelConfig defines IOC feed sources (§6).
type ThreatIntelConfig struct {
	Enabled       bool          `yaml:"enabled"`
	RefreshInterval time.Duration `yaml:"refresh_interval"`
	Feeds         []FeedConfig  `yaml:"feeds"`
}

// FeedConfig is a single threat intel feed.
type FeedConfig struct {
	Name    string `yaml:"name"`
	URL     string `yaml:"url"`
	Format  string `yaml:"format"` // stix, csv, json
	Enabled bool   `yaml:"enabled"`
}

// SovereignConfig implements §21 — air-gapped deployment mode.
type SovereignConfig struct {
	Enabled           bool   `yaml:"enabled"`
	Mode              string `yaml:"mode"` // airgap, restricted, open
	DisableExternalAPI bool   `yaml:"disable_external_api"`
	DisableTelemetry   bool   `yaml:"disable_telemetry"`
	LocalModelsOnly    bool   `yaml:"local_models_only"`
	DataRetentionDays  int    `yaml:"data_retention_days"`
	EncryptAtRest      bool   `yaml:"encrypt_at_rest"`
	AuditAllRequests   bool   `yaml:"audit_all_requests"`
	MaxPeers           int    `yaml:"max_peers"`
}

// P2PConfig defines SOC mesh sync settings (§14).
type P2PConfig struct {
	Enabled    bool         `yaml:"enabled"`
	ListenAddr string       `yaml:"listen_addr"`
	Peers      []PeerConfig `yaml:"peers"`
}

// PeerConfig is a pre-configured P2P peer.
type PeerConfig struct {
	ID       string `yaml:"id"`
	Name     string `yaml:"name"`
	Endpoint string `yaml:"endpoint"`
	Trust    string `yaml:"trust"` // full, partial, readonly
}

// LoggingConfig defines structured logging settings.
type LoggingConfig struct {
	Level      string `yaml:"level"` // debug, info, warn, error
	Format     string `yaml:"format"` // json, text
	AccessLog  bool   `yaml:"access_log"`
	AuditLog   bool   `yaml:"audit_log"`
	OutputFile string `yaml:"output_file"`
}

// Load reads and parses config from a YAML file.
func Load(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("config: read %s: %w", path, err)
	}

	cfg := DefaultConfig()
	if err := yaml.Unmarshal(data, cfg); err != nil {
		return nil, fmt.Errorf("config: parse %s: %w", path, err)
	}

	if err := cfg.Validate(); err != nil {
		return nil, fmt.Errorf("config: validate: %w", err)
	}

	return cfg, nil
}

// DefaultConfig returns sensible defaults.
func DefaultConfig() *Config {
	return &Config{
		Server: ServerConfig{
			Port:            9100,
			ReadTimeout:     10 * time.Second,
			WriteTimeout:    30 * time.Second,
			RateLimitPerMin: 100,
		},
		SOC: SOCConfig{
			DataDir:          ".syntrex",
			MaxEventsPerHour: 10000,
			ClusterEnabled:   true,
			ClusterEps:       0.5,
			ClusterMinPts:    3,
			KillChainEnabled: true,
			SSEBufferSize:    256,
		},
		RBAC: RBACConfig{
			Enabled: false,
		},
		ThreatIntel: ThreatIntelConfig{
			RefreshInterval: 30 * time.Minute,
		},
		Sovereign: SovereignConfig{
			Mode:              "open",
			DataRetentionDays: 90,
			MaxPeers:          10,
		},
		Logging: LoggingConfig{
			Level:     "info",
			Format:    "json",
			AccessLog: true,
			AuditLog:  true,
		},
	}
}

// Validate checks config for consistency.
func (c *Config) Validate() error {
	if c.Server.Port < 1 || c.Server.Port > 65535 {
		return fmt.Errorf("server.port must be 1-65535, got %d", c.Server.Port)
	}
	if c.Sovereign.Enabled && c.Sovereign.Mode == "" {
		return fmt.Errorf("sovereign.mode required when sovereign.enabled=true")
	}
	if c.Sovereign.Enabled && c.Sovereign.Mode == "airgap" {
		// Enforce: no external APIs, no telemetry, local only
		c.Sovereign.DisableExternalAPI = true
		c.Sovereign.DisableTelemetry = true
		c.Sovereign.LocalModelsOnly = true
	}
	return nil
}

// IsSovereign returns whether sovereign mode is active.
func (c *Config) IsSovereign() bool {
	return c.Sovereign.Enabled
}

// IsAirGapped returns whether the deployment is fully air-gapped.
func (c *Config) IsAirGapped() bool {
	return c.Sovereign.Enabled && c.Sovereign.Mode == "airgap"
}
