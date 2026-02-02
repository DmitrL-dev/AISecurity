package config

import (
	"os"
	"sync"
	"testing"
	"time"
)

// Config struct tests
func TestDefaultConfig(t *testing.T) {
	cfg := DefaultConfig()
	if cfg == nil {
		t.Fatal("config should not be nil")
	}
}

func TestDefaultConfig_Server(t *testing.T) {
	cfg := DefaultConfig()
	if cfg.Server.Host != "0.0.0.0" {
		t.Errorf("expected 0.0.0.0, got %s", cfg.Server.Host)
	}
	if cfg.Server.Port != 8080 {
		t.Errorf("expected 8080, got %d", cfg.Server.Port)
	}
}

func TestDefaultConfig_Workers(t *testing.T) {
	cfg := DefaultConfig()
	if cfg.Workers.Count != 10 {
		t.Errorf("expected 10, got %d", cfg.Workers.Count)
	}
}

func TestDefaultConfig_Security(t *testing.T) {
	cfg := DefaultConfig()
	if !cfg.Security.EnableValidation {
		t.Error("validation should be enabled by default")
	}
}

func TestDefaultConfig_Metrics(t *testing.T) {
	cfg := DefaultConfig()
	if !cfg.Metrics.Enabled {
		t.Error("metrics should be enabled by default")
	}
	if cfg.Metrics.Namespace != "gomcp" {
		t.Errorf("expected gomcp, got %s", cfg.Metrics.Namespace)
	}
}

func TestDefaultConfig_Logging(t *testing.T) {
	cfg := DefaultConfig()
	if cfg.Logging.Level != "info" {
		t.Errorf("expected info, got %s", cfg.Logging.Level)
	}
}

// Validate tests
func TestConfig_Validate_Valid(t *testing.T) {
	cfg := DefaultConfig()
	err := cfg.Validate()
	if err != nil {
		t.Errorf("default config should be valid: %v", err)
	}
}

func TestConfig_Validate_InvalidPort(t *testing.T) {
	cfg := DefaultConfig()
	cfg.Server.Port = 0
	err := cfg.Validate()
	if err == nil {
		t.Error("should error on port 0")
	}

	cfg.Server.Port = 70000
	err = cfg.Validate()
	if err == nil {
		t.Error("should error on port > 65535")
	}
}

func TestConfig_Validate_InvalidWorkers(t *testing.T) {
	cfg := DefaultConfig()
	cfg.Workers.Count = 0
	err := cfg.Validate()
	if err == nil {
		t.Error("should error on 0 workers")
	}
}

func TestConfig_Validate_InvalidRateLimit(t *testing.T) {
	cfg := DefaultConfig()
	cfg.Security.RateLimitRequests = -1
	err := cfg.Validate()
	if err == nil {
		t.Error("should error on negative rate limit")
	}
}

// Clone tests
func TestConfig_Clone(t *testing.T) {
	cfg := DefaultConfig()
	cfg.Server.Port = 9999
	cfg.Security.AllowedTools = []string{"tool1", "tool2"}

	clone := cfg.Clone()
	if clone.Server.Port != 9999 {
		t.Error("clone should have same port")
	}

	// Modify clone
	clone.Server.Port = 8888
	if cfg.Server.Port == 8888 {
		t.Error("original should not be modified")
	}
}

func TestConfig_Clone_DeepCopy(t *testing.T) {
	cfg := DefaultConfig()
	cfg.Tenants.Quotas["t1"] = 100

	clone := cfg.Clone()
	clone.Tenants.Quotas["t1"] = 200

	if cfg.Tenants.Quotas["t1"] == 200 {
		t.Error("original quotas should not be modified")
	}
}

// Merge tests
func TestConfig_Merge(t *testing.T) {
	cfg := DefaultConfig()
	other := &Config{
		Server: ServerConfig{
			Port: 9999,
		},
	}

	cfg.Merge(other)
	if cfg.Server.Port != 9999 {
		t.Errorf("expected 9999, got %d", cfg.Server.Port)
	}
}

