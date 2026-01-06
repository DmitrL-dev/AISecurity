/*
 * SENTINEL Shield - FFI Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_common.h"
#include "shield_zone.h"
#include "shield_rule.h"
#include "shield_guard.h"
#include "shield_ratelimit.h"
#include "shield_blocklist.h"
#include "shield_canary.h"
#include "shield_metrics.h"
#include "shield_ffi.h"

/* Internal context */
typedef struct ffi_context {
    zone_registry_t     zones;
    rule_engine_t       rules;
    guard_registry_t    guards;
    ratelimiter_t       ratelimiter;
    blocklist_t         blocklist;
    canary_manager_t    canaries;
    metrics_registry_t  metrics_reg;
    shield_metrics_t    metrics;
    
    uint64_t            total_requests;
    uint64_t            blocked;
    uint64_t            allowed;
} ffi_context_t;

/* Initialize */
SHIELD_API shield_handle_t shield_init(void)
{
    ffi_context_t *ctx = calloc(1, sizeof(ffi_context_t));
    if (!ctx) {
        return NULL;
    }
    
    zone_registry_init(&ctx->zones);
    rule_engine_init(&ctx->rules);
    guard_registry_init(&ctx->guards);
    
    ratelimit_config_t rl_config = {
        .requests_per_second = 100,
        .burst_size = 200,
        .algorithm = RATELIMIT_TOKEN_BUCKET,
    };
    ratelimiter_init(&ctx->ratelimiter, &rl_config);
    
    blocklist_init(&ctx->blocklist, "default", 256);
    canary_manager_init(&ctx->canaries);
    
    metrics_init(&ctx->metrics_reg);
    shield_metrics_init(&ctx->metrics, &ctx->metrics_reg);
    
    return (shield_handle_t)ctx;
}

/* Destroy */
SHIELD_API void shield_destroy(shield_handle_t handle)
{
    ffi_context_t *ctx = (ffi_context_t *)handle;
    if (!ctx) {
        return;
    }
    
    zone_registry_destroy(&ctx->zones);
    rule_engine_destroy(&ctx->rules);
    guard_registry_destroy(&ctx->guards);
    ratelimiter_destroy(&ctx->ratelimiter);
    blocklist_destroy(&ctx->blocklist);
    canary_manager_destroy(&ctx->canaries);
    metrics_destroy(&ctx->metrics_reg);
    
    free(ctx);
}

/* Version */
SHIELD_API const char* shield_version(void)
{
    return SHIELD_VERSION_STRING;
}

/* Load config */
SHIELD_API shield_result_t shield_ffi_load_config(shield_handle_t handle, const char *path)
{
    (void)handle; (void)path;
    /* TODO: Implement config loading */
    return SHIELD_RESULT_OK;
}

/* Save config */
SHIELD_API shield_result_t shield_ffi_save_config(shield_handle_t handle, const char *path)
{
    (void)handle; (void)path;
    /* TODO: Implement config saving */
    return SHIELD_RESULT_OK;
}

/* Create zone */
SHIELD_API shield_result_t shield_zone_create(
    shield_handle_t handle,
    const char *name,
    shield_zone_type_t type)
{
    ffi_context_t *ctx = (ffi_context_t *)handle;
    if (!ctx || !name) {
        return SHIELD_RESULT_INVALID;
    }
    
    shield_err_t err = zone_create(&ctx->zones, name, (zone_type_t)type, NULL);
    return err == SHIELD_OK ? SHIELD_RESULT_OK : SHIELD_RESULT_ERROR;
}

/* Delete zone */
SHIELD_API shield_result_t shield_zone_delete(shield_handle_t handle, const char *name)
{
    ffi_context_t *ctx = (ffi_context_t *)handle;
    if (!ctx || !name) {
        return SHIELD_RESULT_INVALID;
    }
    
    shield_err_t err = zone_delete(&ctx->zones, name);
    return err == SHIELD_OK ? SHIELD_RESULT_OK : SHIELD_RESULT_ERROR;
}

/* Set zone ACL */
SHIELD_API shield_result_t shield_zone_set_acl(
    shield_handle_t handle,
    const char *zone_name,
    uint32_t in_acl,
    uint32_t out_acl)
{
    ffi_context_t *ctx = (ffi_context_t *)handle;
    if (!ctx || !zone_name) {
        return SHIELD_RESULT_INVALID;
    }
    
    shield_zone_t *zone = zone_find_by_name(&ctx->zones, zone_name);
    if (!zone) {
        return SHIELD_RESULT_ERROR;
    }
    
    zone->in_acl = in_acl;
    zone->out_acl = out_acl;
    return SHIELD_RESULT_OK;
}

/* Zone count */
SHIELD_API int shield_zone_count(shield_handle_t handle)
{
    ffi_context_t *ctx = (ffi_context_t *)handle;
    return ctx ? (int)ctx->zones.count : 0;
}

