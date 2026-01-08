/*
 * SENTINEL IMMUNE — Pattern Validator Implementation
 * 
 * Validates regex patterns for ReDoS safety.
 * Uses complexity scoring and dangerous construct detection.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <stdbool.h>
#include <regex.h>
#include <signal.h>
#include <setjmp.h>
#include <time.h>

#include "pattern_safety.h"

/* ==================== Constants ==================== */

/* Complexity weights */
#define WEIGHT_CHAR         1
#define WEIGHT_CHAR_CLASS   2
#define WEIGHT_QUANTIFIER   5
#define WEIGHT_ALTERNATION  10
#define WEIGHT_GROUP        15
#define WEIGHT_NESTED_QUANT 100  /* Auto-reject */

/* Whitelist size */
#define WHITELIST_SIZE      256

/* ==================== Internal State ==================== */

/* Whitelist storage */
static char *whitelist[WHITELIST_SIZE];
static int whitelist_count = 0;

/* Timeout handling */
static jmp_buf timeout_jmp;
static volatile sig_atomic_t timeout_flag = 0;

/* Danger type descriptions */
static const char* danger_strings[] = {
    [DANGER_NONE]             = "No danger",
    [DANGER_NESTED_QUANTIFIER] = "Nested quantifier (e.g., (a+)+)",
    [DANGER_ALTERNATION_EXP]  = "Alternation explosion (e.g., (a|a)+)",
    [DANGER_OVERLAPPING]      = "Overlapping quantifiers (e.g., \\d+\\d+)",
    [DANGER_SUPER_LINEAR]     = "Super-linear pattern (e.g., (.+)+)",
    [DANGER_BACKREF]          = "Backreference detected",
    [DANGER_LOOKAHEAD]        = "Lookahead/lookbehind detected",
    [DANGER_TOO_LONG]         = "Pattern exceeds maximum length",
    [DANGER_TOO_COMPLEX]      = "Complexity exceeds threshold"
};

/* ==================== Helper Functions ==================== */

/**
 * Check if character is a quantifier.
 */
static inline bool
is_quantifier(char c)
{
    return c == '*' || c == '+' || c == '?' || c == '{';
}

/**
 * Check for nested quantifier pattern.
 * Detects: (x+)+, (x*)+, etc.
 */
static danger_type_t
check_nested_quantifier(const char *pattern)
{
    int depth = 0;
    bool in_quantified_group = false;
    const char *p = pattern;
    
    while (*p) {
        if (*p == '\\' && *(p+1)) {
            p += 2;  /* Skip escaped char */
            continue;
        }
        
        if (*p == '(') {
            depth++;
        } else if (*p == ')') {
            depth--;
            /* Check for quantifier after group close */
            if (depth == 0 && *(p+1) && is_quantifier(*(p+1))) {
                if (in_quantified_group) {
                    return DANGER_NESTED_QUANTIFIER;
                }
                in_quantified_group = true;
            }
        } else if (depth > 0 && is_quantifier(*p)) {
            /* Quantifier inside group */
            if (in_quantified_group) {
                return DANGER_NESTED_QUANTIFIER;
            }
            in_quantified_group = true;
        }
        p++;
    }
    
    return DANGER_NONE;
}

/**
 * Check for alternation explosion.
 * Detects: (a|a)+, (a|b|a)+, etc.
 */
static danger_type_t
check_alternation_explosion(const char *pattern)
{
    int depth = 0;
    int alt_count = 0;
    const char *p = pattern;
    
    while (*p) {
        if (*p == '\\' && *(p+1)) {
            p += 2;
            continue;
        }
        
        if (*p == '(') {
            depth++;
            alt_count = 0;
        } else if (*p == ')') {
            /* Check for quantified group with many alternatives */
            if (alt_count > 3 && *(p+1) && is_quantifier(*(p+1))) {
                return DANGER_ALTERNATION_EXP;
            }
            depth--;
        } else if (*p == '|' && depth > 0) {
            alt_count++;
        }
        p++;
    }
    
    return DANGER_NONE;
}

