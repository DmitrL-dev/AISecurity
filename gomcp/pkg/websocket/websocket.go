// Package websocket provides WebSocket streaming for GoMCP.
package websocket

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"sync"
	"sync/atomic"
	"time"

	"golang.org/x/net/websocket"
)

// MessageType defines the type of WebSocket message
type MessageType string

const (
	MessageTypeRequest      MessageType = "request"
	MessageTypeResponse     MessageType = "response"
	MessageTypeNotification MessageType = "notification"
	MessageTypeError        MessageType = "error"
	MessageTypePing         MessageType = "ping"
	MessageTypePong         MessageType = "pong"
)

// Message represents a WebSocket message
type Message struct {
	Type      MessageType     `json:"type"`
	ID        string          `json:"id,omitempty"`
	Method    string          `json:"method,omitempty"`
	Params    json.RawMessage `json:"params,omitempty"`
	Result    json.RawMessage `json:"result,omitempty"`
	Error     *ErrorData      `json:"error,omitempty"`
	Timestamp time.Time       `json:"timestamp,omitempty"`
}

// ErrorData represents error details
type ErrorData struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

// Connection represents a WebSocket connection
type Connection struct {
	id       string
	ws       *websocket.Conn
	handler  MessageHandler
	send     chan *Message
	done     chan struct{}
	closed   atomic.Bool
	metadata map[string]string
	mu       sync.RWMutex
}

// MessageHandler handles incoming messages
type MessageHandler interface {
	HandleMessage(conn *Connection, msg *Message) (*Message, error)
}

// ConnectionOption configures a connection
type ConnectionOption func(*Connection)

// WithMetadata sets connection metadata
func WithMetadata(key, value string) ConnectionOption {
	return func(c *Connection) {
		c.metadata[key] = value
	}
}

// NewConnection creates a new WebSocket connection
func NewConnection(id string, ws *websocket.Conn, handler MessageHandler, opts ...ConnectionOption) *Connection {
	c := &Connection{
		id:       id,
		ws:       ws,
		handler:  handler,
		send:     make(chan *Message, 256),
		done:     make(chan struct{}),
		metadata: make(map[string]string),
	}

	for _, opt := range opts {
		opt(c)
	}

	return c
}

// ID returns the connection ID
func (c *Connection) ID() string {
	return c.id
}

// Send sends a message to the client
func (c *Connection) Send(msg *Message) error {
	if c.closed.Load() {
		return errors.New("connection closed")
	}
	select {
	case c.send <- msg:
		return nil
	default:
		return errors.New("send buffer full")
	}
}

// SendNotification sends a notification message
func (c *Connection) SendNotification(method string, params interface{}) error {
	data, err := json.Marshal(params)
	if err != nil {
		return err
	}
	return c.Send(&Message{
		Type:      MessageTypeNotification,
		Method:    method,
		Params:    data,
		Timestamp: time.Now(),
	})
}

// Close closes the connection
func (c *Connection) Close() error {
	if c.closed.Swap(true) {
		return nil
	}
	close(c.done)
	return c.ws.Close()
}

// IsClosed returns whether the connection is closed
func (c *Connection) IsClosed() bool {
	return c.closed.Load()
}

// GetMetadata returns connection metadata
func (c *Connection) GetMetadata(key string) (string, bool) {
	c.mu.RLock()
	defer c.mu.RUnlock()
	val, ok := c.metadata[key]
	return val, ok
}

// SetMetadata sets connection metadata
func (c *Connection) SetMetadata(key, value string) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.metadata[key] = value
}

// Start starts the connection read/write loops
func (c *Connection) Start(ctx context.Context) {
	go c.readLoop(ctx)
	go c.writeLoop(ctx)
}

func (c *Connection) readLoop(ctx context.Context) {
	defer c.Close()

	for {
		select {
		case <-ctx.Done():
			return
		case <-c.done:
			return
		default:
		}

		var msg Message
		if err := websocket.JSON.Receive(c.ws, &msg); err != nil {
			return
		}

		if msg.Type == MessageTypePing {
			c.Send(&Message{Type: MessageTypePong, ID: msg.ID})
			continue
		}

		if c.handler != nil {
			resp, err := c.handler.HandleMessage(c, &msg)
			if err != nil {
				c.Send(&Message{
					Type: MessageTypeError,
					ID:   msg.ID,
					Error: &ErrorData{
						Code:    -1,
						Message: err.Error(),
					},
				})
				continue
			}
			if resp != nil {
				c.Send(resp)
			}
		}
	}
}

