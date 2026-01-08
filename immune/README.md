# SENTINEL IMMUNE

**Open Source EDR/XDR/MDR Security Platform in Pure C**

Kernel-level protection for AI/LLM infrastructure. Production-ready security hardening.

---

## 🆕 January 2026 Update: Production Hardening Complete!

| Phase | Module | LOC | Status |
|-------|--------|-----|--------|
| **1.1** | TLS Transport (wolfSSL mTLS) | 1,568 | ✅ |
| **1.2** | Pattern Safety (ReDoS protection) | 1,356 | ✅ |
| **2.1** | Bloom Filter (MurmurHash3) | 1,203 | ✅ |
| **2.2** | SENTINEL Bridge (Brain API) | 1,153 | ✅ |
| **3.1** | Kill Switch (Shamir SSS) | 1,192 | ✅ |
| **3.2** | Sybil Defense (PoW, Trust) | 652 | ✅ |
| **3.3** | RCU Buffer (lock-free) | 541 | ✅ |
| **4.1** | Linux eBPF Port | 656 | ✅ |
| **4.2** | Web Dashboard (htmx) | 305 | ✅ |

**Total: ~9,000 LOC, 11 specs, 42 unit tests**

---

## Current Status

| Component | Version | Status |
| --------- | ------- | ------ |
| Hive      | v2.0    | ✅ 34 modules, production-ready |
| Kmod      | v2.2    | ✅ 6 syscall hooks |
| Agent     | v2.0    | ✅ TLS + eBPF support |
| Common    | v1.0    | ✅ 4 security libraries |

## 🔐 Security Features

### TLS 1.3 with mTLS
- wolfSSL integration (conditional compilation)
- Certificate pinning (SHA-256)
- Auto certificate generation script

### ReDoS Protection
- Pattern complexity scoring
- Nested quantifier detection
- Kernel timeout mechanism

### Bloom Filter Pre-filter
- MurmurHash3 hash function
- <100ns lookup latency
- Auto-tuning false positive rate

### Decentralized Kill Switch
- Shamir Secret Sharing over GF(256)
- 3-of-5 threshold scheme
- Dead Man's Switch (canary)

### Anti-Sybil Measures
- Proof-of-Work join barrier
- Trust scoring with decay
- Agent blacklisting

### Race-Free Pattern Reload
- RCU-style double buffer
- Lock-free reader path
- Atomic pointer swap

## What It Does

- **EDR** — Kernel module intercepts syscalls (execve, connect, bind, open, fork, setuid)
- **XDR** — Hive correlates events across agents, detects lateral movement
- **MDR** — Automated playbooks respond to threats

## Quick Start (DragonFlyBSD)

```bash
# Generate certificates for mTLS
cd scripts && ./generate_certs.sh

# Build Hive with TLS
cd hive && ./build.sh
./bin/hived

# Build and load kernel module
cd agent/kmod && make
kldload ./immune.ko

# Build and run agent
cd agent
cc -Wall -O2 -o bin/immune_agent src/immune_daemon.c
./bin/immune_agent
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    HIVE v2.0 (Production)                    │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │   TLS   │ │  Kill   │ │  Sybil  │ │  Web    │           │
│  │ mTLS    │ │ Switch  │ │ Defense │ │Dashboard│           │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘           │
│  ┌────────────────────────────────────────────────┐        │
│  │            SENTINEL Bridge                      │        │
│  │  Edge Inference → Brain API → Pattern Cache    │        │
│  └────────────────────────────────────────────────┘        │
└───────────────────────────┬─────────────────────────────────┘
                            │ TLS 1.3 mTLS
┌───────────────────────────┴─────────────────────────────────┐
│                      AGENT                                   │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐                       │
│  │  Bloom  │ │ Pattern │ │   RCU   │                       │
│  │ Filter  │ │ Safety  │ │ Buffer  │                       │
│  └─────────┘ └─────────┘ └─────────┘                       │
└───────────────────────────┬─────────────────────────────────┘
                            │ sysctl / eBPF
┌───────────────────────────┴─────────────────────────────────┐
│              KMOD (BSD) / eBPF (Linux)                       │
│            6 syscall hooks, lock-free                        │
└─────────────────────────────────────────────────────────────┘
```

## Platform Support

| Platform      | Status |
| ------------- | ------ |
| DragonFlyBSD  | ✅ Full support |
| FreeBSD       | ✅ Compatible |
| Linux (eBPF)  | ✅ Agent ready |
| Windows (ETW) | 🔧 Planned |

## Directory Structure

```
immune/
├── common/                 # Security libraries
│   ├── include/           # tls_transport.h, bloom_filter.h, rcu_buffer.h
│   └── src/               # Implementations
├── hive/                   # Central server
│   ├── include/           # sentinel_bridge.h, kill_switch.h, sybil_defense.h
│   ├── src/               # Implementations
│   └── www/               # Web dashboard (htmx)
├── agent/
│   ├── include/           # ebpf_agent.h
│   ├── src/               # ebpf_agent.c
│   └── kmod/              # DragonFlyBSD kernel module
├── docs/
│   └── specs/             # 11 SDD specification documents
├── tests/                  # 42 unit tests
└── scripts/
    └── generate_certs.sh  # mTLS certificate generation
```

## Requirements

| Requirement | Version |
| ----------- | ------- |
| DragonFlyBSD / FreeBSD / Linux | 6.x / 14.x / 5.10+ |
| C compiler | cc/clang/gcc |
| wolfSSL (optional) | 5.x |
| libbpf (Linux) | 1.x |

## Spec-Driven Development

All modules follow SDD workflow:
1. **Spec first** — `docs/specs/{module}_spec.md`
2. **Header second** — API contract
3. **Implementation third** — Following spec
4. **Tests fourth** — From spec test plan

## License

MIT

## Related

- [SENTINEL Shield](../shield) — AI request pre-filter
- [SENTINEL Strike](../strike) — Red team toolkit
- [SENTINEL Brain](../core/brain) — 258 detection engines
