/*
 * SENTINEL Shield - Rate Limiter Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "shield_common.h"
#include "shield_ratelimit.h"

/* Get current time in microseconds */
static uint64_t get_time_us(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000 + ts.tv_nsec / 1000;
}

/* Initialize rate limiter */
shield_err_t ratelimiter_init(ratelimiter_t *rl, const ratelimit_config_t *config)
{
    if (!rl || !config) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(rl, 0, sizeof(*rl));
    memcpy(&rl->config, config, sizeof(*config));
    
    return SHIELD_OK;
}

/* Destroy rate limiter */
void ratelimiter_destroy(ratelimiter_t *rl)
{
    if (!rl) {
        return;
    }
    
    ratelimit_bucket_t *bucket = rl->buckets;
    while (bucket) {
        ratelimit_bucket_t *next = bucket->next;
        free(bucket);
        bucket = next;
    }
    
    rl->buckets = NULL;
    rl->bucket_count = 0;
}

/* Find or create bucket */
static ratelimit_bucket_t *get_bucket(ratelimiter_t *rl, const char *key)
{
    /* Find existing */
    ratelimit_bucket_t *bucket = rl->buckets;
    while (bucket) {
        if (strcmp(bucket->key, key) == 0) {
            return bucket;
        }
        bucket = bucket->next;
    }
    
    /* Create new */
    bucket = calloc(1, sizeof(ratelimit_bucket_t));
    if (!bucket) {
        return NULL;
    }
    
    strncpy(bucket->key, key, sizeof(bucket->key) - 1);
    bucket->tokens = rl->config.burst_size;
    bucket->last_update = get_time_us();
    
    bucket->next = rl->buckets;
    rl->buckets = bucket;
    rl->bucket_count++;
    
    return bucket;
}

/* Refill tokens based on time elapsed */
static void refill_tokens(ratelimiter_t *rl, ratelimit_bucket_t *bucket)
{
    uint64_t now = get_time_us();
    uint64_t elapsed = now - bucket->last_update;
    
    /* Calculate tokens to add (tokens per microsecond) */
    double tokens_per_us = (double)rl->config.requests_per_second / 1000000.0;
    double new_tokens = elapsed * tokens_per_us;
    
    bucket->tokens += new_tokens;
    
    /* Cap at burst size */
    if (bucket->tokens > rl->config.burst_size) {
        bucket->tokens = rl->config.burst_size;
    }
    
    bucket->last_update = now;
}

/* Check if request is allowed (doesn't consume) */
bool ratelimit_check(ratelimiter_t *rl, const char *key)
{
    if (!rl || !key) {
        return true; /* Allow if invalid */
    }
    
    ratelimit_bucket_t *bucket = get_bucket(rl, key);
    if (!bucket) {
        return true; /* Allow on error */
    }
    
    refill_tokens(rl, bucket);
    
    return bucket->tokens >= 1.0;
}

/* Check and consume token */
bool ratelimit_acquire(ratelimiter_t *rl, const char *key)
{
    if (!rl || !key) {
        return true;
    }
    
    ratelimit_bucket_t *bucket = get_bucket(rl, key);
    if (!bucket) {
        return true;
    }
    
    refill_tokens(rl, bucket);
    
    if (bucket->tokens >= 1.0) {
        bucket->tokens -= 1.0;
        rl->allowed++;
        return true;
    }
    
    rl->denied++;
    return false;
}

/* Get remaining tokens */
double ratelimit_remaining(ratelimiter_t *rl, const char *key)
{
    if (!rl || !key) {
        return 0.0;
    }
    
    ratelimit_bucket_t *bucket = get_bucket(rl, key);
    if (!bucket) {
        return 0.0;
    }
    
    refill_tokens(rl, bucket);
    return bucket->tokens;
}

/* Reset for key */
void ratelimit_reset(ratelimiter_t *rl, const char *key)
{
    if (!rl || !key) {
        return;
    }
    
    ratelimit_bucket_t *bucket = get_bucket(rl, key);
    if (bucket) {
        bucket->tokens = rl->config.burst_size;
        bucket->last_update = get_time_us();
    }
}

/* Clear all */
void ratelimit_clear(ratelimiter_t *rl)
{
    if (!rl) {
        return;
    }
    
    ratelimit_bucket_t *bucket = rl->buckets;
    while (bucket) {
        ratelimit_bucket_t *next = bucket->next;
        free(bucket);
        bucket = next;
    }
    
    rl->buckets = NULL;
    rl->bucket_count = 0;
}

/* Get stats */
void ratelimit_stats(ratelimiter_t *rl, uint64_t *allowed, uint64_t *denied)
{
    if (!rl) {
        return;
    }
    
    if (allowed) *allowed = rl->allowed;
    if (denied) *denied = rl->denied;
}