func TestConfig_Merge_ZeroNotOverride(t *testing.T) {
	cfg := DefaultConfig()
	original := cfg.Server.Port
	other := &Config{}

	cfg.Merge(other)
	if cfg.Server.Port != original {
		t.Error("zero value should not override")
	}
}

// Loader tests
func TestNewLoader(t *testing.T) {
	l := NewLoader("GOMCP")
	if l == nil {
		t.Fatal("loader should not be nil")
	}
}

func TestLoader_LoadFromEnv(t *testing.T) {
	os.Setenv("GOMCP_HOST", "127.0.0.1")
	os.Setenv("GOMCP_PORT", "9090")
	defer os.Unsetenv("GOMCP_HOST")
	defer os.Unsetenv("GOMCP_PORT")

	l := NewLoader("GOMCP")
	cfg := l.LoadFromEnv()

	if cfg.Server.Host != "127.0.0.1" {
		t.Errorf("expected 127.0.0.1, got %s", cfg.Server.Host)
	}
	if cfg.Server.Port != 9090 {
		t.Errorf("expected 9090, got %d", cfg.Server.Port)
	}
}

func TestLoader_LoadFromEnv_Workers(t *testing.T) {
	os.Setenv("GOMCP_WORKERS", "20")
	defer os.Unsetenv("GOMCP_WORKERS")

	l := NewLoader("GOMCP")
	cfg := l.LoadFromEnv()

	if cfg.Workers.Count != 20 {
		t.Errorf("expected 20, got %d", cfg.Workers.Count)
	}
}

func TestLoader_getEnvInt_Invalid(t *testing.T) {
	os.Setenv("GOMCP_PORT", "not-a-number")
	defer os.Unsetenv("GOMCP_PORT")

	l := NewLoader("GOMCP")
	val := l.getEnvInt("PORT")
	if val != 0 {
		t.Error("invalid int should return 0")
	}
}

func TestLoader_getEnvBool(t *testing.T) {
	os.Setenv("GOMCP_TEST", "true")
	defer os.Unsetenv("GOMCP_TEST")

	l := NewLoader("GOMCP")
	if !l.getEnvBool("TEST") {
		t.Error("should return true")
	}
}

func TestLoader_getEnvBool_Numeric(t *testing.T) {
	os.Setenv("GOMCP_TEST", "1")
	defer os.Unsetenv("GOMCP_TEST")

	l := NewLoader("GOMCP")
	if !l.getEnvBool("TEST") {
		t.Error("should return true for '1'")
	}
}

// Watcher tests
func TestNewWatcher(t *testing.T) {
	w := NewWatcher("/path/to/config.yaml", nil)
	if w == nil {
		t.Fatal("watcher should not be nil")
	}
}

func TestWatcher_Path(t *testing.T) {
	w := NewWatcher("/path/to/config.yaml", nil)
	if w.Path() != "/path/to/config.yaml" {
		t.Error("path mismatch")
	}
}

func TestWatcher_IsRunning(t *testing.T) {
	w := NewWatcher("", nil)
	if w.IsRunning() {
		t.Error("should not be running initially")
	}
}

func TestWatcher_Start(t *testing.T) {
	w := NewWatcher("", nil)
	err := w.Start()
	if err != nil {
		t.Errorf("start error: %v", err)
	}
	if !w.IsRunning() {
		t.Error("should be running after start")
	}
}

func TestWatcher_Start_AlreadyRunning(t *testing.T) {
	w := NewWatcher("", nil)
	w.Start()
	err := w.Start()
	if err == nil {
		t.Error("should error if already running")
	}
}

func TestWatcher_Stop(t *testing.T) {
	w := NewWatcher("", nil)
	w.Start()
	w.Stop()
	if w.IsRunning() {
		t.Error("should not be running after stop")
	}
}

