package grpcstream

import (
	"sync"
	"testing"
	"time"
)

func TestNewStream(t *testing.T) {
	s := NewStream("test-1", 10)

	if s.ID != "test-1" {
		t.Error("ID mismatch")
	}

	if s.IsClosed() {
		t.Error("new stream should not be closed")
	}
}

func TestStream_SendReceive(t *testing.T) {
	s := NewStream("test", 10)

	msg := &Message{
		ID:     "msg-1",
		Type:   TypeNotification,
		Method: "test/notify",
	}

	// Simulate receiver
	go func() {
		s.recv <- msg
	}()

	received, err := s.Receive()
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if received.ID != "msg-1" {
		t.Error("message ID mismatch")
	}
}

func TestStream_Send(t *testing.T) {
	s := NewStream("test", 10)

	msg := NewNotification("test/event", nil)

	err := s.Send(msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Check message is in send channel
	select {
	case received := <-s.SendChan():
		if received.Method != "test/event" {
			t.Error("method mismatch")
		}
	default:
		t.Error("message not sent")
	}
}

func TestStream_SendClosed(t *testing.T) {
	s := NewStream("test", 10)
	s.Close()

	err := s.Send(&Message{})
	if err != ErrStreamClosed {
		t.Errorf("expected ErrStreamClosed, got %v", err)
	}
}

func TestStream_ReceiveWithTimeout(t *testing.T) {
	s := NewStream("test", 10)

	_, err := s.ReceiveWithTimeout(10 * time.Millisecond)
	if err != ErrTimeout {
		t.Errorf("expected ErrTimeout, got %v", err)
	}
}

func TestStream_Close(t *testing.T) {
	s := NewStream("test", 10)

	err := s.Close()
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if !s.IsClosed() {
		t.Error("stream should be closed")
	}

	// Double close should error
	err = s.Close()
	if err != ErrStreamClosed {
		t.Errorf("expected ErrStreamClosed, got %v", err)
	}
}

func TestStream_Metadata(t *testing.T) {
	s := NewStream("test", 10)

	s.SetMetadata("user", "john")

	val, ok := s.GetMetadata("user")
	if !ok || val != "john" {
		t.Error("metadata mismatch")
	}

	_, ok = s.GetMetadata("nonexistent")
	if ok {
		t.Error("should not find nonexistent key")
	}
}

func TestStream_Done(t *testing.T) {
	s := NewStream("test", 10)

	select {
	case <-s.Done():
		t.Error("done should not be closed yet")
	default:
		// Good
	}

	s.Close()

	select {
	case <-s.Done():
		// Good
	default:
		t.Error("done should be closed")
	}
}

func TestHub_RegisterUnregister(t *testing.T) {
	h := NewHub()
	s := NewStream("stream-1", 10)

	h.Register(s)

	if h.Count() != 1 {
		t.Errorf("expected 1 stream, got %d", h.Count())
	}

	h.Unregister("stream-1")

	if h.Count() != 0 {
		t.Error("stream should be unregistered")
	}
}

func TestHub_Get(t *testing.T) {
	h := NewHub()
	s := NewStream("stream-1", 10)
	h.Register(s)

	got, ok := h.Get("stream-1")
	if !ok {
		t.Error("should find stream")
	}

	if got.ID != "stream-1" {
		t.Error("ID mismatch")
	}

	_, ok = h.Get("nonexistent")
	if ok {
		t.Error("should not find nonexistent stream")
	}
}

func TestHub_Broadcast(t *testing.T) {
	h := NewHub()

	s1 := NewStream("s1", 10)
	s2 := NewStream("s2", 10)
	s3 := NewStream("s3", 10)

	h.Register(s1)
	h.Register(s2)
	h.Register(s3)

	msg := NewNotification("broadcast", nil)
	count := h.Broadcast(msg)

	if count != 3 {
		t.Errorf("expected 3 broadcasts, got %d", count)
	}
}

func TestHub_BroadcastTo(t *testing.T) {
	h := NewHub()

	s1 := NewStream("s1", 10)
	s2 := NewStream("s2", 10)
	s3 := NewStream("s3", 10)

	h.Register(s1)
	h.Register(s2)
	h.Register(s3)

	msg := NewNotification("targeted", nil)
	count := h.BroadcastTo(msg, "s1", "s3")

	if count != 2 {
		t.Errorf("expected 2 broadcasts, got %d", count)
	}
}

func TestHub_List(t *testing.T) {
	h := NewHub()

	h.Register(NewStream("s1", 10))
	h.Register(NewStream("s2", 10))

	ids := h.List()
	if len(ids) != 2 {
		t.Errorf("expected 2 IDs, got %d", len(ids))
	}
}

func TestHub_OnConnect(t *testing.T) {
	h := NewHub()

	var connected bool
	var mu sync.Mutex

	h.OnConnect(func(s *Stream) {
		mu.Lock()
		connected = true
		mu.Unlock()
	})

	h.Register(NewStream("s1", 10))
	time.Sleep(10 * time.Millisecond)

	mu.Lock()
	if !connected {
		t.Error("OnConnect should be called")
	}
	mu.Unlock()
}

func TestHub_OnDisconnect(t *testing.T) {
	h := NewHub()

	var disconnected bool
	var mu sync.Mutex

	h.OnDisconnect(func(s *Stream) {
		mu.Lock()
		disconnected = true
		mu.Unlock()
	})

	h.Register(NewStream("s1", 10))
	h.Unregister("s1")
	time.Sleep(10 * time.Millisecond)

	mu.Lock()
	if !disconnected {
		t.Error("OnDisconnect should be called")
	}
	mu.Unlock()
}

func TestHub_Close(t *testing.T) {
	h := NewHub()

	h.Register(NewStream("s1", 10))
	h.Register(NewStream("s2", 10))

	h.Close()

	if h.Count() != 0 {
		t.Error("all streams should be closed")
	}
}

func TestNewNotification(t *testing.T) {
	msg := NewNotification("test/notify", map[string]any{"key": "value"})

	if msg.Type != TypeNotification {
		t.Error("type should be notification")
	}

	if msg.Method != "test/notify" {
		t.Error("method mismatch")
	}
}

func TestNewEvent(t *testing.T) {
	msg := NewEvent("test/event", nil)

	if msg.Type != TypeEvent {
		t.Error("type should be event")
	}
}

func TestNewRequest(t *testing.T) {
	msg := NewRequest("test/request", nil)

	if msg.Type != TypeRequest {
		t.Error("type should be request")
	}
}

func TestNewResponse(t *testing.T) {
	msg := NewResponse("req-1", "success")

	if msg.Type != TypeResponse {
		t.Error("type should be response")
	}

	if msg.ID != "req-1" {
		t.Error("ID mismatch")
	}

	if msg.Result != "success" {
		t.Error("result mismatch")
	}
}

func TestNewErrorResponse(t *testing.T) {
	msg := NewErrorResponse("req-1", 500, "internal error")

	if msg.Error == nil {
		t.Fatal("error should not be nil")
	}

	if msg.Error.Code != 500 {
		t.Error("code mismatch")
	}
}

func TestMessage_ToJSON(t *testing.T) {
	msg := NewNotification("test", nil)

	data, err := msg.ToJSON()
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if len(data) == 0 {
		t.Error("JSON should not be empty")
	}
}

func TestFromJSON(t *testing.T) {
	original := NewNotification("test/method", map[string]any{"key": "value"})
	data, _ := original.ToJSON()

	parsed, err := FromJSON(data)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if parsed.Method != "test/method" {
		t.Error("method mismatch")
	}
}

func TestFromJSON_Invalid(t *testing.T) {
	_, err := FromJSON([]byte("invalid json"))
	if err == nil {
		t.Error("should error on invalid JSON")
	}
}

func TestMessageTypes(t *testing.T) {
	if TypeRequest != "request" {
		t.Error("invalid type")
	}
	if TypeResponse != "response" {
		t.Error("invalid type")
	}
	if TypeNotification != "notification" {
		t.Error("invalid type")
	}
	if TypeEvent != "event" {
		t.Error("invalid type")
	}
}

func TestGenerateID(t *testing.T) {
	id1 := generateID()
	id2 := generateID()

	if id1 == id2 {
		t.Error("IDs should be unique")
	}
}
