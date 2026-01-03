# SENTINEL IMMUNE

**Open Source EDR/XDR/MDR Security Platform in Pure C**

Kernel-level protection for AI/LLM infrastructure. DragonFlyBSD first.

## Current Status

| Component | Version | Status                      |
| --------- | ------- | --------------------------- |
| Hive      | v1.0    | ✅ 24 modules, 110KB binary |
| Kmod      | v2.2    | ✅ 6 syscall hooks tested   |
| Agent     | v1.0    | ✅ Connects to Hive         |

## What It Does

- **EDR** — Kernel module intercepts syscalls (execve, connect, bind, open, fork, setuid)
- **XDR** — Hive correlates events across agents, detects lateral movement
- **MDR** — Automated playbooks respond to threats

## Quick Start (DragonFlyBSD)

```bash
# Build Hive
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
┌─────────────────────────────────────┐
│            HIVE (110KB)             │
│       24 modules, Pure C            │
│  sentinel | correlate | playbook   │
└─────────────────┬───────────────────┘
                  │ TCP
┌─────────────────┴───────────────────┐
│         AGENT (userspace)           │
└─────────────────┬───────────────────┘
                  │ sysctl
┌─────────────────┴───────────────────┐
│    KMOD (kernel, 6 syscall hooks)   │
└─────────────────────────────────────┘
```

## Tested Output

```
IMMUNE: [BLOCKED] exec /tmp/test.sh (pid=3158)
IMMUNE: [BLOCKED] connect 127.0.0.1:4444 (pid=3159)
IMMUNE: [AUDIT] open /etc/master.passwd (pid=3160)
IMMUNE: [AUDIT] setuid 0->65534 (pid=3162)
```

## Directory Structure

```
immune/
├── hive/           # Central server (24 C files)
│   ├── src/        # sentinel.c, correlate.c, playbook.c...
│   └── build.sh    # Build script
├── agent/
│   ├── kmod/       # DragonFlyBSD kernel module
│   └── src/        # Userspace daemon
├── docs/           # Documentation
└── articles/       # Dev.to articles
```

## Platform Support

| Platform      | Status     |
| ------------- | ---------- |
| DragonFlyBSD  | ✅ Working |
| FreeBSD       | 🔧 Planned |
| Linux (eBPF)  | 🔧 Planned |
| Windows (ETW) | 🔧 Planned |

## Not Ready Yet

- TLS encryption (TCP only)
- SENTINEL AI integration (bridge code exists)
- Web dashboard
- Production hardening

## Requirements

- DragonFlyBSD 6.x
- C compiler (cc/clang)
- OpenSSL
- Kernel sources (for kmod)

## Roadmap

### Q1 2026

- [ ] TLS encryption for agent-hive
- [ ] HAMMER2 forensic snapshots
- [ ] SENTINEL AI bridge integration

### Q2 2026

- [ ] Linux eBPF agent
- [ ] Web dashboard (htmx)
- [ ] Threat intelligence sharing (Herd)

### Q3 2026

- [ ] Windows ETW agent
- [ ] Production hardening
- [ ] Public beta

## License

MIT

## Related

- [SENTINEL Shield](../shield) — AI request pre-filter
- [SENTINEL Strike](../strike) — Red team toolkit
