# Integration Guide

## Overview

SENTINEL Shield is a **pure C library** designed for integration into any application or infrastructure.

---

## Integration Methods

### 1. Direct C Linking

The primary integration method — link Shield as a static or shared library.

#### Static Library

```bash
# Build (creates both static and shared)
make clean && make

# Link static
gcc -Ipath/to/shield/include \
    my_app.c \
    path/to/shield/build/libshield.a \
    -lssl -lcrypto -lm \
    -o my_app
```

#### Shared Library

```bash
# Build
make clean && make

# Link shared
gcc -Ipath/to/shield/include \
    -Lpath/to/shield/build \
    -lshield \
    my_app.c -o my_app

# Runtime
export LD_LIBRARY_PATH=path/to/shield/build:$LD_LIBRARY_PATH
```

---

### 2. REST API

For any language — integrate via HTTP.

```bash
# Start Shield API server
./shield -c config.json
```

#### Evaluate Input

```bash
curl -X POST http://localhost:8080/api/v1/evaluate \
  -H "Content-Type: application/json" \
  -d '{"input": "user text", "zone": "external"}'
```

Response:

```json
{
  "action": "allow",
  "threat_score": 0.1,
  "intent": "benign"
}
```

#### Filter Output

```bash
curl -X POST http://localhost:8080/api/v1/filter \
  -H "Content-Type: application/json" \
  -d '{"output": "SSN: 123-45-6789"}'
```

Response:

```json
{
  "filtered": "SSN: [REDACTED]",
  "redacted_count": 1
}
```

---

### 3. FFI from Other Languages

Shield exposes a C ABI that can be called from any language with FFI support.

#### Go via cgo

```go
package main

/*
#cgo CFLAGS: -I/path/to/shield/include
#cgo LDFLAGS: -L/path/to/shield/lib -lsentinel-shield
#include "sentinel_shield.h"
*/
import "C"
import "fmt"

func main() {
    var ctx C.shield_context_t
    C.shield_init(&ctx)
    C.shield_load_config(&ctx, C.CString("config.json"))

    var result C.evaluation_result_t
    input := C.CString("test input")
    C.shield_evaluate(&ctx, input, 10,
                      C.CString("external"), C.DIRECTION_INBOUND, &result)

    if result.action == C.ACTION_BLOCK {
        fmt.Println("Blocked!")
    }

    C.shield_destroy(&ctx)
}
```

#### Node.js via node-ffi

```javascript
const ffi = require("ffi-napi");
const ref = require("ref-napi");

const shield = ffi.Library("/path/to/libsentinel-shield", {
  shield_init: ["int", ["pointer"]],
  shield_evaluate: [
    "int",
    ["pointer", "string", "int", "string", "int", "pointer"],
  ],
  shield_destroy: ["void", ["pointer"]],
});

// Usage
const ctx = Buffer.alloc(1024);
shield.shield_init(ctx);
// ...
```

#### Rust via bindgen

```rust
use std::os::raw::c_char;

#[link(name = "sentinel-shield")]
extern "C" {
    fn shield_init(ctx: *mut ShieldContext) -> i32;
    fn shield_evaluate(
        ctx: *mut ShieldContext,
        input: *const c_char,
        input_len: usize,
        zone: *const c_char,
        direction: i32,
        result: *mut EvaluationResult
    ) -> i32;
    fn shield_destroy(ctx: *mut ShieldContext);
}
```

---

## Deployment Patterns

### Sidecar (Kubernetes)

```yaml
apiVersion: v1
kind: Pod
spec:
  containers:
    - name: my-app
      image: my-app:latest
    - name: shield
      image: sentinel/shield:latest
      ports:
        - containerPort: 8080
```

### Nginx Upstream

```nginx
upstream shield {
    server 127.0.0.1:8080;
}

location /api/llm {
    # First check with Shield
    proxy_pass http://shield/api/v1/evaluate;
}
```

### Embedded Library

```c
// Direct embedding in your application
#include "sentinel_shield.h"

void handle_request(const char *input) {
    static shield_context_t ctx;
    static bool initialized = false;

    if (!initialized) {
        shield_init(&ctx);
        shield_load_config(&ctx, "/etc/shield/config.json");
        initialized = true;
    }

    evaluation_result_t result;
    shield_evaluate(&ctx, input, strlen(input),
                    "external", DIRECTION_INBOUND, &result);

    if (result.action == ACTION_BLOCK) {
        reject_request(result.reason);
        return;
    }

    process_request(input);
}
```

---

## Integration Examples

### OpenAI Integration (C + curl)

```c
#include "sentinel_shield.h"
#include <curl/curl.h>

char *call_openai_with_shield(shield_context_t *ctx, const char *prompt) {
    // First: Check with Shield
    evaluation_result_t result;
    shield_evaluate(ctx, prompt, strlen(prompt),
                    "external", DIRECTION_INBOUND, &result);

    if (result.action == ACTION_BLOCK) {
        return strdup("Request blocked for security reasons.");
    }

    // Second: Call OpenAI
    CURL *curl = curl_easy_init();
    // ... setup curl for OpenAI API ...
    char *response = call_api(curl, prompt);
    curl_easy_cleanup(curl);

    // Third: Filter response
    char filtered[8192];
    size_t len;
    shield_filter_output(ctx, response, strlen(response), filtered, &len);

    free(response);
    return strdup(filtered);
}
```

---

## Best Practices

1. **Initialize Once** — Create shield_context_t at startup
2. **Thread Safety** — Each thread needs its own context, or use locking
3. **Error Handling** — Always check return codes
4. **Config Reload** — Use `shield_reload_config()` for dynamic updates
5. **Metrics** — Enable Prometheus for observability

---

_Чистый C. Интеграция с чем угодно._
