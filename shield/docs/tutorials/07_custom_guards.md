# Tutorial 7: Custom Guard Development

> **SSE Module 3.2: Extension Development**

---

## 🎯 Objective

Create custom guards for specific AI components:

- Understand guard architecture
- Implement custom logic
- Register with Shield
- Test and deploy

---

## Guard Architecture

```c
typedef struct guard_vtable {
    const char *name;
    shield_err_t (*init)(void *ctx);
    shield_err_t (*evaluate)(void *ctx, guard_event_t *event, guard_result_t *result);
    void (*destroy)(void *ctx);
} guard_vtable_t;
```

---

## Step 1: Define Guard Structure

```c
// my_custom_guard.h
#ifndef MY_CUSTOM_GUARD_H
#define MY_CUSTOM_GUARD_H

#include "shield_guard.h"

typedef struct {
    guard_t base;
    // Custom fields
    int max_length;
    char *forbidden_words[100];
    int forbidden_count;
} my_custom_guard_t;

shield_err_t my_guard_create(my_custom_guard_t *guard);
void my_guard_destroy(my_custom_guard_t *guard);

#endif
```

---

## Step 2: Implement Guard

```c
// my_custom_guard.c
#include "my_custom_guard.h"

static shield_err_t my_guard_init(void *ctx) {
    my_custom_guard_t *g = (my_custom_guard_t *)ctx;
    g->max_length = 4096;
    return SHIELD_OK;
}

static shield_err_t my_guard_evaluate(
    void *ctx,
    guard_event_t *event,
    guard_result_t *result
) {
    my_custom_guard_t *g = (my_custom_guard_t *)ctx;

    // Check length
    if (event->input_len > g->max_length) {
        result->action = ACTION_BLOCK;
        strcpy(result->reason, "Input too long");
        return SHIELD_OK;
    }

    // Check forbidden words
    for (int i = 0; i < g->forbidden_count; i++) {
        if (strstr(event->input, g->forbidden_words[i])) {
            result->action = ACTION_BLOCK;
            snprintf(result->reason, sizeof(result->reason),
                     "Forbidden word: %s", g->forbidden_words[i]);
            return SHIELD_OK;
        }
    }

    result->action = ACTION_ALLOW;
    return SHIELD_OK;
}

static void my_guard_cleanup(void *ctx) {
    // Cleanup resources
}

// VTable
static guard_vtable_t my_guard_vtable = {
    .name = "my_custom_guard",
    .init = my_guard_init,
    .evaluate = my_guard_evaluate,
    .destroy = my_guard_cleanup,
};

shield_err_t my_guard_create(my_custom_guard_t *guard) {
    memset(guard, 0, sizeof(*guard));
    guard->base.vtable = &my_guard_vtable;
    guard->base.type = GUARD_TYPE_CUSTOM;
    return my_guard_init(guard);
}
```

---

## Step 3: Register Guard

```c
#include "sentinel_shield.h"
#include "my_custom_guard.h"

int main(void) {
    shield_context_t ctx;
    shield_init(&ctx);

    // Create custom guard
    my_custom_guard_t my_guard;
    my_guard_create(&my_guard);

    // Configure
    my_guard.max_length = 2048;
    my_guard.forbidden_words[0] = "banned";
    my_guard.forbidden_count = 1;

    // Register
    shield_register_guard(&ctx, (guard_t *)&my_guard);

    // Use
    evaluation_result_t result;
    shield_evaluate(&ctx, "test input", 10, "external",
                    DIRECTION_INBOUND, &result);

    my_guard_destroy(&my_guard);
    shield_destroy(&ctx);
    return 0;
}
```

---

## Step 4: Build Custom Guard

```bash
# Compile guard as shared library
gcc -shared -fPIC -Ipath/to/shield/include \
    my_custom_guard.c -o libmy_guard.so

# Link with your application
gcc -Ipath/to/shield/include \
    -Lpath/to/shield/build -lshield \
    -L. -lmy_guard \
    my_app.c -o my_app
```

---

## Step 5: Test Custom Guard

```c
// test_my_guard.c
#include "my_custom_guard.h"
#include <assert.h>

void test_my_guard(void) {
    my_custom_guard_t guard;
    my_guard_create(&guard);
    guard.max_length = 100;

    guard_event_t event = {.input = "short", .input_len = 5};
    guard_result_t result;

    guard.base.vtable->evaluate(&guard, &event, &result);
    assert(result.action == ACTION_ALLOW);

    // Test too long
    char long_input[200];
    memset(long_input, 'a', 199);
    long_input[199] = '\0';

    event.input = long_input;
    event.input_len = 199;

    guard.base.vtable->evaluate(&guard, &event, &result);
    assert(result.action == ACTION_BLOCK);

    printf("All tests passed!\n");
    my_guard_destroy(&guard);
}

int main(void) {
    test_my_guard();
    return 0;
}
```

---

## 🎉 What You Learned

- ✅ Guard vtable architecture
- ✅ Implement custom evaluate logic
- ✅ Register with Shield
- ✅ Build as shared library
- ✅ Testing guards

---

## Next Tutorial

**Tutorial 8:** Pattern Engineering

---

_"Every AI component deserves its own guardian."_
