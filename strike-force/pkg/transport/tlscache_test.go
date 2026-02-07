package transport

import (
	"testing"
)

// ============================================================================
// TDD: TLS Session Cache Tests
// ============================================================================

func TestNewTLSSessionCache_NotNil(t *testing.T) {
	cache := NewTLSSessionCache(64)
	if cache == nil {
		t.Fatal("TLS session cache is nil")
	}
}

func TestTLSSessionCache_DefaultCapacity(t *testing.T) {
	cache := NewTLSSessionCache(0)
	if cache.capacity != 128 {
		t.Errorf("default capacity = %d, want 128", cache.capacity)
	}
}

func TestTLSSessionCache_StoreAndRetrieve(t *testing.T) {
	cache := NewTLSSessionCache(16)

	ticket := &SessionTicket{
		Host:   "example.com:443",
		Ticket: []byte("fake-session-ticket-data"),
	}

	cache.Put(ticket)
	got := cache.Get("example.com:443")

	if got == nil {
		t.Fatal("expected cached ticket, got nil")
	}
	if string(got.Ticket) != "fake-session-ticket-data" {
		t.Errorf("ticket data = %q, want 'fake-session-ticket-data'", got.Ticket)
	}
}

func TestTLSSessionCache_MissReturnsNil(t *testing.T) {
	cache := NewTLSSessionCache(16)
	got := cache.Get("nonexistent.com:443")
	if got != nil {
		t.Error("expected nil for cache miss")
	}
}

func TestTLSSessionCache_Overwrite(t *testing.T) {
	cache := NewTLSSessionCache(16)

	cache.Put(&SessionTicket{Host: "a.com:443", Ticket: []byte("old")})
	cache.Put(&SessionTicket{Host: "a.com:443", Ticket: []byte("new")})

	got := cache.Get("a.com:443")
	if got == nil || string(got.Ticket) != "new" {
		t.Error("expected overwritten ticket with 'new' data")
	}
}

func TestTLSSessionCache_Eviction(t *testing.T) {
	cache := NewTLSSessionCache(2) // Only 2 slots

	cache.Put(&SessionTicket{Host: "a.com:443", Ticket: []byte("a")})
	cache.Put(&SessionTicket{Host: "b.com:443", Ticket: []byte("b")})
	cache.Put(&SessionTicket{Host: "c.com:443", Ticket: []byte("c")}) // Evicts oldest

	if cache.Get("a.com:443") != nil {
		t.Error("expected 'a.com' to be evicted")
	}
	if cache.Get("b.com:443") == nil {
		t.Error("expected 'b.com' to still be cached")
	}
	if cache.Get("c.com:443") == nil {
		t.Error("expected 'c.com' to still be cached")
	}
}

func TestTLSSessionCache_Size(t *testing.T) {
	cache := NewTLSSessionCache(16)

	cache.Put(&SessionTicket{Host: "a.com:443", Ticket: []byte("a")})
	cache.Put(&SessionTicket{Host: "b.com:443", Ticket: []byte("b")})

	if cache.Size() != 2 {
		t.Errorf("size = %d, want 2", cache.Size())
	}
}

func TestTLSSessionCache_HasTicket(t *testing.T) {
	cache := NewTLSSessionCache(16)

	if cache.HasTicket("x.com:443") {
		t.Error("should not have ticket for uncached host")
	}

	cache.Put(&SessionTicket{Host: "x.com:443", Ticket: []byte("x")})

	if !cache.HasTicket("x.com:443") {
		t.Error("should have ticket after Put")
	}
}
