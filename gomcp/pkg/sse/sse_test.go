package sse

import (
	"context"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync/atomic"
	"testing"
	"time"
)

func TestNewServer(t *testing.T) {
	handler := func(ctx context.Context, clientID string, message []byte) ([]byte, error) {
		return nil, nil
	}

	server := NewServer(handler)

	if server == nil {
		t.Fatal("expected server to be created")
	}

	if server.heartbeatInterval != 30*time.Second {
		t.Errorf("unexpected heartbeat interval: %v", server.heartbeatInterval)
	}

	if server.maxClients != 1000 {
		t.Errorf("unexpected max clients: %d", server.maxClients)
	}
}

func TestNewServer_WithOptions(t *testing.T) {
	handler := func(ctx context.Context, clientID string, message []byte) ([]byte, error) {
		return nil, nil
	}

	server := NewServer(handler,
		WithHeartbeat(10*time.Second),
		WithMaxClients(500),
	)

	if server.heartbeatInterval != 10*time.Second {
		t.Errorf("unexpected heartbeat interval: %v", server.heartbeatInterval)
	}

	if server.maxClients != 500 {
		t.Errorf("unexpected max clients: %d", server.maxClients)
	}
}

func TestServer_ClientCount(t *testing.T) {
	handler := func(ctx context.Context, clientID string, message []byte) ([]byte, error) {
		return nil, nil
	}

	server := NewServer(handler)

	if server.ClientCount() != 0 {
		t.Error("expected 0 clients initially")
	}
}

func TestNewClient(t *testing.T) {
	client := NewClient("http://localhost:8080/sse")

	if client == nil {
		t.Fatal("expected client to be created")
	}

	if client.url != "http://localhost:8080/sse" {
		t.Errorf("unexpected url: %s", client.url)
	}

	if client.reconnectDelay != 3*time.Second {
		t.Errorf("unexpected reconnect delay: %v", client.reconnectDelay)
	}
}

func TestNewClient_WithOptions(t *testing.T) {
	customHTTP := &http.Client{Timeout: 10 * time.Second}
	connectCalled := false
	disconnectCalled := false
	eventCalled := false

	client := NewClient("http://localhost:8080/sse",
		WithHTTPClient(customHTTP),
		WithReconnect(5*time.Second, 3),
		OnConnect(func() { connectCalled = true }),
		OnDisconnect(func(err error) { disconnectCalled = true }),
		OnEvent(func(e *Event) { eventCalled = true }),
	)

	if client.httpClient != customHTTP {
		t.Error("custom HTTP client not set")
	}

	if client.reconnectDelay != 5*time.Second {
		t.Errorf("unexpected reconnect delay: %v", client.reconnectDelay)
	}

	if client.maxReconnects != 3 {
		t.Errorf("unexpected max reconnects: %d", client.maxReconnects)
	}

	// Verify callbacks are set
	if client.onConnect == nil {
		t.Error("onConnect callback not set")
	}
	if client.onDisconnect == nil {
		t.Error("onDisconnect callback not set")
	}
	if client.onEvent == nil {
		t.Error("onEvent callback not set")
	}

	_ = connectCalled
	_ = disconnectCalled
	_ = eventCalled
}

func TestClient_IsConnected(t *testing.T) {
	client := NewClient("http://localhost:8080/sse")

	if client.IsConnected() {
		t.Error("should not be connected initially")
	}

	atomic.StoreInt32(&client.connected, 1)

	if !client.IsConnected() {
		t.Error("should be connected after setting flag")
	}
}

func TestEvent_Format(t *testing.T) {
	event, err := SendJSON("test", map[string]string{"key": "value"})
	if err != nil {
		t.Fatalf("failed to create event: %v", err)
	}

	if event.Event != "test" {
		t.Errorf("unexpected event name: %s", event.Event)
	}

	if !strings.Contains(event.Data, "key") {
		t.Error("expected data to contain key")
	}
}

func TestServer_ServeHTTP_NoFlusher(t *testing.T) {
	handler := func(ctx context.Context, clientID string, message []byte) ([]byte, error) {
		return nil, nil
	}

	server := NewServer(handler)

	// Use a custom response writer that doesn't implement Flusher
	req := httptest.NewRequest(http.MethodGet, "/sse", nil)
	w := &minimalResponseWriter{
		header: make(http.Header),
		code:   http.StatusOK,
	}

	server.ServeHTTP(w, req)

	// Should return error because SSE not supported
	if w.code != http.StatusInternalServerError {
		t.Errorf("expected 500, got %d", w.code)
	}
}

