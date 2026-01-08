/*
 * SENTINEL IMMUNE — TLS Transport Unit Tests
 * 
 * Tests for tls_transport module.
 * Compile: cc -o test_tls test_tls_transport.c ../common/src/tls_transport.c -DUSE_WOLFSSL -lwolfssl
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>

#include "../common/include/tls_transport.h"

/* Test counters */
static int tests_run = 0;
static int tests_passed = 0;

#define TEST(name) do { \
    printf("  TEST: %s... ", #name); \
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
 * Test init and cleanup without memory leaks.
 */
static int
test_init_cleanup(void)
{
    int ret = tls_init();
    if (ret != TLS_OK) return 0;
    
    tls_cleanup();
    return 1;
}

/**
 * Test default configuration values.
 */
static int
test_config_defaults(void)
{
    tls_config_t config;
    tls_config_init(&config);
    
    /* Check defaults */
    if (!config.verify_peer) return 0;
    if (!config.mtls_enabled) return 0;
    if (config.handshake_timeout != TLS_HANDSHAKE_TIMEOUT) return 0;
    if (config.read_timeout != TLS_READ_TIMEOUT) return 0;
    if (config.pin_enabled) return 0;  /* Should be off by default */
    
    /* Check default paths */
    if (strlen(config.ca_cert_path) == 0) return 0;
    
    return 1;
}

/**
 * Test error string mapping.
 */
static int
test_error_strings(void)
{
    const char *s;
    
    s = tls_error_string(TLS_OK);
    if (!s || strlen(s) == 0) return 0;
    
    s = tls_error_string(TLS_ERR_CONNECT);
    if (!s || strlen(s) == 0) return 0;
    
    s = tls_error_string(TLS_ERR_PIN_MISMATCH);
    if (!s || strcmp(s, "Certificate pin mismatch") != 0) return 0;
    
    return 1;
}

/**
 * Test channel creation.
 */
static int
test_channel_create(void)
{
    tls_config_t config;
    tls_config_init(&config);
    
    /* Disable verification for test (no certs) */
    config.verify_peer = false;
    config.mtls_enabled = false;
    config.ca_cert_path[0] = '\0';
    
    if (tls_init() != TLS_OK) return 0;
    
    tls_channel_t *ch = tls_channel_create(&config);
    
    /* Channel creation should succeed even without wolfSSL */
    if (!ch) {
        tls_cleanup();
        return 0;
    }
    
    /* Should be disconnected initially */
    if (tls_get_state(ch) != TLS_STATE_DISCONNECTED) {
        tls_channel_destroy(ch);
        tls_cleanup();
        return 0;
    }
    
    tls_channel_destroy(ch);
    tls_cleanup();
    return 1;
}

/**
 * Test connect to non-existent server (error handling).
 */
static int
test_connect_no_server(void)
{
    tls_config_t config;
    tls_config_init(&config);
    config.verify_peer = false;
    config.mtls_enabled = false;
    config.ca_cert_path[0] = '\0';
    config.handshake_timeout = 2;  /* Short timeout */
    
    if (tls_init() != TLS_OK) return 0;
    
    tls_channel_t *ch = tls_channel_create(&config);
    if (!ch) {
        tls_cleanup();
        return 0;
    }
    
    /* Connect to non-existent server */
    int ret = tls_channel_connect(ch, "127.0.0.1", 59999);
    
    /* Should fail */
    if (ret == TLS_OK) {
        tls_channel_destroy(ch);
        tls_cleanup();
        return 0;
    }
    
    /* State should be error */
    if (tls_get_state(ch) != TLS_STATE_ERROR) {
        tls_channel_destroy(ch);
        tls_cleanup();
        return 0;
    }
    
    tls_channel_destroy(ch);
    tls_cleanup();
    return 1;
}

/**
 * Test certificate pin setting.
 */
static int
test_pin_setting(void)
{
    tls_config_t config;
    tls_config_init(&config);
    
    uint8_t test_hash[TLS_PIN_HASH_SIZE];
    memset(test_hash, 0xAB, TLS_PIN_HASH_SIZE);
    
    if (config.pin_enabled) return 0;  /* Should be off */
    
    tls_config_set_pin(&config, test_hash);
    
    if (!config.pin_enabled) return 0;  /* Should be on now */
    if (memcmp(config.pinned_hash, test_hash, TLS_PIN_HASH_SIZE) != 0) return 0;
    
    return 1;
}

/**
 * Test NULL handling.
 */
static int
test_null_handling(void)
{
    /* Should not crash on NULL */
    tls_channel_close(NULL);
    tls_channel_destroy(NULL);
    tls_server_destroy(NULL);
    
    if (tls_get_state(NULL) != TLS_STATE_DISCONNECTED) return 0;
    if (tls_get_error(NULL) != TLS_ERR_INIT) return 0;
    
    if (tls_send(NULL, "test", 4) >= 0) return 0;
    if (tls_recv(NULL, NULL, 0) >= 0) return 0;
    
    return 1;
}

/* ==================== Main ==================== */

int
main(void)
{
    printf("\n");
    printf("===========================================\n");
    printf("  IMMUNE TLS Transport — Unit Tests\n");
    printf("===========================================\n\n");
    
    TEST(init_cleanup);
    TEST(config_defaults);
    TEST(error_strings);
    TEST(channel_create);
    TEST(connect_no_server);
    TEST(pin_setting);
    TEST(null_handling);
    
    printf("\n-------------------------------------------\n");
    printf("  Results: %d/%d tests passed\n", tests_passed, tests_run);
    printf("-------------------------------------------\n\n");
    
    return (tests_passed == tests_run) ? 0 : 1;
}
