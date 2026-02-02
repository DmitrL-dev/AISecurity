# Session Module

> Per-session state and tool management for MCP

## Overview

The `session` module provides client session isolation with per-session tool registration, context propagation, and lifecycle callbacks.

## Installation

```go
import "github.com/sentinel-community/gomcp/pkg/session"
```

## Quick Start

```go
manager := session.NewManager()

// Create session
sess, _ := manager.Create("client-123", &session.ClientInfo{
    Name:    "my-client",
    Version: "1.0.0",
})

// Register tools for this session
sess.RegisterTool("calculator")
sess.RegisterTool("file_reader")

// Set session context
sess.SetContext("user_id", "user-456")
sess.SetContext("role", "admin")

// Use in request handling
ctx := session.WithSession(ctx, sess)

// Later, extract session
if s, ok := session.FromContext(ctx); ok {
    if s.HasTool("calculator") {
        // Allow tool call
    }
}
```

## API Reference

### Manager

```go
func NewManager() *Manager
func (m *Manager) Create(id string, clientInfo *ClientInfo) (*Session, error)
func (m *Manager) Get(id string) (*Session, error)
func (m *Manager) Delete(id string) error
func (m *Manager) List() []*Session
func (m *Manager) Count() int
func (m *Manager) Cleanup(maxAge time.Duration) int
func (m *Manager) OnSessionStart(fn func(*Session))
func (m *Manager) OnSessionEnd(fn func(*Session))
```

### Session

```go
// Tool management
func (s *Session) RegisterTool(name string)
func (s *Session) UnregisterTool(name string)
func (s *Session) HasTool(name string) bool
func (s *Session) GetTools() []string

// Context propagation
func (s *Session) SetContext(key string, value any)
func (s *Session) GetContext(key string) (any, bool)
func (s *Session) ClearContext()

// Lifecycle
func (s *Session) Touch()
func (s *Session) ToJSON() ([]byte, error)
```

### Context Integration

```go
// Add session to context
ctx := session.WithSession(ctx, sess)

// Extract session from context
sess, ok := session.FromContext(ctx)
```

### Session Structure

```go
type Session struct {
    ID          string
    ClientInfo  *ClientInfo
    Capabilities map[string]any
    Metadata    map[string]any
    CreatedAt   time.Time
    LastActive  time.Time
}

type ClientInfo struct {
    Name    string
    Version string
}
```

## Use Cases

- **Multi-tenant isolation**: Each client gets isolated tool access
- **Tool filtering**: Only show tools registered for session
- **Request context**: Propagate user/session info through handlers
- **Session cleanup**: Auto-cleanup inactive sessions

## Examples

See [examples/session/](../examples/session/) for complete examples.
