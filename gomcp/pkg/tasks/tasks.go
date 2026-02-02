// Package tasks provides async workflow support for MCP 2025-11-25.
// Tasks enable long-running operations with state tracking and progress updates.
package tasks

import (
	"context"
	"encoding/json"
	"fmt"
	"sync"
	"time"
)

// State represents task execution state
type State string

const (
	StateWorking       State = "working"
	StateInputRequired State = "input_required"
	StateCompleted     State = "completed"
	StateFailed        State = "failed"
	StateCancelled     State = "cancelled"
)

// Task represents an async task
type Task struct {
	ID          string         `json:"id"`
	State       State          `json:"state"`
	Progress    *Progress      `json:"progress,omitempty"`
	Result      any            `json:"result,omitempty"`
	Error       *TaskError     `json:"error,omitempty"`
	InputSchema *InputSchema   `json:"inputSchema,omitempty"`
	Metadata    map[string]any `json:"metadata,omitempty"`
	CreatedAt   time.Time      `json:"createdAt"`
	UpdatedAt   time.Time      `json:"updatedAt"`
}

// Progress tracks task progress
type Progress struct {
	Current int    `json:"current"`
	Total   int    `json:"total"`
	Message string `json:"message,omitempty"`
}

// TaskError represents a task failure
type TaskError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
	Data    any    `json:"data,omitempty"`
}

// InputSchema defines required user input
type InputSchema struct {
	Type       string              `json:"type"`
	Properties map[string]Property `json:"properties,omitempty"`
	Required   []string            `json:"required,omitempty"`
}

// Property defines a schema property
type Property struct {
	Type        string `json:"type"`
	Description string `json:"description,omitempty"`
}

// Handler processes async tasks
type Handler interface {
	// Execute runs the task
	Execute(ctx context.Context, task *Task) error
}

// HandlerFunc is a function adapter for Handler
type HandlerFunc func(ctx context.Context, task *Task) error

// Execute implements Handler
func (f HandlerFunc) Execute(ctx context.Context, task *Task) error {
	return f(ctx, task)
}

// Manager manages async tasks
type Manager struct {
	tasks    map[string]*Task
	handlers map[string]Handler
	mu       sync.RWMutex

	// Channels for notifications
	updates chan *Task
}

// NewManager creates a task manager
func NewManager() *Manager {
	return &Manager{
		tasks:    make(map[string]*Task),
		handlers: make(map[string]Handler),
		updates:  make(chan *Task, 100),
	}
}

// RegisterHandler registers a task handler
func (m *Manager) RegisterHandler(taskType string, handler Handler) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.handlers[taskType] = handler
}

// Create creates a new task
func (m *Manager) Create(taskType string, metadata map[string]any) (*Task, error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	id := generateTaskID()
	now := time.Now()

	task := &Task{
		ID:        id,
		State:     StateWorking,
		Metadata:  metadata,
		CreatedAt: now,
		UpdatedAt: now,
	}

	m.tasks[id] = task
	return task, nil
}

// Get retrieves a task by ID
func (m *Manager) Get(taskID string) (*Task, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	task, ok := m.tasks[taskID]
	if !ok {
		return nil, ErrTaskNotFound
	}

	return task, nil
}

// UpdateProgress updates task progress
func (m *Manager) UpdateProgress(taskID string, current, total int, message string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	task, ok := m.tasks[taskID]
	if !ok {
		return ErrTaskNotFound
	}

	task.Progress = &Progress{
		Current: current,
		Total:   total,
		Message: message,
	}
	task.UpdatedAt = time.Now()

	// Notify listeners
	select {
	case m.updates <- task:
	default:
	}

	return nil
}

// Complete marks task as completed
func (m *Manager) Complete(taskID string, result any) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	task, ok := m.tasks[taskID]
	if !ok {
		return ErrTaskNotFound
	}

	task.State = StateCompleted
	task.Result = result
	task.UpdatedAt = time.Now()

	select {
	case m.updates <- task:
	default:
	}

	return nil
}

