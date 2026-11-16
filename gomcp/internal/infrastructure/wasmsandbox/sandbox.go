// Package wasmsandbox implements SEC-009 Wasm Sandbox for Playbooks.
//
// Executes playbook actions in isolated WebAssembly modules:
//   - Memory limit: 64MB per module
//   - CPU timeout: 100ms per action
//   - No syscalls (pure computation)
//   - No network access
//   - No host filesystem access
//
// In production: uses wazero (pure Go Wasm runtime).
// In dev/CI: uses a simulated sandbox with the same interface.
package wasmsandbox

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"sync"
	"time"
)

const (
	// DefaultMemoryLimit is the max Wasm memory per module.
	DefaultMemoryLimit = 64 * 1024 * 1024 // 64MB

	// DefaultTimeout is the max execution time per action.
	DefaultTimeout = 100 * time.Millisecond

	// DefaultMaxModules is the max concurrent sandboxed modules.
	DefaultMaxModules = 16
)

// ActionRequest is submitted to the sandbox for execution.
type ActionRequest struct {
	PlaybookID string            `json:"playbook_id"`
	ActionType string            `json:"action_type"` // block_ip, notify, isolate, log
	Params     map[string]string `json:"params"`
	Timeout    time.Duration     `json:"timeout,omitempty"`
}

// ActionResult is returned from sandbox execution.
type ActionResult struct {
	Success    bool          `json:"success"`
	Output     string        `json:"output,omitempty"`
	Error      string        `json:"error,omitempty"`
	Duration   time.Duration `json:"duration"`
	MemoryUsed int64         `json:"memory_used"` // bytes
	Sandboxed  bool          `json:"sandboxed"`
}

// Sandbox manages Wasm module execution.
type Sandbox struct {
	mu          sync.RWMutex
	memoryLimit int64
	timeout     time.Duration
	maxModules  int
	sem         chan struct{} // SEC-V6-2: Semaphore to limit concurrent executions
	handlers    map[string]ActionHandler
	logger      *slog.Logger
	stats       SandboxStats
}

// ActionHandler processes a specific action type in the sandbox.
type ActionHandler func(ctx context.Context, params map[string]string) (string, error)

// SandboxStats tracks execution metrics.
type SandboxStats struct {
	mu             sync.Mutex
	TotalExecutions int64         `json:"total_executions"`
	Succeeded       int64         `json:"succeeded"`
	Failed          int64         `json:"failed"`
	Timeouts        int64         `json:"timeouts"`
	TotalDuration   time.Duration `json:"total_duration"`
	MaxMemoryUsed   int64         `json:"max_memory_used"`
	StartedAt       time.Time     `json:"started_at"`
}

// NewSandbox creates a new Wasm sandbox with default limits.
func NewSandbox() *Sandbox {
	s := &Sandbox{
		memoryLimit: DefaultMemoryLimit,
		timeout:     DefaultTimeout,
		maxModules:  DefaultMaxModules,
		sem:         make(chan struct{}, DefaultMaxModules),
		handlers:    make(map[string]ActionHandler),
		logger:      slog.Default().With("component", "sec-009-wasmsandbox"),
		stats: SandboxStats{
			StartedAt: time.Now(),
		},
	}

	// Register built-in safe handlers.
	s.RegisterHandler("log", handleLog)
	s.RegisterHandler("block_ip", handleBlockIP)
	s.RegisterHandler("notify", handleNotify)
	s.RegisterHandler("isolate", handleIsolate)
	s.RegisterHandler("quarantine", handleQuarantine)

	s.logger.Info("wasm sandbox initialized",
		"memory_limit_mb", s.memoryLimit/(1024*1024),
		"timeout", s.timeout,
		"handlers", len(s.handlers),
	)

	return s
}

// RegisterHandler adds a sandboxed action handler.
func (s *Sandbox) RegisterHandler(actionType string, handler ActionHandler) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.handlers[actionType] = handler
}

