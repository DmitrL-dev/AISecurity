/*
 * SENTINEL Shield - String Utilities Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <ctype.h>

#include "shield_string.h"

/* Safe string copy */
size_t str_copy(char *dst, const char *src, size_t dst_size)
{
    if (!dst || !src || dst_size == 0) return 0;
    
    size_t src_len = strlen(src);
    size_t copy_len = src_len < dst_size - 1 ? src_len : dst_size - 1;
    
    memcpy(dst, src, copy_len);
    dst[copy_len] = '\0';
    
    return copy_len;
}

/* Safe string concatenate */
size_t str_concat(char *dst, const char *src, size_t dst_size)
{
    if (!dst || !src || dst_size == 0) return 0;
    
    size_t dst_len = strlen(dst);
    if (dst_len >= dst_size - 1) return dst_len;
    
    return dst_len + str_copy(dst + dst_len, src, dst_size - dst_len);
}

/* Duplicate string */
char *str_dup(const char *s)
{
    if (!s) return NULL;
    return strdup(s);
}

/* Duplicate with max length */
char *str_ndup(const char *s, size_t n)
{
    if (!s) return NULL;
    
    size_t len = strlen(s);
    if (len > n) len = n;
    
    char *dup = malloc(len + 1);
    if (!dup) return NULL;
    
    memcpy(dup, s, len);
    dup[len] = '\0';
    
    return dup;
}

/* Convert to lowercase */
void str_lower(char *s)
{
    if (!s) return;
    while (*s) {
        *s = (char)tolower((unsigned char)*s);
        s++;
    }
}

/* Convert to uppercase */
void str_upper(char *s)
{
    if (!s) return;
    while (*s) {
        *s = (char)toupper((unsigned char)*s);
        s++;
    }
}

/* Trim left */
char *str_ltrim(char *s)
{
    if (!s) return NULL;
    while (*s && isspace((unsigned char)*s)) s++;
    return s;
}

/* Trim right */
char *str_rtrim(char *s)
{
    if (!s || *s == '\0') return s;
    
    char *end = s + strlen(s) - 1;
    while (end >= s && isspace((unsigned char)*end)) end--;
    end[1] = '\0';
    
    return s;
}

/* Trim both */
char *str_trim(char *s)
{
    return str_rtrim(str_ltrim(s));
}

/* Check if starts with */
bool str_starts_with(const char *s, const char *prefix)
{
    if (!s || !prefix) return false;
    return strncmp(s, prefix, strlen(prefix)) == 0;
}

/* Check if ends with */
bool str_ends_with(const char *s, const char *suffix)
{
    if (!s || !suffix) return false;
    
    size_t s_len = strlen(s);
    size_t suffix_len = strlen(suffix);
    
    if (suffix_len > s_len) return false;
    
    return strcmp(s + s_len - suffix_len, suffix) == 0;
}

/* Find substring (case insensitive) */
const char *str_find_i(const char *haystack, const char *needle)
{
    if (!haystack || !needle) return NULL;
    
    size_t needle_len = strlen(needle);
    if (needle_len == 0) return haystack;
    
    size_t haystack_len = strlen(haystack);
    if (needle_len > haystack_len) return NULL;
    
    for (size_t i = 0; i <= haystack_len - needle_len; i++) {
        bool match = true;
        for (size_t j = 0; j < needle_len; j++) {
            if (tolower((unsigned char)haystack[i + j]) != 
                tolower((unsigned char)needle[j])) {
                match = false;
                break;
            }
        }
        if (match) return haystack + i;
    }
    
    return NULL;
}

