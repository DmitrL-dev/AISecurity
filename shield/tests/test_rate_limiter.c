/**
 * @file test_rate_limiter.c
 * @brief Unit tests for SENTINEL Shield Rate Limiter Module
 * 
 * @author SENTINEL Team
 * @date 2026-01-09
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <unistd.h>
#include "../src/core/rate_limiter.h"

/* ============================================================================
 * Test Helpers
 * ============================================================================ */

static int tests_run = 0;
static int tests_passed = 0;

#define TEST(name) static void test_##name(void)
#define RUN_TEST(name) do { \
    printf("  Testing %s... ", #name); \
    tests_run++; \
    test_##name(); \
    tests_passed++; \
    printf("PASS\n"); \
} while(0)

/* ============================================================================
 * Tests
 * ============================================================================ */

TEST(init_success) {
    rate_limit_config_t config = {
        .requests_per_minute = 60,
        .burst_size = 10,
        .per_ip = true,
        .per_user = false,
        .cleanup_interval_sec = 300
    };
    
    int err = rate_limiter_init(&config);
    assert(err == RATE_LIMIT_ERR_SUCCESS);
    assert(rate_limiter_is_initialized() == true);
    
    rate_limiter_cleanup();
    assert(rate_limiter_is_initialized() == false);
}

TEST(init_null_config) {
    int err = rate_limiter_init(NULL);
    assert(err == RATE_LIMIT_ERR_INVALID_ARG);
}

TEST(check_not_initialized) {
    rate_limit_result_t result;
    int err = rate_limiter_check("192.168.1.1", &result);
    assert(err == RATE_LIMIT_ERR_NOT_INIT);
}

TEST(check_allows_requests) {
    rate_limit_config_t config = {
        .requests_per_minute = 60,
        .burst_size = 10,
        .per_ip = true,
        .per_user = false
    };
    rate_limiter_init(&config);
    
    rate_limit_result_t result;
    
    /* First request should pass */
    int err = rate_limiter_check("192.168.1.1", &result);
    assert(err == RATE_LIMIT_ERR_SUCCESS);
    assert(result.remaining == 9); /* 10 - 1 */
    assert(result.limit == 10);
    
    /* Second request should also pass */
    err = rate_limiter_check("192.168.1.1", &result);
    assert(err == RATE_LIMIT_ERR_SUCCESS);
    assert(result.remaining == 8);
    
    rate_limiter_cleanup();
}

TEST(check_blocks_when_exceeded) {
    rate_limit_config_t config = {
        .requests_per_minute = 60,
        .burst_size = 3, /* Very small bucket */
        .per_ip = true,
        .per_user = false
    };
    rate_limiter_init(&config);
    
    rate_limit_result_t result;
    const char *ip = "10.0.0.1";
    
    /* Consume all tokens */
    rate_limiter_check(ip, &result); /* 2 remaining */
    rate_limiter_check(ip, &result); /* 1 remaining */
    rate_limiter_check(ip, &result); /* 0 remaining */
    
    /* Next request should be blocked */
    int err = rate_limiter_check(ip, &result);
    assert(err == RATE_LIMIT_ERR_EXCEEDED);
    assert(result.remaining == 0);
    assert(result.retry_after >= 0);
    
    rate_limiter_cleanup();
}

TEST(check_different_ips_independent) {
    rate_limit_config_t config = {
        .requests_per_minute = 60,
        .burst_size = 2,
        .per_ip = true,
        .per_user = false
    };
    rate_limiter_init(&config);
    
    rate_limit_result_t result;
    
    /* Exhaust IP 1 */
    rate_limiter_check("1.1.1.1", &result);
    rate_limiter_check("1.1.1.1", &result);
    int err = rate_limiter_check("1.1.1.1", &result);
    assert(err == RATE_LIMIT_ERR_EXCEEDED);
    
    /* IP 2 should still work */
    err = rate_limiter_check("2.2.2.2", &result);
    assert(err == RATE_LIMIT_ERR_SUCCESS);
    
    rate_limiter_cleanup();
}

TEST(reset_bucket) {
    rate_limit_config_t config = {
        .requests_per_minute = 60,
        .burst_size = 2,
        .per_ip = true,
        .per_user = false
    };
    rate_limiter_init(&config);
    
    rate_limit_result_t result;
    const char *ip = "3.3.3.3";
    
    /* Exhaust bucket */
    rate_limiter_check(ip, &result);
    rate_limiter_check(ip, &result);
    rate_limiter_check(ip, &result);
    
    /* Reset bucket */
    int err = rate_limiter_reset(ip);
    assert(err == RATE_LIMIT_ERR_SUCCESS);
    
    /* Should work again with fresh bucket */
    err = rate_limiter_check(ip, &result);
    assert(err == RATE_LIMIT_ERR_SUCCESS);
    assert(result.remaining == 1); /* Fresh bucket minus 1 */
    
    rate_limiter_cleanup();
}

TEST(bucket_count) {
    rate_limit_config_t config = {
        .requests_per_minute = 60,
        .burst_size = 10,
        .per_ip = true,
        .per_user = false
    };
    rate_limiter_init(&config);
    
    assert(rate_limiter_bucket_count() == 0);
    
    rate_limit_result_t result;
    rate_limiter_check("ip1", &result);
    assert(rate_limiter_bucket_count() == 1);
    
    rate_limiter_check("ip2", &result);
    assert(rate_limiter_bucket_count() == 2);
    
    rate_limiter_check("ip1", &result); /* Same IP */
    assert(rate_limiter_bucket_count() == 2);
    
    rate_limiter_cleanup();
}

TEST(get_headers) {
    rate_limit_result_t result = {
        .remaining = 5,
        .limit = 10,
        .reset_at = 1704800000,
        .retry_after = 30
    };
    
    rate_limit_headers_t headers;
    rate_limiter_get_headers(&result, &headers);
    
    assert(strcmp(headers.x_ratelimit_limit, "10") == 0);
    assert(strcmp(headers.x_ratelimit_remaining, "5") == 0);
    assert(strcmp(headers.retry_after, "30") == 0);
}

TEST(make_key_ip) {
    char key[256];
    rate_limiter_make_key("192.168.1.1", NULL, key, sizeof(key));
    assert(strstr(key, "ip:") != NULL);
    assert(strstr(key, "192.168.1.1") != NULL);
}

TEST(make_key_user) {
    char key[256];
    rate_limiter_make_key("192.168.1.1", "user123", key, sizeof(key));
    assert(strstr(key, "user:") != NULL);
    assert(strstr(key, "user123") != NULL);
}

/* ============================================================================
 * Main
 * ============================================================================ */

int main(void) {
    printf("\n=== SENTINEL Shield Rate Limiter Tests ===\n\n");
    
    RUN_TEST(init_success);
    RUN_TEST(init_null_config);
    RUN_TEST(check_not_initialized);
    RUN_TEST(check_allows_requests);
    RUN_TEST(check_blocks_when_exceeded);
    RUN_TEST(check_different_ips_independent);
    RUN_TEST(reset_bucket);
    RUN_TEST(bucket_count);
    RUN_TEST(get_headers);
    RUN_TEST(make_key_ip);
    RUN_TEST(make_key_user);
    
    printf("\n=== Results: %d/%d tests passed ===\n\n", tests_passed, tests_run);
    
    return (tests_passed == tests_run) ? 0 : 1;
}