func TestWatcher_Stop_NotRunning(t *testing.T) {
	w := NewWatcher("", nil)
	w.Stop() // Should not panic
}

// Builder tests
func TestNewBuilder(t *testing.T) {
	b := NewBuilder()
	if b == nil {
		t.Fatal("builder should not be nil")
	}
}

func TestBuilder_ServerPort(t *testing.T) {
	cfg := NewBuilder().
		ServerPort(9999).
		Build()

	if cfg.Server.Port != 9999 {
		t.Errorf("expected 9999, got %d", cfg.Server.Port)
	}
}

func TestBuilder_ServerHost(t *testing.T) {
	cfg := NewBuilder().
		ServerHost("localhost").
		Build()

	if cfg.Server.Host != "localhost" {
		t.Errorf("expected localhost, got %s", cfg.Server.Host)
	}
}

func TestBuilder_Workers(t *testing.T) {
	cfg := NewBuilder().
		Workers(50).
		Build()

	if cfg.Workers.Count != 50 {
		t.Errorf("expected 50, got %d", cfg.Workers.Count)
	}
}

func TestBuilder_EnableMetrics(t *testing.T) {
	cfg := NewBuilder().
		EnableMetrics(false).
		Build()

	if cfg.Metrics.Enabled {
		t.Error("metrics should be disabled")
	}
}

func TestBuilder_EnableTracing(t *testing.T) {
	cfg := NewBuilder().
		EnableTracing(true).
		Build()

	if !cfg.Tracing.Enabled {
		t.Error("tracing should be enabled")
	}
}

func TestBuilder_LogLevel(t *testing.T) {
	cfg := NewBuilder().
		LogLevel("debug").
		Build()

	if cfg.Logging.Level != "debug" {
		t.Errorf("expected debug, got %s", cfg.Logging.Level)
	}
}

func TestBuilder_Chaining(t *testing.T) {
	cfg := NewBuilder().
		ServerPort(8081).
		ServerHost("127.0.0.1").
		Workers(20).
		EnableMetrics(true).
		LogLevel("warn").
		Build()

	if cfg.Server.Port != 8081 {
		t.Error("port not set")
	}
	if cfg.Workers.Count != 20 {
		t.Error("workers not set")
	}
	if cfg.Logging.Level != "warn" {
		t.Error("log level not set")
	}
}

// Concurrent tests
func TestLoader_Concurrent(t *testing.T) {
	l := NewLoader("GOMCP")
	var wg sync.WaitGroup

	for i := 0; i < 100; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			l.LoadFromEnv()
		}()
	}
	wg.Wait()
}

func TestWatcher_Concurrent(t *testing.T) {
	w := NewWatcher("", nil)
	var wg sync.WaitGroup

	for i := 0; i < 50; i++ {
		wg.Add(2)
		go func() {
			defer wg.Done()
			w.Start()
		}()
		go func() {
			defer wg.Done()
			w.Stop()
		}()
	}
	wg.Wait()
}

// Duration tests
func TestConfig_Durations(t *testing.T) {
	cfg := DefaultConfig()
	if cfg.Server.ReadTimeout != 30*time.Second {
		t.Error("read timeout mismatch")
	}
	if cfg.Server.WriteTimeout != 30*time.Second {
		t.Error("write timeout mismatch")
	}
}

// Benchmark tests
func BenchmarkDefaultConfig(b *testing.B) {
	for i := 0; i < b.N; i++ {
		DefaultConfig()
	}
}

func BenchmarkConfig_Clone(b *testing.B) {
	cfg := DefaultConfig()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		cfg.Clone()
	}
}

func BenchmarkConfig_Validate(b *testing.B) {
	cfg := DefaultConfig()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		cfg.Validate()
	}
}

func BenchmarkBuilder_Build(b *testing.B) {
	for i := 0; i < b.N; i++ {
		NewBuilder().
			ServerPort(8080).
			Workers(10).
			Build()
	}
}
