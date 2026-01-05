# SENTINEL Academy — Module 13

## Plugin System

_SSE Level | Duration: 5 hours_

---

## Introduction

Guards are built into Shield.

Plugins are external modules loaded dynamically.

Benefits:
- Update without recompiling Shield
- Third-party extensions
- Modular architecture

---

## 13.1 Plugin Architecture

### Plugin Types

| Type | Description |
|------|-------------|
| **Guard Plugin** | Custom guard implementation |
| **Protocol Plugin** | Custom protocol handler |
| **Filter Plugin** | Pre/post processing |
| **Output Plugin** | Custom output destinations |

### Loading Mechanism

```
┌───────────────────────────────────────────────────────────┐
│                       SHIELD                               │
│  ┌─────────────────────────────────────────────────────┐  │
│  │                PLUGIN MANAGER                        │  │
│  │                                                     │  │
│  │   ┌─────────┐   ┌─────────┐   ┌─────────┐          │  │
│  │   │ .so/.dll│   │ .so/.dll│   │ .so/.dll│          │  │
│  │   │ Plugin 1│   │ Plugin 2│   │ Plugin 3│          │  │
│  │   └─────────┘   └─────────┘   └─────────┘          │  │
│  └─────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────┘
```

---

## 13.2 Plugin Interface

### Entry Point

```c
// include/plugin/plugin_interface.h

#define SHIELD_PLUGIN_API_VERSION 1

typedef struct {
    int api_version;
    const char *name;
    const char *version;
    const char *author;
    const char *description;

    // Lifecycle
    shield_err_t (*load)(shield_plugin_ctx_t *ctx);
    void (*unload)(void);

    // Type-specific vtable
    void *vtable;  // Usually guard_vtable_t*
} shield_plugin_t;

// Export macro
#define SHIELD_PLUGIN_EXPORT(plugin) \
    __attribute__((visibility("default"))) \
    shield_plugin_t* shield_plugin_get_info(void) { \
        return &plugin; \
    }
```

### Plugin Context

```c
typedef struct {
    // Shield APIs available to plugins
    void (*log_info)(const char *fmt, ...);
    void (*log_error)(const char *fmt, ...);
    void* (*alloc)(size_t size);
    void (*free)(void *ptr);

    // Config access
    const char* (*get_config)(const char *key);

    // Metrics
    void (*metric_inc)(const char *name, double value);
} shield_plugin_ctx_t;
```

---

## 13.3 Creating a Plugin

### Project Structure

```
my-plugin/
├── CMakeLists.txt
├── include/
│   └── my_plugin.h
├── src/
│   └── my_plugin.c
└── tests/
    └── test_my_plugin.c
```

### Implementation

```c
// src/my_plugin.c

#include "plugin/plugin_interface.h"
#include "guards/guard_interface.h"

static shield_plugin_ctx_t *g_ctx;

static shield_err_t my_guard_evaluate(void *ctx,
                                       const guard_event_t *event,
                                       guard_result_t *result) {
    my_guard_ctx_t *my = ctx;

    if (strstr(event->input, my->keyword)) {
        result->action = ACTION_BLOCK;
        result->threat_score = 0.8f;
        g_ctx->metric_inc("my_plugin_blocks", 1);
    } else {
        result->action = ACTION_ALLOW;
    }

    return SHIELD_OK;
}

static const guard_vtable_t my_guard_vtable = {
    .name = "my_guard",
    .version = "1.0.0",
    .init = my_guard_init,
    .destroy = my_guard_destroy,
    .evaluate = my_guard_evaluate,
};

static shield_plugin_t my_plugin = {
    .api_version = SHIELD_PLUGIN_API_VERSION,
    .name = "my_plugin",
    .version = "1.0.0",
    .author = "Your Name",
    .description = "Example keyword blocking plugin",
    .load = plugin_load,
    .unload = plugin_unload,
    .vtable = (void*)&my_guard_vtable,
};

SHIELD_PLUGIN_EXPORT(my_plugin);
```

---

## 13.4 Loading Plugins

### Configuration

```json
{
  "plugins": {
    "directory": "/etc/shield/plugins",
    "auto_load": true,
    "plugins": [
      {
        "name": "my_plugin",
        "enabled": true,
        "path": "/etc/shield/plugins/shield_my_plugin.so",
        "config": {
          "keyword": "dangerous"
        }
      }
    ]
  }
}
```

---

## 13.5 CLI Commands

```bash
Shield> show plugins

╔══════════════════════════════════════════════════════════╗
║                    LOADED PLUGINS                         ║
╚══════════════════════════════════════════════════════════╝

┌────────────────┬─────────┬──────────────┬─────────────────┐
│ Name           │ Version │ Author       │ Type            │
├────────────────┼─────────┼──────────────┼─────────────────┤
│ my_plugin      │ 1.0.0   │ Your Name    │ guard           │
│ geo_blocker    │ 2.1.0   │ ACME Inc     │ guard           │
└────────────────┴─────────┴──────────────┴─────────────────┘

Shield> plugin load /path/to/new_plugin.so
Loading plugin...
Loaded: new_plugin v1.0.0

Shield> plugin unload my_plugin
Unloading plugin...
Unloaded: my_plugin
```

---

## 13.6 Security Considerations

### Plugin Isolation

```c
typedef struct {
    bool allow_network;
    bool allow_file_io;
    bool allow_exec;
    size_t max_memory;
} plugin_sandbox_t;
```

### Signature Verification

```c
shield_err_t plugin_verify_signature(const char *path, const char *pubkey) {
    char sig_path[PATH_MAX];
    snprintf(sig_path, sizeof(sig_path), "%s.sig", path);
    return crypto_verify_file(path, sig_path, pubkey);
}
```

---

## Module 13 Summary

- Plugin interface and lifecycle
- Dynamic loading (dlopen)
- Plugin manager
- Security considerations
- CLI integration

---

## Next Module

**Module 14: Performance Engineering**

Optimizing Shield performance.

---

_"Plugins = extensibility without recompilation."_
