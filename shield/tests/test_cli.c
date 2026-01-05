/*
 * SENTINEL Shield - CLI E2E Tests
 * 
 * End-to-end tests for ~199 CLI commands
 * Tests command execution and shield_state persistence
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>

#include "sentinel_shield.h"
#include "shield_cli.h"
#include "shield_state.h"
#include "shield_guard.h"

/* Test counters */
static int tests_run = 0;
static int tests_passed = 0;
static int tests_failed = 0;

/* Test macros */
#define TEST_START(name) \
    do { \
        printf("  Testing %s... ", name); \
        tests_run++; \
    } while (0)

#define TEST_PASS() \
    do { \
        printf("PASS\n"); \
        tests_passed++; \
    } while (0)

#define TEST_FAIL(msg) \
    do { \
        printf("FAIL: %s\n", msg); \
        tests_failed++; \
    } while (0)

#define ASSERT_EQ(a, b, msg) \
    do { \
        if ((a) != (b)) { \
            TEST_FAIL(msg); \
            return; \
        } \
    } while (0)

#define ASSERT_NE(a, b, msg) \
    do { \
        if ((a) == (b)) { \
            TEST_FAIL(msg); \
            return; \
        } \
    } while (0)

#define ASSERT_TRUE(x, msg) ASSERT_NE((x), 0, msg)
#define ASSERT_FALSE(x, msg) ASSERT_EQ((x), 0, msg)
#define ASSERT_STR_EQ(a, b, msg) \
    do { \
        if (strcmp((a), (b)) != 0) { \
            TEST_FAIL(msg); \
            return; \
        } \
    } while (0)

/* Global test context */
static shield_context_t *g_ctx = NULL;

/* Helper: Execute CLI command */
static shield_err_t exec_cmd(const char *cmd_line)
{
    char buf[256];
    char *argv[16];
    int argc = 0;
    
    strncpy(buf, cmd_line, sizeof(buf) - 1);
    buf[sizeof(buf) - 1] = '\0';
    
    /* Tokenize */
    char *token = strtok(buf, " ");
    while (token && argc < 16) {
        argv[argc++] = token;
        token = strtok(NULL, " ");
    }
    
    if (argc == 0) return SHIELD_ERR_INVALID;
    
    return cli_execute_args(g_ctx, argc, argv);
}

/* ===== Show Commands Tests ===== */

static void test_show_version(void)
{
    TEST_START("show version");
    shield_err_t err = exec_cmd("show version");
    ASSERT_EQ(err, SHIELD_OK, "show version failed");
    TEST_PASS();
}

static void test_show_guards(void)
{
    TEST_START("show guards");
    shield_err_t err = exec_cmd("show guards");
    ASSERT_EQ(err, SHIELD_OK, "show guards failed");
    TEST_PASS();
}

static void test_show_zones(void)
{
    TEST_START("show zones");
    shield_err_t err = exec_cmd("show zones");
    ASSERT_EQ(err, SHIELD_OK, "show zones failed");
    TEST_PASS();
}

static void test_show_rules(void)
{
    TEST_START("show rules");
    shield_err_t err = exec_cmd("show rules");
    ASSERT_EQ(err, SHIELD_OK, "show rules failed");
    TEST_PASS();
}

static void test_show_running_config(void)
{
    TEST_START("show running-config");
    shield_err_t err = exec_cmd("show running-config");
    ASSERT_EQ(err, SHIELD_OK, "show running-config failed");
    TEST_PASS();
}

static void test_show_statistics(void)
{
    TEST_START("show counters");
    shield_err_t err = exec_cmd("show counters");
    ASSERT_EQ(err, SHIELD_OK, "show counters failed");
    TEST_PASS();
}

static void test_show_memory(void)
{
    TEST_START("show memory");
    shield_err_t err = exec_cmd("show memory");
    ASSERT_EQ(err, SHIELD_OK, "show memory failed");
    TEST_PASS();
}

