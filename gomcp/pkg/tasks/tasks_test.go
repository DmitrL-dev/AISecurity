package tasks

import (
	"context"
	"testing"
	"time"
)

func TestManager_Create(t *testing.T) {
	m := NewManager()

	task, err := m.Create("test", map[string]any{"key": "value"})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if task.ID == "" {
		t.Error("task ID should not be empty")
	}

	if task.State != StateWorking {
		t.Errorf("expected working state, got %s", task.State)
	}

	if task.Metadata["key"] != "value" {
		t.Error("metadata not preserved")
	}
}

func TestManager_Get(t *testing.T) {
	m := NewManager()

	created, _ := m.Create("test", nil)

	task, err := m.Get(created.ID)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if task.ID != created.ID {
		t.Error("task ID mismatch")
	}
}

func TestManager_Get_NotFound(t *testing.T) {
	m := NewManager()

	_, err := m.Get("nonexistent")
	if err != ErrTaskNotFound {
		t.Errorf("expected ErrTaskNotFound, got %v", err)
	}
}

func TestManager_UpdateProgress(t *testing.T) {
	m := NewManager()

	task, _ := m.Create("test", nil)

	err := m.UpdateProgress(task.ID, 5, 10, "halfway")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	updated, _ := m.Get(task.ID)
	if updated.Progress == nil {
		t.Fatal("progress should not be nil")
	}

	if updated.Progress.Current != 5 {
		t.Errorf("expected current 5, got %d", updated.Progress.Current)
	}

	if updated.Progress.Total != 10 {
		t.Errorf("expected total 10, got %d", updated.Progress.Total)
	}

	if updated.Progress.Message != "halfway" {
		t.Error("message mismatch")
	}
}

func TestManager_Complete(t *testing.T) {
	m := NewManager()

	task, _ := m.Create("test", nil)

	err := m.Complete(task.ID, "result data")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	completed, _ := m.Get(task.ID)
	if completed.State != StateCompleted {
		t.Errorf("expected completed, got %s", completed.State)
	}

	if completed.Result != "result data" {
		t.Error("result mismatch")
	}

	if !completed.IsTerminal() {
		t.Error("completed task should be terminal")
	}
}

func TestManager_Fail(t *testing.T) {
	m := NewManager()

	task, _ := m.Create("test", nil)

	err := m.Fail(task.ID, 500, "internal error")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	failed, _ := m.Get(task.ID)
	if failed.State != StateFailed {
		t.Errorf("expected failed, got %s", failed.State)
	}

	if failed.Error == nil {
		t.Fatal("error should not be nil")
	}

	if failed.Error.Code != 500 {
		t.Errorf("expected error code 500, got %d", failed.Error.Code)
	}
}

func TestManager_Cancel(t *testing.T) {
	m := NewManager()

	task, _ := m.Create("test", nil)

	err := m.Cancel(task.ID)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	cancelled, _ := m.Get(task.ID)
	if cancelled.State != StateCancelled {
		t.Errorf("expected cancelled, got %s", cancelled.State)
	}
}

func TestManager_RequestInput(t *testing.T) {
	m := NewManager()

	task, _ := m.Create("test", nil)

	schema := &InputSchema{
		Type:     "object",
		Required: []string{"name"},
	}

	err := m.RequestInput(task.ID, schema)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	waiting, _ := m.Get(task.ID)
	if waiting.State != StateInputRequired {
		t.Errorf("expected input_required, got %s", waiting.State)
	}

	if waiting.InputSchema == nil {
		t.Error("input schema should not be nil")
	}
}

func TestManager_ProvideInput(t *testing.T) {
	m := NewManager()

	task, _ := m.Create("test", nil)
	m.RequestInput(task.ID, &InputSchema{Type: "object"})

	err := m.ProvideInput(task.ID, map[string]any{"name": "John"})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	resumed, _ := m.Get(task.ID)
	if resumed.State != StateWorking {
		t.Errorf("expected working, got %s", resumed.State)
	}

	if resumed.InputSchema != nil {
		t.Error("input schema should be cleared")
	}
}

