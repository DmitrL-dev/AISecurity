/**
 * @file rate_limiter.c
 * @brief SENTINEL Shield Rate Limiting Implementation
 * 
 * Token bucket algorithm with per-IP/user tracking.
 * 
 * @author SENTINEL Team
 * @version Dragon v4.1
 * @date 2026-01-09
 */

#include "rate_limiter.h"
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <pthread.h>

/* ============================================================================
 * Internal Types
 * ============================================================================ */

typedef struct bucket {
    char            key[RATE_LIMIT_MAX_KEY_SIZE];
    int             tokens;           /* Current token count */
    time_t          last_update;      /* Last refill time */
    struct bucket   *next;            /* Hash collision chain */
} bucket_t;

/* ============================================================================
 * Static Variables
 * ============================================================================ */

static rate_limit_config_t s_config;
static bucket_t *s_buckets[RATE_LIMIT_MAX_BUCKETS];
static pthread_mutex_t s_mutex = PTHREAD_MUTEX_INITIALIZER;
static bool s_initialized = false;

/* ============================================================================
 * Hash Function
 * ============================================================================ */

static uint32_t hash_key(const char *key) {
    /* djb2 hash */
    uint32_t hash = 5381;
    int c;
    while ((c = *key++)) {
        hash = ((hash << 5) + hash) + c;
    }
    return hash % RATE_LIMIT_MAX_BUCKETS;
}

/* ============================================================================
 * Bucket Management
 * ============================================================================ */

static bucket_t* find_bucket(const char *key) {
    uint32_t index = hash_key(key);
    bucket_t *b = s_buckets[index];
    
    while (b) {
        if (strcmp(b->key, key) == 0) {
            return b;
        }
        b = b->next;
    }
    return NULL;
}

static bucket_t* create_bucket(const char *key) {
    bucket_t *b = (bucket_t*)calloc(1, sizeof(bucket_t));
    if (!b) return NULL;
    
    strncpy(b->key, key, RATE_LIMIT_MAX_KEY_SIZE - 1);
    b->tokens = s_config.burst_size;
    b->last_update = time(NULL);
    
    /* Insert into hash table */
    uint32_t index = hash_key(key);
    b->next = s_buckets[index];
    s_buckets[index] = b;
    
    return b;
}

static void refill_bucket(bucket_t *b) {
    time_t now = time(NULL);
    time_t elapsed = now - b->last_update;
    
    if (elapsed > 0) {
        /* Calculate tokens to add based on time elapsed */
        int tokens_to_add = (int)(elapsed * s_config.requests_per_minute / 60);
        b->tokens += tokens_to_add;
        
        /* Cap at burst size */
        if (b->tokens > s_config.burst_size) {
            b->tokens = s_config.burst_size;
        }
        
        b->last_update = now;
    }
}

/* ============================================================================
 * Public API
 * ============================================================================ */

int rate_limiter_init(const rate_limit_config_t *config) {
    if (!config) return RATE_LIMIT_ERR_INVALID_ARG;
    
    pthread_mutex_lock(&s_mutex);
    
    memcpy(&s_config, config, sizeof(rate_limit_config_t));
    memset(s_buckets, 0, sizeof(s_buckets));
    s_initialized = true;
    
    pthread_mutex_unlock(&s_mutex);
    
    return RATE_LIMIT_ERR_SUCCESS;
}

void rate_limiter_cleanup(void) {
    pthread_mutex_lock(&s_mutex);
    
    /* Free all buckets */
    for (int i = 0; i < RATE_LIMIT_MAX_BUCKETS; i++) {
        bucket_t *b = s_buckets[i];
        while (b) {
            bucket_t *next = b->next;
            free(b);
            b = next;
        }
        s_buckets[i] = NULL;
    }
    
    s_initialized = false;
    
    pthread_mutex_unlock(&s_mutex);
}

bool rate_limiter_is_initialized(void) {
    return s_initialized;
}

int rate_limiter_check(const char *key, rate_limit_result_t *result) {
    if (!s_initialized) return RATE_LIMIT_ERR_NOT_INIT;
    if (!key || !result) return RATE_LIMIT_ERR_INVALID_ARG;
    
    pthread_mutex_lock(&s_mutex);
    
    bucket_t *b = find_bucket(key);
    if (!b) {
        b = create_bucket(key);
        if (!b) {
            pthread_mutex_unlock(&s_mutex);
            return RATE_LIMIT_ERR_MALLOC;
        }
    }
    
    /* Refill tokens based on elapsed time */
    refill_bucket(b);
    
    int err;
    
    if (b->tokens > 0) {
        /* Allow request, consume token */
        b->tokens--;
        err = RATE_LIMIT_ERR_SUCCESS;
    } else {
        /* Rate limit exceeded */
        err = RATE_LIMIT_ERR_EXCEEDED;
    }
    
    /* Fill result */
    result->remaining = b->tokens;
    result->limit = s_config.burst_size;
    result->reset_at = b->last_update + 60; /* Next minute */
    result->retry_after = (int)(result->reset_at - time(NULL));
    if (result->retry_after < 0) result->retry_after = 0;
    
    pthread_mutex_unlock(&s_mutex);
    
    return err;
}

void rate_limiter_get_headers(const rate_limit_result_t *result,
                              rate_limit_headers_t *headers) {
    if (!result || !headers) return;
    
    snprintf(headers->x_ratelimit_limit, sizeof(headers->x_ratelimit_limit),
             "%d", result->limit);
    snprintf(headers->x_ratelimit_remaining, sizeof(headers->x_ratelimit_remaining),
             "%d", result->remaining);
    snprintf(headers->x_ratelimit_reset, sizeof(headers->x_ratelimit_reset),
             "%ld", (long)result->reset_at);
    snprintf(headers->retry_after, sizeof(headers->retry_after),
             "%d", result->retry_after);
}

int rate_limiter_reset(const char *key) {
    if (!s_initialized) return RATE_LIMIT_ERR_NOT_INIT;
    if (!key) return RATE_LIMIT_ERR_INVALID_ARG;
    
    pthread_mutex_lock(&s_mutex);
    
    uint32_t index = hash_key(key);
    bucket_t *prev = NULL;
    bucket_t *b = s_buckets[index];
    
    while (b) {
        if (strcmp(b->key, key) == 0) {
            /* Remove from chain */
            if (prev) {
                prev->next = b->next;
            } else {
                s_buckets[index] = b->next;
            }
            free(b);
            pthread_mutex_unlock(&s_mutex);
            return RATE_LIMIT_ERR_SUCCESS;
        }
        prev = b;
        b = b->next;
    }
    
    pthread_mutex_unlock(&s_mutex);
    return RATE_LIMIT_ERR_SUCCESS; /* Not found is OK */
}

size_t rate_limiter_bucket_count(void) {
    size_t count = 0;
    
    pthread_mutex_lock(&s_mutex);
    
    for (int i = 0; i < RATE_LIMIT_MAX_BUCKETS; i++) {
        bucket_t *b = s_buckets[i];
        while (b) {
            count++;
            b = b->next;
        }
    }
    
    pthread_mutex_unlock(&s_mutex);
    return count;
}

void rate_limiter_make_key(const char *ip, const char *user_id,
                           char *key, size_t key_size) {
    if (!key || key_size == 0) return;
    
    if (user_id && strlen(user_id) > 0) {
        snprintf(key, key_size, "user:%s", user_id);
    } else if (ip && strlen(ip) > 0) {
        snprintf(key, key_size, "ip:%s", ip);
    } else {
        snprintf(key, key_size, "unknown");
    }
}
