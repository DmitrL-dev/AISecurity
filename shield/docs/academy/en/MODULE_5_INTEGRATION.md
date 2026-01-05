# SENTINEL Academy — Module 5

## Code Integration

_SSA Level | Duration: 4 hours_

---

## Introduction

You've learned theory, configured Shield.

Now — integration into real applications.

All in **pure C**.

---

## 5.1 C API Overview

### Main Header

```c
#include "sentinel_shield.h"
```

### Core Types

```c
// Shield context
typedef struct shield_context shield_context_t;

// Evaluation result
typedef struct {
    action_t action;          // ALLOW, BLOCK, LOG, SANITIZE
    float threat_score;       // 0.0 - 1.0
    char reason[256];         // Decision reason
    char matched_rules[1024]; // JSON array
    uint64_t processing_ns;   // Processing time
} evaluation_result_t;

// Direction
typedef enum {
    DIRECTION_INBOUND,   // Input (from user)
    DIRECTION_OUTBOUND   // Output (from AI)
} direction_t;

// Actions
typedef enum {
    ACTION_ALLOW,
    ACTION_BLOCK,
    ACTION_LOG,
    ACTION_SANITIZE
} action_t;
```

---

## 5.2 Basic Integration

### Minimal Example

```c
#include <stdio.h>
#include <string.h>
#include "sentinel_shield.h"

int main(void) {
    // 1. Initialization
    shield_context_t ctx;
    shield_err_t err = shield_init(&ctx);
    if (err != SHIELD_OK) {
        fprintf(stderr, "Failed to init Shield: %s\n", shield_error_str(err));
        return 1;
    }

    // 2. Load configuration
    err = shield_load_config(&ctx, "config.json");
    if (err != SHIELD_OK) {
        fprintf(stderr, "Failed to load config: %s\n", shield_error_str(err));
        shield_destroy(&ctx);
        return 1;
    }

    // 3. Evaluate input
    const char *user_input = "Hello, what is 2+2?";
    evaluation_result_t result;

    err = shield_evaluate(&ctx,
                          user_input, strlen(user_input),
                          "external", DIRECTION_INBOUND,
                          &result);

    if (err != SHIELD_OK) {
        fprintf(stderr, "Evaluation error: %s\n", shield_error_str(err));
        shield_destroy(&ctx);
        return 1;
    }

    // 4. Make decision
    if (result.action == ACTION_BLOCK) {
        printf("BLOCKED: %s\n", result.reason);
    } else {
        printf("ALLOWED (threat: %.2f)\n", result.threat_score);
        // Can send to AI
    }

    // 5. Cleanup
    shield_destroy(&ctx);
    return 0;
}
```

### Compilation

```bash
gcc -I/path/to/shield/include \
    -L/path/to/shield/lib \
    -lsentinel-shield \
    my_app.c -o my_app
```

---

## 5.3 Full Cycle (Input + Output)

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "sentinel_shield.h"

// Simulate AI call
char* call_ai_model(const char *input) {
    // In reality — HTTP request to OpenAI/Anthropic
    return strdup("The answer is 4. Your API key is sk-abc123.");
}

