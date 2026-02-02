package session

import (
	"context"
	"sync"
	"testing"
	"time"
)

func TestManager_Create(t *testing.T) {
	m := NewManager()

	s, err := m.Create("sess1", &ClientInfo{Name: "test", Version: "1.0"})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if s.ID != "sess1" {
		t.Error("ID mismatch")
	}

	if s.ClientInfo.Name != "test" {
		t.Error("ClientInfo mismatch")
	}
}

func TestManager_Create_EmptyID(t *testing.T) {
	m := NewManager()

	_, err := m.Create("", nil)
	if err != ErrEmptySessionID {
		t.Errorf("expected ErrEmptySessionID, got %v", err)
	}
}

func TestManager_Create_Duplicate(t *testing.T) {
	m := NewManager()

	m.Create("sess1", nil)
	_, err := m.Create("sess1", nil)
	if err != ErrSessionExists {
		t.Errorf("expected ErrSessionExists, got %v", err)
	}
}

func TestManager_Get(t *testing.T) {
	m := NewManager()
	m.Create("sess1", nil)

	s, err := m.Get("sess1")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if s.ID != "sess1" {
		t.Error("ID mismatch")
	}
}

func TestManager_Get_NotFound(t *testing.T) {
	m := NewManager()

	_, err := m.Get("nonexistent")
	if err != ErrSessionNotFound {
		t.Errorf("expected ErrSessionNotFound, got %v", err)
	}
}

func TestManager_Delete(t *testing.T) {
	m := NewManager()
	m.Create("sess1", nil)

	err := m.Delete("sess1")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if m.Count() != 0 {
		t.Error("session should be deleted")
	}
}

func TestManager_Delete_NotFound(t *testing.T) {
	m := NewManager()

	err := m.Delete("nonexistent")
	if err != ErrSessionNotFound {
		t.Errorf("expected ErrSessionNotFound, got %v", err)
	}
}

func TestManager_List(t *testing.T) {
	m := NewManager()

	m.Create("sess1", nil)
	m.Create("sess2", nil)
	m.Create("sess3", nil)

	sessions := m.List()
	if len(sessions) != 3 {
		t.Errorf("expected 3 sessions, got %d", len(sessions))
	}
}

func TestManager_Count(t *testing.T) {
	m := NewManager()

	m.Create("sess1", nil)
	m.Create("sess2", nil)

	if m.Count() != 2 {
		t.Errorf("expected 2, got %d", m.Count())
	}
}

func TestManager_OnSessionStart(t *testing.T) {
	m := NewManager()

	var started bool
	var mu sync.Mutex

	m.OnSessionStart(func(s *Session) {
		mu.Lock()
		started = true
		mu.Unlock()
	})

	m.Create("sess1", nil)
	time.Sleep(10 * time.Millisecond)

	mu.Lock()
	if !started {
		t.Error("OnSessionStart should be called")
	}
	mu.Unlock()
}

func TestManager_OnSessionEnd(t *testing.T) {
	m := NewManager()

	var ended bool
	var mu sync.Mutex

	m.OnSessionEnd(func(s *Session) {
		mu.Lock()
		ended = true
		mu.Unlock()
	})

	m.Create("sess1", nil)
	m.Delete("sess1")
	time.Sleep(10 * time.Millisecond)

	mu.Lock()
	if !ended {
		t.Error("OnSessionEnd should be called")
	}
	mu.Unlock()
}

func TestManager_Cleanup(t *testing.T) {
	m := NewManager()

	s1, _ := m.Create("sess1", nil)
	s2, _ := m.Create("sess2", nil)
	m.Create("sess3", nil)

	// Make sess1 and sess2 old
	s1.LastActive = time.Now().Add(-time.Hour)
	s2.LastActive = time.Now().Add(-time.Hour)

	count := m.Cleanup(30 * time.Minute)
	if count != 2 {
		t.Errorf("expected 2 cleaned, got %d", count)
	}

	if m.Count() != 1 {
		t.Errorf("expected 1 remaining, got %d", m.Count())
	}
}

func TestSession_RegisterTool(t *testing.T) {
	s := &Session{
		tools: make(map[string]bool),
	}

	s.RegisterTool("tool1")
	s.RegisterTool("tool2")

	if !s.HasTool("tool1") {
		t.Error("should have tool1")
	}

	if s.HasTool("tool3") {
		t.Error("should not have tool3")
	}
}

func TestSession_UnregisterTool(t *testing.T) {
	s := &Session{
		tools: make(map[string]bool),
	}

	s.RegisterTool("tool1")
	s.UnregisterTool("tool1")

	if s.HasTool("tool1") {
		t.Error("tool1 should be unregistered")
	}
}

func TestSession_GetTools(t *testing.T) {
	s := &Session{
		tools: make(map[string]bool),
	}

	s.RegisterTool("tool1")
	s.RegisterTool("tool2")

	tools := s.GetTools()
	if len(tools) != 2 {
		t.Errorf("expected 2 tools, got %d", len(tools))
	}
}

func TestSession_Context(t *testing.T) {
	s := &Session{
		context: make(map[string]any),
	}

	s.SetContext("user", "john")

	val, ok := s.GetContext("user")
	if !ok || val != "john" {
		t.Error("context value mismatch")
	}

	_, ok = s.GetContext("nonexistent")
	if ok {
		t.Error("should not find nonexistent key")
	}
}

func TestSession_ClearContext(t *testing.T) {
	s := &Session{
		context: make(map[string]any),
	}

	s.SetContext("a", 1)
	s.SetContext("b", 2)
	s.ClearContext()

	_, ok := s.GetContext("a")
	if ok {
		t.Error("context should be cleared")
	}
}

func TestSession_Touch(t *testing.T) {
	s := &Session{
		LastActive: time.Now().Add(-time.Hour),
	}

	s.Touch()

	if time.Since(s.LastActive) > time.Second {
		t.Error("LastActive should be updated")
	}
}

func TestSession_ToJSON(t *testing.T) {
	s := &Session{
		ID:         "sess1",
		ClientInfo: &ClientInfo{Name: "test", Version: "1.0"},
		CreatedAt:  time.Now(),
		LastActive: time.Now(),
		tools:      make(map[string]bool),
	}

	data, err := s.ToJSON()
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if len(data) == 0 {
		t.Error("JSON should not be empty")
	}
}

func TestWithSession_FromContext(t *testing.T) {
	s := &Session{ID: "sess1"}

	ctx := WithSession(context.Background(), s)

	extracted, ok := FromContext(ctx)
	if !ok {
		t.Error("should find session in context")
	}

	if extracted.ID != "sess1" {
		t.Error("ID mismatch")
	}
}

func TestFromContext_Empty(t *testing.T) {
	_, ok := FromContext(context.Background())
	if ok {
		t.Error("should not find session in empty context")
	}
}

func TestErrors(t *testing.T) {
	if ErrEmptySessionID.Error() == "" {
		t.Error("error should have message")
	}

	if ErrSessionExists.Error() == "" {
		t.Error("error should have message")
	}

	if ErrSessionNotFound.Error() == "" {
		t.Error("error should have message")
	}
}
