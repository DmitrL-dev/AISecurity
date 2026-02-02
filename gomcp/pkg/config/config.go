// Package config provides YAML configuration support for GoMCP.
package config

import (
	"errors"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"
)

// Config represents the GoMCP configuration
type Config struct {
	Server   ServerConfig   `yaml:"server"`
	Security SecurityConfig `yaml:"security"`
	Workers  WorkerConfig   `yaml:"workers"`
	Metrics  MetricsConfig  `yaml:"metrics"`
	Tracing  TracingConfig  `yaml:"tracing"`
	Tenants  TenantsConfig  `yaml:"tenants"`
	Logging  LoggingConfig  `yaml:"logging"`
}

// ServerConfig contains server settings
type ServerConfig struct {
	Host         string        `yaml:"host"`
	Port         int           `yaml:"port"`
	ReadTimeout  time.Duration `yaml:"readTimeout"`
	WriteTimeout time.Duration `yaml:"writeTimeout"`
	IdleTimeout  time.Duration `yaml:"idleTimeout"`
	MaxBodySize  int64         `yaml:"maxBodySize"`
	GRPCPort     int           `yaml:"grpcPort"`
	EnableHTTPS  bool          `yaml:"enableHttps"`
	CertFile     string        `yaml:"certFile"`
	KeyFile      string        `yaml:"keyFile"`
}

// SecurityConfig contains security settings
type SecurityConfig struct {
	EnableValidation  bool          `yaml:"enableValidation"`
	EnableAuditLog    bool          `yaml:"enableAuditLog"`
	EnableRateLimit   bool          `yaml:"enableRateLimit"`
	RateLimitRequests int           `yaml:"rateLimitRequests"`
	RateLimitWindow   time.Duration `yaml:"rateLimitWindow"`
	MaxInputSize      int64         `yaml:"maxInputSize"`
	AllowedTools      []string      `yaml:"allowedTools"`
	DeniedTools       []string      `yaml:"deniedTools"`
}

// WorkerConfig contains worker pool settings
type WorkerConfig struct {
	Count           int           `yaml:"count"`
	QueueSize       int           `yaml:"queueSize"`
	DefaultTimeout  time.Duration `yaml:"defaultTimeout"`
	MaxTimeout      time.Duration `yaml:"maxTimeout"`
	EnableHotReload bool          `yaml:"enableHotReload"`
}

// MetricsConfig contains metrics settings
type MetricsConfig struct {
	Enabled   bool   `yaml:"enabled"`
	Endpoint  string `yaml:"endpoint"`
	Namespace string `yaml:"namespace"`
}

// TracingConfig contains tracing settings
type TracingConfig struct {
	Enabled     bool    `yaml:"enabled"`
	Endpoint    string  `yaml:"endpoint"`
	ServiceName string  `yaml:"serviceName"`
	SampleRate  float64 `yaml:"sampleRate"`
}

// TenantsConfig contains multi-tenancy settings
type TenantsConfig struct {
	Enabled      bool              `yaml:"enabled"`
	DefaultQuota int               `yaml:"defaultQuota"`
	Quotas       map[string]int    `yaml:"quotas"`
	Namespaces   map[string]string `yaml:"namespaces"`
}

// LoggingConfig contains logging settings
type LoggingConfig struct {
	Level  string `yaml:"level"`
	Format string `yaml:"format"`
	Output string `yaml:"output"`
}

// DefaultConfig returns a Config with default values
func DefaultConfig() *Config {
	return &Config{
		Server: ServerConfig{
			Host:         "0.0.0.0",
			Port:         8080,
			ReadTimeout:  30 * time.Second,
			WriteTimeout: 30 * time.Second,
			IdleTimeout:  120 * time.Second,
			MaxBodySize:  10 * 1024 * 1024,
			GRPCPort:     9090,
		},
		Security: SecurityConfig{
			EnableValidation:  true,
			EnableAuditLog:    true,
			EnableRateLimit:   true,
			RateLimitRequests: 1000,
			RateLimitWindow:   time.Minute,
			MaxInputSize:      1024 * 1024,
		},
		Workers: WorkerConfig{
			Count:          10,
			QueueSize:      100,
			DefaultTimeout: 30 * time.Second,
			MaxTimeout:     5 * time.Minute,
		},
		Metrics: MetricsConfig{
			Enabled:   true,
			Endpoint:  "/metrics",
			Namespace: "gomcp",
		},
		Tracing: TracingConfig{
			Enabled:     false,
			ServiceName: "gomcp",
			SampleRate:  0.1,
		},
		Tenants: TenantsConfig{
			Enabled:      false,
			DefaultQuota: 1000,
			Quotas:       make(map[string]int),
			Namespaces:   make(map[string]string),
		},
		Logging: LoggingConfig{
			Level:  "info",
			Format: "json",
			Output: "stdout",
		},
	}
}

// Validate checks if the configuration is valid
func (c *Config) Validate() error {
	if c.Server.Port < 1 || c.Server.Port > 65535 {
		return errors.New("invalid server port")
	}
	if c.Workers.Count < 1 {
		return errors.New("worker count must be at least 1")
	}
	if c.Security.RateLimitRequests < 0 {
		return errors.New("rate limit requests cannot be negative")
	}
	return nil
}

