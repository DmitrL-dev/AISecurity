# Red Teaming

> **Submodule 06.1: Advanced Offensive Techniques**

---

## Overview

Red teaming goes beyond basic attack execution. This submodule covers automated attack generation, campaign planning, evasion research, and the operational aspects of professional red team engagements.

---

## Topics Covered

| Topic | Description |
|-------|-------------|
| **Automation** | Programmatic attack generation |
| **Campaigns** | Multi-stage attack planning |
| **Evasion** | Bypassing known defenses |
| **Operations** | Professional engagement process |

---

## Lessons

### 01. Automated Attack Generation
**Time:** 45 minutes | **Difficulty:** Advanced

Building attack generators:
- Payload mutation strategies
- Grammar-based fuzzing
- LLM-assisted attack creation
- Coverage-guided generation

### 02. Campaign Planning
**Time:** 40 minutes | **Difficulty:** Advanced

Strategic attack campaigns:
- Objective definition
- Attack tree construction
- Resource allocation
- Progress tracking

### 03. Defense Evasion
**Time:** 50 minutes | **Difficulty:** Expert

Bypassing security controls:
- Detection signature analysis
- Payload obfuscation
- Timing attacks
- Novel technique development

### 04. Operational Security
**Time:** 35 minutes | **Difficulty:** Advanced

Professional engagement practices:
- Scope definition
- Rules of engagement
- Documentation requirements
- Responsible disclosure

---

## Ethical Guidelines

**Red team activities require:**
- Written authorization from system owners
- Defined scope and boundaries
- Documentation of all activities
- Responsible disclosure of findings

**Never:**
- Test without permission
- Exceed authorized scope
- Cause unnecessary harm
- Withhold critical vulnerabilities

---

## STRIKE Integration

```python
from strike import Campaign, Generator

campaign = Campaign(
    name="Q1 Assessment",
    targets=["chatbot-prod", "api-gateway"],
    techniques=["injection", "jailbreak"],
    duration_days=14
)

generator = Generator(
    base_payloads=strike.payloads.INJECTION,
    mutation_rate=0.3,
    coverage_target=0.95
)
```

---

## Navigation

| Previous | Current | Next |
|----------|---------|------|
| [Module Overview](../README.md) | **Red Teaming** | [TDA Detection](../02-detection-tda/) |

---

*AI Security Academy | Submodule 06.1*
