/*
 * SENTINEL IMMUNE — Bloom Filter Unit Tests
 * 
 * Tests for bloom filter including FPR measurement.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "../common/include/bloom_filter.h"

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
 * Create and destroy filter.
 */
static int
test_create_destroy(void)
{
    bloom_filter_t *bf = bloom_create(NULL);
    if (!bf) return 0;
    
    bloom_destroy(bf);
    return 1;
}

/**
 * Create with custom config.
 */
static int
test_create_config(void)
{
    bloom_config_t config;
    bloom_config_init(&config);
    
    config.expected_items = 1000;
    config.false_positive_rate = 0.001;  /* 0.1% */
    
    bloom_filter_t *bf = bloom_create(&config);
    if (!bf) return 0;
    
    bloom_stats_t stats;
    bloom_stats(bf, &stats);
    
    /* Should have enough bits for low FPR */
    if (stats.bits_total < 10000) {
        bloom_destroy(bf);
        return 0;
    }
    
    bloom_destroy(bf);
    return 1;
}

/**
 * Add and check items.
 */
static int
test_add_check(void)
{
    bloom_filter_t *bf = bloom_create(NULL);
    if (!bf) return 0;
    
    /* Add items */
    bloom_add_string(bf, "hello");
    bloom_add_string(bf, "world");
    bloom_add_string(bf, "test");
    
    /* Check present */
    if (!bloom_check_string(bf, "hello")) {
        bloom_destroy(bf);
        return 0;
    }
    if (!bloom_check_string(bf, "world")) {
        bloom_destroy(bf);
        return 0;
    }
    if (!bloom_check_string(bf, "test")) {
        bloom_destroy(bf);
        return 0;
    }
    
    bloom_destroy(bf);
    return 1;
}

/**
 * Not-added items should usually not be present.
 */
static int
test_not_present(void)
{
    bloom_filter_t *bf = bloom_create(NULL);
    if (!bf) return 0;
    
    bloom_add_string(bf, "hello");
    
    /* These should NOT be present (with high probability) */
    int false_positives = 0;
    false_positives += bloom_check_string(bf, "goodbye") ? 1 : 0;
    false_positives += bloom_check_string(bf, "xyz123") ? 1 : 0;
    false_positives += bloom_check_string(bf, "qwerty") ? 1 : 0;
    false_positives += bloom_check_string(bf, "foobar") ? 1 : 0;
    false_positives += bloom_check_string(bf, "random") ? 1 : 0;
    
    bloom_destroy(bf);
    
    /* Allow at most 1 false positive (very unlikely with empty filter) */
    return false_positives <= 1;
}

/**
 * MurmurHash3 should produce expected values.
 */
static int
test_murmur3(void)
{
    uint32_t h1 = murmur3_32("hello", 5, 0);
    uint32_t h2 = murmur3_32("hello", 5, 1);
    uint32_t h3 = murmur3_32("world", 5, 0);
    
    /* Different seeds should give different hashes */
    if (h1 == h2) return 0;
    
    /* Different data should give different hashes */
    if (h1 == h3) return 0;
    
    /* Same data/seed should give same hash */
    if (h1 != murmur3_32("hello", 5, 0)) return 0;
    
    return 1;
}

/**
 * Statistics should be correct.
 */
static int
test_stats(void)
{
    bloom_filter_t *bf = bloom_create(NULL);
    if (!bf) return 0;
    
    bloom_stats_t stats;
    bloom_stats(bf, &stats);
    
    if (stats.items_count != 0) {
        bloom_destroy(bf);
        return 0;
    }
    
    bloom_add_string(bf, "test1");
    bloom_add_string(bf, "test2");
    
    bloom_stats(bf, &stats);
    if (stats.items_count != 2) {
        bloom_destroy(bf);
        return 0;
    }
    
    if (stats.bits_set == 0) {
        bloom_destroy(bf);
        return 0;
    }
    
    bloom_destroy(bf);
    return 1;
}

/**
 * Clear should reset filter.
 */
static int
test_clear(void)
{
    bloom_filter_t *bf = bloom_create(NULL);
    if (!bf) return 0;
    
    bloom_add_string(bf, "test");
    
    if (!bloom_check_string(bf, "test")) {
        bloom_destroy(bf);
        return 0;
    }
    
    bloom_clear(bf);
    
    /* After clear, should not be present */
    bloom_stats_t stats;
    bloom_stats(bf, &stats);
    
    if (stats.items_count != 0) {
        bloom_destroy(bf);
        return 0;
    }
    
    bloom_destroy(bf);
    return 1;
}