/**
 * Check for overlapping quantifiers.
 * Detects: \d+\d+, [a-z]+[a-z]+, etc.
 */
static danger_type_t
check_overlapping(const char *pattern)
{
    const char *p = pattern;
    int quant_end = 0;
    
    while (*p) {
        if (*p == '\\' && *(p+1)) {
            p += 2;
            continue;
        }
        
        if (is_quantifier(*p)) {
            int pos = p - pattern;
            if (pos - quant_end <= 2 && quant_end > 0) {
                return DANGER_OVERLAPPING;
            }
            quant_end = pos;
        }
        p++;
    }
    
    return DANGER_NONE;
}

/**
 * Check for super-linear patterns.
 * Detects: (.+)+, (.*)+, .*.*+, etc.
 */
static danger_type_t
check_super_linear(const char *pattern)
{
    /* Look for .+ or .* followed by quantifier */
    const char *p = strstr(pattern, "(.+)+");
    if (p) return DANGER_SUPER_LINEAR;
    
    p = strstr(pattern, "(.*)+");
    if (p) return DANGER_SUPER_LINEAR;
    
    p = strstr(pattern, "(.*)");
    if (p && *(p+4) && is_quantifier(*(p+4))) {
        return DANGER_SUPER_LINEAR;
    }
    
    return DANGER_NONE;
}

/**
 * Check for backreferences.
 */
static danger_type_t
check_backrefs(const char *pattern, bool allowed)
{
    if (allowed) return DANGER_NONE;
    
    const char *p = pattern;
    while (*p) {
        if (*p == '\\' && *(p+1) >= '1' && *(p+1) <= '9') {
            return DANGER_BACKREF;
        }
        p++;
    }
    
    return DANGER_NONE;
}

/**
 * Check for lookahead/lookbehind.
 */
static danger_type_t
check_lookahead(const char *pattern, bool allowed)
{
    if (allowed) return DANGER_NONE;
    
    if (strstr(pattern, "(?=") || strstr(pattern, "(?!") ||
        strstr(pattern, "(?<=") || strstr(pattern, "(?<!")) {
        return DANGER_LOOKAHEAD;
    }
    
    return DANGER_NONE;
}

/**
 * Calculate complexity score.
 */
static int
calculate_complexity(const char *pattern)
{
    int score = 0;
    int len = strlen(pattern);
    const char *p = pattern;
    
    /* Base score from length */
    score += len / 10;
    
    while (*p) {
        if (*p == '\\' && *(p+1)) {
            score += WEIGHT_CHAR;
            p += 2;
            continue;
        }
        
        switch (*p) {
        case '[':
            score += WEIGHT_CHAR_CLASS;
            /* Skip to closing bracket */
            while (*p && *p != ']') p++;
            break;
        case '*':
        case '+':
        case '?':
            score += WEIGHT_QUANTIFIER;
            break;
        case '{':
            score += WEIGHT_QUANTIFIER;
            /* Parse repetition count */
            while (*p && *p != '}') p++;
            break;
        case '|':
            score += WEIGHT_ALTERNATION;
            break;
        case '(':
            score += WEIGHT_GROUP;
            break;
        default:
            score += WEIGHT_CHAR;
        }
        
        if (*p) p++;
    }
    
    return score;
}

/* ==================== Timeout Handling ==================== */

static void
timeout_handler(int sig)
{
    (void)sig;
    timeout_flag = 1;
    longjmp(timeout_jmp, 1);
}

/* ==================== Public API ==================== */

void
pattern_config_init(pattern_config_t *config)
{
    if (!config) return;
    
    config->max_complexity = PATTERN_COMPLEXITY_MAX;
    config->max_length = PATTERN_MAX_LENGTH;
    config->allow_backrefs = false;
    config->allow_lookahead = false;
    config->timeout_ms = PATTERN_TIMEOUT_MS;
    config->review_threshold = 30;
}

