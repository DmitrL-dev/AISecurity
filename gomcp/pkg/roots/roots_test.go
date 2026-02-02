package roots

import (
	"sync"
	"testing"
	"time"
)

func TestManager_Add(t *testing.T) {
	m := NewManager()

	err := m.Add("file:///home/user/project", "Project")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if m.Count() != 1 {
		t.Errorf("expected 1 root, got %d", m.Count())
	}
}

func TestManager_Add_EmptyURI(t *testing.T) {
	m := NewManager()

	err := m.Add("", "Name")
	if err != ErrEmptyURI {
		t.Errorf("expected ErrEmptyURI, got %v", err)
	}
}

func TestManager_Remove(t *testing.T) {
	m := NewManager()

	m.Add("file:///home/user", "User")

	err := m.Remove("file:///home/user")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if m.Count() != 0 {
		t.Error("root should be removed")
	}
}

func TestManager_Remove_NotFound(t *testing.T) {
	m := NewManager()

	err := m.Remove("nonexistent")
	if err != ErrRootNotFound {
		t.Errorf("expected ErrRootNotFound, got %v", err)
	}
}

func TestManager_Get(t *testing.T) {
	m := NewManager()

	m.Add("file:///path", "Path")

	root, err := m.Get("file:///path")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if root.URI != "file:///path" {
		t.Error("URI mismatch")
	}

	if root.Name != "Path" {
		t.Error("name mismatch")
	}
}

func TestManager_Get_NotFound(t *testing.T) {
	m := NewManager()

	_, err := m.Get("nonexistent")
	if err != ErrRootNotFound {
		t.Errorf("expected ErrRootNotFound, got %v", err)
	}
}

func TestManager_List(t *testing.T) {
	m := NewManager()

	m.Add("file:///a", "A")
	m.Add("file:///b", "B")
	m.Add("file:///c", "C")

	roots := m.List()
	if len(roots) != 3 {
		t.Errorf("expected 3 roots, got %d", len(roots))
	}
}

func TestManager_Clear(t *testing.T) {
	m := NewManager()

	m.Add("file:///a", "A")
	m.Add("file:///b", "B")

	m.Clear()

	if m.Count() != 0 {
		t.Errorf("expected 0 roots after clear, got %d", m.Count())
	}
}

func TestManager_Contains(t *testing.T) {
	m := NewManager()

	m.Add("file:///home/user/project", "Project")

	if !m.Contains("file:///home/user/project") {
		t.Error("should contain exact root")
	}

	if !m.Contains("file:///home/user/project/src") {
		t.Error("should contain path within root")
	}

	if m.Contains("file:///other") {
		t.Error("should not contain path outside roots")
	}
}

func TestManager_OnChange(t *testing.T) {
	m := NewManager()

	var called bool
	var mu sync.Mutex

	m.OnChange(func(roots []*Root) {
		mu.Lock()
		called = true
		mu.Unlock()
	})

	m.Add("file:///test", "Test")

	time.Sleep(10 * time.Millisecond)

	mu.Lock()
	if !called {
		t.Error("onChange should be called")
	}
	mu.Unlock()
}

func TestManager_ToJSON(t *testing.T) {
	m := NewManager()

	m.Add("file:///path", "Path")

	data, err := m.ToJSON()
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if len(data) == 0 {
		t.Error("JSON should not be empty")
	}
}

func TestConstants(t *testing.T) {
	if MethodRootsList != "roots/list" {
		t.Error("invalid method")
	}

	if NotifyRootsChanged != "notifications/roots/list_changed" {
		t.Error("invalid notification")
	}
}

func TestRoot_Fields(t *testing.T) {
	root := &Root{
		URI:  "file:///test",
		Name: "Test",
	}

	if root.URI != "file:///test" {
		t.Error("URI field mismatch")
	}

	if root.Name != "Test" {
		t.Error("Name field mismatch")
	}
}
