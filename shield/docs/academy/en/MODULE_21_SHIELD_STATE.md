# Module 21: Shield State — Global State Manager

## Overview

`shield_state_t` is the global state manager for SENTINEL Shield. It provides a single source of truth for all configuration and runtime state, as well as persistence between restarts.

---

## Architecture

```
shield_state_t (singleton)
├── threat_hunter_state_t
├── watchdog_state_t  
├── cognitive_state_t
├── pqc_state_t
├── guards_state_t (6 guards)
├── rate_limit_state_t
├── blocklist_state_t
├── siem_state_t
├── brain_state_t
├── system_config_t
├── debug_state_t
├── ha_config_t
└── api_state_t
```

---

## API

```c
#include "shield_state.h"

// Get global state (singleton)
shield_state_t* shield_state_get(void);

// Initialize with defaults
shield_err_t shield_state_init(void);

// Persistence
shield_err_t shield_state_save(const char *filepath);
shield_err_t shield_state_load(const char *filepath);

// Mark as modified
void shield_state_mark_dirty(void);
```

---

## Configuration Format (INI)

```ini
[threat_hunter]
enabled=true
sensitivity=0.70

[watchdog]
enabled=true
auto_recovery=true

[guards]
llm=enabled
rag=enabled
```

---

## CLI Commands

```
sentinel# show running-config
sentinel# write memory
sentinel# copy running-config startup-config
```

---

## Questions

1. What is the singleton pattern in shield_state_t?
2. Why is the `dirty` flag needed?
3. When is shield_state_save() called?
4. What format stores the configuration?

---

→ [Module 22: Advanced CLI](MODULE_22_CLI_ADVANCED.md)
