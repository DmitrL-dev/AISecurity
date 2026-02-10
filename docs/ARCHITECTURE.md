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
│  │         • TLS Termination  • Rate Limiting  • DDoS Protection        │   │
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
│  │  • Middleware  │    │  • 39K Payloads│    │  • Real-time Defense   │    │
│  └────────────────┘    └────────────────┘    └────────────────────────┘    │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
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

### SHIELD — DMZ Gateway

```
Internet                    SHIELD                     Internal
    │                         │                            │
    │    ┌────────────────────┼────────────────────┐      │
    │    │                    │                    │      │
    ├───▶│  TLS Termination   │   Authentication  │◀─────┤
    │    │                    │                    │      │
    │    │    Rate Limiter    │    Firewall       │      │
    │    │                    │                    │      │
    │    └────────────────────┼────────────────────┘      │
    │                         │                            │
    │                         ▼                            │
    │                    To BRAIN                          │
```

**Language:** Pure C (for speed)  
**Latency:** <5ms  
**Throughput:** 100K+ RPS  

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
│              │  39K+ Attacks│                           │
│              └──────────────┘                           │
└─────────────────────────────────────────────────────────┘
```

**Payloads:** 39,000+  
**Categories:** Injection, Jailbreak, Encoding, RAG, Agentic  

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
```

---

## Deployment Options

| Mode | Description | Use Case |
|------|-------------|----------|
| **Library** | `import sentinel` | Simple apps |
| **Sidecar** | Docker container | Microservices |
| **Gateway** | SHIELD + BRAIN | Enterprise |
| **Embedded** | IMMUNE agent | Desktop apps |

---

*For more details, see [Academy Mid-Level: Production Architecture](./academy/mid-level/01-production-architecture.md)*
