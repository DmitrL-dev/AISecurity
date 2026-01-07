/**
 * @file test_safe_memory.c
 * @brief Unit tests for safe_memory functions
 * 
 * Compile with sanitizers:
 *   gcc -fsanitize=address,undefined -g test_safe_memory.c ../common/src/safe_memory.c \
 *       -I../common/include -o test_safe_memory
 * 
 * @author SENTINEL R&D
 * @date 2026-01-07
 */

#include "safe_memory.h"
#include <stdio.h>
#include <string.h>
#include <assert.h>

/* Test counters */
static int tests_passed = 0;
static int tests_failed = 0;

#define TEST(name) \
    do { \
        printf("  Testing: %s... ", #name); \
        fflush(stdout); \
    } while(0)

#define PASS() \
    do { \
        printf("PASS\n"); \
        tests_passed++; \
    } while(0)

#define FAIL(msg) \
    do { \
        printf("FAIL: %s\n", msg); \
        tests_failed++; \
    } while(0)

#define ASSERT(cond, msg) \
    do { \
        if (!(cond)) { \
            FAIL(msg); \
            return; \
        } \
    } while(0)

/* ============================================================================
 * Allocation Tests
 * ============================================================================ */

static void test_safe_alloc_basic(void) {
    TEST(safe_alloc_basic);
    
    void* ptr = safe_alloc(100);
    ASSERT(ptr != NULL, "allocation failed");
    
    /* Check zero-initialization */
    unsigned char* bytes = (unsigned char*)ptr;
    for (size_t i = 0; i < 100; i++) {
        ASSERT(bytes[i] == 0, "memory not zero-initialized");
    }
    
    SAFE_FREE(ptr);
    ASSERT(ptr == NULL, "pointer not nullified after free");
    
    PASS();
}

static void test_safe_alloc_zero(void) {
    TEST(safe_alloc_zero);
    
    void* ptr = safe_alloc(0);
    ASSERT(ptr == NULL, "should return NULL for size 0");
    
    PASS();
}

static void test_safe_alloc_too_large(void) {
    TEST(safe_alloc_too_large);
    
    void* ptr = safe_alloc(SAFE_MAX_ALLOC_SIZE + 1);
    ASSERT(ptr == NULL, "should return NULL for oversized allocation");
    
    PASS();
}

static void test_safe_calloc_overflow(void) {
    TEST(safe_calloc_overflow);
    
    /* Try to trigger integer overflow: SIZE_MAX/2 * 3 would overflow */
    void* ptr = safe_calloc(SIZE_MAX / 2, 3);
    ASSERT(ptr == NULL, "should return NULL on overflow");
    
    PASS();
}

static void test_safe_free_null(void) {
    TEST(safe_free_null);
    
    void* ptr = NULL;
    SAFE_FREE(ptr);  /* Should not crash */
    ASSERT(ptr == NULL, "should remain NULL");
    
    PASS();
}

static void test_safe_free_double(void) {
    TEST(safe_free_double);
    
    void* ptr = safe_alloc(100);
    ASSERT(ptr != NULL, "allocation failed");
    
    SAFE_FREE(ptr);
    ASSERT(ptr == NULL, "pointer not nullified");
    
    /* Second free should be safe (ptr is now NULL) */
    SAFE_FREE(ptr);
    ASSERT(ptr == NULL, "should still be NULL");
    
    PASS();
}

/* ============================================================================
 * String Tests
 * ============================================================================ */

static void test_safe_strcpy_basic(void) {
    TEST(safe_strcpy_basic);
    
    char dst[20];
    size_t len = safe_strcpy(dst, "hello", sizeof(dst));
    
    ASSERT(len == 5, "wrong length returned");
    ASSERT(strcmp(dst, "hello") == 0, "wrong content");
    
    PASS();
}

static void test_safe_strcpy_truncate(void) {
    TEST(safe_strcpy_truncate);
    
    char dst[5];
    size_t len = safe_strcpy(dst, "hello world", sizeof(dst));
    
    ASSERT(len == 11, "should return source length");
    ASSERT(strlen(dst) == 4, "should truncate to dst_size - 1");
    ASSERT(strcmp(dst, "hell") == 0, "wrong truncated content");
    ASSERT(dst[4] == '\0', "not null-terminated");
    
    PASS();
}

static void test_safe_strcpy_null(void) {
    TEST(safe_strcpy_null);
    
    size_t len = safe_strcpy(NULL, "hello", 10);
    ASSERT(len == 0, "should return 0 for NULL dst");
    
    char dst[10];
    len = safe_strcpy(dst, NULL, sizeof(dst));
    ASSERT(len == 0, "should return 0 for NULL src");
    
    PASS();
}

static void test_safe_sprintf_basic(void) {
    TEST(safe_sprintf_basic);
    
    char dst[50];
    int ret = safe_sprintf(dst, sizeof(dst), "value: %d", 42);
    
    ASSERT(ret == 9, "wrong return value");
    ASSERT(strcmp(dst, "value: 42") == 0, "wrong content");
    
    PASS();
}

static void test_safe_sprintf_truncate(void) {
    TEST(safe_sprintf_truncate);
    
    char dst[10];
    int ret = safe_sprintf(dst, sizeof(dst), "hello world %d", 12345);
    
    /* Should truncate but still be null-terminated */
    ASSERT(dst[9] == '\0', "not null-terminated");
    ASSERT(strlen(dst) == 9, "wrong length after truncation");
    
    PASS();
}

static void test_safe_strdup_basic(void) {
    TEST(safe_strdup_basic);
    
    char* dup = safe_strdup("hello", 100);
    ASSERT(dup != NULL, "duplication failed");
    ASSERT(strcmp(dup, "hello") == 0, "wrong content");
    
    SAFE_FREE(dup);
    ASSERT(dup == NULL, "not nullified after free");
    
    PASS();
}

static void test_safe_strdup_truncate(void) {
    TEST(safe_strdup_truncate);
    
    char* dup = safe_strdup("hello world", 5);
    ASSERT(dup != NULL, "duplication failed");
    ASSERT(strlen(dup) == 5, "wrong length");
    ASSERT(strcmp(dup, "hello") == 0, "wrong truncated content");
    
    SAFE_FREE(dup);
    
    PASS();
}

/* ============================================================================
 * Buffer Tests
 * ============================================================================ */

static void test_safe_memcpy_basic(void) {
    TEST(safe_memcpy_basic);
    
    char src[] = "hello";
    char dst[10] = {0};
    
    bool ok = safe_memcpy(dst, sizeof(dst), src, 5);
    ASSERT(ok, "memcpy failed");
    ASSERT(memcmp(dst, src, 5) == 0, "wrong content");
    
    PASS();
}

static void test_safe_memcpy_overflow(void) {
    TEST(safe_memcpy_overflow);
    
    char src[100];
    char dst[10];
    
    bool ok = safe_memcpy(dst, sizeof(dst), src, 100);
    ASSERT(!ok, "should fail on overflow");
    
    PASS();
}

static void test_safe_memzero(void) {
    TEST(safe_memzero);
    
    char buf[10] = "secret!!!";
    safe_memzero(buf, sizeof(buf));
    
    for (size_t i = 0; i < sizeof(buf); i++) {
        ASSERT(buf[i] == 0, "memory not zeroed");
    }
    
    PASS();
}

/* ============================================================================
 * Overflow Check Tests
 * ============================================================================ */

static void test_safe_mul_size_basic(void) {
    TEST(safe_mul_size_basic);
    
    size_t result;
    bool ok = safe_mul_size(100, 200, &result);
    
    ASSERT(ok, "should succeed");
    ASSERT(result == 20000, "wrong result");
    
    PASS();
}

static void test_safe_mul_size_overflow(void) {
    TEST(safe_mul_size_overflow);
    
    size_t result;
    bool ok = safe_mul_size(SIZE_MAX, 2, &result);
    
    ASSERT(!ok, "should detect overflow");
    
    PASS();
}

static void test_safe_add_size_overflow(void) {
    TEST(safe_add_size_overflow);
    
    size_t result;
    bool ok = safe_add_size(SIZE_MAX, 1, &result);
    
    ASSERT(!ok, "should detect overflow");
    
    PASS();
}

/* ============================================================================
 * Main
 * ============================================================================ */

int main(void) {
    printf("\n=== IMMUNE Safe Memory Tests ===\n\n");
    
    printf("[Allocation Tests]\n");
    test_safe_alloc_basic();
    test_safe_alloc_zero();
    test_safe_alloc_too_large();
    test_safe_calloc_overflow();
    test_safe_free_null();
    test_safe_free_double();
    
    printf("\n[String Tests]\n");
    test_safe_strcpy_basic();
    test_safe_strcpy_truncate();
    test_safe_strcpy_null();
    test_safe_sprintf_basic();
    test_safe_sprintf_truncate();
    test_safe_strdup_basic();
    test_safe_strdup_truncate();
    
    printf("\n[Buffer Tests]\n");
    test_safe_memcpy_basic();
    test_safe_memcpy_overflow();
    test_safe_memzero();
    
    printf("\n[Overflow Check Tests]\n");
    test_safe_mul_size_basic();
    test_safe_mul_size_overflow();
    test_safe_add_size_overflow();
    
    printf("\n=== Results ===\n");
    printf("Passed: %d\n", tests_passed);
    printf("Failed: %d\n", tests_failed);
    printf("\n");
    
    return tests_failed > 0 ? 1 : 0;
}
