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

/* CLI state (used by CLI subsystem) */
typedef struct cli_state {
    cli_mode_t      mode;
    char            prompt[128];
    char            hostname[64];
    char            current_zone[SHIELD_MAX_NAME_LEN];
    bool            enable_mode;
    
    /* History */
    char            *history[SHIELD_MAX_HISTORY];
    int             history_count;
    int             history_pos;
    
    /* Output */
    bool            pager_enabled;
    int             terminal_width;
    int             terminal_height;
} cli_state_t;

/* Shield main context */
typedef struct shield_context {
    /* CLI */
    cli_state_t         cli;
    
    /* Core components */
    zone_registry_t     *zones;
    rule_engine_t       *rules;
    guard_registry_t    *guards;
    
    /* Security */
    ratelimiter_t       *rate_limiter;
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
    bool                api_enabled;
    uint16_t            api_port;
    char                api_token[128];
    bool                metrics_enabled;
    uint16_t            metrics_port;
    
    /* State */
    bool                initialized;
    bool                running;
    uint64_t            start_time;
    
    /* Stats */
    uint64_t            total_requests;
    uint64_t            blocked_requests;
    uint64_t            allowed_requests;
    
    /* System stats (for show commands) */
    uint64_t            uptime_seconds;
    uint64_t            memory_total;
    uint64_t            memory_used;
    float               cpu_1min;
    float               cpu_5min;
    float               cpu_15min;
    uint32_t            cpu_cores;
    char                os_name[64];
    char                kernel_version[64];
    
    /* CLI state */
    cli_mode_t          cli_mode;
    char                cli_prompt[64];
    char                current_zone[64];
    char                current_class_map[64];
    char                current_policy_map[64];
    char                current_policy_class[64];
    uint32_t            current_acl;
    bool                modified;
    log_level_t         log_level;
    
    /* Policy engine */
    struct policy_engine *policy_engine;
    
    /* CLI config */
    char                enable_secret[128];
    char                domain_name[64];
    char                name_server[64];
    char                dns_server[64];
    char                banner_motd[256];
    char                archive_path[256];
    uint32_t            archive_max;
    bool                service_password_encryption;
    
    /* AAA */
    char                aaa_method[32];
    
    /* Logging */
    bool                logging_console;
    uint32_t            logging_buffered_size;
    char                logging_host[64];
    
    /* NTP */
    char                ntp_server[64];
    char                timezone[32];
    
    /* SNMP */
    char                snmp_community[64];
    char                snmp_host[64];
    bool                snmp_readonly;
    
    /* Debug */
    uint32_t            debug_flags;
    bool                terminal_monitor;
    uint64_t            counters[16];
    uint32_t            log_count;
    
    /* Users */
    struct {
        char name[32];
        char password[128];
        uint8_t privilege;
    } users[16];
    int                 user_count;
    
    /* Signature database */
    uint32_t            signature_count;
    
    /* Canary */
    uint32_t            canary_count;
    
    /* Rate limiting */
    bool                rate_limit_enabled;
    uint32_t            rate_limit_requests;
    uint32_t            rate_limit_window;
    
    /* Threat intelligence */
    bool                threat_intel_enabled;
    
    /* Alerting */
    char                alert_destination[256];
    
    /* SIEM */
    bool                siem_enabled;
    char                siem_host[64];
    uint16_t            siem_port;
    char                siem_format[16];
    
    /* HA config (embedded) */
    struct {
        bool            enabled;
        char            virtual_ip[64];
        uint8_t         priority;
        bool            preempt;
        uint32_t        hello_interval;
        uint32_t        hold_time;
        char            auth_key[64];
        char            track_object[64];
        uint32_t        track_decrement;
        char            cluster_name[64];
        int             mode;  /* ha_mode_t */
        bool            failover_enabled;
        char            failover_interface[64];
    } ha;
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
