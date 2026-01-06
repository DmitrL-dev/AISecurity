/**
 * @file http_server.c
 * @brief SENTINEL Shield HTTP Server Implementation
 * 
 * Pure C HTTP/1.1 server with zero external dependencies.
 * Cross-platform: POSIX (Linux/macOS) and Windows.
 * 
 * @author SENTINEL Team
 * @date January 2026
 */

#include "http/http_server.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <time.h>

/* Platform-specific includes */
#ifdef _WIN32
    #define WIN32_LEAN_AND_MEAN
    #include <winsock2.h>
    #include <ws2tcpip.h>
    #pragma comment(lib, "ws2_32.lib")
    typedef SOCKET socket_t;
    #define INVALID_SOCK INVALID_SOCKET
    #define close_socket closesocket
    #define socket_error() WSAGetLastError()
#else
    #include <sys/socket.h>
    #include <sys/select.h>
    #include <netinet/in.h>
    #include <netinet/tcp.h>
    #include <arpa/inet.h>
    #include <unistd.h>
    #include <fcntl.h>
    #include <pthread.h>
    typedef int socket_t;
    #define INVALID_SOCK (-1)
    #define close_socket close
    #define socket_error() errno
#endif

/* ============================================================================
 * Constants
 * ============================================================================ */

#define MAX_ROUTES 64
#define RECV_BUFFER_SIZE 8192
#define SEND_BUFFER_SIZE 8192
#define MAX_HEADERS 64

/* ============================================================================
 * Internal Structures
 * ============================================================================ */

struct http_server {
    http_server_config_t config;
    socket_t listen_fd;
    volatile bool running;
    
    /* Routes */
    http_route_t routes[MAX_ROUTES];
    size_t route_count;
    
    /* Metrics */
    http_server_metrics_t metrics;
    
    /* Thread pool (simplified for now) */
#ifndef _WIN32
    pthread_t accept_thread;
    pthread_mutex_t metrics_mutex;
#else
    HANDLE accept_thread;
    CRITICAL_SECTION metrics_mutex;
#endif
};

/* ============================================================================
 * Forward Declarations
 * ============================================================================ */

static void* accept_loop(void *arg);
static int handle_connection(http_server_t *server, socket_t client_fd, 
                            const char *client_ip, uint16_t client_port);
static int parse_request(const char *buffer, size_t length, http_request_t *request);
static int send_response(socket_t fd, const http_response_t *response);
static const http_route_t* find_route(http_server_t *server, 
                                      http_method_t method, const char *path);
static http_method_t parse_method(const char *method_str);
static const char* status_text(http_status_t status);
static void free_request(http_request_t *request);
static void free_response(http_response_t *response);

/* ============================================================================
 * Platform Initialization
 * ============================================================================ */

static int platform_init(void) {
#ifdef _WIN32
    WSADATA wsa_data;
    return WSAStartup(MAKEWORD(2, 2), &wsa_data);
#else
    return 0;
#endif
}

static void platform_cleanup(void) {
#ifdef _WIN32
    WSACleanup();
#endif
}

/* ============================================================================
 * Server Lifecycle
 * ============================================================================ */

http_server_t* http_server_create(const http_server_config_t *config) {
    if (platform_init() != 0) {
        return NULL;
    }
    
    http_server_t *server = calloc(1, sizeof(http_server_t));
    if (!server) return NULL;
    
    if (config) {
        server->config = *config;
    } else {
        http_server_config_t default_config = HTTP_SERVER_CONFIG_DEFAULT;
        server->config = default_config;
    }
    
    server->listen_fd = INVALID_SOCK;
    server->running = false;
    server->route_count = 0;
    
#ifndef _WIN32
    pthread_mutex_init(&server->metrics_mutex, NULL);
#else
    InitializeCriticalSection(&server->metrics_mutex);
#endif
    
    return server;
}

