/*
 * SENTINEL Shield - Webhook Notifier
 */

#ifndef SHIELD_WEBHOOK_H
#define SHIELD_WEBHOOK_H

#include "shield_common.h"
#include "shield_alert.h"

/* Webhook format */
typedef enum webhook_format {
    WEBHOOK_FORMAT_JSON,
    WEBHOOK_FORMAT_SLACK,
    WEBHOOK_FORMAT_DISCORD,
    WEBHOOK_FORMAT_PAGERDUTY,
    WEBHOOK_FORMAT_OPSGENIE,
} webhook_format_t;

/* Webhook config */
typedef struct webhook_config {
    char            name[64];
    char            url[512];
    webhook_format_t format;
    bool            enabled;
    
    /* Auth */
    char            auth_header[128];
    char            auth_token[256];
    
    /* Rate limit */
    uint32_t        rate_limit_per_min;
    uint64_t        last_send_time;
    int             sends_this_minute;
    
    /* Retry */
    int             max_retries;
    int             retry_delay_ms;
    
    /* TLS */
    bool            verify_tls;
    
    struct webhook_config *next;
} webhook_config_t;

/* Webhook manager */
typedef struct webhook_manager {
    webhook_config_t *webhooks;
    int             count;
    bool            initialized;
} webhook_manager_t;

/* API */
shield_err_t webhook_manager_init(webhook_manager_t *mgr);
void webhook_manager_destroy(webhook_manager_t *mgr);

shield_err_t webhook_add(webhook_manager_t *mgr, const char *name,
                          const char *url, webhook_format_t format);
shield_err_t webhook_remove(webhook_manager_t *mgr, const char *name);

shield_err_t webhook_set_auth(webhook_manager_t *mgr, const char *name,
                               const char *header, const char *token);

/* Send alert */
shield_err_t webhook_send_alert(webhook_manager_t *mgr, const char *name,
                                  const shield_alert_t *alert);
shield_err_t webhook_broadcast_alert(webhook_manager_t *mgr,
                                       const shield_alert_t *alert);

/* Send raw */
shield_err_t webhook_send_raw(webhook_manager_t *mgr, const char *name,
                                const char *payload, size_t len);

/* Format helpers */
char *webhook_format_alert_json(const shield_alert_t *alert);
char *webhook_format_alert_slack(const shield_alert_t *alert);
char *webhook_format_alert_discord(const shield_alert_t *alert);

#endif /* SHIELD_WEBHOOK_H */
