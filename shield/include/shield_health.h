/*
 * SENTINEL Shield - Health Check & Watchdog
 */

#ifndef SHIELD_HEALTH_H
#define SHIELD_HEALTH_H

#include "shield_common.h"

/* Health status */
typedef enum health_status {
    HEALTH_OK = 0,
    HEALTH_DEGRADED = 1,
    HEALTH_CRITICAL = 2,
    HEALTH_UNKNOWN = 3,
} health_status_t;

/* Component health */
typedef struct component_health {
    char            name[64];
    health_status_t status;
    char            message[128];
    uint64_t        last_check;
    uint64_t        check_duration_us;
} component_health_t;

/* Health checker */
typedef health_status_t (*health_check_fn)(void *ctx, char *message, size_t msg_len);

/* Health probe */
typedef struct health_probe {
    char            name[64];
    health_check_fn check;
    void            *ctx;
    uint32_t        interval_ms;
    uint32_t        timeout_ms;
    uint32_t        failures_threshold;
    
    /* State */
    health_status_t status;
    uint32_t        consecutive_failures;
    uint64_t        last_check;
    char            last_message[128];
    
    struct health_probe *next;
} health_probe_t;

/* Health manager */
typedef struct health_manager {
    health_probe_t  *probes;
    int             probe_count;
    
    health_status_t overall_status;
    bool            running;
    
    /* Callbacks */
    void            (*on_status_change)(health_status_t old, health_status_t new, void *ctx);
    void            *callback_ctx;
} health_manager_t;

/* API */
shield_err_t health_manager_init(health_manager_t *mgr);
void health_manager_destroy(health_manager_t *mgr);

shield_err_t health_add_probe(health_manager_t *mgr, const char *name,
                               health_check_fn check, void *ctx,
                               uint32_t interval_ms, uint32_t timeout_ms);
shield_err_t health_remove_probe(health_manager_t *mgr, const char *name);

/* Run all health checks */
health_status_t health_check_all(health_manager_t *mgr);

/* Get overall status */
health_status_t health_get_status(health_manager_t *mgr);

/* Get component status */
component_health_t health_get_component(health_manager_t *mgr, const char *name);

/* Export health as JSON */
char *health_export_json(health_manager_t *mgr);

/* Status to string */
const char *health_status_string(health_status_t status);

/* ===== Watchdog ===== */

typedef struct watchdog {
    uint64_t        timeout_ms;
    uint64_t        last_ping;
    bool            enabled;
    bool            triggered;
    
    void            (*on_timeout)(void *ctx);
    void            *ctx;
} watchdog_t;

shield_err_t watchdog_init(watchdog_t *wd, uint64_t timeout_ms);
void watchdog_destroy(watchdog_t *wd);

void watchdog_ping(watchdog_t *wd);
bool watchdog_check(watchdog_t *wd);
void watchdog_enable(watchdog_t *wd, bool enable);
void watchdog_set_callback(watchdog_t *wd, void (*cb)(void *), void *ctx);

#endif /* SHIELD_HEALTH_H */
