# gRPC Streaming Module

> Bidirectional streaming for real-time MCP communication

## Overview

The `grpcstream` module provides bidirectional streaming support for MCP over gRPC. Enables real-time notifications, events, and request/response patterns.

## Installation

```go
import "github.com/sentinel-community/gomcp/pkg/grpcstream"
```

## Quick Start

```go
// Create stream
stream := grpcstream.NewStream("client-1", 100)

// Send notification
stream.Send(grpcstream.NewNotification("tools/changed", nil))

// Receive messages
go func() {
    for {
        msg, err := stream.Receive()
        if err != nil {
            break
        }
        handleMessage(msg)
    }
}()

// Hub for multiple streams
hub := grpcstream.NewHub()
hub.Register(stream)
hub.Broadcast(grpcstream.NewEvent("server/ready", nil))
```

## API Reference

### Stream

```go
func NewStream(id string, bufferSize int) *Stream
func (s *Stream) Send(msg *Message) error
func (s *Stream) Receive() (*Message, error)
func (s *Stream) ReceiveWithTimeout(timeout time.Duration) (*Message, error)
func (s *Stream) SendChan() <-chan *Message
func (s *Stream) RecvChan() chan<- *Message
func (s *Stream) Close() error
func (s *Stream) IsClosed() bool
func (s *Stream) SetMetadata(key, value string)
func (s *Stream) GetMetadata(key string) (string, bool)
func (s *Stream) Done() <-chan struct{}
```

### Hub

```go
func NewHub() *Hub
func (h *Hub) Register(stream *Stream)
func (h *Hub) Unregister(id string)
func (h *Hub) Get(id string) (*Stream, bool)
func (h *Hub) Broadcast(msg *Message) int
func (h *Hub) BroadcastTo(msg *Message, ids ...string) int
func (h *Hub) Count() int
func (h *Hub) List() []string
func (h *Hub) OnConnect(fn func(*Stream))
func (h *Hub) OnDisconnect(fn func(*Stream))
func (h *Hub) Close()
```

### Message Types

| Type | Constant | Use Case |
|------|----------|----------|
| Request | `TypeRequest` | Client → Server call |
| Response | `TypeResponse` | Server → Client reply |
| Notification | `TypeNotification` | One-way notice |
| Event | `TypeEvent` | Server → Client event |

### Message Builders

```go
func NewNotification(method string, params any) *Message
func NewEvent(method string, params any) *Message
func NewRequest(method string, params any) *Message
func NewResponse(id string, result any) *Message
func NewErrorResponse(id string, code int, message string) *Message
```

### Message Structure

```go
type Message struct {
    ID        string
    Type      MessageType
    Method    string
    Params    any
    Result    any
    Error     *StreamError
    Timestamp time.Time
}
```

## Use Cases

- **Real-time notifications**: Tool/resource changes
- **Progress updates**: Long-running task progress
- **Event streaming**: Server-sent events
- **Bidirectional RPC**: Request/response over stream

## Examples

See [examples/grpcstream/](../examples/grpcstream/) for complete examples.