/**
 * Measure actual false positive rate.
 */
static int
test_fpr_measurement(void)
{
    bloom_config_t config;
    bloom_config_init(&config);
    config.expected_items = 1000;
    config.false_positive_rate = 0.01;  /* 1% */
    
    bloom_filter_t *bf = bloom_create(&config);
    if (!bf) return 0;
    
    /* Add 1000 items */
    char buf[32];
    for (int i = 0; i < 1000; i++) {
        snprintf(buf, sizeof(buf), "item_%d", i);
        bloom_add_string(bf, buf);
    }
    
    /* Check 10000 items not in filter */
    int false_positives = 0;
    for (int i = 1000; i < 11000; i++) {
        snprintf(buf, sizeof(buf), "item_%d", i);
        if (bloom_check_string(bf, buf)) {
            false_positives++;
        }
    }
    
    double actual_fpr = (double)false_positives / 10000.0;
    
    /*
    printf("\n    FPR: %.4f%% (target: 1%%) ", actual_fpr * 100);
    */
    
    bloom_destroy(bf);
    
    /* Allow up to 2% (some variance expected) */
    return actual_fpr < 0.02;
}

/**
 * Save and load filter.
 */
static int
test_save_load(void)
{
    bloom_filter_t *bf = bloom_create(NULL);
    if (!bf) return 0;
    
    bloom_add_string(bf, "hello");
    bloom_add_string(bf, "world");
    
    const char *path = "test_bloom.bin";
    
    if (bloom_save(bf, path) != 0) {
        bloom_destroy(bf);
        return 0;
    }
    
    bloom_destroy(bf);
    
    /* Load */
    bf = bloom_load(path);
    if (!bf) {
        remove(path);
        return 0;
    }
    
    /* Check items still present */
    if (!bloom_check_string(bf, "hello") || 
        !bloom_check_string(bf, "world")) {
        bloom_destroy(bf);
        remove(path);
        return 0;
    }
    
    bloom_destroy(bf);
    remove(path);
    return 1;
}

/**
 * NULL handling should not crash.
 */
static int
test_null_handling(void)
{
    bloom_destroy(NULL);  /* Should not crash */
    bloom_clear(NULL);
    bloom_add(NULL, "test", 4);
    bloom_add_string(NULL, "test");
    
    if (bloom_check(NULL, "test", 4)) return 0;
    if (bloom_check_string(NULL, "test")) return 0;
    
    bloom_stats_t stats;
    bloom_stats(NULL, &stats);
    
    return 1;
}

/**
 * Large dataset test.
 */
static int
test_large_dataset(void)
{
    bloom_config_t config;
    bloom_config_init(&config);
    config.expected_items = 10000;
    config.false_positive_rate = 0.01;
    
    bloom_filter_t *bf = bloom_create(&config);
    if (!bf) return 0;
    
    /* Add 10K items */
    char buf[32];
    for (int i = 0; i < 10000; i++) {
        snprintf(buf, sizeof(buf), "pattern_%d", i);
        bloom_add_string(bf, buf);
    }
    
    /* Verify all present */
    for (int i = 0; i < 10000; i++) {
        snprintf(buf, sizeof(buf), "pattern_%d", i);
        if (!bloom_check_string(bf, buf)) {
            bloom_destroy(bf);
            return 0;
        }
    }
    
    bloom_stats_t stats;
    bloom_stats(bf, &stats);
    
    /* Memory should be reasonable */
    if (stats.memory_bytes > 1024 * 1024) {  /* < 1MB */
        bloom_destroy(bf);
        return 0;
    }
    
    bloom_destroy(bf);
    return 1;
}

/* ==================== Main ==================== */

int
main(void)
{
    printf("\n");
    printf("=============================================\n");
    printf("  IMMUNE Bloom Filter — Unit Tests\n");
    printf("=============================================\n\n");
    
    TEST(create_destroy);
    TEST(create_config);
    TEST(add_check);
    TEST(not_present);
    TEST(murmur3);
    TEST(stats);
    TEST(clear);
    TEST(fpr_measurement);
    TEST(save_load);
    TEST(null_handling);
    TEST(large_dataset);
    
    printf("\n---------------------------------------------\n");
    printf("  Results: %d/%d tests passed\n", tests_passed, tests_run);
    printf("---------------------------------------------\n\n");
    
    return (tests_passed == tests_run) ? 0 : 1;
}
