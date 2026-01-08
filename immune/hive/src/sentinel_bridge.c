/*
 * SENTINEL IMMUNE — SENTINEL Bridge Implementation
 * 
 * Bridge between IMMUNE Hive and SENTINEL Brain.
 * Provides edge inference and async Brain queries.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <pthread.h>
#include <time.h>
#include <unistd.h>

/* For HTTP - optional libcurl */
#ifdef USE_CURL
#include <curl/curl.h>
#endif

#include "sentinel_bridge.h"

/* ==================== Constants ==================== */

#define MAX_CACHE_SIZE      1000
#define MAX_ASYNC_QUEUE     100
#define ENTROPY_THRESHOLD   4.5

/* ==================== Internal Structures ==================== */

/* Cache entry */
typedef struct {
    char        pattern[256];
    threat_level_t level;
    time_t      timestamp;
    bool        valid;
} cache_entry_t;

/* Async query item */
typedef struct {
    char               *input;
    size_t              len;
    detect_context_t    ctx;
    bridge_callback_t   callback;
    void               *user_data;
} async_item_t;

/* Bridge singleton */
static struct {
    bool                initialized;
    bridge_config_t     config;
    bloom_filter_t     *bloom;
    
    /* Cache */
    cache_entry_t       cache[MAX_CACHE_SIZE];
    size_t              cache_count;
    pthread_mutex_t     cache_lock;
    
    /* Async */
    pthread_t           async_thread;
    async_item_t        async_queue[MAX_ASYNC_QUEUE];
    int                 async_head;
    int                 async_tail;
    pthread_mutex_t     async_lock;
    pthread_cond_t      async_cond;
    bool                async_running;
    
    /* Statistics */
    bridge_stats_t      stats;
    pthread_mutex_t     stats_lock;
    
#ifdef USE_CURL
    CURLM              *curl_multi;
#endif
} g_bridge = {0};

/* ==================== String Tables ==================== */

static const char* result_strings[] = {
    [DETECT_CLEAN]      = "Clean",
    [DETECT_SUSPICIOUS] = "Suspicious",
    [DETECT_BLOCK]      = "Block",
    [DETECT_UNKNOWN]    = "Unknown",
    [DETECT_ERROR]      = "Error"
};

static const char* level_strings[] = {
    [THREAT_NONE]     = "None",
    [THREAT_LOW]      = "Low",
    [THREAT_MEDIUM]   = "Medium",
    [THREAT_HIGH]     = "High",
    [THREAT_CRITICAL] = "Critical"
};

const char*
detect_result_string(detect_result_t result)
{
    if (result >= 0 && result <= DETECT_ERROR) {
        return result_strings[result];
    }
    return "Unknown";
}

const char*
threat_level_string(threat_level_t level)
{
    if (level >= 0 && level <= THREAT_CRITICAL) {
        return level_strings[level];
    }
    return "Unknown";
}

/* ==================== Edge Analysis ==================== */

/**
 * Calculate Shannon entropy of data.
 */
static double
calculate_entropy(const char *data, size_t len)
{
    if (len == 0) return 0.0;
    
    int freq[256] = {0};
    for (size_t i = 0; i < len; i++) {
        freq[(unsigned char)data[i]]++;
    }
    
    double entropy = 0.0;
    for (int i = 0; i < 256; i++) {
        if (freq[i] > 0) {
            double p = (double)freq[i] / (double)len;
            entropy -= p * log2(p);
        }
    }
    
    return entropy;
}

/**
 * Check for suspicious patterns locally.
 */
static bool
check_suspicious_patterns(const char *input, size_t len)
{
    /* Basic suspicious patterns */
    static const char *patterns[] = {
        "/etc/passwd",
        "/etc/shadow",
        "rm -rf",
        "curl |",
        "wget ",
        "base64 -d",
        "$((",
        "eval(",
        "__import__",
        "exec(",
        NULL
    };
    
    for (int i = 0; patterns[i]; i++) {
        if (memmem(input, len, patterns[i], strlen(patterns[i]))) {
            return true;
        }
    }
    
    return false;
}

/**
 * memmem implementation for systems without it.
 */
