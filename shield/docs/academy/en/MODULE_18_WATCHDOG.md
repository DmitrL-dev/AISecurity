# Module 18: Watchdog — Self-Healing System

## Overview

Watchdog is the health monitoring and auto-recovery system in SENTINEL Shield. It continuously monitors all system components and automatically responds to problems.

---

## Components Monitored

- **Guards (6)** — All security guards
- **Memory** — Heap usage, pool utilization
- **Connections** — Active connections
- **State** — Overall system health

---

## Alert Escalation

4-level escalation system:

| Level | Description |
|-------|-------------|
| INFO | Normal operation |
| WARNING | Approaching threshold |
| ERROR | Component failure |
| CRITICAL | Immediate action required |

---

## Auto-Recovery

When enabled, Watchdog automatically:
1. Detects failed components
2. Attempts recovery/reinitialization
3. Logs and alerts
4. Escalates if recovery fails

---

## API

```c
#include "shield_watchdog.h"

shield_err_t shield_watchdog_init(void);
void shield_watchdog_set_auto_recovery(bool enable);
shield_err_t shield_watchdog_check_all(void);
float shield_watchdog_get_system_health(void);
```

---

## CLI Commands

```
sentinel# show watchdog
sentinel(config)# watchdog enable
sentinel(config)# watchdog auto-recovery enable
sentinel# watchdog check
```

---

## Questions

1. What components does Watchdog monitor?
2. What happens at CRITICAL alert level?
3. What does auto-recovery do?
4. What does System Health 0.75 mean?

---

→ [Module 19: Cognitive Signatures](MODULE_19_COGNITIVE.md)
