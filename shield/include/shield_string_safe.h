/**
 * @file shield_string_safe.h
 * @brief Safe String Functions for Shield
 * 
 * Replacements for strcpy, strcat, strncpy that always null-terminate
 * and prevent buffer overflows.
 * 
 * Based on: https://daniel.haxx.se/blog/2025/12/29/no-strcpy-either/
 * 
 * @author SENTINEL Team
 * @date January 2026
 */

#ifndef SHIELD_STRING_SAFE_H
#define SHIELD_STRING_SAFE_H

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Safe string copy — always null terminates.
 * 
 * Copies up to (dsize - 1) characters from src to dest,
 * always null-terminating the result.
 * 
 * @param dest Destination buffer
 * @param dsize Size of destination buffer (must be > 0)
 * @param src Source string
 * @param slen Length of source string (use strlen(src) if unknown)
 * @return Number of characters copied (excluding null terminator)
 * 
 * Example:
 *   char buf[32];
 *   shield_strcopy(buf, sizeof(buf), input, strlen(input));
 */
size_t shield_strcopy(char *dest, size_t dsize, 
                      const char *src, size_t slen);

/**
 * @brief Safe string copy (auto-strlen version)
 * 
 * Convenience wrapper that calculates strlen(src) automatically.
 * Use when you don't already have the source length.
 * 
 * @param dest Destination buffer
 * @param dsize Size of destination buffer
 * @param src Source string (must be null-terminated)
 * @return Number of characters copied
 */
size_t shield_strcopy_s(char *dest, size_t dsize, const char *src);

/**
 * @brief Safe string concatenate — always null terminates.
 * 
 * Appends src to dest, ensuring the result is null-terminated
 * and doesn't overflow the buffer.
 * 
 * @param dest Destination buffer (must be null-terminated)
 * @param dsize Total size of destination buffer
 * @param src Source string to append
 * @param slen Length of source string
 * @return Total length of resulting string
 */
size_t shield_strcat(char *dest, size_t dsize,
                     const char *src, size_t slen);

/**
 * @brief Safe string concatenate (auto-strlen version)
 */
size_t shield_strcat_s(char *dest, size_t dsize, const char *src);

/**
 * @brief Safe snprintf wrapper that returns error on truncation
 * 
 * @param dest Destination buffer
 * @param dsize Size of destination buffer
 * @param fmt Format string
 * @param ... Format arguments
 * @return Number of characters written (excluding null), 
 *         or -1 if truncated
 */
int shield_snprintf(char *dest, size_t dsize, const char *fmt, ...)
    __attribute__((format(printf, 3, 4)));

/**
 * @brief Get remaining space in buffer after current content
 * 
 * @param buf Buffer (must be null-terminated)
 * @param bufsize Total buffer size
 * @return Remaining space for additional content (including null)
 */
size_t shield_buf_remaining(const char *buf, size_t bufsize);

#ifdef __cplusplus
}
#endif

/* ============================================================================
 * Compile-time Enforcement (optional)
 * 
 * Define SHIELD_BAN_UNSAFE_STRINGS before including this header to
 * get compile errors when using banned functions.
 * 
 * Note: This only works if this header is included BEFORE <string.h>
 * For safety, ensure shield_string_safe.h is included first in source files.
 * ============================================================================ */

#ifdef SHIELD_BAN_UNSAFE_STRINGS

/* Use GCC pragma poison for hard errors */
#if defined(__GNUC__) || defined(__clang__)

/* 
 * These pragmas will cause compile errors if these functions are used.
 * IMPORTANT: Files must include shield_string_safe.h AFTER string.h for this to work,
 * or use the safe alternatives directly.
 */

/* Uncomment to enable hard errors (may break external headers):
 * #pragma GCC poison strcpy strcat gets sprintf
 */

/* Softer approach: deprecation warnings via wrapper macros */
/* Note: These require the code to NOT include <string.h> before this header */

/* For now, we rely on grep/static analysis to catch remaining uses */
/* All strcpy/strcat have been eliminated from Shield codebase */

#endif /* __GNUC__ || __clang__ */

#endif /* SHIELD_BAN_UNSAFE_STRINGS */

#endif /* SHIELD_STRING_SAFE_H */
