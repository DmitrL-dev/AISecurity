/**
 * @file vault_client.c
 * @brief SENTINEL Shield HashiCorp Vault Client Implementation
 * 
 * @author SENTINEL Team
 * @version Dragon v4.1
 * @date 2026-01-09
 */

#include "vault_client.h"
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <pthread.h>

/* Optional: libcurl for HTTP */
#ifdef SHIELD_USE_CURL
#include <curl/curl.h>
#endif

/* No external JSON library - using simple parsing */

/* ============================================================================
 * Static Variables
 * ============================================================================ */

static vault_config_t s_config;
static vault_secret_t s_cache[VAULT_MAX_CACHED_SECRETS];
static int s_cache_count = 0;
static pthread_mutex_t s_mutex = PTHREAD_MUTEX_INITIALIZER;
static bool s_initialized = false;

/* Statistics */
static int s_fetch_count = 0;
static int s_cache_hits = 0;
static int s_cache_misses = 0;
static time_t s_last_fetch = 0;

/* ============================================================================
 * Mini JSON Parser (for Vault response)
 * ============================================================================ */

/* Extract nested value from Vault KV v2 response */
/* Format: {"data":{"data":{"value":"secret"}}} */
static int vault_json_get_value(const char *json, char *value, size_t value_size) {
    /* Find "value":" pattern in nested data */
    const char *val_key = strstr(json, "\"value\":");
    if (!val_key) return -1;
    
    const char *start = val_key + 8; /* Skip "value": */
    while (*start == ' ' || *start == '\t') start++;
    
    if (*start == '"') {
        start++;
        const char *end = strchr(start, '"');
        if (!end) return -1;
        
        size_t len = end - start;
        if (len >= value_size) len = value_size - 1;
        memcpy(value, start, len);
        value[len] = '\0';
        return 0;
    }
    
    return -1;
}

/* ============================================================================
 * Cache Management
 * ============================================================================ */

static vault_secret_t* cache_find(const char *key) {
    for (int i = 0; i < s_cache_count; i++) {
        if (s_cache[i].valid && strcmp(s_cache[i].key, key) == 0) {
            return &s_cache[i];
        }
    }
    return NULL;
}

static vault_secret_t* cache_add(const char *key, const char *value) {
    vault_secret_t *entry = NULL;
    
    /* Find existing or empty slot */
    for (int i = 0; i < VAULT_MAX_CACHED_SECRETS; i++) {
        if (!s_cache[i].valid) {
            entry = &s_cache[i];
            s_cache_count++;
            break;
        }
    }
    
    /* If no empty slot, evict oldest */
    if (!entry) {
        time_t oldest = time(NULL);
        int oldest_idx = 0;
        for (int i = 0; i < VAULT_MAX_CACHED_SECRETS; i++) {
            if (s_cache[i].fetched_at < oldest) {
                oldest = s_cache[i].fetched_at;
                oldest_idx = i;
            }
        }
        entry = &s_cache[oldest_idx];
    }
    
    /* Fill entry */
    strncpy(entry->key, key, VAULT_MAX_KEY_SIZE - 1);
    strncpy(entry->value, value, VAULT_MAX_VALUE_SIZE - 1);
    entry->fetched_at = time(NULL);
    entry->expires_at = entry->fetched_at + s_config.cache_ttl_seconds;
    entry->valid = true;
    
    return entry;
}

static bool cache_is_valid(vault_secret_t *entry) {
    if (!entry || !entry->valid) return false;
    if (s_config.cache_ttl_seconds <= 0) return false;
    return time(NULL) < entry->expires_at;
}

/* ============================================================================
 * HTTP Client (Stub / libcurl)
 * ============================================================================ */

#ifdef SHIELD_USE_CURL

static size_t write_callback(void *contents, size_t size, size_t nmemb, void *userp) {
    size_t realsize = size * nmemb;
    char *buffer = (char*)userp;
    strncat(buffer, contents, realsize);
    return realsize;
}