#ifndef memmem
static void*
memmem(const void *haystack, size_t haystacklen,
       const void *needle, size_t needlelen)
{
    if (needlelen == 0) return (void *)haystack;
    if (haystacklen < needlelen) return NULL;
    
    const char *h = haystack;
    const char *n = needle;
    
    for (size_t i = 0; i <= haystacklen - needlelen; i++) {
        if (memcmp(h + i, n, needlelen) == 0) {
            return (void *)(h + i);
        }
    }
    return NULL;
}
#endif

/* ==================== Cache ==================== */

static threat_level_t
cache_lookup(const char *input)
{
    pthread_mutex_lock(&g_bridge.cache_lock);
    
    time_t now = time(NULL);
    
    for (size_t i = 0; i < g_bridge.cache_count; i++) {
        cache_entry_t *e = &g_bridge.cache[i];
        if (e->valid && 
            strcmp(e->pattern, input) == 0 &&
            (now - e->timestamp) < g_bridge.config.cache_ttl_sec) {
            
            pthread_mutex_unlock(&g_bridge.cache_lock);
            
            pthread_mutex_lock(&g_bridge.stats_lock);
            g_bridge.stats.cache_hits++;
            pthread_mutex_unlock(&g_bridge.stats_lock);
            
            return e->level;
        }
    }
    
    pthread_mutex_unlock(&g_bridge.cache_lock);
    
    pthread_mutex_lock(&g_bridge.stats_lock);
    g_bridge.stats.cache_misses++;
    pthread_mutex_unlock(&g_bridge.stats_lock);
    
    return THREAT_NONE;  /* Cache miss */
}

static void
cache_add(const char *input, threat_level_t level)
{
    pthread_mutex_lock(&g_bridge.cache_lock);
    
    /* Find empty slot or oldest entry */
    size_t idx = 0;
    time_t oldest = time(NULL);
    
    for (size_t i = 0; i < MAX_CACHE_SIZE; i++) {
        if (!g_bridge.cache[i].valid) {
            idx = i;
            break;
        }
        if (g_bridge.cache[i].timestamp < oldest) {
            oldest = g_bridge.cache[i].timestamp;
            idx = i;
        }
    }
    
    strncpy(g_bridge.cache[idx].pattern, input, 255);
    g_bridge.cache[idx].pattern[255] = '\0';
    g_bridge.cache[idx].level = level;
    g_bridge.cache[idx].timestamp = time(NULL);
    g_bridge.cache[idx].valid = true;
    
    if (idx >= g_bridge.cache_count) {
        g_bridge.cache_count = idx + 1;
    }
    
    pthread_mutex_unlock(&g_bridge.cache_lock);
}

/* ==================== Async Thread ==================== */

static void*
async_worker(void *arg)
{
    (void)arg;
    
    while (g_bridge.async_running) {
        pthread_mutex_lock(&g_bridge.async_lock);
        
        while (g_bridge.async_head == g_bridge.async_tail && 
               g_bridge.async_running) {
            pthread_cond_wait(&g_bridge.async_cond, &g_bridge.async_lock);
        }
        
        if (!g_bridge.async_running) {
            pthread_mutex_unlock(&g_bridge.async_lock);
            break;
        }
        
        /* Get item from queue */
        async_item_t item = g_bridge.async_queue[g_bridge.async_tail];
        g_bridge.async_tail = (g_bridge.async_tail + 1) % MAX_ASYNC_QUEUE;
        
        pthread_mutex_unlock(&g_bridge.async_lock);
        
        /* Process query */
        detect_response_t resp = {0};
        bridge_query_sync(item.input, item.len, &item.ctx, &resp);
        
        /* Call callback */
        if (item.callback) {
            item.callback(item.user_data, &resp);
        }
        
        free(item.input);
    }
    
    return NULL;
}

/* ==================== Configuration ==================== */

void
bridge_config_init(bridge_config_t *config)
{
    if (!config) return;
    
    strncpy(config->brain_url, BRIDGE_DEFAULT_URL, 255);
    config->timeout_ms = BRIDGE_DEFAULT_TIMEOUT;
    config->pool_size = BRIDGE_DEFAULT_POOL;
    config->async_enabled = true;
    config->cache_enabled = true;
    config->cache_ttl_sec = 300;  /* 5 minutes */
    config->edge_threshold = 0.7;
}

