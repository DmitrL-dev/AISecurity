// Package sse provides Server-Sent Events transport for MCP.
// Enables real-time streaming over HTTP for web clients.
package sse

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"sync"
	"sync/atomic"
	"time"
)

// Server handles SSE connections for MCP
type Server struct {
	clients   map[string]*sseClient
	clientsMu sync.RWMutex

	// Message handlers
	handler MessageHandler

	// Options
	heartbeatInterval time.Duration
	maxClients        int
}

// sseClient represents a connected SSE client
type sseClient struct {
	id       string
	w        http.ResponseWriter
	flusher  http.Flusher
	done     chan struct{}
	messages chan *Event
}

// Event represents an SSE event
type Event struct {
	ID    string `json:"id,omitempty"`
	Event string `json:"event,omitempty"`
	Data  string `json:"data"`
	Retry int    `json:"retry,omitempty"`
}

// MessageHandler handles incoming messages
type MessageHandler func(ctx context.Context, clientID string, message []byte) ([]byte, error)

// ServerOption configures the server
type ServerOption func(*Server)

// WithHeartbeat sets heartbeat interval
func WithHeartbeat(d time.Duration) ServerOption {
	return func(s *Server) {
		s.heartbeatInterval = d
	}
}

// WithMaxClients sets max concurrent clients
func WithMaxClients(n int) ServerOption {
	return func(s *Server) {
		s.maxClients = n
	}
}

// NewServer creates a new SSE server
func NewServer(handler MessageHandler, opts ...ServerOption) *Server {
	s := &Server{
		clients:           make(map[string]*sseClient),
		handler:           handler,
		heartbeatInterval: 30 * time.Second,
		maxClients:        1000,
	}

	for _, opt := range opts {
		opt(s)
	}

	return s
}

// ServeHTTP handles SSE connections
func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	// Check if SSE is supported
	flusher, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "SSE not supported", http.StatusInternalServerError)
		return
	}

	// Check client limit
	s.clientsMu.RLock()
	if len(s.clients) >= s.maxClients {
		s.clientsMu.RUnlock()
		http.Error(w, "too many clients", http.StatusServiceUnavailable)
		return
	}
	s.clientsMu.RUnlock()

	// Set SSE headers
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	w.Header().Set("Access-Control-Allow-Origin", "*")

	// Generate client ID
	clientID := r.Header.Get("X-Client-ID")
	if clientID == "" {
		clientID = fmt.Sprintf("sse-%d", time.Now().UnixNano())
	}

	// Create client
	client := &sseClient{
		id:       clientID,
		w:        w,
		flusher:  flusher,
		done:     make(chan struct{}),
		messages: make(chan *Event, 100),
	}

	// Register client
	s.clientsMu.Lock()
	s.clients[clientID] = client
	s.clientsMu.Unlock()

	defer func() {
		s.clientsMu.Lock()
		delete(s.clients, clientID)
		s.clientsMu.Unlock()
		close(client.done)
	}()

	// Send connected event
	s.sendEvent(client, &Event{Event: "connected", Data: clientID})

	// Start heartbeat
	heartbeat := time.NewTicker(s.heartbeatInterval)
	defer heartbeat.Stop()

	// Event loop
	for {
		select {
		case <-r.Context().Done():
			return
		case <-client.done:
			return
		case <-heartbeat.C:
			s.sendEvent(client, &Event{Event: "heartbeat", Data: ""})
		case event := <-client.messages:
			s.sendEvent(client, event)
		}
	}
}

// sendEvent sends an event to a client
func (s *Server) sendEvent(client *sseClient, event *Event) error {
	var sb strings.Builder

	if event.ID != "" {
		sb.WriteString("id: ")
		sb.WriteString(event.ID)
		sb.WriteString("\n")
	}

	if event.Event != "" {
		sb.WriteString("event: ")
		sb.WriteString(event.Event)
		sb.WriteString("\n")
	}

	if event.Retry > 0 {
		sb.WriteString(fmt.Sprintf("retry: %d\n", event.Retry))
	}

	// Handle multi-line data
	lines := strings.Split(event.Data, "\n")
	for _, line := range lines {
		sb.WriteString("data: ")
		sb.WriteString(line)
		sb.WriteString("\n")
	}
	sb.WriteString("\n")

	_, err := client.w.Write([]byte(sb.String()))
	if err != nil {
		return err
	}

	client.flusher.Flush()
	return nil
}

// Broadcast sends an event to all clients
func (s *Server) Broadcast(event *Event) {
	s.clientsMu.RLock()
	defer s.clientsMu.RUnlock()

	for _, client := range s.clients {
		select {
		case client.messages <- event:
		default:
			// Client buffer full, skip
		}
	}
}

// SendTo sends an event to a specific client
func (s *Server) SendTo(clientID string, event *Event) error {
	s.clientsMu.RLock()
	client, ok := s.clients[clientID]
	s.clientsMu.RUnlock()

	if !ok {
		return ErrClientNotFound
	}

	select {
	case client.messages <- event:
		return nil
	default:
		return ErrClientBufferFull
	}
}

// ClientCount returns number of connected clients
func (s *Server) ClientCount() int {
	s.clientsMu.RLock()
	defer s.clientsMu.RUnlock()
	return len(s.clients)
}

