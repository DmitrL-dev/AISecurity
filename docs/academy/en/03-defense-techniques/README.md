# Defense Techniques

> **Module: Core Defense Methods**

---

## Overview

Defense techniques form the foundation of AI security. This module covers both preventive and detective controls for protecting AI systems from attacks, with practical implementation guidance.

---

## Defense Categories

| Category | Purpose | Examples |
|----------|---------|----------|
| **Preventive** | Stop attacks before harm | Input filtering, guardrails |
| **Detective** | Identify attacks in progress | Monitoring, anomaly detection |
| **Corrective** | Respond to incidents | Incident response, rollback |
| **Deterrent** | Discourage attackers | Audit logging, rate limiting |

---

## Defense Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    DEFENSE IN DEPTH                          │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: INPUT DEFENSE                                      │
│  ├── Pattern matching (regex, keywords)                     │
│  ├── Semantic analysis (embeddings, classification)         │
│  └── Rate limiting and anomaly detection                    │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: SYSTEM DEFENSE                                     │
│  ├── Prompt engineering (hardening, structure)              │
│  ├── Privilege separation (least access)                    │
│  └── Resource limits (tokens, time, memory)                 │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: OUTPUT DEFENSE                                     │
│  ├── Content filtering (harmful, PII)                       │
│  ├── Policy enforcement (compliance)                        │
│  └── Response validation (format, length)                   │
├─────────────────────────────────────────────────────────────┤
│  Layer 4: MONITORING                                         │
│  ├── Real-time detection (streaming)                        │
│  ├── Audit logging (forensics)                              │
│  └── Alerting and response (automation)                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Topics

### Input Defense
- Pattern matching with regex and keywords
- Semantic analysis using embeddings
- Rate limiting and quotas
- Input normalization and sanitization

### Output Defense
- Content filtering for harmful material
- PII and credential redaction
- Policy enforcement and compliance
- Response validation and modification

### System Defense
- Architecture hardening principles
- Privilege separation patterns
- Trust boundary enforcement
- Resource limit implementation

### Monitoring
- Real-time threat detection
- Comprehensive audit logging
- Alert configuration and tuning
- Incident response automation

---

## Key Principles

1. **Defense in depth** - Multiple layers; no single point of failure
2. **Minimal privilege** - Grant only necessary access
3. **Fail secure** - Default to blocking when uncertain
4. **Continuous monitoring** - Detect anomalies in real-time
5. **Rapid response** - Quick containment and remediation

---

## Implementation Path

```
Input Filtering → System Hardening → Output Filtering → Monitoring
      ↓                ↓                   ↓              ↓
  Block bad         Limit damage       Catch leaks     Detect attacks
   input           if bypassed         in output       in progress
```

---

## SENTINEL Integration

```python
from sentinel import configure, scan, Guard

# Configure defense layers
configure(
    input_engines=["injection", "jailbreak"],
    output_engines=["pii", "harmful"],
    monitoring=True
)

# Apply protection
guard = Guard(mode="strict")

@guard.protect
def process_message(msg):
    return llm.generate(msg)
```

---

## Navigation

| Previous | Current | Next |
|----------|---------|------|
| [Attack Vectors](../03-attack-vectors/) | **Defense Techniques** | [Agentic Security](../04-agentic-security/) |

---

*AI Security Academy | Defense Techniques*
