# Hooks Module

> Lifecycle callbacks and request interception for MCP operations

## Overview

The `hooks` module provides a registry-based system for intercepting MCP operations at different lifecycle phases: before, after, and on error.

## Installation

```go
import "github.com/sentinel-community/gomcp/pkg/hooks"
```

## Quick Start

```go
registry := hooks.NewRegistry()

// Add before hook
registry.Register("tools/call", hooks.PhaseBefore, hooks.HandlerFunc(
    func(ctx context.Context, e *hooks.Event) error {
        log.Printf("Calling tool: %v", e.Params)
        return nil
    },
))

// Add after hook
registry.Register("tools/call", hooks.PhaseAfter, hooks.HandlerFunc(
    func(ctx context.Context, e *hooks.Event) error {
        log.Printf("Result: %v", e.Result)
        return nil
    },
))

// Execute hooks
registry.ExecuteBefore(ctx, "tools/call", params)
registry.ExecuteAfter(ctx, "tools/call", result)
```

## API Reference

### Registry

```go
func NewRegistry() *Registry
```
Creates a new hook registry.

---

```go
func (r *Registry) Register(method string, phase Phase, handler Handler)
```
Registers a hook for a method and phase.

---

```go
func (r *Registry) RegisterWithOrder(method string, phase Phase, handler Handler, order int)
```
Registers a hook with explicit execution order. Lower order = runs first.

---

```go
func (r *Registry) Execute(ctx context.Context, method string, phase Phase, event *Event) error
```
Executes all hooks for method/phase. Stops on first error.

---

```go
func (r *Registry) ExecuteBefore(ctx context.Context, method string, params any) error
func (r *Registry) ExecuteAfter(ctx context.Context, method string, result any) error
func (r *Registry) ExecuteError(ctx context.Context, method string, err error) error
```
Convenience methods for specific phases.

---

```go
func (r *Registry) Has(method string, phase Phase) bool
```
Checks if any hooks are registered.

---

```go
func (r *Registry) Clear()
```
Removes all registered hooks.

### Phases

| Phase | Constant | When |
|-------|----------|------|
| Before | `hooks.PhaseBefore` | Before operation executes |
| After | `hooks.PhaseAfter` | After successful completion |
| Error | `hooks.PhaseError` | When operation fails |

### Handler Interface

```go
type Handler interface {
    Handle(ctx context.Context, event *Event) error
}

// Function adapter
type HandlerFunc func(ctx context.Context, event *Event) error
```

### Event Structure

```go
type Event struct {
    Phase   Phase
    Method  string
    Params  any
    Result  any
    Error   error
    Context map[string]any
}
```

### Built-in Method Constants

```go
const (
    MethodToolsCall     = "tools/call"
    MethodResourcesRead = "resources/read"
    MethodPromptsGet    = "prompts/get"
    MethodInitialize    = "initialize"
    MethodPing          = "ping"
)
```

### Middleware Pattern

```go
wrapped := hooks.Middleware(registry)(handler)
```

Wraps a handler with automatic before/after/error hook execution.

## Use Cases

- **Logging**: Log all tool calls and results
- **Metrics**: Track operation timing and counts
- **Validation**: Validate params before execution
- **Transformation**: Modify results after execution
- **Error handling**: Custom error recovery
- **Rate limiting**: Check quotas before operations

## Examples

See [examples/hooks/](../examples/hooks/) for complete examples.