// Close disconnects all clients
func (s *Server) Close() {
	s.clientsMu.Lock()
	defer s.clientsMu.Unlock()

	for _, client := range s.clients {
		close(client.done)
	}
	s.clients = make(map[string]*sseClient)
}

// Errors
var (
	ErrClientNotFound   = fmt.Errorf("client not found")
	ErrClientBufferFull = fmt.Errorf("client buffer full")
)

// Client connects to an SSE server
type Client struct {
	url       string
	eventCh   chan *Event
	done      chan struct{}
	connected int32

	// HTTP client
	httpClient *http.Client

	// Callbacks
	onConnect    func()
	onDisconnect func(error)
	onEvent      func(*Event)

	// Reconnection
	reconnectDelay time.Duration
	maxReconnects  int
}

// ClientOption configures the client
type ClientOption func(*Client)

// WithHTTPClient sets custom HTTP client
func WithHTTPClient(c *http.Client) ClientOption {
	return func(client *Client) {
		client.httpClient = c
	}
}

// WithReconnect configures auto-reconnection
func WithReconnect(delay time.Duration, maxAttempts int) ClientOption {
	return func(c *Client) {
		c.reconnectDelay = delay
		c.maxReconnects = maxAttempts
	}
}

// OnConnect sets connection callback
func OnConnect(fn func()) ClientOption {
	return func(c *Client) {
		c.onConnect = fn
	}
}

// OnDisconnect sets disconnection callback
func OnDisconnect(fn func(error)) ClientOption {
	return func(c *Client) {
		c.onDisconnect = fn
	}
}

// OnEvent sets event callback
func OnEvent(fn func(*Event)) ClientOption {
	return func(c *Client) {
		c.onEvent = fn
	}
}

// NewClient creates a new SSE client
func NewClient(url string, opts ...ClientOption) *Client {
	c := &Client{
		url:            url,
		eventCh:        make(chan *Event, 100),
		done:           make(chan struct{}),
		httpClient:     http.DefaultClient,
		reconnectDelay: 3 * time.Second,
		maxReconnects:  10,
	}

	for _, opt := range opts {
		opt(c)
	}

	return c
}

// Connect starts the SSE connection
func (c *Client) Connect(ctx context.Context) error {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, c.url, nil)
	if err != nil {
		return err
	}

	req.Header.Set("Accept", "text/event-stream")
	req.Header.Set("Cache-Control", "no-cache")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return err
	}

	if resp.StatusCode != http.StatusOK {
		resp.Body.Close()
		return fmt.Errorf("unexpected status: %d", resp.StatusCode)
	}

	atomic.StoreInt32(&c.connected, 1)
	if c.onConnect != nil {
		c.onConnect()
	}

	go c.readLoop(ctx, resp.Body)

	return nil
}

// readLoop reads events from the SSE stream
func (c *Client) readLoop(ctx context.Context, body io.ReadCloser) {
	defer body.Close()
	defer atomic.StoreInt32(&c.connected, 0)

	reader := bufio.NewReader(body)
	var event Event

	for {
		select {
		case <-ctx.Done():
			return
		case <-c.done:
			return
		default:
		}

		line, err := reader.ReadString('\n')
		if err != nil {
			if c.onDisconnect != nil {
				c.onDisconnect(err)
			}
			return
		}

		line = strings.TrimRight(line, "\r\n")

		if line == "" {
			// End of event
			if event.Data != "" || event.Event != "" {
				evt := event
				event = Event{}

				if c.onEvent != nil {
					c.onEvent(&evt)
				}

				select {
				case c.eventCh <- &evt:
				default:
				}
			}
			continue
		}

		if strings.HasPrefix(line, ":") {
			// Comment, ignore
			continue
		}

		if strings.HasPrefix(line, "id:") {
			event.ID = strings.TrimPrefix(line, "id:")
			event.ID = strings.TrimSpace(event.ID)
		} else if strings.HasPrefix(line, "event:") {
			event.Event = strings.TrimPrefix(line, "event:")
			event.Event = strings.TrimSpace(event.Event)
		} else if strings.HasPrefix(line, "data:") {
			data := strings.TrimPrefix(line, "data:")
			data = strings.TrimSpace(data)
			if event.Data != "" {
				event.Data += "\n"
			}
			event.Data += data
		} else if strings.HasPrefix(line, "retry:") {
			// Parse retry interval
			retry := strings.TrimPrefix(line, "retry:")
			retry = strings.TrimSpace(retry)
			fmt.Sscanf(retry, "%d", &event.Retry)
		}
	}
}

// Events returns the event channel
func (c *Client) Events() <-chan *Event {
	return c.eventCh
}

// IsConnected returns connection status
func (c *Client) IsConnected() bool {
	return atomic.LoadInt32(&c.connected) == 1
}

// Close disconnects the client
func (c *Client) Close() error {
	close(c.done)
	return nil
}

// SendJSON sends JSON data as an event
func SendJSON(event string, data any) (*Event, error) {
	jsonData, err := json.Marshal(data)
	if err != nil {
		return nil, err
	}

	return &Event{
		Event: event,
		Data:  string(jsonData),
	}, nil
}