// Fail marks task as failed
func (m *Manager) Fail(taskID string, code int, message string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	task, ok := m.tasks[taskID]
	if !ok {
		return ErrTaskNotFound
	}

	task.State = StateFailed
	task.Error = &TaskError{
		Code:    code,
		Message: message,
	}
	task.UpdatedAt = time.Now()

	select {
	case m.updates <- task:
	default:
	}

	return nil
}

// Cancel cancels a task
func (m *Manager) Cancel(taskID string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	task, ok := m.tasks[taskID]
	if !ok {
		return ErrTaskNotFound
	}

	task.State = StateCancelled
	task.UpdatedAt = time.Now()

	select {
	case m.updates <- task:
	default:
	}

	return nil
}

// RequestInput transitions task to input_required state
func (m *Manager) RequestInput(taskID string, schema *InputSchema) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	task, ok := m.tasks[taskID]
	if !ok {
		return ErrTaskNotFound
	}

	task.State = StateInputRequired
	task.InputSchema = schema
	task.UpdatedAt = time.Now()

	select {
	case m.updates <- task:
	default:
	}

	return nil
}

// ProvideInput provides input for a waiting task
func (m *Manager) ProvideInput(taskID string, input map[string]any) error {
	m.mu.Lock()
	task, ok := m.tasks[taskID]
	if !ok {
		m.mu.Unlock()
		return ErrTaskNotFound
	}

	if task.State != StateInputRequired {
		m.mu.Unlock()
		return ErrTaskNotWaiting
	}

	task.State = StateWorking
	task.InputSchema = nil
	task.UpdatedAt = time.Now()

	// Store input in metadata
	if task.Metadata == nil {
		task.Metadata = make(map[string]any)
	}
	task.Metadata["_lastInput"] = input
	m.mu.Unlock()

	select {
	case m.updates <- task:
	default:
	}

	return nil
}

// List returns all tasks
func (m *Manager) List() []*Task {
	m.mu.RLock()
	defer m.mu.RUnlock()

	result := make([]*Task, 0, len(m.tasks))
	for _, task := range m.tasks {
		result = append(result, task)
	}
	return result
}

// Updates returns the updates channel
func (m *Manager) Updates() <-chan *Task {
	return m.updates
}

// Delete removes a task
func (m *Manager) Delete(taskID string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if _, ok := m.tasks[taskID]; !ok {
		return ErrTaskNotFound
	}

	delete(m.tasks, taskID)
	return nil
}

// Cleanup removes old completed/failed/cancelled tasks
func (m *Manager) Cleanup(maxAge time.Duration) int {
	m.mu.Lock()
	defer m.mu.Unlock()

	cutoff := time.Now().Add(-maxAge)
	count := 0

	for id, task := range m.tasks {
		if task.State == StateCompleted || task.State == StateFailed || task.State == StateCancelled {
			if task.UpdatedAt.Before(cutoff) {
				delete(m.tasks, id)
				count++
			}
		}
	}

	return count
}

// Errors
var (
	ErrTaskNotFound   = fmt.Errorf("task not found")
	ErrTaskNotWaiting = fmt.Errorf("task is not waiting for input")
)

// JSON-RPC method names
const (
	MethodTaskCreate = "tasks/create"
	MethodTaskGet    = "tasks/get"
	MethodTaskCancel = "tasks/cancel"
	MethodTaskStatus = "tasks/status"
)

// generateTaskID creates a unique task ID
var taskIDCounter uint64

func generateTaskID() string {
	taskIDCounter++
	return fmt.Sprintf("task_%d_%d", time.Now().UnixNano(), taskIDCounter)
}

// ToJSON serializes task to JSON
func (t *Task) ToJSON() ([]byte, error) {
	return json.Marshal(t)
}

// IsTerminal returns true if task is in a terminal state
func (t *Task) IsTerminal() bool {
	return t.State == StateCompleted || t.State == StateFailed || t.State == StateCancelled
}

// IsActive returns true if task is still running
func (t *Task) IsActive() bool {
	return t.State == StateWorking || t.State == StateInputRequired
}
