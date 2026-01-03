/*
 * SENTINEL IMMUNE — Hive Discovery Module
 * 
 * Network scanning for unprotected hosts.
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
#include <netdb.h>
#include <fcntl.h>
#include <sys/select.h>

#include "../include/hive.h"

#define SCAN_TIMEOUT_MS     100
#define MAX_SCAN_THREADS    32

/* Scan result */
typedef struct {
    char        ip[MAX_IP_LEN];
    int         port;
    int         is_up;
    int         is_immune;  /* Already has agent */
} scan_result_t;

/* Scan context */
typedef struct {
    immune_hive_t   *hive;
    char            target_ip[MAX_IP_LEN];
    int             port;
    scan_result_t   *result;
} scan_ctx_t;

/* ==================== Port Scanning ==================== */

static int
tcp_connect_timeout(const char *ip, int port, int timeout_ms)
{
    int sock;
    struct sockaddr_in addr;
    fd_set fdset;
    struct timeval tv;
    int flags;
    int result = 0;
    
    sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0)
        return 0;
    
    /* Non-blocking */
    flags = fcntl(sock, F_GETFL, 0);
    fcntl(sock, F_SETFL, flags | O_NONBLOCK);
    
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    inet_pton(AF_INET, ip, &addr.sin_addr);
    
    connect(sock, (struct sockaddr *)&addr, sizeof(addr));
    
    FD_ZERO(&fdset);
    FD_SET(sock, &fdset);
    
    tv.tv_sec = timeout_ms / 1000;
    tv.tv_usec = (timeout_ms % 1000) * 1000;
    
    if (select(sock + 1, NULL, &fdset, NULL, &tv) == 1) {
        int so_error;
        socklen_t len = sizeof(so_error);
        
        getsockopt(sock, SOL_SOCKET, SO_ERROR, &so_error, &len);
        
        if (so_error == 0)
            result = 1;
    }
    
    close(sock);
    return result;
}

/* ==================== Host Discovery ==================== */

static void*
scan_host_thread(void *arg)
{
    scan_ctx_t *ctx = (scan_ctx_t *)arg;
    
    ctx->result->is_up = tcp_connect_timeout(
        ctx->target_ip, ctx->port, SCAN_TIMEOUT_MS
    );
    
    strcpy(ctx->result->ip, ctx->target_ip);
    ctx->result->port = ctx->port;
    
    /* Check if running IMMUNE agent */
    if (ctx->result->is_up && ctx->port == 9998) {
        ctx->result->is_immune = 1;
    }
    
    free(ctx);
    return NULL;
}

int
hive_scan_host(immune_hive_t *hive, const char *ip, int port,
               scan_result_t *result)
{
    scan_ctx_t *ctx = malloc(sizeof(scan_ctx_t));
    if (!ctx)
        return -1;
    
    ctx->hive = hive;
    strncpy(ctx->target_ip, ip, MAX_IP_LEN - 1);
    ctx->port = port;
    ctx->result = result;
    
    pthread_t thread;
    pthread_create(&thread, NULL, scan_host_thread, ctx);
    pthread_join(thread, NULL);
    
    return 0;
}

/* Scan subnet */
int
hive_scan_subnet(immune_hive_t *hive, const char *subnet, int port,
                 scan_result_t *results, int max_results)
{
    /* Parse subnet (e.g., "192.168.1.0/24") */
    char base_ip[MAX_IP_LEN];
    int prefix;
    
    if (sscanf(subnet, "%[^/]/%d", base_ip, &prefix) != 2) {
        return -1;
    }
    
    /* Calculate range */
    struct in_addr base;
    inet_pton(AF_INET, base_ip, &base);
    
    uint32_t ip_num = ntohl(base.s_addr);
    uint32_t mask = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF;
    uint32_t start = ip_num & mask;
    uint32_t end = start | ~mask;
    
    int count = 0;
    pthread_t threads[MAX_SCAN_THREADS];
    scan_ctx_t *ctxs[MAX_SCAN_THREADS];
    int active = 0;
    
    for (uint32_t i = start + 1; i < end && count < max_results; i++) {
        struct in_addr addr;
        addr.s_addr = htonl(i);
        
        char ip[MAX_IP_LEN];
        inet_ntop(AF_INET, &addr, ip, sizeof(ip));
        
        /* Start scan thread */
        scan_ctx_t *ctx = malloc(sizeof(scan_ctx_t));
        ctx->hive = hive;
        strncpy(ctx->target_ip, ip, MAX_IP_LEN - 1);
        ctx->port = port;
        ctx->result = &results[count];
        
        pthread_create(&threads[active], NULL, scan_host_thread, ctx);
        ctxs[active] = ctx;
        active++;
        count++;
        
        /* Wait for batch */
        if (active >= MAX_SCAN_THREADS) {
            for (int j = 0; j < active; j++) {
                pthread_join(threads[j], NULL);
            }
            active = 0;
        }
    }
    
    /* Wait for remaining */
    for (int j = 0; j < active; j++) {
        pthread_join(threads[j], NULL);
    }
    
    return count;
}

/* Count live hosts */
int
hive_count_live_hosts(scan_result_t *results, int count)
{
    int live = 0;
    for (int i = 0; i < count; i++) {
        if (results[i].is_up)
            live++;
    }
    return live;
}
