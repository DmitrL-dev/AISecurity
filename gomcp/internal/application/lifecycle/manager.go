// Package lifecycle manages graceful shutdown with auto-save of session state,
// cache flush, and database closure.
package lifecycle

import (
	"context"
	"io"
	"log"
	"sync"
	"time"
)

// ShutdownFunc is a function called during graceful shutdown.
// Name is used for logging. The function receives a context with a deadline.
type ShutdownFunc struct {
	Name string
	Fn   func(ctx context.Context) error
}

// Manager orchestrates graceful shutdown of all resources.
type Manager struct {
	mu      sync.Mutex
	hooks   []ShutdownFunc
	timeout time.Duration
	done    bool
}

// NewManager creates a new lifecycle Manager.
// Timeout is the maximum time allowed for all shutdown hooks to complete.
func NewManager(timeout time.Duration) *Manager {
	if timeout <= 0 {
		timeout = 10 * time.Second
	}
	return &Manager{
		timeout: timeout,
	}
}

// OnShutdown registers a shutdown hook. Hooks are called in LIFO order
// (last registered = first called), matching defer semantics.
func (m *Manager) OnShutdown(name string, fn func(ctx context.Context) error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.hooks = append(m.hooks, ShutdownFunc{Name: name, Fn: fn})
}

// OnClose registers an io.Closer as a shutdown hook.
func (m *Manager) OnClose(name string, c io.Closer) {
	m.OnShutdown(name, func(_ context.Context) error {
		return c.Close()
	})
}

// Shutdown executes all registered hooks in reverse order (LIFO).
// It logs each step and any errors. Returns the first error encountered.
func (m *Manager) Shutdown() error {
	m.mu.Lock()
	if m.done {
		m.mu.Unlock()
		return nil
	}
	m.done = true
	hooks := make([]ShutdownFunc, len(m.hooks))
	copy(hooks, m.hooks)
	m.mu.Unlock()

	ctx, cancel := context.WithTimeout(context.Background(), m.timeout)
	defer cancel()

	log.Printf("Graceful shutdown started (%d hooks, timeout %s)", len(hooks), m.timeout)

	var firstErr error
	// Execute in reverse order (LIFO).
	for i := len(hooks) - 1; i >= 0; i-- {
		h := hooks[i]
		log.Printf("  shutdown: %s", h.Name)
		if err := h.Fn(ctx); err != nil {
			log.Printf("  shutdown %s: ERROR: %v", h.Name, err)
			if firstErr == nil {
				firstErr = err
			}
		}
	}

	log.Printf("Graceful shutdown complete")
	return firstErr
}

// Done returns true if Shutdown has already been called.
func (m *Manager) Done() bool {
	m.mu.Lock()
	defer m.mu.Unlock()
	return m.done
}
