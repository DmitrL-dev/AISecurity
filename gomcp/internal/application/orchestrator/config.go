package orchestrator

import (
	"encoding/json"
	"fmt"
	"os"
	"time"
)

// JSONConfig is the v3.4 file-based configuration for the Orchestrator.
// Loaded from .rlm/config.json. Overrides compiled defaults.
type JSONConfig struct {
	HeartbeatIntervalSec int     `json:"heartbeat_interval_sec,omitempty"`
	JitterPercent        int     `json:"jitter_percent,omitempty"`
	EntropyThreshold     float64 `json:"entropy_threshold,omitempty"`
	MaxSyncBatchSize     int     `json:"max_sync_batch_size,omitempty"`
	SynapseIntervalMult  int     `json:"synapse_interval_multiplier,omitempty"` // default: 12
}

// LoadConfigFromFile reads .rlm/config.json and returns a Config.
// Missing or invalid file → returns defaults silently.
func LoadConfigFromFile(path string) Config {
	cfg := Config{
		HeartbeatInterval: 5 * time.Minute,
		JitterPercent:     30,
		EntropyThreshold:  0.8,
		MaxSyncBatchSize:  100,
	}

	data, err := os.ReadFile(path)
	if err != nil {
		return cfg // File not found → use defaults.
	}

	var jcfg JSONConfig
	if err := json.Unmarshal(data, &jcfg); err != nil {
		return cfg // Invalid JSON → use defaults.
	}

	if jcfg.HeartbeatIntervalSec > 0 {
		cfg.HeartbeatInterval = time.Duration(jcfg.HeartbeatIntervalSec) * time.Second
	}
	if jcfg.JitterPercent > 0 && jcfg.JitterPercent <= 100 {
		cfg.JitterPercent = jcfg.JitterPercent
	}
	if jcfg.EntropyThreshold > 0 && jcfg.EntropyThreshold <= 1.0 {
		cfg.EntropyThreshold = jcfg.EntropyThreshold
	}
	if jcfg.MaxSyncBatchSize > 0 {
		cfg.MaxSyncBatchSize = jcfg.MaxSyncBatchSize
	}

	return cfg
}

// WriteDefaultConfig writes a default config.json to the given path.
func WriteDefaultConfig(path string) error {
	jcfg := JSONConfig{
		HeartbeatIntervalSec: 300,
		JitterPercent:        30,
		EntropyThreshold:     0.8,
		MaxSyncBatchSize:     100,
		SynapseIntervalMult:  12,
	}
	data, err := json.MarshalIndent(jcfg, "", "  ")
	if err != nil {
		return fmt.Errorf("marshal config: %w", err)
	}
	return os.WriteFile(path, data, 0o644)
}
