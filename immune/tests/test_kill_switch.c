/*
 * SENTINEL IMMUNE — Kill Switch Unit Tests
 * 
 * Tests for Shamir Secret Sharing and kill switch functionality.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../hive/include/kill_switch.h"

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
 * Generate and combine shares (3-of-5).
 */
static int
test_split_combine_3of5(void)
{
    uint8_t secret[KILL_SECRET_SIZE];
    uint8_t recovered[KILL_SECRET_SIZE];
    kill_share_t shares[5];
    
    /* Generate random secret */
    if (kill_generate_secret(secret) != 0) return 0;
    
    /* Split into 5 shares, threshold 3 */
    if (kill_generate_shares(secret, shares, 5, 3) != 0) return 0;
    
    /* Combine first 3 shares */
    if (kill_combine_shares(shares, 3, recovered) != 0) return 0;
    
    /* Should match */
    if (memcmp(secret, recovered, KILL_SECRET_SIZE) != 0) return 0;
    
    return 1;
}

/**
 * Different 3 shares should also work.
 */
static int
test_different_shares(void)
{
    uint8_t secret[KILL_SECRET_SIZE];
    uint8_t recovered[KILL_SECRET_SIZE];
    kill_share_t shares[5];
    kill_share_t subset[3];
    
    if (kill_generate_secret(secret) != 0) return 0;
    if (kill_generate_shares(secret, shares, 5, 3) != 0) return 0;
    
    /* Use shares 0, 2, 4 */
    subset[0] = shares[0];
    subset[1] = shares[2];
    subset[2] = shares[4];
    
    if (kill_combine_shares(subset, 3, recovered) != 0) return 0;
    if (memcmp(secret, recovered, KILL_SECRET_SIZE) != 0) return 0;
    
    /* Use shares 1, 3, 4 */
    subset[0] = shares[1];
    subset[1] = shares[3];
    subset[2] = shares[4];
    
    if (kill_combine_shares(subset, 3, recovered) != 0) return 0;
    if (memcmp(secret, recovered, KILL_SECRET_SIZE) != 0) return 0;
    
    return 1;
}

/**
 * 2 of 5 shares should NOT reconstruct (we can't really test this).
 * We just verify it gives a different result.
 */
static int
test_insufficient_shares(void)
{
    uint8_t secret[KILL_SECRET_SIZE];
    uint8_t recovered[KILL_SECRET_SIZE];
    kill_share_t shares[5];
    
    if (kill_generate_secret(secret) != 0) return 0;
    if (kill_generate_shares(secret, shares, 5, 3) != 0) return 0;
    
    /* Try with only 2 shares - should give wrong result */
    if (kill_combine_shares(shares, 2, recovered) != 0) return 0;
    
    /* Should NOT match (with overwhelming probability) */
    if (memcmp(secret, recovered, KILL_SECRET_SIZE) == 0) {
        /* Extremely unlikely collision */
        return 0;
    }
    
    return 1;
}

/**
 * Configuration initialization.
 */
static int
test_config_init(void)
{
    kill_config_t config;
    kill_config_init(&config);
    
    if (config.threshold != KILL_DEFAULT_THRESHOLD) return 0;
    if (config.total_shares != KILL_DEFAULT_SHARES) return 0;
    if (config.canary_hours != KILL_CANARY_HOURS) return 0;
    
    return 1;
}

/**
 * Kill switch initialization.
 */
static int
test_init(void)
{
    if (kill_init(NULL) != 0) return 0;
    if (kill_get_state() != KILL_STATE_NORMAL) return 0;
    
    return 1;
}

/**
 * Share submission.
 */
static int
test_share_submission(void)
{
    uint8_t secret[KILL_SECRET_SIZE];
    kill_share_t shares[5];
    
    if (kill_generate_secret(secret) != 0) return 0;
    if (kill_generate_shares(secret, shares, 5, 3) != 0) return 0;
    
    /* Submit 3 shares */
    if (kill_submit_share(&shares[0]) != 1) return 0;  /* Now have 1 */
    if (kill_submit_share(&shares[1]) != 2) return 0;  /* Now have 2 */
    if (kill_submit_share(&shares[2]) != 3) return 0;  /* Now have 3 */
    
    /* Should be armed */
    if (kill_get_state() != KILL_STATE_ARMED) return 0;
    
    /* Clear */
    kill_clear_shares();
    if (kill_get_state() != KILL_STATE_NORMAL) return 0;
    
    return 1;
}

/**
 * Kill command verification.
 */
static int
test_command_verify(void)
{
    kill_command_t cmd;
    
    /* Valid command */
    memcpy(cmd.magic, "KILL", 4);
    cmd.version = 1;
    cmd.timestamp = (uint64_t)time(NULL);
    memset(cmd.payload, 0xAB, KILL_SECRET_SIZE);
    
    if (!kill_verify_command(&cmd)) return 0;
    
    /* Invalid magic */
    memcpy(cmd.magic, "NOPE", 4);
    if (kill_verify_command(&cmd)) return 0;
    
    /* Invalid version */
    memcpy(cmd.magic, "KILL", 4);
    cmd.version = 99;
    if (kill_verify_command(&cmd)) return 0;
    
    return 1;
}

/**
 * State string mapping.
 */
static int
test_state_strings(void)
{
    const char *s;
    
    s = kill_state_string(KILL_STATE_NORMAL);
    if (!s || strcmp(s, "Normal") != 0) return 0;
    
    s = kill_state_string(KILL_STATE_TRIGGERED);
    if (!s || strcmp(s, "Triggered") != 0) return 0;
    
    return 1;
}

/**
 * Secure zero.
 */
static int
test_secure_zero(void)
{
    uint8_t buf[32];
    memset(buf, 0xAB, sizeof(buf));
    
    kill_secure_zero(buf, sizeof(buf));
    
    for (int i = 0; i < 32; i++) {
        if (buf[i] != 0) return 0;
    }
    
    return 1;
}

/**
 * 2-of-3 threshold.
 */
static int
test_2of3_threshold(void)
{
    uint8_t secret[KILL_SECRET_SIZE];
    uint8_t recovered[KILL_SECRET_SIZE];
    kill_share_t shares[3];
    
    if (kill_generate_secret(secret) != 0) return 0;
    if (kill_generate_shares(secret, shares, 3, 2) != 0) return 0;
    
    /* Any 2 shares should work */
    if (kill_combine_shares(shares, 2, recovered) != 0) return 0;
    if (memcmp(secret, recovered, KILL_SECRET_SIZE) != 0) return 0;
    
    return 1;
}

/* ==================== Main ==================== */

int
main(void)
{
    printf("\n");
    printf("=============================================\n");
    printf("  IMMUNE Kill Switch — Unit Tests\n");
    printf("=============================================\n\n");
    
    TEST(config_init);
    TEST(init);
    TEST(split_combine_3of5);
    TEST(different_shares);
    TEST(insufficient_shares);
    TEST(2of3_threshold);
    TEST(share_submission);
    TEST(command_verify);
    TEST(state_strings);
    TEST(secure_zero);
    
    printf("\n---------------------------------------------\n");
    printf("  Results: %d/%d tests passed\n", tests_passed, tests_run);
    printf("---------------------------------------------\n\n");
    
    return (tests_passed == tests_run) ? 0 : 1;
}
