package identity

import (
	"fmt"
	"strings"
	"sync"
)

// NamespacedMemory wraps any key-value store with agent-level namespace isolation.
// Agent A cannot read/write/query Agent B's memory (SDD-003 M4).
type NamespacedMemory struct {
	mu      sync.RWMutex
	entries map[string]interface{} // "agentID::key" → value
}

// NewNamespacedMemory creates a new namespaced memory store.
func NewNamespacedMemory() *NamespacedMemory {
	return &NamespacedMemory{
		entries: make(map[string]interface{}),
	}
}

// namespacePrefix returns the unambiguous, collision-free internal prefix for
// an agent's namespace.
//
// SECURITY: the agentID is length-prefixed ("<len>:<agentID>::") so that no
// agentID/key combination can collide with another agent's namespace. A naive
// "agentID::key" scheme is unsafe because agentIDs and keys are arbitrary,
// caller-supplied strings that may themselves contain "::" — e.g. Store("a",
// "b::x") and Store("a::b", "x") would otherwise map to the SAME internal key,
// and Keys("a")/Count("a") would also enumerate agent "a::b"'s entries via the
// shared "a::" prefix, breaking the M4 cross-agent isolation guarantee.
func namespacePrefix(agentID string) string {
	return fmt.Sprintf("%d:%s::", len(agentID), agentID)
}

// namespacedKey creates the internal key for (agentID, key).
func namespacedKey(agentID, key string) string {
	return namespacePrefix(agentID) + key
}

// Store stores a value within the agent's namespace.
func (n *NamespacedMemory) Store(agentID, key string, value interface{}) {
	n.mu.Lock()
	defer n.mu.Unlock()
	n.entries[namespacedKey(agentID, key)] = value
}

// Get retrieves a value from the agent's own namespace.
// Returns nil, false if the key doesn't exist.
func (n *NamespacedMemory) Get(agentID, key string) (interface{}, bool) {
	n.mu.RLock()
	defer n.mu.RUnlock()
	val, ok := n.entries[namespacedKey(agentID, key)]
	return val, ok
}

// Delete removes a value from the agent's own namespace.
func (n *NamespacedMemory) Delete(agentID, key string) {
	n.mu.Lock()
	defer n.mu.Unlock()
	delete(n.entries, namespacedKey(agentID, key))
}

// Keys returns all keys within the agent's namespace (without the namespace prefix).
func (n *NamespacedMemory) Keys(agentID string) []string {
	n.mu.RLock()
	defer n.mu.RUnlock()

	prefix := namespacePrefix(agentID)
	var keys []string
	for k := range n.entries {
		if strings.HasPrefix(k, prefix) {
			keys = append(keys, k[len(prefix):])
		}
	}
	return keys
}

// Count returns the number of entries in the agent's namespace.
func (n *NamespacedMemory) Count(agentID string) int {
	n.mu.RLock()
	defer n.mu.RUnlock()

	prefix := namespacePrefix(agentID)
	count := 0
	for k := range n.entries {
		if strings.HasPrefix(k, prefix) {
			count++
		}
	}
	return count
}
