/*
 * SENTINEL Shield - Example Custom Guard Plugin
 * 
 * Demonstrates how to create a custom guard plugin.
 * 
 * Build:
 *   gcc -shared -fPIC -o custom_guard.so custom_guard_plugin.c
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>

/* Guard interface (simplified from shield_guard.h) */
typedef enum {
    CHECK_PASSED = 0,
    CHECK_FAILED = 1,
    CHECK_SUSPICIOUS = 2,
} check_result_t;

typedef struct {
    check_result_t result;
    float confidence;
    char reason[256];
} guard_check_result_t;

/* Plugin interface */
typedef struct {
    int (*init)(void *config);
    void (*destroy)(void);
    struct {
        char name[64];
        char version[16];
        char author[64];
        char description[256];
        int type;
    } (*get_info)(void);
    void *(*create_guard)(void);
} plugin_interface_t;

/* ===== Custom Guard Implementation ===== */

/* Custom check: detect specific keywords */
static guard_check_result_t custom_check(void *ctx, const char *data, size_t len)
{
    (void)ctx;
    guard_check_result_t result = {
        .result = CHECK_PASSED,
        .confidence = 1.0f,
        .reason = ""
    };
    
    /* Example: detect "CONFIDENTIAL" keyword */
    if (data && len > 0) {
        if (strstr(data, "CONFIDENTIAL") != NULL) {
            result.result = CHECK_FAILED;
            result.confidence = 0.95f;
            snprintf(result.reason, sizeof(result.reason),
                     "Detected confidential keyword");
        }
        
        /* Check for SSN pattern (xxx-xx-xxxx) */
        for (size_t i = 0; i + 10 < len; i++) {
            if (data[i] >= '0' && data[i] <= '9' &&
                data[i+3] == '-' && data[i+6] == '-') {
                /* Simplified SSN check */
                result.result = CHECK_SUSPICIOUS;
                result.confidence = 0.7f;
                snprintf(result.reason, sizeof(result.reason),
                         "Possible SSN pattern detected");
                break;
            }
        }
    }
    
    return result;
}

/* Custom guard structure */
typedef struct {
    char name[64];
    guard_check_result_t (*check)(void *, const char *, size_t);
} custom_guard_t;

static custom_guard_t g_custom_guard = {
    .name = "custom-dlp",
    .check = custom_check,
};

/* ===== Plugin Interface ===== */

static int plugin_init(void *config)
{
    (void)config;
    printf("Custom guard plugin initialized\n");
    return 0;
}

static void plugin_destroy(void)
{
    printf("Custom guard plugin destroyed\n");
}

static struct {
    char name[64];
    char version[16];
    char author[64];
    char description[256];
    int type;
} plugin_get_info(void)
{
    struct {
        char name[64];
        char version[16];
        char author[64];
        char description[256];
        int type;
    } info = {0};
    
    strncpy(info.name, "custom-dlp", sizeof(info.name) - 1);
    strncpy(info.version, "1.0.0", sizeof(info.version) - 1);
    strncpy(info.author, "SENTINEL", sizeof(info.author) - 1);
    strncpy(info.description, "Custom DLP guard for detecting sensitive data",
            sizeof(info.description) - 1);
    info.type = 0; /* PLUGIN_TYPE_GUARD */
    
    return info;
}

static void *create_guard(void)
{
    return &g_custom_guard;
}

/* Export plugin interface */
#ifdef _WIN32
__declspec(dllexport)
#else
__attribute__((visibility("default")))
#endif
plugin_interface_t shield_plugin_interface(void)
{
    plugin_interface_t interface = {
        .init = plugin_init,
        .destroy = plugin_destroy,
        .get_info = plugin_get_info,
        .create_guard = create_guard,
    };
    return interface;
}