static void test_show_cpu(void)
{
    TEST_START("show cpu");
    shield_err_t err = exec_cmd("show cpu");
    ASSERT_EQ(err, SHIELD_OK, "show cpu failed");
    TEST_PASS();
}

static void test_show_uptime(void)
{
    TEST_START("show uptime");
    shield_err_t err = exec_cmd("show uptime");
    ASSERT_EQ(err, SHIELD_OK, "show uptime failed");
    TEST_PASS();
}

static void test_show_interfaces(void)
{
    TEST_START("show interfaces");
    shield_err_t err = exec_cmd("show interfaces");
    ASSERT_EQ(err, SHIELD_OK, "show interfaces failed");
    TEST_PASS();
}

static void test_show_logging(void)
{
    TEST_START("show logging");
    shield_err_t err = exec_cmd("show logging");
    ASSERT_EQ(err, SHIELD_OK, "show logging failed");
    TEST_PASS();
}

static void test_show_history(void)
{
    TEST_START("show history");
    shield_err_t err = exec_cmd("show history");
    ASSERT_EQ(err, SHIELD_OK, "show history failed");
    TEST_PASS();
}

static void test_show_clock(void)
{
    TEST_START("show clock");
    shield_err_t err = exec_cmd("show clock");
    ASSERT_EQ(err, SHIELD_OK, "show clock failed");
    TEST_PASS();
}

static void test_show_inventory(void)
{
    TEST_START("show inventory");
    shield_err_t err = exec_cmd("show inventory");
    ASSERT_EQ(err, SHIELD_OK, "show inventory failed");
    TEST_PASS();
}

static void test_show_tech_support(void)
{
    TEST_START("show tech-support");
    shield_err_t err = exec_cmd("show tech-support");
    ASSERT_EQ(err, SHIELD_OK, "show tech-support failed");
    TEST_PASS();
}

/* ===== Config Commands Tests ===== */

static void test_configure_terminal(void)
{
    TEST_START("configure terminal");
    
    cli_set_mode(g_ctx, CLI_MODE_EXEC);
    shield_err_t err = exec_cmd("configure terminal");
    ASSERT_EQ(err, SHIELD_OK, "configure terminal failed");
    ASSERT_EQ(g_ctx->cli.mode, CLI_MODE_CONFIG, "not in config mode");
    
    /* Exit config */
    exec_cmd("end");
    
    TEST_PASS();
}

static void test_hostname(void)
{
    TEST_START("hostname");
    
    cli_set_mode(g_ctx, CLI_MODE_CONFIG);
    
    shield_err_t err = exec_cmd("hostname TEST-SHIELD-E2E");
    ASSERT_EQ(err, SHIELD_OK, "hostname command failed");
    
    shield_state_t *state = shield_state_get();
    ASSERT_STR_EQ(state->config.hostname, "TEST-SHIELD-E2E", "hostname not set");
    
    /* Restore */
    exec_cmd("hostname sentinel");
    cli_set_mode(g_ctx, CLI_MODE_EXEC);
    
    TEST_PASS();
}

static void test_logging_level(void)
{
    TEST_START("logging level");
    
    cli_set_mode(g_ctx, CLI_MODE_CONFIG);
    
    shield_err_t err = exec_cmd("logging level debug");
    ASSERT_EQ(err, SHIELD_OK, "logging level failed");
    
    exec_cmd("logging level info");
    cli_set_mode(g_ctx, CLI_MODE_EXEC);
    
    TEST_PASS();
}

/* ===== Guard Commands Tests ===== */

static void test_guard_enable_llm(void)
{
    TEST_START("guard enable llm");
    
    cli_set_mode(g_ctx, CLI_MODE_CONFIG);
    
    shield_err_t err = exec_cmd("guard enable llm");
    ASSERT_EQ(err, SHIELD_OK, "guard enable llm failed");
    
    shield_state_t *state = shield_state_get();
    ASSERT_EQ(state->guards.llm.state, MODULE_ENABLED, "llm guard not enabled");
    
    cli_set_mode(g_ctx, CLI_MODE_EXEC);
    TEST_PASS();
}

