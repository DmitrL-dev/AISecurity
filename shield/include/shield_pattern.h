/*
 * SENTINEL Shield - Pattern Compiler
 * 
 * Compile and optimize matching patterns
 */

#ifndef SHIELD_PATTERN_H
#define SHIELD_PATTERN_H

#include "shield_common.h"

#ifndef SHIELD_PLATFORM_WINDOWS
#include <regex.h>
#endif

/* Pattern types */
typedef enum pattern_type {
    PATTERN_EXACT,
    PATTERN_CONTAINS,
    PATTERN_PREFIX,
    PATTERN_SUFFIX,
    PATTERN_REGEX,
    PATTERN_GLOB,
} pattern_type_t;

/* Compiled pattern */
typedef struct compiled_pattern {
    char            original[256];
    pattern_type_t  type;
    bool            case_insensitive;
    
#ifndef SHIELD_PLATFORM_WINDOWS
    regex_t         regex;
    bool            regex_compiled;
#endif
    
    /* For simple patterns */
    char            *normalized;
    size_t          normalized_len;
    
    /* Stats */
    uint64_t        match_count;
    uint64_t        eval_count;
    uint64_t        total_time_ns;
} compiled_pattern_t;

/* Pattern cache */
typedef struct pattern_cache {
    compiled_pattern_t  **patterns;
    int                 count;
    int                 capacity;
    
    /* LRU tracking */
    uint64_t            *last_used;
    int                 max_size;
} pattern_cache_t;

/* Compile pattern */
shield_err_t pattern_compile(const char *pattern, pattern_type_t type,
                              bool case_insensitive, compiled_pattern_t **out);
void pattern_free(compiled_pattern_t *pattern);

/* Match */
bool pattern_match(compiled_pattern_t *pattern, const char *text, size_t len);

/* Cache */
shield_err_t pattern_cache_init(pattern_cache_t *cache, int max_size);
void pattern_cache_destroy(pattern_cache_t *cache);

compiled_pattern_t *pattern_cache_get(pattern_cache_t *cache, const char *pattern,
                                       pattern_type_t type, bool case_insensitive);
void pattern_cache_clear(pattern_cache_t *cache);

/* Helpers */
pattern_type_t pattern_detect_type(const char *pattern);
const char *pattern_type_name(pattern_type_t type);

#endif /* SHIELD_PATTERN_H */
