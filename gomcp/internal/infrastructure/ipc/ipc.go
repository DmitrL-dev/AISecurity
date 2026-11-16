// Package ipc provides a cross-platform inter-process communication layer
// for SENTINEL SOC Process Isolation (SEC-001).
//
// On Linux: Unix Domain Sockets with SO_PEERCRED validation.
// On Windows: Named Pipes (\\.\pipe\sentinel-soc-*).
//
// Protocol: newline-delimited JSON messages over the pipe.
// Each message has a Type field for routing (event, incident, ack, heartbeat).
package ipc

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net"
	"sync"
	"time"
)

// SOCMsgType identifies the SOC IPC message kind.
// Named differently from the Swarm transport Message to avoid conflicts.
type SOCMsgType string

const (
	SOCMsgEvent     SOCMsgType = "soc_event"     // Persisted event → correlate
	SOCMsgIncident  SOCMsgType = "soc_incident"  // Created incident → respond
	SOCMsgAck       SOCMsgType = "soc_ack"       // Acknowledgement
	SOCMsgHeartbeat SOCMsgType = "soc_heartbeat" // Keepalive

	// DefaultTimeout for IPC operations.
	DefaultTimeout = 5 * time.Second

	// MaxRetries for message delivery.
	MaxRetries = 3

	// BufferSize for pending messages when downstream is slow.
	BufferSize = 4096
)

// SOCMessage is the wire format for SOC process isolation IPC.
type SOCMessage struct {
	Type      SOCMsgType      `json:"type"`
	ID        string          `json:"id,omitempty"`
	Timestamp int64           `json:"ts"`
	Payload   json.RawMessage `json:"payload,omitempty"`
}

// NewSOCMessage creates a new SOC IPC message with the given type and payload.
func NewSOCMessage(t SOCMsgType, payload any) (*SOCMessage, error) {
	data, err := json.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("ipc: marshal payload: %w", err)
	}
	return &SOCMessage{
		Type:      t,
		ID:        fmt.Sprintf("%d", time.Now().UnixNano()),
		Timestamp: time.Now().Unix(),
		Payload:   data,
	}, nil
}

// Sender writes messages to a downstream IPC pipe.
type Sender struct {
	mu      sync.Mutex
	conn    net.Conn
	encoder *json.Encoder
	name    string
	logger  *slog.Logger
}

// NewSender wraps a net.Conn for sending JSON messages.
func NewSender(conn net.Conn, name string) *Sender {
	return &Sender{
		conn:    conn,
		encoder: json.NewEncoder(conn),
		name:    name,
		logger:  slog.Default().With("component", "ipc-sender", "pipe", name),
	}
}

// Send writes a message to the downstream pipe. Thread-safe.
func (s *Sender) Send(msg *SOCMessage) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if err := s.conn.SetWriteDeadline(time.Now().Add(DefaultTimeout)); err != nil {
		return fmt.Errorf("ipc: set deadline: %w", err)
	}

	if err := s.encoder.Encode(msg); err != nil {
		s.logger.Error("send failed", "type", msg.Type, "error", err)
		return fmt.Errorf("ipc: send %s: %w", msg.Type, err)
	}
	return nil
}

// SendWithRetry attempts to send a message with retries.
func (s *Sender) SendWithRetry(msg *SOCMessage) error {
	var lastErr error
	for i := 0; i < MaxRetries; i++ {
		if err := s.Send(msg); err != nil {
			lastErr = err
			s.logger.Warn("send retry", "attempt", i+1, "error", err)
			time.Sleep(100 * time.Millisecond * time.Duration(i+1))
			continue
		}
		return nil
	}
	return fmt.Errorf("ipc: send failed after %d retries: %w", MaxRetries, lastErr)
}

// Close shuts down the sender connection.
func (s *Sender) Close() error {
	return s.conn.Close()
}

// Receiver reads messages from an upstream IPC pipe.
type Receiver struct {
	conn    net.Conn
	scanner *bufio.Scanner
	name    string
	logger  *slog.Logger
}

// NewReceiver wraps a net.Conn for reading JSON messages.
func NewReceiver(conn net.Conn, name string) *Receiver {
	scanner := bufio.NewScanner(conn)
	scanner.Buffer(make([]byte, 64*1024), 1024*1024) // 1MB max message
	return &Receiver{
		conn:    conn,
		scanner: scanner,
		name:    name,
		logger:  slog.Default().With("component", "ipc-receiver", "pipe", name),
	}
}

