// Package pythonbridge provides a persistent Python process for RLM tools.
// This enables GoMCP to delegate Python-specific operations without spawning
// a new process for each call.
package pythonbridge

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os/exec"
	"sync"
	"time"
)

// Bridge manages a long-running Python process for tool execution
type Bridge struct {
	pythonPath  string
	workerPath  string
	projectRoot string

	process *exec.Cmd
	stdin   io.WriteCloser
	stdout  *bufio.Reader

	mu        sync.Mutex
	started   bool
	lastError error

	requestID uint64
	pending   map[uint64]chan *Response
	pendingMu sync.Mutex
}

// Request represents a tool call to Python
type Request struct {
	ID     uint64         `json:"id"`
	Tool   string         `json:"tool"`
	Params map[string]any `json:"params"`
}

// Response represents Python tool result
type Response struct {
	ID      uint64         `json:"id"`
	Success bool           `json:"success"`
	Result  map[string]any `json:"result,omitempty"`
	Error   string         `json:"error,omitempty"`
}

// Config for bridge initialization
type Config struct {
	PythonPath  string
	WorkerPath  string
	ProjectRoot string
}

// New creates a new Python bridge
func New(cfg Config) *Bridge {
	if cfg.PythonPath == "" {
		cfg.PythonPath = "python"
	}
	return &Bridge{
		pythonPath:  cfg.PythonPath,
		workerPath:  cfg.WorkerPath,
		projectRoot: cfg.ProjectRoot,
		pending:     make(map[uint64]chan *Response),
	}
}

// Start starts the Python worker process
func (b *Bridge) Start(ctx context.Context) error {
	b.mu.Lock()
	defer b.mu.Unlock()

	if b.started {
		return nil
	}

	b.process = exec.CommandContext(ctx, b.pythonPath, b.workerPath)
	b.process.Dir = b.projectRoot

	var err error
	b.stdin, err = b.process.StdinPipe()
	if err != nil {
		return fmt.Errorf("stdin pipe: %w", err)
	}

	stdout, err := b.process.StdoutPipe()
	if err != nil {
		return fmt.Errorf("stdout pipe: %w", err)
	}
	b.stdout = bufio.NewReader(stdout)

	if err := b.process.Start(); err != nil {
		return fmt.Errorf("start process: %w", err)
	}

	b.started = true

	// Start response reader
	go b.readResponses()

	return nil
}

// Call executes a Python tool and returns the result
func (b *Bridge) Call(ctx context.Context, tool string, params map[string]any) (*Response, error) {
	b.mu.Lock()
	if !b.started {
		b.mu.Unlock()
		return nil, ErrNotStarted
	}
	b.mu.Unlock()

	// Create request
	b.pendingMu.Lock()
	b.requestID++
	id := b.requestID
	respChan := make(chan *Response, 1)
	b.pending[id] = respChan
	b.pendingMu.Unlock()

	defer func() {
		b.pendingMu.Lock()
		delete(b.pending, id)
		b.pendingMu.Unlock()
	}()

	req := Request{
		ID:     id,
		Tool:   tool,
		Params: params,
	}

	// Send request
	data, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("marshal request: %w", err)
	}

	b.mu.Lock()
	_, err = b.stdin.Write(append(data, '\n'))
	b.mu.Unlock()
	if err != nil {
		return nil, fmt.Errorf("write request: %w", err)
	}

	// Wait for response
	select {
	case resp := <-respChan:
		return resp, nil
	case <-ctx.Done():
		return nil, ctx.Err()
	case <-time.After(5 * time.Minute):
		return nil, ErrTimeout
	}
}

// readResponses reads responses from Python worker
func (b *Bridge) readResponses() {
	for {
		line, err := b.stdout.ReadBytes('\n')
		if err != nil {
			b.mu.Lock()
			b.lastError = err
			b.started = false
			b.mu.Unlock()
			return
		}

		var resp Response
		if err := json.Unmarshal(line, &resp); err != nil {
			continue
		}

		b.pendingMu.Lock()
		if ch, ok := b.pending[resp.ID]; ok {
			ch <- &resp
		}
		b.pendingMu.Unlock()
	}
}

// Stop stops the Python process
func (b *Bridge) Stop() error {
	b.mu.Lock()
	defer b.mu.Unlock()

	if !b.started {
		return nil
	}

	b.stdin.Close()
	b.started = false

	if b.process != nil && b.process.Process != nil {
		return b.process.Process.Kill()
	}
	return nil
}

// IsRunning returns true if the bridge is running
func (b *Bridge) IsRunning() bool {
	b.mu.Lock()
	defer b.mu.Unlock()
	return b.started
}

// LastError returns the last error
func (b *Bridge) LastError() error {
	b.mu.Lock()
	defer b.mu.Unlock()
	return b.lastError
}

// Errors
var (
	ErrNotStarted = fmt.Errorf("python bridge not started")
	ErrTimeout    = fmt.Errorf("python bridge call timeout")
)
