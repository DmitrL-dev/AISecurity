/*
 * SENTINEL Shield - Context Manager
 * 
 * Global context and state management
 */

#ifndef SHIELD_CONTEXT_H
#define SHIELD_CONTEXT_H

#include "shield_common.h"
#include "shield_zone.h"
#include "shield_rule.h"
#include "shield_guard.h"
#include "shield_ratelimit.h"
#include "shield_blocklist.h"
#include "shield_session.h"
#include "shield_canary.h"
#include "shield_metrics.h"
#include "shield_ha.h"
#include "shield_health.h"
#include "shield_event.h"
#include "shield_quarantine.h"
#include "shield_alert.h"
#include "shield_pattern.h"

/* Shield main context */
typedef struct shield_context {
    /* Core components */
    zone_registry_t     *zones;
    rule_registry_t     *rules;
    guard_registry_t    *guards;
    
    /* Security */
    rate_limiter_t      *rate_limiter;
    blocklist_t         *blocklist;
    session_manager_t   *sessions;
    canary_manager_t    *canaries;
    quarantine_manager_t *quarantine;
    alert_manager_t     *alerts;
    
    /* Monitoring */
    metrics_registry_t  *metrics;
    health_manager_t    *health;
    event_bus_t         *events;
    
    /* HA */
    ha_cluster_t        *cluster;
    
    /* Caching */
    pattern_cache_t     *pattern_cache;
    
    /* Config */
    char                hostname[64];
    char                config_file[256];
    bool                enable_api;
    uint16_t            api_port;
    bool                enable_metrics;
    uint16_t            metrics_port;
    
    /* State */
    bool                initialized;
    bool                running;
    uint64_t            start_time;
    
    /* Stats */
    uint64_t            total_requests;
    uint64_t            blocked_requests;
    uint64_t            allowed_requests;
} shield_context_t;

/* Global context */
extern shield_context_t *g_shield;

/* Lifecycle */
shield_err_t shield_context_init(shield_context_t *ctx);
void shield_context_destroy(shield_context_t *ctx);

/* Get global instance */
shield_context_t *shield_get_context(void);

/* Operations */
shield_err_t shield_start(shield_context_t *ctx);
void shield_stop(shield_context_t *ctx);
bool shield_is_running(shield_context_t *ctx);

/* Evaluate request */
typedef struct shield_request {
    const char      *zone;
    rule_direction_t direction;
    const char      *data;
    size_t          data_len;
    const char      *session_id;
    const char      *source_ip;
} shield_request_t;

typedef struct shield_response {
    rule_action_t   action;
    uint32_t        rule_number;
    char            reason[256];
    char            quarantine_id[64];
    float           confidence;
    uint64_t        latency_us;
} shield_response_t;

shield_err_t shield_evaluate(shield_context_t *ctx,
                              const shield_request_t *request,
                              shield_response_t *response);

/* Config */
shield_err_t shield_load_config(shield_context_t *ctx, const char *path);
shield_err_t shield_save_config(shield_context_t *ctx, const char *path);
shield_err_t shield_reload_config(shield_context_t *ctx);

/* Stats */
void shield_get_stats(shield_context_t *ctx,
                       uint64_t *total, uint64_t *blocked, uint64_t *allowed);
void shield_reset_stats(shield_context_t *ctx);

#endif /* SHIELD_CONTEXT_H */