/* Replace all occurrences */
char *str_replace(const char *s, const char *old, const char *new_str)
{
    if (!s || !old || !new_str) return NULL;
    
    size_t old_len = strlen(old);
    if (old_len == 0) return str_dup(s);
    
    size_t new_len = strlen(new_str);
    
    /* Count occurrences */
    int count = 0;
    const char *p = s;
    while ((p = strstr(p, old)) != NULL) {
        count++;
        p += old_len;
    }
    
    if (count == 0) return str_dup(s);
    
    /* Allocate result */
    size_t result_len = strlen(s) + count * (new_len - old_len);
    char *result = malloc(result_len + 1);
    if (!result) return NULL;
    
    /* Build result */
    char *dst = result;
    p = s;
    while (*p) {
        if (strncmp(p, old, old_len) == 0) {
            memcpy(dst, new_str, new_len);
            dst += new_len;
            p += old_len;
        } else {
            *dst++ = *p++;
        }
    }
    *dst = '\0';
    
    return result;
}

/* Check if empty */
bool str_empty(const char *s)
{
    return s == NULL || *s == '\0';
}

/* Compare (null-safe) */
int str_cmp(const char *a, const char *b)
{
    if (a == b) return 0;
    if (!a) return -1;
    if (!b) return 1;
    return strcmp(a, b);
}

/* Compare case-insensitive */
int str_cmp_i(const char *a, const char *b)
{
    if (a == b) return 0;
    if (!a) return -1;
    if (!b) return 1;
    
    while (*a && *b) {
        int diff = tolower((unsigned char)*a) - tolower((unsigned char)*b);
        if (diff != 0) return diff;
        a++;
        b++;
    }
    
    return tolower((unsigned char)*a) - tolower((unsigned char)*b);
}

/* Hash string (FNV-1a) */
uint32_t str_hash(const char *s)
{
    if (!s) return 0;
    
    uint32_t hash = 2166136261u;
    while (*s) {
        hash ^= (uint8_t)*s++;
        hash *= 16777619u;
    }
    return hash;
}

/* Count occurrences */
int str_count(const char *s, const char *substr)
{
    if (!s || !substr) return 0;
    
    size_t substr_len = strlen(substr);
    if (substr_len == 0) return 0;
    
    int count = 0;
    const char *p = s;
    while ((p = strstr(p, substr)) != NULL) {
        count++;
        p += substr_len;
    }
    
    return count;
}

/* Levenshtein distance */
int str_distance(const char *a, const char *b)
{
    if (!a || !b) return -1;
    
    size_t len_a = strlen(a);
    size_t len_b = strlen(b);
    
    if (len_a == 0) return (int)len_b;
    if (len_b == 0) return (int)len_a;
    
    /* Simplified: only two rows needed */
    int *prev = calloc(len_b + 1, sizeof(int));
    int *curr = calloc(len_b + 1, sizeof(int));
    if (!prev || !curr) {
        free(prev);
        free(curr);
        return -1;
    }
    
    for (size_t j = 0; j <= len_b; j++) {
        prev[j] = (int)j;
    }
    
    for (size_t i = 1; i <= len_a; i++) {
        curr[0] = (int)i;
        
        for (size_t j = 1; j <= len_b; j++) {
            int cost = (a[i-1] == b[j-1]) ? 0 : 1;
            
            int insert = curr[j-1] + 1;
            int del = prev[j] + 1;
            int sub = prev[j-1] + cost;
            
            curr[j] = insert < del ? insert : del;
            if (sub < curr[j]) curr[j] = sub;
        }
        
        int *tmp = prev;
        prev = curr;
        curr = tmp;
    }
    
    int result = prev[len_b];
    free(prev);
    free(curr);
    
    return result;
}

/* Format string */
char *str_format(const char *fmt, ...)
{
    if (!fmt) return NULL;
    
    va_list args;
    va_start(args, fmt);
    
    int len = vsnprintf(NULL, 0, fmt, args);
    va_end(args);
    
    if (len < 0) return NULL;
    
    char *result = malloc(len + 1);
    if (!result) return NULL;
    
    va_start(args, fmt);
    vsnprintf(result, len + 1, fmt, args);
    va_end(args);
    
    return result;
}