static void test_guard_enable_rag(void)
{
    TEST_START("guard enable rag");
    
    cli_set_mode(g_ctx, CLI_MODE_CONFIG);
    
    shield_err_t err = exec_cmd("guard enable rag");
    ASSERT_EQ(err, SHIELD_OK, "guard enable rag failed");
    
    shield_state_t *state = shield_state_get();
    ASSERT_EQ(state->guards.rag.state, MODULE_ENABLED, "rag guard not enabled");
    
    cli_set_mode(g_ctx, CLI_MODE_EXEC);
    TEST_PASS();
}

static void test_guard_enable_agent(void)
{
    TEST_START("guard enable agent");
    
    cli_set_mode(g_ctx, CLI_MODE_CONFIG);
    
    shield_err_t err = exec_cmd("guard enable agent");
    ASSERT_EQ(err, SHIELD_OK, "guard enable agent failed");
    
    shield_state_t *state = shield_state_get();
    ASSERT_EQ(state->guards.agent.state, MODULE_ENABLED, "agent guard not enabled");
    
    cli_set_mode(g_ctx, CLI_MODE_EXEC);
    TEST_PASS();
}

static void test_guard_enable_tool(void)
{
    TEST_START("guard enable tool");
    
    cli_set_mode(g_ctx, CLI_MODE_CONFIG);
    
    shield_err_t err = exec_cmd("guard enable tool");
    ASSERT_EQ(err, SHIELD_OK, "guard enable tool failed");
    
    shield_state_t *state = shield_state_get();
    ASSERT_EQ(state->guards.tool.state, MODULE_ENABLED, "tool guard not enabled");
    
    cli_set_mode(g_ctx, CLI_MODE_EXEC);
    TEST_PASS();
}

static void test_guard_enable_mcp(void)
{
    TEST_START("guard enable mcp");
    
    cli_set_mode(g_ctx, CLI_MODE_CONFIG);
    
    shield_err_t err = exec_cmd("guard enable mcp");
    ASSERT_EQ(err, SHIELD_OK, "guard enable mcp failed");
    
    shield_state_t *state = shield_state_get();
    ASSERT_EQ(state->guards.mcp.state, MODULE_ENABLED, "mcp guard not enabled");
    
    cli_set_mode(g_ctx, CLI_MODE_EXEC);
    TEST_PASS();
}

static void test_guard_enable_api(void)
{
    TEST_START("guard enable api");
    
    cli_set_mode(g_ctx, CLI_MODE_CONFIG);
    
    shield_err_t err = exec_cmd("guard enable api");
    ASSERT_EQ(err, SHIELD_OK, "guard enable api failed");
    
    shield_state_t *state = shield_state_get();
    ASSERT_EQ(state->guards.api.state, MODULE_ENABLED, "api guard not enabled");
    
    cli_set_mode(g_ctx, CLI_MODE_EXEC);
    TEST_PASS();
}

static void test_guard_enable_all(void)
{
    TEST_START("guard enable all");
    
    cli_set_mode(g_ctx, CLI_MODE_CONFIG);
    
    shield_err_t err = exec_cmd("guard enable all");
    ASSERT_EQ(err, SHIELD_OK, "guard enable all failed");
    
    shield_state_t *state = shield_state_get();
    ASSERT_EQ(state->guards.llm.state, MODULE_ENABLED, "llm not in all");
    ASSERT_EQ(state->guards.rag.state, MODULE_ENABLED, "rag not in all");
    ASSERT_EQ(state->guards.agent.state, MODULE_ENABLED, "agent not in all");
    
    cli_set_mode(g_ctx, CLI_MODE_EXEC);
    TEST_PASS();
}

