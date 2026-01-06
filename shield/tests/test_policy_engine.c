/**
 * @file test_policy_engine.c
 * @brief Policy Engine Unit Tests
 * 
 * @author SENTINEL Team
 * @date January 2026
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>

#include "shield_common.h"
#include "shield_policy.h"

/* Test Framework */
static int tests_run = 0;
static int tests_passed = 0;
static int tests_failed = 0;

#define TEST_START(name) \
    do { tests_run++; printf("  [TEST] %-50s ", name); fflush(stdout); } while(0)

#define TEST_PASS() do { tests_passed++; printf("✅ PASS\n"); } while(0)
#define TEST_FAIL(msg) do { tests_failed++; printf("❌ FAIL: %s\n", msg); } while(0)

#define ASSERT_TRUE(cond, msg) do { if (!(cond)) { TEST_FAIL(msg); return; } } while(0)
#define ASSERT_EQ(a, b, msg) ASSERT_TRUE((a) == (b), msg)
#define ASSERT_NE(a, b, msg) ASSERT_TRUE((a) != (b), msg)

/* Policy Engine Tests */

static void test_policy_engine_init(void)
{
    TEST_START("policy_engine_init");
    
    policy_engine_t engine;
    shield_err_t err = policy_engine_init(&engine);
    
    ASSERT_EQ(err, SHIELD_OK, "init should succeed");
    ASSERT_EQ(engine.set_count, 0, "initial set count = 0");
    
    policy_engine_destroy(&engine);
    TEST_PASS();
}

static void test_policy_set_create(void)
{
    TEST_START("policy_set_create");
    
    policy_engine_t engine;
    policy_engine_init(&engine);
    
    policy_set_t *set = NULL;
    shield_err_t err = policy_set_create(&engine, "test_set", &set);
    
    ASSERT_EQ(err, SHIELD_OK, "create should succeed");
    ASSERT_NE(set, NULL, "set not null");
    ASSERT_EQ(engine.set_count, 1, "set count = 1");
    
    policy_engine_destroy(&engine);
    TEST_PASS();
}

static void test_policy_set_duplicate(void)
{
    TEST_START("policy_set_duplicate_error");
    
    policy_engine_t engine;
    policy_engine_init(&engine);
    
    policy_set_create(&engine, "dup_set", NULL);
    shield_err_t err = policy_set_create(&engine, "dup_set", NULL);
    
    ASSERT_EQ(err, SHIELD_ERR_EXISTS, "duplicate should fail");
    
    policy_engine_destroy(&engine);
    TEST_PASS();
}

static void test_policy_rule_add(void)
{
    TEST_START("policy_rule_add");
    
    policy_engine_t engine;
    policy_engine_init(&engine);
    
    policy_set_t *set = NULL;
    policy_set_create(&engine, "rules_set", &set);
    
    policy_rule_t *rule = NULL;
    shield_err_t err = policy_rule_add(set, "block_injection", POLICY_PRIORITY_HIGH, &rule);
    
    ASSERT_EQ(err, SHIELD_OK, "add rule should succeed");
    ASSERT_NE(rule, NULL, "rule not null");
    ASSERT_EQ(set->rule_count, 1, "rule count = 1");
    
    policy_engine_destroy(&engine);
    TEST_PASS();
}

static void test_policy_add_condition(void)
{
    TEST_START("policy_add_condition");
    
    policy_engine_t engine;
    policy_engine_init(&engine);
    
    policy_set_t *set = NULL;
    policy_set_create(&engine, "cond_set", &set);
    
    policy_rule_t *rule = NULL;
    policy_rule_add(set, "detect", POLICY_PRIORITY_HIGH, &rule);
    
    shield_err_t err = policy_add_condition(rule, MATCH_CONTAINS, "injection");
    ASSERT_EQ(err, SHIELD_OK, "add condition should succeed");
    ASSERT_NE(rule->conditions, NULL, "conditions not null");
    
    policy_engine_destroy(&engine);
    TEST_PASS();
}

static void test_policy_add_action(void)
{
    TEST_START("policy_add_action");
    
    policy_engine_t engine;
    policy_engine_init(&engine);
    
    policy_set_t *set = NULL;
    policy_set_create(&engine, "action_set", &set);
    
    policy_rule_t *rule = NULL;
    policy_rule_add(set, "block_rule", POLICY_PRIORITY_HIGH, &rule);
    
    shield_err_t err = policy_add_action(rule, ACTION_BLOCK, 100);
    ASSERT_EQ(err, SHIELD_OK, "add action should succeed");
    ASSERT_NE(rule->actions, NULL, "actions not null");
    
    policy_engine_destroy(&engine);
    TEST_PASS();
}

