/*
 * SENTINEL Shield - HTTP API Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

#include "shield_common.h"
#include "shield_platform.h"
#include "shield_api.h"

/* Parse HTTP method */
static http_method_t parse_method(const char *str)
{
    if (strncmp(str, "GET", 3) == 0) return HTTP_GET;
    if (strncmp(str, "POST", 4) == 0) return HTTP_POST;
    if (strncmp(str, "PUT", 3) == 0) return HTTP_PUT;
    if (strncmp(str, "DELETE", 6) == 0) return HTTP_DELETE;
    return HTTP_GET;
}

/* Parse HTTP request */
static shield_err_t parse_request(const char *data, size_t len, http_request_t *req)
{
    (void)len;
    memset(req, 0, sizeof(*req));
    
    /* Parse request line: METHOD PATH HTTP/1.x */
    char method[16], path[256];
    if (sscanf(data, "%15s %255s", method, path) != 2) {
        return SHIELD_ERR_PARSE;
    }
    
    req->method = parse_method(method);
    
    /* Split path and query */
    char *query = strchr(path, '?');
    if (query) {
        *query++ = '\0';
        strncpy(req->query, query, sizeof(req->query) - 1);
    }
    strncpy(req->path, path, sizeof(req->path) - 1);
    
    /* Find headers end */
    const char *headers_end = strstr(data, "\r\n\r\n");
    if (headers_end) {
        size_t headers_len = headers_end - data;
        if (headers_len < sizeof(req->headers)) {
            strncpy(req->headers, data, headers_len);
        }
        
        /* Body starts after headers */
        const char *body = headers_end + 4;
        req->body = (char *)body;
        req->body_len = strlen(body);
    }
    
    /* Parse Content-Type */
    const char *ct = strstr(req->headers, "Content-Type:");
    if (ct) {
        ct += 13;
        while (*ct && isspace(*ct)) ct++;
        char *end = strchr(ct, '\r');
        if (end) {
            size_t ct_len = end - ct;
            if (ct_len < sizeof(req->content_type)) {
                strncpy(req->content_type, ct, ct_len);
            }
        }
    }
    
    return SHIELD_OK;
}

/* Build HTTP response */
static char *build_response(http_response_t *resp, size_t *out_len)
{
    const char *status_text = "OK";
    if (resp->status_code == 400) status_text = "Bad Request";
    else if (resp->status_code == 404) status_text = "Not Found";
    else if (resp->status_code == 500) status_text = "Internal Server Error";
    
    char *buf = malloc(resp->body_len + 512);
    if (!buf) {
        return NULL;
    }
    
    int header_len = snprintf(buf, 512,
        "HTTP/1.1 %d %s\r\n"
        "Content-Type: %s\r\n"
        "Content-Length: %zu\r\n"
        "Connection: close\r\n"
        "Server: SENTINEL-Shield/1.0\r\n"
        "\r\n",
        resp->status_code, status_text,
        resp->content_type[0] ? resp->content_type : "text/plain",
        resp->body_len);
    
    if (resp->body && resp->body_len > 0) {
        memcpy(buf + header_len, resp->body, resp->body_len);
    }
    
    *out_len = header_len + resp->body_len;
    return buf;
}

/* Initialize API server */
shield_err_t api_server_init(api_server_t *server, uint16_t port, void *context)
{
    if (!server) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(server, 0, sizeof(*server));
    server->port = port ? port : 8080;
    server->context = context;
    server->socket = -1;
    
    return SHIELD_OK;
}

/* Destroy API server */
void api_server_destroy(api_server_t *server)
{
    if (!server) {
        return;
    }
    
    api_server_stop(server);
    
    api_route_t *route = server->routes;
    while (route) {
        api_route_t *next = route->next;
        free(route);
        route = next;
    }
    
    server->routes = NULL;
}

