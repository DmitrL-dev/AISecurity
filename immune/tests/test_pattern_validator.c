/*
 * SENTINEL IMMUNE — Pattern Validator Unit Tests
 * 
 * Tests for pattern safety validation including ReDoS detection.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>

#include "../common/include/pattern_safety.h"

/* Test counters */
static int tests_run = 0;
static int tests_passed = 0;

#define TEST(name) do { \
    printf("  TEST: %-35s ", #name); \
    tests_run++; \
    if (test_##name()) { \
        printf("PASS\n"); \
        tests_passed++; \
    } else { \
        printf("FAIL\n"); \
    } \
} while(0)

/* ==================== Unit Tests ==================== */

/**
 * Simple safe patterns should pass.
 */
static int
test_simple_safe(void)
{
    return pattern_is_safe("^hello$") &&
           pattern_is_safe("world") &&
           pattern_is_safe("[a-z]+") &&
           pattern_is_safe("\\d{3}");
}

/**
 * Nested quantifiers should be rejected.
 */
static int
test_nested_quantifier(void)
{
    pattern_result_t result;
    
    pattern_validate("(a+)+", NULL, &result);
    if (result.safety != PATTERN_DANGEROUS) return 0;
    if (result.danger != DANGER_NESTED_QUANTIFIER) return 0;
    
    return 1;
}

/**
 * Super-linear patterns should be rejected.
 */
static int
test_super_linear(void)
{
    pattern_result_t result;
    
    pattern_validate("(.+)+", NULL, &result);
    if (result.safety != PATTERN_DANGEROUS) return 0;
    if (result.danger != DANGER_SUPER_LINEAR) return 0;
    
    pattern_validate("(.*)+", NULL, &result);
    if (result.safety != PATTERN_DANGEROUS) return 0;
    
    return 1;
}

/**
 * Backreferences should be rejected by default.
 */
static int
test_backreference(void)
{
    pattern_result_t result;
    
    pattern_validate("(a)\\1", NULL, &result);
    if (result.safety != PATTERN_DANGEROUS) return 0;
    if (result.danger != DANGER_BACKREF) return 0;
    
    /* Allow backrefs with config */
    pattern_config_t config;
    pattern_config_init(&config);
    config.allow_backrefs = true;
    
    pattern_validate("(a)\\1", &config, &result);
    if (result.safety == PATTERN_DANGEROUS && 
        result.danger == DANGER_BACKREF) return 0;
    
    return 1;
}

/**
 * Invalid syntax should be detected.
 */
static int
test_invalid_syntax(void)
{
    pattern_result_t result;
    
    pattern_validate("[a-", NULL, &result);
    if (result.safety != PATTERN_INVALID) return 0;
    
    pattern_validate("(abc", NULL, &result);
    if (result.safety != PATTERN_INVALID) return 0;
    
    return 1;
}

/**
 * Complexity scoring should work.
 */
static int
test_complexity_scoring(void)
{
    int c1 = pattern_complexity("hello");
    int c2 = pattern_complexity("[a-zA-Z]+");
    int c3 = pattern_complexity("(a|b|c|d)+");
    
    /* More complex patterns should score higher */
    if (c1 >= c2) return 0;
    if (c2 >= c3) return 0;
    
    return 1;
}

/**
 * High complexity should be marked COMPLEX.
 */
static int
test_high_complexity(void)
{
    pattern_result_t result;
    pattern_config_t config;
    
    pattern_config_init(&config);
    config.review_threshold = 10;  /* Low threshold for test */
    config.max_complexity = 100;
    
    pattern_validate("([a-z]+|[A-Z]+|[0-9]+)+", &config, &result);
    
    if (result.safety != PATTERN_COMPLEX) return 0;
    if (result.complexity <= config.review_threshold) return 0;
    
    return 1;
}

/**
 * Danger string mapping should work.
 */
static int
test_danger_strings(void)
{
    const char *s;
    
    s = pattern_danger_string(DANGER_NONE);
    if (!s || strlen(s) == 0) return 0;
    
    s = pattern_danger_string(DANGER_NESTED_QUANTIFIER);
    if (!s || strstr(s, "Nested") == NULL) return 0;
    
    return 1;
}

