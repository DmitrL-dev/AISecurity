---
title: "IMMUNE: Building an EDR/XDR/MDR Security Platform in Pure C — Solo Dev Progress"
published: false
description: "Open source kernel-level security for DragonFlyBSD. What actually works today."
tags: security, c, opensource, dragonflybsd
cover_image: ./docs/images/immune_hero.png
---

# IMMUNE: Open Source EDR/XDR/MDR — Progress Report

I'm building **SENTINEL IMMUNE** — an open source security platform in Pure C.

This is a solo project. Progress is steady, not fast. But I'm sharing what **actually works today**.

---

## What This Is

IMMUNE is a complete security stack:

- **EDR** (Endpoint Detection) — Kernel module on each host (6 syscall hooks)
- **XDR** (Extended Detection) — Cross-agent correlation in Hive (24 modules)
- **MDR** (Managed Detection) — Automated playbook responses

All open source. All Pure C. No Python dependencies.

---

## What Actually Works Right Now

### Kernel Module (v2.2) — ✅ Tested

Six syscall hooks that intercept at kernel level:

```
root@dragonfly:~# kldload ./immune.ko

IMMUNE: [BLOCKED] exec /tmp/test.sh (pid=3158)
IMMUNE: [BLOCKED] connect 127.0.0.1:4444 (pid=3159)
IMMUNE: [AUDIT] open /etc/master.passwd (pid=3160)
IMMUNE: [AUDIT] setuid 0->65534 (pid=3162)
```

**This is real output.** The module blocks suspicious executions and network connections, audits sensitive file access.

| Hook      | Status     | What It Does                            |
| --------- | ---------- | --------------------------------------- |
| `execve`  | ✅ Working | Blocks /tmp/ and reverse shell patterns |
| `connect` | ✅ Working | Blocks connections to port 4444         |
| `bind`    | ✅ Working | Detects backdoor listeners              |
| `open`    | ✅ Working | Audits /etc/shadow, /etc/master.passwd  |
| `fork`    | ✅ Working | Tracks process creation                 |
| `setuid`  | ✅ Working | Detects privilege escalation            |

### Hive Server (v1.0) — ✅ Compiles & Runs

```bash
root@dragonfly:~/immune/hive# ./build.sh

=== SUCCESS ===
Binary: bin/hived
-rwxr-xr-x  1 root  wheel  110208 Jan  3 15:24 bin/hived
```

24 modules compiled into 110KB binary:

- `sentinel.c` — Bridge to SENTINEL AI platform
- `correlate.c` — Cross-agent event correlation
- `playbook.c` — Automated response playbooks
- `network.c`, `api.c`, `crypto.c`, `jail.c`... 21 more

### Agent Daemon (v1.0) — ✅ Connects

```
SENTINEL IMMUNE Agent v1.0.0
DragonFlyBSD Edition
Hive: localhost:9998

IMMUNE Agent: kmod detected (enabled=1, events=3)
IMMUNE Agent: Connected to Hive at localhost:9998
```

Agent reads kernel events via sysctl and forwards to Hive.

---

## Architecture

```
┌─────────────────────────────────────┐
│            HIVE (110KB)             │
│  Central orchestrator, 24 modules   │
└─────────────────┬───────────────────┘
                  │ TCP
┌─────────────────┴───────────────────┐
│         AGENT (userspace)           │
│     Reads sysctl, sends JSON        │
└─────────────────┬───────────────────┘
                  │ sysctl IPC
┌─────────────────┴───────────────────┐
│         KMOD (kernel)               │
│     6 syscall hooks, ring buffer    │
└─────────────────────────────────────┘
```

All components work together. Not 24 separate tools bolted together — **one organism**.

---

## Why Pure C on DragonFlyBSD

Honest answer: because I wanted to build something that can't be easily bypassed.

- **No runtime to exploit** — Python/Node security tools have their own attack surface
- **Kernel-level hooks** — Can't be bypassed from userspace
- **110KB binary** — vs 50MB+ for typical security tools
- **DragonFlyBSD** — Clean kernel API, HAMMER2 filesystem, native jails

Is this the fastest development path? No.  
Is this the most secure? I believe so.

---

## What's NOT Ready Yet

Being honest about current limitations:

- ❌ TLS encryption for agent-hive communication (TCP only now)
- ❌ SENTINEL AI integration (bridge code exists, not connected)
- ❌ Linux/Windows agents (DragonFlyBSD only)
- ❌ Web dashboard
- ❌ Production hardening

---

## Why Open Source

This is fully open source because:

1. Security tools should be auditable
2. Solo dev = slow progress, community can help
3. I believe in building public infrastructure

The code is at [GitHub repo]. No paid tiers, no "enterprise features". Everything is open.

---

## Solo Dev Reality

I work on this alone. That means:

- Features ship when they're ready, not on a roadmap
- Some days I fix one bug, other days I add whole modules
- Quality over speed — I'd rather ship working code slowly

If you want to contribute, the codebase is clean C with minimal dependencies. PRs welcome.

---

## Source Code

Code will be pushed to GitHub after this article goes live:

**Repository:** [github.com/username/sentinel-community](https://github.com/username/sentinel-community)

The `immune/` directory contains:

- `hive/` — Central server (24 .c files)
- `agent/kmod/` — DragonFlyBSD kernel module
- `agent/src/` — Userspace daemon

Star the repo to get notified when the code lands.

---

## Numbers (Real)

| Metric              | Value  |
| ------------------- | ------ |
| C source files      | 30+    |
| Hive modules        | 24     |
| Hive binary         | 110KB  |
| Kmod hooks          | 6      |
| Python dependencies | 0      |
| Contributors        | 1 (me) |

---

## Follow Along

I post updates as I build. Next priorities:

1. TLS for agent communication
2. HAMMER2 forensic snapshots on detection
3. Connect SENTINEL AI bridge properly

Building security infrastructure the hard way. Slow but right.

---

_Solo dev building SENTINEL AI Security Platform. Pure C enthusiast. DragonFlyBSD user._
