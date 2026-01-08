# IMMUNE Race Condition Fixes — Specification

> **Version:** 1.0  
> **Author:** SENTINEL Team  
> **Date:** 2026-01-08  
> **Status:** Draft

---

## 1. Overview

### 1.1 Purpose

Eliminate race conditions in IMMUNE Kmod pattern reload using RCU-style (Read-Copy-Update) double-buffering for lock-free reads.

### 1.2 Problem Statement

From architecture critique (S5):
- Pattern array can be freed while Kmod is matching
- No synchronization for hot reload
- Potential use-after-free in kernel

### 1.3 Scope

| In Scope | Out of Scope |
|----------|--------------|
| Double-buffer pattern storage | Full RCU (kernel RCU) |
| Atomic pointer swap | Lock-free data structures |
| Grace period tracking | Hazard pointers |

---

## 2. Architecture

### 2.1 Double Buffer Design

```
┌──────────────────────────────────────────────────────────────┐
│                    DOUBLE BUFFER PATTERN                      │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  Active Buffer ──────► [Pattern Array A]  ◄──── Readers       │
│       ↓                                                       │
│  (atomic swap on reload)                                      │
│       ↓                                                       │
│  Standby Buffer ──────► [Pattern Array B]  ◄──── Writer       │
│                                                               │
│  On reload:                                                   │
│  1. Writer updates standby buffer                             │
│  2. Atomic swap active ↔ standby                             │
│  3. Wait for grace period (readers drain)                     │
│  4. Free old patterns in (now) standby                        │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### 2.2 Grace Period

```
Grace period = max(all active readers finish)

Simple approach:
- Epoch counter incremented on swap
- Readers record epoch on entry
- Free when no readers from old epoch
```

---

## 3. API Design

```c
/* Double buffer handle */
typedef struct rcu_buffer rcu_buffer_t;

/* Reader section */
void rcu_read_lock(rcu_buffer_t *buf);
void *rcu_dereference(rcu_buffer_t *buf);
void rcu_read_unlock(rcu_buffer_t *buf);

/* Writer operations */
void *rcu_get_standby(rcu_buffer_t *buf);
void rcu_swap(rcu_buffer_t *buf);
void rcu_synchronize(rcu_buffer_t *buf);
```

---

## 4. Implementation Plan

- [ ] rcu_buffer.h header
- [ ] rcu_buffer.c implementation
- [ ] Atomic operations (stdatomic.h)
- [ ] Grace period tracking
- [ ] Integration with Kmod pattern reload
- [ ] Unit tests with TSan

---

*Compact spec for Phase 3.3*