/**
 * Whitelisting should work.
 */
static int
test_whitelist(void)
{
    pattern_whitelist_clear();
    
    /* Add to whitelist */
    if (!pattern_whitelist_add("^test$")) return 0;
    if (!pattern_whitelist_check("^test$")) return 0;
    
    /* Not whitelisted */
    if (pattern_whitelist_check("^other$")) return 0;
    
    /* Whitelisted pattern should always be safe */
    pattern_result_t result;
    pattern_validate("^test$", NULL, &result);
    if (result.safety != PATTERN_SAFE) return 0;
    
    pattern_whitelist_clear();
    return 1;
}

/**
 * Pattern compilation should work.
 */
static int
test_compile(void)
{
    pattern_compiled_t *compiled = NULL;
    
    if (!pattern_compile("^[a-z]+$", NULL, &compiled)) return 0;
    if (!compiled) return 0;
    
    pattern_free(compiled);
    
    /* Dangerous pattern should not compile */
    compiled = NULL;
    if (pattern_compile("(a+)+", NULL, &compiled)) return 0;
    if (compiled) return 0;
    
    return 1;
}

/**
 * Pattern matching should work.
 */
static int
test_match(void)
{
    int result;
    
    result = pattern_match("^hello$", "hello");
    if (result != 1) return 0;
    
    result = pattern_match("^hello$", "world");
    if (result != 0) return 0;
    
    result = pattern_match("[0-9]+", "abc123def");
    if (result != 1) return 0;
    
    return 1;
}

/**
 * Too long patterns should be rejected.
 */
static int
test_too_long(void)
{
    pattern_result_t result;
    pattern_config_t config;
    
    pattern_config_init(&config);
    config.max_length = 10;
    
    pattern_validate("this_is_a_very_long_pattern", &config, &result);
    
    if (result.safety != PATTERN_DANGEROUS) return 0;
    if (result.danger != DANGER_TOO_LONG) return 0;
    
    return 1;
}

/**
 * NULL handling should not crash.
 */
static int
test_null_handling(void)
{
    pattern_result_t result;
    
    if (pattern_validate(NULL, NULL, &result)) return 0;
    if (pattern_is_safe(NULL)) return 0;
    if (pattern_complexity(NULL) != 0) return 0;
    
    pattern_free(NULL);  /* Should not crash */
    
    return 1;
}

/* ==================== ReDoS Attack Patterns ==================== */

/**
 * Known ReDoS patterns must all be rejected.
 */
static int
test_known_redos(void)
{
    const char *redos_patterns[] = {
        "(a+)+$",
        "(a|aa)+$",
        "([a-zA-Z]+)*$",
        "^(a+)+$",
        "(.+)+",
        "(.*)+",
        NULL
    };
    
    for (int i = 0; redos_patterns[i]; i++) {
        if (pattern_is_safe(redos_patterns[i])) {
            printf("\n    Allowed ReDoS: %s ", redos_patterns[i]);
            return 0;
        }
    }
    
    return 1;
}

/* ==================== Main ==================== */

int
main(void)
{
    printf("\n");
    printf("=============================================\n");
    printf("  IMMUNE Pattern Validator — Unit Tests\n");
    printf("=============================================\n\n");
    
    TEST(simple_safe);
    TEST(nested_quantifier);
    TEST(super_linear);
    TEST(backreference);
    TEST(invalid_syntax);
    TEST(complexity_scoring);
    TEST(high_complexity);
    TEST(danger_strings);
    TEST(whitelist);
    TEST(compile);
    TEST(match);
    TEST(too_long);
    TEST(null_handling);
    TEST(known_redos);
    
    printf("\n---------------------------------------------\n");
    printf("  Results: %d/%d tests passed\n", tests_passed, tests_run);
    printf("---------------------------------------------\n\n");
    
    return (tests_passed == tests_run) ? 0 : 1;
}
