/*
 * SENTINEL Shield - Context Manager Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "shield_context.h"
#include "shield_platform.h"

/* Global context */
shield_context_t *g_shield = NULL;

/* Initialize context */
shield_err_t shield_context_init(shield_context_t *ctx)
{
    if (!ctx) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(ctx, 0, sizeof(*ctx));
    
    shield_err_t err;
    
    /* Allocate components */
    ctx->zones = calloc(1, sizeof(zone_registry_t));
    ctx->rules = calloc(1, sizeof(rule_registry_t));
    ctx->guards = calloc(1, sizeof(guard_registry_t));
    ctx->rate_limiter = calloc(1, sizeof(rate_limiter_t));
    ctx->blocklist = calloc(1, sizeof(blocklist_t));
    ctx->sessions = calloc(1, sizeof(session_manager_t));
    ctx->canaries = calloc(1, sizeof(canary_manager_t));
    ctx->quarantine = calloc(1, sizeof(quarantine_manager_t));
    ctx->alerts = calloc(1, sizeof(alert_manager_t));
    ctx->metrics = calloc(1, sizeof(metrics_registry_t));
    ctx->health = calloc(1, sizeof(health_manager_t));
    ctx->events = calloc(1, sizeof(event_bus_t));
    ctx->pattern_cache = calloc(1, sizeof(pattern_cache_t));
    
    if (!ctx->zones || !ctx->rules || !ctx->guards ||
        !ctx->rate_limiter || !ctx->blocklist || !ctx->sessions ||
        !ctx->canaries || !ctx->quarantine || !ctx->alerts ||
        !ctx->metrics || !ctx->health || !ctx->events ||
        !ctx->pattern_cache) {
        shield_context_destroy(ctx);
        return SHIELD_ERR_NOMEM;
    }
    
    /* Initialize components */
    err = zone_registry_init(ctx->zones);
    if (err != SHIELD_OK) goto error;
    
    err = rule_registry_init(ctx->rules);
    if (err != SHIELD_OK) goto error;
    
    err = guard_registry_init(ctx->guards);
    if (err != SHIELD_OK) goto error;
    
    err = ratelimit_init(ctx->rate_limiter, 100, 200);
    if (err != SHIELD_OK) goto error;
    
    err = blocklist_init(ctx->blocklist, 10000);
    if (err != SHIELD_OK) goto error;
    
    err = session_manager_init(ctx->sessions, 300);
    if (err != SHIELD_OK) goto error;
    
    err = canary_manager_init(ctx->canaries);
    if (err != SHIELD_OK) goto error;
    
    err = quarantine_init(ctx->quarantine, 1000, 86400);
    if (err != SHIELD_OK) goto error;
    
    err = alert_manager_init(ctx->alerts, 1000);
    if (err != SHIELD_OK) goto error;
    
    err = metrics_init(ctx->metrics);
    if (err != SHIELD_OK) goto error;
    
    err = health_manager_init(ctx->health);
    if (err != SHIELD_OK) goto error;
    
    err = event_bus_init(ctx->events);
    if (err != SHIELD_OK) goto error;
    
    err = pattern_cache_init(ctx->pattern_cache, 256);
    if (err != SHIELD_OK) goto error;
    
    /* Defaults */
    strncpy(ctx->hostname, "sentinel", sizeof(ctx->hostname) - 1);
    ctx->api_port = 8080;
    ctx->metrics_port = 9090;
    
    ctx->initialized = true;
    ctx->start_time = (uint64_t)time(NULL);
    
    g_shield = ctx;
    
    LOG_INFO("Shield context initialized");
    
    return SHIELD_OK;
    
error:
    shield_context_destroy(ctx);
    return err;
}

/* Destroy context */
void shield_context_destroy(shield_context_t *ctx)
{
    if (!ctx) return;
    
    ctx->running = false;
    
    /* Destroy components */
    if (ctx->zones) {
        zone_registry_destroy(ctx->zones);
        free(ctx->zones);
    }
    if (ctx->rules) {
        rule_registry_destroy(ctx->rules);
        free(ctx->rules);
    }
    if (ctx->guards) {
        guard_registry_destroy(ctx->guards);
        free(ctx->guards);
    }
    if (ctx->rate_limiter) {
        ratelimit_destroy(ctx->rate_limiter);
        free(ctx->rate_limiter);
    }
    if (ctx->blocklist) {
        blocklist_destroy(ctx->blocklist);
        free(ctx->blocklist);
    }
    if (ctx->sessions) {
        session_manager_destroy(ctx->sessions);
        free(ctx->sessions);
    }
    if (ctx->canaries) {
        canary_manager_destroy(ctx->canaries);
        free(ctx->canaries);
    }
    if (ctx->quarantine) {
        quarantine_destroy(ctx->quarantine);
        free(ctx->quarantine);
    }
    if (ctx->alerts) {
        alert_manager_destroy(ctx->alerts);
        free(ctx->alerts);
    }
    if (ctx->metrics) {
        metrics_destroy(ctx->metrics);
        free(ctx->metrics);
    }
    if (ctx->health) {
        health_manager_destroy(ctx->health);
        free(ctx->health);
    }
    if (ctx->events) {
        event_bus_destroy(ctx->events);
        free(ctx->events);
    }
    if (ctx->cluster) {
        ha_cluster_destroy(ctx->cluster);
        free(ctx->cluster);
    }
    if (ctx->pattern_cache) {
        pattern_cache_destroy(ctx->pattern_cache);
        free(ctx->pattern_cache);
    }
    
    ctx->initialized = false;
    
    if (g_shield == ctx) {
        g_shield = NULL;
    }
    
    LOG_INFO("Shield context destroyed");
}

