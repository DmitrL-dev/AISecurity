package transport

import (
	"sync"
)

// ============================================================================
// TLS SESSION CACHE — Resumption Mimicry
// ============================================================================
// Chrome caches TLS sessions (via session tickets or session IDs).
// When reconnecting to the same server, Chrome presents the cached ticket
// for an abbreviated handshake. Go's default client does NOT do this
// between separate Dial calls.
//
// This cache stores session tickets keyed by host:port, enabling
// session resumption across multiple connections. LRU eviction
// prevents unbounded memory growth.
// Fixes GAP-8: TLS Session Resumption.
// ============================================================================

// SessionTicket represents a cached TLS session.
type SessionTicket struct {
	Host   string // host:port
	Ticket []byte // Opaque session ticket data
}

// TLSSessionCache is a thread-safe LRU cache for TLS session tickets.
type TLSSessionCache struct {
	mu       sync.Mutex
	capacity int
	entries  map[string]*SessionTicket
	order    []string // LRU order: oldest first
}

// NewTLSSessionCache creates a cache with the given capacity.
// Default capacity is 128 if 0 is passed.
func NewTLSSessionCache(capacity int) *TLSSessionCache {
	if capacity <= 0 {
		capacity = 128
	}
	return &TLSSessionCache{
		capacity: capacity,
		entries:  make(map[string]*SessionTicket),
		order:    make([]string, 0, capacity),
	}
}

// Put stores a session ticket, evicting the oldest entry if at capacity.
func (c *TLSSessionCache) Put(ticket *SessionTicket) {
	c.mu.Lock()
	defer c.mu.Unlock()

	// If already exists, update and move to end (most recent)
	if _, exists := c.entries[ticket.Host]; exists {
		c.entries[ticket.Host] = ticket
		c.moveToEnd(ticket.Host)
		return
	}

	// Evict oldest if at capacity
	if len(c.entries) >= c.capacity {
		oldest := c.order[0]
		delete(c.entries, oldest)
		c.order = c.order[1:]
	}

	c.entries[ticket.Host] = ticket
	c.order = append(c.order, ticket.Host)
}

// Get retrieves a cached session ticket for the given host.
// Returns nil on cache miss.
func (c *TLSSessionCache) Get(host string) *SessionTicket {
	c.mu.Lock()
	defer c.mu.Unlock()

	ticket, ok := c.entries[host]
	if !ok {
		return nil
	}

	// Touch: move to end (most recently used)
	c.moveToEnd(host)
	return ticket
}

// HasTicket checks if a session ticket exists for the host.
func (c *TLSSessionCache) HasTicket(host string) bool {
	c.mu.Lock()
	defer c.mu.Unlock()
	_, ok := c.entries[host]
	return ok
}

// Size returns the number of cached sessions.
func (c *TLSSessionCache) Size() int {
	c.mu.Lock()
	defer c.mu.Unlock()
	return len(c.entries)
}

// moveToEnd moves a key to the end of the LRU order (most recent).
// Must be called with lock held.
func (c *TLSSessionCache) moveToEnd(key string) {
	for i, k := range c.order {
		if k == key {
			c.order = append(c.order[:i], c.order[i+1:]...)
			c.order = append(c.order, key)
			return
		}
	}
}
