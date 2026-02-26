/**
 * @file http_middleware.c
 * @brief SENTINEL Shield HTTP Middleware Implementation
 * 
 * @author SENTINEL Team
 * @version Dragon v4.1
 * @date 2026-01-09
 */

#include "http/http_middleware.h"
#include "protocols/szaa_jwt.h"
#include "core/rate_limiter.h"
#include <string.h>
#include <stdio.h>

/* ============================================================================
 * Static Variables
 * ============================================================================ */

static http_middleware_config_t s_config;
static bool s_initialized = false;

/* ============================================================================
 * Initialization
 * ============================================================================ */

int http_middleware_init(const http_middleware_config_t *config) {
    if (!config) return -1;
    
    memcpy(&s_config, config, sizeof(http_middleware_config_t));
    
    /* Initialize JWT if enabled */
    if (s_config.jwt_enabled && s_config.jwt_secret) {
        jwt_config_t jwt_cfg = {0};
        jwt_cfg.algorithm = JWT_ALG_HS256;
        strncpy(jwt_cfg.secret, s_config.jwt_secret, JWT_MAX_SECRET_SIZE - 1);
        if (s_config.jwt_issuer) {
            strncpy(jwt_cfg.issuer, s_config.jwt_issuer, JWT_MAX_CLAIM_SIZE - 1);
        }
        if (s_config.jwt_audience) {
            strncpy(jwt_cfg.audience, s_config.jwt_audience, JWT_MAX_CLAIM_SIZE - 1);
        }
        jwt_cfg.clock_skew_seconds = s_config.jwt_clock_skew;
        jwt_cfg.require_exp = true;
        
        if (jwt_init(&jwt_cfg) != JWT_ERR_SUCCESS) {
            return -1;
        }
    }
    
    /* Initialize rate limiter if enabled */
    if (s_config.rate_limit_enabled) {
        rate_limit_config_t rate_cfg = {
            .requests_per_minute = s_config.rate_limit_rpm,
            .burst_size = s_config.rate_limit_burst,
            .per_ip = true,
            .per_user = true,
            .cleanup_interval_sec = 300
        };
        
        if (rate_limiter_init(&rate_cfg) != RATE_LIMIT_ERR_SUCCESS) {
            return -1;
        }
    }
    
    s_initialized = true;
    printf("[MIDDLEWARE] Initialized (JWT=%s, RateLimit=%s)\n",
           s_config.jwt_enabled ? "ON" : "OFF",
           s_config.rate_limit_enabled ? "ON" : "OFF");
    
    return 0;
}

void http_middleware_cleanup(void) {
    if (s_config.jwt_enabled) {
        jwt_cleanup();
    }
    if (s_config.rate_limit_enabled) {
        rate_limiter_cleanup();
    }
    s_initialized = false;
}

/* ============================================================================
 * Whitelist
 * ============================================================================ */

bool http_middleware_is_whitelisted(const char *path) {
    if (!path) return false;
    
    for (size_t i = 0; i < s_config.whitelist_count; i++) {
        if (s_config.whitelist[i] && strcmp(s_config.whitelist[i], path) == 0) {
            return true;
        }
    }
    
    /* Default whitelisted paths */
    if (strcmp(path, "/health") == 0) return true;
    if (strcmp(path, "/healthz") == 0) return true;
    if (strcmp(path, "/ready") == 0) return true;
    if (strcmp(path, "/metrics") == 0) return true;
    
    return false;
}

int http_middleware_whitelist_add(const char *path) {
    if (!path) return -1;
    if (s_config.whitelist_count >= MIDDLEWARE_MAX_WHITELIST) return -1;
    
    s_config.whitelist[s_config.whitelist_count++] = path;
    return 0;
}

/* ============================================================================
 * Request Processing
 * ============================================================================ */

static const char* get_header(const http_request_t *request, const char *name) {
    if (!request || !name) return NULL;
    
    for (size_t i = 0; i < request->header_count; i++) {
        if (request->headers[i].name && 
            strcasecmp(request->headers[i].name, name) == 0) {
            return request->headers[i].value;
        }
    }
    return NULL;
}

middleware_result_t http_middleware_process(
    const http_request_t *request,
    http_response_t *response,
    middleware_context_t *ctx
) {
    if (!request || !response || !ctx) {
        return MIDDLEWARE_ERROR;
    }
    
    memset(ctx, 0, sizeof(middleware_context_t));
    
    /* Skip middleware for whitelisted paths */
    if (http_middleware_is_whitelisted(request->path)) {
        ctx->authenticated = true;
        return MIDDLEWARE_OK;
    }
    
    /* Rate limiting check */
    if (s_config.rate_limit_enabled && s_initialized) {
        char key[256];
        rate_limiter_make_key(request->client_ip, ctx->user_id, key, sizeof(key));
        
        rate_limit_result_t rate_result;
        int err = rate_limiter_check(key, &rate_result);
        
        ctx->rate_remaining = rate_result.remaining;
        ctx->rate_limit = rate_result.limit;
        
        if (err == RATE_LIMIT_ERR_EXCEEDED) {
            response->status = HTTP_STATUS_TOO_MANY_REQUESTS;
            http_response_error(response, HTTP_STATUS_TOO_MANY_REQUESTS, 
                              "Rate limit exceeded");
            
            /* Add Retry-After header */
            char retry_after[32];
            snprintf(retry_after, sizeof(retry_after), "%d", rate_result.retry_after);
            http_response_add_header(response, "Retry-After", retry_after);
            
            return MIDDLEWARE_RATE_LIMITED;
        }
    }
    
    /* JWT authentication */
    if (s_config.jwt_enabled && s_initialized) {
        const char *auth_header = get_header(request, "Authorization");
        
        if (!auth_header) {
            response->status = HTTP_STATUS_UNAUTHORIZED;
            http_response_error(response, HTTP_STATUS_UNAUTHORIZED, 
                              "Missing Authorization header");
            http_response_add_header(response, "WWW-Authenticate", 
                                    "Bearer realm=\"shield\"");
            return MIDDLEWARE_UNAUTHORIZED;
        }
        
        jwt_claims_t claims;
        int err = jwt_verify(auth_header, &claims);
        
        if (err != JWT_ERR_SUCCESS) {
            response->status = HTTP_STATUS_UNAUTHORIZED;
            http_response_error(response, HTTP_STATUS_UNAUTHORIZED, 
                              jwt_strerror(err));
            http_response_add_header(response, "WWW-Authenticate", 
                                    "Bearer realm=\"shield\"");
            return MIDDLEWARE_UNAUTHORIZED;
        }
        
        /* Extract user info */
        strncpy(ctx->user_id, claims.sub, sizeof(ctx->user_id) - 1);
        jwt_get_claim(&claims, "roles", ctx->user_roles, sizeof(ctx->user_roles));
        ctx->authenticated = true;
    }
    
    return MIDDLEWARE_OK;
}

/* ============================================================================
 * Response Headers
 * ============================================================================ */

void http_middleware_add_headers(
    http_response_t *response,
    const middleware_context_t *ctx
) {
    if (!response || !ctx) return;
    
    /* Add rate limit headers */
    if (s_config.rate_limit_enabled) {
        char limit_str[32], remaining_str[32];
        snprintf(limit_str, sizeof(limit_str), "%d", ctx->rate_limit);
        snprintf(remaining_str, sizeof(remaining_str), "%d", ctx->rate_remaining);
        
        http_response_add_header(response, "X-RateLimit-Limit", limit_str);
        http_response_add_header(response, "X-RateLimit-Remaining", remaining_str);
    }
}
