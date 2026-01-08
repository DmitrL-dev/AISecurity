/*
 * SENTINEL IMMUNE — SENTINEL Bridge
 * 
 * Integration bridge between IMMUNE Hive and SENTINEL Brain.
 * Provides edge inference (fast local checks) and async Brain queries.
 * 
 * Features:
 * - Edge inference with Bloom filter
 * - HTTP client for Brain API
 * - Async query with callbacks
 * - Pattern cache synchronization
 */

#ifndef IMMUNE_SENTINEL_BRIDGE_H
#define IMMUNE_SENTINEL_BRIDGE_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#include "bloom_filter.h"

/* Default Brain API URL */
#define BRIDGE_DEFAULT_URL      "http://localhost:8080/api/v1"
#define BRIDGE_DEFAULT_TIMEOUT  5000    /* ms */
#define BRIDGE_DEFAULT_POOL     10

/* Detection result */
typedef enum {
    DETECT_CLEAN,       /* No threat detected */
    DETECT_SUSPICIOUS,  /* Needs Brain query for confirmation */
    DETECT_BLOCK,       /* Definite threat - block */
    DETECT_UNKNOWN,     /* Query failed / uncertain */
    DETECT_ERROR        /* Internal error */
} detect_result_t;

/* Threat level from Brain */
typedef enum {
    THREAT_NONE    = 0,
    THREAT_LOW     = 1,
    THREAT_MEDIUM  = 2,
    THREAT_HIGH    = 3,
    THREAT_CRITICAL = 4
} threat_level_t;

/* Detection context */
typedef struct {
    const char *syscall;        /* Syscall name (execve, connect, etc.) */
    uint32_t    pid;            /* Process ID */
    uint32_t    uid;            /* User ID */
    const char *agent_id;       /* Agent identifier */
    const char *command;        /* Command line (for execve) */
    const char *path;           /* File path (for open) */
    const char *addr;           /* Network address (for connect) */
} detect_context_t;

/* Detection response */
typedef struct {
    detect_result_t result;
    threat_level_t  level;
    const char     *engine;     /* Engine that detected (if any) */
    const char     *details;    /* Human-readable details */
    float           score;      /* Confidence score 0.0-1.0 */
} detect_response_t;

/* Async query callback */
typedef void (*bridge_callback_t)(
    void *user_data,
    const detect_response_t *response
);

/* Bridge configuration */
typedef struct {
    char    brain_url[256];     /* Brain API base URL */
    int     timeout_ms;         /* Query timeout */
    int     pool_size;          /* Connection pool size */
    bool    async_enabled;      /* Enable async queries */
    bool    cache_enabled;      /* Enable pattern cache */
    int     cache_ttl_sec;      /* Cache TTL */
    float   edge_threshold;     /* Suspicion threshold for edge */
} bridge_config_t;

/* Bridge statistics */
typedef struct {
    uint64_t edge_queries;      /* Total edge queries */
    uint64_t edge_clean;        /* Edge: clean */
    uint64_t edge_block;        /* Edge: blocked */
    uint64_t edge_suspicious;   /* Edge: needs Brain */
    uint64_t brain_queries;     /* Total Brain queries */
    uint64_t brain_success;     /* Brain: successful */
    uint64_t brain_timeout;     /* Brain: timeout */
    uint64_t brain_error;       /* Brain: error */
    uint64_t cache_hits;        /* Cache hits */
    uint64_t cache_misses;      /* Cache misses */
    double   avg_edge_ms;       /* Average edge latency */
    double   avg_brain_ms;      /* Average Brain latency */
} bridge_stats_t;

/* === Configuration === */

/**
 * Initialize configuration with defaults.
 * @param config Configuration to initialize
 */
void bridge_config_init(bridge_config_t *config);

/* === Lifecycle === */

/**
 * Initialize bridge singleton.
 * @param config Configuration (NULL for defaults)
 * @return 0 on success, -1 on error
 */
int bridge_init(const bridge_config_t *config);

/**
 * Shutdown bridge and cleanup.
 */
void bridge_shutdown(void);

/**
 * Check if bridge is initialized.
 * @return true if initialized
 */
bool bridge_is_ready(void);

/* === Edge Inference === */

/**
 * Fast local detection (no network).
 * Uses Bloom filter, entropy, length, and cached patterns.
 * @param input Input text to analyze
 * @param len   Input length
 * @param ctx   Optional context (syscall info)
 * @param resp  Output response
 * @return DETECT_CLEAN, DETECT_BLOCK, or DETECT_SUSPICIOUS
 */
detect_result_t bridge_edge_detect(const char *input, 
                                    size_t len,
                                    const detect_context_t *ctx,
                                    detect_response_t *resp);

/**
 * Quick edge check (string version).
 * @param input Null-terminated input
 * @return Detection result
 */
detect_result_t bridge_edge_check(const char *input);

/* === Brain Queries === */

/**
 * Synchronous Brain query (blocking).
 * @param input Input text
 * @param len   Input length
 * @param ctx   Optional context
 * @param resp  Output response
 * @return Detection result
 */
detect_result_t bridge_query_sync(const char *input,
                                   size_t len,
                                   const detect_context_t *ctx,
                                   detect_response_t *resp);

/**
 * Asynchronous Brain query (non-blocking).
 * @param input     Input text
 * @param len       Input length
 * @param ctx       Optional context
 * @param callback  Callback function
 * @param user_data User data passed to callback
 * @return 0 on success (query queued), -1 on error
 */
int bridge_query_async(const char *input,
                       size_t len,
                       const detect_context_t *ctx,
                       bridge_callback_t callback,
                       void *user_data);

/* === Cache === */

/**
 * Sync pattern cache from Brain.
 * @return Number of patterns synced, -1 on error
 */
int bridge_cache_sync(void);

/**
 * Clear pattern cache.
 */
void bridge_cache_clear(void);

/**
 * Get cache size.
 * @return Number of cached patterns
 */
size_t bridge_cache_size(void);

/* === Bloom Filter === */

/**
 * Get edge Bloom filter for direct access.
 * @return Bloom filter or NULL
 */
bloom_filter_t* bridge_get_bloom(void);

/**
 * Add pattern to edge Bloom filter.
 * @param pattern Pattern to add
 */
void bridge_bloom_add(const char *pattern);

/* === Statistics === */

/**
 * Get bridge statistics.
 * @param stats Output statistics
 */
void bridge_get_stats(bridge_stats_t *stats);

/**
 * Reset statistics.
 */
void bridge_reset_stats(void);

/* === Utility === */

/**
 * Get detection result string.
 * @param result Detection result
 * @return Human-readable string
 */
const char* detect_result_string(detect_result_t result);

/**
 * Get threat level string.
 * @param level Threat level
 * @return Human-readable string
 */
const char* threat_level_string(threat_level_t level);

#endif /* IMMUNE_SENTINEL_BRIDGE_H */
