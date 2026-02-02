package websocket

import (
	"sync"
	"testing"
	"time"
)

// MockWebSocket for testing without real network
type MockWebSocket struct {
	messages []Message
	sendErr  error
	recvErr  error
	closed   bool
	mu       sync.Mutex
}

// Message tests
func TestMessageType_Values(t *testing.T) {
	if MessageTypeRequest != "request" {
		t.Errorf("expected request, got %s", MessageTypeRequest)
	}
	if MessageTypeResponse != "response" {
		t.Errorf("expected response, got %s", MessageTypeResponse)
	}
	if MessageTypeNotification != "notification" {
		t.Errorf("expected notification, got %s", MessageTypeNotification)
	}
}

func TestMessage_Create(t *testing.T) {
	msg := Message{
		Type:   MessageTypeRequest,
		ID:     "1",
		Method: "test",
	}

	if msg.Type != MessageTypeRequest {
		t.Error("type mismatch")
	}
	if msg.ID != "1" {
		t.Error("id mismatch")
	}
}

func TestMessage_WithError(t *testing.T) {
	msg := Message{
		Type: MessageTypeError,
		Error: &ErrorData{
			Code:    -1,
			Message: "test error",
		},
	}

	if msg.Error == nil {
		t.Fatal("error should not be nil")
	}
	if msg.Error.Code != -1 {
		t.Error("error code mismatch")
	}
}

// ErrorData tests
func TestErrorData_Create(t *testing.T) {
	err := &ErrorData{
		Code:    500,
		Message: "internal error",
	}

	if err.Code != 500 {
		t.Error("code mismatch")
	}
	if err.Message != "internal error" {
		t.Error("message mismatch")
	}
}

// Server tests
func TestNewServer(t *testing.T) {
	server := NewServer(nil)
	if server == nil {
		t.Fatal("server should not be nil")
	}
}

func TestNewServer_WithCallbacks(t *testing.T) {
	connectCalled := false
	disconnectCalled := false

	server := NewServer(nil,
		WithOnConnect(func(c *Connection) { connectCalled = true }),
		WithOnDisconnect(func(c *Connection) { disconnectCalled = true }),
	)

	if server.onConnect == nil {
		t.Error("onConnect should be set")
	}
	if server.onDisconnect == nil {
		t.Error("onDisconnect should be set")
	}

	// Use the variables to avoid compiler error
	_ = connectCalled
	_ = disconnectCalled
}

func TestServer_ConnectionCount_Empty(t *testing.T) {
	server := NewServer(nil)
	if server.ConnectionCount() != 0 {
		t.Errorf("expected 0, got %d", server.ConnectionCount())
	}
}

func TestServer_GetConnection_NotFound(t *testing.T) {
	server := NewServer(nil)
	_, ok := server.GetConnection("nonexistent")
	if ok {
		t.Error("should not find connection")
	}
}

func TestServer_GenerateID(t *testing.T) {
	server := NewServer(nil)
	id1 := server.generateID()
	id2 := server.generateID()

	if id1 == "" {
		t.Error("id should not be empty")
	}
	if id1 == id2 {
		t.Error("ids should be unique")
	}
}

func TestServer_Handler(t *testing.T) {
	server := NewServer(nil)
	handler := server.Handler()
	if handler == nil {
		t.Fatal("handler should not be nil")
	}
}

// Stream tests
func TestNewStream(t *testing.T) {
	stream := NewStream(nil)
	if stream == nil {
		t.Fatal("stream should not be nil")
	}
}

func TestStream_Push(t *testing.T) {
	stream := NewStream(nil)
	msg := &Message{Type: MessageTypeNotification}

	err := stream.Push(msg)
	if err != nil {
		t.Errorf("push error: %v", err)
	}

	// Should have message in channel
	select {
	case received := <-stream.Events():
		if received.Type != MessageTypeNotification {
			t.Error("wrong message type")
		}
	default:
		t.Error("should have message")
	}
}

func TestStream_Push_Closed(t *testing.T) {
	stream := NewStream(nil)
	stream.Close()

	err := stream.Push(&Message{})
	if err == nil {
		t.Error("should error on closed stream")
	}
}

func TestStream_IsClosed(t *testing.T) {
	stream := NewStream(nil)
	if stream.IsClosed() {
		t.Error("should not be closed")
	}
	stream.Close()
	if !stream.IsClosed() {
		t.Error("should be closed")
	}
}

func TestStream_Close_Idempotent(t *testing.T) {
	stream := NewStream(nil)
	stream.Close()
	stream.Close() // Should not panic
}

