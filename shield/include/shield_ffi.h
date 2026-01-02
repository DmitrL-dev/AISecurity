/*
 * SENTINEL Shield - C API for FFI
 * 
 * Stable C API for Python, Go, Node.js bindings
 */

#ifndef SHIELD_FFI_H
#define SHIELD_FFI_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef _WIN32
    #ifdef SHIELD_EXPORTS
        #define SHIELD_API __declspec(dllexport)
    #else
        #define SHIELD_API __declspec(dllimport)
    #endif
#else
    #define SHIELD_API __attribute__((visibility("default")))
#endif

#ifdef __cplusplus
extern "C" {
#endif

/* Opaque handle */
typedef void* shield_handle_t;

/* Result codes */
typedef enum {
    SHIELD_RESULT_OK = 0,
    SHIELD_RESULT_ERROR = -1,
    SHIELD_RESULT_INVALID = -2,
    SHIELD_RESULT_NOMEM = -3,
} shield_result_t;

/* Actions */
typedef enum {
    SHIELD_ACTION_ALLOW = 0,
    SHIELD_ACTION_BLOCK = 1,
    SHIELD_ACTION_QUARANTINE = 2,
    SHIELD_ACTION_LOG = 3,
} shield_action_t;

/* Directions */
typedef enum {
    SHIELD_DIR_INPUT = 0,
    SHIELD_DIR_OUTPUT = 1,
} shield_direction_t;

/* Zone types */
typedef enum {
    SHIELD_ZONE_UNKNOWN = 0,
    SHIELD_ZONE_LLM = 1,
    SHIELD_ZONE_RAG = 2,
    SHIELD_ZONE_AGENT = 3,
    SHIELD_ZONE_TOOL = 4,
    SHIELD_ZONE_MCP = 5,
    SHIELD_ZONE_API = 6,
} shield_zone_type_t;

/* Evaluation result */
typedef struct {
    shield_action_t action;
    uint32_t        rule_number;
    float           confidence;
    char            reason[256];
} shield_eval_result_t;

/* ===== Lifecycle ===== */

/* Initialize shield instance */
SHIELD_API shield_handle_t shield_init(void);

/* Destroy shield instance */
SHIELD_API void shield_destroy(shield_handle_t handle);

/* Get version string */
SHIELD_API const char* shield_version(void);

/* ===== Configuration ===== */

/* Load configuration from file */
SHIELD_API shield_result_t shield_load_config(shield_handle_t handle, const char *path);

/* Save configuration to file */
SHIELD_API shield_result_t shield_save_config(shield_handle_t handle, const char *path);

/* ===== Zone Management ===== */

/* Create zone */
SHIELD_API shield_result_t shield_zone_create(
    shield_handle_t handle,
    const char *name,
    shield_zone_type_t type
);

/* Delete zone */
SHIELD_API shield_result_t shield_zone_delete(shield_handle_t handle, const char *name);

/* Set zone ACL */
SHIELD_API shield_result_t shield_zone_set_acl(
    shield_handle_t handle,
    const char *zone_name,
    uint32_t in_acl,
    uint32_t out_acl
);

/* Get zone count */
SHIELD_API int shield_zone_count(shield_handle_t handle);

/* ===== Rule Management ===== */

/* Add rule */
SHIELD_API shield_result_t shield_rule_add(
    shield_handle_t handle,
    uint32_t acl_number,
    uint32_t rule_number,
    shield_action_t action,
    shield_direction_t direction,
    shield_zone_type_t zone_type,
    const char *match_pattern
);

/* Delete rule */
SHIELD_API shield_result_t shield_rule_delete(
    shield_handle_t handle,
    uint32_t acl_number,
    uint32_t rule_number
);

/* ===== Evaluation ===== */

/* Evaluate request */
SHIELD_API shield_eval_result_t shield_evaluate(
    shield_handle_t handle,
    const char *zone_name,
    shield_direction_t direction,
    const char *data,
    size_t data_len
);

/* Quick check (returns action only) */
SHIELD_API shield_action_t shield_check(
    shield_handle_t handle,
    const char *zone_name,
    shield_direction_t direction,
    const char *data,
    size_t data_len
);

/* ===== Blocklist ===== */

/* Add to blocklist */
SHIELD_API shield_result_t shield_blocklist_add(
    shield_handle_t handle,
    const char *pattern,
    const char *reason
);

/* Check blocklist */
SHIELD_API bool shield_blocklist_check(shield_handle_t handle, const char *text);

/* Load blocklist from file */
SHIELD_API shield_result_t shield_blocklist_load(shield_handle_t handle, const char *path);

/* ===== Rate Limiting ===== */

/* Configure rate limiter */
SHIELD_API shield_result_t shield_ratelimit_config(
    shield_handle_t handle,
    uint32_t requests_per_second,
    uint32_t burst_size
);

/* Check rate limit */
SHIELD_API bool shield_ratelimit_check(shield_handle_t handle, const char *key);

/* Acquire rate limit token */
SHIELD_API bool shield_ratelimit_acquire(shield_handle_t handle, const char *key);

/* ===== Canary Tokens ===== */

/* Create canary token */
SHIELD_API shield_result_t shield_canary_create(
    shield_handle_t handle,
    const char *value,
    const char *description,
    char *out_id,
    size_t out_id_len
);

/* Scan for canary tokens */
SHIELD_API bool shield_canary_scan(shield_handle_t handle, const char *text, size_t len);

/* ===== Statistics ===== */

/* Get statistics */
SHIELD_API void shield_stats(
    shield_handle_t handle,
    uint64_t *total_requests,
    uint64_t *blocked,
    uint64_t *allowed
);

/* Reset statistics */
SHIELD_API void shield_stats_reset(shield_handle_t handle);

/* Export metrics (Prometheus format) */
SHIELD_API char* shield_metrics_export(shield_handle_t handle);

/* Free exported string */
SHIELD_API void shield_free_string(char *str);

#ifdef __cplusplus
}
#endif

#endif /* SHIELD_FFI_H */