// minimalResponseWriter is a ResponseWriter that does NOT implement http.Flusher
type minimalResponseWriter struct {
	header http.Header
	code   int
	body   []byte
}

func (w *minimalResponseWriter) Header() http.Header { return w.header }
func (w *minimalResponseWriter) Write(b []byte) (int, error) {
	w.body = append(w.body, b...)
	return len(b), nil
}
func (w *minimalResponseWriter) WriteHeader(code int) { w.code = code }

func TestServer_Broadcast(t *testing.T) {
	handler := func(ctx context.Context, clientID string, message []byte) ([]byte, error) {
		return nil, nil
	}

	server := NewServer(handler)

	// Broadcast to empty server shouldn't panic
	server.Broadcast(&Event{Event: "test", Data: "hello"})
}

func TestServer_SendTo_NotFound(t *testing.T) {
	handler := func(ctx context.Context, clientID string, message []byte) ([]byte, error) {
		return nil, nil
	}

	server := NewServer(handler)

	err := server.SendTo("non-existent", &Event{Event: "test"})
	if err != ErrClientNotFound {
		t.Errorf("expected ErrClientNotFound, got %v", err)
	}
}

func TestServer_Close(t *testing.T) {
	handler := func(ctx context.Context, clientID string, message []byte) ([]byte, error) {
		return nil, nil
	}

	server := NewServer(handler)

	// Close empty server shouldn't panic
	server.Close()

	if server.ClientCount() != 0 {
		t.Error("expected 0 clients after close")
	}
}

func TestClient_Close(t *testing.T) {
	client := NewClient("http://localhost:8080/sse")

	// Close should not panic
	err := client.Close()
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestClient_Events(t *testing.T) {
	client := NewClient("http://localhost:8080/sse")

	ch := client.Events()
	if ch == nil {
		t.Error("expected event channel")
	}
}

func TestErrors(t *testing.T) {
	if ErrClientNotFound == nil {
		t.Error("ErrClientNotFound should be defined")
	}

	if ErrClientBufferFull == nil {
		t.Error("ErrClientBufferFull should be defined")
	}
}

// Integration test with real HTTP server
func TestServer_Integration(t *testing.T) {
	handler := func(ctx context.Context, clientID string, message []byte) ([]byte, error) {
		return []byte("response"), nil
	}

	server := NewServer(handler, WithHeartbeat(100*time.Millisecond))

	ts := httptest.NewServer(server)
	defer ts.Close()

	// Create client and connect
	client := NewClient(ts.URL)

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	err := client.Connect(ctx)
	if err != nil {
		t.Fatalf("failed to connect: %v", err)
	}
	defer client.Close()

	if !client.IsConnected() {
		t.Error("expected client to be connected")
	}

	// Wait for connected event
	select {
	case event := <-client.Events():
		if event.Event != "connected" {
			t.Errorf("expected connected event, got %s", event.Event)
		}
	case <-ctx.Done():
		t.Fatal("timeout waiting for connected event")
	}

	// Wait for heartbeat
	select {
	case event := <-client.Events():
		if event.Event != "heartbeat" {
			t.Errorf("expected heartbeat event, got %s", event.Event)
		}
	case <-ctx.Done():
		t.Fatal("timeout waiting for heartbeat")
	}
}

func TestServer_Broadcast_Integration(t *testing.T) {
	handler := func(ctx context.Context, clientID string, message []byte) ([]byte, error) {
		return nil, nil
	}

	server := NewServer(handler, WithHeartbeat(1*time.Hour)) // Disable heartbeat for test

	ts := httptest.NewServer(server)
	defer ts.Close()

	client := NewClient(ts.URL)

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	err := client.Connect(ctx)
	if err != nil {
		t.Fatalf("failed to connect: %v", err)
	}
	defer client.Close()

	// Wait for connected
	select {
	case <-client.Events():
	case <-ctx.Done():
		t.Fatal("timeout waiting for connected")
	}

	// Give server time to register client
	time.Sleep(50 * time.Millisecond)

	// Broadcast a message
	server.Broadcast(&Event{Event: "broadcast", Data: "hello world"})

	// Wait for broadcast
	select {
	case event := <-client.Events():
		if event.Event != "broadcast" {
			t.Errorf("expected broadcast event, got %s", event.Event)
		}
		if event.Data != "hello world" {
			t.Errorf("unexpected data: %s", event.Data)
		}
	case <-ctx.Done():
		t.Fatal("timeout waiting for broadcast")
	}
}
