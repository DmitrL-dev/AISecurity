// Package grpcstream provides bidirectional streaming support for MCP over gRPC.
// Enables real-time notifications and event streaming between client and server.
package grpcstream

import (
	"encoding/json"
	"fmt"
	"sync"
	"time"
)

// Message represents a streaming message
type Message struct {
	ID        string       `json:"id"`
	Type      MessageType  `json:"type"`
	Method    string       `json:"method,omitempty"`
	Params    any          `json:"params,omitempty"`
	Result    any          `json:"result,omitempty"`
	Error     *StreamError `json:"error,omitempty"`
	Timestamp time.Time    `json:"timestamp"`
}

// MessageType indicates the message direction/type
type MessageType string

const (
	TypeRequest      MessageType = "request"
	TypeResponse     MessageType = "response"
	TypeNotification MessageType = "notification"
	TypeEvent        MessageType = "event"
)

// StreamError represents a streaming error
type StreamError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

// Stream represents a bidirectional stream
type Stream struct {
	ID       string
	send     chan *Message
	recv     chan *Message
	done     chan struct{}
	mu       sync.RWMutex
	closed   bool
	metadata map[string]string
}

// NewStream creates a bidirectional stream
func NewStream(id string, bufferSize int) *Stream {
	if bufferSize <= 0 {
		bufferSize = 100
	}
	return &Stream{
		ID:       id,
		send:     make(chan *Message, bufferSize),
		recv:     make(chan *Message, bufferSize),
		done:     make(chan struct{}),
		metadata: make(map[string]string),
	}
}

// Send sends a message to the stream
func (s *Stream) Send(msg *Message) error {
	s.mu.RLock()
	if s.closed {
		s.mu.RUnlock()
		return ErrStreamClosed
	}
	s.mu.RUnlock()

	if msg.Timestamp.IsZero() {
		msg.Timestamp = time.Now()
	}

	select {
	case s.send <- msg:
		return nil
	case <-s.done:
		return ErrStreamClosed
	}
}

// Receive receives a message from the stream
func (s *Stream) Receive() (*Message, error) {
	select {
	case msg := <-s.recv:
		return msg, nil
	case <-s.done:
		return nil, ErrStreamClosed
	}
}

// ReceiveWithTimeout receives with timeout
func (s *Stream) ReceiveWithTimeout(timeout time.Duration) (*Message, error) {
	select {
	case msg := <-s.recv:
		return msg, nil
	case <-s.done:
		return nil, ErrStreamClosed
	case <-time.After(timeout):
		return nil, ErrTimeout
	}
}

// SendChan returns the send channel for reading
func (s *Stream) SendChan() <-chan *Message {
	return s.send
}

// RecvChan returns the receive channel for writing
func (s *Stream) RecvChan() chan<- *Message {
	return s.recv
}

// Close closes the stream
func (s *Stream) Close() error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if s.closed {
		return ErrStreamClosed
	}

	s.closed = true
	close(s.done)
	return nil
}

// IsClosed checks if stream is closed
func (s *Stream) IsClosed() bool {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.closed
}

// SetMetadata sets stream metadata
func (s *Stream) SetMetadata(key, value string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.metadata[key] = value
}

// GetMetadata gets stream metadata
func (s *Stream) GetMetadata(key string) (string, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	v, ok := s.metadata[key]
	return v, ok
}

// Done returns channel that closes when stream ends
func (s *Stream) Done() <-chan struct{} {
	return s.done
}

// Hub manages multiple streams
type Hub struct {
	streams map[string]*Stream
	mu      sync.RWMutex

	// Callbacks
	onConnect    func(*Stream)
	onDisconnect func(*Stream)
}

// NewHub creates a stream hub
func NewHub() *Hub {
	return &Hub{
		streams: make(map[string]*Stream),
	}
}

// Register adds a stream to the hub
func (h *Hub) Register(stream *Stream) {
	h.mu.Lock()
	h.streams[stream.ID] = stream
	h.mu.Unlock()

	if h.onConnect != nil {
		go h.onConnect(stream)
	}
}

