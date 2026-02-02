# Elicitation Module

> User input collection for MCP operations

## Overview

The `elicitation` module enables MCP servers to request user input for confirmations, selections, and data entry.

## Installation

```go
import "github.com/sentinel-community/gomcp/pkg/elicitation"
```

## Quick Start

```go
// Create request builders
confirmReq := elicitation.BooleanInput("confirm", 
    "Delete files?", 
    "This cannot be undone")

textReq := elicitation.TextInput("name",
    "Enter project name:",
    "Must be lowercase").
    WithValidation(`^[a-z-]+$`)

selectReq := elicitation.SelectInput("lang",
    "Choose language:",
    []string{"go", "python", "rust"}).
    WithDefault("go")

numberReq := elicitation.NumberInput("count",
    "How many items?",
    "Enter a positive number").
    WithRange(1, 100)
```

## API Reference

### Input Builders

#### BooleanInput
```go
func BooleanInput(id, title, description string) *Request
```
Creates yes/no confirmation request.

#### TextInput
```go
func TextInput(id, title, description string) *TextInputBuilder
func (b *TextInputBuilder) WithValidation(pattern string) *TextInputBuilder
func (b *TextInputBuilder) WithDefault(value string) *TextInputBuilder
func (b *TextInputBuilder) Build() *Request
```

#### SelectInput
```go
func SelectInput(id, title string, options []string) *SelectInputBuilder
func (b *SelectInputBuilder) WithDefault(value string) *SelectInputBuilder
func (b *SelectInputBuilder) Build() *Request
```

#### NumberInput
```go
func NumberInput(id, title, description string) *NumberInputBuilder
func (b *NumberInputBuilder) WithRange(min, max float64) *NumberInputBuilder
func (b *NumberInputBuilder) WithDefault(value float64) *NumberInputBuilder
func (b *NumberInputBuilder) Build() *Request
```

#### ObjectInput
```go
func ObjectInput(id, title string, schema map[string]any) *Request
```
Creates complex object input request.

### Handler Interface

```go
type Handler interface {
    Handle(ctx context.Context, req *Request) (*Response, error)
}
```

### MockHandler (Testing)

```go
handler := elicitation.NewMockHandler(map[string]any{
    "confirm": true,
    "name":    "my-project",
    "lang":    "go",
})
```

### Request/Response

```go
type Request struct {
    RequestID   string
    Title       string
    Description string
    Type        InputType
    Schema      map[string]any
}

type Response struct {
    Action string // "accept" or "decline"
    Value  any
}
```

### Input Types

| Type | Constant |
|------|----------|
| Boolean | `TypeBoolean` |
| Text | `TypeText` |
| Select | `TypeSelect` |
| Number | `TypeNumber` |
| Object | `TypeObject` |

### JSON-RPC Method

| Method | Description |
|--------|-------------|
| `elicitation/create` | Request user input |

## Examples

See [examples/elicitation/](../examples/elicitation/) for complete examples.
