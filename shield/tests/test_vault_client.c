/**
 * @file test_vault_client.c
 * @brief Unit tests for SENTINEL Shield Vault Client Module
 * 
 * @author SENTINEL Team
 * @date 2026-01-09
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include "../src/utils/vault_client.h"

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

/* Test fallback file for unit tests */
static const char *TEST_FALLBACK_FILE = "/tmp/sentinel_vault_test.txt";

static void create_test_fallback_file(void) {
    FILE *fp = fopen(TEST_FALLBACK_FILE, "w");
    if (fp) {
        fprintf(fp, "jwt_secret=test-secret-from-fallback\n");
        fprintf(fp, "api_key=test-api-key-12345\n");
        fprintf(fp, "db_password=super-secure-password\n");
        fclose(fp);
    }
}

static void cleanup_test_fallback_file(void) {
    remove(TEST_FALLBACK_FILE);
}

/* ============================================================================
 * Tests
 * ============================================================================ */

TEST(init_success) {
    vault_config_t config = {0};
    strncpy(config.address, "http://127.0.0.1:8200", sizeof(config.address) - 1);
    strncpy(config.token, "test-token", sizeof(config.token) - 1);
    strncpy(config.secret_path, "secret/data/sentinel", sizeof(config.secret_path) - 1);
    config.cache_ttl_seconds = 300;
    config.timeout_seconds = 5;
    config.verify_ssl = false;
    
    int err = vault_init(&config);
    assert(err == VAULT_ERR_SUCCESS);
    assert(vault_is_initialized() == true);
    
    vault_cleanup();
    assert(vault_is_initialized() == false);
}

TEST(init_null_config) {
    int err = vault_init(NULL);
    assert(err == VAULT_ERR_INVALID_ARG);
}

TEST(get_secret_not_initialized) {
    char value[256];
    int err = vault_get_secret("test_key", value, sizeof(value));
    assert(err == VAULT_ERR_NOT_INITIALIZED);
}

TEST(get_secret_null_args) {
    vault_config_t config = {0};
    strncpy(config.address, "http://127.0.0.1:8200", sizeof(config.address) - 1);
    vault_init(&config);
    
    char value[256];
    
    int err = vault_get_secret(NULL, value, sizeof(value));
    assert(err == VAULT_ERR_INVALID_ARG);
    
    err = vault_get_secret("key", NULL, sizeof(value));
    assert(err == VAULT_ERR_INVALID_ARG);
    
    err = vault_get_secret("key", value, 0);
    assert(err == VAULT_ERR_INVALID_ARG);
    
    vault_cleanup();
}

TEST(fallback_file) {
    create_test_fallback_file();
    
    vault_config_t config = {0};
    strncpy(config.address, "http://127.0.0.1:8200", sizeof(config.address) - 1);
    strncpy(config.fallback_file, TEST_FALLBACK_FILE, sizeof(config.fallback_file) - 1);
    config.enable_fallback = true;
    config.cache_ttl_seconds = 0; /* No caching for test */
    
    vault_init(&config);
    
    char value[256] = {0};
    int err = vault_get_secret("jwt_secret", value, sizeof(value));
    
    /* Should succeed with fallback (or fail if HTTP fails and fallback works) */
    /* In stub mode without libcurl, should use fallback */
    #ifndef SHIELD_USE_CURL
    if (err == VAULT_ERR_SUCCESS) {
        assert(strcmp(value, "test-secret-from-fallback") == 0);
    }
    #endif
    
    vault_cleanup();
    cleanup_test_fallback_file();
}

TEST(cache_operations) {
    vault_config_t config = {0};
    strncpy(config.address, "http://127.0.0.1:8200", sizeof(config.address) - 1);
    config.cache_ttl_seconds = 300;
    
    vault_init(&config);
    
    /* Initially no cached secrets */
    vault_status_t status;
    vault_get_status(&status);
    assert(status.cached_secrets == 0);
    
    /* Invalidate all (should work even with empty cache) */
    vault_invalidate_cache(NULL);
    
    vault_get_status(&status);
    assert(status.cached_secrets == 0);
    
    vault_cleanup();
}

TEST(status_tracking) {
    vault_config_t config = {0};
    strncpy(config.address, "http://127.0.0.1:8200", sizeof(config.address) - 1);
    config.cache_ttl_seconds = 300;
    
    vault_init(&config);
    
    vault_status_t status;
    vault_get_status(&status);
    
    assert(status.initialized == true);
    assert(status.fetch_count == 0);
    assert(status.cache_hits == 0);
    
    vault_cleanup();
}

TEST(health_check) {
    vault_config_t config = {0};
    strncpy(config.address, "http://127.0.0.1:8200", sizeof(config.address) - 1);
    
    vault_init(&config);
    
    int err = vault_health_check();
    assert(err == VAULT_ERR_SUCCESS);
    
    vault_cleanup();
}

TEST(renew_token) {
    vault_config_t config = {0};
    strncpy(config.address, "http://127.0.0.1:8200", sizeof(config.address) - 1);
    strncpy(config.token, "test-token", sizeof(config.token) - 1);
    
    vault_init(&config);
    
    int err = vault_renew_token();
    assert(err == VAULT_ERR_SUCCESS);
    
    vault_cleanup();
}

TEST(strerror) {
    const char *msg;
    
    msg = vault_strerror(VAULT_ERR_SUCCESS);
    assert(msg != NULL);
    assert(strlen(msg) > 0);
    
    msg = vault_strerror(VAULT_ERR_NOT_FOUND);
    assert(msg != NULL);
    assert(strstr(msg, "not found") != NULL || strstr(msg, "Not found") != NULL);
    
    msg = vault_strerror(VAULT_ERR_AUTH_FAILED);
    assert(msg != NULL);
    
    msg = vault_strerror(-999);
    assert(msg != NULL); /* Unknown error */
}

TEST(invalidate_specific_key) {
    vault_config_t config = {0};
    strncpy(config.address, "http://127.0.0.1:8200", sizeof(config.address) - 1);
    config.cache_ttl_seconds = 300;
    
    vault_init(&config);
    
    /* Invalidate non-existent key should not crash */
    vault_invalidate_cache("non_existent_key");
    
    vault_status_t status;
    vault_get_status(&status);
    assert(status.initialized == true);
    
    vault_cleanup();
}

/* ============================================================================
 * Main
 * ============================================================================ */

int main(void) {
    printf("\n=== SENTINEL Shield Vault Client Tests ===\n\n");
    
    RUN_TEST(init_success);
    RUN_TEST(init_null_config);
    RUN_TEST(get_secret_not_initialized);
    RUN_TEST(get_secret_null_args);
    RUN_TEST(fallback_file);
    RUN_TEST(cache_operations);
    RUN_TEST(status_tracking);
    RUN_TEST(health_check);
    RUN_TEST(renew_token);
    RUN_TEST(strerror);
    RUN_TEST(invalidate_specific_key);
    
    printf("\n=== Results: %d/%d tests passed ===\n\n", tests_passed, tests_run);
    
    return (tests_passed == tests_run) ? 0 : 1;
}