func TestManager_ProvideInput_NotWaiting(t *testing.T) {
	m := NewManager()

	task, _ := m.Create("test", nil)

	err := m.ProvideInput(task.ID, map[string]any{})
	if err != ErrTaskNotWaiting {
		t.Errorf("expected ErrTaskNotWaiting, got %v", err)
	}
}

func TestManager_List(t *testing.T) {
	m := NewManager()

	m.Create("test1", nil)
	m.Create("test2", nil)
	m.Create("test3", nil)

	tasks := m.List()
	if len(tasks) != 3 {
		t.Errorf("expected 3 tasks, got %d", len(tasks))
	}
}

func TestManager_Delete(t *testing.T) {
	m := NewManager()

	task, _ := m.Create("test", nil)

	err := m.Delete(task.ID)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	_, err = m.Get(task.ID)
	if err != ErrTaskNotFound {
		t.Error("task should be deleted")
	}
}

func TestManager_Cleanup(t *testing.T) {
	m := NewManager()

	task1, _ := m.Create("test1", nil)
	task2, _ := m.Create("test2", nil)
	_, _ = m.Create("test3", nil)

	m.Complete(task1.ID, nil)
	m.Fail(task2.ID, 500, "error")
	// task3 stays working

	// Sleep briefly so tasks are "old"
	time.Sleep(10 * time.Millisecond)

	// Cleanup with small duration should remove completed/failed
	count := m.Cleanup(5 * time.Millisecond)
	if count != 2 {
		t.Errorf("expected 2 cleaned, got %d", count)
	}

	tasks := m.List()
	if len(tasks) != 1 {
		t.Errorf("expected 1 remaining task, got %d", len(tasks))
	}
}

func TestTask_IsTerminal(t *testing.T) {
	tests := []struct {
		state    State
		terminal bool
	}{
		{StateWorking, false},
		{StateInputRequired, false},
		{StateCompleted, true},
		{StateFailed, true},
		{StateCancelled, true},
	}

	for _, tc := range tests {
		task := &Task{State: tc.state}
		if task.IsTerminal() != tc.terminal {
			t.Errorf("state %s: expected terminal=%v", tc.state, tc.terminal)
		}
	}
}

func TestTask_IsActive(t *testing.T) {
	tests := []struct {
		state  State
		active bool
	}{
		{StateWorking, true},
		{StateInputRequired, true},
		{StateCompleted, false},
		{StateFailed, false},
		{StateCancelled, false},
	}

	for _, tc := range tests {
		task := &Task{State: tc.state}
		if task.IsActive() != tc.active {
			t.Errorf("state %s: expected active=%v", tc.state, tc.active)
		}
	}
}

func TestTask_ToJSON(t *testing.T) {
	task := &Task{
		ID:    "test-123",
		State: StateWorking,
	}

	data, err := task.ToJSON()
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if len(data) == 0 {
		t.Error("JSON should not be empty")
	}
}

func TestHandlerFunc(t *testing.T) {
	called := false

	hf := HandlerFunc(func(ctx context.Context, task *Task) error {
		called = true
		return nil
	})

	err := hf.Execute(context.Background(), &Task{})
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}

	if !called {
		t.Error("handler not called")
	}
}

func TestManager_Updates(t *testing.T) {
	m := NewManager()

	ch := m.Updates()
	if ch == nil {
		t.Error("updates channel should not be nil")
	}
}

func TestConstants(t *testing.T) {
	if MethodTaskCreate != "tasks/create" {
		t.Error("invalid method")
	}

	if MethodTaskGet != "tasks/get" {
		t.Error("invalid method")
	}

	if StateWorking != "working" {
		t.Error("invalid state")
	}

	if StateCompleted != "completed" {
		t.Error("invalid state")
	}
}

func TestGenerateTaskID(t *testing.T) {
	id1 := generateTaskID()
	time.Sleep(time.Nanosecond)
	id2 := generateTaskID()

	if id1 == id2 {
		t.Error("task IDs should be unique")
	}
}