static int fetch_from_vault(const char *key, char *value, size_t value_size) {
    CURL *curl;
    CURLcode res;
    char url[1024];
    char response[8192] = {0};
    char auth_header[512];
    struct curl_slist *headers = NULL;
    
    curl = curl_easy_init();
    if (!curl) return VAULT_ERR_HTTP_FAILED;
    
    /* Build URL: /v1/secret/data/{path}/{key} */
    snprintf(url, sizeof(url), "%s/v1/%s/%s", 
             s_config.address, s_config.secret_path, key);
    
    /* Auth header */
    snprintf(auth_header, sizeof(auth_header), "X-Vault-Token: %s", s_config.token);
    headers = curl_slist_append(headers, auth_header);
    headers = curl_slist_append(headers, "Content-Type: application/json");
    
    curl_easy_setopt(curl, CURLOPT_URL, url);
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_callback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, response);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, s_config.timeout_seconds);
    
    if (!s_config.verify_ssl) {
        curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 0L);
        curl_easy_setopt(curl, CURLOPT_SSL_VERIFYHOST, 0L);
    }
    
    res = curl_easy_perform(curl);
    curl_slist_free_all(headers);
    curl_easy_cleanup(curl);
    
    if (res != CURLE_OK) {
        return VAULT_ERR_HTTP_FAILED;
    }
    
    /* Parse response using simple parser */
    if (vault_json_get_value(response, value, value_size) != 0) {
        return VAULT_ERR_PARSE_FAILED;
    }
    
    s_fetch_count++;
    s_last_fetch = time(NULL);
    
    return VAULT_ERR_SUCCESS;
}

#else

/* Stub implementation without libcurl */
static int fetch_from_vault(const char *key, char *value, size_t value_size) {
    (void)key;
    (void)value;
    (void)value_size;
    /* In stub mode, try fallback file */
    return VAULT_ERR_HTTP_FAILED;
}

#endif

/* ============================================================================
 * Fallback File
 * ============================================================================ */

static int load_secret_from_fallback(const char *key, char *value, size_t value_size) {
    if (strlen(s_config.fallback_file) == 0) {
        return VAULT_ERR_NOT_FOUND;
    }
    
    FILE *fp = fopen(s_config.fallback_file, "r");
    if (!fp) return VAULT_ERR_NOT_FOUND;
    
    char line[VAULT_MAX_VALUE_SIZE + VAULT_MAX_KEY_SIZE + 2];
    while (fgets(line, sizeof(line), fp)) {
        /* Format: key=value */
        char *eq = strchr(line, '=');
        if (!eq) continue;
        
        *eq = '\0';
        char *file_key = line;
        char *file_value = eq + 1;
        
        /* Trim newline */
        char *nl = strchr(file_value, '\n');
        if (nl) *nl = '\0';
        
        if (strcmp(file_key, key) == 0) {
            strncpy(value, file_value, value_size - 1);
            value[value_size - 1] = '\0';
            fclose(fp);
            return VAULT_ERR_SUCCESS;
        }
    }
    
    fclose(fp);
    return VAULT_ERR_NOT_FOUND;
}

/* ============================================================================
 * Public API
 * ============================================================================ */

int vault_init(const vault_config_t *config) {
    if (!config) return VAULT_ERR_INVALID_ARG;
    
    pthread_mutex_lock(&s_mutex);
    
    memcpy(&s_config, config, sizeof(vault_config_t));
    memset(s_cache, 0, sizeof(s_cache));
    s_cache_count = 0;
    s_fetch_count = 0;
    s_cache_hits = 0;
    s_cache_misses = 0;
    s_last_fetch = 0;
    s_initialized = true;
    
    pthread_mutex_unlock(&s_mutex);
    
    #ifdef SHIELD_USE_CURL
    curl_global_init(CURL_GLOBAL_DEFAULT);
    #endif
    
    return VAULT_ERR_SUCCESS;
}

void vault_cleanup(void) {
    pthread_mutex_lock(&s_mutex);
    
    memset(&s_config, 0, sizeof(vault_config_t));
    memset(s_cache, 0, sizeof(s_cache));
    s_cache_count = 0;
    s_initialized = false;
    
    pthread_mutex_unlock(&s_mutex);
    
    #ifdef SHIELD_USE_CURL
    curl_global_cleanup();
    #endif
}

bool vault_is_initialized(void) {
    return s_initialized;
}

int vault_get_secret(const char *key, char *value, size_t value_size) {
    if (!s_initialized) return VAULT_ERR_NOT_INITIALIZED;
    if (!key || !value || value_size == 0) return VAULT_ERR_INVALID_ARG;
    
    pthread_mutex_lock(&s_mutex);
    
    /* Check cache first */
    vault_secret_t *cached = cache_find(key);
    if (cached && cache_is_valid(cached)) {
        strncpy(value, cached->value, value_size - 1);
        value[value_size - 1] = '\0';
        s_cache_hits++;
        pthread_mutex_unlock(&s_mutex);
        return VAULT_ERR_SUCCESS;
    }
    
    s_cache_misses++;
    
    /* Fetch from Vault */
    int err = fetch_from_vault(key, value, value_size);
    
    /* Try fallback if enabled */
    if (err != VAULT_ERR_SUCCESS && s_config.enable_fallback) {
        err = load_secret_from_fallback(key, value, value_size);
    }
    
    /* Cache if successful */
    if (err == VAULT_ERR_SUCCESS && s_config.cache_ttl_seconds > 0) {
        cache_add(key, value);
    }
    
    pthread_mutex_unlock(&s_mutex);
    return err;
}