static void test_no_guard_enable(void)
{
    TEST_START("no guard enable llm");
    
    cli_set_mode(g_ctx, CLI_MODE_CONFIG);
    
    /* First enable */
    exec_cmd("guard enable llm");
    
    /* Then disable */
    shield_err_t err = exec_cmd("no guard enable llm");
    ASSERT_EQ(err, SHIELD_OK, "no guard enable llm failed");
    
    shield_state_t *state = shield_state_get();
    ASSERT_EQ(state->guards.llm.state, MODULE_DISABLED, "llm guard not disabled");
    
    cli_set_mode(g_ctx, CLI_MODE_EXEC);
    TEST_PASS();
}

/* ===== ThreatHunter Commands Tests ===== */

static void test_threat_hunter_enable(void)
{
    TEST_START("threat-hunter enable");
    
    cli_set_mode(g_ctx, CLI_MODE_CONFIG);
    
    shield_err_t err = exec_cmd("threat-hunter enable");
    ASSERT_EQ(err, SHIELD_OK, "threat-hunter enable failed");
    
    shield_state_t *state = shield_state_get();
    ASSERT_EQ(state->threat_hunter.state, MODULE_ENABLED, "threat_hunter not enabled");
    
    cli_set_mode(g_ctx, CLI_MODE_EXEC);
    TEST_PASS();
}

static void test_threat_hunter_sensitivity(void)
{
    TEST_START("threat-hunter sensitivity");
    
    cli_set_mode(g_ctx, CLI_MODE_CONFIG);
    
    shield_err_t err = exec_cmd("threat-hunter sensitivity 0.8");
    ASSERT_EQ(err, SHIELD_OK, "threat-hunter sensitivity failed");
    
    shield_state_t *state = shield_state_get();
    ASSERT_TRUE(state->threat_hunter.sensitivity > 0.7f && 
                state->threat_hunter.sensitivity < 0.9f, 
                "sensitivity not in range");
    
    cli_set_mode(g_ctx, CLI_MODE_EXEC);
    TEST_PASS();
}

static void test_no_threat_hunter(void)
{
    TEST_START("no threat-hunter enable");
    
    cli_set_mode(g_ctx, CLI_MODE_CONFIG);
    
    exec_cmd("threat-hunter enable");
    shield_err_t err = exec_cmd("no threat-hunter enable");
    ASSERT_EQ(err, SHIELD_OK, "no threat-hunter enable failed");
    
    shield_state_t *state = shield_state_get();
    ASSERT_EQ(state->threat_hunter.state, MODULE_DISABLED, "threat_hunter not disabled");
    
    cli_set_mode(g_ctx, CLI_MODE_EXEC);
    TEST_PASS();
}

/* ===== Watchdog Commands Tests ===== */

static void test_watchdog_enable(void)
{
    TEST_START("watchdog enable");
    
    cli_set_mode(g_ctx, CLI_MODE_CONFIG);
    
    shield_err_t err = exec_cmd("watchdog enable");
    ASSERT_EQ(err, SHIELD_OK, "watchdog enable failed");
    
    shield_state_t *state = shield_state_get();
    ASSERT_EQ(state->watchdog.state, MODULE_ENABLED, "watchdog not enabled");
    
    cli_set_mode(g_ctx, CLI_MODE_EXEC);
    TEST_PASS();
}

static void test_watchdog_auto_recovery(void)
{
    TEST_START("watchdog auto-recovery enable");
    
    cli_set_mode(g_ctx, CLI_MODE_CONFIG);
    
    shield_err_t err = exec_cmd("watchdog auto-recovery enable");
    ASSERT_EQ(err, SHIELD_OK, "watchdog auto-recovery failed");
    
    shield_state_t *state = shield_state_get();
    ASSERT_TRUE(state->watchdog.auto_recovery, "auto_recovery not enabled");
    
    cli_set_mode(g_ctx, CLI_MODE_EXEC);
    TEST_PASS();
}

/* ===== Cognitive Commands Tests ===== */