int main(void) {
    shield_context_t ctx;
    shield_init(&ctx);
    shield_load_config(&ctx, "config.json");

    const char *user_input = "What is 2+2?";
    evaluation_result_t result;

    // ═══════════════════════════════════════════
    // STEP 1: Check INPUT
    // ═══════════════════════════════════════════
    shield_evaluate(&ctx,
                    user_input, strlen(user_input),
                    "external", DIRECTION_INBOUND,
                    &result);

    if (result.action == ACTION_BLOCK) {
        printf("Input blocked: %s\n", result.reason);
        shield_destroy(&ctx);
        return 1;
    }

    printf("[INPUT] Allowed, threat=%.2f\n", result.threat_score);

    // ═══════════════════════════════════════════
    // STEP 2: Call AI MODEL
    // ═══════════════════════════════════════════
    char *ai_response = call_ai_model(user_input);
    printf("[AI] Response: %s\n", ai_response);

    // ═══════════════════════════════════════════
    // STEP 3: Filter OUTPUT
    // ═══════════════════════════════════════════
    char filtered[4096];
    size_t filtered_len;
    filter_result_t filter_result;

    shield_filter_output(&ctx,
                          ai_response, strlen(ai_response),
                          filtered, &filtered_len,
                          &filter_result);

    if (filter_result.redacted_count > 0) {
        printf("[OUTPUT] Redacted %d sensitive items\n",
               filter_result.redacted_count);
    }

    // ═══════════════════════════════════════════
    // STEP 4: Return SAFE response
    // ═══════════════════════════════════════════
    printf("[SAFE] %s\n", filtered);
    // Output: "The answer is 4. Your API key is [REDACTED]."

    free(ai_response);
    shield_destroy(&ctx);
    return 0;
}
```

---

## 5.4 Error Handling

### Error Codes

```c
typedef enum {
    SHIELD_OK = 0,
    SHIELD_ERR_INIT,
    SHIELD_ERR_CONFIG,
    SHIELD_ERR_INVALID_INPUT,
    SHIELD_ERR_INVALID_ZONE,
    SHIELD_ERR_MEMORY,
    SHIELD_ERR_INTERNAL
} shield_err_t;
```

### Handling Pattern

```c
shield_err_t err = shield_evaluate(&ctx, input, len, zone, dir, &result);

switch (err) {
    case SHIELD_OK:
        // Success
        break;
    case SHIELD_ERR_INVALID_ZONE:
        fprintf(stderr, "Unknown zone: %s\n", zone);
        // Fallback to default zone
        break;
    case SHIELD_ERR_INVALID_INPUT:
        fprintf(stderr, "Invalid input\n");
        // Reject request
        break;
    default:
        fprintf(stderr, "Internal error: %s\n", shield_error_str(err));
        // Log and fallback
        break;
}
```

---

## 5.5 Thread Safety

### Rules

1. **shield_context_t** — NOT thread-safe
2. Each thread must have its own context
3. OR use mutex

### Option 1: Context per thread

```c
#include <pthread.h>

void* worker_thread(void *arg) {
    // Each thread — own context
    shield_context_t ctx;
    shield_init(&ctx);
    shield_load_config(&ctx, "config.json");

    // ... work ...

    shield_destroy(&ctx);
    return NULL;
}
```

### Option 2: Shared context + mutex

```c
#include <pthread.h>

static shield_context_t g_ctx;
static pthread_mutex_t g_mutex = PTHREAD_MUTEX_INITIALIZER;

shield_err_t safe_evaluate(const char *input, size_t len,
                           const char *zone,
                           evaluation_result_t *result) {
    pthread_mutex_lock(&g_mutex);
    shield_err_t err = shield_evaluate(&g_ctx, input, len,
                                        zone, DIRECTION_INBOUND, result);
    pthread_mutex_unlock(&g_mutex);
    return err;
}
```

---

## 5.6 Integration with HTTP Server

### Example with libmicrohttpd

```c
#include <microhttpd.h>
#include "sentinel_shield.h"

static shield_context_t g_ctx;

