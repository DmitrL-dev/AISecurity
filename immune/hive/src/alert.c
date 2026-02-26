/*
 * SENTINEL IMMUNE — Hive Alerting Module
 * 
 * Multi-channel threat alerting.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#ifdef _WIN32
    #include <windows.h>
#else
    #include <unistd.h>
    #include <sys/socket.h>
    #include <netinet/in.h>
    #include <arpa/inet.h>
#endif

#include "../include/hive.h"

#define MAX_CHANNELS        20
#define ALERT_BUFFER_SIZE   4096

/* Alert channels */
typedef enum {
    CHANNEL_CONSOLE = 1,
    CHANNEL_SYSLOG,
    CHANNEL_FILE,
    CHANNEL_WEBHOOK,
    CHANNEL_EMAIL,
    CHANNEL_SLACK,
    CHANNEL_PAGERDUTY
} channel_type_t;

/* Alert priority */
typedef enum {
    PRIORITY_LOW = 1,
    PRIORITY_MEDIUM = 2,
    PRIORITY_HIGH = 3,
    PRIORITY_CRITICAL = 4
} alert_priority_t;

/* Channel configuration */
typedef struct {
    channel_type_t  type;
    int             enabled;
    int             min_priority;
    char            config[256];    /* URL, path, etc. */
} alert_channel_t;

/* Alert context */
typedef struct {
    alert_channel_t channels[MAX_CHANNELS];
    int             channel_count;
    
    char            log_path[256];
    FILE            *log_file;
    
    uint64_t        alerts_sent;
    uint64_t        alerts_failed;
} alert_ctx_t;

/* Global context */
static alert_ctx_t g_alert;

/* ==================== Initialization ==================== */

int
alert_init(const char *log_path)
{
    memset(&g_alert, 0, sizeof(alert_ctx_t));
    
    /* Default: console channel */
    g_alert.channels[0].type = CHANNEL_CONSOLE;
    g_alert.channels[0].enabled = 1;
    g_alert.channels[0].min_priority = PRIORITY_LOW;
    g_alert.channel_count = 1;
    
    /* File logging */
    if (log_path) {
        strncpy(g_alert.log_path, log_path, sizeof(g_alert.log_path) - 1);
        g_alert.log_file = fopen(log_path, "a");
        
        if (g_alert.log_file) {
            g_alert.channels[1].type = CHANNEL_FILE;
            g_alert.channels[1].enabled = 1;
            g_alert.channels[1].min_priority = PRIORITY_LOW;
            strncpy(g_alert.channels[1].config, log_path,
                    sizeof(g_alert.channels[1].config) - 1);
            g_alert.channel_count = 2;
        }
    }
    
    printf("ALERT: Alerting module initialized\n");
    return 0;
}

void
alert_shutdown(void)
{
    if (g_alert.log_file) {
        fclose(g_alert.log_file);
        g_alert.log_file = NULL;
    }
    
    printf("ALERT: Sent %lu alerts, %lu failed\n",
           g_alert.alerts_sent, g_alert.alerts_failed);
}

/* ==================== Channel Management ==================== */

int
alert_add_channel(channel_type_t type, const char *config, int min_priority)
{
    if (g_alert.channel_count >= MAX_CHANNELS)
        return -1;
    
    alert_channel_t *ch = &g_alert.channels[g_alert.channel_count];
    
    ch->type = type;
    ch->enabled = 1;
    ch->min_priority = min_priority;
    
    if (config) {
        strncpy(ch->config, config, sizeof(ch->config) - 1);
    }
    
    g_alert.channel_count++;
    return 0;
}

int
alert_add_webhook(const char *url, int min_priority)
{
    return alert_add_channel(CHANNEL_WEBHOOK, url, min_priority);
}

int
alert_add_slack(const char *webhook_url, int min_priority)
{
    return alert_add_channel(CHANNEL_SLACK, webhook_url, min_priority);
}

/* ==================== Alert Sending ==================== */

