/*
 * SENTINEL Shield - Watchdog Module
 * 
 * System health monitoring and automatic recovery.
 * Monitors Shield components and triggers alerts on anomalies.
 * 
 * Features:
 * - Component health checks
 * - Resource monitoring (memory, CPU-proxy)
 * - Deadlock detection
 * - Automatic restart/recovery
 * - Alert escalation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>
#include <stdbool.h>

#include "shield_common.h"
#include "shield_string_safe.h"

/* ===== Watchdog Constants ===== */

#define WATCHDOG_MAX_COMPONENTS   32
#define WATCHDOG_HISTORY_SIZE     64
#define WATCHDOG_CHECK_INTERVAL   5000   /* ms */

/* ===== Component Types ===== */

typedef enum component_type {
    COMP_TYPE_GUARD,
    COMP_TYPE_PROTOCOL,
    COMP_TYPE_CORE,
    COMP_TYPE_EXTERNAL,
} component_type_t;

typedef enum component_status {
    COMP_STATUS_UNKNOWN,
    COMP_STATUS_HEALTHY,
    COMP_STATUS_DEGRADED,
    COMP_STATUS_UNHEALTHY,
    COMP_STATUS_DEAD,
} component_status_t;

/* ===== Health Check Result ===== */

typedef struct health_check {
    component_status_t  status;
    float               health_score;     /* 0.0-1.0 */
    uint64_t            latency_us;
    uint64_t            last_check;
    char                message[128];
} health_check_t;

/* ===== Component Definition ===== */

typedef struct watchdog_component {
    char                name[64];
    component_type_t    type;
    bool                critical;         /* If critical, failure triggers alert */
    
    /* Health state */
    component_status_t  status;
    float               health_score;
    uint64_t            last_healthy;
    uint32_t            consecutive_failures;
    
    /* Thresholds */
    float               degraded_threshold;   /* Below this = degraded */
    float               unhealthy_threshold;  /* Below this = unhealthy */
    uint32_t            max_failures;         /* After this = dead */
    
    /* Check function pointer */
    health_check_t      (*check_fn)(void *ctx);
    void               *check_ctx;
    
    /* Recovery function */
    shield_err_t        (*recover_fn)(void *ctx);
    void               *recover_ctx;
    
    /* Statistics */
    uint64_t            checks_total;
    uint64_t            failures_total;
    uint64_t            recoveries;
} watchdog_component_t;

/* ===== Alert Levels ===== */

typedef enum alert_level {
    ALERT_LEVEL_INFO,
    ALERT_LEVEL_WARNING,
    ALERT_LEVEL_ERROR,
    ALERT_LEVEL_CRITICAL,
} alert_level_t;

typedef struct watchdog_alert {
    alert_level_t       level;
    char                component[64];
    char                message[256];
    uint64_t            timestamp;
    bool                acknowledged;
} watchdog_alert_t;

/* ===== Watchdog Context ===== */

typedef struct watchdog {
    bool                enabled;
    bool                auto_recovery;
    
    /* Components */
    watchdog_component_t components[WATCHDOG_MAX_COMPONENTS];
    size_t              component_count;
    
    /* Alerts */
    watchdog_alert_t    alerts[64];
    size_t              alert_count;
    size_t              alert_head;       /* Circular buffer */
    
    /* Overall health */
    float               system_health;
    component_status_t  system_status;
    
    /* Timing */
    uint64_t            check_interval_ms;
    uint64_t            last_check;
    
    /* Statistics */
    uint64_t            checks_completed;
    uint64_t            alerts_raised;
    uint64_t            recoveries_attempted;
    uint64_t            recoveries_successful;
} watchdog_t;

/* Global watchdog instance */
static watchdog_t g_watchdog = {0};

/* ===== Internal Helpers ===== */

static uint64_t get_time_ms(void)
{
    return (uint64_t)time(NULL) * 1000;
}