// Next reads the next message, blocking until available.
// Returns io.EOF when the connection is closed.
func (r *Receiver) Next() (*SOCMessage, error) {
	if !r.scanner.Scan() {
		if err := r.scanner.Err(); err != nil {
			return nil, fmt.Errorf("ipc: read %s: %w", r.name, err)
		}
		return nil, io.EOF
	}

	var msg SOCMessage
	if err := json.Unmarshal(r.scanner.Bytes(), &msg); err != nil {
		r.logger.Warn("invalid message", "raw", r.scanner.Text(), "error", err)
		return nil, fmt.Errorf("ipc: unmarshal: %w", err)
	}
	return &msg, nil
}

// Close shuts down the receiver connection.
func (r *Receiver) Close() error {
	return r.conn.Close()
}

// Listener accepts incoming IPC connections on a named pipe.
type Listener struct {
	listener net.Listener
	name     string
	logger   *slog.Logger
}

// Listen creates a platform-specific named pipe listener.
// On Linux: Unix Domain Socket at /tmp/sentinel-<name>.sock
// On Windows: Named Pipe at \\.\pipe\sentinel-<name>
func Listen(name string) (*Listener, error) {
	l, err := platformListen(name)
	if err != nil {
		return nil, fmt.Errorf("ipc: listen %s: %w", name, err)
	}
	return &Listener{
		listener: l,
		name:     name,
		logger:   slog.Default().With("component", "ipc-listener", "pipe", name),
	}, nil
}

// Accept waits for and returns the next connection.
func (l *Listener) Accept() (net.Conn, error) {
	conn, err := l.listener.Accept()
	if err != nil {
		return nil, fmt.Errorf("ipc: accept %s: %w", l.name, err)
	}
	l.logger.Info("client connected", "remote", conn.RemoteAddr())
	return conn, nil
}

// Close shuts down the listener.
func (l *Listener) Close() error {
	return l.listener.Close()
}

// Addr returns the listener's address.
func (l *Listener) Addr() net.Addr {
	return l.listener.Addr()
}

// Dial connects to an existing named pipe.
func Dial(name string) (net.Conn, error) {
	return platformDial(name)
}

// DialWithRetry attempts to connect to a named pipe with retries.
// Useful during startup when the downstream process may not be ready.
func DialWithRetry(ctx context.Context, name string, maxRetries int) (net.Conn, error) {
	var lastErr error
	for i := 0; i < maxRetries; i++ {
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		default:
		}

		conn, err := platformDial(name)
		if err != nil {
			lastErr = err
			delay := time.Duration(i+1) * 500 * time.Millisecond
			slog.Warn("ipc: dial retry", "pipe", name, "attempt", i+1, "delay", delay, "error", err)
			time.Sleep(delay)
			continue
		}
		return conn, nil
	}
	return nil, fmt.Errorf("ipc: dial %s failed after %d retries: %w", name, maxRetries, lastErr)
}

// BufferedSender wraps a Sender with an async buffer for non-blocking sends.
// If the downstream pipe is slow, messages are buffered up to BufferSize.
type BufferedSender struct {
	sender  *Sender
	msgCh   chan *SOCMessage
	done    chan struct{}
	logger  *slog.Logger
}

// NewBufferedSender creates a buffered async sender.
func NewBufferedSender(conn net.Conn, name string) *BufferedSender {
	bs := &BufferedSender{
		sender: NewSender(conn, name),
		msgCh:  make(chan *SOCMessage, BufferSize),
		done:   make(chan struct{}),
		logger: slog.Default().With("component", "ipc-buffered", "pipe", name),
	}
	go bs.drain()
	return bs
}

// Send enqueues a message for async delivery. Non-blocking if buffer isn't full.
func (bs *BufferedSender) Send(msg *SOCMessage) error {
	select {
	case bs.msgCh <- msg:
		return nil
	default:
		bs.logger.Error("buffer full, dropping message", "type", msg.Type, "buffer_size", BufferSize)
		return fmt.Errorf("ipc: buffer full (%d)", BufferSize)
	}
}

// drain processes buffered messages in background.
func (bs *BufferedSender) drain() {
	defer close(bs.done)
	for msg := range bs.msgCh {
		if err := bs.sender.SendWithRetry(msg); err != nil {
			bs.logger.Error("buffered send failed", "type", msg.Type, "error", err)
		}
	}
}

// Close flushes remaining messages and shuts down.
func (bs *BufferedSender) Close() error {
	close(bs.msgCh)
	<-bs.done // wait for drain
	return bs.sender.Close()
}

// Pending returns the number of messages waiting in the buffer.
func (bs *BufferedSender) Pending() int {
	return len(bs.msgCh)
}
