/*
 * SENTINEL IMMUNE — SOC Connector
 * 
 * SIEM/SOC integration for enterprise deployments.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#ifdef _WIN32
    #include <winsock2.h>
#else
    #include <sys/socket.h>
    #include <netinet/in.h>
    #include <arpa/inet.h>
    #include <unistd.h>
#endif

#include "../include/hive.h"

#define MAX_SOC_TARGETS     10
#define SYSLOG_PORT         514
#define SYSLOG_MAX_MSG      1024

/* SOC integration types */
typedef enum {
    SOC_SYSLOG = 1,
    SOC_CEF,            /* Common Event Format */
    SOC_LEEF,           /* Log Event Extended Format (IBM) */
    SOC_JSON,
    SOC_SPLUNK,
    SOC_ELASTIC
} soc_format_t;

/* SOC target */
typedef struct {
    char            host[128];
    uint16_t        port;
    soc_format_t    format;
    int             enabled;
    int             use_tls;
    uint64_t        events_sent;
    uint64_t        events_failed;
} soc_target_t;

/* SOC context */
typedef struct {
    soc_target_t    targets[MAX_SOC_TARGETS];
    int             target_count;
    
    char            facility_name[64];
    
    uint64_t        total_sent;
    uint64_t        total_failed;
} soc_ctx_t;

static soc_ctx_t g_soc;

/* ==================== Initialization ==================== */

int
soc_init(void)
{
    memset(&g_soc, 0, sizeof(soc_ctx_t));
    strcpy(g_soc.facility_name, "IMMUNE");
    
    printf("SOC: Connector initialized\n");
    return 0;
}

void
soc_shutdown(void)
{
    printf("SOC: Sent %lu events, failed %lu\n",
           g_soc.total_sent, g_soc.total_failed);
}

/* ==================== Target Management ==================== */

int
soc_add_target(const char *host, uint16_t port, int format)
{
    if (g_soc.target_count >= MAX_SOC_TARGETS)
        return -1;
    
    soc_target_t *target = &g_soc.targets[g_soc.target_count];
    
    strncpy(target->host, host, sizeof(target->host) - 1);
    target->port = port > 0 ? port : SYSLOG_PORT;
    target->format = format;
    target->enabled = 1;
    
    g_soc.target_count++;
    
    printf("SOC: Added target %s:%d\n", host, port);
    return 0;
}

/* ==================== Message Formatting ==================== */

/* RFC 5424 Syslog */
static int
format_syslog(char *buffer, size_t size, int severity,
              const char *message)
{
    time_t now = time(NULL);
    struct tm *tm = gmtime(&now);
    
    char timestamp[32];
    strftime(timestamp, sizeof(timestamp), "%Y-%m-%dT%H:%M:%SZ", tm);
    
    /* 
     * Format: <priority>version timestamp hostname app-name procid msgid msg
     * Priority = facility * 8 + severity
     * Facility 1 = user-level
     */
    int priority = 1 * 8 + severity;
    
    return snprintf(buffer, size,
        "<%d>1 %s IMMUNE-HIVE immuned - - %s",
        priority, timestamp, message);
}

/* ArcSight CEF */
static int
format_cef(char *buffer, size_t size, int severity,
           threat_event_t *event)
{
    return snprintf(buffer, size,
        "CEF:0|SENTINEL|IMMUNE|1.0|%u|Threat Detected|%d|"
        "src=%u dpt=0 rt=%ld msg=%s",
        event->type,
        severity,
        event->agent_id,
        event->timestamp,
        event->signature
    );
}

/* IBM QRadar LEEF */
static int
format_leef(char *buffer, size_t size, int severity,
            threat_event_t *event)
{
    return snprintf(buffer, size,
        "LEEF:1.0|SENTINEL|IMMUNE|1.0|ThreatDetected|"
        "devTime=%ld\tsrc=%u\tsev=%d\tmsg=%s",
        event->timestamp,
        event->agent_id,
        severity,
        event->signature
    );
}

/* JSON format */
static int
format_json(char *buffer, size_t size, int severity,
            threat_event_t *event)
{
    return snprintf(buffer, size,
        "{"
        "\"@timestamp\":%ld,"
        "\"source\":\"IMMUNE\","
        "\"event_id\":%lu,"
        "\"agent_id\":%u,"
        "\"severity\":%d,"
        "\"type\":%d,"
        "\"signature\":\"%s\","
        "\"action\":%d"
        "}",
        event->timestamp,
        event->event_id,
        event->agent_id,
        severity,
        event->type,
        event->signature,
        event->action
    );
}

/* ==================== Sending ==================== */

static int
send_udp(const char *host, uint16_t port, const char *message, size_t len)
{
    int sock;
    struct sockaddr_in addr;
    
#ifdef _WIN32
    WSADATA wsa;
    WSAStartup(MAKEWORD(2, 2), &wsa);
#endif
    
    sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock < 0) {
        return -1;
    }
    
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    inet_pton(AF_INET, host, &addr.sin_addr);
    
    ssize_t sent = sendto(sock, message, len, 0,
                          (struct sockaddr *)&addr, sizeof(addr));
    
#ifdef _WIN32
    closesocket(sock);
    WSACleanup();
#else
    close(sock);
#endif
    
    return sent == (ssize_t)len ? 0 : -1;
}

/* ==================== Event Sending ==================== */

int
soc_send_threat(threat_event_t *event)
{
    if (!event) return -1;
    
    int severity = 5 - event->level;  /* Invert for syslog (0=emergency) */
    if (severity < 0) severity = 0;
    if (severity > 7) severity = 7;
    
    char buffer[SYSLOG_MAX_MSG];
    int sent = 0;
    
    for (int i = 0; i < g_soc.target_count; i++) {
        soc_target_t *target = &g_soc.targets[i];
        
        if (!target->enabled)
            continue;
        
        int len = 0;
        
        switch (target->format) {
        case SOC_SYSLOG:
            len = format_syslog(buffer, sizeof(buffer), severity,
                               event->signature);
            break;
            
        case SOC_CEF:
            len = format_cef(buffer, sizeof(buffer), severity, event);
            break;
            
        case SOC_LEEF:
            len = format_leef(buffer, sizeof(buffer), severity, event);
            break;
            
        case SOC_JSON:
        case SOC_SPLUNK:
        case SOC_ELASTIC:
            len = format_json(buffer, sizeof(buffer), severity, event);
            break;
            
        default:
            continue;
        }
        
        if (len > 0) {
            int result = send_udp(target->host, target->port, buffer, len);
            
            if (result == 0) {
                target->events_sent++;
                sent++;
            } else {
                target->events_failed++;
            }
        }
    }
    
    g_soc.total_sent += sent;
    return sent > 0 ? 0 : -1;
}

int
soc_send_alert(int severity, const char *message)
{
    char buffer[SYSLOG_MAX_MSG];
    int sent = 0;
    
    for (int i = 0; i < g_soc.target_count; i++) {
        soc_target_t *target = &g_soc.targets[i];
        
        if (!target->enabled)
            continue;
        
        int len = format_syslog(buffer, sizeof(buffer), severity, message);
        
        if (len > 0) {
            if (send_udp(target->host, target->port, buffer, len) == 0) {
                target->events_sent++;
                sent++;
            }
        }
    }
    
    g_soc.total_sent += sent;
    return sent > 0 ? 0 : -1;
}

/* Statistics */
void
soc_stats(uint64_t *sent, uint64_t *failed)
{
    if (sent) *sent = g_soc.total_sent;
    if (failed) *failed = g_soc.total_failed;
}
