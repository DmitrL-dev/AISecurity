# SENTINEL Academy — Module 12

## Custom Guard Development

_SSE Level | Duration: 5 hours_

---

## Guard Interface

```c
typedef struct {
    shield_err_t (*init)(void **state, const config_t *cfg);
    shield_err_t (*check)(void *state, const request_t *req, 
                          check_result_t *result);
    void (*destroy)(void *state);
} guard_interface_t;
```

---

## Creating a Custom Guard

### 1. Define State

```c
typedef struct {
    regex_t *patterns;
    int pattern_count;
    float threshold;
} my_guard_state_t;
```

### 2. Implement Functions

```c
static shield_err_t my_guard_init(void **state, const config_t *cfg) {
    my_guard_state_t *s = calloc(1, sizeof(*s));
    s->threshold = config_get_float(cfg, "threshold", 0.5);
    *state = s;
    return SHIELD_OK;
}

static shield_err_t my_guard_check(void *state, const request_t *req,
                                    check_result_t *result) {
    my_guard_state_t *s = state;
    result->score = analyze(req->input, req->len);
    result->blocked = result->score > s->threshold;
    return SHIELD_OK;
}

static void my_guard_destroy(void *state) {
    free(state);
}
```

### 3. Register

```c
guard_interface_t my_guard = {
    .init = my_guard_init,
    .check = my_guard_check,
    .destroy = my_guard_destroy
};

guard_register("my_guard", &my_guard);
```

---

## Testing

```c
void test_my_guard(void) {
    void *state;
    my_guard_init(&state, NULL);
    
    request_t req = { .input = "test", .len = 4 };
    check_result_t result;
    my_guard_check(state, &req, &result);
    
    assert(result.score >= 0);
    my_guard_destroy(state);
}
```

---

_"Custom guards extend Shield's power."_
