# Roots Module

> Filesystem boundary management for MCP clients

## Overview

The `roots` module manages filesystem roots that a client exposes to the server. Roots define sandbox boundaries for file access.

## Installation

```go
import "github.com/sentinel-community/gomcp/pkg/roots"
```

## Quick Start

```go
manager := roots.NewManager()

// Add roots
manager.Add("file:///home/user/project", "Main Project")
manager.Add("file:///tmp/workspace", "Temp")

// Check if path is allowed
if manager.Contains("file:///home/user/project/src/main.go") {
    // Access allowed
}

// List all roots
for _, root := range manager.List() {
    fmt.Printf("%s: %s\n", root.Name, root.URI)
}
```

## API Reference

### Manager

```go
func NewManager() *Manager
```
Creates a new roots manager.

---

```go
func (m *Manager) Add(uri, name string) error
```
Adds a root. Returns `ErrEmptyURI` if URI is empty.

---

```go
func (m *Manager) Remove(uri string) error
```
Removes a root. Returns `ErrRootNotFound` if not found.

---

```go
func (m *Manager) Get(uri string) (*Root, error)
```
Gets a root by URI.

---

```go
func (m *Manager) List() []*Root
```
Returns all registered roots.

---

```go
func (m *Manager) Contains(uri string) bool
```
Checks if URI is within any root boundary.

---

```go
func (m *Manager) Count() int
```
Returns number of registered roots.

---

```go
func (m *Manager) Clear()
```
Removes all roots.

---

```go
func (m *Manager) OnChange(fn func(roots []*Root))
```
Sets callback for root changes.

---

```go
func (m *Manager) ToJSON() ([]byte, error)
```
Exports roots as JSON for protocol.

### Root Structure

```go
type Root struct {
    URI  string `json:"uri"`
    Name string `json:"name,omitempty"`
}
```

### JSON-RPC Methods

| Method | Description |
|--------|-------------|
| `roots/list` | List all roots |
| `notifications/roots/list_changed` | Roots changed notification |

## Security

Roots define the sandbox boundary for file access:

- Server can only access files within declared roots
- Use `Contains()` to validate all file access requests
- Roots cannot overlap with sensitive system paths

## Examples

See [examples/roots/](../examples/roots/) for complete examples.
