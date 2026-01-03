/*
 * SENTINEL IMMUNE — Hive Test Suite
 * 
 * Tests for Hive server components.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>

/* Include Hive headers */
#include "../include/hive.h"

/* ==================== Test Utilities ==================== */

static int tests_passed = 0;
static int tests_failed = 0;

#define TEST(name) \
    printf("Test: %s... ", name); \
    fflush(stdout)

#define PASS() \
    do { \
        printf("PASSED\n"); \
        tests_passed++; \
    } while (0)

#define FAIL(msg) \
    do { \
        printf("FAILED: %s\n", msg); \
        tests_failed++; \
    } while (0)

#define ASSERT(cond, msg) \
    if (!(cond)) { FAIL(msg); return; } else { }

/* ==================== Hive Core Tests ==================== */

static void
test_hive_init(void)
{
    TEST("Hive initialization");
    
    immune_hive_t hive;
    int ret = hive_init(&hive, "./test_hive_data");
    
    ASSERT(ret == 0, "hive_init failed");
    ASSERT(hive.threats != NULL, "threats not allocated");
    ASSERT(hive.signatures != NULL, "signatures not allocated");
    
    hive_shutdown(&hive);
    PASS();
}

static void
test_agent_registration(void)
{
    TEST("Agent registration");
    
    immune_hive_t hive;
    hive_init(&hive, "./test_hive_data");
    
    uint32_t id1 = hive_register_agent(&hive, "host1", "192.168.1.1", 
                                       "Linux", "0.1.0");
    uint32_t id2 = hive_register_agent(&hive, "host2", "192.168.1.2",
                                       "DragonFlyBSD", "0.1.0");
    
    ASSERT(id1 > 0, "first registration failed");
    ASSERT(id2 > 0, "second registration failed");
    ASSERT(id1 != id2, "duplicate IDs");
    
    immune_agent_t *agent = hive_get_agent(&hive, id1);
    ASSERT(agent != NULL, "agent not found");
    ASSERT(strcmp(agent->hostname, "host1") == 0, "hostname mismatch");
    ASSERT(agent->status == AGENT_STATUS_ONLINE, "wrong status");
    
    hive_shutdown(&hive);
    PASS();
}

static void
test_threat_handling(void)
{
    TEST("Threat handling");
    
    immune_hive_t hive;
    hive_init(&hive, "./test_hive_data");
    
    uint32_t agent_id = hive_register_agent(&hive, "test-host", "10.0.0.1",
                                            "Linux", "0.1.0");
    
    uint64_t event1 = hive_receive_threat(&hive, agent_id, THREAT_LEVEL_HIGH,
                                          THREAT_TYPE_JAILBREAK, 
                                          "ignore all previous");
    
    ASSERT(event1 > 0, "threat not logged");
    ASSERT(hive.stats.threats_total == 1, "threat count wrong");
    
    immune_agent_t *agent = hive_get_agent(&hive, agent_id);
    ASSERT(agent->threats_detected == 1, "agent threat count wrong");
    
    uint64_t event2 = hive_receive_threat(&hive, agent_id, THREAT_LEVEL_CRITICAL,
                                          THREAT_TYPE_MALWARE,
                                          "meterpreter");
    
    ASSERT(event2 > event1, "event IDs not sequential");
    ASSERT(hive.stats.threats_total == 2, "threat count wrong");
    
    hive_shutdown(&hive);
    PASS();
}

static void
test_heartbeat(void)
{
    TEST("Agent heartbeat");
    
    immune_hive_t hive;
    hive_init(&hive, "./test_hive_data");
    
    uint32_t agent_id = hive_register_agent(&hive, "heartbeat-test", "10.0.0.5",
                                            "FreeBSD", "0.1.0");
    
    /* Mark as offline */
    hive_agent_offline(&hive, agent_id);
    
    immune_agent_t *agent = hive_get_agent(&hive, agent_id);
    ASSERT(agent->status == AGENT_STATUS_OFFLINE, "not offline");
    
    /* Send heartbeat */
    hive_agent_heartbeat(&hive, agent_id);
    
    agent = hive_get_agent(&hive, agent_id);
    ASSERT(agent->status == AGENT_STATUS_ONLINE, "not back online");
    
    hive_shutdown(&hive);
    PASS();
}

