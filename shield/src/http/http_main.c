/**
 * @file http_main.c
 * @brief HTTP Server Entry Point
 * 
 * Initializes and starts the Shield REST API server.
 * Can be called from CLI or standalone.
 * 
 * @author SENTINEL Team
 * @date January 2026
 */

#include "http/http_server.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>

/* ============================================================================
 * External Route Declarations
 * ============================================================================ */

/* From route_analyze.c */
extern http_route_t route_analyze;

/* From route_health.c */
extern http_route_t route_health;
extern void route_health_init(void);

/* From route_metrics.c */
extern http_route_t route_metrics;

/* ============================================================================
 * Global Server Instance
 * ============================================================================ */

static http_server_t *g_server = NULL;

/* ============================================================================
 * Signal Handler
 * ============================================================================ */

static void signal_handler(int sig) {
    (void)sig;
    printf("\n[HTTP] Shutting down...\n");
    if (g_server) {
        http_server_stop(g_server);
    }
}

/* ============================================================================
 * Server Initialization
 * ============================================================================ */

/**
 * @brief Initialize and start HTTP server
 * 
 * @param port Port to listen on (0 = default 8080)
 * @param async If true, start in background thread
 * @return 0 on success
 */
int http_server_init(uint16_t port, bool async) {
    /* Create configuration */
    http_server_config_t config = HTTP_SERVER_CONFIG_DEFAULT;
    if (port > 0) {
        config.port = port;
    }
    
    /* Create server */
    g_server = http_server_create(&config);
    if (!g_server) {
        fprintf(stderr, "[HTTP] Failed to create server\n");
        return -1;
    }
    
    /* Initialize route modules */
    route_health_init();
    
    /* Register routes */
    http_server_add_route(g_server, &route_health);
    http_server_add_route(g_server, &route_metrics);
    http_server_add_route(g_server, &route_analyze);
    
    /* TODO: Add more routes */
    /* http_server_add_route(g_server, &route_guard_llm); */
    /* http_server_add_route(g_server, &route_guard_rag); */
    /* http_server_add_route(g_server, &route_openapi); */
    
    printf("[HTTP] Registered %d routes\n", 3);
    printf("[HTTP] Routes:\n");
    printf("  GET  /health          - Health check\n");
    printf("  GET  /metrics         - Prometheus metrics\n");
    printf("  POST /api/v1/analyze  - Security analysis\n");
    
    /* Setup signal handler */
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);
    
    /* Start server */
    if (async) {
        return http_server_start_async(g_server);
    } else {
        return http_server_start(g_server);
    }
}

/**
 * @brief Stop and cleanup HTTP server
 */
void http_server_shutdown(void) {
    if (g_server) {
        http_server_destroy(g_server);
        g_server = NULL;
    }
}

/**
 * @brief Check if HTTP server is running
 */
bool http_server_running(void) {
    return g_server && http_server_is_running(g_server);
}

/* ============================================================================
 * Standalone Main (for testing)
 * ============================================================================ */

#ifdef HTTP_STANDALONE

int main(int argc, char **argv) {
    uint16_t port = 8080;
    
    /* Parse arguments */
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-p") == 0 && i + 1 < argc) {
            port = (uint16_t)atoi(argv[++i]);
        } else if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
            printf("SENTINEL Shield HTTP Server\n");
            printf("\nUsage: %s [options]\n", argv[0]);
            printf("\nOptions:\n");
            printf("  -p PORT    Listen port (default: 8080)\n");
            printf("  -h         Show this help\n");
            printf("\nExample:\n");
            printf("  %s -p 9000\n", argv[0]);
            return 0;
        }
    }
    
    printf("╔════════════════════════════════════════════╗\n");
    printf("║     SENTINEL Shield REST API v4.1         ║\n");
    printf("║     \"Dragon\" Edition                      ║\n");
    printf("╚════════════════════════════════════════════╝\n\n");
    
    int result = http_server_init(port, false);
    
    http_server_shutdown();
    
    return result;
}

#endif /* HTTP_STANDALONE */
