# SENTINEL Academy — Module 13

## Plugin System

_SSE Level | Время: 5 часов_

---

## Введение

Guards встроены в Shield.

Plugins — это внешние модули, загружаемые динамически.

Преимущества:

- Обновление без перекомпиляции Shield
- Сторонние расширения
- Modular architecture

---

## 13.1 Plugin Architecture

### Plugin Types

| Type                | Description                 |
| ------------------- | --------------------------- |
| **Guard Plugin**    | Custom guard implementation |
| **Protocol Plugin** | Custom protocol handler     |
| **Filter Plugin**   | Pre/post processing         |
| **Output Plugin**   | Custom output destinations  |

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
    void (*metric_set)(const char *name, double value);
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

### CMakeLists.txt

```cmake
cmake_minimum_required(VERSION 3.14)
project(my_plugin VERSION 1.0.0)

# Find Shield SDK
find_package(SentinelShield REQUIRED)

# Create shared library
add_library(my_plugin SHARED
    src/my_plugin.c
)

target_include_directories(my_plugin PRIVATE
    include
    ${SENTINEL_SHIELD_INCLUDE_DIRS}
)

# Set output name
set_target_properties(my_plugin PROPERTIES
    OUTPUT_NAME "shield_my_plugin"
    PREFIX ""
)

# Install
install(TARGETS my_plugin DESTINATION lib/shield/plugins)
```

### Implementation

```c
// src/my_plugin.c

#include "plugin/plugin_interface.h"
#include "guards/guard_interface.h"

// Plugin context (set during load)
static shield_plugin_ctx_t *g_ctx;

// Guard context
typedef struct {
    char keyword[64];
} my_guard_ctx_t;

// === Guard Implementation ===

static shield_err_t my_guard_init(const char *config, void **ctx) {
    my_guard_ctx_t *my = g_ctx->alloc(sizeof(my_guard_ctx_t));
    if (!my) return SHIELD_ERR_MEMORY;

    // Parse config
    const char *keyword = g_ctx->get_config("keyword");
    strncpy(my->keyword, keyword ? keyword : "blocked", sizeof(my->keyword));

    g_ctx->log_info("MyPlugin: initialized with keyword=%s", my->keyword);

    *ctx = my;
    return SHIELD_OK;
}

static void my_guard_destroy(void *ctx) {
    my_guard_ctx_t *my = ctx;
    g_ctx->free(my);
}

static shield_err_t my_guard_evaluate(void *ctx,
                                       const guard_event_t *event,
                                       guard_result_t *result) {
    my_guard_ctx_t *my = ctx;

    if (strstr(event->input, my->keyword)) {
        result->action = ACTION_BLOCK;
        result->threat_score = 0.8f;
        snprintf(result->reason, sizeof(result->reason),
                 "Keyword '%s' detected", my->keyword);
        g_ctx->metric_inc("my_plugin_blocks", 1);
    } else {
        result->action = ACTION_ALLOW;
        result->threat_score = 0.0f;
    }

    return SHIELD_OK;
}

static const guard_vtable_t my_guard_vtable = {
    .name = "my_guard",
    .version = "1.0.0",
    .type = GUARD_TYPE_CUSTOM,
    .init = my_guard_init,
    .destroy = my_guard_destroy,
    .evaluate = my_guard_evaluate,
};

// === Plugin Entry ===

static shield_err_t plugin_load(shield_plugin_ctx_t *ctx) {
    g_ctx = ctx;
    ctx->log_info("MyPlugin: loading...");
    return SHIELD_OK;
}

static void plugin_unload(void) {
    g_ctx->log_info("MyPlugin: unloading...");
}

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

## 13.4 Building the Plugin

```bash
mkdir build && cd build
cmake -DCMAKE_PREFIX_PATH=/path/to/shield ..
make
```

Output: `shield_my_plugin.so` (Linux) or `shield_my_plugin.dll` (Windows)

---

## 13.5 Loading Plugins

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

### Programmatic Loading

```c
// Load plugin
plugin_handle_t handle;
shield_err_t err = plugin_load("/path/to/shield_my_plugin.so", &handle);
if (err != SHIELD_OK) {
    log_error("Failed to load plugin: %d", err);
    return err;
}

// Get plugin info
shield_plugin_t *plugin = plugin_get_info(handle);
log_info("Loaded plugin: %s v%s by %s",
         plugin->name, plugin->version, plugin->author);

// Register guard
if (plugin->vtable) {
    guard_registry_add(&registry, plugin->vtable);
}
```

---

## 13.6 Plugin Manager

### Implementation

```c
// src/plugin/plugin_manager.c