static int handle_request(void *cls,
                          struct MHD_Connection *connection,
                          const char *url,
                          const char *method,
                          const char *version,
                          const char *upload_data,
                          size_t *upload_data_size,
                          void **con_cls) {

    if (strcmp(method, "POST") != 0) {
        return MHD_NO;
    }

    // Get input from POST body
    const char *user_input = upload_data;

    // Check through Shield
    evaluation_result_t result;
    shield_evaluate(&g_ctx, user_input, strlen(user_input),
                    "external", DIRECTION_INBOUND, &result);

    char response[1024];
    if (result.action == ACTION_BLOCK) {
        snprintf(response, sizeof(response),
                 "{\"error\": \"blocked\", \"reason\": \"%s\"}",
                 result.reason);
    } else {
        // Call AI and return
        snprintf(response, sizeof(response),
                 "{\"status\": \"ok\", \"threat\": %.2f}",
                 result.threat_score);
    }

    struct MHD_Response *resp = MHD_create_response_from_buffer(
        strlen(response), response, MHD_RESPMEM_MUST_COPY);
    int ret = MHD_queue_response(connection, MHD_HTTP_OK, resp);
    MHD_destroy_response(resp);

    return ret;
}

int main(void) {
    shield_init(&g_ctx);
    shield_load_config(&g_ctx, "config.json");

    struct MHD_Daemon *daemon = MHD_start_daemon(
        MHD_USE_SELECT_INTERNALLY,
        8080, NULL, NULL,
        &handle_request, NULL,
        MHD_OPTION_END);

    printf("Server running on port 8080\n");
    getchar();  // Wait for Enter

    MHD_stop_daemon(daemon);
    shield_destroy(&g_ctx);
    return 0;
}
```

---

## 5.7 Callbacks and Hooks

### Event callbacks

```c
void on_block(const char *input, const char *rule, void *user_data) {
    printf("Blocked: %s (rule: %s)\n", input, rule);
    // Log to file, send alert, etc.
}

void on_threat(float score, const char *input, void *user_data) {
    if (score > 0.5) {
        printf("High threat detected: %.2f\n", score);
    }
}

int main(void) {
    shield_context_t ctx;
    shield_init(&ctx);

    // Register callbacks
    shield_on_block(&ctx, on_block, NULL);
    shield_on_threat(&ctx, on_threat, NULL);

    shield_load_config(&ctx, "config.json");
    // ...
}
```

---

## 5.8 Performance Tips

### 1. Reuse context

```c
// BAD: Create per request
void handle(const char *input) {
    shield_context_t ctx;
    shield_init(&ctx);
    shield_load_config(&ctx, "config.json");  // Slow!
    // ...
    shield_destroy(&ctx);
}

// GOOD: Once at startup
static shield_context_t g_ctx;

void init(void) {
    shield_init(&g_ctx);
    shield_load_config(&g_ctx, "config.json");
}

void handle(const char *input) {
    // Use g_ctx
}
```

### 2. Async logging

```c
// Enable async logging
shield_set_option(&ctx, SHIELD_OPT_ASYNC_LOG, "true");
```

### 3. Rule ordering

Fast rules (literal) first:

```json
{
  "rules": [
    { "id": 1, "pattern": "badword", "pattern_type": "literal" },
    { "id": 2, "pattern": "complex.*regex", "pattern_type": "regex" },
    { "id": 3, "pattern": "semantic_check", "pattern_type": "semantic" }
  ]
}
```

---

## Practice

### Task 1

Write a C program that:
1. Reads input from stdin
2. Checks through Shield
3. Outputs result

### Task 2

Modify program to:
1. If ALLOW — simulate AI response
2. Filter output through Shield
3. Output safe response

### Task 3

Add:
1. Callback on each block
2. Logging to file
3. Statistics counting

---

## Module 5 Summary

- C API is simple and clear
- Init → Config → Evaluate → Destroy
- Thread safety via mutex or separate contexts
- Callbacks for extensibility
- Performance via reuse and ordering

---

## SSA Completion

🎉 **Congratulations!**

You've completed all SSA modules:

1. ✅ Module 0: Why AI is Unsafe
2. ✅ Module 1: Attacks on AI
3. ✅ Module 2: Shield Architecture
4. ✅ Module 3: Installation
5. ✅ Module 4: Rules
6. ✅ Module 5: Integration

**Next step:** Take the SSA-100 exam!

---

_"Know the theory. Know the practice. Ready for certification."_
