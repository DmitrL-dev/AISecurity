/*
 * SENTINEL Shield - Health Check & Watchdog Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "shield_common.h"
#include "shield_health.h"
#include "shield_platform.h"

/* Get time in milliseconds */
static uint64_t get_time_ms(void)
{
    return platform_time_ms();
}

/* Initialize health manager */
shield_err_t health_manager_init(health_manager_t *mgr)
{
    if (!mgr) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(mgr, 0, sizeof(*mgr));
    mgr->overall_status = HEALTH_UNKNOWN;
    mgr->running = true;
    
    return SHIELD_OK;
}

/* Destroy */
void health_manager_destroy(health_manager_t *mgr)
{
    if (!mgr) {
        return;
    }
    
    health_probe_t *probe = mgr->probes;
    while (probe) {
        health_probe_t *next = probe->next;
        free(probe);
        probe = next;
    }
    
    mgr->probes = NULL;
    mgr->probe_count = 0;
}

/* Add probe */
shield_err_t health_add_probe(health_manager_t *mgr, const char *name,
                               health_check_fn check, void *ctx,
                               uint32_t interval_ms, uint32_t timeout_ms)
{
    if (!mgr || !name || !check) {
        return SHIELD_ERR_INVALID;
    }
    
    health_probe_t *probe = calloc(1, sizeof(health_probe_t));
    if (!probe) {
        return SHIELD_ERR_NOMEM;
    }
    
    strncpy(probe->name, name, sizeof(probe->name) - 1);
    probe->check = check;
    probe->ctx = ctx;
    probe->interval_ms = interval_ms > 0 ? interval_ms : 10000;
    probe->timeout_ms = timeout_ms > 0 ? timeout_ms : 5000;
    probe->failures_threshold = 3;
    probe->status = HEALTH_UNKNOWN;
    
    probe->next = mgr->probes;
    mgr->probes = probe;
    mgr->probe_count++;
    
    return SHIELD_OK;
}

/* Remove probe */
shield_err_t health_remove_probe(health_manager_t *mgr, const char *name)
{
    if (!mgr || !name) {
        return SHIELD_ERR_INVALID;
    }
    
    health_probe_t **pp = &mgr->probes;
    while (*pp) {
        if (strcmp((*pp)->name, name) == 0) {
            health_probe_t *probe = *pp;
            *pp = probe->next;
            free(probe);
            mgr->probe_count--;
            return SHIELD_OK;
        }
        pp = &(*pp)->next;
    }
    
    return SHIELD_ERR_NOTFOUND;
}

/* Check all probes */
health_status_t health_check_all(health_manager_t *mgr)
{
    if (!mgr) {
        return HEALTH_UNKNOWN;
    }
    
    health_status_t worst = HEALTH_OK;
    uint64_t now = get_time_ms();
    
    health_probe_t *probe = mgr->probes;
    while (probe) {
        /* Check if due */
        if (now - probe->last_check >= probe->interval_ms) {
            uint64_t start = platform_time_us();
            
            char message[128] = "";
            probe->status = probe->check(probe->ctx, message, sizeof(message));
            strncpy(probe->last_message, message, sizeof(probe->last_message) - 1);
            
            probe->last_check = now;
            
            /* Track failures */
            if (probe->status != HEALTH_OK) {
                probe->consecutive_failures++;
            } else {
                probe->consecutive_failures = 0;
            }
            
            (void)start; /* TODO: Track check duration */
        }
        
        /* Update worst status */
        if (probe->status > worst) {
            worst = probe->status;
        }
        
        probe = probe->next;
    }
    
    /* Update overall */
    health_status_t old_status = mgr->overall_status;
    mgr->overall_status = worst;
    
    if (old_status != worst && mgr->on_status_change) {
        mgr->on_status_change(old_status, worst, mgr->callback_ctx);
    }
    
    return worst;
}

/* Get overall status */
health_status_t health_get_status(health_manager_t *mgr)
{
    return mgr ? mgr->overall_status : HEALTH_UNKNOWN;
}

/* Get component status */
component_health_t health_get_component(health_manager_t *mgr, const char *name)
{
    component_health_t result = {0};
    result.status = HEALTH_UNKNOWN;
    
    if (!mgr || !name) {
        return result;
    }
    
    health_probe_t *probe = mgr->probes;
    while (probe) {
        if (strcmp(probe->name, name) == 0) {
            strncpy(result.name, probe->name, sizeof(result.name) - 1);
            result.status = probe->status;
            strncpy(result.message, probe->last_message, sizeof(result.message) - 1);
            result.last_check = probe->last_check;
            return result;
        }
        probe = probe->next;
    }
    
    return result;
}

/* Export as JSON */
char *health_export_json(health_manager_t *mgr)
{
    if (!mgr) {
        return NULL;
    }
    
    char *buf = malloc(4096);
    if (!buf) {
        return NULL;
    }
    
    size_t pos = 0;
    pos += snprintf(buf + pos, 4096 - pos,
        "{\"status\":\"%s\",\"components\":[",
        health_status_string(mgr->overall_status));
    
    bool first = true;
    health_probe_t *probe = mgr->probes;
    while (probe && pos < 3900) {
        if (!first) buf[pos++] = ',';
        first = false;
        
        pos += snprintf(buf + pos, 4096 - pos,
            "{\"name\":\"%s\",\"status\":\"%s\",\"message\":\"%s\"}",
            probe->name,
            health_status_string(probe->status),
            probe->last_message);
        
        probe = probe->next;
    }
    
    pos += snprintf(buf + pos, 4096 - pos, "]}");
    
    return buf;
}

/* Status to string */
const char *health_status_string(health_status_t status)
{
    switch (status) {
    case HEALTH_OK: return "ok";
    case HEALTH_DEGRADED: return "degraded";
    case HEALTH_CRITICAL: return "critical";
    default: return "unknown";
    }
}

/* ===== Watchdog ===== */

shield_err_t watchdog_init(watchdog_t *wd, uint64_t timeout_ms)
{
    if (!wd) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(wd, 0, sizeof(*wd));
    wd->timeout_ms = timeout_ms;
    wd->last_ping = get_time_ms();
    wd->enabled = true;
    
    return SHIELD_OK;
}

void watchdog_destroy(watchdog_t *wd)
{
    if (wd) {
        wd->enabled = false;
    }
}

void watchdog_ping(watchdog_t *wd)
{
    if (wd) {
        wd->last_ping = get_time_ms();
        wd->triggered = false;
    }
}

bool watchdog_check(watchdog_t *wd)
{
    if (!wd || !wd->enabled) {
        return true;
    }
    
    uint64_t now = get_time_ms();
    if (now - wd->last_ping > wd->timeout_ms) {
        if (!wd->triggered) {
            wd->triggered = true;
            if (wd->on_timeout) {
                wd->on_timeout(wd->ctx);
            }
        }
        return false;
    }
    
    return true;
}

void watchdog_enable(watchdog_t *wd, bool enable)
{
    if (wd) {
        wd->enabled = enable;
        if (enable) {
            wd->last_ping = get_time_ms();
        }
    }
}

void watchdog_set_callback(watchdog_t *wd, void (*cb)(void *), void *ctx)
{
    if (wd) {
        wd->on_timeout = cb;
        wd->ctx = ctx;
    }
}
