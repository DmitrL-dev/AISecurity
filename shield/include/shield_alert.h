/*
 * SENTINEL Shield - Alert Manager
 * 
 * Manage security alerts and notifications
 */

#ifndef SHIELD_ALERT_H
#define SHIELD_ALERT_H

#include "shield_common.h"

/* Alert severity */
typedef enum alert_severity {
    ALERT_INFO = 0,
    ALERT_WARNING = 1,
    ALERT_ERROR = 2,
    ALERT_CRITICAL = 3,
} alert_severity_t;

/* Alert */
typedef struct shield_alert {
    char            id[64];
    uint64_t        timestamp;
    alert_severity_t severity;
    char            source[64];
    char            title[128];
    char            description[512];
    
    /* Context */
    char            zone[64];
    char            session_id[64];
    uint32_t        rule;
    
    /* State */
    bool            firing;
    bool            acknowledged;
    char            ack_by[64];
    uint64_t        ack_time;
    
    /* Notification */
    bool            notification_sent;
    uint64_t        notification_time;
    
    struct shield_alert *next;
} shield_alert_t;

/* Alert handler (for webhooks, email, etc) */
typedef void (*alert_handler_t)(const shield_alert_t *alert, void *ctx);

/* Alert channel */
typedef struct alert_channel {
    char            name[64];
    char            type[32];       /* webhook, email, slack, pagerduty */
    char            endpoint[256];
    alert_severity_t min_severity;
    alert_handler_t handler;
    void            *ctx;
    bool            enabled;
    struct alert_channel *next;
} alert_channel_t;

/* Alert manager */
typedef struct alert_manager {
    shield_alert_t  *alerts;
    int             count;
    int             max_alerts;
    
    alert_channel_t *channels;
    int             channel_count;
    
    /* Rate limiting */
    uint64_t        rate_limit_ms;
    uint64_t        last_alert_time;
    int             alerts_in_window;
    int             max_alerts_per_window;
    
    /* Stats */
    uint64_t        total_alerts;
    uint64_t        alerts_by_severity[4];
} alert_manager_t;

/* API */
shield_err_t alert_manager_init(alert_manager_t *mgr, int max_alerts);
void alert_manager_destroy(alert_manager_t *mgr);

/* Fire alert */
shield_err_t alert_fire(alert_manager_t *mgr,
                         alert_severity_t severity,
                         const char *source, const char *title,
                         const char *description,
                         const char *zone, const char *session_id, uint32_t rule);

/* Resolve alert */
shield_err_t alert_resolve(alert_manager_t *mgr, const char *id);

/* Acknowledge */
shield_err_t alert_acknowledge(alert_manager_t *mgr, const char *id, const char *by);

/* Channels */
shield_err_t alert_add_channel(alert_manager_t *mgr, const char *name,
                                const char *type, const char *endpoint,
                                alert_severity_t min_severity);
shield_err_t alert_remove_channel(alert_manager_t *mgr, const char *name);
void alert_set_channel_handler(alert_manager_t *mgr, const char *name,
                                alert_handler_t handler, void *ctx);

/* Query */
shield_alert_t *alert_get(alert_manager_t *mgr, const char *id);
int alert_list_firing(alert_manager_t *mgr, shield_alert_t **alerts, int max_count);
int alert_count_by_severity(alert_manager_t *mgr, alert_severity_t severity);

/* Helpers */
const char *alert_severity_string(alert_severity_t severity);

#endif /* SHIELD_ALERT_H */
