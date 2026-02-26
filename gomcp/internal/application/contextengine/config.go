package contextengine

import (
	"encoding/json"
	"os"

	ctxdomain "github.com/sentinel-community/gomcp/internal/domain/context"
)

// LoadConfig loads engine configuration from a JSON file.
// If the file does not exist, returns DefaultEngineConfig.
// If the file exists but is invalid, returns an error.
func LoadConfig(path string) (ctxdomain.EngineConfig, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return ctxdomain.DefaultEngineConfig(), nil
		}
		return ctxdomain.EngineConfig{}, err
	}

	var cfg ctxdomain.EngineConfig
	if err := json.Unmarshal(data, &cfg); err != nil {
		return ctxdomain.EngineConfig{}, err
	}

	// Build skip set from deserialized SkipTools slice.
	cfg.BuildSkipSet()

	// If skip_tools was omitted in JSON, use defaults.
	if cfg.SkipTools == nil {
		cfg.SkipTools = ctxdomain.DefaultSkipTools()
		cfg.BuildSkipSet()
	}

	if err := cfg.Validate(); err != nil {
		return ctxdomain.EngineConfig{}, err
	}

	return cfg, nil
}

// SaveDefaultConfig writes the default configuration to a JSON file.
// Useful for bootstrapping .rlm/context.json.
func SaveDefaultConfig(path string) error {
	cfg := ctxdomain.DefaultEngineConfig()
	data, err := json.MarshalIndent(cfg, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, data, 0o644)
}