bool
pattern_validate(const char *pattern, 
                 const pattern_config_t *config,
                 pattern_result_t *result)
{
    pattern_config_t default_config;
    
    if (!pattern || !result) {
        return false;
    }
    
    /* Use defaults if no config */
    if (!config) {
        pattern_config_init(&default_config);
        config = &default_config;
    }
    
    /* Initialize result */
    result->safety = PATTERN_SAFE;
    result->complexity = 0;
    result->danger = DANGER_NONE;
    result->reason = NULL;
    result->position = -1;
    
    /* Check whitelist first */
    if (pattern_whitelist_check(pattern)) {
        result->safety = PATTERN_SAFE;
        result->reason = "Whitelisted pattern";
        return true;
    }
    
    /* Check length */
    size_t len = strlen(pattern);
    if ((int)len > config->max_length) {
        result->safety = PATTERN_DANGEROUS;
        result->danger = DANGER_TOO_LONG;
        result->reason = danger_strings[DANGER_TOO_LONG];
        return false;
    }
    
    /* Check syntax with regex compile */
    regex_t re;
    int ret = regcomp(&re, pattern, REG_EXTENDED | REG_NOSUB);
    if (ret != 0) {
        result->safety = PATTERN_INVALID;
        result->reason = "Invalid regex syntax";
        result->position = 0;  /* regcomp doesn't give position */
        return false;
    }
    regfree(&re);
    
    /* Check for dangerous constructs */
    danger_type_t danger;
    
    danger = check_nested_quantifier(pattern);
    if (danger != DANGER_NONE) goto dangerous;
    
    danger = check_super_linear(pattern);
    if (danger != DANGER_NONE) goto dangerous;
    
    danger = check_alternation_explosion(pattern);
    if (danger != DANGER_NONE) goto dangerous;
    
    danger = check_overlapping(pattern);
    if (danger != DANGER_NONE) goto dangerous;
    
    danger = check_backrefs(pattern, config->allow_backrefs);
    if (danger != DANGER_NONE) goto dangerous;
    
    danger = check_lookahead(pattern, config->allow_lookahead);
    if (danger != DANGER_NONE) goto dangerous;
    
    /* Calculate complexity */
    result->complexity = calculate_complexity(pattern);
    
    /* Check complexity threshold */
    if (result->complexity > config->max_complexity) {
        result->safety = PATTERN_DANGEROUS;
        result->danger = DANGER_TOO_COMPLEX;
        result->reason = danger_strings[DANGER_TOO_COMPLEX];
        return false;
    }
    
    /* Mark as COMPLEX if above review threshold */
    if (result->complexity > config->review_threshold) {
        result->safety = PATTERN_COMPLEX;
        result->reason = "High complexity - review recommended";
    } else {
        result->safety = PATTERN_SAFE;
        result->reason = "Pattern is safe";
    }
    
    return true;

dangerous:
    result->safety = PATTERN_DANGEROUS;
    result->danger = danger;
    result->reason = danger_strings[danger];
    return false;
}

bool
pattern_is_safe(const char *pattern)
{
    pattern_result_t result;
    return pattern_validate(pattern, NULL, &result) && 
           result.safety != PATTERN_DANGEROUS;
}

int
pattern_complexity(const char *pattern)
{
    if (!pattern) return 0;
    return calculate_complexity(pattern);
}

const char*
pattern_danger_string(danger_type_t danger)
{
    if (danger < 0 || danger > DANGER_TOO_COMPLEX) {
        return "Unknown danger";
    }
    return danger_strings[danger];
}

/* ==================== Compilation ==================== */

struct pattern_compiled {
    regex_t     regex;
    int         timeout_ms;
    bool        valid;
};