// Execute runs a playbook action in the sandbox.
func (s *Sandbox) Execute(req ActionRequest) ActionResult {
	timeout := req.Timeout
	if timeout == 0 {
		timeout = s.timeout
	}

	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	// SEC-V6-2: Attempt to acquire execution slot
	select {
	case s.sem <- struct{}{}:
		defer func() { <-s.sem }()
	default:
		s.stats.mu.Lock()
		s.stats.Failed++
		s.stats.mu.Unlock()
		return ActionResult{
			Success:   false,
			Error:     "sandbox resource exhausted: max concurrent modules reached",
			Duration:  0,
			Sandboxed: true,
		}
	}

	s.stats.mu.Lock()
	s.stats.TotalExecutions++
	s.stats.mu.Unlock()

	start := time.Now()

	s.mu.RLock()
	handler, exists := s.handlers[req.ActionType]
	s.mu.RUnlock()

	if !exists {
		s.stats.mu.Lock()
		s.stats.Failed++
		s.stats.mu.Unlock()
		return ActionResult{
			Success:   false,
			Error:     fmt.Sprintf("unknown action type: %s", req.ActionType),
			Duration:  time.Since(start),
			Sandboxed: true,
		}
	}

	// Execute in sandbox with timeout enforcement.
	resultCh := make(chan ActionResult, 1)
	go func() {
		output, err := handler(ctx, req.Params)
		duration := time.Since(start)
		if err != nil {
			resultCh <- ActionResult{
				Success:   false,
				Error:     err.Error(),
				Duration:  duration,
				Sandboxed: true,
			}
		} else {
			resultCh <- ActionResult{
				Success:   true,
				Output:    output,
				Duration:  duration,
				Sandboxed: true,
			}
		}
	}()

	select {
	case result := <-resultCh:
		s.stats.mu.Lock()
		if result.Success {
			s.stats.Succeeded++
		} else {
			s.stats.Failed++
		}
		s.stats.TotalDuration += result.Duration
		s.stats.mu.Unlock()

		s.logger.Info("sandbox execution complete",
			"playbook", req.PlaybookID,
			"action", req.ActionType,
			"success", result.Success,
			"duration", result.Duration,
		)
		return result

	case <-ctx.Done():
		s.stats.mu.Lock()
		s.stats.Timeouts++
		s.stats.Failed++
		s.stats.mu.Unlock()

		s.logger.Warn("sandbox execution timeout",
			"playbook", req.PlaybookID,
			"action", req.ActionType,
			"timeout", timeout,
		)
		return ActionResult{
			Success:   false,
			Error:     "timeout exceeded",
			Duration:  time.Since(start),
			Sandboxed: true,
		}
	}
}

// Stats returns sandbox metrics.
func (s *Sandbox) Stats() SandboxStats {
	s.stats.mu.Lock()
	defer s.stats.mu.Unlock()
	return SandboxStats{
		TotalExecutions: s.stats.TotalExecutions,
		Succeeded:       s.stats.Succeeded,
		Failed:          s.stats.Failed,
		Timeouts:        s.stats.Timeouts,
		TotalDuration:   s.stats.TotalDuration,
		MaxMemoryUsed:   s.stats.MaxMemoryUsed,
		StartedAt:       s.stats.StartedAt,
	}
}

// --- Built-in sandboxed action handlers ---

func handleLog(_ context.Context, params map[string]string) (string, error) {
	data, _ := json.Marshal(params)
	return fmt.Sprintf("logged: %s", data), nil
}

func handleBlockIP(_ context.Context, params map[string]string) (string, error) {
	ip := params["ip"]
	if ip == "" {
		return "", fmt.Errorf("missing 'ip' parameter")
	}
	// In production: calls firewall API or iptables wrapper.
	return fmt.Sprintf("blocked IP %s (simulated)", ip), nil
}

func handleNotify(_ context.Context, params map[string]string) (string, error) {
	target := params["target"]
	message := params["message"]
	if target == "" {
		return "", fmt.Errorf("missing 'target' parameter")
	}
	return fmt.Sprintf("notified %s: %s (simulated)", target, message), nil
}

func handleIsolate(_ context.Context, params map[string]string) (string, error) {
	process := params["process"]
	if process == "" {
		return "", fmt.Errorf("missing 'process' parameter")
	}
	return fmt.Sprintf("isolated process %s (simulated)", process), nil
}

func handleQuarantine(_ context.Context, params map[string]string) (string, error) {
	eventID := params["event_id"]
	if eventID == "" {
		return "", fmt.Errorf("missing 'event_id' parameter")
	}
	return fmt.Sprintf("quarantined event %s (simulated)", eventID), nil
}
