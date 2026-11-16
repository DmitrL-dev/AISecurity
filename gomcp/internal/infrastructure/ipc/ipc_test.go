package ipc

import (
	"context"
	"encoding/json"
	"io"
	"testing"
	"time"
)

func TestSendReceive(t *testing.T) {
	listener, err := Listen("test-pipe")
	if err != nil {
		t.Fatalf("Listen: %v", err)
	}
	defer listener.Close()

	// Accept in background.
	connCh := make(chan struct{})
	var receiver *Receiver
	go func() {
		conn, err := listener.Accept()
		if err != nil {
			t.Errorf("Accept: %v", err)
			return
		}
		receiver = NewReceiver(conn, "test")
		close(connCh)
	}()

	// Dial to the listener.
	conn, err := Dial("test-pipe")
	if err != nil {
		t.Fatalf("Dial: %v", err)
	}
	sender := NewSender(conn, "test")
	defer sender.Close()

	<-connCh // Wait for accept.

	// Send a message.
	payload := map[string]string{"foo": "bar"}
	msg, err := NewSOCMessage(SOCMsgEvent, payload)
	if err != nil {
		t.Fatalf("NewSOCMessage: %v", err)
	}

	if err := sender.Send(msg); err != nil {
		t.Fatalf("Send: %v", err)
	}

	// Receive it.
	got, err := receiver.Next()
	if err != nil {
		t.Fatalf("Next: %v", err)
	}

	if got.Type != SOCMsgEvent {
		t.Errorf("Type = %s, want %s", got.Type, SOCMsgEvent)
	}

	var gotPayload map[string]string
	if err := json.Unmarshal(got.Payload, &gotPayload); err != nil {
		t.Fatalf("unmarshal payload: %v", err)
	}
	if gotPayload["foo"] != "bar" {
		t.Errorf("payload foo = %s, want bar", gotPayload["foo"])
	}
}

func TestBufferedSender(t *testing.T) {
	listener, err := Listen("test-buffered")
	if err != nil {
		t.Fatalf("Listen: %v", err)
	}
	defer listener.Close()

	connCh := make(chan struct{})
	var receiver *Receiver
	go func() {
		conn, _ := listener.Accept()
		receiver = NewReceiver(conn, "test")
		close(connCh)
	}()

	conn, err := Dial("test-buffered")
	if err != nil {
		t.Fatalf("Dial: %v", err)
	}

	bs := NewBufferedSender(conn, "test-buffered")
	<-connCh

	// Send 10 messages.
	for i := 0; i < 10; i++ {
		msg, _ := NewSOCMessage(SOCMsgEvent, map[string]int{"n": i})
		if err := bs.Send(msg); err != nil {
			t.Fatalf("BufferedSend #%d: %v", i, err)
		}
	}

	// Receive 10 messages.
	for i := 0; i < 10; i++ {
		got, err := receiver.Next()
		if err != nil {
			t.Fatalf("Receive #%d: %v", i, err)
		}
		if got.Type != SOCMsgEvent {
			t.Errorf("#%d Type = %s, want soc_event", i, got.Type)
		}
	}

	bs.Close()
}

func TestDialWithRetry(t *testing.T) {
	// Start listener after a short delay.
	go func() {
		time.Sleep(300 * time.Millisecond)
		l, err := Listen("test-retry")
		if err != nil {
			t.Errorf("delayed Listen: %v", err)
			return
		}
		defer l.Close()
		conn, _ := l.Accept()
		if conn != nil {
			conn.Close()
		}
	}()

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	conn, err := DialWithRetry(ctx, "test-retry", 10)
	if err != nil {
		t.Fatalf("DialWithRetry: %v", err)
	}
	conn.Close()
}

func TestCloseProducesEOF(t *testing.T) {
	listener, err := Listen("test-eof")
	if err != nil {
		t.Fatalf("Listen: %v", err)
	}
	defer listener.Close()

	connCh := make(chan struct{})
	var receiver *Receiver
	go func() {
		conn, _ := listener.Accept()
		receiver = NewReceiver(conn, "test")
		close(connCh)
	}()

	conn, err := Dial("test-eof")
	if err != nil {
		t.Fatalf("Dial: %v", err)
	}

	<-connCh

	// Close sender side.
	conn.Close()

	// Receiver should get EOF.
	_, err = receiver.Next()
	if err != io.EOF {
		t.Errorf("expected io.EOF, got %v", err)
	}
}