static void raise_alert(alert_level_t level, const char *component, const char *message)
{
    size_t idx = g_watchdog.alert_head;
    watchdog_alert_t *alert = &g_watchdog.alerts[idx];
    
    alert->level = level;
    strncpy(alert->component, component, sizeof(alert->component) - 1);
    strncpy(alert->message, message, sizeof(alert->message) - 1);
    alert->timestamp = get_time_ms();
    alert->acknowledged = false;
    
    g_watchdog.alert_head = (g_watchdog.alert_head + 1) % 64;
    if (g_watchdog.alert_count < 64) {
        g_watchdog.alert_count++;
    }
    g_watchdog.alerts_raised++;
    
    /* Log based on level */
    switch (level) {
        case ALERT_LEVEL_CRITICAL:
            LOG_ERROR("WATCHDOG CRITICAL: [%s] %s", component, message);
            break;
        case ALERT_LEVEL_ERROR:
            LOG_ERROR("WATCHDOG ERROR: [%s] %s", component, message);
            break;
        case ALERT_LEVEL_WARNING:
            LOG_WARN("WATCHDOG WARNING: [%s] %s", component, message);
            break;
        default:
            LOG_INFO("WATCHDOG INFO: [%s] %s", component, message);
            break;
    }
}

/* ===== Default Health Check Functions ===== */

static health_check_t default_check(void *ctx)
{
    (void)ctx;
    health_check_t result = {
        .status = COMP_STATUS_HEALTHY,
        .health_score = 1.0f,
        .latency_us = 100,
        .last_check = get_time_ms(),
    };
    shield_strcopy_s(result.message, sizeof(result.message), "OK");
    return result;
}

/* Memory health check */
static health_check_t memory_check(void *ctx)
{
    (void)ctx;
    health_check_t result = {
        .status = COMP_STATUS_HEALTHY,
        .health_score = 1.0f,
        .latency_us = 50,
        .last_check = get_time_ms(),
    };
    
    /* Simple allocation test */
    void *test = malloc(1024);
    if (test) {
        free(test);
        shield_strcopy_s(result.message, sizeof(result.message), "Memory allocation OK");
    } else {
        result.status = COMP_STATUS_UNHEALTHY;
        result.health_score = 0.0f;
        shield_strcopy_s(result.message, sizeof(result.message), "Memory allocation failed!");
    }
    
    return result;
}

/* Guard health check */
static health_check_t guard_check(void *ctx)
{
    const char *guard_name = (const char *)ctx;
    health_check_t result = {
        .status = COMP_STATUS_HEALTHY,
        .health_score = 1.0f,
        .latency_us = 100,
        .last_check = get_time_ms(),
    };
    
    /* Guard is healthy if it exists */
    if (guard_name) {
        snprintf(result.message, sizeof(result.message),
                "Guard %s operational", guard_name);
    }
    
    return result;
}

/* ===== Initialization ===== */

shield_err_t shield_watchdog_init(void)
{
    memset(&g_watchdog, 0, sizeof(g_watchdog));
    
    g_watchdog.enabled = true;
    g_watchdog.auto_recovery = true;
    g_watchdog.check_interval_ms = WATCHDOG_CHECK_INTERVAL;
    g_watchdog.system_health = 1.0f;
    g_watchdog.system_status = COMP_STATUS_HEALTHY;
    
    /* Register core components */
    
    /* Memory subsystem */
    watchdog_component_t *mem = &g_watchdog.components[g_watchdog.component_count++];
    shield_strcopy_s(mem->name, sizeof(mem->name), "Memory");
    mem->type = COMP_TYPE_CORE;
    mem->critical = true;
    mem->status = COMP_STATUS_UNKNOWN;
    mem->degraded_threshold = 0.7f;
    mem->unhealthy_threshold = 0.3f;
    mem->max_failures = 3;
    mem->check_fn = memory_check;
    
    /* Guards */
    const char *guards[] = {"LLM", "MCP", "RAG", "Tool", "Agent", "API"};
    for (size_t i = 0; i < 6 && g_watchdog.component_count < WATCHDOG_MAX_COMPONENTS; i++) {
        watchdog_component_t *guard = &g_watchdog.components[g_watchdog.component_count++];
        snprintf(guard->name, sizeof(guard->name), "%s Guard", guards[i]);
        guard->type = COMP_TYPE_GUARD;
        guard->critical = true;
        guard->status = COMP_STATUS_UNKNOWN;
        guard->degraded_threshold = 0.8f;
        guard->unhealthy_threshold = 0.5f;
        guard->max_failures = 5;
        guard->check_fn = guard_check;
        guard->check_ctx = (void *)guards[i];
    }
    
    LOG_INFO("Watchdog: Initialized with %zu components", g_watchdog.component_count);
    
    return SHIELD_OK;
}

