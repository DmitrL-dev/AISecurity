# Trust Boundaries

> **Submodule 04.3: Managing Trust in Agent Systems**

---

## Overview

Trust boundary management is fundamental to agent security. Agents interact with multiple components of varying trust levels—user input, external content, tools, other agents, and internal systems. This submodule teaches you to identify, enforce, and monitor trust boundaries.

---

## Trust Levels

| Component | Trust Level | Example |
|-----------|-------------|---------|
| **System Prompt** | Fully Trusted | Internal configuration |
| **Internal APIs** | Highly Trusted | Company databases |
| **User Input** | Untrusted | Chat messages |
| **External Content** | Untrusted | Web pages, documents |
| **Other Agents** | Conditional | Verified peer agents |
| **Third-party Tools** | Low Trust | External MCP servers |

---

## Lessons

### 01. Trust Boundary Identification
**Time:** 35 minutes | **Difficulty:** Intermediate

Finding boundaries in your architecture:
- Component inventory
- Data flow mapping
- Trust level assignment
- Boundary documentation

### 02. Boundary Enforcement
**Time:** 40 minutes | **Difficulty:** Intermediate-Advanced

Implementing boundary controls:
- Input validation at boundaries
- Context isolation
- Privilege escalation prevention
- Cross-boundary sanitization

### 03. Trust Delegation
**Time:** 40 minutes | **Difficulty:** Advanced

When agents need to share trust:
- Capability-based delegation
- Time-limited tokens
- Audit and revocation
- Confused deputy prevention

### 04. Continuous Monitoring
**Time:** 35 minutes | **Difficulty:** Intermediate

Watching boundary crossings:
- Anomaly detection
- Policy violation alerts
- Audit logging
- Incident response

---

## Trust Boundary Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    FULLY TRUSTED ZONE                        │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │ System   │    │ Config   │    │ Internal │              │
│  │ Prompt   │    │ Database │    │ APIs     │              │
│  └──────────┘    └──────────┘    └──────────┘              │
├─────────────────────────────────────────────────────────────┤
│  ╔═══════════════════ TRUST BOUNDARY ═══════════════════╗  │
├─────────────────────────────────────────────────────────────┤
│                    UNTRUSTED ZONE                            │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │ User     │    │ External │    │ Third-   │              │
│  │ Input    │    │ Content  │    │ party    │              │
│  └──────────┘    └──────────┘    └──────────┘              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Enforcement Principles

1. **Never trust, always verify** - Validate everything crossing boundaries
2. **Least privilege** - Grant minimal necessary access
3. **Defense in depth** - Multiple layers of validation
4. **Fail secure** - Deny by default, allow explicitly
5. **Audit all crossings** - Log boundary transitions

---

## Navigation

| Previous | Current | Next |
|----------|---------|------|
| [Protocols](../02-protocols/) | **Trust Boundaries** | [Tool Security](../04-tools/) |

---

*AI Security Academy | Submodule 04.3*
