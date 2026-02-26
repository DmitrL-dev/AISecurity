/**
 * @file safe_memory.c
 * @brief IMMUNE Safe Memory Management Implementation
 * 
 * @author SENTINEL R&D
 * @date 2026-01-07
 */

#include "safe_memory.h"

#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <stdio.h>
#include <limits.h>

/* ============================================================================
 * Internal Helpers
 * ============================================================================ */

/** Volatile memset that won't be optimized away */
static void volatile_memset(volatile void* ptr, int value, size_t size) {
    volatile unsigned char* p = (volatile unsigned char*)ptr;
    while (size--) {
        *p++ = (unsigned char)value;
    }
}

/* ============================================================================
 * Allocation Functions
 * ============================================================================ */

void* safe_alloc(size_t size) {
    if (size == 0 || size > SAFE_MAX_ALLOC_SIZE) {
        return NULL;
    }
    
    void* ptr = calloc(1, size);
    /* calloc already zero-initializes */
    return ptr;
}

void* safe_calloc(size_t count, size_t elem_size) {
    if (count == 0 || elem_size == 0) {
        return NULL;
    }
    
    /* Check for overflow */
    size_t total;
    if (!safe_mul_size(count, elem_size, &total)) {
        return NULL;
    }
    
    if (total > SAFE_MAX_ALLOC_SIZE) {
        return NULL;
    }
    
    return calloc(count, elem_size);
}

void* safe_realloc(void* ptr, size_t new_size) {
    if (new_size == 0) {
        /* realloc(ptr, 0) behavior is implementation-defined */
        /* We choose to free and return NULL */
        if (ptr) {
            free(ptr);
        }
        return NULL;
    }
    
    if (new_size > SAFE_MAX_ALLOC_SIZE) {
        return NULL;
    }
    
    return realloc(ptr, new_size);
}

void safe_free(void** pptr) {
    if (pptr == NULL || *pptr == NULL) {
        return;
    }
    
    free(*pptr);
    *pptr = NULL;
}

void safe_free_size(void** pptr, size_t size) {
    if (pptr == NULL || *pptr == NULL) {
        return;
    }
    
#if SAFE_POISON_ON_FREE
    /* Poison memory before freeing (helps detect UAF in debug) */
    if (size > 0) {
        volatile_memset(*pptr, SAFE_POISON_BYTE, size);
    }
#else
    (void)size;
#endif
    
    free(*pptr);
    *pptr = NULL;
}

/* ============================================================================
 * String Functions
 * ============================================================================ */

size_t safe_strcpy(char* dst, const char* src, size_t dst_size) {
    if (dst == NULL || src == NULL) {
        return 0;
    }
    
    if (dst_size == 0) {
        return strlen(src);
    }
    
    size_t src_len = strlen(src);
    size_t copy_len = (src_len < dst_size - 1) ? src_len : dst_size - 1;
    
    memcpy(dst, src, copy_len);
    dst[copy_len] = '\0';
    
    return src_len;
}

size_t safe_strcat(char* dst, const char* src, size_t dst_size) {
    if (dst == NULL || src == NULL) {
        return 0;
    }
    
    size_t dst_len = strlen(dst);
    size_t src_len = strlen(src);
    
    if (dst_len >= dst_size) {
        /* dst is already full or oversized */
        return dst_size + src_len;
    }
    
    size_t remaining = dst_size - dst_len - 1;
    size_t copy_len = (src_len < remaining) ? src_len : remaining;
    
    memcpy(dst + dst_len, src, copy_len);
    dst[dst_len + copy_len] = '\0';
    
    return dst_len + src_len;
}

int safe_sprintf(char* dst, size_t dst_size, const char* fmt, ...) {
    if (dst == NULL || dst_size == 0 || fmt == NULL) {
        return -1;
    }
    
    va_list args;
    va_start(args, fmt);
    int ret = vsnprintf(dst, dst_size, fmt, args);
    va_end(args);
    
    /* Ensure null-termination even if vsnprintf didn't */
    dst[dst_size - 1] = '\0';
    
    return ret;
}

char* safe_strdup(const char* src, size_t max_len) {
    if (src == NULL) {
        return NULL;
    }
    
    size_t src_len = strlen(src);
    size_t copy_len = (src_len < max_len) ? src_len : max_len;
    
    char* dst = safe_alloc(copy_len + 1);
    if (dst == NULL) {
        return NULL;
    }
    
    memcpy(dst, src, copy_len);
    dst[copy_len] = '\0';
    
    return dst;
}

/* ============================================================================
 * Buffer Operations
 * ============================================================================ */

bool safe_memcpy(void* dst, size_t dst_size, const void* src, size_t count) {
    if (dst == NULL || src == NULL) {
        return false;
    }
    
    if (count == 0) {
        return true;
    }
    
    if (count > dst_size) {
        return false; /* Would overflow */
    }
    
    /* Check for overlap */
    const unsigned char* s = (const unsigned char*)src;
    unsigned char* d = (unsigned char*)dst;
    
    if ((s < d && s + count > d) || (d < s && d + count > s)) {
        return false; /* Overlap detected, use safe_memmove instead */
    }
    
    memcpy(dst, src, count);
    return true;
}

bool safe_memmove(void* dst, size_t dst_size, const void* src, size_t count) {
    if (dst == NULL || src == NULL) {
        return false;
    }
    
    if (count == 0) {
        return true;
    }
    
    if (count > dst_size) {
        return false; /* Would overflow */
    }
    
    memmove(dst, src, count);
    return true;
}

void safe_memzero(void* ptr, size_t size) {
    if (ptr == NULL || size == 0) {
        return;
    }
    
    volatile_memset(ptr, 0, size);
}

/* ============================================================================
 * Validation Helpers
 * ============================================================================ */

bool safe_mul_size(size_t a, size_t b, size_t* result) {
    if (a == 0 || b == 0) {
        if (result) *result = 0;
        return true;
    }
    
    /* Check: a * b would overflow if a > SIZE_MAX / b */
    if (a > SIZE_MAX / b) {
        return false;
    }
    
    if (result) {
        *result = a * b;
    }
    return true;
}

bool safe_add_size(size_t a, size_t b, size_t* result) {
    /* Check: a + b would overflow if a > SIZE_MAX - b */
    if (a > SIZE_MAX - b) {
        return false;
    }
    
    if (result) {
        *result = a + b;
    }
    return true;
}
