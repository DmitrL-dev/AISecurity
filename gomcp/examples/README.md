# GoMCP Examples

This directory contains working examples for all major GoMCP features.

## Quick Start

```bash
# Run any example
cd examples/<name>
go run main.go
```

## Examples

| Example | Description | Module |
|---------|-------------|--------|
| [hooks](./hooks/) | Lifecycle callbacks and request interception | `pkg/hooks` |
| [tasks](./tasks/) | Async workflows with progress tracking | `pkg/tasks` |
| [completions](./completions/) | Auto-completion for prompts and resources | `pkg/completions` |
| [roots](./roots/) | Filesystem boundary management | `pkg/roots` |
| [sampling](./sampling/) | LLM inference requests | `pkg/sampling` |
| [elicitation](./elicitation/) | User input collection | `pkg/elicitation` |
| [client](./client/) | MCP client SDK usage | `pkg/client` |

## Features Demonstrated

### Hooks (`examples/hooks/`)
- Before/After hook registration
- Error handling hooks
- Timing middleware
- Hook execution order

### Tasks (`examples/tasks/`)
- Creating async tasks
- Progress updates
- State transitions
- Result handling

### Completions (`examples/completions/`)
- Static completion providers
- Dynamic (prefix) providers
- Prompt argument completion
- Resource URI completion

### Roots (`examples/roots/`)
- Adding/removing roots
- Path containment checks
- Change notifications
- JSON export

### Sampling (`examples/sampling/`)
- Request building
- Model preferences
- Response handling
- Streaming (simulated)

### Elicitation (`examples/elicitation/`)
- Boolean confirmations
- Text input with validation
- Select from options
- Number input with ranges

### Client (`examples/client/`)
- Stdio client creation
- Tool listing and calling
- Resource reading
- Prompt execution

## Protocol Version

All examples target **MCP Protocol 2025-11-25**.
