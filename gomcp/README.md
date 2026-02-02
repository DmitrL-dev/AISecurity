# GoMCP

**Production-Grade Model Context Protocol Server in Go**

MCP 2025-11-25 compliant with enterprise security, multi-tenancy, and observability.

[![Protocol](https://img.shields.io/badge/MCP-2025--11--25-blue)](https://modelcontextprotocol.io)
[![Tests](https://img.shields.io/badge/tests-550%2B-green)](./pkg)
[![Full Ralph](https://img.shields.io/badge/Full%20Ralph-1000%20iterations-brightgreen)](./docs)

## Features

### Core MCP Protocol
- **Tasks**: Async workflows with progress tracking
- **Sampling**: LLM inference from server to client
- **Elicitation**: User input collection
- **Completions**: Auto-completion for prompts/resources
- **Roots**: Filesystem boundary management
- **Hooks**: Lifecycle callbacks and middleware

### Enterprise
- **Security Hardening**: Input validation, audit logging, rate limiting
- **Multi-tenant Support**: Namespace isolation with quotas  
- **Session Management**: Per-session tools and context
- **gRPC Streaming**: Bidirectional real-time communication

### Operations
- **HTTP Mode**: REST API for Docker/Kubernetes deployments
- **Hot-reload**: Zero-downtime tool configuration updates
- **Health Checks**: Kubernetes-ready liveness/readiness probes
- **Observability**: OpenTelemetry + Prometheus metrics

### SDKs
- **Go Client SDK**: Native MCP client
- **TypeScript SDK**: Type-safe client library
- **Python SDK**: Full-featured client

## Installation

```bash
go install github.com/sentinel-community/gomcp/cmd/gomcp-server@latest
```

## Quick Start

### Run Server

```bash
# Stdio mode (MCP v1 compatible)
gomcp-server -mode=stdio

# HTTP mode (Docker-native)
gomcp-server -mode=http

# With custom timeout
gomcp-server -mode=http -timeout=60s
```

### HTTP API

```bash
# List tools
curl http://localhost:8080/v1/tools

# Call a tool
curl -X POST http://localhost:8080/v1/tools/call \
  -H "Content-Type: application/json" \
  -d '{"tool": "echo", "arguments": {"msg": "hello"}}'

# Batch call
curl -X POST http://localhost:8080/v1/tools/batch \
  -H "Content-Type: application/json" \
  -d '{"requests": [{"tool": "t1"}, {"tool": "t2"}], "parallel": true}'
```

### Health Endpoints

```bash
curl http://localhost:8080/health    # Full health
curl http://localhost:8080/healthz   # Liveness
curl http://localhost:8080/readyz    # Readiness
curl http://localhost:8080/metrics   # Prometheus metrics
```

## Packages

### MCP Protocol (2025-11-25)

| Package | Description |
|---------|-------------|
| `pkg/tasks` | Async workflows with state machine |
| `pkg/sampling` | LLM inference requests |
| `pkg/elicitation` | User input collection |
| `pkg/completions` | Auto-completion providers |
| `pkg/roots` | Filesystem boundary management |
| `pkg/hooks` | Lifecycle callbacks & middleware |
| `pkg/session` | Per-session state & tools |
| `pkg/client` | Go MCP client SDK |
| `pkg/sse` | Server-Sent Events transport |
| `pkg/grpcstream` | Bidirectional gRPC streaming |

### Enterprise

| Package | Description |
|---------|-------------|
| `pkg/supervisor` | Worker management and tool call orchestration |
| `pkg/security` | Input validation, audit logging, rate limiting |
| `pkg/httpmode` | REST API server for Docker deployments |
| `pkg/health` | Health check endpoints and component monitoring |
| `pkg/tenant` | Multi-tenant namespace isolation |
| `pkg/batching` | Parallel batch tool execution |
| `pkg/hotreload` | Zero-downtime config updates |
| `pkg/adapter/mcpv1` | MCP v1 protocol compatibility |

## Usage Examples

### Security Validation

```go
import "github.com/sentinel-community/gomcp/pkg/security"

validator := security.DefaultValidator()
result := validator.ValidateJSON(input)
if !result.Valid {
    log.Printf("Validation failed: %v", result.Errors)
}
```

### Multi-tenant Support

```go
import "github.com/sentinel-community/gomcp/pkg/tenant"

tm := tenant.NewManager()
t, _ := tm.CreateTenant("customer1", "Customer 1", tenant.DefaultQuotas())
t.SetAllowedTools([]string{"read_file", "list_dir"})

ctx := tenant.WithTenant(ctx, t)
```

### Batch Processing

```go
import "github.com/sentinel-community/gomcp/pkg/batching"

batch := batching.NewBuilder().
    Add("r1", "tool1", args1).
    Add("r2", "tool2", args2).
    Parallel(5).
    Build()

result := processor.Process(ctx, batch)
fmt.Printf("Success: %d, Errors: %d", result.SuccessCount, result.ErrorCount)
```

### Health Checks

```go
import "github.com/sentinel-community/gomcp/pkg/health"

srv := health.NewServer("1.0.0")
srv.RegisterChecker(health.WorkerChecker(getWorkerStats))
srv.RegisterHandlers(mux)
```

## Testing

```bash
# Run all tests
go test ./...

# Run with verbose output
go test ./... -v

# Run specific package
go test ./pkg/security/...
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    gomcp-server                         │
├─────────────┬─────────────┬─────────────┬──────────────┤
│   Stdio     │   HTTP      │   gRPC      │   Health     │
│   Adapter   │   Mode      │   Server    │   Endpoints  │
├─────────────┴─────────────┴─────────────┴──────────────┤
│                     Supervisor                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │
│  │ Security │ │ Tenant   │ │ Batching │ │ HotReload │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────┘  │
├─────────────────────────────────────────────────────────┤
│                      Workers                            │
└─────────────────────────────────────────────────────────┘
```

## License

Apache-2.0
