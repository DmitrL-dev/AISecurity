/*
 * SENTINEL Shield - Unit Tests
 * 
 * Comprehensive test suite
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>

#include "shield_common.h"
#include "shield_zone.h"
#include "shield_rule.h"
#include "shield_blocklist.h"
#include "shield_pattern.h"
#include "shield_mempool.h"
#include "shield_ringbuf.h"
#include "shield_json.h"

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
        printf("FAILED\n    Assertion failed: %s\n    %s:%d\n", \
               #cond, __FILE__, __LINE__); \
        exit(1); \
    } \
} while(0)

/* ===== Zone Tests ===== */

TEST(zone_registry)
{
    zone_registry_t registry;
    ASSERT(zone_registry_init(&registry) == SHIELD_OK);
    
    zone_t *zone = NULL;
    ASSERT(zone_create(&registry, "test", ZONE_TYPE_LLM, &zone) == SHIELD_OK);
    ASSERT(zone != NULL);
    ASSERT(strcmp(zone->name, "test") == 0);
    ASSERT(zone->type == ZONE_TYPE_LLM);
    
    zone_t *found = zone_lookup(&registry, "test");
    ASSERT(found == zone);
    
    ASSERT(zone_lookup(&registry, "nonexistent") == NULL);
    
    ASSERT(zone_delete(&registry, "test") == SHIELD_OK);
    ASSERT(zone_lookup(&registry, "test") == NULL);
    
    zone_registry_destroy(&registry);
}

TEST(zone_acl)
{
    zone_registry_t registry;
    zone_registry_init(&registry);
    
    zone_t *zone = NULL;
    zone_create(&registry, "test", ZONE_TYPE_LLM, &zone);
    
    ASSERT(zone_set_acl(zone, 100, 200) == SHIELD_OK);
    ASSERT(zone->inbound_acl == 100);
    ASSERT(zone->outbound_acl == 200);
    
    zone_registry_destroy(&registry);
}

/* ===== Rule Tests ===== */

TEST(rule_registry)
{
    rule_registry_t registry;
    ASSERT(rule_registry_init(&registry) == SHIELD_OK);
    
    access_list_t *acl = NULL;
    ASSERT(acl_create(&registry, 100, &acl) == SHIELD_OK);
    ASSERT(acl != NULL);
    ASSERT(acl->number == 100);
    
    ASSERT(acl_lookup(&registry, 100) == acl);
    ASSERT(acl_lookup(&registry, 999) == NULL);
    
    rule_registry_destroy(&registry);
}

TEST(rule_add)
{
    rule_registry_t registry;
    rule_registry_init(&registry);
    
    access_list_t *acl = NULL;
    acl_create(&registry, 100, &acl);
    
    ASSERT(rule_add(acl, 10, ACTION_BLOCK, DIRECTION_INPUT, 
                    ZONE_TYPE_LLM, "ignore") == SHIELD_OK);
    ASSERT(acl->rule_count == 1);
    
    ASSERT(rule_add(acl, 20, ACTION_ALLOW, DIRECTION_OUTPUT,
                    ZONE_TYPE_ANY, NULL) == SHIELD_OK);
    ASSERT(acl->rule_count == 2);
    
    /* Duplicate should fail */
    ASSERT(rule_add(acl, 10, ACTION_BLOCK, DIRECTION_INPUT,
                    ZONE_TYPE_LLM, NULL) != SHIELD_OK);
    
    rule_registry_destroy(&registry);
}

/* ===== Blocklist Tests ===== */

TEST(blocklist)
{
    blocklist_t bl;
    ASSERT(blocklist_init(&bl, 1000) == SHIELD_OK);
    
    ASSERT(blocklist_add(&bl, "password", "sensitive") == SHIELD_OK);
    ASSERT(blocklist_add(&bl, "secret_key", "sensitive") == SHIELD_OK);
    
    ASSERT(blocklist_check(&bl, "my password is 123") == true);
    ASSERT(blocklist_check(&bl, "the secret_key here") == true);
    ASSERT(blocklist_check(&bl, "hello world") == false);
    
    blocklist_destroy(&bl);
}

/* ===== Pattern Tests ===== */

TEST(pattern_exact)
{
    compiled_pattern_t *p = NULL;
    ASSERT(pattern_compile("hello", PATTERN_EXACT, false, &p) == SHIELD_OK);
    
    ASSERT(pattern_match(p, "hello", 5) == true);
    ASSERT(pattern_match(p, "Hello", 5) == false);
    ASSERT(pattern_match(p, "hello world", 11) == false);
    
    pattern_free(p);
}

TEST(pattern_contains)
{
    compiled_pattern_t *p = NULL;
    ASSERT(pattern_compile("test", PATTERN_CONTAINS, true, &p) == SHIELD_OK);
    
    ASSERT(pattern_match(p, "this is a test", 14) == true);
    ASSERT(pattern_match(p, "TEST case", 9) == true);
    ASSERT(pattern_match(p, "hello world", 11) == false);
    
    pattern_free(p);
}