func (c *Connection) writeLoop(ctx context.Context) {
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-c.done:
			return
		case msg := <-c.send:
			if err := websocket.JSON.Send(c.ws, msg); err != nil {
				c.Close()
				return
			}
		case <-ticker.C:
			c.Send(&Message{Type: MessageTypePing})
		}
	}
}

// Server is a WebSocket server
type Server struct {
	handler      MessageHandler
	connections  sync.Map
	connCounter  atomic.Uint64
	onConnect    func(*Connection)
	onDisconnect func(*Connection)
	mu           sync.RWMutex
}

// ServerOption configures the server
type ServerOption func(*Server)

// WithOnConnect sets connection callback
func WithOnConnect(fn func(*Connection)) ServerOption {
	return func(s *Server) {
		s.onConnect = fn
	}
}

// WithOnDisconnect sets disconnection callback
func WithOnDisconnect(fn func(*Connection)) ServerOption {
	return func(s *Server) {
		s.onDisconnect = fn
	}
}

// NewServer creates a new WebSocket server
func NewServer(handler MessageHandler, opts ...ServerOption) *Server {
	s := &Server{
		handler: handler,
	}

	for _, opt := range opts {
		opt(s)
	}

	return s
}

// Handler returns an HTTP handler for WebSocket connections
func (s *Server) Handler() http.Handler {
	return websocket.Handler(s.serveWS)
}

func (s *Server) serveWS(ws *websocket.Conn) {
	id := s.generateID()
	conn := NewConnection(id, ws, s.handler)

	s.connections.Store(id, conn)
	defer s.connections.Delete(id)

	if s.onConnect != nil {
		s.onConnect(conn)
	}

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	conn.Start(ctx)

	<-conn.done

	if s.onDisconnect != nil {
		s.onDisconnect(conn)
	}
}

func (s *Server) generateID() string {
	n := s.connCounter.Add(1)
	return uintToString(n)
}

// Broadcast sends a message to all connections
func (s *Server) Broadcast(msg *Message) {
	s.connections.Range(func(_, value interface{}) bool {
		if conn, ok := value.(*Connection); ok {
			conn.Send(msg)
		}
		return true
	})
}

// BroadcastNotification sends a notification to all connections
func (s *Server) BroadcastNotification(method string, params interface{}) error {
	data, err := json.Marshal(params)
	if err != nil {
		return err
	}
	msg := &Message{
		Type:      MessageTypeNotification,
		Method:    method,
		Params:    data,
		Timestamp: time.Now(),
	}
	s.Broadcast(msg)
	return nil
}

// ConnectionCount returns the number of active connections
func (s *Server) ConnectionCount() int {
	count := 0
	s.connections.Range(func(_, _ interface{}) bool {
		count++
		return true
	})
	return count
}

// GetConnection returns a connection by ID
func (s *Server) GetConnection(id string) (*Connection, bool) {
	val, ok := s.connections.Load(id)
	if !ok {
		return nil, false
	}
	return val.(*Connection), true
}

// CloseAll closes all connections
func (s *Server) CloseAll() {
	s.connections.Range(func(_, value interface{}) bool {
		if conn, ok := value.(*Connection); ok {
			conn.Close()
		}
		return true
	})
}

// Stream represents a message stream
type Stream struct {
	conn   *Connection
	events chan *Message
	done   chan struct{}
	closed atomic.Bool
}

// NewStream creates a new stream for a connection
func NewStream(conn *Connection) *Stream {
	return &Stream{
		conn:   conn,
		events: make(chan *Message, 64),
		done:   make(chan struct{}),
	}
}

// Events returns the event channel
func (s *Stream) Events() <-chan *Message {
	return s.events
}

// Push pushes a message to the stream
func (s *Stream) Push(msg *Message) error {
	if s.closed.Load() {
		return errors.New("stream closed")
	}
	select {
	case s.events <- msg:
		return nil
	default:
		return errors.New("stream buffer full")
	}
}

// Close closes the stream
func (s *Stream) Close() {
	if s.closed.Swap(true) {
		return
	}
	close(s.done)
	close(s.events)
}

// IsClosed returns whether the stream is closed
func (s *Stream) IsClosed() bool {
	return s.closed.Load()
}

// Helper function
func uintToString(n uint64) string {
	if n == 0 {
		return "0"
	}
	result := make([]byte, 0, 20)
	for n > 0 {
		result = append([]byte{byte('0' + n%10)}, result...)
		n /= 10
	}
	return string(result)
}
