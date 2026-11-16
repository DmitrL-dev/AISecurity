package alert

import "sync"

// Bus is a thread-safe event bus for Alert distribution.
// Uses a ring buffer for bounded memory. Supports multiple subscribers.
type Bus struct {
	mu          sync.RWMutex
	ring        []Alert
	capacity    int
	writePos    int
	count       int
	subscribers []chan Alert
}

// NewBus creates a new Alert bus with the given capacity.
func NewBus(capacity int) *Bus {
	if capacity <= 0 {
		capacity = 100
	}
	return &Bus{
		ring:     make([]Alert, capacity),
		capacity: capacity,
	}
}

// Emit publishes an alert to the bus.
// Stored in ring buffer and sent to all subscribers.
func (b *Bus) Emit(a Alert) {
	b.mu.Lock()
	b.ring[b.writePos] = a
	b.writePos = (b.writePos + 1) % b.capacity
	if b.count < b.capacity {
		b.count++
	}

	// Copy subscribers under lock to avoid race.
	subs := make([]chan Alert, len(b.subscribers))
	copy(subs, b.subscribers)
	b.mu.Unlock()

	// Non-blocking send to subscribers.
	for _, ch := range subs {
		select {
		case ch <- a:
		default:
			// Subscriber too slow — drop alert.
		}
	}
}

// Recent returns the last n alerts, newest first.
func (b *Bus) Recent(n int) []Alert {
	b.mu.RLock()
	defer b.mu.RUnlock()

	if n > b.count {
		n = b.count
	}
	if n <= 0 {
		return nil
	}

	result := make([]Alert, n)
	for i := 0; i < n; i++ {
		// Read backwards from writePos.
		idx := (b.writePos - 1 - i + b.capacity) % b.capacity
		result[i] = b.ring[idx]
	}
	return result
}

// Subscribe returns a channel that receives new alerts.
// Buffer size determines how many alerts can queue before dropping.
func (b *Bus) Subscribe(bufSize int) <-chan Alert {
	if bufSize <= 0 {
		bufSize = 10
	}
	ch := make(chan Alert, bufSize)
	b.mu.Lock()
	b.subscribers = append(b.subscribers, ch)
	b.mu.Unlock()
	return ch
}

// Count returns the total number of stored alerts.
func (b *Bus) Count() int {
	b.mu.RLock()
	defer b.mu.RUnlock()
	return b.count
}

// MaxSeverity returns the highest severity among recent alerts.
func (b *Bus) MaxSeverity(n int) Severity {
	alerts := b.Recent(n)
	max := SeverityInfo
	for _, a := range alerts {
		if a.Severity > max {
			max = a.Severity
		}
	}
	return max
}