/* Add rule */
SHIELD_API shield_result_t shield_rule_add(
    shield_handle_t handle,
    uint32_t acl_number,
    uint32_t rule_number,
    shield_action_t action,
    shield_direction_t direction,
    shield_zone_type_t zone_type,
    const char *match_pattern)
{
    ffi_context_t *ctx = (ffi_context_t *)handle;
    if (!ctx) {
        return SHIELD_RESULT_INVALID;
    }
    
    /* Get or create ACL */
    access_list_t *acl = acl_find(&ctx->rules, acl_number);
    if (!acl) {
        if (acl_create(&ctx->rules, acl_number, &acl) != SHIELD_OK) {
            return SHIELD_RESULT_ERROR;
        }
    }
    
    /* Add rule */
    shield_rule_t *rule = NULL;
    shield_err_t err = rule_add(acl, rule_number, (rule_action_t)action,
                                 (rule_direction_t)direction,
                                 (zone_type_t)zone_type, NULL, &rule);
    if (err != SHIELD_OK) {
        return SHIELD_RESULT_ERROR;
    }
    
    /* Add pattern if provided */
    if (match_pattern && match_pattern[0] && rule) {
        rule_add_condition(rule, MATCH_PATTERN, match_pattern, 0);
    }
    
    return SHIELD_RESULT_OK;
}

/* Delete rule */
SHIELD_API shield_result_t shield_rule_delete(
    shield_handle_t handle,
    uint32_t acl_number,
    uint32_t rule_number)
{
    ffi_context_t *ctx = (ffi_context_t *)handle;
    if (!ctx) {
        return SHIELD_RESULT_INVALID;
    }
    
    access_list_t *acl = acl_find(&ctx->rules, acl_number);
    if (!acl) {
        return SHIELD_RESULT_ERROR;
    }
    
    shield_err_t err = rule_delete(acl, rule_number);
    return err == SHIELD_OK ? SHIELD_RESULT_OK : SHIELD_RESULT_ERROR;
}

/* Evaluate */
SHIELD_API shield_eval_result_t shield_ffi_evaluate(
    shield_handle_t handle,
    const char *zone_name,
    shield_direction_t direction,
    const char *data,
    size_t data_len)
{
    shield_eval_result_t result = {
        .action = SHIELD_ACTION_ALLOW,
        .rule_number = 0,
        .confidence = 1.0f,
        .reason = ""
    };
    
    ffi_context_t *ctx = (ffi_context_t *)handle;
    if (!ctx || !data) {
        return result;
    }
    
    ctx->total_requests++;
    metrics_inc(ctx->metrics.requests_total);
    
    /* Find zone */
    shield_zone_t *zone = zone_name ? zone_find_by_name(&ctx->zones, zone_name) : NULL;
    zone_type_t type = zone ? zone->type : ZONE_TYPE_UNKNOWN;
    uint32_t acl = 100; /* Default */
    
    if (zone) {
        acl = direction == SHIELD_DIR_INPUT ? zone->in_acl : zone->out_acl;
    }
    
    /* Check blocklist first */
    if (blocklist_contains(&ctx->blocklist, data)) {
        result.action = SHIELD_ACTION_BLOCK;
        strncpy(result.reason, "Blocklist match", sizeof(result.reason) - 1);
        ctx->blocked++;
        metrics_inc(ctx->metrics.requests_blocked);
        return result;
    }
    
    /* Evaluate rules */
    rule_verdict_t verdict = rule_evaluate(&ctx->rules, acl,
                                           (rule_direction_t)direction,
                                           type, zone_name, data, data_len);
    
    metrics_inc(ctx->metrics.rule_evaluations);
    
    result.action = (shield_action_t)verdict.action;
    result.rule_number = verdict.matched_rule ? verdict.matched_rule->number : 0;
    if (verdict.reason) {
        strncpy(result.reason, verdict.reason, sizeof(result.reason) - 1);
    }
    
    if (result.action == SHIELD_ACTION_BLOCK) {
        ctx->blocked++;
        metrics_inc(ctx->metrics.requests_blocked);
    } else {
        ctx->allowed++;
        metrics_inc(ctx->metrics.requests_allowed);
    }
    
    return result;
}

/* Quick check */
SHIELD_API shield_action_t shield_check(
    shield_handle_t handle,
    const char *zone_name,
    shield_direction_t direction,
    const char *data,
    size_t data_len)
{
    shield_eval_result_t result = shield_ffi_evaluate(handle, zone_name, direction, data, data_len);
    return result.action;
}