// Unregister removes a stream from the hub
func (h *Hub) Unregister(id string) {
	h.mu.Lock()
	stream, ok := h.streams[id]
	if ok {
		delete(h.streams, id)
	}
	h.mu.Unlock()

	if ok && h.onDisconnect != nil {
		go h.onDisconnect(stream)
	}
}

// Get retrieves a stream by ID
func (h *Hub) Get(id string) (*Stream, bool) {
	h.mu.RLock()
	defer h.mu.RUnlock()
	s, ok := h.streams[id]
	return s, ok
}

// Broadcast sends a message to all streams
func (h *Hub) Broadcast(msg *Message) int {
	h.mu.RLock()
	defer h.mu.RUnlock()

	count := 0
	for _, stream := range h.streams {
		if err := stream.Send(msg); err == nil {
			count++
		}
	}
	return count
}

// BroadcastTo sends a message to specific streams
func (h *Hub) BroadcastTo(msg *Message, ids ...string) int {
	h.mu.RLock()
	defer h.mu.RUnlock()

	count := 0
	for _, id := range ids {
		if stream, ok := h.streams[id]; ok {
			if err := stream.Send(msg); err == nil {
				count++
			}
		}
	}
	return count
}

// Count returns number of active streams
func (h *Hub) Count() int {
	h.mu.RLock()
	defer h.mu.RUnlock()
	return len(h.streams)
}

// List returns all stream IDs
func (h *Hub) List() []string {
	h.mu.RLock()
	defer h.mu.RUnlock()

	ids := make([]string, 0, len(h.streams))
	for id := range h.streams {
		ids = append(ids, id)
	}
	return ids
}

// OnConnect sets callback for new connections
func (h *Hub) OnConnect(fn func(*Stream)) {
	h.mu.Lock()
	defer h.mu.Unlock()
	h.onConnect = fn
}

// OnDisconnect sets callback for disconnections
func (h *Hub) OnDisconnect(fn func(*Stream)) {
	h.mu.Lock()
	defer h.mu.Unlock()
	h.onDisconnect = fn
}

// Close closes all streams
func (h *Hub) Close() {
	h.mu.Lock()
	defer h.mu.Unlock()

	for _, stream := range h.streams {
		stream.Close()
	}
	h.streams = make(map[string]*Stream)
}

// Notification helpers

// NewNotification creates a notification message
func NewNotification(method string, params any) *Message {
	return &Message{
		ID:        generateID(),
		Type:      TypeNotification,
		Method:    method,
		Params:    params,
		Timestamp: time.Now(),
	}
}

// NewEvent creates an event message
func NewEvent(method string, params any) *Message {
	return &Message{
		ID:        generateID(),
		Type:      TypeEvent,
		Method:    method,
		Params:    params,
		Timestamp: time.Now(),
	}
}

// NewRequest creates a request message
func NewRequest(method string, params any) *Message {
	return &Message{
		ID:        generateID(),
		Type:      TypeRequest,
		Method:    method,
		Params:    params,
		Timestamp: time.Now(),
	}
}

// NewResponse creates a response message
func NewResponse(id string, result any) *Message {
	return &Message{
		ID:        id,
		Type:      TypeResponse,
		Result:    result,
		Timestamp: time.Now(),
	}
}

// NewErrorResponse creates an error response
func NewErrorResponse(id string, code int, message string) *Message {
	return &Message{
		ID:   id,
		Type: TypeResponse,
		Error: &StreamError{
			Code:    code,
			Message: message,
		},
		Timestamp: time.Now(),
	}
}

// ToJSON serializes message to JSON
func (m *Message) ToJSON() ([]byte, error) {
	return json.Marshal(m)
}

// FromJSON deserializes message from JSON
func FromJSON(data []byte) (*Message, error) {
	var msg Message
	if err := json.Unmarshal(data, &msg); err != nil {
		return nil, err
	}
	return &msg, nil
}

// ID generation
var (
	idCounter uint64
	idMu      sync.Mutex
)

func generateID() string {
	idMu.Lock()
	idCounter++
	id := idCounter
	idMu.Unlock()
	return fmt.Sprintf("msg-%d-%d", time.Now().UnixNano(), id)
}

// Errors
var (
	ErrStreamClosed = fmt.Errorf("stream is closed")
	ErrTimeout      = fmt.Errorf("operation timed out")
)
