# SENTINEL Architecture

> **Visual guide to SENTINEL's component architecture**

---

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SENTINEL PLATFORM                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                          SHIELD (C)                                   │   │
│  │                    DMZ Security Gateway                               │   │
│  │    • TLS Termination  • Rate Limiting  • Real-time Detection         │   │
│  │    • 6 Guards (LLM, RAG, Agent, Tool, MCP, API)                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                          BRAIN (Python)                               │   │
│  │                     AI Security Detection                             │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐     │   │
│  │  │ Injection  │  │ Jailbreak  │  │    PII     │  │  Agentic   │     │   │
│  │  │  Engines   │  │  Engines   │  │  Engines   │  │  Engines   │     │   │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘     │   │
│  │                      217 Detection Engines                           │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│         ┌──────────────────────────┼──────────────────────────┐             │
│         ▼                          ▼                          ▼             │
│  ┌────────────────┐    ┌────────────────┐    ┌────────────────────────┐    │
│  │   FRAMEWORK    │    │     STRIKE     │    │        IMMUNE          │    │
│  │    (Python)    │    │    (Python)    │    │          (C)           │    │
│  │                │    │                │    │                        │    │
│  │  • SDK         │    │  • Red Team    │    │  • EDR                 │    │
│  │  • FastAPI     │    │  • HYDRA       │    │  • Agent Protection    │    │
│  │  • Middleware  │    │  • 44K Payloads│    │  • Real-time Defense   │    │
│  └────────────────┘    └────────────────┘    └────────────────────────┘    │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                       DASHBOARD (Next.js)                             │   │
│  │              Unified Management & Monitoring Interface                │   │
│  │    • Real-time Topology  • Shield/Brain/Strike Control  • RBAC      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                       RLM-TOOLKIT (Python)                            │   │
│  │              Secure LangChain Replacement with SENTINEL               │   │
│  │         • InfiniRetri  • H-MEM  • R-Zero  • Built-in Security        │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### SHIELD — DMZ Gateway (Pure C)

```
Internet                    SHIELD                     Internal
    │                         │                            │
    │    ┌────────────────────┼────────────────────┐      │
    │    │                    │                    │      │
    ├───▶│  TLS Termination   │   Authentication  │◀─────┤
    │    │                    │                    │      │
    │    │    Rate Limiter    │   6 Guards        │      │
    │    │                    │                    │      │
    │    │  Pattern Matching  │   Zone Control    │      │
    │    │                    │                    │      │
    │    └────────────────────┼────────────────────┘      │
    │                         │                            │
    │                         ▼                            │
    │                    To BRAIN                          │
```

**Language:** Pure C (for speed)  
**Latency:** <5ms  
**Throughput:** 100K+ RPS  
**Guards:** LLM, RAG, Agent, Tool, MCP, API  
**Ports:** 8081 (API), 9090 (Metrics)

---

### BRAIN — Detection Engine

```
Input Prompt
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│                    BRAIN Pipeline                        │
│                                                          │
│  Tier 1 (<10ms)     Tier 2 (<50ms)     Tier 3 (<200ms) │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐ │
│  │ • Keywords   │   │ • Jailbreak  │   │ • TDA        │ │
│  │ • Regex      │   │ • Encoding   │   │ • ML Models  │ │
│  │ • Blocklist  │   │ • RAG Check  │   │ • Sheaf      │ │
│  └──────────────┘   └──────────────┘   └──────────────┘ │
│         │                  │                  │          │
│         └──────────────────┼──────────────────┘          │
│                            ▼                             │
│                    Threat Decision                       │
└─────────────────────────────────────────────────────────┘
     │
     ▼
ScanResult {is_threat, confidence, details}
```

**Engines:** 217  
**OWASP Coverage:** 100% LLM Top 10 + 100% Agentic AI Top 10  

---

### STRIKE — Red Team Platform

```
┌─────────────────────────────────────────────────────────┐
│                        STRIKE                            │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │                   HYDRA Engine                   │    │
│  │                                                  │    │
│  │  Head 1   Head 2   Head 3   ...   Head 10       │    │
│  │    │        │        │              │           │    │
│  │    └────────┴────────┴──────────────┘           │    │
│  │                   │                              │    │
│  └───────────────────┼──────────────────────────────┘    │
│                      ▼                                   │
│              ┌──────────────┐                           │
│              │  Payload DB  │                           │
│              │  44K+ Attacks│                           │
│              └──────────────┘                           │
└─────────────────────────────────────────────────────────┘
```