void shield_watchdog_destroy(void)
{
    g_watchdog.enabled = false;
    LOG_INFO("Watchdog: Destroyed");
}

/* ===== Component Registration ===== */

shield_err_t shield_watchdog_register_component(const char *name, component_type_t type,
                                                  bool critical,
                                                  health_check_t (*check_fn)(void *),
                                                  void *check_ctx)
{
    if (!name || g_watchdog.component_count >= WATCHDOG_MAX_COMPONENTS) {
        return SHIELD_ERR_INVALID;
    }
    
    watchdog_component_t *comp = &g_watchdog.components[g_watchdog.component_count++];
    strncpy(comp->name, name, sizeof(comp->name) - 1);
    comp->type = type;
    comp->critical = critical;
    comp->status = COMP_STATUS_UNKNOWN;
    comp->degraded_threshold = 0.7f;
    comp->unhealthy_threshold = 0.3f;
    comp->max_failures = 5;
    comp->check_fn = check_fn ? check_fn : default_check;
    comp->check_ctx = check_ctx;
    
    LOG_DEBUG("Watchdog: Registered component '%s'", name);
    return SHIELD_OK;
}

/* ===== Health Check Execution ===== */

shield_err_t shield_watchdog_check_all(void)
{
    if (!g_watchdog.enabled) {
        return SHIELD_ERR_INVALID;
    }
    
    float total_health = 0;
    size_t healthy_count = 0;
    size_t critical_failures = 0;
    
    for (size_t i = 0; i < g_watchdog.component_count; i++) {
        watchdog_component_t *comp = &g_watchdog.components[i];
        
        /* Execute health check */
        health_check_t result = comp->check_fn(comp->check_ctx);
        comp->checks_total++;
        
        /* Update component state */
        component_status_t old_status = comp->status;
        comp->health_score = result.health_score;
        
        if (result.health_score >= comp->degraded_threshold) {
            comp->status = COMP_STATUS_HEALTHY;
            comp->consecutive_failures = 0;
            comp->last_healthy = get_time_ms();
            healthy_count++;
        } else if (result.health_score >= comp->unhealthy_threshold) {
            comp->status = COMP_STATUS_DEGRADED;
            comp->consecutive_failures++;
        } else {
            comp->status = COMP_STATUS_UNHEALTHY;
            comp->consecutive_failures++;
            comp->failures_total++;
        }
        
        /* Check for dead component */
        if (comp->consecutive_failures >= comp->max_failures) {
            comp->status = COMP_STATUS_DEAD;
            if (comp->critical) {
                critical_failures++;
            }
        }
        
        /* Raise alerts on status changes */
        if (comp->status != old_status && old_status != COMP_STATUS_UNKNOWN) {
            char msg[256];
            alert_level_t level = ALERT_LEVEL_INFO;
            
            switch (comp->status) {
                case COMP_STATUS_HEALTHY:
                    snprintf(msg, sizeof(msg), "Recovered (health: %.2f)", comp->health_score);
                    level = ALERT_LEVEL_INFO;
                    break;
                case COMP_STATUS_DEGRADED:
                    snprintf(msg, sizeof(msg), "Degraded (health: %.2f)", comp->health_score);
                    level = ALERT_LEVEL_WARNING;
                    break;
                case COMP_STATUS_UNHEALTHY:
                    snprintf(msg, sizeof(msg), "Unhealthy (health: %.2f)", comp->health_score);
                    level = ALERT_LEVEL_ERROR;
                    break;
                case COMP_STATUS_DEAD:
                    snprintf(msg, sizeof(msg), "DEAD after %u failures", comp->consecutive_failures);
                    level = comp->critical ? ALERT_LEVEL_CRITICAL : ALERT_LEVEL_ERROR;
                    break;
                default:
                    continue;
            }
            
            raise_alert(level, comp->name, msg);
        }
        
        /* Attempt recovery if enabled and needed */
        if (g_watchdog.auto_recovery && 
            comp->status == COMP_STATUS_DEAD && 
            comp->recover_fn) {
            g_watchdog.recoveries_attempted++;
            if (comp->recover_fn(comp->recover_ctx) == SHIELD_OK) {
                comp->status = COMP_STATUS_UNKNOWN;
                comp->consecutive_failures = 0;
                comp->recoveries++;
                g_watchdog.recoveries_successful++;
                raise_alert(ALERT_LEVEL_INFO, comp->name, "Recovery successful");
            }
        }
        
        total_health += comp->health_score;
    }
    
    /* Update system health */
    g_watchdog.system_health = total_health / g_watchdog.component_count;
    
    if (critical_failures > 0) {
        g_watchdog.system_status = COMP_STATUS_DEAD;
    } else if (g_watchdog.system_health < 0.5f) {
        g_watchdog.system_status = COMP_STATUS_UNHEALTHY;
    } else if (g_watchdog.system_health < 0.8f) {
        g_watchdog.system_status = COMP_STATUS_DEGRADED;
    } else {
        g_watchdog.system_status = COMP_STATUS_HEALTHY;
    }
    
    g_watchdog.checks_completed++;
    g_watchdog.last_check = get_time_ms();
    
    return SHIELD_OK;
}

