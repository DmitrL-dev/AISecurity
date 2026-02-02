// Package supervisor manages tool workers with timeout enforcement and health monitoring.
package supervisor

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"sync"
	"time"
)

// DefaultTimeout for tool calls if not specified
const DefaultTimeout = 30 * time.Second

// HeartbeatInterval for health checks
const HeartbeatInterval = 5 * time.Second

// Worker represents a tool worker process
type Worker struct {
	ID        string
	Command   string
	Args      []string
	Process   *exec.Cmd
	Stdin     chan []byte
	Stdout    chan []byte
	StartedAt time.Time
	Tools     []ToolDef
	mu        sync.RWMutex
	healthy   bool
}

// ToolDef defines a tool's metadata
type ToolDef struct {
	Name           string          `json:"name"`
	Description    string          `json:"description"`
	InputSchema    json.RawMessage `json:"inputSchema"`
	DefaultTimeout time.Duration   `json:"defaultTimeout"`
}

// ToolCall represents a pending tool call
type ToolCall struct {
	RequestID string
	ToolName  string
	Arguments json.RawMessage
	Timeout   time.Duration
	Started   time.Time
	Done      chan *ToolResult
}

// ToolResult is the result of a tool call
type ToolResult struct {
	Output   json.RawMessage
	Error    *ToolError
	Duration time.Duration
}

// ToolError represents a tool execution error
type ToolError struct {
	Code    ErrorCode `json:"code"`
	Message string    `json:"message"`
	Details string    `json:"details,omitempty"`
}

// ErrorCode for categorizing errors
type ErrorCode int

const (
	ErrUnknown ErrorCode = iota
	ErrTimeout
	ErrToolNotFound
	ErrWorkerCrashed
	ErrPermissionDenied
	ErrInvalidArguments
)

// Supervisor manages workers and routes tool calls
type Supervisor struct {
	workers      map[string]*Worker
	toolToWorker map[string]*Worker
	config       Config
	mu           sync.RWMutex
	ctx          context.Context
	cancel       context.CancelFunc
}

// Config for supervisor behavior
type Config struct {
	DefaultTimeout  time.Duration
	MaxWorkers      int
	HeartbeatPeriod time.Duration
}

// New creates a new supervisor
func New(cfg Config) *Supervisor {
	if cfg.DefaultTimeout == 0 {
		cfg.DefaultTimeout = DefaultTimeout
	}
	if cfg.HeartbeatPeriod == 0 {
		cfg.HeartbeatPeriod = HeartbeatInterval
	}

	ctx, cancel := context.WithCancel(context.Background())

	s := &Supervisor{
		workers:      make(map[string]*Worker),
		toolToWorker: make(map[string]*Worker),
		config:       cfg,
		ctx:          ctx,
		cancel:       cancel,
	}

	go s.heartbeatLoop()

	return s
}

// RegisterWorker adds a worker to the supervisor
func (s *Supervisor) RegisterWorker(w *Worker) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.workers[w.ID] = w
	for _, tool := range w.Tools {
		s.toolToWorker[tool.Name] = w
	}

	return nil
}

// CallTool executes a tool with timeout enforcement
func (s *Supervisor) CallTool(ctx context.Context, call *ToolCall) *ToolResult {
	s.mu.RLock()
	worker, ok := s.toolToWorker[call.ToolName]
	s.mu.RUnlock()

	if !ok {
		return &ToolResult{
			Error: &ToolError{
				Code:    ErrToolNotFound,
				Message: fmt.Sprintf("tool not found: %s", call.ToolName),
			},
		}
	}

	// Determine timeout
	timeout := call.Timeout
	if timeout == 0 {
		timeout = s.config.DefaultTimeout
	}

	// Create timeout context
	timeoutCtx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	call.Started = time.Now()
	call.Done = make(chan *ToolResult, 1)

	// Execute in goroutine
	go s.executeCall(worker, call)

	// Wait for result or timeout
	select {
	case result := <-call.Done:
		result.Duration = time.Since(call.Started)
		return result
	case <-timeoutCtx.Done():
		return &ToolResult{
			Error: &ToolError{
				Code:    ErrTimeout,
				Message: fmt.Sprintf("tool call timed out after %s", timeout),
			},
			Duration: time.Since(call.Started),
		}
	}
}

// executeCall sends the call to the worker
func (s *Supervisor) executeCall(w *Worker, call *ToolCall) {
	// TODO: Implement actual IPC with worker process
	// For now, simulate execution
	result := &ToolResult{
		Output: json.RawMessage(`{"status": "ok", "message": "tool executed"}`),
	}
	call.Done <- result
}

// heartbeatLoop monitors worker health
func (s *Supervisor) heartbeatLoop() {
	ticker := time.NewTicker(s.config.HeartbeatPeriod)
	defer ticker.Stop()

	for {
		select {
		case <-s.ctx.Done():
			return
		case <-ticker.C:
			s.checkWorkerHealth()
		}
	}
}

// checkWorkerHealth pings all workers
func (s *Supervisor) checkWorkerHealth() {
	s.mu.RLock()
	workers := make([]*Worker, 0, len(s.workers))
	for _, w := range s.workers {
		workers = append(workers, w)
	}
	s.mu.RUnlock()

	for _, w := range workers {
		w.mu.Lock()
		// TODO: Actually ping the worker process
		w.healthy = w.Process != nil && w.Process.ProcessState == nil
		w.mu.Unlock()
	}
}

// ListTools returns all registered tools
func (s *Supervisor) ListTools() []ToolDef {
	s.mu.RLock()
	defer s.mu.RUnlock()

	var tools []ToolDef
	for _, w := range s.workers {
		tools = append(tools, w.Tools...)
	}
	return tools
}

// Shutdown gracefully stops the supervisor
func (s *Supervisor) Shutdown() {
	s.cancel()

	s.mu.Lock()
	defer s.mu.Unlock()

	for _, w := range s.workers {
		if w.Process != nil && w.Process.Process != nil {
			w.Process.Process.Signal(os.Interrupt)
		}
	}
}
