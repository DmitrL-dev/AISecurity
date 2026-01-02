/*
 * SENTINEL Shield - Input Sanitizer
 * 
 * Sanitize and normalize input before processing
 */

#ifndef SHIELD_SANITIZER_H
#define SHIELD_SANITIZER_H

#include "shield_common.h"

/* Sanitization flags */
typedef enum sanitize_flags {
    SANITIZE_NONE           = 0,
    SANITIZE_TRIM           = 1 << 0,
    SANITIZE_NORMALIZE_WS   = 1 << 1,
    SANITIZE_REMOVE_CONTROL = 1 << 2,
    SANITIZE_NORMALIZE_UNICODE = 1 << 3,
    SANITIZE_UNESCAPE_HTML  = 1 << 4,
    SANITIZE_DECODE_URL     = 1 << 5,
    SANITIZE_DECODE_BASE64  = 1 << 6,
    SANITIZE_LOWERCASE      = 1 << 7,
    SANITIZE_REMOVE_TAGS    = 1 << 8,
    SANITIZE_ALL            = 0xFFFF,
} sanitize_flags_t;

/* Sanitize context */
typedef struct sanitizer {
    sanitize_flags_t default_flags;
    int max_length;
    bool allow_newlines;
    bool allow_tabs;
} sanitizer_t;

/* Initialize */
shield_err_t sanitizer_init(sanitizer_t *san);

/* Sanitize string in place */
char *sanitize_string(sanitizer_t *san, char *str, sanitize_flags_t flags);

/* Sanitize to new buffer */
char *sanitize_copy(sanitizer_t *san, const char *str, sanitize_flags_t flags);

/* Specific sanitizations */
char *sanitize_remove_control_chars(char *str);
char *sanitize_normalize_whitespace(char *str);
char *sanitize_html_unescape(const char *str);
char *sanitize_url_decode(const char *str);
char *sanitize_remove_html_tags(const char *str);

/* Detect encoding */
bool is_base64_encoded(const char *str);
bool is_url_encoded(const char *str);
bool contains_control_chars(const char *str);
bool contains_unicode_control(const char *str);

/* Recursive decode (for layered encoding) */
char *sanitize_recursive_decode(const char *str, int max_iterations);

#endif /* SHIELD_SANITIZER_H */
