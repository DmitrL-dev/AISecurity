# SENTINEL Shield Architecture

## Overview

SENTINEL Shield implements a **layered security architecture** for AI systems, acting as a DMZ between trusted infrastructure and untrusted AI components.

---

## Architectural Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                        APPLICATION LAYER                         │
│                   CLI │ REST API │ FFI Bindings                  │
├─────────────────────────────────────────────────────────────────┤
│                        ANALYSIS LAYER                            │
│  Semantic │ Encoding │ Signatures │ Anomaly │ Classifier        │
│  N-gram │ Vectorizer │ Embedding │ Fingerprint                  │
├─────────────────────────────────────────────────────────────────┤
│                        CONTROL LAYER                             │
│  Zone │ Rule │ Guard │ Pattern │ Rate Limiter │ Blocklist       │
│  Session │ Canary │ Quarantine │ Alert │ Safety Prompt          │
├─────────────────────────────────────────────────────────────────┤
│                        CONTEXT LAYER                             │
│  Context Window │ Token Budget │ History │ Request Log          │
│  Output Filter │ Response Validator │ Input Sanitizer           │
├─────────────────────────────────────────────────────────────────┤
│                        RELIABILITY LAYER                         │
│  Timer │ Circuit Breaker │ Retry │ Batch │ Thread Pool          │
├─────────────────────────────────────────────────────────────────┤
│                        OBSERVABILITY LAYER                       │
│  Metrics │ Stats │ Report │ Audit │ Health │ Event Bus          │
├─────────────────────────────────────────────────────────────────┤
│                        PROTOCOL LAYER                            │
│  STP │ SBP │ ZDP │ SHSP │ SAF │ SSRP                            │
├─────────────────────────────────────────────────────────────────┤
│                        PLATFORM LAYER                            │
│  Cross-platform abstractions │ Memory Management │ I/O          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Concepts

### Zones

Zones define **trust boundaries**. Each zone has a trust level (1-10):

| Zone     | Trust Level | Description          |
| -------- | ----------- | -------------------- |
| external | 1           | Untrusted user input |
| dmz      | 5           | Partially trusted    |
| internal | 10          | Fully trusted        |

### Rules

Rules define **security policies**:

```
IF pattern MATCHES input
   AND zone = "external"
   AND direction = "inbound"
THEN action = BLOCK
```

### Guards

Guards are **specialized protectors** for different AI components:

| Guard       | Protects               | Focus                |
| ----------- | ---------------------- | -------------------- |
| LLM Guard   | Language Models        | Injection, jailbreak |
| RAG Guard   | Retrieval Systems      | Data poisoning       |
| Agent Guard | Autonomous Agents      | Tool abuse           |
| Tool Guard  | External Tools         | Injection, RCE       |
| MCP Guard   | Model Context Protocol | Protocol attacks     |
| API Guard   | External APIs          | Rate limiting, auth  |

---

## Request Flow

```
User Input
    │
    ▼
┌─────────────────┐
│ Input Sanitizer │ ──── Normalize, clean
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Zone Resolution │ ──── Determine trust level
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Encoding Detect │ ──── Decode obfuscation
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Semantic Analyze│ ──── Detect intent
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Pattern Match   │ ──── Check signatures
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Rule Evaluation │ ──── Apply policies
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Guard Invocation│ ──── Type-specific check
└────────┬────────┘
         │
         ▼
    ┌────┴────┐
    │ ALLOW?  │
    └────┬────┘
    Yes  │  No
    │    │
    ▼    ▼
   LLM  Block/Quarantine
```

---

## Response Flow

```
LLM Response
    │
    ▼
┌─────────────────┐
│ Output Filter   │ ──── Redact PII/secrets
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Response Valid. │ ──── Check for leaks
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Safety Inject   │ ──── Add safety suffix
└────────┬────────┘
         │
         ▼
    User
```

---

## Protocol Stack

### Layer AI Protocols

```
┌─────────────────────────────────────────┐
│           Application Layer             │
│              Shield API                 │
├─────────────────────────────────────────┤
│           Session Layer                 │
│         SBP (Brain Protocol)            │
├─────────────────────────────────────────┤
│          Discovery Layer                │
│         ZDP (Zone Discovery)            │
├─────────────────────────────────────────┤
│          Analytics Layer                │
│        SAF (Analytics Flow)             │
├─────────────────────────────────────────┤
│         Replication Layer               │
│        SSRP (State Replication)         │
├─────────────────────────────────────────┤
│          Transport Layer                │
│        STP (Sentinel Transfer)          │
└─────────────────────────────────────────┘
```

---

## High Availability

### Cluster Architecture

```
        ┌──────────────┐
        │   Primary    │
        │    Shield    │
        └──────┬───────┘
               │ SHSP Heartbeat
        ┌──────┴───────┐
        │              │
   ┌────▼────┐   ┌────▼────┐
   │ Standby │   │ Standby │
   │    1    │   │    2    │
   └─────────┘   └─────────┘
```

### State Replication (SSRP)

- **Full sync** — On node join
- **Delta sync** — Incremental updates
- **Conflict resolution** — Last-write-wins

---

## Memory Architecture

### Memory Pools

