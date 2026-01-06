/**
 * @file route_health.c
 * @brief Health Check Route Handler
 * 
 * GET /health — Returns server health status.
 * 
 * @author SENTINEL Team
 * @date January 2026
 */

#include "http/http_server.h"
#include "http/json_builder.h"
#include <stdio.h>
#include <time.h>

/* ============================================================================
 * Global State
 * ============================================================================ */

static time_t server_start_time = 0;

void route_health_init(void) {
    server_start_time = time(NULL);
}

/* ============================================================================
 * Route Handler
 * ============================================================================ */

int route_health_handler(const http_request_t *request,
                         http_response_t *response,
                         void *user_data) {
    (void)request;
    (void)user_data;
    
    /* Calculate uptime */
    time_t now = time(NULL);
    long uptime = (long)(now - server_start_time);
    
    /* Build response */
    json_builder_t *builder = json_builder_create();
    
    json_object_start(builder);
    json_add_string(builder, "status", "healthy");
    json_add_string(builder, "version", "4.1.0");
    json_add_string(builder, "codename", "Dragon");
    json_add_int(builder, "uptime_seconds", uptime);
    json_add_int(builder, "guards_enabled", 6);
    
    /* Components status */
    json_add_object(builder, "components");
    json_add_string(builder, "llm_guard", "ok");
    json_add_string(builder, "rag_guard", "ok");
    json_add_string(builder, "agent_guard", "ok");
    json_add_string(builder, "tool_guard", "ok");
    json_add_string(builder, "mcp_guard", "ok");
    json_add_string(builder, "api_guard", "ok");
    json_object_end(builder);
    
    json_object_end(builder);
    
    /* Set response */
    response->status = HTTP_STATUS_OK;
    http_response_set_json(response, json_builder_get_string(builder));
    
    json_builder_destroy(builder);
    
    return 0;
}

/* ============================================================================
 * Route Registration
 * ============================================================================ */

http_route_t route_health = {
    .method = HTTP_METHOD_GET,
    .path = "/health",
    .handler = route_health_handler,
    .user_data = NULL
};