/* ==================== Lifecycle ==================== */

int
bridge_init(const bridge_config_t *config)
{
    if (g_bridge.initialized) {
        return 0;  /* Already initialized */
    }
    
    memset(&g_bridge, 0, sizeof(g_bridge));
    
    /* Apply config */
    if (config) {
        memcpy(&g_bridge.config, config, sizeof(bridge_config_t));
    } else {
        bridge_config_init(&g_bridge.config);
    }
    
    /* Initialize Bloom filter */
    bloom_config_t bloom_config;
    bloom_config_init(&bloom_config);
    bloom_config.expected_items = 10000;
    bloom_config.false_positive_rate = 0.01;
    
    g_bridge.bloom = bloom_create(&bloom_config);
    if (!g_bridge.bloom) {
        return -1;
    }
    
    /* Initialize locks */
    pthread_mutex_init(&g_bridge.cache_lock, NULL);
    pthread_mutex_init(&g_bridge.async_lock, NULL);
    pthread_mutex_init(&g_bridge.stats_lock, NULL);
    pthread_cond_init(&g_bridge.async_cond, NULL);
    
    /* Start async thread if enabled */
    if (g_bridge.config.async_enabled) {
        g_bridge.async_running = true;
        pthread_create(&g_bridge.async_thread, NULL, async_worker, NULL);
    }
    
#ifdef USE_CURL
    curl_global_init(CURL_GLOBAL_ALL);
    g_bridge.curl_multi = curl_multi_init();
#endif
    
    g_bridge.initialized = true;
    printf("[BRIDGE] Initialized (Brain: %s)\n", g_bridge.config.brain_url);
    
    return 0;
}

void
bridge_shutdown(void)
{
    if (!g_bridge.initialized) return;
    
    /* Stop async thread */
    if (g_bridge.config.async_enabled) {
        g_bridge.async_running = false;
        pthread_cond_signal(&g_bridge.async_cond);
        pthread_join(g_bridge.async_thread, NULL);
    }
    
    /* Cleanup */
    if (g_bridge.bloom) {
        bloom_destroy(g_bridge.bloom);
    }
    
#ifdef USE_CURL
    if (g_bridge.curl_multi) {
        curl_multi_cleanup(g_bridge.curl_multi);
    }
    curl_global_cleanup();
#endif
    
    pthread_mutex_destroy(&g_bridge.cache_lock);
    pthread_mutex_destroy(&g_bridge.async_lock);
    pthread_mutex_destroy(&g_bridge.stats_lock);
    pthread_cond_destroy(&g_bridge.async_cond);
    
    g_bridge.initialized = false;
    printf("[BRIDGE] Shutdown complete\n");
}

bool
bridge_is_ready(void)
{
    return g_bridge.initialized;
}

/* ==================== Edge Inference ==================== */

