package soc

import (
	"log/slog"
	"sync"
)

// EventBus implements a pub-sub event bus for real-time event streaming (SSE/WebSocket).
// Subscribers receive events as they are ingested via IngestEvent pipeline.
type EventBus struct {
	mu          sync.RWMutex
	subscribers map[string]chan SOCEvent
	bufSize     int
	scopes      map[string]string
}

// NewEventBus creates a new event bus with the given channel buffer size.
func NewEventBus(bufSize int) *EventBus {
	if bufSize <= 0 {
		bufSize = 100
	}
	return &EventBus{
		subscribers: make(map[string]chan SOCEvent),
		bufSize:     bufSize,
		scopes:      make(map[string]string),
	}
}

// Subscribe creates a new subscriber channel. Returns channel and subscriber ID.
func (eb *EventBus) Subscribe(id string) <-chan SOCEvent {
	return eb.SubscribeTenant(id, "")
}

// SubscribeTenant filters before queueing, so other tenants cannot evict events.
func (eb *EventBus) SubscribeTenant(id, tenant string) <-chan SOCEvent {
	eb.mu.Lock()
	defer eb.mu.Unlock()

	ch := make(chan SOCEvent, eb.bufSize)
	eb.subscribers[id] = ch
	eb.scopes[id] = tenant
	return ch
}

// Unsubscribe removes a subscriber and closes its channel.
func (eb *EventBus) Unsubscribe(id string) {
	eb.mu.Lock()
	defer eb.mu.Unlock()

	if ch, ok := eb.subscribers[id]; ok {
		close(ch)
		delete(eb.subscribers, id)
		delete(eb.scopes, id)
	}
}

// Publish sends an event to all subscribers. Non-blocking — drops if subscriber is full.
func (eb *EventBus) Publish(event SOCEvent) {
	eb.mu.RLock()
	delivered, dropped := 0, 0
	for id, ch := range eb.subscribers {
		if tenant := eb.scopes[id]; tenant != "" && tenant != event.TenantID {
			continue
		}
		select {
		case ch <- event:
			delivered++
		default:
			dropped++
		}
	}
	total := len(eb.subscribers)
	eb.mu.RUnlock()

	// Log AFTER releasing the lock, and only when something was dropped (Review
	// 14.06 round-5). The previous per-subscriber slog.Info/Warn ran synchronous
	// stderr I/O O(N) UNDER the RLock on the ingest hot path — blocking
	// Subscribe/Unsubscribe and adding N log writes of latency to every ingested
	// event (amplified by a large subscriber count). The per-delivery info line
	// was also pure per-event-ID noise.
	if dropped > 0 {
		slog.Warn("eventbus: dropped events (slow subscribers)",
			"event_id", event.ID, "dropped", dropped, "delivered", delivered, "subscribers", total)
	}
}

// SubscriberCount returns the number of active subscribers.
func (eb *EventBus) SubscriberCount() int {
	eb.mu.RLock()
	defer eb.mu.RUnlock()
	return len(eb.subscribers)
}
