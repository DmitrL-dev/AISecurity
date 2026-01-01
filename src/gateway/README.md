# ⚡ SENTINEL Gateway

**High-performance Go gateway for AI security filtering**

## Overview

The Gateway provides a production-ready reverse proxy that intercepts AI/LLM traffic and applies security analysis via the Python Brain component.

## Architecture

```
Client → Gateway (Go) → Brain (Python) → LLM Provider
                ↓
        Security Analysis
        - Prompt Injection Detection
        - Jailbreak Prevention
        - PII Filtering
        - Rate Limiting
```

## Key Features

| Feature | Description |
|---------|-------------|
| **<10ms Latency** | Go Fiber framework for minimal overhead |
| **PoW Challenge** | Hashcash-style anti-DDoS protection |
| **Compute Guardian** | Cost estimation before LLM calls |
| **gRPC/REST** | Dual protocol support |
| **WebSocket** | Real-time streaming support |

## Quick Start

```bash
# Build
cd src/gateway
go build -o sentinel-gateway ./cmd

# Run
./sentinel-gateway --brain-url http://localhost:8000
```

## Configuration

```yaml
# config.yaml
server:
  port: 8080
  timeout: 30s

brain:
  url: http://localhost:8000
  timeout: 5s

security:
  pow_enabled: true
  pow_difficulty: 16
  rate_limit: 100  # req/sec
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/analyze` | POST | Analyze prompt for threats |
| `/v1/chat` | POST | Proxied chat completion |
| `/health` | GET | Health check |
| `/metrics` | GET | Prometheus metrics |

## Integration

```go
// Example: Custom middleware
func SecurityMiddleware(c *fiber.Ctx) error {
    result := brain.Analyze(c.Body())
    if !result.IsSafe {
        return c.Status(403).JSON(result)
    }
    return c.Next()
}
```

## Performance

- **Throughput**: 1000+ req/sec
- **P99 Latency**: <10ms (excluding brain analysis)
- **Memory**: ~50MB base

## Documentation

- [Deployment Guide](../docs/guides/deployment-en.md)
- [Configuration](../docs/guides/configuration-en.md)
- [Integration](../docs/guides/integration-en.md)

---

**Part of [SENTINEL AI Security Platform](../README.md)**
