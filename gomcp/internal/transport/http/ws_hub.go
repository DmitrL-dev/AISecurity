package httpserver

import (
	"crypto/rand"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"sync"
	"time"

	"github.com/syntrex/gomcp/internal/infrastructure/auth"
)

// wsClient holds a subscriber's channel and the tenant it is scoped to.
// An empty tenant means "see all" (superadmin, or single-tenant/test deploys).
type wsClient struct {
	ch     chan []byte
	tenant string
}

// WSHub manages WebSocket connections for live dashboard updates.
// Uses server-side Upgrade per RFC 6455 (no external deps — Go 1.24 net/http
// doesn't natively support WS, so we use SSE with long-poll fallback here
// and document the upgrade path to gorilla/websocket).
//
// For now, this implements an SSE-based push hub (same API as WebSocket
// but with EventSource transport). Upgrade to WS is a non-breaking change.
type WSHub struct {
	mu      sync.RWMutex
	clients map[string]*wsClient // clientID → client
}

// NewWSHub creates a new WebSocket/SSE push hub.
func NewWSHub() *WSHub {
	return &WSHub{
		clients: make(map[string]*wsClient),
	}
}

// Subscribe adds a client to the hub scoped to the given tenant (empty = all).
// Returns channel and cleanup function.
func (h *WSHub) Subscribe(clientID, tenant string) (<-chan []byte, func()) {
	ch := make(chan []byte, 64) // buffered to prevent slow client blocking
	h.mu.Lock()
	h.clients[clientID] = &wsClient{ch: ch, tenant: tenant}
	h.mu.Unlock()

	slog.Debug("ws hub: client subscribed", "client_id", clientID, "total", h.ClientCount())

	cleanup := func() {
		h.mu.Lock()
		delete(h.clients, clientID)
		close(ch)
		h.mu.Unlock()
		slog.Debug("ws hub: client unsubscribed", "client_id", clientID)
	}
	return ch, cleanup
}

// Broadcast sends a message to connected clients whose tenant scope matches.
// tenant is the owning tenant of the event. A client subscribed with an empty
// tenant (superadmin / single-tenant deploy) receives everything; a
// tenant-scoped client receives ONLY events whose tenant equals its own
// (untenanted/global events therefore reach see-all clients only — the strict
// choice, consistent with the /api/soc/stream handler).
// Non-blocking: slow clients' messages are dropped.
//
// SEC (multi-tenant isolation): without this filter the hub fanned every
// tenant's SOC events out to every connected dashboard, a cross-tenant leak.
func (h *WSHub) Broadcast(eventType, tenant string, data any) {
	payload, err := json.Marshal(map[string]any{
		"type":      eventType,
		"data":      data,
		"timestamp": time.Now().Format(time.RFC3339),
	})
	if err != nil {
		slog.Error("ws hub: marshal broadcast", "error", err)
		return
	}

	h.mu.RLock()
	defer h.mu.RUnlock()

	for id, c := range h.clients {
		// Deliver only when the client may see this tenant's data.
		// Empty client tenant = superadmin / single-tenant deploy → see all.
		if c.tenant != "" && c.tenant != tenant {
			continue
		}
		select {
		case c.ch <- payload:
		default:
			slog.Warn("ws hub: dropped message for slow client", "client_id", id)
		}
	}
}

// ClientCount returns the number of connected clients.
func (h *WSHub) ClientCount() int {
	h.mu.RLock()
	defer h.mu.RUnlock()
	return len(h.clients)
}

// HandleSSEStream serves Server-Sent Events for live dashboard updates.
// GET /api/soc/ws — returns SSE stream (Content-Type: text/event-stream).
func (h *WSHub) HandleSSEStream(w http.ResponseWriter, r *http.Request) {
	flusher, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "streaming not supported", http.StatusInternalServerError)
		return
	}

	// SEC-V6-3: Enforce maximum concurrent connections to prevent DoS via file descriptor exhaustion
	if h.ClientCount() >= 500 {
		http.Error(w, "max connections reached", http.StatusServiceUnavailable)
		return
	}

	// SEC-V6-3: Prevent stream hijacking by enforcing cryptographically random client IDs
	// Avoid trusting unauthenticated 'client_id' query parameters for map keys.
	b := make([]byte, 16)
	rand.Read(b)
	randSuffix := fmt.Sprintf("%x-%x-%x-%x-%x", b[0:4], b[4:6], b[6:8], b[8:10], b[10:])
	clientID := fmt.Sprintf("%s-%s", r.RemoteAddr, randSuffix)

	// SEC (multi-tenant isolation): scope this subscription to the caller's
	// tenant so the broadcast hub only fans this client its own tenant's events.
	// Empty scope ("") = superadmin or single-tenant/test deploy → receives all.
	tenantScope := ""
	if claims := auth.GetClaims(r.Context()); claims != nil && claims.Role != "superadmin" {
		tenantScope = claims.TenantID
	}

	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	w.Header().Set("X-Accel-Buffering", "no") // nginx proxy support

	ch, cleanup := h.Subscribe(clientID, tenantScope)
	defer cleanup()

	// Send initial connected event.
	w.Write([]byte("event: connected\ndata: {\"status\":\"ok\"}\n\n"))
	flusher.Flush()

	ctx := r.Context()
	for {
		select {
		case <-ctx.Done():
			return
		case msg, ok := <-ch:
			if !ok {
				return
			}
			w.Write([]byte("event: update\ndata: "))
			w.Write(msg)
			w.Write([]byte("\n\n"))
			flusher.Flush()
		}
	}
}