/* Add route */
shield_err_t api_add_route(api_server_t *server, http_method_t method,
                            const char *path, api_handler_t handler)
{
    if (!server || !path || !handler) {
        return SHIELD_ERR_INVALID;
    }
    
    api_route_t *route = calloc(1, sizeof(api_route_t));
    if (!route) {
        return SHIELD_ERR_NOMEM;
    }
    
    route->method = method;
    strncpy(route->path, path, sizeof(route->path) - 1);
    route->handler = handler;
    
    route->next = server->routes;
    server->routes = route;
    
    return SHIELD_OK;
}

/* Find route */
static api_route_t *find_route(api_server_t *server, http_method_t method, const char *path)
{
    api_route_t *route = server->routes;
    while (route) {
        if (route->method == method && strcmp(route->path, path) == 0) {
            return route;
        }
        route = route->next;
    }
    return NULL;
}

/* Start server */
shield_err_t api_server_start(api_server_t *server)
{
    if (!server) {
        return SHIELD_ERR_INVALID;
    }
    
    platform_network_init();
    
    server->socket = socket(AF_INET, SOCK_STREAM, 0);
    if (server->socket < 0) {
        return SHIELD_ERR_IO;
    }
    
    int reuse = 1;
    setsockopt(server->socket, SOL_SOCKET, SO_REUSEADDR, (const char *)&reuse, sizeof(reuse));
    
    struct sockaddr_in addr = {
        .sin_family = AF_INET,
        .sin_port = htons(server->port),
        .sin_addr.s_addr = INADDR_ANY,
    };
    
    if (bind(server->socket, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        socket_close(server->socket);
        return SHIELD_ERR_IO;
    }
    
    if (listen(server->socket, 10) < 0) {
        socket_close(server->socket);
        return SHIELD_ERR_IO;
    }
    
    server->running = true;
    LOG_INFO("API server listening on port %u", server->port);
    
    return SHIELD_OK;
}

/* Stop server */
void api_server_stop(api_server_t *server)
{
    if (!server) {
        return;
    }
    
    server->running = false;
    
    if (server->socket >= 0) {
        socket_close(server->socket);
        server->socket = -1;
    }
}

/* Process request */
shield_err_t api_process_request(api_server_t *server, int client_socket)
{
    if (!server || client_socket < 0) {
        return SHIELD_ERR_INVALID;
    }
    
    /* Read request */
    char buffer[4096];
    ssize_t received = recv(client_socket, buffer, sizeof(buffer) - 1, 0);
    if (received <= 0) {
        return SHIELD_ERR_IO;
    }
    buffer[received] = '\0';
    
    /* Parse request */
    http_request_t req;
    shield_err_t err = parse_request(buffer, received, &req);
    if (err != SHIELD_OK) {
        return err;
    }
    
    /* Find and call handler */
    http_response_t resp = {0};
    
    api_route_t *route = find_route(server, req.method, req.path);
    if (route) {
        route->handler(&req, &resp, server->context);
    } else {
        api_response_error(&resp, 404, "Not Found");
    }
    
    /* Send response */
    size_t resp_len;
    char *resp_data = build_response(&resp, &resp_len);
    if (resp_data) {
        send(client_socket, resp_data, (int)resp_len, 0);
        free(resp_data);
    }
    
    if (resp.body) {
        free(resp.body);
    }
    
    return SHIELD_OK;
}

/* Response helpers */
void api_response_json(http_response_t *resp, int status, const char *json)
{
    resp->status_code = status;
    strncpy(resp->content_type, "application/json", sizeof(resp->content_type) - 1);
    resp->body = strdup(json);
    resp->body_len = strlen(json);
}

void api_response_text(http_response_t *resp, int status, const char *text)
{
    resp->status_code = status;
    strncpy(resp->content_type, "text/plain", sizeof(resp->content_type) - 1);
    resp->body = strdup(text);
    resp->body_len = strlen(text);
}

void api_response_error(http_response_t *resp, int status, const char *message)
{
    char json[256];
    snprintf(json, sizeof(json), "{\"error\": \"%s\"}", message);
    api_response_json(resp, status, json);
}
