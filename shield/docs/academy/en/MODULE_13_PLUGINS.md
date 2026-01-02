# SENTINEL Academy — Module 13

## Plugin System

_SSE Level | Duration: 4 hours_

---

## Architecture

```
┌─────────────────────────────────────────┐
│              Shield Core                 │
├─────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌────────┐│
│  │ plugin_a │  │ plugin_b │  │plugin_c││
│  └──────────┘  └──────────┘  └────────┘│
└─────────────────────────────────────────┘
```

---

## Plugin Interface

```c
typedef struct {
    const char *name;
    const char *version;
    
    shield_err_t (*on_load)(plugin_ctx_t *ctx);
    shield_err_t (*on_unload)(plugin_ctx_t *ctx);
    shield_err_t (*on_request)(plugin_ctx_t *ctx, request_t *req);
    shield_err_t (*on_response)(plugin_ctx_t *ctx, response_t *resp);
} plugin_t;
```

---

## Creating a Plugin

```c
#include "shield_plugin.h"

static shield_err_t my_on_load(plugin_ctx_t *ctx) {
    printf("Plugin loaded\n");
    return SHIELD_OK;
}

static shield_err_t my_on_request(plugin_ctx_t *ctx, request_t *req) {
    // Process request
    return SHIELD_OK;
}

SHIELD_PLUGIN_EXPORT plugin_t plugin = {
    .name = "my_plugin",
    .version = "1.0.0",
    .on_load = my_on_load,
    .on_request = my_on_request
};
```

---

## Loading Plugins

### CLI

```
Shield(config)# plugin load /usr/lib/shield/my_plugin.so
Shield# show plugins
```

### Config

```json
{
  "plugins": [
    { "path": "/usr/lib/shield/my_plugin.so" }
  ]
}
```

---

_"Plugins enable infinite extensibility."_