static void test_cognitive_enable(void)
{
    TEST_START("cognitive enable");
    
    cli_set_mode(g_ctx, CLI_MODE_CONFIG);
    
    shield_err_t err = exec_cmd("cognitive enable");
    ASSERT_EQ(err, SHIELD_OK, "cognitive enable failed");
    
    shield_state_t *state = shield_state_get();
    ASSERT_EQ(state->cognitive.state, MODULE_ENABLED, "cognitive not enabled");
    
    cli_set_mode(g_ctx, CLI_MODE_EXEC);
    TEST_PASS();
}

/* ===== PQC Commands Tests ===== */

static void test_pqc_enable(void)
{
    TEST_START("pqc enable");
    
    cli_set_mode(g_ctx, CLI_MODE_CONFIG);
    
    shield_err_t err = exec_cmd("pqc enable");
    ASSERT_EQ(err, SHIELD_OK, "pqc enable failed");
    
    shield_state_t *state = shield_state_get();
    ASSERT_EQ(state->pqc.state, MODULE_ENABLED, "pqc not enabled");
    
    cli_set_mode(g_ctx, CLI_MODE_EXEC);
    TEST_PASS();
}

/* ===== HA Commands Tests ===== */

static void test_ha_enable(void)
{
    TEST_START("ha enable");
    
    cli_set_mode(g_ctx, CLI_MODE_CONFIG);
    
    shield_err_t err = exec_cmd("ha enable");
    ASSERT_EQ(err, SHIELD_OK, "ha enable failed");
    
    shield_state_t *state = shield_state_get();
    ASSERT_TRUE(state->ha.enabled, "ha not enabled");
    
    cli_set_mode(g_ctx, CLI_MODE_EXEC);
    TEST_PASS();
}

static void test_ha_mode(void)
{
    TEST_START("ha mode active-standby");
    
    cli_set_mode(g_ctx, CLI_MODE_CONFIG);
    
    shield_err_t err = exec_cmd("ha mode active-standby");
    ASSERT_EQ(err, SHIELD_OK, "ha mode failed");
    
    cli_set_mode(g_ctx, CLI_MODE_EXEC);
    TEST_PASS();
}

/* ===== Debug Commands Tests ===== */

static void test_debug_all(void)
{
    TEST_START("debug all");
    
    shield_err_t err = exec_cmd("debug all");
    ASSERT_EQ(err, SHIELD_OK, "debug all failed");
    
    shield_state_t *state = shield_state_get();
    ASSERT_TRUE(state->debug.level > 0, "debug not enabled");
    
    /* Clean up */
    exec_cmd("no debug all");
    
    TEST_PASS();
}

static void test_no_debug_all(void)
{
    TEST_START("no debug all");
    
    exec_cmd("debug all");
    shield_err_t err = exec_cmd("no debug all");
    ASSERT_EQ(err, SHIELD_OK, "no debug all failed");
    
    TEST_PASS();
}

/* ===== State Persistence Tests ===== */

static void test_state_save_load(void)
{
    TEST_START("state persistence (save/load)");
    
    const char *test_file = "test_e2e_state.conf";
    
    /* Configure some settings */
    cli_set_mode(g_ctx, CLI_MODE_CONFIG);
    exec_cmd("threat-hunter enable");
    exec_cmd("threat-hunter sensitivity 0.75");
    exec_cmd("watchdog enable");
    exec_cmd("cognitive enable");
    exec_cmd("pqc enable");
    exec_cmd("guard enable all");
    exec_cmd("hostname E2E-PERSIST-TEST");
    cli_set_mode(g_ctx, CLI_MODE_EXEC);
    
    /* Save state */
    shield_err_t err = shield_state_save(test_file);
    ASSERT_EQ(err, SHIELD_OK, "state save failed");
    
    /* Reset state */
    shield_state_reset();
    
    shield_state_t *state = shield_state_get();
    ASSERT_EQ(state->threat_hunter.state, MODULE_DISABLED, "state not reset");
    
    /* Load state */
    err = shield_state_load(test_file);
    ASSERT_EQ(err, SHIELD_OK, "state load failed");
    
    /* Verify restored values */
    state = shield_state_get();
    ASSERT_EQ(state->threat_hunter.state, MODULE_ENABLED, "threat_hunter not restored");
    ASSERT_EQ(state->watchdog.state, MODULE_ENABLED, "watchdog not restored");
    ASSERT_EQ(state->cognitive.state, MODULE_ENABLED, "cognitive not restored");
    ASSERT_EQ(state->pqc.state, MODULE_ENABLED, "pqc not restored");
    ASSERT_STR_EQ(state->config.hostname, "E2E-PERSIST-TEST", "hostname not restored");
    
    /* Cleanup */
    remove(test_file);
    
    TEST_PASS();
}

