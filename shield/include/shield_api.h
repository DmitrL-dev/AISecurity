/*
 * SENTINEL Shield - HTTP API Server
 * 
 * Simple REST API for integration
 */

#ifndef SHIELD_API_H
#define SHIELD_API_H

#include "shield_common.h"

/* HTTP methods */
typedef enum http_method {
    HTTP_GET,
    HTTP_POST,
    HTTP_PUT,
    HTTP_DELETE,
} http_method_t;

/* HTTP request */
typedef struct http_request {
    http_method_t   method;
    char            path[256];
    char            query[512];
    char            content_type[64];
    char            *body;
    size_t          body_len;
    char            headers[2048];
} http_request_t;

/* HTTP response */
typedef struct http_response {
    int             status_code;
    char            content_type[64];
    char            *body;
    size_t          body_len;
    char            headers[2048];
} http_response_t;

/* Request handler */
typedef void (*api_handler_t)(const http_request_t *req, http_response_t *resp, void *ctx);

/* Route */
typedef struct api_route {
    http_method_t   method;
    char            path[128];
    api_handler_t   handler;
    struct api_route *next;
} api_route_t;

/* API server */
typedef struct api_server {
    int             socket;
    uint16_t        port;
    bool            running;
    api_route_t     *routes;
    void            *context;
} api_server_t;

/* API */
shield_err_t api_server_init(api_server_t *server, uint16_t port, void *context);
void api_server_destroy(api_server_t *server);

shield_err_t api_add_route(api_server_t *server, http_method_t method,
                            const char *path, api_handler_t handler);

shield_err_t api_server_start(api_server_t *server);
void api_server_stop(api_server_t *server);

/* Process single request (for embedded use) */
shield_err_t api_process_request(api_server_t *server, int client_socket);

/* Response helpers */
void api_response_json(http_response_t *resp, int status, const char *json);
void api_response_text(http_response_t *resp, int status, const char *text);
void api_response_error(http_response_t *resp, int status, const char *message);

#endif /* SHIELD_API_H */
