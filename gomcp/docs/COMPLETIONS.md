# Completions Module

> Auto-completion support for prompts and resources

## Overview

The `completions` module provides auto-completion suggestions for prompt arguments and resource URIs, enhancing developer experience.

## Installation

```go
import "github.com/sentinel-community/gomcp/pkg/completions"
```

## Quick Start

```go
manager := completions.NewManager()

// Register static provider
manager.RegisterProvider(
    completions.RefTypePrompt,
    "my_prompt",
    completions.NewStaticProvider([]string{"opt1", "opt2", "opt3"}),
)

// Get completions
resp, _ := manager.Complete(ctx, &completions.Request{
    Ref: completions.CompletionRef{
        Type: completions.RefTypePrompt,
        Name: "my_prompt",
    },
    Argument: completions.CompletionArg{
        Name:  "option",
        Value: "opt",  // prefix to match
    },
})

// resp.Completion.Values = ["opt1", "opt2", "opt3"]
```

## API Reference

### Manager

```go
func NewManager() *Manager
```
Creates a new completion manager.

---

```go
func (m *Manager) RegisterProvider(refType, name string, provider Provider)
```
Registers a provider for a reference type and name.

---

```go
func (m *Manager) Complete(ctx context.Context, req *Request) (*Response, error)
```
Generates completions for a request.

### Provider Interface

```go
type Provider interface {
    Complete(ctx context.Context, req *Request) (*Response, error)
    Supports(ref CompletionRef) bool
}
```

### Built-in Providers

#### StaticProvider
```go
provider := completions.NewStaticProvider([]string{"a", "b", "c"})
```
Returns values that match the input prefix.

#### PrefixProvider
```go
provider := completions.NewPrefixProvider(func() []string {
    return getValuesFromDatabase()
})
```
Dynamic values via callback, filtered by prefix.

#### ProviderFunc
```go
provider := completions.ProviderFunc(func(ctx context.Context, req *Request) (*Response, error) {
    return &Response{
        Completion: Completion{Values: []string{"custom"}},
    }, nil
})
```
Function adapter for custom logic.

### Request/Response

```go
type Request struct {
    Ref      CompletionRef
    Argument CompletionArg
}

type CompletionRef struct {
    Type string // "ref/prompt" or "ref/resource"
    Name string
    URI  string
}

type CompletionArg struct {
    Name  string
    Value string // prefix to match
}

type Response struct {
    Completion Completion
}

type Completion struct {
    Values  []string
    Total   int
    HasMore bool
}
```

### Reference Types

```go
const (
    RefTypePrompt   = "ref/prompt"
    RefTypeResource = "ref/resource"
)
```

### JSON-RPC Method

| Method | Description |
|--------|-------------|
| `completion/complete` | Get completion suggestions |

## Examples

See [examples/completions/](../examples/completions/) for complete examples.