/* Get global context */
shield_context_t *shield_get_context(void)
{
    return g_shield;
}

/* Start shield */
shield_err_t shield_start(shield_context_t *ctx)
{
    if (!ctx || !ctx->initialized) {
        return SHIELD_ERR_INVALID;
    }
    
    ctx->running = true;
    ctx->start_time = (uint64_t)time(NULL);
    
    LOG_INFO("Shield started");
    
    return SHIELD_OK;
}

/* Stop shield */
void shield_stop(shield_context_t *ctx)
{
    if (!ctx) return;
    
    ctx->running = false;
    
    LOG_INFO("Shield stopped");
}

/* Is running */
bool shield_is_running(shield_context_t *ctx)
{
    return ctx && ctx->running;
}

/* Evaluate request */
shield_err_t shield_evaluate(shield_context_t *ctx,
                              const shield_request_t *request,
                              shield_response_t *response)
{
    if (!ctx || !request || !response || !ctx->initialized) {
        return SHIELD_ERR_INVALID;
    }
    
    uint64_t start = platform_time_us();
    
    memset(response, 0, sizeof(*response));
    response->action = ACTION_ALLOW;
    response->confidence = 1.0f;
    
    /* Look up zone */
    zone_t *zone = zone_lookup(ctx->zones, request->zone);
    if (!zone) {
        snprintf(response->reason, sizeof(response->reason), "Unknown zone");
        response->action = ACTION_BLOCK;
        return SHIELD_ERR_NOTFOUND;
    }
    
    /* Rate limit check */
    const char *key = request->session_id ? request->session_id : request->source_ip;
    if (key && !ratelimit_acquire(ctx->rate_limiter, key)) {
        response->action = ACTION_BLOCK;
        snprintf(response->reason, sizeof(response->reason), "Rate limit exceeded");
        ctx->blocked_requests++;
        ctx->total_requests++;
        return SHIELD_OK;
    }
    
    /* Blocklist check */
    if (request->data && blocklist_check(ctx->blocklist, request->data)) {
        response->action = ACTION_BLOCK;
        snprintf(response->reason, sizeof(response->reason), "Blocklist match");
        ctx->blocked_requests++;
        ctx->total_requests++;
        return SHIELD_OK;
    }
    
    /* Canary check */
    if (request->data && canary_scan(ctx->canaries, request->data, request->data_len)) {
        /* Fire alert */
        alert_fire(ctx->alerts, ALERT_CRITICAL, "canary",
                   "Canary token detected", "Data exfiltration attempt",
                   request->zone, request->session_id, 0);
        
        response->action = ACTION_BLOCK;
        snprintf(response->reason, sizeof(response->reason), "Canary token detected");
        ctx->blocked_requests++;
        ctx->total_requests++;
        return SHIELD_OK;
    }
    
    /* Rule evaluation */
    uint32_t acl_id = (request->direction == DIRECTION_INPUT) 
                       ? zone->inbound_acl : zone->outbound_acl;
    
    if (acl_id > 0) {
        rule_verdict_t verdict = rule_evaluate(ctx->rules, acl_id,
            request->direction, zone->type, request->zone,
            request->data, request->data_len);
        
        response->action = verdict.action;
        response->rule_number = verdict.matched_rule;
        if (verdict.reason) {
            strncpy(response->reason, verdict.reason, sizeof(response->reason) - 1);
        }
    }
    
    /* Handle quarantine */
    if (response->action == ACTION_QUARANTINE) {
        quarantine_add(ctx->quarantine, request->zone, request->session_id,
                        request->direction, response->rule_number,
                        response->reason, request->data, request->data_len,
                        response->quarantine_id, sizeof(response->quarantine_id));
    }
    
    /* Update stats */
    ctx->total_requests++;
    if (response->action == ACTION_BLOCK || response->action == ACTION_QUARANTINE) {
        ctx->blocked_requests++;
    } else {
        ctx->allowed_requests++;
    }
    
    /* Metrics */
    metrics_inc(ctx->metrics, "shield_requests_total", NULL);
    if (response->action == ACTION_BLOCK) {
        metrics_inc(ctx->metrics, "shield_requests_blocked", NULL);
    }
    
    response->latency_us = platform_time_us() - start;
    
    return SHIELD_OK;
}

/* Get stats */
void shield_get_stats(shield_context_t *ctx,
                       uint64_t *total, uint64_t *blocked, uint64_t *allowed)
{
    if (!ctx) return;
    
    if (total) *total = ctx->total_requests;
    if (blocked) *blocked = ctx->blocked_requests;
    if (allowed) *allowed = ctx->allowed_requests;
}

/* Reset stats */
void shield_reset_stats(shield_context_t *ctx)
{
    if (!ctx) return;
    
    ctx->total_requests = 0;
    ctx->blocked_requests = 0;
    ctx->allowed_requests = 0;
}