TEST(pattern_cache)
{
    pattern_cache_t cache;
    ASSERT(pattern_cache_init(&cache, 10) == SHIELD_OK);
    
    compiled_pattern_t *p1 = pattern_cache_get(&cache, "test1", PATTERN_CONTAINS, false);
    ASSERT(p1 != NULL);
    
    compiled_pattern_t *p2 = pattern_cache_get(&cache, "test1", PATTERN_CONTAINS, false);
    ASSERT(p2 == p1);  /* Should be same cached pattern */
    
    compiled_pattern_t *p3 = pattern_cache_get(&cache, "test2", PATTERN_CONTAINS, false);
    ASSERT(p3 != NULL);
    ASSERT(p3 != p1);
    
    pattern_cache_destroy(&cache);
}

/* ===== Memory Pool Tests ===== */

TEST(mempool)
{
    mem_pool_t pool;
    ASSERT(mempool_init(&pool, 64, 10) == SHIELD_OK);
    
    ASSERT(mempool_available(&pool) == 10);
    
    void *p1 = mempool_alloc(&pool);
    ASSERT(p1 != NULL);
    ASSERT(mempool_available(&pool) == 9);
    
    void *p2 = mempool_alloc(&pool);
    ASSERT(p2 != NULL);
    ASSERT(p2 != p1);
    
    mempool_free(&pool, p1);
    ASSERT(mempool_available(&pool) == 9);
    
    mempool_reset(&pool);
    ASSERT(mempool_available(&pool) == 10);
    
    mempool_destroy(&pool);
}

/* ===== Ring Buffer Tests ===== */

TEST(ringbuf)
{
    ring_buffer_t rb;
    ASSERT(ringbuf_init(&rb, 256) == SHIELD_OK);
    
    ASSERT(ringbuf_is_empty(&rb) == true);
    
    const char *data = "Hello, World!";
    size_t written = ringbuf_write(&rb, data, strlen(data));
    ASSERT(written == strlen(data));
    
    ASSERT(ringbuf_available(&rb) == strlen(data));
    ASSERT(ringbuf_is_empty(&rb) == false);
    
    char buf[64];
    size_t read = ringbuf_read(&rb, buf, sizeof(buf));
    ASSERT(read == strlen(data));
    ASSERT(memcmp(buf, data, read) == 0);
    
    ASSERT(ringbuf_is_empty(&rb) == true);
    
    ringbuf_destroy(&rb);
}

/* ===== JSON Tests ===== */

TEST(json_parse)
{
    const char *json = "{\"name\":\"test\",\"value\":42,\"flag\":true}";
    json_value_t *v = json_parse(json, 0);
    ASSERT(v != NULL);
    ASSERT(json_is_object(v));
    
    json_value_t *name = json_get(v, "name");
    ASSERT(name != NULL);
    ASSERT(json_is_string(name));
    ASSERT(strcmp(json_as_string(name), "test") == 0);
    
    json_value_t *value = json_get(v, "value");
    ASSERT(value != NULL);
    ASSERT(json_is_number(value));
    ASSERT(json_as_number(value) == 42);
    
    json_value_t *flag = json_get(v, "flag");
    ASSERT(flag != NULL);
    ASSERT(json_is_bool(flag));
    ASSERT(json_as_bool(flag) == true);
    
    json_free(v);
}

TEST(json_array)
{
    const char *json = "[1, 2, 3, \"four\"]";
    json_value_t *v = json_parse(json, 0);
    ASSERT(v != NULL);
    ASSERT(json_is_array(v));
    ASSERT(json_array_length(v) == 4);
    
    ASSERT(json_as_number(json_array_get(v, 0)) == 1);
    ASSERT(json_as_number(json_array_get(v, 2)) == 3);
    ASSERT(strcmp(json_as_string(json_array_get(v, 3)), "four") == 0);
    
    json_free(v);
}

/* ===== Main ===== */

int main(void)
{
    printf("\n");
    printf("========================================\n");
    printf("  SENTINEL Shield Unit Tests\n");
    printf("========================================\n\n");
    
    /* Zone tests */
    printf("[ZONE]\n");
    RUN_TEST(zone_registry);
    RUN_TEST(zone_acl);
    printf("\n");
    
    /* Rule tests */
    printf("[RULE]\n");
    RUN_TEST(rule_registry);
    RUN_TEST(rule_add);
    printf("\n");
    
    /* Blocklist tests */
    printf("[BLOCKLIST]\n");
    RUN_TEST(blocklist);
    printf("\n");
    
    /* Pattern tests */
    printf("[PATTERN]\n");
    RUN_TEST(pattern_exact);
    RUN_TEST(pattern_contains);
    RUN_TEST(pattern_cache);
    printf("\n");
    
    /* Memory pool tests */
    printf("[MEMPOOL]\n");
    RUN_TEST(mempool);
    printf("\n");
    
    /* Ring buffer tests */
    printf("[RINGBUF]\n");
    RUN_TEST(ringbuf);
    printf("\n");
    
    /* JSON tests */
    printf("[JSON]\n");
    RUN_TEST(json_parse);
    RUN_TEST(json_array);
    printf("\n");
    
    printf("========================================\n");
    printf("  Results: %d/%d tests passed\n", tests_passed, tests_run);
    printf("========================================\n\n");
    
    return (tests_passed == tests_run) ? 0 : 1;
}
