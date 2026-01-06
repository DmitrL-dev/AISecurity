# Shield REST API — Implementation Plan

> **Priority:** P1  
> **Estimated Effort:** 3-4 days  
> **Goal:** HTTP server with OpenAPI spec for Shield

---

## Overview

Add REST API layer to Shield, enabling:
- HTTP-based guard invocation
- JSON request/response
- OpenAPI 3.0 specification
- Health checks and metrics endpoints

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Shield REST API                       │
├─────────────────────────────────────────────────────────┤
│  HTTP Server (Pure C, no dependencies)                  │
│  ├── Listener (port 8080)                               │
│  ├── Request Parser (HTTP/1.1)                          │
│  ├── Router (path → handler)                            │
│  ├── JSON Parser (minimal, embedded)                    │
│  └── Response Writer                                    │
├─────────────────────────────────────────────────────────┤
│  Routes                                                 │
│  ├── POST /api/v1/analyze     → Guard analysis          │
│  ├── POST /api/v1/guard/llm   → LLM Guard               │
│  ├── POST /api/v1/guard/rag   → RAG Guard               │
│  ├── POST /api/v1/guard/agent → Agent Guard             │
│  ├── GET  /health             → Health check            │
│  ├── GET  /metrics            → Prometheus metrics      │
│  └── GET  /openapi.json       → OpenAPI spec            │
├─────────────────────────────────────────────────────────┤
│  Existing Shield Core                                   │
│  └── Guards, Protocols, State, CLI                      │
└─────────────────────────────────────────────────────────┘
```

---

## File Structure

```
shield/
├── src/
│   └── http/                    # NEW: HTTP module
│       ├── http_server.c        # Main server loop
│       ├── http_server.h        # Server interface
│       ├── http_parser.c        # HTTP request parsing
│       ├── http_parser.h        # Parser interface
│       ├── http_router.c        # Route matching
│       ├── http_router.h        # Router interface
│       ├── http_response.c      # Response building
│       ├── http_response.h      # Response interface
│       ├── json_parser.c        # Minimal JSON parser
│       ├── json_parser.h        # JSON interface
│       ├── json_builder.c       # JSON response builder
│       ├── json_builder.h       # Builder interface
│       └── routes/              # Route handlers
│           ├── route_analyze.c  # POST /api/v1/analyze
│           ├── route_guards.c   # Guard-specific routes
│           ├── route_health.c   # GET /health
│           └── route_metrics.c  # GET /metrics
├── include/
│   └── shield_http.h            # Public HTTP API
└── data/
    └── openapi.json             # OpenAPI 3.0 spec
```

---

## Implementation Phases

### Phase 1: HTTP Core (Day 1)
- [ ] `http_server.c` — TCP listener, accept loop
- [ ] `http_parser.c` — Parse HTTP/1.1 requests
- [ ] `http_response.c` — Build HTTP responses
- [ ] Basic GET /health endpoint

### Phase 2: JSON Layer (Day 1-2)
- [ ] `json_parser.c` — Parse JSON request body
- [ ] `json_builder.c` — Build JSON responses
- [ ] Error handling with JSON errors

### Phase 3: Routes (Day 2-3)
- [ ] `http_router.c` — Path matching, method dispatch
- [ ] `route_analyze.c` — Main analysis endpoint
- [ ] `route_guards.c` — Individual guard endpoints
- [ ] `route_metrics.c` — Prometheus format

### Phase 4: Integration (Day 3-4)
- [ ] Connect routes to Shield guards
- [ ] Thread pool for concurrent requests
- [ ] Connection keep-alive
- [ ] OpenAPI spec generation

---

## API Endpoints

### POST /api/v1/analyze

Main analysis endpoint — runs all enabled guards.

**Request:**
```json
{
  "input": "User prompt to analyze",
  "context": {
    "session_id": "sess_123",
    "user_id": "user_456"
  },
  "guards": ["llm", "rag", "agent"],
  "options": {
    "include_details": true
  }
}
```

**Response:**
```json
{
  "verdict": "BLOCKED",
  "risk_score": 0.92,
  "latency_ms": 0.42,
  "guards": {
    "llm": {
      "triggered": true,
      "score": 0.92,
      "reason": "Prompt injection detected"
    },
    "rag": {
      "triggered": false,
      "score": 0.15
    }
  },
  "request_id": "req_abc123"
}
```

### POST /api/v1/guard/{guard_name}

Individual guard endpoint.

**Guards:** `llm`, `rag`, `agent`, `tool`, `mcp`, `api`

### GET /health

```json
{
  "status": "healthy",
  "version": "4.1.0",
  "uptime_seconds": 3600,
  "guards_enabled": 6
}
```

### GET /metrics

Prometheus format:
```
shield_requests_total{endpoint="/api/v1/analyze"} 1234
shield_request_duration_ms{quantile="0.99"} 0.85
shield_guards_triggered{guard="llm"} 456
```

---

## Code Snippets

### http_server.h
```c
#ifndef SHIELD_HTTP_SERVER_H
#define SHIELD_HTTP_SERVER_H

#include <stdint.h>
#include <stdbool.h>

typedef struct {
    uint16_t port;
    int backlog;
    int max_connections;
    int thread_pool_size;
    bool enable_keep_alive;
} http_server_config_t;

typedef struct http_server http_server_t;

http_server_t* http_server_create(const http_server_config_t *config);
int http_server_start(http_server_t *server);
void http_server_stop(http_server_t *server);
void http_server_destroy(http_server_t *server);

#endif
```

### Main server loop
```c
int http_server_start(http_server_t *server) {
    server->socket_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server->socket_fd < 0) return -1;
    
    struct sockaddr_in addr = {
        .sin_family = AF_INET,
        .sin_port = htons(server->config.port),
        .sin_addr.s_addr = INADDR_ANY
    };
    
    if (bind(server->socket_fd, (struct sockaddr*)&addr, sizeof(addr)) < 0)
        return -1;
    
    if (listen(server->socket_fd, server->config.backlog) < 0)
        return -1;
    
    server->running = true;
    
    while (server->running) {
        int client_fd = accept(server->socket_fd, NULL, NULL);
        if (client_fd < 0) continue;
        
        // Dispatch to thread pool
        thread_pool_submit(server->pool, handle_connection, (void*)(intptr_t)client_fd);
    }
    
    return 0;
}
```

---

## Dependencies

**Zero external dependencies** — all in Pure C:
- Socket API (POSIX/Winsock)
- pthreads (POSIX) / Windows threads
- Custom JSON parser (embedded)

---

## Testing Plan

1. **Unit Tests:**
   - `test_http_parser.c` — Request parsing
   - `test_json_parser.c` — JSON parsing
   - `test_router.c` — Route matching

2. **Integration Tests:**
   - curl-based endpoint tests
   - Load testing with wrk/hey

3. **Benchmarks:**
   - Target: 10K+ RPS on single core
   - P99 latency < 1ms

---

## Success Criteria

- [ ] HTTP server starts and accepts connections
- [ ] /health endpoint returns 200 OK
- [ ] /api/v1/analyze processes requests
- [ ] JSON parsing works for all request types
- [ ] Guards are invoked correctly
- [ ] Prometheus metrics exposed
- [ ] OpenAPI spec generated

---

## Next Steps After REST API

1. **Brain FFI** — Connect Python ML engines
2. **mTLS** — Mutual TLS for production
3. **Rate Limiting** — Per-client limits
4. **WebSocket** — Streaming responses
