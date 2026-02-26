/*
 * SENTINEL Shield - Input Sanitizer Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

#include "shield_sanitizer.h"
#include "shield_base64.h"

/* Initialize sanitizer */
shield_err_t sanitizer_init(sanitizer_t *san)
{
    if (!san) return SHIELD_ERR_INVALID;
    
    san->default_flags = SANITIZE_TRIM | SANITIZE_REMOVE_CONTROL;
    san->max_length = 100000;
    san->allow_newlines = true;
    san->allow_tabs = true;
    
    return SHIELD_OK;
}

/* Remove control characters */
char *sanitize_remove_control_chars(char *str)
{
    if (!str) return NULL;
    
    char *read = str;
    char *write = str;
    
    while (*read) {
        unsigned char c = (unsigned char)*read;
        
        /* Keep printable, space, tab, newlines */
        if (c >= 32 || c == '\n' || c == '\r' || c == '\t') {
            *write++ = *read;
        }
        read++;
    }
    *write = '\0';
    
    return str;
}

/* Normalize whitespace */
char *sanitize_normalize_whitespace(char *str)
{
    if (!str) return NULL;
    
    char *read = str;
    char *write = str;
    bool last_was_space = true;  /* Trim leading */
    
    while (*read) {
        if (isspace((unsigned char)*read)) {
            if (!last_was_space) {
                *write++ = ' ';
                last_was_space = true;
            }
        } else {
            *write++ = *read;
            last_was_space = false;
        }
        read++;
    }
    
    /* Trim trailing */
    if (write > str && *(write - 1) == ' ') {
        write--;
    }
    *write = '\0';
    
    return str;
}

/* HTML unescape */
char *sanitize_html_unescape(const char *str)
{
    if (!str) return NULL;
    
    size_t len = strlen(str);
    char *out = malloc(len + 1);
    if (!out) return NULL;
    
    const char *read = str;
    char *write = out;
    
    while (*read) {
        if (*read == '&') {
            if (strncmp(read, "&amp;", 5) == 0) {
                *write++ = '&';
                read += 5;
            } else if (strncmp(read, "&lt;", 4) == 0) {
                *write++ = '<';
                read += 4;
            } else if (strncmp(read, "&gt;", 4) == 0) {
                *write++ = '>';
                read += 4;
            } else if (strncmp(read, "&quot;", 6) == 0) {
                *write++ = '"';
                read += 6;
            } else if (strncmp(read, "&apos;", 6) == 0) {
                *write++ = '\'';
                read += 6;
            } else if (strncmp(read, "&#", 2) == 0) {
                /* Numeric entity */
                const char *p = read + 2;
                int code = 0;
                if (*p == 'x' || *p == 'X') {
                    p++;
                    while (isxdigit((unsigned char)*p)) {
                        code = code * 16 + (isdigit((unsigned char)*p) ? 
                               *p - '0' : (tolower((unsigned char)*p) - 'a' + 10));
                        p++;
                    }
                } else {
                    while (isdigit((unsigned char)*p)) {
                        code = code * 10 + (*p - '0');
                        p++;
                    }
                }
                if (*p == ';' && code > 0 && code < 128) {
                    *write++ = (char)code;
                    read = p + 1;
                } else {
                    *write++ = *read++;
                }
            } else {
                *write++ = *read++;
            }
        } else {
            *write++ = *read++;
        }
    }
    *write = '\0';
    
    return out;
}

/* URL decode */
char *sanitize_url_decode(const char *str)
{
    if (!str) return NULL;
    
    size_t len = strlen(str);
    char *out = malloc(len + 1);
    if (!out) return NULL;
    
    const char *read = str;
    char *write = out;
    
    while (*read) {
        if (*read == '%' && isxdigit((unsigned char)read[1]) && 
            isxdigit((unsigned char)read[2])) {
            int hi = isdigit((unsigned char)read[1]) ? 
                     read[1] - '0' : (tolower((unsigned char)read[1]) - 'a' + 10);
            int lo = isdigit((unsigned char)read[2]) ? 
                     read[2] - '0' : (tolower((unsigned char)read[2]) - 'a' + 10);
            *write++ = (char)((hi << 4) | lo);
            read += 3;
        } else if (*read == '+') {
            *write++ = ' ';
            read++;
        } else {
            *write++ = *read++;
        }
    }
    *write = '\0';
    
    return out;
}