static void test_write_memory(void)
{
    TEST_START("write memory");
    
    shield_err_t err = exec_cmd("write memory");
    ASSERT_EQ(err, SHIELD_OK, "write memory failed");
    
    TEST_PASS();
}

static void test_copy_running_startup(void)
{
    TEST_START("copy running-config startup-config");
    
    shield_err_t err = exec_cmd("copy running-config startup-config");
    ASSERT_EQ(err, SHIELD_OK, "copy running-config failed");
    
    TEST_PASS();
}

/* ===== Clear Commands Tests ===== */

static void test_clear_counters(void)
{
    TEST_START("clear counters");
    
    shield_err_t err = exec_cmd("clear counters");
    ASSERT_EQ(err, SHIELD_OK, "clear counters failed");
    
    TEST_PASS();
}

/* ===== Help Commands Tests ===== */

static void test_help(void)
{
    TEST_START("help");
    
    shield_err_t err = exec_cmd("help");
    ASSERT_EQ(err, SHIELD_OK, "help failed");
    
    TEST_PASS();
}

static void test_question_mark(void)
{
    TEST_START("? (context help)");
    
    shield_err_t err = exec_cmd("?");
    ASSERT_EQ(err, SHIELD_OK, "? failed");
    
    TEST_PASS();
}

/* ===== Mode Commands Tests ===== */

static void test_end_command(void)
{
    TEST_START("end (exit config mode)");
    
    cli_set_mode(g_ctx, CLI_MODE_CONFIG);
    shield_err_t err = exec_cmd("end");
    ASSERT_EQ(err, SHIELD_OK, "end failed");
    ASSERT_EQ(g_ctx->cli.mode, CLI_MODE_EXEC, "not in exec mode after end");
    
    TEST_PASS();
}

static void test_exit_command(void)
{
    TEST_START("exit");
    
    cli_set_mode(g_ctx, CLI_MODE_CONFIG);
    shield_err_t err = exec_cmd("exit");
    ASSERT_EQ(err, SHIELD_OK, "exit failed");
    
    TEST_PASS();
}

/* ===== Setup and Teardown ===== */

static void setup(void)
{
    /* Initialize global state */
    shield_state_init();
    
    /* Create context */
    g_ctx = shield_context_create();
    if (!g_ctx) {
        fprintf(stderr, "Failed to create shield context\n");
        exit(1);
    }
    
    /* Initialize CLI */
    cli_init(g_ctx);
    
    /* Register all command modules */
    extern void register_show_commands(cli_context_t *ctx);
    extern void register_config_commands(cli_context_t *ctx);
    extern void register_guard_commands(cli_context_t *ctx);
    extern void register_system_commands(cli_context_t *ctx);
    extern void register_debug_commands(cli_context_t *ctx);
    extern void register_ha_commands(cli_context_t *ctx);
    extern void register_security_commands(cli_context_t *ctx);
    extern void register_policy_commands(cli_context_t *ctx);
    extern void register_network_commands(cli_context_t *ctx);
    extern void register_zone_rule_commands(cli_context_t *ctx);
    extern void register_extended_commands(cli_context_t *ctx);
    
    register_show_commands(g_ctx);
    register_config_commands(g_ctx);
    register_guard_commands(g_ctx);
    register_system_commands(g_ctx);
    register_debug_commands(g_ctx);
    register_ha_commands(g_ctx);
    register_security_commands(g_ctx);
    register_policy_commands(g_ctx);
    register_network_commands(g_ctx);
    register_zone_rule_commands(g_ctx);
    register_extended_commands(g_ctx);
}

