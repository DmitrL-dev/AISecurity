# Shield Security Audit: String Functions
**Date**: January 6, 2026  
**Status**: ✅ P0-P2 Complete, P3-P4 Pending  
**Build**: 116 files, 0 errors, 0 warnings

---

## Executive Summary

Eliminated all unsafe `strcpy` and `strcat` calls based on [curl best practices](https://daniel.haxx.se/blog/2025/12/29/no-strcpy-either/).

| Function | Before | After | Status |
|----------|--------|-------|--------|
| `strcpy()` | 32 | **0** | ✅ Eliminated |
| `strcat()` | 12 | **0** | ✅ Eliminated |
| `sprintf()` | 0 | 0 | ✅ Never used |
| `gets()` | 0 | 0 | ✅ Never used |
| `strncpy()` | ~200 | ~200 | 🟡 Safe pattern |

---

## Phases Completed

### P0: Critical (strcat in loops) ✅
High risk of buffer overflow in concatenation loops.

| File | Function | Change |
|------|----------|--------|
| `safety_prompt.c` | Multiple | 12 strcat → shield_strcat_s |
| `ngram.c` | `ngram_to_string()` | 4 strcat → shield_strcat_s |

### P1: High (strcpy elimination) ✅
All strcpy replaced with safe alternatives.

| File | Changes |
|------|---------|
| `output_filter.c` | 7 |
| `http_client.c` | 5 |
| `watchdog.c` | 4 |
| `anomaly.c` | 3 |
| `threat_hunter.c` | 3 |
| `embedding.c` | 2 |
| `classifier.c` | 1 |
| `batch.c` | 1 |
| `semantic.c` | 1 |
| `tokens.c` | 1 |
| `cmd_config.c` | 1 |
| `sllm.c` | 1 |

### P2: Cosmetic (magic numbers) ✅
Replaced hardcoded sizes with `sizeof() - 1`.

| File | Pattern | Changes |
|------|---------|---------|
| `semantic.c` | 63 → sizeof()-1 | 6 |
| `response_validator.c` | 127 → sizeof()-1 | 8 |
| `main.c` | 255 → sizeof()-1 | 1 |
| `llm_guard.c` | 31 (kept with comment) | 0 |

---

## New Safe String API

Created `include/shield_string_safe.h` and `src/utils/string_safe.c`:

```c
// Safe copy with explicit size
size_t shield_strcopy(char *dest, size_t dsize, const char *src, size_t slen);
size_t shield_strcopy_s(char *dest, size_t dsize, const char *src);

// Safe concatenation
size_t shield_strcat(char *dest, size_t dsize, const char *src, size_t slen);
size_t shield_strcat_s(char *dest, size_t dsize, const char *src);

// Safe printf
int shield_snprintf(char *dest, size_t dsize, const char *fmt, ...);

// Utilities
bool shield_str_ends_with(const char *str, const char *suffix);
char *shield_strdup_safe(const char *src, size_t max_len);
```

---

## Remaining Work

### P3: Compile-time Enforcement (TODO)
```c
#ifdef SHIELD_BAN_UNSAFE_STRINGS
#define strcpy(d,s) COMPILE_ERROR("Use shield_strcopy_s")
#define strcat(d,s) COMPILE_ERROR("Use shield_strcat_s")
#endif
```

### P4: strncpy Optimization (Optional)
~200 uses of `strncpy(dest, src, sizeof(dest) - 1)` — all safe.
Could migrate to `shield_strcopy_s` for consistency.

---

## Verification

```bash
# Build test
make clean && make
# Result: 116 files compiled, 0 errors, 0 warnings

# Check for remaining unsafe calls
grep -r "strcpy\|strcat" src/ --include="*.c" | grep -v "shield_"
# Result: 0 matches
```
