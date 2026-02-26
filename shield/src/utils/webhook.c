/*
 * SENTINEL Shield - Webhook Notifier Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "shield_common.h"
#include "shield_webhook.h"
#include "shield_platform.h"

/* Initialize */
shield_err_t webhook_manager_init(webhook_manager_t *mgr)
{
    if (!mgr) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(mgr, 0, sizeof(*mgr));
    mgr->initialized = true;
    
    return SHIELD_OK;
}

/* Destroy */
void webhook_manager_destroy(webhook_manager_t *mgr)
{
    if (!mgr) return;
    
    webhook_config_t *wh = mgr->webhooks;
    while (wh) {
        webhook_config_t *next = wh->next;
        free(wh);
        wh = next;
    }
    
    mgr->webhooks = NULL;
    mgr->count = 0;
    mgr->initialized = false;
}

/* Add webhook */
shield_err_t webhook_add(webhook_manager_t *mgr, const char *name,
                          const char *url, webhook_format_t format)
{
    if (!mgr || !name || !url) {
        return SHIELD_ERR_INVALID;
    }
    
    webhook_config_t *wh = calloc(1, sizeof(webhook_config_t));
    if (!wh) {
        return SHIELD_ERR_NOMEM;
    }
    
    strncpy(wh->name, name, sizeof(wh->name) - 1);
    strncpy(wh->url, url, sizeof(wh->url) - 1);
    wh->format = format;
    wh->enabled = true;
    wh->rate_limit_per_min = 60;
    wh->max_retries = 3;
    wh->retry_delay_ms = 1000;
    wh->verify_tls = true;
    
    wh->next = mgr->webhooks;
    mgr->webhooks = wh;
    mgr->count++;
    
    LOG_INFO("Webhook added: %s -> %s", name, url);
    
    return SHIELD_OK;
}

/* Remove webhook */
shield_err_t webhook_remove(webhook_manager_t *mgr, const char *name)
{
    if (!mgr || !name) {
        return SHIELD_ERR_INVALID;
    }
    
    webhook_config_t **pp = &mgr->webhooks;
    while (*pp) {
        if (strcmp((*pp)->name, name) == 0) {
            webhook_config_t *wh = *pp;
            *pp = wh->next;
            free(wh);
            mgr->count--;
            return SHIELD_OK;
        }
        pp = &(*pp)->next;
    }
    
    return SHIELD_ERR_NOTFOUND;
}

/* Set auth */
shield_err_t webhook_set_auth(webhook_manager_t *mgr, const char *name,
                               const char *header, const char *token)
{
    if (!mgr || !name) {
        return SHIELD_ERR_INVALID;
    }
    
    webhook_config_t *wh = mgr->webhooks;
    while (wh) {
        if (strcmp(wh->name, name) == 0) {
            if (header) strncpy(wh->auth_header, header, sizeof(wh->auth_header) - 1);
            if (token) strncpy(wh->auth_token, token, sizeof(wh->auth_token) - 1);
            return SHIELD_OK;
        }
        wh = wh->next;
    }
    
    return SHIELD_ERR_NOTFOUND;
}

/* HTTP POST (simplified - requires libcurl in real implementation) */
static shield_err_t http_post(const char *url, const char *payload,
                               const char *auth_header, const char *auth_token)
{
    LOG_DEBUG("Webhook POST to %s: %zu bytes", url, strlen(payload));
    
    /* In a real implementation, use libcurl:
     *
     * CURL *curl = curl_easy_init();
     * curl_easy_setopt(curl, CURLOPT_URL, url);
     * curl_easy_setopt(curl, CURLOPT_POSTFIELDS, payload);
     * 
     * struct curl_slist *headers = NULL;
     * headers = curl_slist_append(headers, "Content-Type: application/json");
     * if (auth_header && auth_token) {
     *     char auth[512];
     *     snprintf(auth, sizeof(auth), "%s: %s", auth_header, auth_token);
     *     headers = curl_slist_append(headers, auth);
     * }
     * curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
     * 
     * CURLcode res = curl_easy_perform(curl);
     * curl_slist_free_all(headers);
     * curl_easy_cleanup(curl);
     */
    
    (void)auth_header;
    (void)auth_token;
    
    /* Stub - log payload */
    LOG_INFO("Webhook: %s", payload);
    
    return SHIELD_OK;
}

/* Format alert as JSON */
char *webhook_format_alert_json(const shield_alert_t *alert)
{
    if (!alert) return strdup("{}");
    
    char *buf = malloc(2048);
    if (!buf) return NULL;
    
    snprintf(buf, 2048,
        "{"
        "\"id\":\"%s\","
        "\"timestamp\":%lu,"
        "\"severity\":\"%s\","
        "\"source\":\"%s\","
        "\"title\":\"%s\","
        "\"description\":\"%s\","
        "\"zone\":\"%s\","
        "\"firing\":%s"
        "}",
        alert->id,
        (unsigned long)alert->timestamp,
        alert_severity_string(alert->severity),
        alert->source,
        alert->title,
        alert->description,
        alert->zone,
        alert->firing ? "true" : "false"
    );
    
    return buf;
}

