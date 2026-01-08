# IMMUNE Sybil Defense — Specification

> **Version:** 1.0  
> **Author:** SENTINEL Team  
> **Date:** 2026-01-08  
> **Status:** Draft

---

## 1. Overview

### 1.1 Purpose

Protect IMMUNE HERD network from Sybil attacks where attacker creates many fake agents to corrupt threat intelligence or disrupt consensus.

### 1.2 Problem Statement

From architecture critique (S3):
- Nothing prevents agent ID spoofing
- No join barrier for new agents
- Trust can be gained too easily

### 1.3 Scope

| In Scope | Out of Scope |
|----------|--------------|
| Proof-of-Work for join | Blockchain consensus |
| Vouching system | PKI infrastructure |
| Trust decay over time | ML-based anomaly |

---

## 2. Requirements

### 2.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | PoW puzzle to join network | P0 |
| FR-02 | Existing agent vouching | P0 |
| FR-03 | Trust score per agent | P0 |
| FR-04 | Trust decay over time | P1 |
| FR-05 | Blacklist for bad agents | P2 |

---

## 3. Architecture

### 3.1 Join Protocol

```
New Agent:
1. Solve PoW puzzle (difficulty ~1 min)
2. Request vouching from N existing agents
3. Get minimum M vouches to join
4. Receive provisional trust score
```

### 3.2 Trust Score

```
Trust = Base + Σ(vouch_weight × vouch_trust)
      - Σ(reports × penalty)
      - age_decay

Range: 0.0 - 1.0
Threshold for consensus: 0.5
```

---

## 4. API Design

```c
/* Agent identity */
typedef struct {
    uint64_t    id;
    uint8_t     pubkey[32];
    double      trust;
    time_t      joined;
} sybil_agent_t;

/* Functions */
int sybil_init(config);
int sybil_solve_pow(puzzle, solution);
int sybil_request_vouch(target_agent);
int sybil_grant_vouch(agent_id);
double sybil_get_trust(agent_id);
void sybil_report_bad(agent_id, reason);
```

---

## 5. Implementation Plan

- [ ] sybil_defense.h header
- [ ] sybil_defense.c implementation
- [ ] PoW (SHA256-based)
- [ ] Vouch system
- [ ] Trust scoring
- [ ] Unit tests

---

*Compact spec for Phase 3.2*
