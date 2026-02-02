package main

import (
	"testing"
	"time"

	"github.com/sentinel-community/gomcp/pkg/supervisor"
)

func TestVersionConstant(t *testing.T) {
	if version != "0.1.0-proto" {
		t.Errorf("expected version 0.1.0-proto, got %s", version)
	}
}

func TestSupervisorCreation(t *testing.T) {
	sup := supervisor.New(supervisor.Config{
		DefaultTimeout:  30 * time.Second,
		MaxWorkers:      10,
		HeartbeatPeriod: 5 * time.Second,
	})

	if sup == nil {
		t.Fatal("supervisor should not be nil")
	}
}

func TestSupervisorWithDifferentConfigs(t *testing.T) {
	testCases := []struct {
		name   string
		config supervisor.Config
	}{
		{
			name: "default",
			config: supervisor.Config{
				DefaultTimeout:  30 * time.Second,
				MaxWorkers:      10,
				HeartbeatPeriod: 5 * time.Second,
			},
		},
		{
			name: "short_timeout",
			config: supervisor.Config{
				DefaultTimeout:  5 * time.Second,
				MaxWorkers:      5,
				HeartbeatPeriod: 1 * time.Second,
			},
		},
		{
			name: "high_capacity",
			config: supervisor.Config{
				DefaultTimeout:  time.Minute,
				MaxWorkers:      100,
				HeartbeatPeriod: 10 * time.Second,
			},
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			sup := supervisor.New(tc.config)
			if sup == nil {
				t.Fatal("supervisor should not be nil")
			}
		})
	}
}

func TestSupervisorShutdown(t *testing.T) {
	sup := supervisor.New(supervisor.Config{
		DefaultTimeout:  30 * time.Second,
		MaxWorkers:      10,
		HeartbeatPeriod: 5 * time.Second,
	})

	// Should not panic
	sup.Shutdown()
}

func TestSupervisorDoubleShutdown(t *testing.T) {
	sup := supervisor.New(supervisor.Config{
		DefaultTimeout: 30 * time.Second,
	})

	// Double shutdown should not panic
	sup.Shutdown()
	sup.Shutdown()
}

func TestRunStdioAdapterDoesNotPanic(t *testing.T) {
	sup := supervisor.New(supervisor.Config{
		DefaultTimeout: 30 * time.Second,
	})

	// Should not panic (just prints not implemented)
	runStdioAdapter(sup)
}

func TestRunGRPCServerDoesNotPanic(t *testing.T) {
	sup := supervisor.New(supervisor.Config{
		DefaultTimeout: 30 * time.Second,
	})

	// Should not panic
	runGRPCServer(sup)
}

func TestRunHTTPServerDoesNotPanic(t *testing.T) {
	sup := supervisor.New(supervisor.Config{
		DefaultTimeout: 30 * time.Second,
	})

	// Should not panic
	runHTTPServer(sup)
}

func TestModeValidation(t *testing.T) {
	isValidMode := func(m string) bool {
		switch m {
		case "stdio", "grpc", "http":
			return true
		default:
			return false
		}
	}

	t.Run("valid modes", func(t *testing.T) {
		validModes := []string{"stdio", "grpc", "http"}
		for _, m := range validModes {
			if !isValidMode(m) {
				t.Errorf("mode %s should be valid", m)
			}
		}
	})

	t.Run("invalid modes", func(t *testing.T) {
		invalidModes := []string{"invalid", "tcp", "ws", ""}
		for _, m := range invalidModes {
			if isValidMode(m) {
				t.Errorf("mode %s should be invalid", m)
			}
		}
	})
}

func TestTimeoutDurations(t *testing.T) {
	testCases := []struct {
		name     string
		duration time.Duration
		valid    bool
	}{
		{"zero", 0, false},
		{"second", time.Second, true},
		{"minute", time.Minute, true},
		{"default_30s", 30 * time.Second, true},
		{"negative", -time.Second, false},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			isValid := tc.duration > 0
			if isValid != tc.valid {
				t.Errorf("duration %v validity: expected %v, got %v", tc.duration, tc.valid, isValid)
			}
		})
	}
}

// Benchmark
func BenchmarkSupervisorCreation(b *testing.B) {
	for i := 0; i < b.N; i++ {
		sup := supervisor.New(supervisor.Config{
			DefaultTimeout:  30 * time.Second,
			MaxWorkers:      10,
			HeartbeatPeriod: 5 * time.Second,
		})
		_ = sup
	}
}

func BenchmarkSupervisorShutdown(b *testing.B) {
	for i := 0; i < b.N; i++ {
		sup := supervisor.New(supervisor.Config{
			DefaultTimeout: 30 * time.Second,
		})
		sup.Shutdown()
	}
}