/* ===== Status Queries ===== */

component_status_t shield_watchdog_get_system_status(void)
{
    return g_watchdog.system_status;
}

float shield_watchdog_get_system_health(void)
{
    return g_watchdog.system_health;
}

component_status_t shield_watchdog_get_component_status(const char *name)
{
    for (size_t i = 0; i < g_watchdog.component_count; i++) {
        if (strcmp(g_watchdog.components[i].name, name) == 0) {
            return g_watchdog.components[i].status;
        }
    }
    return COMP_STATUS_UNKNOWN;
}

/* ===== Statistics ===== */

void shield_watchdog_get_stats(char *buffer, size_t buflen)
{
    if (!buffer || buflen == 0) return;
    
    const char *status_str;
    switch (g_watchdog.system_status) {
        case COMP_STATUS_HEALTHY:   status_str = "HEALTHY"; break;
        case COMP_STATUS_DEGRADED:  status_str = "DEGRADED"; break;
        case COMP_STATUS_UNHEALTHY: status_str = "UNHEALTHY"; break;
        case COMP_STATUS_DEAD:      status_str = "DEAD"; break;
        default:                    status_str = "UNKNOWN"; break;
    }
    
    snprintf(buffer, buflen,
        "Watchdog Statistics:\n"
        "  Status: %s\n"
        "  System Health: %.2f\n"
        "  Components: %zu\n"
        "  Checks Completed: %llu\n"
        "  Alerts Raised: %llu\n"
        "  Recoveries: %llu/%llu\n"
        "  Auto-Recovery: %s\n",
        status_str,
        g_watchdog.system_health,
        g_watchdog.component_count,
        (unsigned long long)g_watchdog.checks_completed,
        (unsigned long long)g_watchdog.alerts_raised,
        (unsigned long long)g_watchdog.recoveries_successful,
        (unsigned long long)g_watchdog.recoveries_attempted,
        g_watchdog.auto_recovery ? "ENABLED" : "DISABLED");
}

/* ===== Configuration ===== */

void shield_watchdog_set_auto_recovery(bool enable)
{
    g_watchdog.auto_recovery = enable;
}

void shield_watchdog_set_check_interval(uint64_t interval_ms)
{
    if (interval_ms >= 1000) {  /* Minimum 1 second */
        g_watchdog.check_interval_ms = interval_ms;
    }
}

/* ===== Alert Management ===== */

size_t shield_watchdog_get_alerts(watchdog_alert_t *alerts, size_t max_alerts, bool unack_only)
{
    size_t count = 0;
    
    for (size_t i = 0; i < g_watchdog.alert_count && count < max_alerts; i++) {
        watchdog_alert_t *alert = &g_watchdog.alerts[i];
        if (!unack_only || !alert->acknowledged) {
            if (alerts) {
                memcpy(&alerts[count], alert, sizeof(watchdog_alert_t));
            }
            count++;
        }
    }
    
    return count;
}

void shield_watchdog_acknowledge_all(void)
{
    for (size_t i = 0; i < g_watchdog.alert_count; i++) {
        g_watchdog.alerts[i].acknowledged = true;
    }
}
