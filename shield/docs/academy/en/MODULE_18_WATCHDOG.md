# Module 18: Watchdog — Self-Healing System

## Overview

Watchdog is a health monitoring and automatic recovery system in SENTINEL Shield. It continuously monitors the state of all system components and automatically responds to problems.

---

## Watchdog Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Watchdog                            │
├───────────────┬──────────────────┬──────────────────────┤
│   Monitoring  │   Health Check   │   Auto-Recovery      │
├───────────────┼──────────────────┼──────────────────────┤
│ • Guards (6)  │  • CPU Usage     │  • Restart           │
│ • Memory      │  • Memory        │  • Reinitialize      │
│ • Connections │  • Latency       │  • Failover          │
│ • State       │  • Error Rate    │  • Alert             │
└───────────────┴──────────────────┴──────────────────────┘
```

---

## Monitoring Components

### 1. Guard Monitoring

Watchdog monitors all 6 Guards:

| Guard | Metrics | Threshold |
|-------|---------|-----------|
| LLM Guard | checks/s, errors | >5% error rate |
| RAG Guard | latency, blocks | >100ms latency |
| Agent Guard | sessions, alerts | >10 alerts/min |
| Tool Guard | calls, denials | >20% denial rate |
| MCP Guard | connections | >80% capacity |
| API Guard | requests, 4xx/5xx | >10% error rate |

### 2. Memory Subsystem

- Heap usage tracking
- Memory pool utilization
- Leak detection
- Fragmentation monitoring

### 3. System Health

- Overall health score (0.0 - 1.0)
- Component-level health
- Trend analysis
- Predictive alerts

---

## Alert Escalation

Watchdog uses a 4-level escalation system:

```
┌────────────────────────────────────────────────────────┐
│  CRITICAL  │ Immediate action required, system at risk │
├────────────┼───────────────────────────────────────────┤
│   ERROR    │ Component failure, degraded service       │
├────────────┼───────────────────────────────────────────┤
│  WARNING   │ Approaching threshold, attention needed   │
├────────────┼───────────────────────────────────────────┤
│   INFO     │ Normal operation, status update           │
└────────────┴───────────────────────────────────────────┘
```

**Automatic actions:**
- **INFO** → Log only
- **WARNING** → Log + Metric increment
- **ERROR** → Log + Alert + Auto-recovery attempt
- **CRITICAL** → Log + Alert + Escalate + Possible failover

---

## Watchdog API

### Initialization

```c
#include "shield_watchdog.h"

// Initialize
shield_err_t shield_watchdog_init(void);

// Release resources
void shield_watchdog_destroy(void);
```

### Configuration

```c
// Enable/disable auto-recovery
void shield_watchdog_set_auto_recovery(bool enable);

// Set check interval (ms)
void shield_watchdog_set_interval(uint32_t ms);
```

### Health Check

```c
// Check all components
shield_err_t shield_watchdog_check_all(void);

// Get overall health score
float shield_watchdog_get_system_health(void);

// Get component status
component_health_t shield_watchdog_get_component(const char *name);
```

### Check Result

```c
typedef struct component_health {
    char            name[64];
    health_status_t status;      // HEALTHY, DEGRADED, UNHEALTHY
    float           score;       // 0.0 - 1.0
    uint64_t        last_check;
    char            message[128];
} component_health_t;
```

---

## CLI Commands

```
sentinel# show watchdog
Watchdog Status
===============
State:         ENABLED
Auto-Recovery: yes
Check Interval: 5000 ms
System Health: 95%

Statistics:
  Checks Total:    12456
  Alerts Raised:   23
  Recoveries:      5

sentinel(config)# watchdog enable
Watchdog enabled

sentinel(config)# watchdog auto-recovery enable
Watchdog auto-recovery enabled

sentinel# watchdog check
Running health check...
Health Check Complete
=====================
System Health: 95%
Status: HEALTHY
```

---

## Integration with shield_state_t

```c
typedef struct watchdog_state {
    module_state_t state;              // ENABLED/DISABLED
    bool           auto_recovery;
    uint32_t       check_interval_ms;
    float          system_health;      // 0.0 - 1.0
    time_t         last_check;
    uint64_t       checks_total;
    uint64_t       alerts_raised;
    uint64_t       recoveries_attempted;
} watchdog_state_t;
```

Configuration in `shield.conf`:
```ini
[watchdog]
enabled=true
auto_recovery=true
check_interval_ms=5000
```

---

## Auto-Recovery Strategies

### 1. Guard Recovery
```c
// On Guard error:
1. Log error
2. Increment error counter
3. If error_rate > threshold:
   a. Disable guard temporarily
   b. Reinitialize guard
   c. Re-enable guard
   d. Monitor for 60 seconds
```

### 2. Memory Recovery
```c
// On high memory usage:
1. Log warning
2. Run garbage collection on pools
3. Evict old sessions
4. Clear caches
5. If still high: alert CRITICAL
```

### 3. Connection Recovery
```c
// On connection loss to Brain:
1. Try reconnect (3 attempts)
2. If failed: switch to local-only mode
3. Alert operator
4. Continue monitoring
```

---

## Lab Exercise LAB-180

### Objective
Configure Watchdog for monitoring and automatic recovery.

### Task 1: Enable Watchdog
```bash
sentinel> enable
sentinel# configure terminal
sentinel(config)# watchdog enable
sentinel(config)# watchdog auto-recovery enable
sentinel(config)# end
sentinel# show watchdog
```

### Task 2: Health Check
```bash
sentinel# watchdog check
```

**Expected result:** System Health >= 80%

### Task 3: Problem Simulation
```bash
# Disable guard
sentinel(config)# no guard enable llm

# Check health
sentinel# watchdog check
# Health should drop

# Re-enable guard
sentinel(config)# guard enable llm
sentinel# watchdog check
# Health should recover
```

---

## Self-Check Questions

1. What components does Watchdog monitor?
2. What happens on a CRITICAL alert?
3. How does Watchdog recover a failed Guard?
4. What does System Health 0.75 mean?
5. Why is check_interval_ms needed?

---

## Next Module

→ [Module 19: Cognitive Signatures](MODULE_19_COGNITIVE.md)