/* Format alert for Slack */
char *webhook_format_alert_slack(const shield_alert_t *alert)
{
    if (!alert) return strdup("{}");
    
    const char *color;
    switch (alert->severity) {
    case ALERT_CRITICAL: color = "danger"; break;
    case ALERT_ERROR: color = "danger"; break;
    case ALERT_WARNING: color = "warning"; break;
    default: color = "good"; break;
    }
    
    char *buf = malloc(2048);
    if (!buf) return NULL;
    
    snprintf(buf, 2048,
        "{"
        "\"attachments\":[{"
        "\"color\":\"%s\","
        "\"title\":\"%s\","
        "\"text\":\"%s\","
        "\"fields\":["
        "{\"title\":\"Severity\",\"value\":\"%s\",\"short\":true},"
        "{\"title\":\"Zone\",\"value\":\"%s\",\"short\":true}"
        "]"
        "}]"
        "}",
        color,
        alert->title,
        alert->description,
        alert_severity_string(alert->severity),
        alert->zone
    );
    
    return buf;
}

/* Format alert for Discord */
char *webhook_format_alert_discord(const shield_alert_t *alert)
{
    if (!alert) return strdup("{}");
    
    int color;
    switch (alert->severity) {
    case ALERT_CRITICAL: color = 0xFF0000; break;
    case ALERT_ERROR: color = 0xFF6600; break;
    case ALERT_WARNING: color = 0xFFFF00; break;
    default: color = 0x00FF00; break;
    }
    
    char *buf = malloc(2048);
    if (!buf) return NULL;
    
    snprintf(buf, 2048,
        "{"
        "\"embeds\":[{"
        "\"title\":\"%s\","
        "\"description\":\"%s\","
        "\"color\":%d,"
        "\"fields\":["
        "{\"name\":\"Severity\",\"value\":\"%s\",\"inline\":true},"
        "{\"name\":\"Zone\",\"value\":\"%s\",\"inline\":true}"
        "]"
        "}]"
        "}",
        alert->title,
        alert->description,
        color,
        alert_severity_string(alert->severity),
        alert->zone
    );
    
    return buf;
}

/* Send alert */
shield_err_t webhook_send_alert(webhook_manager_t *mgr, const char *name,
                                  const shield_alert_t *alert)
{
    if (!mgr || !name || !alert) {
        return SHIELD_ERR_INVALID;
    }
    
    webhook_config_t *wh = mgr->webhooks;
    while (wh) {
        if (strcmp(wh->name, name) == 0) {
            if (!wh->enabled) {
                return SHIELD_ERR_INVALID;
            }
            
            /* Rate limit check */
            uint64_t now = (uint64_t)time(NULL);
            if (now - wh->last_send_time >= 60) {
                wh->sends_this_minute = 0;
                wh->last_send_time = now;
            }
            
            if ((uint32_t)wh->sends_this_minute >= wh->rate_limit_per_min) {
                return SHIELD_ERR_RATELIMIT;
            }
            
            /* Format payload */
            char *payload;
            switch (wh->format) {
            case WEBHOOK_FORMAT_SLACK:
                payload = webhook_format_alert_slack(alert);
                break;
            case WEBHOOK_FORMAT_DISCORD:
                payload = webhook_format_alert_discord(alert);
                break;
            default:
                payload = webhook_format_alert_json(alert);
                break;
            }
            
            if (!payload) {
                return SHIELD_ERR_NOMEM;
            }
            
            /* Send */
            shield_err_t err = http_post(wh->url, payload,
                                           wh->auth_header[0] ? wh->auth_header : NULL,
                                           wh->auth_token[0] ? wh->auth_token : NULL);
            
            free(payload);
            wh->sends_this_minute++;
            
            return err;
        }
        wh = wh->next;
    }
    
    return SHIELD_ERR_NOTFOUND;
}

/* Broadcast to all webhooks */
shield_err_t webhook_broadcast_alert(webhook_manager_t *mgr,
                                       const shield_alert_t *alert)
{
    if (!mgr || !alert) {
        return SHIELD_ERR_INVALID;
    }
    
    webhook_config_t *wh = mgr->webhooks;
    while (wh) {
        if (wh->enabled) {
            webhook_send_alert(mgr, wh->name, alert);
        }
        wh = wh->next;
    }
    
    return SHIELD_OK;
}

/* Send raw payload */
shield_err_t webhook_send_raw(webhook_manager_t *mgr, const char *name,
                                const char *payload, size_t len)
{
    if (!mgr || !name || !payload) {
        return SHIELD_ERR_INVALID;
    }
    
    (void)len;
    
    webhook_config_t *wh = mgr->webhooks;
    while (wh) {
        if (strcmp(wh->name, name) == 0) {
            return http_post(wh->url, payload,
                             wh->auth_header[0] ? wh->auth_header : NULL,
                             wh->auth_token[0] ? wh->auth_token : NULL);
        }
        wh = wh->next;
    }
    
    return SHIELD_ERR_NOTFOUND;
}
