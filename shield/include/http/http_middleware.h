/**
 * @file http_middleware.h
 * @brief SENTINEL Shield HTTP Middleware
 * 
 * Authentication and rate limiting middleware for Shield HTTP server.
 * 
 * @author SENTINEL Team
 * @version Dragon v4.1
 * @date 2026-01-09
 */

#ifndef HTTP_MIDDLEWARE_H
#define HTTP_MIDDLEWARE_H

#include "http/http_server.h"
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ============================================================================
 * Configuration
 * ============================================================================ */

#define MIDDLEWARE_MAX_WHITELIST 32

/**
 * @brief Middleware configuration
 */
typedef struct {
    /* JWT settings */
    bool        jwt_enabled;
    const char *jwt_secret;
    const char *jwt_issuer;
    const char *jwt_audience;
    int         jwt_clock_skew;
    
    /* Rate limiting settings */
    bool        rate_limit_enabled;
    int         rate_limit_rpm;         /**< Requests per minute */
    int         rate_limit_burst;       /**< Burst size */
    
    /* Whitelisted paths (no auth required) */
    const char *whitelist[MIDDLEWARE_MAX_WHITELIST];
    size_t      whitelist_count;
} http_middleware_config_t;

/* Default configuration */
#define HTTP_MIDDLEWARE_CONFIG_DEFAULT { \
    .jwt_enabled = false, \
    .jwt_secret = NULL, \
    .jwt_issuer = NULL, \
    .jwt_audience = NULL, \
    .jwt_clock_skew = 30, \
    .rate_limit_enabled = false, \
    .rate_limit_rpm = 60, \
    .rate_limit_burst = 10, \
    .whitelist_count = 0 \
}

/* ============================================================================
 * Middleware Result
 * ============================================================================ */

typedef enum {
    MIDDLEWARE_OK = 0,          /**< Request allowed, continue */
    MIDDLEWARE_UNAUTHORIZED,    /**< JWT auth failed */
    MIDDLEWARE_RATE_LIMITED,    /**< Rate limit exceeded */
    MIDDLEWARE_ERROR            /**< Internal error */
} middleware_result_t;

/**
 * @brief Middleware context passed through handlers
 */
typedef struct {
    char        user_id[256];       /**< Extracted from JWT sub claim */
    char        user_roles[512];    /**< Extracted from JWT roles claim */
    int         rate_remaining;     /**< Remaining rate limit */
    int         rate_limit;         /**< Total rate limit */
    bool        authenticated;      /**< True if JWT valid */
} middleware_context_t;

/* ============================================================================
 * API Functions
 * ============================================================================ */

/**
 * @brief Initialize middleware with configuration
 * 
 * @param config Middleware configuration
 * @return 0 on success
 */
int http_middleware_init(const http_middleware_config_t *config);

/**
 * @brief Cleanup middleware
 */
void http_middleware_cleanup(void);

/**
 * @brief Process incoming request through middleware chain
 * 
 * Must be called before route handler. Sets up context and checks auth/limits.
 * 
 * @param request HTTP request
 * @param response HTTP response (filled on error)
 * @param ctx Middleware context (output)
 * @return MIDDLEWARE_OK to continue, error code to stop
 */
middleware_result_t http_middleware_process(
    const http_request_t *request,
    http_response_t *response,
    middleware_context_t *ctx
);

/**
 * @brief Add rate limit headers to response
 * 
 * @param response HTTP response
 * @param ctx Middleware context
 */
void http_middleware_add_headers(
    http_response_t *response,
    const middleware_context_t *ctx
);

/**
 * @brief Check if path is whitelisted (no auth required)
 * 
 * @param path Request path
 * @return true if whitelisted
 */
bool http_middleware_is_whitelisted(const char *path);

/**
 * @brief Add path to whitelist
 * 
 * @param path Path to whitelist (e.g., "/health", "/metrics")
 * @return 0 on success
 */
int http_middleware_whitelist_add(const char *path);

#ifdef __cplusplus
}
#endif

#endif /* HTTP_MIDDLEWARE_H */