**Payloads:** 44,000+  
**Categories:** Injection, Jailbreak, Encoding, RAG, Agentic  

---

## Production Architecture

```
                            ┌─────────────────────────────────────────────────┐
                            │                   INTERNET                       │
                            └─────────────────────────────────────────────────┘
                                                    │
                                                    ▼
                            ┌─────────────────────────────────────────────────┐
                            │              LOAD BALANCER                       │
                            │         (nginx / AWS ALB / Cloudflare)          │
                            │              TLS Termination                     │
                            └─────────────────────────────────────────────────┘
                                                    │
                        ┌───────────────────────────┼───────────────────────────┐
                        │                           │                           │
                        ▼                           ▼                           ▼
                ┌───────────────┐           ┌───────────────┐           ┌───────────────┐
                │   SHIELD 1    │           │   SHIELD 2    │           │   SHIELD 3    │
                │     (C)       │           │     (C)       │           │     (C)       │
                │   6 Guards    │           │   6 Guards    │           │   6 Guards    │
                └───────────────┘           └───────────────┘           └───────────────┘
                        │                           │                           │
                        └───────────────────────────┼───────────────────────────┘
                                                    │
                                            ┌───────┴───────┐
                                            │  gRPC + mTLS  │
                                            └───────┬───────┘
                        ┌───────────────────────────┼───────────────────────────┐
                        │                           │                           │
                        ▼                           ▼                           ▼
                ┌───────────────┐           ┌───────────────┐           ┌───────────────┐
                │    BRAIN 1    │           │    BRAIN 2    │           │    BRAIN 3    │
                │   (Python)    │           │   (Python)    │           │   (Python)    │
                │  217 engines  │           │  217 engines  │           │  217 engines  │
                └───────────────┘           └───────────────┘           └───────────────┘
                                                    │
                                                    ▼
                                        ┌─────────────────────┐
                                        │      DASHBOARD      │
                                        │     (Next.js)       │
                                        │  Fleet Management   │
                                        └─────────────────────┘
```

### Component Scaling

| Component         | Role                              | Scaling            |
| ----------------- | --------------------------------- | ------------------ |
| **Load Balancer** | TLS termination, routing          | 1 (HA pair)        |
| **Shield**        | DMZ gateway, rate limiting, auth  | 2-10 replicas      |
| **Brain**         | ML engines, analysis              | 3-20 replicas      |
| **Redis**         | Cache, sessions, rate limits      | Cluster (3+ nodes) |
| **Dashboard**     | Management UI                     | 1-3 replicas       |

---

## Data Flow

```
┌────────┐    ┌─────────┐    ┌───────┐    ┌─────────┐    ┌──────────┐
│  User  │───▶│ SHIELD  │───▶│ BRAIN │───▶│   LLM   │───▶│ Response │
└────────┘    └─────────┘    └───────┘    └─────────┘    └──────────┘
                  │              │
                  │              │
              ┌───▼───┐     ┌────▼────┐
              │ Logs  │     │ Metrics │
              └───────┘     └─────────┘
                  │              │
                  └──────┬───────┘
                         ▼
                  ┌────────────┐
                  │ DASHBOARD  │
                  └────────────┘
```

---

## Deployment Options

| Mode | Description | Use Case |
|------|-------------|----------|
| **Library** | `import sentinel` | Simple apps |
| **Sidecar** | Shield container | Microservices |
| **Gateway** | Shield + BRAIN cluster | Enterprise |
| **Embedded** | IMMUNE agent | Desktop apps |

---

## Port Reference

| Component | Port | Protocol | Description |
|-----------|------|----------|-------------|
| Shield API | 8081 | HTTP | REST API |
| Shield Metrics | 9090 | HTTP | Prometheus metrics |
| Brain API | 8000 | HTTP | REST API |
| Brain gRPC | 50051 | gRPC | Internal comms |
| Dashboard | 3000 | HTTP | Web UI |
| Strike | 8082 | HTTP | Red Team API |

---

*For deployment guide, see [Production Deployment](./guides/deployment-en.md)*
