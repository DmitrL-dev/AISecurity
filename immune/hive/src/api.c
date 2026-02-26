/*
 * SENTINEL IMMUNE — Hive HTTP API
 * 
 * RESTful API for external integrations.
 * Minimal HTTP server in pure C.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <pthread.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

#include "../include/hive.h"

#define HTTP_BUFFER     8192
#define MAX_ROUTE_LEN   256

/* HTTP Response codes */
#define HTTP_200_OK             "HTTP/1.1 200 OK\r\n"
#define HTTP_400_BAD_REQUEST    "HTTP/1.1 400 Bad Request\r\n"
#define HTTP_404_NOT_FOUND      "HTTP/1.1 404 Not Found\r\n"
#define HTTP_500_ERROR          "HTTP/1.1 500 Internal Server Error\r\n"

#define CONTENT_JSON    "Content-Type: application/json\r\n"
#define CORS_HEADERS    "Access-Control-Allow-Origin: *\r\n"

/* ==================== JSON Helpers ==================== */

static void
json_status(immune_hive_t *hive, char *buffer, size_t len)
{
    hive_stats_t stats = hive_get_stats(hive);
    
    snprintf(buffer, len,
        "{"
        "\"version\":\"%s\","
        "\"agents\":{\"total\":%u,\"online\":%u,\"offline\":%u},"
        "\"threats\":{\"total\":%lu},"
        "\"signatures\":%lu"
        "}",
        HIVE_VERSION,
        stats.agents_total, stats.agents_online, stats.agents_offline,
        stats.threats_total,
        stats.signatures_total
    );
}

static void
json_agents(immune_hive_t *hive, char *buffer, size_t len)
{
    char *p = buffer;
    char *end = buffer + len - 1;
    
    p += snprintf(p, end - p, "{\"agents\":[");
    
    int first = 1;
    for (uint32_t i = 1; i < MAX_AGENTS && p < end - 100; i++) {
        if (!hive->agents[i].active)
            continue;
        
        if (!first)
            p += snprintf(p, end - p, ",");
        first = 0;
        
        immune_agent_t *a = &hive->agents[i];
        p += snprintf(p, end - p,
            "{"
            "\"id\":%u,"
            "\"hostname\":\"%s\","
            "\"ip\":\"%s\","
            "\"status\":\"%s\","
            "\"threats\":%lu"
            "}",
            a->agent_id,
            a->hostname,
            a->ip_address,
            a->status == AGENT_STATUS_ONLINE ? "online" : "offline",
            a->threats_detected
        );
    }
    
    p += snprintf(p, end - p, "]}");
}

static void
json_threats(immune_hive_t *hive, char *buffer, size_t len, int limit)
{
    char *p = buffer;
    char *end = buffer + len - 1;
    
    p += snprintf(p, end - p, "{\"threats\":[");
    
    int count = 0;
    uint64_t start = (hive->threat_count > limit) ? 
                     hive->threat_count - limit : 0;
    
    for (uint64_t i = start; i < hive->threat_count && p < end - 200; i++) {
        if (count > 0)
            p += snprintf(p, end - p, ",");
        
        threat_event_t *t = &hive->threats[i];
        p += snprintf(p, end - p,
            "{"
            "\"id\":%lu,"
            "\"agent\":%u,"
            "\"level\":%d,"
            "\"type\":%d,"
            "\"signature\":\"%s\""
            "}",
            t->event_id,
            t->agent_id,
            t->level,
            t->type,
            t->signature
        );
        
        count++;
    }
    
    p += snprintf(p, end - p, "]}");
}

static void
json_health(char *buffer, size_t len)
{
    snprintf(buffer, len, "{\"status\":\"healthy\"}");
}

/* ==================== HTTP Handler ==================== */

static void
handle_http_request(immune_hive_t *hive, int fd, 
                    const char *method, const char *path)
{
    char response[HTTP_BUFFER];
    char body[HTTP_BUFFER - 512];
    const char *status = HTTP_200_OK;
    
    /* Route requests */
    if (strcmp(method, "GET") == 0) {
        if (strcmp(path, "/api/status") == 0 ||
            strcmp(path, "/") == 0) {
            json_status(hive, body, sizeof(body));
        }
        else if (strcmp(path, "/api/health") == 0) {
            json_health(body, sizeof(body));
        }
        else if (strcmp(path, "/api/agents") == 0) {
            json_agents(hive, body, sizeof(body));
        }
        else if (strcmp(path, "/api/threats") == 0) {
            json_threats(hive, body, sizeof(body), 50);
        }
        else {
            status = HTTP_404_NOT_FOUND;
            snprintf(body, sizeof(body), "{\"error\":\"Not found\"}");
        }
    }
    else {
        status = HTTP_400_BAD_REQUEST;
        snprintf(body, sizeof(body), "{\"error\":\"Method not allowed\"}");
    }
    
    /* Build response */
    snprintf(response, sizeof(response),
        "%s"
        "%s"
        "%s"
        "Content-Length: %zu\r\n"
        "\r\n"
        "%s",
        status,
        CONTENT_JSON,
        CORS_HEADERS,
        strlen(body),
        body
    );
    
    send(fd, response, strlen(response), 0);
}

static void*
handle_http_client(void *arg)
{
    int *fds = (int *)arg;
    int fd = fds[0];
    immune_hive_t *hive = (immune_hive_t *)(intptr_t)fds[1];
    free(arg);
    
    char buffer[HTTP_BUFFER];
    ssize_t n = recv(fd, buffer, sizeof(buffer) - 1, 0);
    
    if (n > 0) {
        buffer[n] = '\0';
        
        /* Parse request line */
        char method[16], path[256];
        if (sscanf(buffer, "%15s %255s", method, path) == 2) {
            handle_http_request(hive, fd, method, path);
        }
    }
    
    close(fd);
    return NULL;
}

/* ==================== HTTP Server ==================== */

int
hive_api_start(immune_hive_t *hive, uint16_t port)
{
    int server_fd;
    struct sockaddr_in addr;
    int opt = 1;
    
    server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd < 0) {
        perror("[API] Socket failed");
        return -1;
    }
    
    setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
    
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port = htons(port);
    
    if (bind(server_fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("[API] Bind failed");
        close(server_fd);
        return -1;
    }
    
    if (listen(server_fd, 128) < 0) {
        perror("[API] Listen failed");
        close(server_fd);
        return -1;
    }
    
    printf("[API] HTTP server listening on port %d\n", port);
    
    while (hive->running) {
        int client_fd = accept(server_fd, NULL, NULL);
        if (client_fd < 0)
            continue;
        
        int *fds = malloc(sizeof(int) * 2);
        fds[0] = client_fd;
        fds[1] = (intptr_t)hive;
        
        pthread_t thread;
        pthread_create(&thread, NULL, handle_http_client, fds);
        pthread_detach(thread);
    }
    
    close(server_fd);
    return 0;
}

void*
hive_api_thread(void *arg)
{
    immune_hive_t *hive = (immune_hive_t *)arg;
    hive_api_start(hive, hive->api_port);
    return NULL;
}