/* Format alert message */
static void
format_alert(char *buffer, size_t size, alert_priority_t priority,
             const char *title, const char *message)
{
    time_t now = time(NULL);
    struct tm *tm = localtime(&now);
    char timestamp[32];
    strftime(timestamp, sizeof(timestamp), "%Y-%m-%d %H:%M:%S", tm);
    
    const char *priority_str;
    switch (priority) {
    case PRIORITY_CRITICAL: priority_str = "CRITICAL"; break;
    case PRIORITY_HIGH:     priority_str = "HIGH"; break;
    case PRIORITY_MEDIUM:   priority_str = "MEDIUM"; break;
    default:                priority_str = "LOW";
    }
    
    snprintf(buffer, size,
             "[%s] [%s] %s: %s",
             timestamp, priority_str, title, message);
}

/* Send to console */
static int
send_console(const char *message, alert_priority_t priority)
{
    const char *color = "";
    const char *reset = "";
    
#ifndef _WIN32
    switch (priority) {
    case PRIORITY_CRITICAL: color = "\033[1;31m"; break;
    case PRIORITY_HIGH:     color = "\033[0;31m"; break;
    case PRIORITY_MEDIUM:   color = "\033[0;33m"; break;
    default:                color = "\033[0;32m";
    }
    reset = "\033[0m";
#endif
    
    fprintf(stderr, "%s%s%s\n", color, message, reset);
    return 0;
}

/* Send to file */
static int
send_file(const char *message)
{
    if (g_alert.log_file) {
        fprintf(g_alert.log_file, "%s\n", message);
        fflush(g_alert.log_file);
        return 0;
    }
    return -1;
}

/* Send webhook (placeholder) */
static int
send_webhook(const char *url, const char *message)
{
    /* Would use libcurl or raw sockets */
    printf("ALERT: Would POST to %s: %s\n", url, message);
    return 0;
}

/* Main alert function */
int
alert_send(int priority, const char *title, 
           const char *message)
{
    if (!title || !message)
        return -1;
    
    char formatted[ALERT_BUFFER_SIZE];
    format_alert(formatted, sizeof(formatted), (alert_priority_t)priority, title, message);
    
    int sent = 0;
    int failed = 0;
    
    for (int i = 0; i < g_alert.channel_count; i++) {
        alert_channel_t *ch = &g_alert.channels[i];
        
        if (!ch->enabled)
            continue;
        
        if (priority < ch->min_priority)
            continue;
        
        int result = 0;
        
        switch (ch->type) {
        case CHANNEL_CONSOLE:
            result = send_console(formatted, priority);
            break;
            
        case CHANNEL_FILE:
            result = send_file(formatted);
            break;
            
        case CHANNEL_WEBHOOK:
        case CHANNEL_SLACK:
            result = send_webhook(ch->config, formatted);
            break;
            
        default:
            result = -1;
        }
        
        if (result == 0) {
            sent++;
        } else {
            failed++;
        }
    }
    
    g_alert.alerts_sent += sent;
    g_alert.alerts_failed += failed;
    
    return sent > 0 ? 0 : -1;
}

/* ==================== Convenience Functions ==================== */

int
alert_threat(threat_level_t level, const char *details)
{
    alert_priority_t priority;
    
    switch (level) {
    case THREAT_LEVEL_CRITICAL: priority = PRIORITY_CRITICAL; break;
    case THREAT_LEVEL_HIGH:     priority = PRIORITY_HIGH; break;
    case THREAT_LEVEL_MEDIUM:   priority = PRIORITY_MEDIUM; break;
    default:                    priority = PRIORITY_LOW;
    }
    
    return alert_send(priority, "THREAT DETECTED", details);
}

int
alert_agent_offline(uint32_t agent_id, const char *hostname)
{
    char message[256];
    snprintf(message, sizeof(message),
             "Agent %u (%s) went offline", agent_id, hostname);
    
    return alert_send(PRIORITY_MEDIUM, "AGENT OFFLINE", message);
}

int
alert_agent_compromised(uint32_t agent_id, const char *hostname)
{
    char message[256];
    snprintf(message, sizeof(message),
             "Agent %u (%s) appears compromised", agent_id, hostname);
    
    return alert_send(PRIORITY_CRITICAL, "AGENT COMPROMISED", message);
}

/* Statistics */
void
alert_stats(uint64_t *sent, uint64_t *failed)
{
    if (sent) *sent = g_alert.alerts_sent;
    if (failed) *failed = g_alert.alerts_failed;
}