func TestStream_Events(t *testing.T) {
	stream := NewStream(nil)
	ch := stream.Events()
	if ch == nil {
		t.Error("events channel should not be nil")
	}
}

// Connection metadata tests
func TestConnection_SetGetMetadata(t *testing.T) {
	conn := &Connection{
		metadata: make(map[string]string),
	}

	conn.SetMetadata("key", "value")
	val, ok := conn.GetMetadata("key")
	if !ok {
		t.Error("should find metadata")
	}
	if val != "value" {
		t.Errorf("expected value, got %s", val)
	}
}

func TestConnection_GetMetadata_NotFound(t *testing.T) {
	conn := &Connection{
		metadata: make(map[string]string),
	}

	_, ok := conn.GetMetadata("nonexistent")
	if ok {
		t.Error("should not find metadata")
	}
}

func TestWithMetadata(t *testing.T) {
	conn := &Connection{
		metadata: make(map[string]string),
	}
	opt := WithMetadata("tenant", "t1")
	opt(conn)

	val, ok := conn.GetMetadata("tenant")
	if !ok || val != "t1" {
		t.Error("metadata not set correctly")
	}
}

// Helper tests
func TestUintToString(t *testing.T) {
	tests := []struct {
		input    uint64
		expected string
	}{
		{0, "0"},
		{1, "1"},
		{42, "42"},
		{100, "100"},
		{12345, "12345"},
	}

	for _, tt := range tests {
		result := uintToString(tt.input)
		if result != tt.expected {
			t.Errorf("uintToString(%d): expected %s, got %s", tt.input, tt.expected, result)
		}
	}
}

// Connection IsClosed tests
func TestConnection_IsClosed(t *testing.T) {
	conn := &Connection{
		metadata: make(map[string]string),
		done:     make(chan struct{}),
	}

	if conn.IsClosed() {
		t.Error("should not be closed initially")
	}
}

// Connection ID test
func TestConnection_ID(t *testing.T) {
	conn := &Connection{
		id:       "test-id",
		metadata: make(map[string]string),
	}

	if conn.ID() != "test-id" {
		t.Errorf("expected test-id, got %s", conn.ID())
	}
}

// Connection Send error tests
func TestConnection_Send_Closed(t *testing.T) {
	conn := &Connection{
		id:       "1",
		send:     make(chan *Message, 1),
		done:     make(chan struct{}),
		metadata: make(map[string]string),
	}
	conn.closed.Store(true)

	err := conn.Send(&Message{})
	if err == nil {
		t.Error("should error on closed connection")
	}
}

func TestConnection_Send_BufferFull(t *testing.T) {
	conn := &Connection{
		id:       "1",
		send:     make(chan *Message, 1),
		done:     make(chan struct{}),
		metadata: make(map[string]string),
	}

	// Fill buffer
	conn.Send(&Message{})

	// Should fail
	err := conn.Send(&Message{})
	if err == nil {
		t.Error("should error when buffer full")
	}
}

// Concurrent tests
func TestStream_Concurrent(t *testing.T) {
	stream := NewStream(nil)
	var wg sync.WaitGroup

	for i := 0; i < 50; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			stream.Push(&Message{})
		}()
	}

	wg.Wait()
	stream.Close()
}

func TestConnection_MetadataConcurrent(t *testing.T) {
	conn := &Connection{
		metadata: make(map[string]string),
	}

	var wg sync.WaitGroup
	for i := 0; i < 100; i++ {
		wg.Add(2)
		go func(n int) {
			defer wg.Done()
			conn.SetMetadata("key", "value")
		}(i)
		go func(n int) {
			defer wg.Done()
			conn.GetMetadata("key")
		}(i)
	}
	wg.Wait()
}

// Benchmark tests
func BenchmarkStream_Push(b *testing.B) {
	stream := NewStream(nil)
	msg := &Message{Type: MessageTypeNotification}

	go func() {
		for range stream.Events() {
		}
	}()

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		stream.Push(msg)
	}
}

func BenchmarkServer_GenerateID(b *testing.B) {
	server := NewServer(nil)
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		server.generateID()
	}
}

func BenchmarkUintToString(b *testing.B) {
	for i := 0; i < b.N; i++ {
		uintToString(uint64(i))
	}
}

// Message timestamp test
func TestMessage_Timestamp(t *testing.T) {
	now := time.Now()
	msg := Message{
		Type:      MessageTypeNotification,
		Timestamp: now,
	}

	if msg.Timestamp != now {
		t.Error("timestamp mismatch")
	}
}