detect_result_t
bridge_edge_detect(const char *input, 
                   size_t len,
                   const detect_context_t *ctx,
                   detect_response_t *resp)
{
    if (!g_bridge.initialized || !input || len == 0) {
        if (resp) resp->result = DETECT_ERROR;
        return DETECT_ERROR;
    }
    
    (void)ctx;  /* Context used in Brain query */
    
    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);
    
    /* Initialize response */
    if (resp) {
        resp->result = DETECT_CLEAN;
        resp->level = THREAT_NONE;
        resp->score = 0.0;
        resp->details = NULL;
        resp->engine = "edge";
    }
    
    pthread_mutex_lock(&g_bridge.stats_lock);
    g_bridge.stats.edge_queries++;
    pthread_mutex_unlock(&g_bridge.stats_lock);
    
    /* Check Bloom filter */
    if (g_bridge.bloom && bloom_check(g_bridge.bloom, input, len)) {
        if (resp) {
            resp->result = DETECT_BLOCK;
            resp->level = THREAT_HIGH;
            resp->details = "Matched Bloom filter";
        }
        pthread_mutex_lock(&g_bridge.stats_lock);
        g_bridge.stats.edge_block++;
        pthread_mutex_unlock(&g_bridge.stats_lock);
        return DETECT_BLOCK;
    }
    
    /* Check suspicious patterns */
    if (check_suspicious_patterns(input, len)) {
        if (resp) {
            resp->result = DETECT_SUSPICIOUS;
            resp->level = THREAT_MEDIUM;
            resp->details = "Suspicious pattern detected";
        }
        pthread_mutex_lock(&g_bridge.stats_lock);
        g_bridge.stats.edge_suspicious++;
        pthread_mutex_unlock(&g_bridge.stats_lock);
        return DETECT_SUSPICIOUS;
    }
    
    /* Check entropy (high entropy may indicate obfuscation) */
    double entropy = calculate_entropy(input, len);
    if (entropy > ENTROPY_THRESHOLD && len > 50) {
        if (resp) {
            resp->result = DETECT_SUSPICIOUS;
            resp->level = THREAT_LOW;
            resp->score = (float)(entropy / 8.0);
            resp->details = "High entropy content";
        }
        pthread_mutex_lock(&g_bridge.stats_lock);
        g_bridge.stats.edge_suspicious++;
        pthread_mutex_unlock(&g_bridge.stats_lock);
        return DETECT_SUSPICIOUS;
    }
    
    /* Clean */
    pthread_mutex_lock(&g_bridge.stats_lock);
    g_bridge.stats.edge_clean++;
    pthread_mutex_unlock(&g_bridge.stats_lock);
    
    clock_gettime(CLOCK_MONOTONIC, &end);
    double latency_ms = (end.tv_sec - start.tv_sec) * 1000.0 +
                        (end.tv_nsec - start.tv_nsec) / 1000000.0;
    
    pthread_mutex_lock(&g_bridge.stats_lock);
    g_bridge.stats.avg_edge_ms = (g_bridge.stats.avg_edge_ms * 0.95) + 
                                  (latency_ms * 0.05);
    pthread_mutex_unlock(&g_bridge.stats_lock);
    
    return DETECT_CLEAN;
}

detect_result_t
bridge_edge_check(const char *input)
{
    if (!input) return DETECT_ERROR;
    detect_response_t resp;
    return bridge_edge_detect(input, strlen(input), NULL, &resp);
}

/* ==================== Brain Queries ==================== */

detect_result_t
bridge_query_sync(const char *input,
                  size_t len,
                  const detect_context_t *ctx,
                  detect_response_t *resp)
{
    if (!g_bridge.initialized || !input || len == 0) {
        if (resp) resp->result = DETECT_ERROR;
        return DETECT_ERROR;
    }
    
    (void)ctx;  /* Would be included in JSON body */
    
    pthread_mutex_lock(&g_bridge.stats_lock);
    g_bridge.stats.brain_queries++;
    pthread_mutex_unlock(&g_bridge.stats_lock);
    
    /* Check cache first */
    if (g_bridge.config.cache_enabled) {
        threat_level_t cached = cache_lookup(input);
        if (cached != THREAT_NONE) {
            if (resp) {
                resp->result = cached >= THREAT_MEDIUM ? DETECT_BLOCK : DETECT_CLEAN;
                resp->level = cached;
                resp->engine = "cache";
            }
            return resp->result;
        }
    }
    
#ifdef USE_CURL
    /* Make HTTP request to Brain */
    CURL *curl = curl_easy_init();
    if (!curl) {
        pthread_mutex_lock(&g_bridge.stats_lock);
        g_bridge.stats.brain_error++;
        pthread_mutex_unlock(&g_bridge.stats_lock);
        if (resp) resp->result = DETECT_ERROR;
        return DETECT_ERROR;
    }
    
    /* Build URL */
    char url[512];
    snprintf(url, sizeof(url), "%s/analyze", g_bridge.config.brain_url);
    
    /* Build JSON body */
    char body[4096];
    snprintf(body, sizeof(body),
             "{\"text\":\"%.*s\",\"mode\":\"standard\"}",
             (int)(len > 3000 ? 3000 : len), input);
    
    struct curl_slist *headers = NULL;
    headers = curl_slist_append(headers, "Content-Type: application/json");
    
    curl_easy_setopt(curl, CURLOPT_URL, url);
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, body);
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT_MS, g_bridge.config.timeout_ms);
    
    CURLcode res = curl_easy_perform(curl);
    
    curl_slist_free_all(headers);
    curl_easy_cleanup(curl);
    
    if (res != CURLE_OK) {
        pthread_mutex_lock(&g_bridge.stats_lock);
        if (res == CURLE_OPERATION_TIMEDOUT) {
            g_bridge.stats.brain_timeout++;
        } else {
            g_bridge.stats.brain_error++;
        }
        pthread_mutex_unlock(&g_bridge.stats_lock);
        
        if (resp) {
            resp->result = DETECT_UNKNOWN;
            resp->details = curl_easy_strerror(res);
        }
        return DETECT_UNKNOWN;
    }
    
    /* Would parse JSON response here */
    pthread_mutex_lock(&g_bridge.stats_lock);
    g_bridge.stats.brain_success++;
    pthread_mutex_unlock(&g_bridge.stats_lock);
    
    if (resp) {
        resp->result = DETECT_CLEAN;  /* From response */
        resp->engine = "brain";
    }
    
