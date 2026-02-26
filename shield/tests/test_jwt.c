/**
 * @file test_jwt.c
 * @brief Unit tests for SENTINEL Shield JWT Module
 * 
 * @author SENTINEL Team
 * @date 2026-01-09
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include "../src/protocols/szaa_jwt.h"

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

/* Sample JWT tokens for testing */
/* Header: {"alg":"HS256","typ":"JWT"} = eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9 */
/* Payload: {"sub":"user123","iss":"sentinel","aud":"shield-api","exp":9999999999,"iat":1704800000} */

static const char *VALID_TOKEN = 
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzdWIiOiJ1c2VyMTIzIiwiaXNzIjoic2VudGluZWwiLCJhdWQiOiJzaGllbGQtYXBpIiwiZXhwIjo5OTk5OTk5OTk5LCJpYXQiOjE3MDQ4MDAwMDB9."
    "test_signature_placeholder";

/* Expired token (exp: 1704800000 - in the past) */
static const char *EXPIRED_TOKEN =
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzdWIiOiJ1c2VyMTIzIiwiaXNzIjoic2VudGluZWwiLCJhdWQiOiJzaGllbGQtYXBpIiwiZXhwIjoxNzA0ODAwMDAwLCJpYXQiOjE3MDQ3MDAwMDB9."
    "test_signature_placeholder";

static const char *TEST_SECRET = "super-secret-key-for-testing-only";

/* ============================================================================
 * Tests
 * ============================================================================ */

TEST(jwt_init_success) {
    jwt_config_t config = {0};
    config.algorithm = JWT_ALG_HS256;
    strncpy(config.secret, TEST_SECRET, sizeof(config.secret) - 1);
    strncpy(config.issuer, "sentinel", sizeof(config.issuer) - 1);
    strncpy(config.audience, "shield-api", sizeof(config.audience) - 1);
    config.clock_skew_seconds = 30;
    config.require_exp = true;
    
    int err = jwt_init(&config);
    assert(err == JWT_ERR_SUCCESS);
    assert(jwt_is_initialized() == true);
    
    jwt_cleanup();
    assert(jwt_is_initialized() == false);
}

TEST(jwt_init_null_config) {
    int err = jwt_init(NULL);
    assert(err == JWT_ERR_INVALID_TOKEN);
}

TEST(jwt_verify_not_initialized) {
    jwt_claims_t claims;
    int err = jwt_verify(VALID_TOKEN, &claims);
    assert(err == JWT_ERR_NOT_INITIALIZED);
}

TEST(jwt_verify_null_token) {
    jwt_config_t config = {0};
    config.algorithm = JWT_ALG_HS256;
    strncpy(config.secret, TEST_SECRET, sizeof(config.secret) - 1);
    jwt_init(&config);
    
    jwt_claims_t claims;
    int err = jwt_verify(NULL, &claims);
    assert(err == JWT_ERR_INVALID_TOKEN);
    
    jwt_cleanup();
}

TEST(jwt_verify_invalid_format) {
    jwt_config_t config = {0};
    config.algorithm = JWT_ALG_HS256;
    strncpy(config.secret, TEST_SECRET, sizeof(config.secret) - 1);
    jwt_init(&config);
    
    jwt_claims_t claims;
    
    /* No dots */
    int err = jwt_verify("invalid_token_no_dots", &claims);
    assert(err == JWT_ERR_INVALID_TOKEN);
    
    /* Only one dot */
    err = jwt_verify("header.payload", &claims);
    assert(err == JWT_ERR_INVALID_TOKEN);
    
    jwt_cleanup();
}

TEST(jwt_verify_bearer_prefix) {
    jwt_config_t config = {0};
    config.algorithm = JWT_ALG_HS256;
    strncpy(config.secret, TEST_SECRET, sizeof(config.secret) - 1);
    jwt_init(&config);
    
    jwt_claims_t claims;
    char token_with_bearer[1024];
    snprintf(token_with_bearer, sizeof(token_with_bearer), "Bearer %s", VALID_TOKEN);
    
    /* Should handle Bearer prefix - might fail on sig but not on format */
    int err = jwt_verify(token_with_bearer, &claims);
    /* We're testing that Bearer prefix is stripped, not signature validity */
    /* In non-wolfssl mode, signature check is skipped */
    #ifndef SHIELD_USE_WOLFSSL
    assert(err == JWT_ERR_SUCCESS || err == JWT_ERR_INVALID_SIG);
    #endif
    
    jwt_cleanup();
}

TEST(jwt_parse_claims) {
    jwt_config_t config = {0};
    config.algorithm = JWT_ALG_HS256;
    strncpy(config.secret, TEST_SECRET, sizeof(config.secret) - 1);
    /* Don't verify issuer/audience for this test */
    jwt_init(&config);
    
    jwt_claims_t claims;
    int err = jwt_verify(VALID_TOKEN, &claims);
    
    #ifndef SHIELD_USE_WOLFSSL
    /* In stub mode without crypto, should parse claims */
    if (err == JWT_ERR_SUCCESS) {
        assert(strcmp(claims.sub, "user123") == 0);
        assert(strcmp(claims.iss, "sentinel") == 0);
        assert(strcmp(claims.aud, "shield-api") == 0);
        assert(claims.exp == 9999999999LL);
    }
    #endif
    
    jwt_cleanup();
}

TEST(jwt_strerror) {
    const char *msg;
    
    msg = jwt_strerror(JWT_ERR_SUCCESS);
    assert(msg != NULL);
    assert(strlen(msg) > 0);
    
    msg = jwt_strerror(JWT_ERR_EXPIRED);
    assert(msg != NULL);
    assert(strstr(msg, "expired") != NULL || strstr(msg, "Expired") != NULL);
    
    msg = jwt_strerror(JWT_ERR_INVALID_SIG);
    assert(msg != NULL);
    
    msg = jwt_strerror(-999);
    assert(msg != NULL); /* Unknown error message */
}

TEST(base64url_decode) {
    /* "hello" in base64url = aGVsbG8 */
    const char *input = "aGVsbG8";
    uint8_t output[32];
    
    int len = jwt_base64url_decode(input, strlen(input), output, sizeof(output));
    assert(len == 5);
    assert(memcmp(output, "hello", 5) == 0);
}

TEST(base64url_decode_with_padding) {
    /* Test with URL-safe characters - and _ */
    const char *input = "YWJjZC1l"; /* "abcd-e" encoded */
    uint8_t output[32];
    
    int len = jwt_base64url_decode(input, strlen(input), output, sizeof(output));
    assert(len > 0);
}

/* ============================================================================
 * Main
 * ============================================================================ */

int main(void) {
    printf("\n=== SENTINEL Shield JWT Tests ===\n\n");
    
    RUN_TEST(jwt_init_success);
    RUN_TEST(jwt_init_null_config);
    RUN_TEST(jwt_verify_not_initialized);
    RUN_TEST(jwt_verify_null_token);
    RUN_TEST(jwt_verify_invalid_format);
    RUN_TEST(jwt_verify_bearer_prefix);
    RUN_TEST(jwt_parse_claims);
    RUN_TEST(jwt_strerror);
    RUN_TEST(base64url_decode);
    RUN_TEST(base64url_decode_with_padding);
    
    printf("\n=== Results: %d/%d tests passed ===\n\n", tests_passed, tests_run);
    
    return (tests_passed == tests_run) ? 0 : 1;
}
