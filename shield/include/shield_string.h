/*
 * SENTINEL Shield - String Utilities
 */

#ifndef SHIELD_STRING_H
#define SHIELD_STRING_H

#include "shield_common.h"

/* Safe string copy */
size_t str_copy(char *dst, const char *src, size_t dst_size);

/* Safe string concatenate */
size_t str_concat(char *dst, const char *src, size_t dst_size);

/* Duplicate string */
char *str_dup(const char *s);

/* Duplicate with max length */
char *str_ndup(const char *s, size_t n);

/* Convert to lowercase (in place) */
void str_lower(char *s);

/* Convert to uppercase (in place) */
void str_upper(char *s);

/* Trim whitespace (in place) */
char *str_trim(char *s);

/* Trim left */
char *str_ltrim(char *s);

/* Trim right */
char *str_rtrim(char *s);

/* Check if starts with */
bool str_starts_with(const char *s, const char *prefix);

/* Check if ends with */
bool str_ends_with(const char *s, const char *suffix);

/* Find substring (case insensitive) */
const char *str_find_i(const char *haystack, const char *needle);

/* Replace all occurrences */
char *str_replace(const char *s, const char *old, const char *new);

/* Split string */
int str_split(const char *s, char delimiter, char **parts, int max_parts);

/* Join strings */
char *str_join(char **parts, int count, const char *delimiter);

/* Format (like snprintf) */
char *str_format(const char *fmt, ...);

/* Check if empty or null */
bool str_empty(const char *s);

/* Compare (null-safe) */
int str_cmp(const char *a, const char *b);

/* Compare case-insensitive */
int str_cmp_i(const char *a, const char *b);

/* Hash string */
uint32_t str_hash(const char *s);

/* Count occurrences */
int str_count(const char *s, const char *substr);

/* Levenshtein distance */
int str_distance(const char *a, const char *b);

#endif /* SHIELD_STRING_H */