#else
    /* No curl - simulate response */
    if (resp) {
        resp->result = DETECT_CLEAN;
        resp->engine = "mock";
        resp->details = "Brain not available (no libcurl)";
    }
    
    pthread_mutex_lock(&g_bridge.stats_lock);
    g_bridge.stats.brain_success++;
    pthread_mutex_unlock(&g_bridge.stats_lock);
#endif
    
    /* Cache result */
    if (g_bridge.config.cache_enabled && resp) {
        cache_add(input, resp->level);
    }
    
    return resp ? resp->result : DETECT_CLEAN;
}

int
bridge_query_async(const char *input,
                   size_t len,
                   const detect_context_t *ctx,
                   bridge_callback_t callback,
                   void *user_data)
{
    if (!g_bridge.initialized || !g_bridge.config.async_enabled) {
        return -1;
    }
    
    pthread_mutex_lock(&g_bridge.async_lock);
    
    /* Check queue full */
    int next_head = (g_bridge.async_head + 1) % MAX_ASYNC_QUEUE;
    if (next_head == g_bridge.async_tail) {
        pthread_mutex_unlock(&g_bridge.async_lock);
        return -1;  /* Queue full */
    }
    
    /* Add to queue */
    async_item_t *item = &g_bridge.async_queue[g_bridge.async_head];
    item->input = strndup(input, len);
    item->len = len;
    if (ctx) {
        memcpy(&item->ctx, ctx, sizeof(detect_context_t));
    }
    item->callback = callback;
    item->user_data = user_data;
    
    g_bridge.async_head = next_head;
    
    pthread_cond_signal(&g_bridge.async_cond);
    pthread_mutex_unlock(&g_bridge.async_lock);
    
    return 0;
}

/* ==================== Cache === */

int
bridge_cache_sync(void)
{
    /* Would fetch patterns from Brain and update local cache/bloom */
    /* For now, return 0 (success, no patterns synced) */
    return 0;
}

void
bridge_cache_clear(void)
{
    pthread_mutex_lock(&g_bridge.cache_lock);
    memset(g_bridge.cache, 0, sizeof(g_bridge.cache));
    g_bridge.cache_count = 0;
    pthread_mutex_unlock(&g_bridge.cache_lock);
}

size_t
bridge_cache_size(void)
{
    return g_bridge.cache_count;
}

/* ==================== Bloom === */

bloom_filter_t*
bridge_get_bloom(void)
{
    return g_bridge.bloom;
}

void
bridge_bloom_add(const char *pattern)
{
    if (g_bridge.bloom && pattern) {
        bloom_add_string(g_bridge.bloom, pattern);
    }
}

/* ==================== Statistics === */

void
bridge_get_stats(bridge_stats_t *stats)
{
    if (!stats) return;
    
    pthread_mutex_lock(&g_bridge.stats_lock);
    memcpy(stats, &g_bridge.stats, sizeof(bridge_stats_t));
    pthread_mutex_unlock(&g_bridge.stats_lock);
}

void
bridge_reset_stats(void)
{
    pthread_mutex_lock(&g_bridge.stats_lock);
    memset(&g_bridge.stats, 0, sizeof(bridge_stats_t));
    pthread_mutex_unlock(&g_bridge.stats_lock);
}
