/*
 * SENTINEL IMMUNE — Pattern Matching Implementation
 * 
 * Fast pattern matching using Boyer-Moore-Horspool.
 * Falls back to SIMD when available.
 */

#include <string.h>
#include <ctype.h>

#include "../include/patterns.h"
#include "../include/immune.h"

/* External SIMD functions */
extern int immune_simd_available(void);
extern long immune_simd_scan(const char *hay, size_t hay_len,
                             const char *needle, size_t needle_len);

/* Skip table for BMH algorithm */
static uint8_t skip_tables[INNATE_PATTERN_COUNT][256];
static int tables_initialized = 0;

/*
 * Build BMH skip table for a pattern
 */
static void
build_skip_table(const char *pattern, size_t len, uint8_t *table)
{
    /* Default: skip full pattern length */
    for (int i = 0; i < 256; i++) {
        table[i] = len;
    }
    
    /* For each char in pattern (except last), set skip distance */
    for (size_t i = 0; i < len - 1; i++) {
        unsigned char c = tolower((unsigned char)pattern[i]);
        table[c] = len - 1 - i;
        /* Also uppercase */
        table[toupper(c)] = len - 1 - i;
    }
}

/*
 * Initialize pattern tables
 */
int
immune_patterns_init(void)
{
    if (tables_initialized)
        return 0;
    
    for (int i = 0; INNATE_PATTERNS[i].pattern != NULL; i++) {
        build_skip_table(
            INNATE_PATTERNS[i].pattern,
            INNATE_PATTERNS[i].length,
            skip_tables[i]
        );
    }
    
    tables_initialized = 1;
    return 0;
}

/*
 * Get patterns array
 */
const immune_pattern_t*
immune_patterns_get(void)
{
    return INNATE_PATTERNS;
}

/*
 * Get pattern count
 */
int
immune_patterns_count(void)
{
    return INNATE_PATTERN_COUNT;
}

/*
 * Case-insensitive compare
 */
static int
memcmp_nocase(const char *a, const char *b, size_t len)
{
    for (size_t i = 0; i < len; i++) {
        char ca = tolower((unsigned char)a[i]);
        char cb = tolower((unsigned char)b[i]);
        if (ca != cb)
            return 1;
    }
    return 0;
}

/*
 * Boyer-Moore-Horspool search (case-insensitive)
 */
static long
bmh_search(const char *haystack, size_t hay_len,
           const char *needle, size_t needle_len,
           const uint8_t *skip_table)
{
    if (needle_len > hay_len)
        return -1;
    
    size_t pos = 0;
    size_t max_pos = hay_len - needle_len;
    
    while (pos <= max_pos) {
        /* Compare from end */
        size_t j = needle_len - 1;
        
        while (tolower((unsigned char)haystack[pos + j]) == 
               tolower((unsigned char)needle[j])) {
            if (j == 0)
                return pos;  /* Match found */
            j--;
        }
        
        /* Skip based on last character */
        unsigned char c = (unsigned char)haystack[pos + needle_len - 1];
        pos += skip_table[c];
    }
    
    return -1;
}

/*
 * Match all patterns against content
 * 
 * Returns: number of matches found
 * Sets: highest severity and type found
 */
int
immune_patterns_match(const char *content, size_t len,
                      uint8_t *out_severity, uint8_t *out_type)
{
    if (!tables_initialized)
        immune_patterns_init();
    
    int use_simd = immune_simd_available();
    int matches = 0;
    uint8_t max_severity = 0;
    uint8_t max_type = 0;
    
    for (int i = 0; INNATE_PATTERNS[i].pattern != NULL; i++) {
        const immune_pattern_t *pat = &INNATE_PATTERNS[i];
        long pos;
        
        if (use_simd) {
            pos = immune_simd_scan(content, len, 
                                   pat->pattern, pat->length);
        } else {
            pos = bmh_search(content, len,
                            pat->pattern, pat->length,
                            skip_tables[i]);
        }
        
        if (pos >= 0) {
            matches++;
            if (pat->severity > max_severity) {
                max_severity = pat->severity;
                max_type = pat->type;
            }
        }
    }
    
    if (out_severity)
        *out_severity = max_severity;
    if (out_type)
        *out_type = max_type;
    
    return matches;
}

/*
 * Quick scan wrapper (used by innate.asm)
 */
threat_level_t
immune_innate_scan(const char *content, size_t len)
{
    uint8_t severity = 0;
    uint8_t type = 0;
    
    int matches = immune_patterns_match(content, len, &severity, &type);
    
    if (matches == 0)
        return THREAT_NONE;
    
    /* Map severity to threat level */
    switch (severity) {
        case 1: return THREAT_LOW;
        case 2: return THREAT_MEDIUM;
        case 3: return THREAT_HIGH;
        case 4: return THREAT_CRITICAL;
        default: return THREAT_NONE;
    }
}
