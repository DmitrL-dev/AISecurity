/*
 * SENTINEL IMMUNE — Hive SENTINEL AI Bridge
 * 
 * Integration with SENTINEL AI Security Platform for:
 * - Threat analysis via 207 detection engines
 * - Meta-Judge triage
 * - Response recommendations
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netdb.h>
#include <pthread.h>

#include "../include/hive.h"

/* ==================== Configuration ==================== */

#define SENTINEL_DEFAULT_HOST   "localhost"
#define SENTINEL_DEFAULT_PORT   8080
#define SENTINEL_API_PATH       "/api/v1/analyze"
#define SENTINEL_TIMEOUT_MS     5000
#define SENTINEL_BATCH_SIZE     50
#define MAX_RESPONSE_SIZE       4096

/* ==================== Structures ==================== */

typedef struct {
    char        host[256];
    uint16_t    port;
    char        api_key[128];
    int         timeout_ms;
    int         batch_size;
    int         connected;
} sentinel_config_t;

typedef struct {
    float       risk_score;         /* 0.0 - 1.0 */
    char        classification[64];
    char        engines_triggered[256];
    int         engine_count;
    response_action_t recommended_action;
    char        explanation[512];
} sentinel_verdict_t;

/* Event queue for batch processing */
typedef struct {
    threat_event_t  events[SENTINEL_BATCH_SIZE];
    int             count;
    pthread_mutex_t lock;
} event_queue_t;

/* ==================== Globals ==================== */

static sentinel_config_t g_sentinel = {
    .host = SENTINEL_DEFAULT_HOST,
    .port = SENTINEL_DEFAULT_PORT,
    .timeout_ms = SENTINEL_TIMEOUT_MS,
    .batch_size = SENTINEL_BATCH_SIZE,
    .connected = 0
};

static event_queue_t g_queue = {
    .count = 0
};

/* ==================== HTTP Client ==================== */

static int
http_connect(const char *host, uint16_t port)
{
    struct sockaddr_in addr;
    struct hostent *he;
    int sock;
    
    he = gethostbyname(host);
    if (!he) {
        fprintf(stderr, "[SENTINEL] Cannot resolve %s\n", host);
        return -1;
    }
    
    sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) {
        perror("[SENTINEL] socket");
        return -1;
    }
    
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    memcpy(&addr.sin_addr, he->h_addr, he->h_length);
    
    if (connect(sock, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        close(sock);
        return -1;
    }
    
    return sock;
}

static int
http_post_json(const char *host, uint16_t port, const char *path,
               const char *json, char *response, size_t resp_size)
{
    int sock = http_connect(host, port);
    if (sock < 0)
        return -1;
    
    /* Build HTTP request */
    char request[2048];
    int req_len = snprintf(request, sizeof(request),
        "POST %s HTTP/1.1\r\n"
        "Host: %s\r\n"
        "Content-Type: application/json\r\n"
        "Content-Length: %zu\r\n"
        "Connection: close\r\n"
        "\r\n"
        "%s",
        path, host, strlen(json), json);
    
    /* Send request */
    if (send(sock, request, req_len, 0) != req_len) {
        close(sock);
        return -1;
    }
    
    /* Read response */
    ssize_t total = 0;
    ssize_t n;
    while ((n = recv(sock, response + total, resp_size - total - 1, 0)) > 0) {
        total += n;
        if (total >= resp_size - 1)
            break;
    }
    response[total] = '\0';
    
    close(sock);
    return (int)total;
}

/* ==================== JSON Helpers ==================== */

static int
json_format_event(threat_event_t *event, char *buffer, size_t size)
{
    return snprintf(buffer, size,
        "{"
        "\"agent_id\":%u,"
        "\"level\":%d,"
        "\"type\":%d,"
        "\"signature\":\"%s\","
        "\"timestamp\":%lu,"
        "\"context\":\"%s\""
        "}",
        event->agent_id,
        event->level,
        event->type,
        event->signature,
        (unsigned long)event->timestamp,
        event->context);
}

static int
json_parse_verdict(const char *json, sentinel_verdict_t *verdict)
{
    memset(verdict, 0, sizeof(*verdict));
    
    /* Simple JSON parsing (production would use proper parser) */
    const char *p;
    
    /* Parse risk_score */
    p = strstr(json, "\"risk_score\":");
    if (p) {
        sscanf(p + 13, "%f", &verdict->risk_score);
    }
    
    /* Parse classification */
    p = strstr(json, "\"classification\":\"");
    if (p) {
        sscanf(p + 18, "%63[^\"]", verdict->classification);
    }
    
    /* Parse recommended_action */
    p = strstr(json, "\"action\":");
    if (p) {
        int action;
        sscanf(p + 9, "%d", &action);
        verdict->recommended_action = (response_action_t)action;
    }
    
    /* Parse engines_triggered */
    p = strstr(json, "\"engines\":");
    if (p) {
        char *start = strchr(p, '[');
        char *end = strchr(p, ']');
        if (start && end && end > start) {
            size_t len = end - start - 1;
            if (len < sizeof(verdict->engines_triggered))
                strncpy(verdict->engines_triggered, start + 1, len);
        }
    }
    
    return 0;
}