static void
test_signatures(void)
{
    TEST("Herd signatures");
    
    immune_hive_t hive;
    hive_init(&hive, "./test_hive_data");
    
    uint64_t sig1 = hive_add_signature(&hive, "pattern_one",
                                       THREAT_TYPE_JAILBREAK,
                                       THREAT_LEVEL_HIGH, 0);
    
    ASSERT(sig1 > 0, "signature not added");
    ASSERT(hive.stats.signatures_count == 1, "signature count wrong");
    
    uint64_t sig2 = hive_add_signature(&hive, "pattern_two",
                                       THREAT_TYPE_INJECTION,
                                       THREAT_LEVEL_CRITICAL, 0);
    
    ASSERT(sig2 > sig1, "signature IDs not sequential");
    
    hive_shutdown(&hive);
    PASS();
}

static void
test_persistence(void)
{
    TEST("State persistence");
    
    immune_hive_t hive1;
    hive_init(&hive1, "./test_hive_data");
    
    uint32_t agent_id = hive_register_agent(&hive1, "persist-host", "10.0.0.10",
                                            "Linux", "0.1.0");
    
    hive_add_signature(&hive1, "persistent_pattern",
                       THREAT_TYPE_MALWARE, THREAT_LEVEL_HIGH, 0);
    
    /* Save and shutdown */
    hive_save_state(&hive1);
    hive_shutdown(&hive1);
    
    /* Reload */
    immune_hive_t hive2;
    hive_init(&hive2, "./test_hive_data");
    
    ASSERT(hive2.agent_count >= 1, "agents not persisted");
    ASSERT(hive2.sig_count >= 1, "signatures not persisted");
    
    hive_shutdown(&hive2);
    PASS();
}

static void
test_correlation(void)
{
    TEST("Threat correlation");
    
    immune_hive_t hive;
    hive_init(&hive, "./test_hive_data");
    
    threat_event_t event;
    
    event.level = THREAT_LEVEL_LOW;
    ASSERT(hive_correlate_threat(&hive, &event) == RESPONSE_LOG, 
           "LOW should LOG");
    
    event.level = THREAT_LEVEL_MEDIUM;
    ASSERT(hive_correlate_threat(&hive, &event) == RESPONSE_ALERT,
           "MEDIUM should ALERT");
    
    event.level = THREAT_LEVEL_HIGH;
    ASSERT(hive_correlate_threat(&hive, &event) == RESPONSE_BLOCK,
           "HIGH should BLOCK");
    
    event.level = THREAT_LEVEL_CRITICAL;
    ASSERT(hive_correlate_threat(&hive, &event) == RESPONSE_ISOLATE,
           "CRITICAL should ISOLATE");
    
    hive_shutdown(&hive);
    PASS();
}

static void
test_stats(void)
{
    TEST("Statistics");
    
    immune_hive_t hive;
    hive_init(&hive, "./test_hive_data");
    
    /* Register some agents */
    hive_register_agent(&hive, "stat1", "10.0.0.1", "Linux", "0.1.0");
    hive_register_agent(&hive, "stat2", "10.0.0.2", "Linux", "0.1.0");
    hive_register_agent(&hive, "stat3", "10.0.0.3", "Linux", "0.1.0");
    
    hive_stats_t stats;
    hive_get_stats(&hive, &stats);
    
    ASSERT(stats.agents_total == 3, "agent count wrong");
    ASSERT(stats.agents_online == 3, "online count wrong");
    
    hive_shutdown(&hive);
    PASS();
}

/* ==================== Main ==================== */

int
main(int argc, char *argv[])
{
    (void)argc;
    (void)argv;
    
    printf("\n=== SENTINEL IMMUNE Hive Tests ===\n\n");
    
    /* Run tests */
    test_hive_init();
    test_agent_registration();
    test_threat_handling();
    test_heartbeat();
    test_signatures();
    test_persistence();
    test_correlation();
    test_stats();
    
    /* Summary */
    printf("\n=== Results ===\n");
    printf("Passed: %d\n", tests_passed);
    printf("Failed: %d\n", tests_failed);
    printf("Total:  %d\n", tests_passed + tests_failed);
    printf("================\n\n");
    
    /* Cleanup test data */
    system("rm -rf ./test_hive_data 2>/dev/null");
    
    return tests_failed > 0 ? 1 : 0;
}
