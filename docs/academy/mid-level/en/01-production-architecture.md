# 🏗️ Lesson 1.1: Production Architecture

> **Time: 45 minutes** | Mid-Level Module 1

---

## Deployment Patterns

### Pattern 1: Simple (Library)

```
Your App + SENTINEL SDK → LLM
```

```python
# Embedded in your application
from sentinel import scan
```

**Best for:** Small apps, prototypes

---

### Pattern 2: Standard (Sidecar)

```
┌─────────────────────────────────────────────────────────────┐
│                      Your Application                        │
│  ┌─────────────────┐          ┌─────────────────┐           │
│  │    Your Code    │ ──────── │    SENTINEL     │           │
│  │                 │   HTTP   │    Sidecar      │           │
│  └─────────────────┘          └─────────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

**Best for:** Microservices, Docker deployments

---

### Pattern 3: Enterprise (Gateway)

```
┌─────────────────────────────────────────────────────────────┐
│                        DMZ                                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                    SHIELD                            │    │
│  │              (C Gateway, TLS, Auth)                  │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                             │
┌─────────────────────────────────────────────────────────────┐
│                      Internal Network                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐  │
│  │      BRAIN      │  │    Your Apps    │  │     LLMs    │  │
│  │  (Detection)    │  │                 │  │             │  │
│  └─────────────────┘  └─────────────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Best for:** Enterprise, multiple services

---

## Component Deep Dive

### BRAIN (Detection)

- 59 Rust detection engines (<1ms each)
- Tiered execution (fast → slow)
- Rust via PyO3, gRPC API

### SHIELD (Gateway)

- Pure C, <1ms latency
- TLS termination
- Rate limiting, auth

### FRAMEWORK (SDK)

- Python package
- Decorators, middleware
- CLI tools

---

## Scaling

| Load | Architecture |
|------|--------------|
| <100 RPS | Library mode |
| 100-1000 RPS | Sidecar mode |
| >1000 RPS | Gateway + horizontal scale |

---

## Next Lesson

→ [1.2: Docker Deployment](./02-docker-deployment.md)
