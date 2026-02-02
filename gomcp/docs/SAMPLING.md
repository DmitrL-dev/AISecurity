# Sampling Module

> LLM inference requests via MCP protocol

## Overview

The `sampling` module enables MCP servers to request LLM inference from connected clients. This reverses the typical client-server relationship, allowing servers to leverage client-side LLM capabilities.

## Installation

```go
import "github.com/sentinel-community/gomcp/pkg/sampling"
```

## Quick Start

```go
manager := sampling.NewManager()

// Set handler (connects to client)
manager.SetHandler(myClientHandler)

// Build request
req := sampling.NewRequestBuilder().
    WithSystemPrompt("You are helpful.").
    AddUserMessage("Explain Go interfaces.").
    WithModel("claude-3-sonnet").
    WithMaxTokens(500).
    Build()

// Execute
resp, _ := manager.Sample(ctx, req)
fmt.Println(resp.Content.Text)
```

## API Reference

### Manager

```go
func NewManager() *Manager
func (m *Manager) SetHandler(h Handler)
func (m *Manager) Sample(ctx context.Context, req *Request) (*Response, error)
```

### RequestBuilder

```go
func NewRequestBuilder() *RequestBuilder
func (b *RequestBuilder) WithSystemPrompt(prompt string) *RequestBuilder
func (b *RequestBuilder) AddUserMessage(text string) *RequestBuilder
func (b *RequestBuilder) AddAssistantMessage(text string) *RequestBuilder
func (b *RequestBuilder) WithModel(models ...string) *RequestBuilder
func (b *RequestBuilder) WithMaxTokens(n int) *RequestBuilder
func (b *RequestBuilder) WithTemperature(t float64) *RequestBuilder
func (b *RequestBuilder) WithStopSequences(seqs ...string) *RequestBuilder
func (b *RequestBuilder) Build() *Request
```

### Request/Response

```go
type Request struct {
    Messages         []Message
    ModelPreferences ModelPreferences
    SystemPrompt     string
    MaxTokens        int
}

type Response struct {
    Model      string
    StopReason string
    Content    Content
}

type Content struct {
    Type string // "text" or "image"
    Text string
}
```

### JSON-RPC Method

| Method | Description |
|--------|-------------|
| `sampling/createMessage` | Request LLM inference |

## Examples

See [examples/sampling/](../examples/sampling/) for complete examples.
