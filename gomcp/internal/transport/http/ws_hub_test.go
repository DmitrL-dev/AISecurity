package httpserver

import (
	"testing"
	"time"
)

// TestWSHub_BroadcastTenantIsolation is a regression test for the multi-tenant
// isolation fix on the live event stream: the broadcast hub must fan an event
// only to clients whose tenant scope matches the event's owning tenant, while
// empty-scope clients (superadmin / single-tenant deploy) still see everything.
//
// Before the fix, WSHub.Broadcast delivered every event to every connected
// client, leaking one tenant's SOC event descriptions/session IDs to another.
func TestWSHub_BroadcastTenantIsolation(t *testing.T) {
	h := NewWSHub()

	chA, cleanupA := h.Subscribe("client-a", "tnt-a")
	defer cleanupA()
	chB, cleanupB := h.Subscribe("client-b", "tnt-b")
	defer cleanupB()
	chAll, cleanupAll := h.Subscribe("client-super", "") // superadmin / see-all
	defer cleanupAll()

	// Broadcast an event owned by tenant A.
	h.Broadcast("soc_event", "tnt-a", map[string]any{"description": "alpha-only secret"})

	// Tenant-A client must receive it.
	if !received(chA) {
		t.Fatal("tenant-A client did NOT receive its own tenant's event")
	}
	// See-all client must receive it.
	if !received(chAll) {
		t.Fatal("empty-scope (superadmin) client did NOT receive the event")
	}
	// Tenant-B client must NOT receive it (cross-tenant leak guard).
	if received(chB) {
		t.Fatal("tenant-B client RECEIVED tenant-A's event — cross-tenant leak")
	}

	// Strict scoping: an untenanted/global event ("") is delivered only to
	// see-all clients, not to tenant-scoped ones (consistent with the
	// /api/soc/stream handler, which drops events whose tenant != caller's).
	h.Broadcast("soc_event", "", map[string]any{"description": "system-wide"})
	if !received(chAll) {
		t.Fatal("see-all client did NOT receive a global (untenanted) event")
	}
	if received(chB) {
		t.Fatal("tenant-B client received a global event — should be see-all only")
	}
}

// received reports whether a message is available on ch within a short window.
func received(ch <-chan []byte) bool {
	select {
	case <-ch:
		return true
	case <-time.After(100 * time.Millisecond):
		return false
	}
}