static void test_policy_set_find(void)
{
    TEST_START("policy_set_find");
    
    policy_engine_t engine;
    policy_engine_init(&engine);
    
    policy_set_create(&engine, "alpha", NULL);
    policy_set_create(&engine, "beta", NULL);
    
    policy_set_t *found = policy_set_find(&engine, "beta");
    ASSERT_NE(found, NULL, "should find beta");
    
    policy_set_t *notfound = policy_set_find(&engine, "gamma");
    ASSERT_EQ(notfound, NULL, "should not find gamma");
    
    policy_engine_destroy(&engine);
    TEST_PASS();
}

static void test_policy_set_delete(void)
{
    TEST_START("policy_set_delete");
    
    policy_engine_t engine;
    policy_engine_init(&engine);
    
    policy_set_create(&engine, "to_delete", NULL);
    ASSERT_EQ(engine.set_count, 1, "count = 1");
    
    shield_err_t err = policy_set_delete(&engine, "to_delete");
    ASSERT_EQ(err, SHIELD_OK, "delete should succeed");
    ASSERT_EQ(engine.set_count, 0, "count = 0");
    
    policy_engine_destroy(&engine);
    TEST_PASS();
}

static void test_policy_evaluate_match(void)
{
    TEST_START("policy_evaluate_match");
    
    policy_engine_t engine;
    policy_engine_init(&engine);
    
    policy_set_t *set = NULL;
    policy_set_create(&engine, "eval_set", &set);
    
    policy_rule_t *rule = NULL;
    policy_rule_add(set, "block_inject", POLICY_PRIORITY_HIGH, &rule);
    policy_add_condition(rule, MATCH_CONTAINS, "injection");
    policy_add_action(rule, ACTION_BLOCK, 100);
    
    rule_action_t result = policy_evaluate(&engine, "eval_set", "test injection attack", 21);
    ASSERT_EQ(result, ACTION_BLOCK, "should block injection");
    
    policy_engine_destroy(&engine);
    TEST_PASS();
}

static void test_policy_evaluate_no_match(void)
{
    TEST_START("policy_evaluate_no_match");
    
    policy_engine_t engine;
    policy_engine_init(&engine);
    
    policy_set_t *set = NULL;
    policy_set_create(&engine, "safe_set", &set);
    
    policy_rule_t *rule = NULL;
    policy_rule_add(set, "block_inject", POLICY_PRIORITY_HIGH, &rule);
    policy_add_condition(rule, MATCH_CONTAINS, "injection");
    policy_add_action(rule, ACTION_BLOCK, 100);
    
    rule_action_t result = policy_evaluate(&engine, "safe_set", "hello world", 11);
    ASSERT_EQ(result, ACTION_ALLOW, "safe content should pass");
    
    policy_engine_destroy(&engine);
    TEST_PASS();
}

/* Main */
int main(int argc, char *argv[])
{
    (void)argc; (void)argv;
    
    printf("\n");
    printf("╔════════════════════════════════════════════════════════════╗\n");
    printf("║         SENTINEL Shield - Policy Engine Tests              ║\n");
    printf("╚════════════════════════════════════════════════════════════╝\n\n");
    
    printf("▶ Policy Engine Lifecycle:\n");
    test_policy_engine_init();
    
    printf("\n▶ Policy Set API:\n");
    test_policy_set_create();
    test_policy_set_duplicate();
    test_policy_set_find();
    test_policy_set_delete();
    
    printf("\n▶ Policy Rule API:\n");
    test_policy_rule_add();
    test_policy_add_condition();
    test_policy_add_action();
    
    printf("\n▶ Policy Evaluation:\n");
    test_policy_evaluate_match();
    test_policy_evaluate_no_match();
    
    printf("\n");
    printf("════════════════════════════════════════════════════════════════\n");
    printf("  Results: %d/%d passed", tests_passed, tests_run);
    if (tests_failed > 0) printf(" (%d failed)", tests_failed);
    printf("\n");
    printf("════════════════════════════════════════════════════════════════\n\n");
    
    return tests_failed > 0 ? 1 : 0;
}