/* Remove HTML tags */
char *sanitize_remove_html_tags(const char *str)
{
    if (!str) return NULL;
    
    size_t len = strlen(str);
    char *out = malloc(len + 1);
    if (!out) return NULL;
    
    const char *read = str;
    char *write = out;
    bool in_tag = false;
    
    while (*read) {
        if (*read == '<') {
            in_tag = true;
        } else if (*read == '>') {
            in_tag = false;
        } else if (!in_tag) {
            *write++ = *read;
        }
        read++;
    }
    *write = '\0';
    
    return out;
}

/* Sanitize to new buffer */
char *sanitize_copy(sanitizer_t *san, const char *str, sanitize_flags_t flags)
{
    if (!str) return NULL;
    
    char *result = strdup(str);
    if (!result) return NULL;
    
    return sanitize_string(san, result, flags);
}

/* Main sanitize function */
char *sanitize_string(sanitizer_t *san, char *str, sanitize_flags_t flags)
{
    if (!str) return NULL;
    
    if (san) {
        flags |= san->default_flags;
    }
    
    /* Order matters for some sanitizations */
    
    if (flags & SANITIZE_DECODE_URL) {
        char *decoded = sanitize_url_decode(str);
        if (decoded) {
            free(str);
            str = decoded;
        }
    }
    
    if (flags & SANITIZE_DECODE_BASE64) {
        if (is_base64_encoded(str)) {
            size_t out_len;
            uint8_t *decoded = base64_decode(str, &out_len);
            if (decoded) {
                free(str);
                str = (char *)decoded;
            }
        }
    }
    
    if (flags & SANITIZE_UNESCAPE_HTML) {
        char *unescaped = sanitize_html_unescape(str);
        if (unescaped) {
            free(str);
            str = unescaped;
        }
    }
    
    if (flags & SANITIZE_REMOVE_TAGS) {
        char *stripped = sanitize_remove_html_tags(str);
        if (stripped) {
            free(str);
            str = stripped;
        }
    }
    
    if (flags & SANITIZE_REMOVE_CONTROL) {
        sanitize_remove_control_chars(str);
    }
    
    if (flags & SANITIZE_NORMALIZE_WS) {
        sanitize_normalize_whitespace(str);
    }
    
    if (flags & SANITIZE_LOWERCASE) {
        char *p = str;
        while (*p) {
            *p = (char)tolower((unsigned char)*p);
            p++;
        }
    }
    
    if (flags & SANITIZE_TRIM) {
        /* Trim in place */
        char *start = str;
        while (*start && isspace((unsigned char)*start)) start++;
        
        if (start != str) {
            memmove(str, start, strlen(start) + 1);
        }
        
        char *end = str + strlen(str) - 1;
        while (end > str && isspace((unsigned char)*end)) {
            *end-- = '\0';
        }
    }
    
    return str;
}

/* Detection helpers */

bool is_base64_encoded(const char *str)
{
    if (!str) return false;
    return base64_is_valid(str) && strlen(str) % 4 == 0 && strlen(str) >= 4;
}

bool is_url_encoded(const char *str)
{
    if (!str) return false;
    return strchr(str, '%') != NULL;
}

bool contains_control_chars(const char *str)
{
    if (!str) return false;
    
    while (*str) {
        unsigned char c = (unsigned char)*str;
        if (c < 32 && c != '\n' && c != '\r' && c != '\t') {
            return true;
        }
        str++;
    }
    
    return false;
}

bool contains_unicode_control(const char *str)
{
    if (!str) return false;
    
    /* Check for known Unicode control sequences */
    if (strstr(str, "\xE2\x80\xAE") != NULL) return true;  /* RTL override */
    if (strstr(str, "\xE2\x80\x8B") != NULL) return true;  /* Zero-width space */
    if (strstr(str, "\xE2\x80\xA8") != NULL) return true;  /* Line separator */
    if (strstr(str, "\xE2\x80\xA9") != NULL) return true;  /* Paragraph separator */
    
    return false;
}

/* Recursive decode */
char *sanitize_recursive_decode(const char *str, int max_iterations)
{
    if (!str || max_iterations <= 0) return strdup(str);
    
    char *current = strdup(str);
    if (!current) return NULL;
    
    for (int i = 0; i < max_iterations; i++) {
        bool changed = false;
        
        /* Try base64 decode */
        if (is_base64_encoded(current)) {
            size_t out_len;
            uint8_t *decoded = base64_decode(current, &out_len);
            if (decoded) {
                free(current);
                current = (char *)decoded;
                changed = true;
            }
        }
        
        /* Try URL decode */
        if (is_url_encoded(current)) {
            char *decoded = sanitize_url_decode(current);
            if (decoded && strcmp(decoded, current) != 0) {
                free(current);
                current = decoded;
                changed = true;
            } else {
                free(decoded);
            }
        }
        
        if (!changed) break;
    }
    
    return current;
}