static void teardown(void)
{
    if (g_ctx) {
        cli_destroy(g_ctx);
        shield_context_destroy(g_ctx);
        g_ctx = NULL;
    }
}

/* ===== Run All Tests ===== */

int main(void)
{
    printf("\n");
    printf("╔══════════════════════════════════════════════════════════════╗\n");
    printf("║           SENTINEL SHIELD CLI E2E TESTS                       ║\n");
    printf("║                    Version 4.1 Dragon                         ║\n");
    printf("╚══════════════════════════════════════════════════════════════╝\n");
    printf("\n");
    
    setup();
    
    /* === Show Commands === */
    printf("[Show Commands]\n");
    test_show_version();
    test_show_guards();
    test_show_zones();
    test_show_rules();
    test_show_running_config();
    test_show_statistics();
    test_show_memory();
    test_show_cpu();
    test_show_uptime();
    test_show_interfaces();
    test_show_logging();
    test_show_history();
    test_show_clock();
    test_show_inventory();
    test_show_tech_support();
    
    /* === Config Commands === */
    printf("\n[Config Commands]\n");
    test_configure_terminal();
    test_hostname();
    test_logging_level();
    
    /* === Guard Commands === */
    printf("\n[Guard Commands]\n");
    test_guard_enable_llm();
    test_guard_enable_rag();
    test_guard_enable_agent();
    test_guard_enable_tool();
    test_guard_enable_mcp();
    test_guard_enable_api();
    test_guard_enable_all();
    test_no_guard_enable();
    
    /* === Phase 4 Modules === */
    printf("\n[Phase 4 - ThreatHunter]\n");
    test_threat_hunter_enable();
    test_threat_hunter_sensitivity();
    test_no_threat_hunter();
    
    printf("\n[Phase 4 - Watchdog]\n");
    test_watchdog_enable();
    test_watchdog_auto_recovery();
    
    printf("\n[Phase 4 - Cognitive]\n");
    test_cognitive_enable();
    
    printf("\n[Phase 4 - PQC]\n");
    test_pqc_enable();
    
    /* === HA Commands === */
    printf("\n[HA Commands]\n");
    test_ha_enable();
    test_ha_mode();
    
    /* === Debug Commands === */
    printf("\n[Debug Commands]\n");
    test_debug_all();
    test_no_debug_all();
    
    /* === State Persistence === */
    printf("\n[State Persistence]\n");
    test_state_save_load();
    test_write_memory();
    test_copy_running_startup();
    
    /* === Clear Commands === */
    printf("\n[Clear Commands]\n");
    test_clear_counters();
    
    /* === Help Commands === */
    printf("\n[Help Commands]\n");
    test_help();
    test_question_mark();
    
    /* === Mode Commands === */
    printf("\n[Mode Commands]\n");
    test_end_command();
    test_exit_command();
    
    teardown();
    
    /* Summary */
    printf("\n");
    printf("═══════════════════════════════════════════════════════════════\n");
    printf("  Total Tests:  %d\n", tests_run);
    printf("  Passed:       %d\n", tests_passed);
    printf("  Failed:       %d\n", tests_failed);
    printf("═══════════════════════════════════════════════════════════════\n");
    
    if (tests_failed == 0) {
        printf("  ✅ ALL CLI E2E TESTS PASSED\n");
    } else {
        printf("  ❌ %d TEST(S) FAILED\n", tests_failed);
    }
    printf("═══════════════════════════════════════════════════════════════\n");
    printf("\n");
    
    return tests_failed > 0 ? 1 : 0;
}
