/**
 * @file http_server.h
 * @brief SENTINEL Shield HTTP Server Interface
 * 
 * Pure C HTTP/1.1 server for Shield REST API.
 * Zero external dependencies.
 * 
 * @author SENTINEL Team
 * @date January 2026
 */

#ifndef SHIELD_HTTP_SERVER_H
#define SHIELD_HTTP_SERVER_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ============================================================================
 * Configuration
 * ============================================================================ */

/**
 * @brief HTTP server configuration
 */
typedef struct {
    uint16_t port;              /**< Listen port (default: 8080) */
    const char *bind_address;   /**< Bind address (default: "0.0.0.0") */
    int backlog;                /**< Listen backlog (default: 128) */
    int max_connections;        /**< Max concurrent connections (default: 1000) */
    int thread_pool_size;       /**< Worker threads (default: 4) */
    bool enable_keep_alive;     /**< HTTP keep-alive (default: true) */
    int keep_alive_timeout_ms;  /**< Keep-alive timeout (default: 30000) */
    int request_timeout_ms;     /**< Request timeout (default: 5000) */
    size_t max_request_size;    /**< Max request body (default: 1MB) */
    bool enable_metrics;        /**< Expose /metrics endpoint */
    bool enable_health;         /**< Expose /health endpoint */
} http_server_config_t;

/**
 * @brief Default configuration
 */
#define HTTP_SERVER_CONFIG_DEFAULT { \
    .port = 8080, \
    .bind_address = "0.0.0.0", \
    .backlog = 128, \
    .max_connections = 1000, \
    .thread_pool_size = 4, \
    .enable_keep_alive = true, \
    .keep_alive_timeout_ms = 30000, \
    .request_timeout_ms = 5000, \
    .max_request_size = 1048576, \
    .enable_metrics = true, \
    .enable_health = true \
}

/* ============================================================================
 * HTTP Methods
 * ============================================================================ */

typedef enum {
    HTTP_METHOD_GET,
    HTTP_METHOD_POST,
    HTTP_METHOD_PUT,
    HTTP_METHOD_DELETE,
    HTTP_METHOD_PATCH,
    HTTP_METHOD_OPTIONS,
    HTTP_METHOD_HEAD,
    HTTP_METHOD_UNKNOWN
} http_method_t;

/* ============================================================================
 * HTTP Status Codes
 * ============================================================================ */

typedef enum {
    HTTP_STATUS_OK = 200,
    HTTP_STATUS_CREATED = 201,
    HTTP_STATUS_NO_CONTENT = 204,
    HTTP_STATUS_BAD_REQUEST = 400,
    HTTP_STATUS_UNAUTHORIZED = 401,
    HTTP_STATUS_FORBIDDEN = 403,
    HTTP_STATUS_NOT_FOUND = 404,
    HTTP_STATUS_METHOD_NOT_ALLOWED = 405,
    HTTP_STATUS_REQUEST_TIMEOUT = 408,
    HTTP_STATUS_PAYLOAD_TOO_LARGE = 413,
    HTTP_STATUS_UNPROCESSABLE_ENTITY = 422,
    HTTP_STATUS_TOO_MANY_REQUESTS = 429,
    HTTP_STATUS_INTERNAL_ERROR = 500,
    HTTP_STATUS_SERVICE_UNAVAILABLE = 503
} http_status_t;

/* ============================================================================
 * Request/Response Structures
 * ============================================================================ */

/**
 * @brief HTTP header
 */
typedef struct {
    char *name;
    char *value;
} http_header_t;

/**
 * @brief HTTP request
 */
typedef struct {
    http_method_t method;
    char *path;
    char *query_string;
    char *http_version;
    http_header_t *headers;
    size_t header_count;
    char *body;
    size_t body_length;
    const char *content_type;
    const char *client_ip;
    uint16_t client_port;
} http_request_t;

/**
 * @brief HTTP response
 */
typedef struct {
    http_status_t status;
    http_header_t *headers;
    size_t header_count;
    char *body;
    size_t body_length;
    const char *content_type;
} http_response_t;

/* ============================================================================
 * Route Handler
 * ============================================================================ */

/**
 * @brief Route handler function type
 * 
 * @param request Incoming request
 * @param response Response to populate
 * @param user_data User-defined context
 * @return 0 on success, non-zero on error
 */
typedef int (*http_handler_fn)(
    const http_request_t *request,
    http_response_t *response,
    void *user_data
);

/**
 * @brief Route definition
 */
typedef struct {
    http_method_t method;
    const char *path;           /**< Path pattern (e.g., "/api/v1/analyze") */
    http_handler_fn handler;
    void *user_data;
} http_route_t;

/* ============================================================================
 * Server Handle
 * ============================================================================ */

typedef struct http_server http_server_t;

/* ============================================================================
 * Server Lifecycle
 * ============================================================================ */

/**
 * @brief Create HTTP server
 * 
 * @param config Server configuration
 * @return Server handle, or NULL on error
 */
http_server_t* http_server_create(const http_server_config_t *config);

/**
 * @brief Register route
 * 
 * @param server Server handle
 * @param route Route definition
 * @return 0 on success
 */
int http_server_add_route(http_server_t *server, const http_route_t *route);

/**
 * @brief Start server (blocking)
 * 
 * @param server Server handle
 * @return 0 on clean shutdown, non-zero on error
 */
int http_server_start(http_server_t *server);

/**
 * @brief Start server (non-blocking)
 * 
 * @param server Server handle
 * @return 0 on success
 */
int http_server_start_async(http_server_t *server);

/**
 * @brief Stop server
 * 
 * @param server Server handle
 */
void http_server_stop(http_server_t *server);

/**
 * @brief Destroy server and free resources
 * 
 * @param server Server handle
 */
void http_server_destroy(http_server_t *server);

/**
 * @brief Check if server is running
 * 
 * @param server Server handle
 * @return true if running
 */
bool http_server_is_running(const http_server_t *server);

/* ============================================================================
 * Response Helpers
 * ============================================================================ */

/**
 * @brief Set response body (copies data)
 */
int http_response_set_body(http_response_t *response, const char *body, size_t length);

/**
 * @brief Set JSON response body
 */
int http_response_set_json(http_response_t *response, const char *json);

/**
 * @brief Add response header
 */
int http_response_add_header(http_response_t *response, const char *name, const char *value);

/**
 * @brief Send JSON error response
 */
int http_response_error(http_response_t *response, http_status_t status, const char *message);

/* ============================================================================
 * Metrics
 * ============================================================================ */

typedef struct {
    uint64_t requests_total;
    uint64_t requests_success;
    uint64_t requests_error;
    uint64_t bytes_received;
    uint64_t bytes_sent;
    double avg_latency_ms;
    double p99_latency_ms;
    uint64_t active_connections;
} http_server_metrics_t;

/**
 * @brief Get server metrics
 */
int http_server_get_metrics(const http_server_t *server, http_server_metrics_t *metrics);

#ifdef __cplusplus
}
#endif

#endif /* SHIELD_HTTP_SERVER_H */
