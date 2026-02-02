// Package roots provides client filesystem roots support for MCP 2025-11-25.
// Roots define the filesystem boundaries that a client exposes to the server.
package roots

import (
	"encoding/json"
	"fmt"
	"sync"
)

// Root represents a filesystem root exposed by the client
type Root struct {
	URI  string `json:"uri"`
	Name string `json:"name,omitempty"`
}

// Manager manages filesystem roots
type Manager struct {
	roots map[string]*Root
	mu    sync.RWMutex

	// Callback for root changes
	onChange func(roots []*Root)
}

// NewManager creates a roots manager
func NewManager() *Manager {
	return &Manager{
		roots: make(map[string]*Root),
	}
}

// Add adds a root
func (m *Manager) Add(uri, name string) error {
	if uri == "" {
		return ErrEmptyURI
	}

	m.mu.Lock()
	defer m.mu.Unlock()

	m.roots[uri] = &Root{
		URI:  uri,
		Name: name,
	}

	m.notifyChange()
	return nil
}

// Remove removes a root by URI
func (m *Manager) Remove(uri string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if _, ok := m.roots[uri]; !ok {
		return ErrRootNotFound
	}

	delete(m.roots, uri)
	m.notifyChange()
	return nil
}

// Get retrieves a root by URI
func (m *Manager) Get(uri string) (*Root, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	root, ok := m.roots[uri]
	if !ok {
		return nil, ErrRootNotFound
	}

	return root, nil
}

// List returns all roots
func (m *Manager) List() []*Root {
	m.mu.RLock()
	defer m.mu.RUnlock()

	result := make([]*Root, 0, len(m.roots))
	for _, root := range m.roots {
		result = append(result, root)
	}
	return result
}

// Clear removes all roots
func (m *Manager) Clear() {
	m.mu.Lock()
	defer m.mu.Unlock()

	m.roots = make(map[string]*Root)
	m.notifyChange()
}

// OnChange sets a callback for root changes
func (m *Manager) OnChange(fn func(roots []*Root)) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.onChange = fn
}

// notifyChange triggers the change callback
func (m *Manager) notifyChange() {
	if m.onChange == nil {
		return
	}

	roots := make([]*Root, 0, len(m.roots))
	for _, root := range m.roots {
		roots = append(roots, root)
	}

	go m.onChange(roots)
}

// Count returns the number of roots
func (m *Manager) Count() int {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return len(m.roots)
}

// Contains checks if a URI is within any root
func (m *Manager) Contains(uri string) bool {
	m.mu.RLock()
	defer m.mu.RUnlock()

	for rootURI := range m.roots {
		if len(uri) >= len(rootURI) && uri[:len(rootURI)] == rootURI {
			return true
		}
	}
	return false
}

// ToJSON serializes roots to JSON
func (m *Manager) ToJSON() ([]byte, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	roots := make([]*Root, 0, len(m.roots))
	for _, root := range m.roots {
		roots = append(roots, root)
	}
	return json.Marshal(roots)
}

// Errors
var (
	ErrEmptyURI     = fmt.Errorf("URI cannot be empty")
	ErrRootNotFound = fmt.Errorf("root not found")
)

// JSON-RPC method names
const (
	MethodRootsList    = "roots/list"
	NotifyRootsChanged = "notifications/roots/list_changed"
)
