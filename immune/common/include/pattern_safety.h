/*
 * SENTINEL IMMUNE — Pattern Safety Module
 * 
 * Protects Kmod from ReDoS attacks by validating patterns
 * before loading. Rejects dangerous constructs and enforces
 * complexity thresholds.
 * 
 * Based on RE2 design principles (linear time guarantee).
 */

#ifndef IMMUNE_PATTERN_SAFETY_H
#define IMMUNE_PATTERN_SAFETY_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

/* Maximum pattern length */
#define PATTERN_MAX_LENGTH      1024

/* Default complexity threshold */
#define PATTERN_COMPLEXITY_MAX  50

/* Default kernel matching timeout (ms) */
#define PATTERN_TIMEOUT_MS      10

/* Pattern safety levels */
typedef enum {
    PATTERN_SAFE,       /* Can be loaded into Kmod */
    PATTERN_COMPLEX,    /* Safe but needs review (complexity > 30) */
    PATTERN_DANGEROUS,  /* REJECT - ReDoS risk */
    PATTERN_INVALID     /* Syntax error */
} pattern_safety_t;

/* Dangerous construct types */
typedef enum {
    DANGER_NONE             = 0,
    DANGER_NESTED_QUANTIFIER = 1,   /* (a+)+ */
    DANGER_ALTERNATION_EXP  = 2,    /* (a|a)+ */
    DANGER_OVERLAPPING      = 3,    /* \d+\d+ */
    DANGER_SUPER_LINEAR     = 4,    /* (.+)+ */
    DANGER_BACKREF          = 5,    /* (a)\1 */
    DANGER_LOOKAHEAD        = 6,    /* (?=...) */
    DANGER_TOO_LONG         = 7,    /* Exceeds max length */
    DANGER_TOO_COMPLEX      = 8     /* Exceeds complexity threshold */
} danger_type_t;

/* Validation result */
typedef struct {
    pattern_safety_t safety;        /* Safety level */
    int              complexity;    /* Complexity score */
    danger_type_t    danger;        /* Type of danger if DANGEROUS */
    const char      *reason;        /* Human-readable reason */
    int              position;      /* Error position (if INVALID) */
} pattern_result_t;

/* Validator configuration */
typedef struct {
    int  max_complexity;        /* Complexity threshold (default: 50) */
    int  max_length;            /* Max pattern length (default: 1024) */
    bool allow_backrefs;        /* Allow backreferences (default: false) */
    bool allow_lookahead;       /* Allow lookahead/behind (default: false) */
    int  timeout_ms;            /* Kernel timeout in ms (default: 10) */
    int  review_threshold;      /* Mark COMPLEX if above (default: 30) */
} pattern_config_t;

/* Compiled pattern (opaque) */
typedef struct pattern_compiled pattern_compiled_t;

/* === Configuration === */

/**
 * Initialize configuration with defaults.
 * @param config Configuration to initialize
 */
void pattern_config_init(pattern_config_t *config);

/* === Validation === */

/**
 * Validate a pattern for safety.
 * @param pattern Regex pattern string
 * @param config  Validation configuration (NULL for defaults)
 * @param result  Output validation result
 * @return true if pattern is SAFE or COMPLEX, false if DANGEROUS/INVALID
 */
bool pattern_validate(const char *pattern, 
                      const pattern_config_t *config,
                      pattern_result_t *result);

/**
 * Quick check if pattern is safe (uses defaults).
 * @param pattern Regex pattern string
 * @return true if safe to load
 */
bool pattern_is_safe(const char *pattern);

/**
 * Calculate complexity score for a pattern.
 * @param pattern Regex pattern string
 * @return Complexity score (higher = more complex)
 */
int pattern_complexity(const char *pattern);

/**
 * Get human-readable description of danger type.
 * @param danger Danger type
 * @return Description string
 */
const char* pattern_danger_string(danger_type_t danger);

/* === Compilation === */

/**
 * Compile pattern for matching (validates first).
 * @param pattern Regex pattern string
 * @param config  Configuration
 * @param compiled Output compiled pattern
 * @return true on success, false if validation fails
 */
bool pattern_compile(const char *pattern,
                     const pattern_config_t *config,
                     pattern_compiled_t **compiled);

/**
 * Free compiled pattern.
 * @param compiled Pattern to free
 */
void pattern_free(pattern_compiled_t *compiled);

/* === Matching === */

/**
 * Match input against compiled pattern with timeout.
 * Kernel-safe: will return after timeout even on complex patterns.
 * @param compiled Compiled pattern
 * @param input    Input string to match
 * @param len      Length of input
 * @param timeout_ms Timeout in milliseconds
 * @return 1 if match, 0 if no match, -1 if timeout/error
 */
int pattern_match_timeout(const pattern_compiled_t *compiled,
                          const char *input,
                          size_t len,
                          int timeout_ms);

/**
 * Match input against pattern string (validates, compiles, matches).
 * Convenience function for one-off matching.
 * @param pattern Regex pattern string
 * @param input   Input string
 * @return 1 if match, 0 if no match, -1 if pattern invalid/timeout
 */
int pattern_match(const char *pattern, const char *input);

/* === Whitelisting === */

/**
 * Add pattern to whitelist (bypasses validation).
 * Use for known-safe patterns from trusted sources.
 * @param pattern Pattern to whitelist
 * @return true on success
 */
bool pattern_whitelist_add(const char *pattern);

/**
 * Check if pattern is whitelisted.
 * @param pattern Pattern to check
 * @return true if whitelisted
 */
bool pattern_whitelist_check(const char *pattern);

/**
 * Clear all whitelisted patterns.
 */
void pattern_whitelist_clear(void);

#endif /* IMMUNE_PATTERN_SAFETY_H */
