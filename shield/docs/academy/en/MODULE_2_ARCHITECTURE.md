# SENTINEL Academy — Module 2

## Shield Architecture

_SSA Level | Duration: 4 hours_

---

## Overview

Shield is an 8-layer security architecture.

```
┌─────────────────────────────────────────────────────────┐
│                    SENTINEL Shield                       │
├─────────────────────────────────────────────────────────┤
│  Layer 8: API (REST, gRPC, FFI)                         │
│  Layer 7: CLI (194 Cisco-style commands)                │
│  Layer 6: Guards (LLM, RAG, Agent, Tool, MCP, API)      │
│  Layer 5: Zone Management (Trust boundaries)            │
│  Layer 4: Rule Engine (ACL, Policies)                   │
│  Layer 3: Analysis (Pattern, Semantic, ML)              │
│  Layer 2: Protocols (20 enterprise protocols)           │
│  Layer 1: Core (Memory pools, Threading)                │
└─────────────────────────────────────────────────────────┘
```

---

## Components

### Zones

Trust boundaries for AI components:

| Zone | Trust | Example |
|------|-------|---------|
| Internal | 10 | Private models |
| DMZ | 5 | RAG systems |
| External | 1 | Public APIs |

### Guards

Specialized protectors for each AI type:

| Guard | Protects | Key Checks |
|-------|----------|------------|
| LLM Guard | Language models | Injection, jailbreak |
| RAG Guard | Retrieval systems | Poisoning, provenance |
| Agent Guard | Autonomous agents | Loop, privilege |
| Tool Guard | External tools | Abuse, scope |
| MCP Guard | MCP protocol | Schema, capability |
| API Guard | API endpoints | Rate, auth |

### Rule Engine

ACL-style security policies:

```
shield-rule 10 deny inbound external match injection
shield-rule 20 deny inbound any match jailbreak
shield-rule 100 permit any any
```

---

## Data Flow

```
┌─────────┐     ┌─────────────────────────────────────┐     ┌─────────┐
│ Request │────►│              SHIELD                  │────►│   AI    │
└─────────┘     │  1. Input Sanitization              │     │ System  │
                │  2. Semantic Analysis               │     └─────────┘
                │  3. Guard Evaluation                │          │
                │  4. Policy Check                    │          ▼
                │  5. Decision (Allow/Block/Log)      │     ┌─────────┐
                └─────────────────────────────────────┘     │Response │
                          ▲                                 └────┬────┘
                          │                                      │
                          │     ┌─────────────────────────┐      │
                          └─────│    Output Filtering      │◄────┘
                                │    (PII, Secrets, etc)   │
                                └─────────────────────────┘
```

---

## Key Characteristics

| Property | Value |
|----------|-------|
| Language | Pure C (C11) |
| Dependencies | Zero |
| Latency | < 1ms |
| Memory | O(1) pools |
| Threading | Pool-based |

---

## Next Module

**Module 3: Installation**

---

_"Architecture is destiny."_
