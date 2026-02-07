package config

// Config holds global configuration
type Config struct {
	ThreadPoolSize int
	TargetURL      string
	StrictMode     bool
}

// Load reads config from environment or flags
func Load() (*Config, error) {
	// Stub implementation
	return &Config{
		ThreadPoolSize: 10,
		TargetURL:      "http://localhost:8080",
		StrictMode:     true,
	}, nil
}
