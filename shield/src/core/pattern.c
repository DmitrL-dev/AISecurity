/*
 * SENTINEL Shield - Pattern Compiler Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <time.h>

#include "shield_common.h"
#include "shield_pattern.h"

/* Convert to lowercase */
static char *str_to_lower(const char *str, size_t len)
{
    char *lower = malloc(len + 1);
    if (!lower) return NULL;
    
    for (size_t i = 0; i < len; i++) {
        lower[i] = (char)tolower((unsigned char)str[i]);
    }
    lower[len] = '\0';
    
    return lower;
}

/* Compile pattern */
shield_err_t pattern_compile(const char *pattern, pattern_type_t type,
                              bool case_insensitive, compiled_pattern_t **out)
{
    if (!pattern || !out) {
        return SHIELD_ERR_INVALID;
    }
    
    compiled_pattern_t *cp = calloc(1, sizeof(compiled_pattern_t));
    if (!cp) {
        return SHIELD_ERR_NOMEM;
    }
    
    strncpy(cp->original, pattern, sizeof(cp->original) - 1);
    cp->type = type;
    cp->case_insensitive = case_insensitive;
    
    size_t len = strlen(pattern);
    
    /* Normalize for simple patterns */
    if (type != PATTERN_REGEX) {
        if (case_insensitive) {
            cp->normalized = str_to_lower(pattern, len);
        } else {
            cp->normalized = strdup(pattern);
        }
        cp->normalized_len = len;
    }
    
#ifndef SHIELD_PLATFORM_WINDOWS
    /* Compile regex */
    if (type == PATTERN_REGEX) {
        int flags = REG_EXTENDED | REG_NOSUB;
        if (case_insensitive) {
            flags |= REG_ICASE;
        }
        
        int ret = regcomp(&cp->regex, pattern, flags);
        if (ret != 0) {
            free(cp);
            return SHIELD_ERR_PARSE;
        }
        cp->regex_compiled = true;
    }
#endif
    
    *out = cp;
    return SHIELD_OK;
}

/* Free pattern */
void pattern_free(compiled_pattern_t *pattern)
{
    if (!pattern) return;
    
#ifndef SHIELD_PLATFORM_WINDOWS
    if (pattern->regex_compiled) {
        regfree(&pattern->regex);
    }
#endif
    
    free(pattern->normalized);
    free(pattern);
}

/* Match pattern */
bool pattern_match(compiled_pattern_t *pattern, const char *text, size_t len)
{
    if (!pattern || !text) return false;
    
    pattern->eval_count++;
    
    /* Prepare text for case-insensitive matching */
    char *search_text = NULL;
    if (pattern->case_insensitive && pattern->type != PATTERN_REGEX) {
        search_text = str_to_lower(text, len);
        if (!search_text) return false;
        text = search_text;
    }
    
    bool matched = false;
    
    switch (pattern->type) {
    case PATTERN_EXACT:
        matched = (len == pattern->normalized_len &&
                   memcmp(text, pattern->normalized, len) == 0);
        break;
    
    case PATTERN_CONTAINS:
        if (pattern->normalized_len <= len) {
            matched = (strstr(text, pattern->normalized) != NULL);
        }
        break;
    
    case PATTERN_PREFIX:
        if (pattern->normalized_len <= len) {
            matched = (strncmp(text, pattern->normalized, pattern->normalized_len) == 0);
        }
        break;
    
    case PATTERN_SUFFIX:
        if (pattern->normalized_len <= len) {
            size_t offset = len - pattern->normalized_len;
            matched = (strcmp(text + offset, pattern->normalized) == 0);
        }
        break;
    
    case PATTERN_REGEX:
#ifndef SHIELD_PLATFORM_WINDOWS
        if (pattern->regex_compiled) {
            matched = (regexec(&pattern->regex, text, 0, NULL, 0) == 0);
        }
#else
        /* Simple fallback for Windows - contains check */
        matched = (strstr(text, pattern->original) != NULL);
#endif
        break;
    
    case PATTERN_GLOB:
        /* Simple glob: * matches anything */
        /* TODO: implement proper glob matching */
        matched = (strstr(text, pattern->normalized) != NULL);
        break;
    }
    
    free(search_text);
    
    if (matched) {
        pattern->match_count++;
    }
    
    return matched;
}

