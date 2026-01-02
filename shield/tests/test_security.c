/*
 * SENTINEL Shield - Security Tests
 * 
 * Tests for security-critical functionality
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>

#include "shield_common.h"
#include "shield_canary.h"
#include "shield_entropy.h"
#include "shield_session.h"
#include "shield_ratelimit.h"

static int tests_run = 0;
static int tests_passed = 0;

#define TEST(name) static void test_##name(void)
#define RUN_TEST(name) do { \
    printf("  [TEST] %s... ", #name); \
    test_##name(); \
    tests_run++; \
    tests_passed++; \
    printf("PASSED\n"); \
} while(0)

#define ASSERT(cond) do { \
    if (!(cond)) { \
        printf("FAILED\n    Assertion failed: %s\n", #cond); \
        exit(1); \
    } \
} while(0)

/* ===== Canary Tests ===== */

TEST(canary_create)
{
    canary_manager_t mgr;
    ASSERT(canary_manager_init(&mgr) == SHIELD_OK);
    
    canary_token_t *token = NULL;
    ASSERT(canary_create(&mgr, CANARY_TYPE_STRING, "SECRET123", "test", &token) == SHIELD_OK);
    ASSERT(token != NULL);
    ASSERT(strcmp(token->value, "SECRET123") == 0);
    
    canary_manager_destroy(&mgr);
}

TEST(canary_scan)
{
    canary_manager_t mgr;
    canary_manager_init(&mgr);
    
    canary_token_t *token = NULL;
    canary_create(&mgr, CANARY_TYPE_STRING, "CANARY_TOKEN_XYZ", "test", &token);
    
    ASSERT(canary_scan(&mgr, "Normal text without token", 25) == false);
    ASSERT(canary_scan(&mgr, "Text with CANARY_TOKEN_XYZ inside", 32) == true);
    ASSERT(token->triggered_count == 1);
    
    canary_manager_destroy(&mgr);
}

/* ===== Entropy Tests ===== */

TEST(entropy_normal)
{
    const char *normal = "Hello, this is a normal English sentence.";
    float entropy = calculate_entropy((const uint8_t *)normal, strlen(normal));
    
    /* Normal text should have entropy around 3-4 bits/byte */
    ASSERT(entropy > 2.0f);
    ASSERT(entropy < 5.0f);
}

TEST(entropy_high)
{
    const char *random = "7Kj9#mX$2pL@qR8nZvBwYcFhGtDsEa";
    float entropy = calculate_entropy((const uint8_t *)random, strlen(random));
    
    /* Random/encoded data should have higher entropy */
    ASSERT(entropy > 4.0f);
}

TEST(entropy_low)
{
    const char *repeating = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
    float entropy = calculate_entropy((const uint8_t *)repeating, strlen(repeating));
    
    /* Repeating data should have very low entropy */
    ASSERT(entropy < 1.0f);
}

/* ===== SimHash Tests ===== */

TEST(simhash_similar)
{
    const char *text1 = "The quick brown fox jumps over the lazy dog";
    const char *text2 = "The quick brown fox jumps over the lazy cat";
    
    uint64_t hash1 = simhash((const uint8_t *)text1, strlen(text1));
    uint64_t hash2 = simhash((const uint8_t *)text2, strlen(text2));
    
    int distance = simhash_distance(hash1, hash2);
    
    /* Similar texts should have small Hamming distance */
    ASSERT(distance < 10);
}

TEST(simhash_different)
{
    const char *text1 = "The quick brown fox";
    const char *text2 = "Lorem ipsum dolor sit amet";
    
    uint64_t hash1 = simhash((const uint8_t *)text1, strlen(text1));
    uint64_t hash2 = simhash((const uint8_t *)text2, strlen(text2));
    
    int distance = simhash_distance(hash1, hash2);
    
    /* Different texts should have larger Hamming distance */
    ASSERT(distance > 15);
}

/* ===== Session Tests ===== */

TEST(session_create)
{
    session_manager_t mgr;
    ASSERT(session_manager_init(&mgr, 300) == SHIELD_OK);
    
    session_t *session = NULL;
    ASSERT(session_create(&mgr, "192.168.1.1", "test-zone", &session) == SHIELD_OK);
    ASSERT(session != NULL);
    ASSERT(strcmp(session->source_ip, "192.168.1.1") == 0);
    
    session_manager_destroy(&mgr);
}

TEST(session_threat)
{
    session_manager_t mgr;
    session_manager_init(&mgr, 300);
    
    session_t *session = NULL;
    session_create(&mgr, "192.168.1.1", "test-zone", &session);
    
    ASSERT(session->threat_score == 0.0f);
    
    session_add_threat(session, 0.5f, "test threat");
    ASSERT(session->threat_score == 0.5f);
    
    session_add_threat(session, 0.3f, "another threat");
    ASSERT(session->threat_score == 0.8f);
    
    session_manager_destroy(&mgr);
}

/* ===== Rate Limit Tests ===== */

TEST(ratelimit_acquire)
{
    rate_limiter_t rl;
    ASSERT(ratelimit_init(&rl, 5, 3) == SHIELD_OK);  /* 5 rps, burst 3 */
    
    /* First 3 should succeed (burst) */
    ASSERT(ratelimit_acquire(&rl, "user1") == true);
    ASSERT(ratelimit_acquire(&rl, "user1") == true);
    ASSERT(ratelimit_acquire(&rl, "user1") == true);
    
    /* Different user should have own bucket */
    ASSERT(ratelimit_acquire(&rl, "user2") == true);
    
    ratelimit_destroy(&rl);
}

/* ===== Main ===== */

int main(void)
{
    printf("\n");
    printf("========================================\n");
    printf("  SENTINEL Shield Security Tests\n");
    printf("========================================\n\n");
    
    /* Canary tests */
    printf("[CANARY]\n");
    RUN_TEST(canary_create);
    RUN_TEST(canary_scan);
    printf("\n");
    
    /* Entropy tests */
    printf("[ENTROPY]\n");
    RUN_TEST(entropy_normal);
    RUN_TEST(entropy_high);
    RUN_TEST(entropy_low);
    printf("\n");
    
    /* SimHash tests */
    printf("[SIMHASH]\n");
    RUN_TEST(simhash_similar);
    RUN_TEST(simhash_different);
    printf("\n");
    
    /* Session tests */
    printf("[SESSION]\n");
    RUN_TEST(session_create);
    RUN_TEST(session_threat);
    printf("\n");
    
    /* Rate limit tests */
    printf("[RATELIMIT]\n");
    RUN_TEST(ratelimit_acquire);
    printf("\n");
    
    printf("========================================\n");
    printf("  Results: %d/%d tests passed\n", tests_passed, tests_run);
    printf("========================================\n\n");
    
    return (tests_passed == tests_run) ? 0 : 1;
}
