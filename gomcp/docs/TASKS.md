# Tasks Module

> Async workflow support for MCP Protocol 2025-11-25

## Overview

The `tasks` module provides async task management with state tracking, progress updates, and lifecycle management. This enables long-running operations that can report progress and request user input.

## Installation

```go
import "github.com/sentinel-community/gomcp/pkg/tasks"
```

## Quick Start

```go
// Create manager
manager := tasks.NewManager()

// Create task
task, _ := manager.Create("process_data", map[string]any{
    "input": "data.csv",
})

// Update progress
manager.UpdateProgress(task.ID, 50, 100, "Processing...")

// Complete
manager.Complete(task.ID, map[string]any{"rows": 1000})
```

## API Reference

### Manager

```go
func NewManager() *Manager
```
Creates a new task manager.

---

```go
func (m *Manager) Create(taskType string, metadata map[string]any) (*Task, error)
```
Creates a new task with the given type and metadata. Returns task in `working` state.

---

```go
func (m *Manager) Get(id string) (*Task, error)
```
Retrieves a task by ID. Returns `ErrTaskNotFound` if not found.

---

```go
func (m *Manager) List() []*Task
```
Returns all active tasks.

---

```go
func (m *Manager) UpdateProgress(id string, current, total int, message string) error
```
Updates task progress. The `current`/`total` ratio determines percentage.

---

```go
func (m *Manager) Complete(id string, result any) error
```
Marks task as completed with result data.

---

```go
func (m *Manager) Fail(id string, code int, message string) error
```
Marks task as failed with error code and message.

---

```go
func (m *Manager) Cancel(id string) error
```
Cancels a running task.

---

```go
func (m *Manager) RequestInput(id string, inputType string, schema map[string]any) error
```
Puts task into `input_required` state for user input.

---

```go
func (m *Manager) ProvideInput(id string, input any) error
```
Provides input and resumes task to `working` state.

---

```go
func (m *Manager) Updates() <-chan *Task
```
Returns channel for task update notifications.

---

```go
func (m *Manager) Cleanup(maxAge time.Duration) int
```
Removes terminal tasks older than maxAge. Returns count removed.

### Task States

| State | Description |
|-------|-------------|
| `working` | Task is actively processing |
| `input_required` | Waiting for user input |
| `completed` | Successfully finished |
| `failed` | Failed with error |
| `cancelled` | Cancelled by user |

### Task Structure

```go
type Task struct {
    ID        string
    Type      string
    State     TaskState
    Metadata  map[string]any
    Progress  *Progress
    Result    any
    Error     *TaskError
    CreatedAt time.Time
    UpdatedAt time.Time
}
```

## JSON-RPC Methods

| Method | Description |
|--------|-------------|
| `tasks/create` | Create new task |
| `tasks/get` | Get task by ID |
| `tasks/list` | List all tasks |
| `tasks/cancel` | Cancel a task |
| `notifications/tasks/progress` | Progress update notification |

## Examples

See [examples/tasks/](../examples/tasks/) for complete examples.