/* ==================== Public API ==================== */

int
sentinel_init(const char *host, uint16_t port, const char *api_key)
{
    if (host)
        strncpy(g_sentinel.host, host, sizeof(g_sentinel.host) - 1);
    if (port)
        g_sentinel.port = port;
    if (api_key)
        strncpy(g_sentinel.api_key, api_key, sizeof(g_sentinel.api_key) - 1);
    
    pthread_mutex_init(&g_queue.lock, NULL);
    
    printf("[SENTINEL] Bridge initialized: %s:%d\n", 
           g_sentinel.host, g_sentinel.port);
    
    /* Test connection */
    int sock = http_connect(g_sentinel.host, g_sentinel.port);
    if (sock >= 0) {
        close(sock);
        g_sentinel.connected = 1;
        printf("[SENTINEL] Connection verified\n");
    } else {
        printf("[SENTINEL] Warning: SENTINEL not reachable\n");
    }
    
    return 0;
}

int
sentinel_analyze(threat_event_t *event, void *verd)
{
    sentinel_verdict_t *verdict = (sentinel_verdict_t *)verd;
    
    if (!event || !verdict)
        return -1;
    
    /* Format event as JSON */
    char json[1024];
    json_format_event(event, json, sizeof(json));
    
    /* Send to SENTINEL */
    char response[MAX_RESPONSE_SIZE];
    int n = http_post_json(g_sentinel.host, g_sentinel.port,
                          SENTINEL_API_PATH, json, 
                          response, sizeof(response));
    
    if (n <= 0) {
        fprintf(stderr, "[SENTINEL] Analysis failed\n");
        return -1;
    }
    
    /* Parse response */
    json_parse_verdict(response, verdict);
    
    printf("[SENTINEL] Analysis: risk=%.2f class=%s action=%d\n",
           verdict->risk_score, verdict->classification,
           verdict->recommended_action);
    
    return 0;
}

int
sentinel_queue_event(threat_event_t *event)
{
    pthread_mutex_lock(&g_queue.lock);
    
    if (g_queue.count >= SENTINEL_BATCH_SIZE) {
        pthread_mutex_unlock(&g_queue.lock);
        return -1; /* Queue full */
    }
    
    memcpy(&g_queue.events[g_queue.count], event, sizeof(threat_event_t));
    g_queue.count++;
    
    pthread_mutex_unlock(&g_queue.lock);
    return 0;
}

int
sentinel_flush_queue(sentinel_verdict_t *verdicts, int max_verdicts)
{
    pthread_mutex_lock(&g_queue.lock);
    
    int count = g_queue.count;
    if (count == 0) {
        pthread_mutex_unlock(&g_queue.lock);
        return 0;
    }
    
    /* Process each event */
    for (int i = 0; i < count && i < max_verdicts; i++) {
        sentinel_analyze(&g_queue.events[i], &verdicts[i]);
    }
    
    g_queue.count = 0;
    pthread_mutex_unlock(&g_queue.lock);
    
    printf("[SENTINEL] Flushed %d events\n", count);
    return count;
}

/* ==================== Auto-response Integration ==================== */

response_action_t
sentinel_get_recommended_action(threat_event_t *event)
{
    sentinel_verdict_t verdict;
    
    if (sentinel_analyze(event, &verdict) < 0) {
        /* Fallback to simple rules if SENTINEL unavailable */
        switch (event->level) {
        case THREAT_LEVEL_CRITICAL:
            return RESPONSE_ISOLATE;
        case THREAT_LEVEL_HIGH:
            return RESPONSE_BLOCK;
        case THREAT_LEVEL_MEDIUM:
            return RESPONSE_ALERT;
        default:
            return RESPONSE_LOG;
        }
    }
    
    /* Use SENTINEL's recommendation */
    if (verdict.risk_score >= 0.9)
        return RESPONSE_ISOLATE;
    else if (verdict.risk_score >= 0.7)
        return RESPONSE_BLOCK;
    else if (verdict.risk_score >= 0.5)
        return RESPONSE_ALERT;
    
    return verdict.recommended_action;
}

void
sentinel_shutdown(void)
{
    pthread_mutex_destroy(&g_queue.lock);
    g_sentinel.connected = 0;
    printf("[SENTINEL] Bridge shutdown\n");
}