/* Initialize cache */
shield_err_t pattern_cache_init(pattern_cache_t *cache, int max_size)
{
    if (!cache || max_size <= 0) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(cache, 0, sizeof(*cache));
    cache->max_size = max_size;
    cache->capacity = max_size;
    
    cache->patterns = calloc(max_size, sizeof(compiled_pattern_t *));
    cache->last_used = calloc(max_size, sizeof(uint64_t));
    
    if (!cache->patterns || !cache->last_used) {
        free(cache->patterns);
        free(cache->last_used);
        return SHIELD_ERR_NOMEM;
    }
    
    return SHIELD_OK;
}

/* Destroy cache */
void pattern_cache_destroy(pattern_cache_t *cache)
{
    if (!cache) return;
    
    for (int i = 0; i < cache->count; i++) {
        pattern_free(cache->patterns[i]);
    }
    
    free(cache->patterns);
    free(cache->last_used);
    cache->patterns = NULL;
    cache->count = 0;
}

/* Get or create cached pattern */
compiled_pattern_t *pattern_cache_get(pattern_cache_t *cache, const char *pattern,
                                       pattern_type_t type, bool case_insensitive)
{
    if (!cache || !pattern) return NULL;
    
    uint64_t now = (uint64_t)time(NULL);
    
    /* Search existing */
    for (int i = 0; i < cache->count; i++) {
        compiled_pattern_t *cp = cache->patterns[i];
        if (cp && cp->type == type && cp->case_insensitive == case_insensitive &&
            strcmp(cp->original, pattern) == 0) {
            cache->last_used[i] = now;
            return cp;
        }
    }
    
    /* Compile new */
    compiled_pattern_t *cp = NULL;
    if (pattern_compile(pattern, type, case_insensitive, &cp) != SHIELD_OK) {
        return NULL;
    }
    
    /* Add to cache */
    if (cache->count < cache->capacity) {
        cache->patterns[cache->count] = cp;
        cache->last_used[cache->count] = now;
        cache->count++;
    } else {
        /* Evict LRU */
        int lru_idx = 0;
        uint64_t lru_time = cache->last_used[0];
        for (int i = 1; i < cache->count; i++) {
            if (cache->last_used[i] < lru_time) {
                lru_time = cache->last_used[i];
                lru_idx = i;
            }
        }
        
        pattern_free(cache->patterns[lru_idx]);
        cache->patterns[lru_idx] = cp;
        cache->last_used[lru_idx] = now;
    }
    
    return cp;
}

/* Clear cache */
void pattern_cache_clear(pattern_cache_t *cache)
{
    if (!cache) return;
    
    for (int i = 0; i < cache->count; i++) {
        pattern_free(cache->patterns[i]);
        cache->patterns[i] = NULL;
    }
    cache->count = 0;
}

/* Detect pattern type from string */
pattern_type_t pattern_detect_type(const char *pattern)
{
    if (!pattern) return PATTERN_CONTAINS;
    
    size_t len = strlen(pattern);
    if (len == 0) return PATTERN_CONTAINS;
    
    /* Check for regex special chars */
    bool has_regex = false;
    for (size_t i = 0; i < len; i++) {
        char c = pattern[i];
        if (c == '[' || c == ']' || c == '(' || c == ')' ||
            c == '{' || c == '}' || c == '|' || c == '^' ||
            c == '$' || c == '\\' || c == '+' || c == '?') {
            has_regex = true;
            break;
        }
    }
    
    if (has_regex) return PATTERN_REGEX;
    
    /* Check for glob wildcards */
    if (strchr(pattern, '*') != NULL) {
        if (pattern[0] == '*' && pattern[len-1] != '*') {
            return PATTERN_SUFFIX;
        }
        if (pattern[len-1] == '*' && pattern[0] != '*') {
            return PATTERN_PREFIX;
        }
        return PATTERN_GLOB;
    }
    
    return PATTERN_CONTAINS;
}

/* Type name */
const char *pattern_type_name(pattern_type_t type)
{
    switch (type) {
    case PATTERN_EXACT: return "exact";
    case PATTERN_CONTAINS: return "contains";
    case PATTERN_PREFIX: return "prefix";
    case PATTERN_SUFFIX: return "suffix";
    case PATTERN_REGEX: return "regex";
    case PATTERN_GLOB: return "glob";
    default: return "unknown";
    }
}
