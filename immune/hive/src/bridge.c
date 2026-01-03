/*
 * SENTINEL IMMUNE — Integration Bridge
 * 
 * Bridge for SENTINEL Brain integration.
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
#endif

#include "../include/hive.h"

#define BRAIN_PORT          8080
#define BRAIN_ENDPOINT      "/api/immune/threat"
#define MAX_PAYLOAD         4096

/* Bridge context */
typedef struct {
    char        brain_host[128];
    int         brain_port;
    char        api_key[128];
    int         enabled;
    int         connected;
} bridge_ctx_t;

static bridge_ctx_t g_bridge;

/* ==================== Initialization ==================== */

int
bridge_init(const char *brain_host, int port, const char *api_key)
{
    memset(&g_bridge, 0, sizeof(bridge_ctx_t));
    
    if (brain_host) {
        strncpy(g_bridge.brain_host, brain_host, 
                sizeof(g_bridge.brain_host) - 1);
    } else {
        strcpy(g_bridge.brain_host, "127.0.0.1");
    }
    
    g_bridge.brain_port = port > 0 ? port : BRAIN_PORT;
    
    if (api_key) {
        strncpy(g_bridge.api_key, api_key, sizeof(g_bridge.api_key) - 1);
    }
    
    g_bridge.enabled = 1;
    
    printf("BRIDGE: Initialized (Brain at %s:%d)\n",
           g_bridge.brain_host, g_bridge.brain_port);
    
    return 0;
}

void
bridge_shutdown(void)
{
    g_bridge.enabled = 0;
    printf("BRIDGE: Shutdown complete\n");
}

/* ==================== Brain Communication ==================== */

/* Format threat as JSON */
static void
format_threat_json(char *buffer, size_t size, threat_event_t *event)
{
    snprintf(buffer, size,
        "{"
        "\"event_id\":%lu,"
        "\"agent_id\":%u,"
        "\"timestamp\":%ld,"
        "\"level\":%d,"
        "\"type\":%d,"
        "\"signature\":\"%s\","
        "\"action\":%d,"
        "\"source\":\"IMMUNE\""
        "}",
        event->event_id,
        event->agent_id,
        event->timestamp,
        event->level,
        event->type,
        event->signature,
        event->action
    );
}

/* Send threat to Brain */
int
bridge_report_threat(threat_event_t *event)
{
    if (!g_bridge.enabled || !event)
        return -1;
    
    char payload[MAX_PAYLOAD];
    format_threat_json(payload, sizeof(payload), event);
    
    /* Would use HTTP POST here */
    printf("BRIDGE: Would POST to Brain: %s\n", payload);
    
    return 0;
}

/* Send agent status to Brain */
int
bridge_report_agent(immune_agent_t *agent)
{
    if (!g_bridge.enabled || !agent)
        return -1;
    
    char payload[MAX_PAYLOAD];
    snprintf(payload, sizeof(payload),
        "{"
        "\"agent_id\":%u,"
        "\"hostname\":\"%s\","
        "\"ip_address\":\"%s\","
        "\"os_type\":\"%s\","
        "\"status\":%d,"
        "\"threats_detected\":%lu,"
        "\"source\":\"IMMUNE\""
        "}",
        agent->agent_id,
        agent->hostname,
        agent->ip_address,
        agent->os_type,
        agent->status,
        agent->threats_detected
    );
    
    printf("BRIDGE: Would POST agent to Brain: %s\n", payload);
    
    return 0;
}

/* Request scan from Brain engines */
int
bridge_request_scan(const char *text, size_t length)
{
    if (!g_bridge.enabled || !text)
        return -1;
    
    /* Truncate for safe logging */
    char preview[128];
    strncpy(preview, text, sizeof(preview) - 1);
    preview[sizeof(preview) - 1] = '\0';
    
    printf("BRIDGE: Would request scan from Brain: %.50s...\n", preview);
    
    return 0;
}

/* Get configuration from Brain */
int
bridge_sync_config(immune_hive_t *hive)
{
    if (!g_bridge.enabled || !hive)
        return -1;
    
    printf("BRIDGE: Would sync config from Brain\n");
    
    return 0;
}

/* Get signatures from Brain */
int
bridge_sync_signatures(immune_hive_t *hive)
{
    if (!g_bridge.enabled || !hive)
        return -1;
    
    printf("BRIDGE: Would sync signatures from Brain\n");
    
    return 0;
}

/* ==================== Status ==================== */

void
bridge_status(int *enabled, int *connected, 
              const char **host, int *port)
{
    if (enabled) *enabled = g_bridge.enabled;
    if (connected) *connected = g_bridge.connected;
    if (host) *host = g_bridge.brain_host;
    if (port) *port = g_bridge.brain_port;
}
