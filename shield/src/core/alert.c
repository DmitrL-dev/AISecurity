/*
 * SENTINEL Shield - Alert Manager Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "shield_common.h"
#include "shield_alert.h"

/* Generate alert ID */
static void generate_alert_id(char *id, size_t len)
{
    static uint64_t counter = 0;
    snprintf(id, len, "alert-%lu-%lu", (unsigned long)time(NULL), (unsigned long)++counter);
}

/* Initialize */
shield_err_t alert_manager_init(alert_manager_t *mgr, int max_alerts)
{
    if (!mgr) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(mgr, 0, sizeof(*mgr));
    mgr->max_alerts = max_alerts > 0 ? max_alerts : 1000;
    mgr->rate_limit_ms = 60000; /* 1 minute */
    mgr->max_alerts_per_window = 100;
    
    return SHIELD_OK;
}

/* Destroy */
void alert_manager_destroy(alert_manager_t *mgr)
{
    if (!mgr) return;
    
    shield_alert_t *alert = mgr->alerts;
    while (alert) {
        shield_alert_t *next = alert->next;
        free(alert);
        alert = next;
    }
    
    alert_channel_t *channel = mgr->channels;
    while (channel) {
        alert_channel_t *next = channel->next;
        free(channel);
        channel = next;
    }
    
    mgr->alerts = NULL;
    mgr->channels = NULL;
}

/* Notify channels */
static void notify_channels(alert_manager_t *mgr, const shield_alert_t *alert)
{
    alert_channel_t *channel = mgr->channels;
    while (channel) {
        if (channel->enabled && 
            alert->severity >= channel->min_severity &&
            channel->handler) {
            channel->handler(alert, channel->ctx);
        }
        channel = channel->next;
    }
}

/* Fire alert */
shield_err_t alert_fire(alert_manager_t *mgr,
                         alert_severity_t severity,
                         const char *source, const char *title,
                         const char *description,
                         const char *zone, const char *session_id, uint32_t rule)
{
    if (!mgr) {
        return SHIELD_ERR_INVALID;
    }
    
    uint64_t now = (uint64_t)time(NULL) * 1000;
    
    /* Rate limiting */
    if (now - mgr->last_alert_time < mgr->rate_limit_ms) {
        mgr->alerts_in_window++;
        if (mgr->alerts_in_window > mgr->max_alerts_per_window) {
            LOG_WARN("Alert rate limit exceeded");
            return SHIELD_ERR_RATELIMIT;
        }
    } else {
        mgr->alerts_in_window = 1;
        mgr->last_alert_time = now;
    }
    
    /* Create alert */
    shield_alert_t *alert = calloc(1, sizeof(shield_alert_t));
    if (!alert) {
        return SHIELD_ERR_NOMEM;
    }
    
    generate_alert_id(alert->id, sizeof(alert->id));
    alert->timestamp = now / 1000;
    alert->severity = severity;
    alert->firing = true;
    alert->rule = rule;
    
    if (source) strncpy(alert->source, source, sizeof(alert->source) - 1);
    if (title) strncpy(alert->title, title, sizeof(alert->title) - 1);
    if (description) strncpy(alert->description, description, sizeof(alert->description) - 1);
    if (zone) strncpy(alert->zone, zone, sizeof(alert->zone) - 1);
    if (session_id) strncpy(alert->session_id, session_id, sizeof(alert->session_id) - 1);
    
    /* Add to list */
    alert->next = mgr->alerts;
    mgr->alerts = alert;
    mgr->count++;
    mgr->total_alerts++;
    mgr->alerts_by_severity[severity]++;
    
    /* Notify channels */
    notify_channels(mgr, alert);
    alert->notification_sent = true;
    alert->notification_time = now / 1000;
    
    LOG_INFO("Alert: [%s] %s - %s", 
             alert_severity_string(severity), source, title);
    
    /* Cleanup old alerts */
    if (mgr->count > mgr->max_alerts) {
        /* Remove oldest */
        shield_alert_t **pp = &mgr->alerts;
        while (*pp && (*pp)->next) {
            pp = &(*pp)->next;
        }
        if (*pp) {
            free(*pp);
            *pp = NULL;
            mgr->count--;
        }
    }
    
    return SHIELD_OK;
}

