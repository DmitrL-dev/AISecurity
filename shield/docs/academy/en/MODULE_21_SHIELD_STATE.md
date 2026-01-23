# Module 21: Shield State — Global State Manager

## Overview

`shield_state_t` is the global state manager for SENTINEL Shield. It provides a single source of truth for all configuration and runtime state, as well as persistence across restarts.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      shield_state_t                          │
│                       (singleton)                            │
├─────────────────┬─────────────────┬─────────────────────────┤
│   Module States │    Config       │    Statistics           │
├─────────────────┼─────────────────┼─────────────────────────┤
│ threat_hunter   │  system_config  │  requests_total         │
│ watchdog        │  debug_state    │  blocked_total          │
│ cognitive       │  ha_config      │  allowed_total          │
│ pqc             │  api_state      │  uptime_seconds         │
│ guards (6)      │                 │                         │
│ rate_limit      │                 │                         │
│ blocklist       │                 │                         │
│ siem            │                 │                         │
│ brain           │                 │                         │
└─────────────────┴─────────────────┴─────────────────────────┘
```

---

## Key Structures

### shield_state_t

```c
typedef struct shield_state {
    // Module states
    threat_hunter_state_t  threat_hunter;
    watchdog_state_t       watchdog;
    cognitive_state_t      cognitive;
    pqc_state_t           pqc;
    guards_state_t         guards;
    
    // Network/Enterprise
    rate_limit_state_t     rate_limit;
    blocklist_state_t      blocklist;
    siem_state_t          siem;
    brain_state_t         brain;
    
    // Configuration
    system_config_t        system;
    debug_state_t         debug;
    ha_config_t           ha;
    api_state_t           api;
    
    // Metadata
    time_t                last_modified;
    bool                  dirty;
    char                  config_path[256];
} shield_state_t;
```

### module_state_t (universal)

```c
typedef enum module_state {
    MODULE_DISABLED = 0,
    MODULE_ENABLED  = 1,
    MODULE_ERROR    = 2,
    MODULE_INIT     = 3
} module_state_t;
```

---

## Shield State API

### Access (Singleton)

```c
#include "shield_state.h"

// Get global state
shield_state_t* shield_state_get(void);
```

### Lifecycle

```c
// Initialize with defaults
shield_err_t shield_state_init(void);

// Reset to defaults
void shield_state_reset(void);
```

### Persistence

```c
// Save to file (INI format)
shield_err_t shield_state_save(const char *filepath);

// Load from file
shield_err_t shield_state_load(const char *filepath);

// Mark as changed
void shield_state_mark_dirty(void);

// Check for unsaved changes
bool shield_state_is_dirty(void);
```

### Statistics

```c
// Increment counters
void shield_state_inc_requests(void);
void shield_state_inc_blocked(void);
void shield_state_inc_allowed(void);

// Formatted output
void shield_state_format_summary(char *buf, size_t buflen);
```

---

## Configuration Format (INI)

```ini
# shield.conf

[system]
log_level=info
max_connections=1000
timezone=UTC

[threat_hunter]
enabled=true
sensitivity=0.70
hunt_ioc=true
hunt_behavioral=true
hunt_anomaly=true

[watchdog]
enabled=true
auto_recovery=true
check_interval_ms=5000

[cognitive]
enabled=true

[pqc]
enabled=true

[guards]
llm=enabled
rag=enabled
agent=enabled
tool=enabled
mcp=enabled
api=enabled

[rate_limit]
enabled=true
max_requests=1000
window_seconds=60

[blocklist]
enabled=true
auto_block_threshold=5

[siem]
enabled=false
endpoint=

[brain]
enabled=true
url=http://localhost:8000
timeout_ms=5000

[ha]
enabled=false
mode=standalone
peer_url=

[api]
enabled=true
port=8080
auth_required=true
```

---

## CLI Integration

All CLI commands use `shield_state_t`:

```c
// Example: cmd_threat_hunter_enable
int cmd_threat_hunter_enable(cli_context_t *ctx, int argc, char **argv) {
    shield_state_t *state = shield_state_get();
    
    state->threat_hunter.state = MODULE_ENABLED;
    shield_state_mark_dirty();  // Mark for saving
    
    cli_out(ctx, "ThreatHunter enabled\n");
    return 0;
}
```

```
sentinel# configure terminal
sentinel(config)# threat-hunter enable
ThreatHunter enabled

sentinel(config)# end
sentinel# write memory
Building configuration...
Configuration saved to shield.conf
[OK]
```

---

## Dual Sync Pattern (Guards)

Guards have dual synchronization:

```c
// cmd_guard_enable
int cmd_guard_enable(cli_context_t *ctx, int argc, char **argv) {
    shield_state_t *state = shield_state_get();
    
    // 1. Update ctx (for immediate effect)
    ctx->guards.llm = true;
    
    // 2. Update shield_state (for persistence)
    state->guards.llm.state = MODULE_ENABLED;
    
    shield_state_mark_dirty();
    return 0;
}
```

---

## Lab Exercise LAB-210

### Objective
Understand Global State Manager operation.

### Task 1: State Modification
```bash
sentinel# configure terminal
sentinel(config)# threat-hunter enable
sentinel(config)# watchdog enable
sentinel(config)# pqc enable
sentinel(config)# end
```

### Task 2: View State
```bash
sentinel# show running-config
```

### Task 3: Save Configuration
```bash
sentinel# write memory
# or
sentinel# copy running-config startup-config
```

### Task 4: Reload and Verify
```bash
sentinel# reload
# After reload:
sentinel# show threat-hunter
# ThreatHunter should be enabled
```

---

## Self-Check Questions

1. What is the singleton pattern in shield_state_t?
2. Why is the `dirty` flag needed?
3. When is shield_state_save() called?
4. What is the Dual Sync Pattern?
5. In what format is configuration stored?

---

## Next Module

→ [Module 22: Advanced CLI — 199 Commands](MODULE_22_CLI_ADVANCED.md)