int http_server_add_route(http_server_t *server, const http_route_t *route) {
    if (!server || !route) return -1;
    if (server->route_count >= MAX_ROUTES) return -1;
    
    server->routes[server->route_count++] = *route;
    return 0;
}

int http_server_start(http_server_t *server) {
    if (!server) return -1;
    
    /* Create socket */
    server->listen_fd = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (server->listen_fd == INVALID_SOCK) {
        fprintf(stderr, "[HTTP] Failed to create socket: %d\n", socket_error());
        return -1;
    }
    
    /* Set socket options */
    int opt = 1;
    setsockopt(server->listen_fd, SOL_SOCKET, SO_REUSEADDR, 
               (const char*)&opt, sizeof(opt));
    
    /* Bind */
    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(server->config.port);
    
    if (server->config.bind_address) {
        inet_pton(AF_INET, server->config.bind_address, &addr.sin_addr);
    } else {
        addr.sin_addr.s_addr = INADDR_ANY;
    }
    
    if (bind(server->listen_fd, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
        fprintf(stderr, "[HTTP] Failed to bind to port %d: %d\n", 
                server->config.port, socket_error());
        close_socket(server->listen_fd);
        return -1;
    }
    
    /* Listen */
    if (listen(server->listen_fd, server->config.backlog) < 0) {
        fprintf(stderr, "[HTTP] Failed to listen: %d\n", socket_error());
        close_socket(server->listen_fd);
        return -1;
    }
    
    server->running = true;
    
    printf("[HTTP] Shield REST API listening on %s:%d\n",
           server->config.bind_address ? server->config.bind_address : "0.0.0.0",
           server->config.port);
    
    /* Accept loop */
    accept_loop(server);
    
    return 0;
}

int http_server_start_async(http_server_t *server) {
    if (!server) return -1;
    
    /* Create socket (same as start) */
    server->listen_fd = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (server->listen_fd == INVALID_SOCK) return -1;
    
    int opt = 1;
    setsockopt(server->listen_fd, SOL_SOCKET, SO_REUSEADDR, 
               (const char*)&opt, sizeof(opt));
    
    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(server->config.port);
    addr.sin_addr.s_addr = INADDR_ANY;
    
    if (bind(server->listen_fd, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
        close_socket(server->listen_fd);
        return -1;
    }
    
    if (listen(server->listen_fd, server->config.backlog) < 0) {
        close_socket(server->listen_fd);
        return -1;
    }
    
    server->running = true;
    
#ifndef _WIN32
    if (pthread_create(&server->accept_thread, NULL, accept_loop, server) != 0) {
        server->running = false;
        close_socket(server->listen_fd);
        return -1;
    }
#else
    server->accept_thread = CreateThread(NULL, 0, 
        (LPTHREAD_START_ROUTINE)accept_loop, server, 0, NULL);
    if (!server->accept_thread) {
        server->running = false;
        close_socket(server->listen_fd);
        return -1;
    }
#endif
    
    printf("[HTTP] Shield REST API started on port %d (async)\n", server->config.port);
    return 0;
}

void http_server_stop(http_server_t *server) {
    if (!server) return;
    
    server->running = false;
    
    if (server->listen_fd != INVALID_SOCK) {
        close_socket(server->listen_fd);
        server->listen_fd = INVALID_SOCK;
    }
    
    printf("[HTTP] Server stopped\n");
}

void http_server_destroy(http_server_t *server) {
    if (!server) return;
    
    http_server_stop(server);
    
#ifndef _WIN32
    pthread_mutex_destroy(&server->metrics_mutex);
#else
    DeleteCriticalSection(&server->metrics_mutex);
#endif
    
    free(server);
    platform_cleanup();
}

bool http_server_is_running(const http_server_t *server) {
    return server && server->running;
}

/* ============================================================================
 * Accept Loop
 * ============================================================================ */

static void* accept_loop(void *arg) {
    http_server_t *server = (http_server_t*)arg;
    
    while (server->running) {
        struct sockaddr_in client_addr;
        socklen_t addr_len = sizeof(client_addr);
        
        socket_t client_fd = accept(server->listen_fd, 
                                   (struct sockaddr*)&client_addr, 
                                   &addr_len);
        
        if (client_fd == INVALID_SOCK) {
            if (server->running) {
                fprintf(stderr, "[HTTP] Accept failed: %d\n", socket_error());
            }
            continue;
        }
        
        /* Get client info */
        char client_ip[INET_ADDRSTRLEN];
        inet_ntop(AF_INET, &client_addr.sin_addr, client_ip, sizeof(client_ip));
        uint16_t client_port = ntohs(client_addr.sin_port);
        
        /* Handle connection (simplified: synchronous for now) */
        /* TODO: Submit to thread pool */
        handle_connection(server, client_fd, client_ip, client_port);
        
        close_socket(client_fd);
    }
    
    return NULL;
}

/* ============================================================================
 * Connection Handler
 * ============================================================================ */

static int handle_connection(http_server_t *server, socket_t client_fd,
                            const char *client_ip, uint16_t client_port) {
    char buffer[RECV_BUFFER_SIZE];
    ssize_t bytes_read;
    
    /* Receive request */
    bytes_read = recv(client_fd, buffer, sizeof(buffer) - 1, 0);
    if (bytes_read <= 0) {
        return -1;
    }
    buffer[bytes_read] = '\0';
    
    /* Parse request */
    http_request_t request;
    memset(&request, 0, sizeof(request));
    request.client_ip = client_ip;
    request.client_port = client_port;
    
    if (parse_request(buffer, bytes_read, &request) != 0) {
        /* Send 400 Bad Request */
        http_response_t response = {0};
        response.status = HTTP_STATUS_BAD_REQUEST;
        http_response_error(&response, HTTP_STATUS_BAD_REQUEST, "Invalid request");
        send_response(client_fd, &response);
        free_response(&response);
        return -1;
    }
    
    /* Find route */
    const http_route_t *route = find_route(server, request.method, request.path);
    
    http_response_t response = {0};
    
    if (route) {
        /* Call handler */
        route->handler(&request, &response, route->user_data);
    } else {
        /* 404 Not Found */
        http_response_error(&response, HTTP_STATUS_NOT_FOUND, "Not found");
    }
    
    /* Send response */
    send_response(client_fd, &response);
    
    /* Update metrics */
#ifndef _WIN32
    pthread_mutex_lock(&server->metrics_mutex);
#else
    EnterCriticalSection(&server->metrics_mutex);
#endif
    server->metrics.requests_total++;
    if (response.status >= 200 && response.status < 400) {
        server->metrics.requests_success++;
    } else {
        server->metrics.requests_error++;
    }
#ifndef _WIN32
    pthread_mutex_unlock(&server->metrics_mutex);
#else
    LeaveCriticalSection(&server->metrics_mutex);
#endif
    
    /* Cleanup */
    free_request(&request);
    free_response(&response);
    
    return 0;
}

/* ============================================================================
 * Request Parser
 * ============================================================================ */

static http_method_t parse_method(const char *method_str) {
    if (strcmp(method_str, "GET") == 0) return HTTP_METHOD_GET;
    if (strcmp(method_str, "POST") == 0) return HTTP_METHOD_POST;
    if (strcmp(method_str, "PUT") == 0) return HTTP_METHOD_PUT;
    if (strcmp(method_str, "DELETE") == 0) return HTTP_METHOD_DELETE;
    if (strcmp(method_str, "PATCH") == 0) return HTTP_METHOD_PATCH;
    if (strcmp(method_str, "OPTIONS") == 0) return HTTP_METHOD_OPTIONS;
    if (strcmp(method_str, "HEAD") == 0) return HTTP_METHOD_HEAD;
    return HTTP_METHOD_UNKNOWN;
}

static int parse_request(const char *buffer, size_t length, http_request_t *request) {
    if (!buffer || !request || length < 10) return -1;
    
    /* Copy buffer for tokenization */
    char *buf_copy = strdup(buffer);
    if (!buf_copy) return -1;
    
    /* Parse request line: METHOD PATH HTTP/1.1 */
    char *line = strtok(buf_copy, "\r\n");
    if (!line) {
        free(buf_copy);
        return -1;
    }
    
    char method_str[16], path[1024], version[16];
    if (sscanf(line, "%15s %1023s %15s", method_str, path, version) != 3) {
        free(buf_copy);
        return -1;
    }
    
    request->method = parse_method(method_str);
    request->path = strdup(path);
    request->http_version = strdup(version);
    
    /* Parse query string */
    char *query = strchr(request->path, '?');
    if (query) {
        *query = '\0';
        request->query_string = strdup(query + 1);
    }
    
    /* Parse headers */
    request->headers = calloc(MAX_HEADERS, sizeof(http_header_t));
    request->header_count = 0;
    
    while ((line = strtok(NULL, "\r\n")) != NULL) {
        if (strlen(line) == 0) break; /* Empty line = end of headers */
        
        char *colon = strchr(line, ':');
        if (colon && request->header_count < MAX_HEADERS) {
            *colon = '\0';
            char *value = colon + 1;
            while (*value == ' ') value++; /* Skip leading space */
            
            request->headers[request->header_count].name = strdup(line);
            request->headers[request->header_count].value = strdup(value);
            
            /* Track Content-Type */
            if (strcasecmp(line, "Content-Type") == 0) {
                request->content_type = request->headers[request->header_count].value;
            }
            
            request->header_count++;
        }
    }
    
    /* Parse body (after \r\n\r\n) */
    const char *body_start = strstr(buffer, "\r\n\r\n");
    if (body_start) {
        body_start += 4;
        size_t body_len = length - (body_start - buffer);
        if (body_len > 0) {
            request->body = malloc(body_len + 1);
            if (request->body) {
                memcpy(request->body, body_start, body_len);
                request->body[body_len] = '\0';
                request->body_length = body_len;
            }
        }
    }
    
    free(buf_copy);
    return 0;
}

/* ============================================================================
 * Route Matching
 * ============================================================================ */

static const http_route_t* find_route(http_server_t *server, 
                                      http_method_t method, const char *path) {
    for (size_t i = 0; i < server->route_count; i++) {
        const http_route_t *route = &server->routes[i];
        
        if (route->method == method && strcmp(route->path, path) == 0) {
            return route;
        }
    }
    return NULL;
}

/* ============================================================================
 * Response Helpers
 * ============================================================================ */

static const char* status_text(http_status_t status) {
    switch (status) {
        case HTTP_STATUS_OK: return "OK";
        case HTTP_STATUS_CREATED: return "Created";
        case HTTP_STATUS_NO_CONTENT: return "No Content";
        case HTTP_STATUS_BAD_REQUEST: return "Bad Request";
        case HTTP_STATUS_UNAUTHORIZED: return "Unauthorized";
        case HTTP_STATUS_FORBIDDEN: return "Forbidden";
        case HTTP_STATUS_NOT_FOUND: return "Not Found";
        case HTTP_STATUS_METHOD_NOT_ALLOWED: return "Method Not Allowed";
        case HTTP_STATUS_REQUEST_TIMEOUT: return "Request Timeout";
        case HTTP_STATUS_PAYLOAD_TOO_LARGE: return "Payload Too Large";
        case HTTP_STATUS_UNPROCESSABLE_ENTITY: return "Unprocessable Entity";
        case HTTP_STATUS_TOO_MANY_REQUESTS: return "Too Many Requests";
        case HTTP_STATUS_INTERNAL_ERROR: return "Internal Server Error";
        case HTTP_STATUS_SERVICE_UNAVAILABLE: return "Service Unavailable";
        default: return "Unknown";
    }
}

int http_response_set_body(http_response_t *response, const char *body, size_t length) {
    if (!response) return -1;
    
    if (response->body) free(response->body);
    
    response->body = malloc(length + 1);
    if (!response->body) return -1;
    
    memcpy(response->body, body, length);
    response->body[length] = '\0';
    response->body_length = length;
    
    return 0;
}

int http_response_set_json(http_response_t *response, const char *json) {
    if (!response || !json) return -1;
    
    response->content_type = "application/json";
    return http_response_set_body(response, json, strlen(json));
}

int http_response_add_header(http_response_t *response, const char *name, const char *value) {
    if (!response || !name || !value) return -1;
    
    /* Allocate or expand headers array */
    size_t new_count = response->header_count + 1;
    http_header_t *new_headers = realloc(response->headers, 
                                         new_count * sizeof(http_header_t));
    if (!new_headers) return -1;
    
    response->headers = new_headers;
    response->headers[response->header_count].name = strdup(name);
    response->headers[response->header_count].value = strdup(value);
    response->header_count = new_count;
    
    return 0;
}

int http_response_error(http_response_t *response, http_status_t status, const char *message) {
    if (!response) return -1;
    
    response->status = status;
    
    char json[256];
    snprintf(json, sizeof(json), 
             "{\"error\":{\"code\":%d,\"message\":\"%s\"}}", 
             status, message ? message : status_text(status));
    
    return http_response_set_json(response, json);
}

static int send_response(socket_t fd, const http_response_t *response) {
    char buffer[SEND_BUFFER_SIZE];
    int offset = 0;
    
    /* Status line */
    offset += snprintf(buffer + offset, sizeof(buffer) - offset,
                      "HTTP/1.1 %d %s\r\n",
                      response->status, status_text(response->status));
    
    /* Content-Type */
    const char *content_type = response->content_type ? 
                               response->content_type : "application/json";
    offset += snprintf(buffer + offset, sizeof(buffer) - offset,
                      "Content-Type: %s\r\n", content_type);
    
    /* Content-Length */
    offset += snprintf(buffer + offset, sizeof(buffer) - offset,
                      "Content-Length: %zu\r\n", response->body_length);
    
    /* Custom headers */
    for (size_t i = 0; i < response->header_count; i++) {
        offset += snprintf(buffer + offset, sizeof(buffer) - offset,
                          "%s: %s\r\n",
                          response->headers[i].name,
                          response->headers[i].value);
    }
    
    /* Standard headers */
    offset += snprintf(buffer + offset, sizeof(buffer) - offset,
                      "Server: SENTINEL Shield/4.1\r\n"
                      "Connection: close\r\n"
                      "\r\n");
    
    /* Send headers */
    send(fd, buffer, offset, 0);
    
    /* Send body */
    if (response->body && response->body_length > 0) {
        send(fd, response->body, response->body_length, 0);
    }
    
    return 0;
}

/* ============================================================================
 * Cleanup
 * ============================================================================ */

static void free_request(http_request_t *request) {
    if (!request) return;
    
    free(request->path);
    free(request->query_string);
    free(request->http_version);
    free(request->body);
    
    for (size_t i = 0; i < request->header_count; i++) {
        free(request->headers[i].name);
        free(request->headers[i].value);
    }
    free(request->headers);
}

static void free_response(http_response_t *response) {
    if (!response) return;
    
    free(response->body);
    
    for (size_t i = 0; i < response->header_count; i++) {
        free(response->headers[i].name);
        free(response->headers[i].value);
    }
    free(response->headers);
}

/* ============================================================================
 * Metrics
 * ============================================================================ */

int http_server_get_metrics(const http_server_t *server, http_server_metrics_t *metrics) {
    if (!server || !metrics) return -1;
    
    *metrics = server->metrics;
    return 0;
}