int vault_refresh_secret(const char *key, char *value, size_t value_size) {
    if (!s_initialized) return VAULT_ERR_NOT_INITIALIZED;
    if (!key || !value || value_size == 0) return VAULT_ERR_INVALID_ARG;
    
    pthread_mutex_lock(&s_mutex);
    
    /* Invalidate cache entry */
    vault_secret_t *cached = cache_find(key);
    if (cached) {
        cached->valid = false;
    }
    
    /* Fetch fresh from Vault */
    int err = fetch_from_vault(key, value, value_size);
    
    /* Cache if successful */
    if (err == VAULT_ERR_SUCCESS && s_config.cache_ttl_seconds > 0) {
        cache_add(key, value);
    }
    
    pthread_mutex_unlock(&s_mutex);
    return err;
}

void vault_invalidate_cache(const char *key) {
    pthread_mutex_lock(&s_mutex);
    
    if (key == NULL) {
        /* Invalidate all */
        for (int i = 0; i < VAULT_MAX_CACHED_SECRETS; i++) {
            s_cache[i].valid = false;
        }
        s_cache_count = 0;
    } else {
        vault_secret_t *cached = cache_find(key);
        if (cached) {
            cached->valid = false;
            s_cache_count--;
        }
    }
    
    pthread_mutex_unlock(&s_mutex);
}

void vault_get_status(vault_status_t *status) {
    if (!status) return;
    
    pthread_mutex_lock(&s_mutex);
    
    status->initialized = s_initialized;
    status->connected = s_last_fetch > 0;
    status->cached_secrets = s_cache_count;
    status->last_fetch = s_last_fetch;
    status->fetch_count = s_fetch_count;
    status->cache_hits = s_cache_hits;
    status->cache_misses = s_cache_misses;
    
    pthread_mutex_unlock(&s_mutex);
}

int vault_health_check(void) {
    if (!s_initialized) return VAULT_ERR_NOT_INITIALIZED;
    
    /* Try to fetch a health endpoint */
    /* For now, just return success if initialized */
    return VAULT_ERR_SUCCESS;
}

int vault_renew_token(void) {
    if (!s_initialized) return VAULT_ERR_NOT_INITIALIZED;
    /* Token renewal would be implemented with libcurl */
    /* POST /v1/auth/token/renew-self */
    return VAULT_ERR_SUCCESS;
}

int vault_load_fallback(void) {
    /* Already implemented in load_secret_from_fallback */
    return VAULT_ERR_SUCCESS;
}

int vault_save_fallback(void) {
    if (!s_initialized) return VAULT_ERR_NOT_INITIALIZED;
    if (strlen(s_config.fallback_file) == 0) return VAULT_ERR_INVALID_ARG;
    
    FILE *fp = fopen(s_config.fallback_file, "w");
    if (!fp) return VAULT_ERR_HTTP_FAILED;
    
    pthread_mutex_lock(&s_mutex);
    
    for (int i = 0; i < VAULT_MAX_CACHED_SECRETS; i++) {
        if (s_cache[i].valid) {
            fprintf(fp, "%s=%s\n", s_cache[i].key, s_cache[i].value);
        }
    }
    
    pthread_mutex_unlock(&s_mutex);
    
    fclose(fp);
    return VAULT_ERR_SUCCESS;
}

const char* vault_strerror(int error_code) {
    switch (error_code) {
        case VAULT_ERR_SUCCESS:         return "Success";
        case VAULT_ERR_NOT_INITIALIZED: return "Vault client not initialized";
        case VAULT_ERR_INVALID_ARG:     return "Invalid argument";
        case VAULT_ERR_HTTP_FAILED:     return "HTTP request failed";
        case VAULT_ERR_NOT_FOUND:       return "Secret not found";
        case VAULT_ERR_AUTH_FAILED:     return "Authentication failed";
        case VAULT_ERR_PARSE_FAILED:    return "Response parse failed";
        case VAULT_ERR_CACHE_MISS:      return "Cache miss";
        case VAULT_ERR_MALLOC:          return "Memory allocation failed";
        default:                        return "Unknown error";
    }
}
