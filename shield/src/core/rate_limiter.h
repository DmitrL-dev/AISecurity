/**
 * @file rate_limiter.h
 * @brief SENTINEL Shield Rate Limiting Module
 * 
 * Token bucket rate limiting for Shield HTTP server.
 * Supports per-IP and per-user limits.
 * 
 * @author SENTINEL Team
 * @version Dragon v4.1
 * @date 2026-01-09
 */

#ifndef RATE_LIMITER_H
#define RATE_LIMITER_H

#include <stdbool.h>
#include <stdint.h>
#include <time.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ============================================================================
 * Constants
 * ============================================================================ */

#define RATE_LIMIT_MAX_KEY_SIZE     256
#define RATE_LIMIT_MAX_BUCKETS      65536

#define RATE_LIMIT_ERR_SUCCESS      0
#define RATE_LIMIT_ERR_EXCEEDED     -1
#define RATE_LIMIT_ERR_MALLOC       -2
#define RATE_LIMIT_ERR_NOT_INIT     -3
#define RATE_LIMIT_ERR_INVALID_ARG  -4

/* ============================================================================
 * Types
 * ============================================================================ */

/**
 * @brief Rate limit configuration
 */
typedef struct {
    int     requests_per_minute;    /**< Max requests per minute */
    int     burst_size;             /**< Max burst size (bucket capacity) */
    bool    per_ip;                 /**< Enable per-IP limiting */
    bool    per_user;               /**< Enable per-user limiting */
    int     cleanup_interval_sec;   /**< Interval for bucket cleanup */
} rate_limit_config_t;

/**
 * @brief Rate limit check result
 */
typedef struct {
    int     remaining;              /**< Remaining requests */
    int     limit;                  /**< Total limit */
    time_t  reset_at;               /**< When bucket resets (Unix timestamp) */
    int     retry_after;            /**< Seconds to wait before retry */
} rate_limit_result_t;

/**
 * @brief Rate limit headers for HTTP response
 */
typedef struct {
    char    x_ratelimit_limit[32];      /**< X-RateLimit-Limit */
    char    x_ratelimit_remaining[32];   /**< X-RateLimit-Remaining */
    char    x_ratelimit_reset[32];       /**< X-RateLimit-Reset */
    char    retry_after[32];             /**< Retry-After */
} rate_limit_headers_t;

/* ============================================================================
 * API Functions
 * ============================================================================ */

/**
 * @brief Initialize rate limiter with configuration
 * 
 * @param config Pointer to rate limit configuration
 * @return RATE_LIMIT_ERR_SUCCESS on success
 */
int rate_limiter_init(const rate_limit_config_t *config);

/**
 * @brief Cleanup rate limiter and free resources
 */
void rate_limiter_cleanup(void);

/**
 * @brief Check if request is allowed
 * 
 * Decrements token bucket if allowed, returns error if limit exceeded.
 * 
 * @param key Unique key (IP address or user ID)
 * @param result Pointer to result structure
 * @return RATE_LIMIT_ERR_SUCCESS if allowed, RATE_LIMIT_ERR_EXCEEDED if not
 */
int rate_limiter_check(const char *key, rate_limit_result_t *result);

/**
 * @brief Get rate limit headers for HTTP response
 * 
 * @param result Rate limit result from check
 * @param headers Pointer to headers structure to fill
 */
void rate_limiter_get_headers(const rate_limit_result_t *result,
                              rate_limit_headers_t *headers);

/**
 * @brief Reset rate limit for a specific key
 * 
 * @param key Key to reset
 * @return RATE_LIMIT_ERR_SUCCESS on success
 */
int rate_limiter_reset(const char *key);

/**
 * @brief Get current bucket count (for monitoring)
 * 
 * @return Number of active buckets
 */
size_t rate_limiter_bucket_count(void);

/**
 * @brief Check if rate limiter is initialized
 * 
 * @return true if initialized
 */
bool rate_limiter_is_initialized(void);

/* ============================================================================
 * Utility Functions
 * ============================================================================ */

/**
 * @brief Create composite key from IP and user
 * 
 * @param ip Client IP address
 * @param user_id User ID (can be NULL)
 * @param key Output buffer for composite key
 * @param key_size Size of output buffer
 */
void rate_limiter_make_key(const char *ip, const char *user_id,
                           char *key, size_t key_size);

#ifdef __cplusplus
}
#endif

#endif /* RATE_LIMITER_H */