/* Resolve alert */
shield_err_t alert_resolve(alert_manager_t *mgr, const char *id)
{
    shield_alert_t *alert = alert_get(mgr, id);
    if (!alert) {
        return SHIELD_ERR_NOTFOUND;
    }
    
    alert->firing = false;
    LOG_INFO("Alert resolved: %s", id);
    
    return SHIELD_OK;
}

/* Acknowledge */
shield_err_t alert_acknowledge(alert_manager_t *mgr, const char *id, const char *by)
{
    shield_alert_t *alert = alert_get(mgr, id);
    if (!alert) {
        return SHIELD_ERR_NOTFOUND;
    }
    
    alert->acknowledged = true;
    alert->ack_time = (uint64_t)time(NULL);
    if (by) strncpy(alert->ack_by, by, sizeof(alert->ack_by) - 1);
    
    LOG_INFO("Alert acknowledged: %s by %s", id, by ? by : "unknown");
    
    return SHIELD_OK;
}

/* Add channel */
shield_err_t alert_add_channel(alert_manager_t *mgr, const char *name,
                                const char *type, const char *endpoint,
                                alert_severity_t min_severity)
{
    if (!mgr || !name || !type) {
        return SHIELD_ERR_INVALID;
    }
    
    alert_channel_t *channel = calloc(1, sizeof(alert_channel_t));
    if (!channel) {
        return SHIELD_ERR_NOMEM;
    }
    
    strncpy(channel->name, name, sizeof(channel->name) - 1);
    strncpy(channel->type, type, sizeof(channel->type) - 1);
    if (endpoint) strncpy(channel->endpoint, endpoint, sizeof(channel->endpoint) - 1);
    channel->min_severity = min_severity;
    channel->enabled = true;
    
    channel->next = mgr->channels;
    mgr->channels = channel;
    mgr->channel_count++;
    
    return SHIELD_OK;
}

/* Remove channel */
shield_err_t alert_remove_channel(alert_manager_t *mgr, const char *name)
{
    if (!mgr || !name) {
        return SHIELD_ERR_INVALID;
    }
    
    alert_channel_t **pp = &mgr->channels;
    while (*pp) {
        if (strcmp((*pp)->name, name) == 0) {
            alert_channel_t *channel = *pp;
            *pp = channel->next;
            free(channel);
            mgr->channel_count--;
            return SHIELD_OK;
        }
        pp = &(*pp)->next;
    }
    
    return SHIELD_ERR_NOTFOUND;
}

/* Set channel handler */
void alert_set_channel_handler(alert_manager_t *mgr, const char *name,
                                alert_handler_t handler, void *ctx)
{
    if (!mgr || !name) return;
    
    alert_channel_t *channel = mgr->channels;
    while (channel) {
        if (strcmp(channel->name, name) == 0) {
            channel->handler = handler;
            channel->ctx = ctx;
            return;
        }
        channel = channel->next;
    }
}

/* Get alert */
shield_alert_t *alert_get(alert_manager_t *mgr, const char *id)
{
    if (!mgr || !id) return NULL;
    
    shield_alert_t *alert = mgr->alerts;
    while (alert) {
        if (strcmp(alert->id, id) == 0) {
            return alert;
        }
        alert = alert->next;
    }
    
    return NULL;
}

/* List firing alerts */
int alert_list_firing(alert_manager_t *mgr, shield_alert_t **alerts, int max_count)
{
    if (!mgr || !alerts) return 0;
    
    int count = 0;
    shield_alert_t *alert = mgr->alerts;
    
    while (alert && count < max_count) {
        if (alert->firing) {
            alerts[count++] = alert;
        }
        alert = alert->next;
    }
    
    return count;
}

/* Count by severity */
int alert_count_by_severity(alert_manager_t *mgr, alert_severity_t severity)
{
    if (!mgr || severity > ALERT_CRITICAL) return 0;
    
    int count = 0;
    shield_alert_t *alert = mgr->alerts;
    
    while (alert) {
        if (alert->firing && alert->severity == severity) {
            count++;
        }
        alert = alert->next;
    }
    
    return count;
}

/* Severity string */
const char *alert_severity_string(alert_severity_t severity)
{
    switch (severity) {
    case ALERT_INFO: return "INFO";
    case ALERT_WARNING: return "WARNING";
    case ALERT_ERROR: return "ERROR";
    case ALERT_CRITICAL: return "CRITICAL";
    default: return "UNKNOWN";
    }
}