/* Blocklist add */
SHIELD_API shield_result_t shield_blocklist_add(
    shield_handle_t handle,
    const char *pattern,
    const char *reason)
{
    ffi_context_t *ctx = (ffi_context_t *)handle;
    if (!ctx || !pattern) {
        return SHIELD_RESULT_INVALID;
    }
    
    shield_err_t err = blocklist_add(&ctx->blocklist, pattern, reason);
    return err == SHIELD_OK ? SHIELD_RESULT_OK : SHIELD_RESULT_ERROR;
}

/* Blocklist check */
SHIELD_API bool shield_blocklist_check(shield_handle_t handle, const char *text)
{
    ffi_context_t *ctx = (ffi_context_t *)handle;
    if (!ctx || !text) {
        return false;
    }
    return blocklist_contains(&ctx->blocklist, text);
}

/* Blocklist load */
SHIELD_API shield_result_t shield_blocklist_load(shield_handle_t handle, const char *path)
{
    ffi_context_t *ctx = (ffi_context_t *)handle;
    if (!ctx || !path) {
        return SHIELD_RESULT_INVALID;
    }
    
    shield_err_t err = blocklist_load(&ctx->blocklist, path);
    return err == SHIELD_OK ? SHIELD_RESULT_OK : SHIELD_RESULT_ERROR;
}

/* Rate limit config */
SHIELD_API shield_result_t shield_ratelimit_config(
    shield_handle_t handle,
    uint32_t requests_per_second,
    uint32_t burst_size)
{
    ffi_context_t *ctx = (ffi_context_t *)handle;
    if (!ctx) {
        return SHIELD_RESULT_INVALID;
    }
    
    ctx->ratelimiter.config.requests_per_second = requests_per_second;
    ctx->ratelimiter.config.burst_size = burst_size;
    return SHIELD_RESULT_OK;
}

/* Rate limit check */
SHIELD_API bool shield_ratelimit_check(shield_handle_t handle, const char *key)
{
    ffi_context_t *ctx = (ffi_context_t *)handle;
    if (!ctx || !key) {
        return true;
    }
    return ratelimit_check(&ctx->ratelimiter, key);
}

/* Rate limit acquire */
SHIELD_API bool shield_ratelimit_acquire(shield_handle_t handle, const char *key)
{
    ffi_context_t *ctx = (ffi_context_t *)handle;
    if (!ctx || !key) {
        return true;
    }
    
    bool acquired = ratelimit_acquire(&ctx->ratelimiter, key);
    if (!acquired) {
        metrics_inc(ctx->metrics.ratelimit_denied);
    }
    return acquired;
}

/* Canary create */
SHIELD_API shield_result_t shield_canary_create(
    shield_handle_t handle,
    const char *value,
    const char *description,
    char *out_id,
    size_t out_id_len)
{
    ffi_context_t *ctx = (ffi_context_t *)handle;
    if (!ctx || !value) {
        return SHIELD_RESULT_INVALID;
    }
    
    canary_token_t *token = NULL;
    shield_err_t err = canary_create(&ctx->canaries, CANARY_TYPE_STRING,
                                      value, description, &token);
    if (err != SHIELD_OK) {
        return SHIELD_RESULT_ERROR;
    }
    
    if (out_id && out_id_len > 0 && token) {
        strncpy(out_id, token->id, out_id_len - 1);
    }
    
    return SHIELD_RESULT_OK;
}

/* Canary scan */
SHIELD_API bool shield_canary_scan(shield_handle_t handle, const char *text, size_t len)
{
    ffi_context_t *ctx = (ffi_context_t *)handle;
    if (!ctx || !text) {
        return false;
    }
    
    bool detected = canary_contains_any(&ctx->canaries, text, len);
    if (detected) {
        metrics_inc(ctx->metrics.canary_triggers);
    }
    return detected;
}

/* Stats */
SHIELD_API void shield_stats(
    shield_handle_t handle,
    uint64_t *total_requests,
    uint64_t *blocked,
    uint64_t *allowed)
{
    ffi_context_t *ctx = (ffi_context_t *)handle;
    if (!ctx) {
        return;
    }
    
    if (total_requests) *total_requests = ctx->total_requests;
    if (blocked) *blocked = ctx->blocked;
    if (allowed) *allowed = ctx->allowed;
}

/* Stats reset */
SHIELD_API void shield_stats_reset(shield_handle_t handle)
{
    ffi_context_t *ctx = (ffi_context_t *)handle;
    if (ctx) {
        ctx->total_requests = 0;
        ctx->blocked = 0;
        ctx->allowed = 0;
    }
}

/* Export metrics */
SHIELD_API char* shield_metrics_export(shield_handle_t handle)
{
    ffi_context_t *ctx = (ffi_context_t *)handle;
    if (!ctx) {
        return NULL;
    }
    return metrics_export_prometheus(&ctx->metrics_reg);
}

/* Free string */
SHIELD_API void shield_free_string(char *str)
{
    free(str);
}
