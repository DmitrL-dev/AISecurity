# IMMUNE Linux eBPF Port — Specification

> **Version:** 1.0  
> **Author:** SENTINEL Team  
> **Date:** 2026-01-08  
> **Status:** Draft

---

## 1. Overview

### 1.1 Purpose

Port IMMUNE agent to Linux using eBPF for syscall interception. Replaces DragonFlyBSD Kmod with libbpf programs.

### 1.2 Scope

| In Scope | Out of Scope |
|----------|--------------|
| libbpf integration | BTF generation |
| Syscall tracing (execve, open, connect) | Container-specific features |
| Perf ring buffer for events | Kernel-side pattern matching |

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LINUX eBPF AGENT                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   Kernel Space:                                              │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  [eBPF Programs]                                    │   │
│   │   tp/syscalls/sys_enter_execve                     │   │
│   │   tp/syscalls/sys_enter_openat                     │   │
│   │   tp/syscalls/sys_enter_connect                     │   │
│   └─────────────────────────────────────────┬───────────┘   │
│                                             │               │
│                                             ▼               │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  [Perf Ring Buffer]                                │   │
│   │   Event data passed to userspace                    │   │
│   └─────────────────────────────────────────┬───────────┘   │
│                                             │               │
│   User Space:                               ▼               │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  [IMMUNE Agent]                                     │   │
│   │   - Pattern matching (Bloom, regex)                │   │
│   │   - Threat detection                                │   │
│   │   - Hive communication (TLS)                       │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. API Design

```c
/* eBPF program loader */
int ebpf_init(void);
int ebpf_load_programs(void);
int ebpf_attach(void);
void ebpf_detach(void);

/* Event polling */
int ebpf_poll_events(ebpf_callback_t cb, int timeout_ms);

/* Event types */
typedef enum {
    EBPF_EVENT_EXEC,
    EBPF_EVENT_OPEN,
    EBPF_EVENT_CONNECT
} ebpf_event_type_t;
```

---

## 4. Implementation Plan

- [ ] ebpf_agent.h header
- [ ] ebpf_agent.c loader implementation
- [ ] eBPF programs (.bpf.c):
  - [ ] execve tracing
  - [ ] openat tracing
  - [ ] connect tracing
- [ ] Perf ring buffer handling
- [ ] Build with libbpf

---

*Based on Tetragon-inspired architecture*