typedef struct {
    char path[PATH_MAX];
    void *handle;  // dlopen handle
    shield_plugin_t *plugin;
} loaded_plugin_t;

typedef struct {
    loaded_plugin_t plugins[MAX_PLUGINS];
    size_t count;
    const char *plugin_dir;
} plugin_manager_t;

shield_err_t plugin_manager_load_all(plugin_manager_t *pm) {
    DIR *dir = opendir(pm->plugin_dir);
    if (!dir) return SHIELD_ERR_IO;

    struct dirent *entry;
    while ((entry = readdir(dir)) != NULL) {
        // Check for .so/.dll extension
        if (!is_plugin_file(entry->d_name)) continue;

        char path[PATH_MAX];
        snprintf(path, sizeof(path), "%s/%s", pm->plugin_dir, entry->d_name);

        shield_err_t err = plugin_manager_load_one(pm, path);
        if (err != SHIELD_OK) {
            log_warn("Failed to load plugin %s: %d", path, err);
        }
    }

    closedir(dir);
    return SHIELD_OK;
}

shield_err_t plugin_manager_load_one(plugin_manager_t *pm, const char *path) {
    if (pm->count >= MAX_PLUGINS) {
        return SHIELD_ERR_LIMIT;
    }

    // dlopen
    void *handle = dlopen(path, RTLD_NOW);
    if (!handle) {
        log_error("dlopen failed: %s", dlerror());
        return SHIELD_ERR_PLUGIN;
    }

    // Get entry point
    typedef shield_plugin_t* (*get_info_fn)(void);
    get_info_fn get_info = dlsym(handle, "shield_plugin_get_info");
    if (!get_info) {
        dlclose(handle);
        return SHIELD_ERR_PLUGIN;
    }

    shield_plugin_t *plugin = get_info();

    // Version check
    if (plugin->api_version != SHIELD_PLUGIN_API_VERSION) {
        log_error("Plugin API version mismatch: %d != %d",
                  plugin->api_version, SHIELD_PLUGIN_API_VERSION);
        dlclose(handle);
        return SHIELD_ERR_VERSION;
    }

    // Call load
    shield_plugin_ctx_t ctx = create_plugin_context();
    shield_err_t err = plugin->load(&ctx);
    if (err != SHIELD_OK) {
        dlclose(handle);
        return err;
    }

    // Store
    loaded_plugin_t *lp = &pm->plugins[pm->count++];
    strncpy(lp->path, path, sizeof(lp->path));
    lp->handle = handle;
    lp->plugin = plugin;

    log_info("Loaded plugin: %s v%s", plugin->name, plugin->version);
    return SHIELD_OK;
}

void plugin_manager_unload_all(plugin_manager_t *pm) {
    for (size_t i = 0; i < pm->count; i++) {
        loaded_plugin_t *lp = &pm->plugins[i];
        lp->plugin->unload();
        dlclose(lp->handle);
    }
    pm->count = 0;
}
```

---

## 13.7 CLI Commands

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
│ json_logger    │ 1.2.0   │ Community    │ output          │
└────────────────┴─────────┴──────────────┴─────────────────┘

Shield> plugin load /path/to/new_plugin.so
Loading plugin...
Loaded: new_plugin v1.0.0

Shield> plugin unload my_plugin
Unloading plugin...
Unloaded: my_plugin
```

---

## 13.8 Security Considerations

### Plugin Isolation

```c
// Limit what plugins can do
typedef struct {
    bool allow_network;
    bool allow_file_io;
    bool allow_exec;
    size_t max_memory;
} plugin_sandbox_t;

// Validate before loading
shield_err_t plugin_validate(const char *path, plugin_sandbox_t *sandbox);
```

### Signature Verification

```c
// Verify plugin signature
shield_err_t plugin_verify_signature(const char *path, const char *pubkey) {
    // Load signature file
    char sig_path[PATH_MAX];
    snprintf(sig_path, sizeof(sig_path), "%s.sig", path);

    // Verify with public key
    return crypto_verify_file(path, sig_path, pubkey);
}
```

---

## Практика

### Задание 1

Создай Filter Plugin:

- Pre-process: lowercase всего входа
- Post-process: добавить metadata к результату

### Задание 2

Создай Output Plugin:

- Отправка events в Webhook URL
- Batching
- Retry logic

### Задание 3

Добавь signature verification:

- Генерация ключей
- Подпись плагина
- Проверка при загрузке

---

## Итоги Module 13

- Plugin interface и lifecycle
- Dynamic loading (dlopen)
- Plugin manager
- Security considerations
- CLI integration

---

## Следующий модуль

**Module 14: Performance Engineering**

Оптимизация производительности Shield.

---

_"Plugins = extensibility without recompilation."_
