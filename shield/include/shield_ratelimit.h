/*
 * SENTINEL Shield - Rate Limiter
 * 
 * Token bucket and sliding window rate limiting
 */

#ifndef SHIELD_RATELIMIT_H
#define SHIELD_RATELIMIT_H

#include "shield_common.h"

/* Rate limit algorithm */
typedef enum ratelimit_algo {
    RATELIMIT_TOKEN_BUCKET,
    RATELIMIT_SLIDING_WINDOW,
    RATELIMIT_FIXED_WINDOW,
} ratelimit_algo_t;

/* Rate limiter configuration */
typedef struct ratelimit_config {
    uint32_t        requests_per_second;
    uint32_t        burst_size;
    ratelimit_algo_t algorithm;
} ratelimit_config_t;

/* Per-key state (token bucket) */
typedef struct ratelimit_bucket {
    char            key[128];
    double          tokens;
    uint64_t        last_update;
    struct ratelimit_bucket *next;
} ratelimit_bucket_t;

/* Rate limiter */
typedef struct ratelimiter {
    ratelimit_config_t  config;
    ratelimit_bucket_t  *buckets;
    uint32_t            bucket_count;
    
    /* Statistics */
    uint64_t            allowed;
    uint64_t            denied;
} ratelimiter_t;

/* API */
shield_err_t ratelimiter_init(ratelimiter_t *rl, const ratelimit_config_t *config);
void ratelimiter_destroy(ratelimiter_t *rl);

/* Check if request is allowed */
bool ratelimit_check(ratelimiter_t *rl, const char *key);

/* Check and consume token */
bool ratelimit_acquire(ratelimiter_t *rl, const char *key);

/* Get remaining tokens for key */
double ratelimit_remaining(ratelimiter_t *rl, const char *key);

/* Reset rate limiter for key */
void ratelimit_reset(ratelimiter_t *rl, const char *key);

/* Clear all buckets */
void ratelimit_clear(ratelimiter_t *rl);

/* Get statistics */
void ratelimit_stats(ratelimiter_t *rl, uint64_t *allowed, uint64_t *denied);

#endif /* SHIELD_RATELIMIT_H */
