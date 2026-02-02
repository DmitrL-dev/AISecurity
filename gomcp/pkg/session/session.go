// Package session provides per-session state and tool management for MCP.
// Sessions enable isolated tool registration and context propagation per client.
package session

import (
	"context"
	"encoding/json"
	"fmt"
	"sync"
	"time"
)

// Session represents a client session with isolated state
type Session struct {
	ID           string         `json:"id"`
	ClientInfo   *ClientInfo    `json:"clientInfo,omitempty"`
	Capabilities map[string]any `json:"capabilities,omitempty"`
	Tools        []string       `json:"tools,omitempty"`
	Metadata     map[string]any `json:"metadata,omitempty"`
	CreatedAt    time.Time      `json:"createdAt"`
	LastActive   time.Time      `json:"lastActive"`

	mu      sync.RWMutex
	tools   map[string]bool
	context map[string]any
}

// ClientInfo contains client identification
type ClientInfo struct {
	Name    string `json:"name"`
	Version string `json:"version"`
}

// Manager manages multiple sessions
type Manager struct {
	sessions map[string]*Session
	mu       sync.RWMutex

	// Callbacks
	onSessionStart func(*Session)
	onSessionEnd   func(*Session)
}

// NewManager creates a session manager
func NewManager() *Manager {
	return &Manager{
		sessions: make(map[string]*Session),
	}
}

// Create creates a new session
func (m *Manager) Create(id string, clientInfo *ClientInfo) (*Session, error) {
	if id == "" {
		return nil, ErrEmptySessionID
	}

	m.mu.Lock()
	defer m.mu.Unlock()

	if _, exists := m.sessions[id]; exists {
		return nil, ErrSessionExists
	}

	session := &Session{
		ID:         id,
		ClientInfo: clientInfo,
		CreatedAt:  time.Now(),
		LastActive: time.Now(),
		tools:      make(map[string]bool),
		context:    make(map[string]any),
		Metadata:   make(map[string]any),
	}

	m.sessions[id] = session

	if m.onSessionStart != nil {
		go m.onSessionStart(session)
	}

	return session, nil
}

// Get retrieves a session by ID
func (m *Manager) Get(id string) (*Session, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	session, ok := m.sessions[id]
	if !ok {
		return nil, ErrSessionNotFound
	}

	return session, nil
}

// Delete removes a session
func (m *Manager) Delete(id string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	session, ok := m.sessions[id]
	if !ok {
		return ErrSessionNotFound
	}

	delete(m.sessions, id)

	if m.onSessionEnd != nil {
		go m.onSessionEnd(session)
	}

	return nil
}

// List returns all active sessions
func (m *Manager) List() []*Session {
	m.mu.RLock()
	defer m.mu.RUnlock()

	result := make([]*Session, 0, len(m.sessions))
	for _, s := range m.sessions {
		result = append(result, s)
	}
	return result
}

// Count returns number of active sessions
func (m *Manager) Count() int {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return len(m.sessions)
}

// OnSessionStart sets callback for new sessions
func (m *Manager) OnSessionStart(fn func(*Session)) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.onSessionStart = fn
}

// OnSessionEnd sets callback for ended sessions
func (m *Manager) OnSessionEnd(fn func(*Session)) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.onSessionEnd = fn
}

// Cleanup removes sessions older than maxAge
func (m *Manager) Cleanup(maxAge time.Duration) int {
	m.mu.Lock()
	defer m.mu.Unlock()

	cutoff := time.Now().Add(-maxAge)
	count := 0

	for id, s := range m.sessions {
		if s.LastActive.Before(cutoff) {
			delete(m.sessions, id)
			count++
		}
	}

	return count
}

// Session methods

// RegisterTool adds a tool to this session
func (s *Session) RegisterTool(name string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.tools[name] = true
	s.LastActive = time.Now()
}

// UnregisterTool removes a tool from this session
func (s *Session) UnregisterTool(name string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	delete(s.tools, name)
	s.LastActive = time.Now()
}

// HasTool checks if session has access to a tool
func (s *Session) HasTool(name string) bool {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.tools[name]
}

// GetTools returns all registered tools
func (s *Session) GetTools() []string {
	s.mu.RLock()
	defer s.mu.RUnlock()

	result := make([]string, 0, len(s.tools))
	for name := range s.tools {
		result = append(result, name)
	}
	return result
}

// SetContext sets a context value
func (s *Session) SetContext(key string, value any) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.context[key] = value
	s.LastActive = time.Now()
}

// GetContext gets a context value
func (s *Session) GetContext(key string) (any, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	val, ok := s.context[key]
	return val, ok
}

// ClearContext removes all context values
func (s *Session) ClearContext() {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.context = make(map[string]any)
	s.LastActive = time.Now()
}

// Touch updates LastActive timestamp
func (s *Session) Touch() {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.LastActive = time.Now()
}

// ToJSON serializes session to JSON
func (s *Session) ToJSON() ([]byte, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	// Build tools list
	tools := make([]string, 0, len(s.tools))
	for name := range s.tools {
		tools = append(tools, name)
	}

	export := struct {
		ID         string      `json:"id"`
		ClientInfo *ClientInfo `json:"clientInfo,omitempty"`
		Tools      []string    `json:"tools"`
		CreatedAt  time.Time   `json:"createdAt"`
		LastActive time.Time   `json:"lastActive"`
	}{
		ID:         s.ID,
		ClientInfo: s.ClientInfo,
		Tools:      tools,
		CreatedAt:  s.CreatedAt,
		LastActive: s.LastActive,
	}

	return json.Marshal(export)
}

// Context key for session
type contextKey struct{}

// WithSession adds session to context
func WithSession(ctx context.Context, s *Session) context.Context {
	return context.WithValue(ctx, contextKey{}, s)
}

// FromContext extracts session from context
func FromContext(ctx context.Context) (*Session, bool) {
	s, ok := ctx.Value(contextKey{}).(*Session)
	return s, ok
}

// Errors
var (
	ErrEmptySessionID  = fmt.Errorf("session ID cannot be empty")
	ErrSessionExists   = fmt.Errorf("session already exists")
	ErrSessionNotFound = fmt.Errorf("session not found")
)