```c
// Pre-allocated pools for common objects
mempool_t rule_pool;      // Rule objects
mempool_t event_pool;     // Event buffers
mempool_t request_pool;   // Request contexts
```

### Ring Buffers

Used for high-throughput event logging:

```c
ringbuf_t event_log;      // Lock-free circular buffer
```

---

## Threading Model

```
┌─────────────────────────────────────┐
│           Main Thread               │
│  Config │ CLI │ Signal Handling     │
├─────────────────────────────────────┤
│           Worker Pool               │
│  Thread 1 │ Thread 2 │ Thread N     │
│     ▲          ▲          ▲         │
│     └──────────┴──────────┘         │
│              Work Queue             │
├─────────────────────────────────────┤
│           Event Thread              │
│  Async notifications, webhooks      │
├─────────────────────────────────────┤
│           Metrics Thread            │
│  Prometheus scrape endpoint         │
└─────────────────────────────────────┘
```

---

## Security Considerations

### Defense in Depth

1. **Input Sanitization** — First line of defense
2. **Semantic Analysis** — Intent detection
3. **Pattern Matching** — Known attack signatures
4. **Guard Validation** — Type-specific checks
5. **Output Filtering** — Data loss prevention

### Attack Surface Minimization

- Zero external dependencies in core
- Memory-safe patterns (bounds checking)
- No dynamic code execution
- Minimal privilege requirements

---

## Extension Points

### Plugin System

```c
// Custom plugin
typedef struct {
    char name[64];
    int (*init)(void *ctx);
    int (*evaluate)(void *ctx, const char *input, void *result);
    void (*destroy)(void *ctx);
} shield_plugin_t;
```

### Guard Extensions

Custom guards can be registered for new AI component types.

---

## Brain FFI Integration

Shield communicates with external AI analysis engines via Brain FFI:

```
┌─────────────────┐     ┌─────────────────┐
│     Shield      │────▶│      Brain      │
│   (C Library)   │     │  (Python/AI)    │
└────────┬────────┘     └─────────────────┘
         │
    ┌────┴────┐
    │ FFI Mode│
    └────┬────┘
         │
    ┌────┼────┬─────────┐
    ▼    ▼    ▼         ▼
  Stub  HTTP  gRPC   Python
```

### FFI Modes

| Mode   | Use Case           | Performance |
|--------|--------------------| ------------|
| Stub   | Testing, mock data | Fastest     |
| HTTP   | REST API backend   | Good        |
| gRPC   | High-throughput    | Best        |
| Python | Embedded inference | Flexible    |

---

## TLS/Security Layer

Shield supports OpenSSL for secure communications:

```
┌─────────────────────────────────────────┐
│              TLS Layer                   │
│  OpenSSL │ Certificate validation        │
│  TLS 1.2+ │ Mutual TLS support           │
├─────────────────────────────────────────┤
│          Post-Quantum Ready              │
│  Kyber (KEM) │ Dilithium (Signatures)    │
└─────────────────────────────────────────┘
```

---

## Kubernetes Integration

Cloud-native deployment architecture:

```yaml
k8s/
├── deployment.yaml      # 3 replicas, resource limits
├── service.yaml         # ClusterIP + LoadBalancer
├── configmap.yaml       # Shield configuration
├── rbac.yaml            # ServiceAccount, Role, RoleBinding
├── hpa.yaml             # Horizontal Pod Autoscaler
└── README.md            # Deployment guide
```

---

## CI/CD Pipeline

GitHub Actions workflow with quality gates:

```
┌──────────┐   ┌──────────┐   ┌──────────┐
│  Build   │──▶│  Test    │──▶│ Quality  │
│  Linux   │   │  94+9    │   │  Checks  │
└──────────┘   └──────────┘   └──────────┘
     │              │              │
     ▼              ▼              ▼
┌──────────┐   ┌──────────┐   ┌──────────┐
│  Build   │   │ Valgrind │   │  Docker  │
│ Windows  │   │   ASAN   │   │  Build   │
└──────────┘   └──────────┘   └──────────┘
```

### Quality Gates

- **103 tests** must pass (94 CLI + 9 LLM)
- **0 warnings** build requirement
- **0 memory leaks** Valgrind check
- **Docker image** builds successfully

---

## Testing Architecture

```
tests/
├── test_cli.c              # 94 CLI E2E tests
├── test_llm_integration.c  # 9 LLM integration tests
├── test_guards.c           # Guard unit tests
├── test_policy_engine.c    # Policy engine tests
└── test_protocols.c        # Protocol tests
```

### Test Categories

| Category    | Tests | Focus                    |
|-------------|-------|--------------------------|
| CLI E2E     | 94    | Full system behavior     |
| LLM         | 9     | Brain FFI, threat detect |
| Guards      | 12    | Guard functionality      |
| Policy      | 8     | Policy engine logic      |
| Protocols   | 6     | Protocol correctness     |

---

## See Also

- [API Reference](API.md)
- [Configuration](CONFIGURATION.md)
- [Deployment](DEPLOYMENT.md)
- [Kubernetes Manifests](../k8s/README.md)
- [CI/CD Pipeline](../.github/workflows/shield-ci.yml)