// Merge merges another config into this one (non-zero values override)
func (c *Config) Merge(other *Config) {
	if other.Server.Port != 0 {
		c.Server.Port = other.Server.Port
	}
	if other.Server.Host != "" {
		c.Server.Host = other.Server.Host
	}
	if other.Workers.Count != 0 {
		c.Workers.Count = other.Workers.Count
	}
	// Add more merge logic as needed
}

// Clone creates a deep copy of the config
func (c *Config) Clone() *Config {
	clone := *c
	clone.Security.AllowedTools = append([]string{}, c.Security.AllowedTools...)
	clone.Security.DeniedTools = append([]string{}, c.Security.DeniedTools...)
	clone.Tenants.Quotas = make(map[string]int)
	for k, v := range c.Tenants.Quotas {
		clone.Tenants.Quotas[k] = v
	}
	clone.Tenants.Namespaces = make(map[string]string)
	for k, v := range c.Tenants.Namespaces {
		clone.Tenants.Namespaces[k] = v
	}
	return &clone
}

// Loader loads configuration from various sources
type Loader struct {
	envPrefix string
	mu        sync.RWMutex
}

// NewLoader creates a new config loader
func NewLoader(envPrefix string) *Loader {
	return &Loader{
		envPrefix: envPrefix,
	}
}

// LoadFromEnv loads configuration from environment variables
func (l *Loader) LoadFromEnv() *Config {
	l.mu.RLock()
	defer l.mu.RUnlock()

	cfg := DefaultConfig()

	// Server
	if val := l.getEnv("HOST"); val != "" {
		cfg.Server.Host = val
	}
	if val := l.getEnvInt("PORT"); val > 0 {
		cfg.Server.Port = val
	}
	if val := l.getEnvInt("GRPC_PORT"); val > 0 {
		cfg.Server.GRPCPort = val
	}

	// Workers
	if val := l.getEnvInt("WORKERS"); val > 0 {
		cfg.Workers.Count = val
	}
	if val := l.getEnvInt("QUEUE_SIZE"); val > 0 {
		cfg.Workers.QueueSize = val
	}

	// Security
	if val := l.getEnvBool("ENABLE_VALIDATION"); val {
		cfg.Security.EnableValidation = val
	}
	if val := l.getEnvBool("ENABLE_RATE_LIMIT"); val {
		cfg.Security.EnableRateLimit = val
	}

	// Metrics
	if val := l.getEnvBool("METRICS_ENABLED"); val {
		cfg.Metrics.Enabled = val
	}

	// Logging
	if val := l.getEnv("LOG_LEVEL"); val != "" {
		cfg.Logging.Level = val
	}

	return cfg
}

func (l *Loader) getEnv(key string) string {
	return os.Getenv(l.envPrefix + "_" + key)
}

func (l *Loader) getEnvInt(key string) int {
	val := l.getEnv(key)
	if val == "" {
		return 0
	}
	n, _ := strconv.Atoi(val)
	return n
}

func (l *Loader) getEnvBool(key string) bool {
	val := l.getEnv(key)
	return strings.ToLower(val) == "true" || val == "1"
}

// Watcher watches for config changes
type Watcher struct {
	path     string
	onChange func(*Config)
	stop     chan struct{}
	running  bool
	mu       sync.Mutex
}

// NewWatcher creates a config watcher
func NewWatcher(path string, onChange func(*Config)) *Watcher {
	return &Watcher{
		path:     path,
		onChange: onChange,
		stop:     make(chan struct{}),
	}
}

// Path returns the watched path
func (w *Watcher) Path() string {
	return w.path
}

// IsRunning returns whether the watcher is running
func (w *Watcher) IsRunning() bool {
	w.mu.Lock()
	defer w.mu.Unlock()
	return w.running
}

// Start starts watching for changes
func (w *Watcher) Start() error {
	w.mu.Lock()
	defer w.mu.Unlock()
	if w.running {
		return errors.New("watcher already running")
	}
	w.running = true
	w.stop = make(chan struct{})
	return nil
}

// Stop stops watching
func (w *Watcher) Stop() {
	w.mu.Lock()
	defer w.mu.Unlock()
	if !w.running {
		return
	}
	close(w.stop)
	w.running = false
}

// Builder helps construct configurations
type Builder struct {
	cfg *Config
}

// NewBuilder creates a config builder
func NewBuilder() *Builder {
	return &Builder{
		cfg: DefaultConfig(),
	}
}

// ServerPort sets the server port
func (b *Builder) ServerPort(port int) *Builder {
	b.cfg.Server.Port = port
	return b
}

// ServerHost sets the server host
func (b *Builder) ServerHost(host string) *Builder {
	b.cfg.Server.Host = host
	return b
}

// Workers sets the worker count
func (b *Builder) Workers(count int) *Builder {
	b.cfg.Workers.Count = count
	return b
}

// EnableMetrics enables metrics
func (b *Builder) EnableMetrics(enabled bool) *Builder {
	b.cfg.Metrics.Enabled = enabled
	return b
}

// EnableTracing enables tracing
func (b *Builder) EnableTracing(enabled bool) *Builder {
	b.cfg.Tracing.Enabled = enabled
	return b
}

// LogLevel sets the log level
func (b *Builder) LogLevel(level string) *Builder {
	b.cfg.Logging.Level = level
	return b
}

// Build returns the constructed config
func (b *Builder) Build() *Config {
	return b.cfg.Clone()
}
