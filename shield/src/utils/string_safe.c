/**
 * @file string_safe.c
 * @brief Safe String Functions Implementation
 * 
 * @author SENTINEL Team
 * @date January 2026
 */

#include "shield_string_safe.h"
#include <string.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>

/* ============================================================================
 * Core Functions
 * ============================================================================ */

size_t shield_strcopy(char *dest, size_t dsize, 
                      const char *src, size_t slen) {
    /* Validate inputs */
    if (!dest || dsize == 0) {
        return 0;
    }
    
    if (!src || slen == 0) {
        dest[0] = '\0';
        return 0;
    }
    
    /* Calculate actual copy length */
    size_t copy_len = (slen < dsize - 1) ? slen : dsize - 1;
    
    /* Copy and null-terminate */
    memcpy(dest, src, copy_len);
    dest[copy_len] = '\0';
    
    return copy_len;
}

size_t shield_strcopy_s(char *dest, size_t dsize, const char *src) {
    if (!src) {
        if (dest && dsize > 0) {
            dest[0] = '\0';
        }
        return 0;
    }
    return shield_strcopy(dest, dsize, src, strlen(src));
}

size_t shield_strcat(char *dest, size_t dsize,
                     const char *src, size_t slen) {
    /* Validate inputs */
    if (!dest || dsize == 0) {
        return 0;
    }
    
    /* Find current end of dest */
    size_t dest_len = strnlen(dest, dsize);
    
    /* Check if buffer is already full */
    if (dest_len >= dsize - 1) {
        dest[dsize - 1] = '\0'; /* Ensure null-termination */
        return dest_len;
    }
    
    if (!src || slen == 0) {
        return dest_len;
    }
    
    /* Calculate remaining space and copy length */
    size_t remaining = dsize - dest_len - 1;
    size_t copy_len = (slen < remaining) ? slen : remaining;
    
    /* Append and null-terminate */
    memcpy(dest + dest_len, src, copy_len);
    dest[dest_len + copy_len] = '\0';
    
    return dest_len + copy_len;
}

size_t shield_strcat_s(char *dest, size_t dsize, const char *src) {
    if (!src) {
        return dest ? strnlen(dest, dsize) : 0;
    }
    return shield_strcat(dest, dsize, src, strlen(src));
}

int shield_snprintf(char *dest, size_t dsize, const char *fmt, ...) {
    if (!dest || dsize == 0 || !fmt) {
        return -1;
    }
    
    va_list args;
    va_start(args, fmt);
    int result = vsnprintf(dest, dsize, fmt, args);
    va_end(args);
    
    /* Ensure null-termination */
    dest[dsize - 1] = '\0';
    
    /* Return -1 if truncated */
    if (result < 0 || (size_t)result >= dsize) {
        return -1;
    }
    
    return result;
}

size_t shield_buf_remaining(const char *buf, size_t bufsize) {
    if (!buf || bufsize == 0) {
        return 0;
    }
    
    size_t used = strnlen(buf, bufsize);
    if (used >= bufsize) {
        return 0;
    }
    
    return bufsize - used;
}

/* ============================================================================
 * Additional Safe Utilities
 * ============================================================================ */

/**
 * @brief Safe string duplicate with size limit
 * 
 * @param src Source string
 * @param max_len Maximum length to copy
 * @return Newly allocated string (caller must free), or NULL on error
 */
char* shield_strndup(const char *src, size_t max_len) {
    if (!src) {
        return NULL;
    }
    
    size_t len = strnlen(src, max_len);
    char *dup = (char*)malloc(len + 1);
    
    if (dup) {
        memcpy(dup, src, len);
        dup[len] = '\0';
    }
    
    return dup;
}

/**
 * @brief Check if string fits in buffer
 * 
 * @param str String to check
 * @param bufsize Buffer size
 * @return true if str fits (including null), false otherwise
 */
int shield_str_fits(const char *str, size_t bufsize) {
    if (!str || bufsize == 0) {
        return 0;
    }
    
    size_t len = strnlen(str, bufsize);
    return len < bufsize;
}
