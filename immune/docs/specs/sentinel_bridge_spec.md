# IMMUNE SENTINEL Bridge — Specification

> **Version:** 1.0  
> **Author:** SENTINEL Team  
> **Date:** 2026-01-08  
> **Status:** Draft

---

## 1. Overview

### 1.1 Purpose

Bridge IMMUNE Hive with SENTINEL Brain for advanced AI-powered threat detection. Enables Hive to query Brain's 258 detection engines for complex analysis.

### 1.2 Problem Statement

From architecture critique (M4):
- Local pattern matching is limited
- Brain has advanced ML engines (TDA, Sheaf, etc.)
- Need async integration without blocking Hive

### 1.3 Scope

| In Scope | Out of Scope |
|----------|--------------|
| HTTP client to Brain API | gRPC transport |
| Edge inference (local heuristics) | Full ML in Hive |
| Async query mode | Real-time streaming |
| Pattern cache sync | Bidirectional sync |

---

## 2. Requirements

### 2.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | HTTP client for Brain /analyze endpoint | P0 |
| FR-02 | Edge inference (fast local checks) | P0 |
| FR-03 | Async query mode (non-blocking) | P0 |
| FR-04 | Pattern cache sync from Brain | P1 |
| FR-05 | Connection pooling | P2 |
| FR-06 | Retry with exponential backoff | P2 |

### 2.2 Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-01 | Query latency (edge) | < 1ms |
| NFR-02 | Query latency (Brain) | < 100ms |
| NFR-03 | Memory per connection | < 50KB |
| NFR-04 | Connection reuse | 95%+ |

---

## 3. Architecture

### 3.1 Query Strategy

```
┌─────────────────────────────────────────────────────────────┐
│                    SENTINEL BRIDGE                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Input ───► [Edge Inference] ───► Decision?                │
│                   │                   │                      │
│                   ▼                   ▼                      │
│             Suspicious?          Yes: BLOCK/ALLOW           │
│                   │                                          │
│                   ▼ (async)                                  │
│             [Brain Query] ───► Update decision               │
│                   │                                          │
│                   ▼                                          │
│             Log + Learn                                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Edge Inference

Fast local checks in Hive (no network):
- Bloom filter pattern check
- Entropy analysis
- Length limits
- Known-bad signatures (cached)

### 3.3 Brain Query

HTTP POST to Brain API when edge is uncertain:
```
POST /api/v1/analyze
Content-Type: application/json

{
  "text": "user input here",
  "context": {
    "syscall": "execve",
    "pid": 12345,
    "agent_id": "hive-001"
  }
}
```

---

## 4. API Design

### 4.1 Data Types

```c
/* Detection result */
typedef enum {
    DETECT_CLEAN,       /* No threat */
    DETECT_SUSPICIOUS,  /* Needs Brain query */
    DETECT_BLOCK,       /* Definite threat */
    DETECT_UNKNOWN      /* Query failed */
} detect_result_t;

/* Query callback */
typedef void (*bridge_callback_t)(
    void *user_data,
    detect_result_t result,
    const char *details
);

/* Bridge configuration */
typedef struct {
    char    brain_url[256];     /* Brain API URL */
    int     timeout_ms;         /* Query timeout */
    int     pool_size;          /* Connection pool */
    bool    async_enabled;      /* Allow async queries */
} bridge_config_t;
```

### 4.2 Functions

| Function | Description |
|----------|-------------|
| `bridge_init(config)` | Initialize bridge |
| `bridge_shutdown()` | Cleanup |
| `bridge_edge_detect(input)` | Fast local check |
| `bridge_query_sync(input)` | Blocking Brain query |
| `bridge_query_async(input, cb)` | Non-blocking query |
| `bridge_cache_sync()` | Update pattern cache |

---

## 5. Implementation Plan

### Phase 1: Edge Inference (0.5 day)
- [ ] sentinel_bridge.h header
- [ ] Edge detection (entropy, length, bloom)
- [ ] Local cache lookup

### Phase 2: HTTP Client (0.5 day)
- [ ] HTTP client (libcurl wrapper)
- [ ] JSON serialization
- [ ] Connection pooling

### Phase 3: Async + Sync (0.5 day)
- [ ] Thread pool for async
- [ ] Callback mechanism
- [ ] Retry logic

### Phase 4: Testing (0.5 day)
- [ ] Unit tests
- [ ] Integration tests (mock Brain)
- [ ] Performance benchmarks

---

## 6. Test Plan

### 6.1 Unit Tests

| Test | Description |
|------|-------------|
| `test_edge_clean` | Clean input passes |
| `test_edge_block` | Malicious input blocked |
| `test_sync_query` | Sync Brain query |
| `test_async_query` | Async with callback |
| `test_cache_hit` | Cached result used |

---

## 7. Acceptance Criteria

- [ ] Edge inference < 1ms
- [ ] Brain query < 100ms (network permitting)
- [ ] Async queries don't block Hive
- [ ] All unit tests pass

---

*Document ready for implementation*