bool
pattern_compile(const char *pattern,
                const pattern_config_t *config,
                pattern_compiled_t **compiled)
{
    pattern_result_t result;
    pattern_config_t default_config;
    
    if (!pattern || !compiled) return false;
    
    if (!config) {
        pattern_config_init(&default_config);
        config = &default_config;
    }
    
    /* Validate first */
    if (!pattern_validate(pattern, config, &result)) {
        fprintf(stderr, "[PATTERN] Rejected: %s - %s\n", pattern, result.reason);
        return false;
    }
    
    /* Allocate compiled pattern */
    pattern_compiled_t *cp = calloc(1, sizeof(pattern_compiled_t));
    if (!cp) return false;
    
    /* Compile regex */
    if (regcomp(&cp->regex, pattern, REG_EXTENDED | REG_NOSUB) != 0) {
        free(cp);
        return false;
    }
    
    cp->timeout_ms = config->timeout_ms;
    cp->valid = true;
    *compiled = cp;
    
    return true;
}

void
pattern_free(pattern_compiled_t *compiled)
{
    if (compiled) {
        if (compiled->valid) {
            regfree(&compiled->regex);
        }
        free(compiled);
    }
}

/* ==================== Matching ==================== */

int
pattern_match_timeout(const pattern_compiled_t *compiled,
                      const char *input,
                      size_t len,
                      int timeout_ms)
{
    if (!compiled || !compiled->valid || !input) {
        return -1;
    }
    
    (void)len;  /* Unused with regexec */
    
    /* Setup timeout handler */
    timeout_flag = 0;
    struct sigaction sa, old_sa;
    sa.sa_handler = timeout_handler;
    sa.sa_flags = 0;
    sigemptyset(&sa.sa_mask);
    sigaction(SIGALRM, &sa, &old_sa);
    
    /* Set timer */
    struct itimerval timer, old_timer;
    timer.it_value.tv_sec = timeout_ms / 1000;
    timer.it_value.tv_usec = (timeout_ms % 1000) * 1000;
    timer.it_interval.tv_sec = 0;
    timer.it_interval.tv_usec = 0;
    setitimer(ITIMER_REAL, &timer, &old_timer);
    
    int result;
    if (setjmp(timeout_jmp) == 0) {
        /* Normal execution */
        result = regexec(&compiled->regex, input, 0, NULL, 0) == 0 ? 1 : 0;
    } else {
        /* Timeout occurred */
        result = -1;
    }
    
    /* Restore timer and handler */
    setitimer(ITIMER_REAL, &old_timer, NULL);
    sigaction(SIGALRM, &old_sa, NULL);
    
    return result;
}

int
pattern_match(const char *pattern, const char *input)
{
    pattern_compiled_t *compiled;
    
    if (!pattern_compile(pattern, NULL, &compiled)) {
        return -1;
    }
    
    int result = pattern_match_timeout(compiled, input, strlen(input),
                                       PATTERN_TIMEOUT_MS);
    pattern_free(compiled);
    
    return result;
}

/* ==================== Whitelisting ==================== */

bool
pattern_whitelist_add(const char *pattern)
{
    if (!pattern || whitelist_count >= WHITELIST_SIZE) {
        return false;
    }
    
    /* Check if already whitelisted */
    if (pattern_whitelist_check(pattern)) {
        return true;
    }
    
    whitelist[whitelist_count] = strdup(pattern);
    if (!whitelist[whitelist_count]) {
        return false;
    }
    
    whitelist_count++;
    return true;
}

bool
pattern_whitelist_check(const char *pattern)
{
    if (!pattern) return false;
    
    for (int i = 0; i < whitelist_count; i++) {
        if (strcmp(whitelist[i], pattern) == 0) {
            return true;
        }
    }
    
    return false;
}

void
pattern_whitelist_clear(void)
{
    for (int i = 0; i < whitelist_count; i++) {
        free(whitelist[i]);
        whitelist[i] = NULL;
    }
    whitelist_count = 0;
}
