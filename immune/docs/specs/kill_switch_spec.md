# IMMUNE Kill Switch — Specification

> **Version:** 1.0  
> **Author:** SENTINEL Team  
> **Date:** 2026-01-08  
> **Status:** Draft

---

## 1. Overview

### 1.1 Purpose

Implement decentralized emergency kill switch for IMMUNE agents using Shamir's Secret Sharing. Requires M-of-N authorized parties to activate, preventing single-point-of-failure and rogue shutdown.

### 1.2 Problem Statement

From architecture critique (S2):
- Single owner can shutdown entire fleet
- No protection against compromised admin
- No dead man's switch (orphan detection)

### 1.3 Scope

| In Scope | Out of Scope |
|----------|--------------|
| Shamir 3-of-5 threshold | Hardware security modules |
| Dead Man's Switch (canary) | Multi-sig blockchain |
| Emergency broadcast | Recovery procedures |
| Share distribution | Biometric auth |

---

## 2. Requirements

### 2.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | Split kill secret into N shares | P0 |
| FR-02 | Require M shares to reconstruct | P0 |
| FR-03 | Broadcast shutdown command with proof | P0 |
| FR-04 | Dead Man's Switch (daily canary) | P1 |
| FR-05 | Share holder management | P2 |

### 2.2 Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-01 | Share reconstruction time | < 100ms |
| NFR-02 | Maximum share holders | 10 |
| NFR-03 | Broadcast latency | < 5 seconds |

---

## 3. Architecture

### 3.1 Shamir Secret Sharing

```
Secret S (kill code) is split into N=5 shares:
  S₁, S₂, S₃, S₄, S₅

Any M=3 shares can reconstruct S:
  f(S₁, S₂, S₃) = S ✓
  f(S₁, S₃, S₅) = S ✓
  f(S₁, S₂)     = ? ✗ (not enough)
```

### 3.2 Kill Sequence

```
┌──────────────────────────────────────────────────────────────┐
│                    KILL SWITCH ACTIVATION                     │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  Admin₁ ─► Share₁ ─┐                                         │
│  Admin₂ ─► Share₂ ─┼──► [Reconstruct] ─► Kill Code           │
│  Admin₃ ─► Share₃ ─┘                          │               │
│                                                │               │
│                                                ▼               │
│                                         [Sign Command]        │
│                                                │               │
│                                                ▼               │
│                                         [Broadcast]           │
│                                                │               │
│                    ┌───────────────────────────┼──────────┐   │
│                    ▼           ▼               ▼          ▼   │
│                 Agent₁     Agent₂          Agent₃     Agent₄  │
│                 [STOP]     [STOP]          [STOP]     [STOP]  │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### 3.3 Dead Man's Switch

```
Daily canary: Hive broadcasts "I'm alive" every 24h
  - Signed by Hive private key
  - Published to /canary endpoint
  - Agents check every 6h

If canary missing for 48h:
  - Agents go into safe mode
  - Stop processing new events
  - Continue logging only
```

---

## 4. API Design

### 4.1 Data Types

```c
/* Share holder */
typedef struct {
    uint8_t     id;             /* 1-255 */
    char        name[64];       /* Human-readable name */
    uint8_t     share[32];      /* The share data */
} kill_share_t;

/* Kill switch configuration */
typedef struct {
    int         threshold;      /* M shares needed */
    int         total_shares;   /* N total shares */
    int         canary_hours;   /* Dead man interval */
} kill_config_t;
```

### 4.2 Functions

| Function | Description |
|----------|-------------|
| `kill_init(config)` | Initialize kill switch |
| `kill_generate_shares(secret, shares, n, m)` | Split secret |
| `kill_combine_shares(shares, m, secret)` | Reconstruct |
| `kill_broadcast(kill_code, signature)` | Send to all agents |
| `kill_canary_publish()` | Publish daily canary |
| `kill_canary_check()` | Agent checks canary |

---

## 5. Implementation Plan

### Phase 1: Shamir SSS (0.5 day)
- [ ] kill_switch.h header
- [ ] Shamir implementation (GF(256))
- [ ] Share generation and reconstruction

### Phase 2: Broadcast (0.5 day)
- [ ] Kill command structure
- [ ] Signature verification
- [ ] Broadcast to all agents

### Phase 3: Dead Man's Switch (0.5 day)
- [ ] Canary publishing
- [ ] Agent canary check
- [ ] Safe mode implementation

---

## 6. Test Plan

| Test | Description |
|------|-------------|
| `test_split_combine` | 3-of-5 works |
| `test_insufficient` | 2-of-5 fails |
| `test_broadcast` | All agents receive |
| `test_canary_expire` | Safe mode activates |

---

## 7. Acceptance Criteria

- [ ] 3 of 5 shares reconstructs secret
- [ ] 2 of 5 shares cannot reconstruct
- [ ] Kill broadcast reaches all agents < 5s
- [ ] Dead man's switch activates after 48h

---

*Document ready for implementation*
