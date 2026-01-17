/**
 * @file vault_client.h
 * @brief SENTINEL Shield HashiCorp Vault Client
 * 
 * Integration with HashiCorp Vault for secrets management.
 * Supports KV v2 secrets engine with local caching.
 * 
 * @author SENTINEL Team
 * @version Dragon v4.1
 * @date 2026-01-09
 */

#ifndef VAULT_CLIENT_H
#define VAULT_CLIENT_H

#include <stdbool.h>
#include <stdint.h>
#include <time.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ============================================================================
 * Constants
 * ============================================================================ */

#define VAULT_MAX_URL_SIZE          512
#define VAULT_MAX_TOKEN_SIZE        256
#define VAULT_MAX_PATH_SIZE         256
#define VAULT_MAX_KEY_SIZE          128
#define VAULT_MAX_VALUE_SIZE        4096
#define VAULT_MAX_CACHED_SECRETS    256

#define VAULT_ERR_SUCCESS           0
#define VAULT_ERR_NOT_INITIALIZED   -1
#define VAULT_ERR_INVALID_ARG       -2
#define VAULT_ERR_HTTP_FAILED       -3
#define VAULT_ERR_NOT_FOUND         -4
#define VAULT_ERR_AUTH_FAILED       -5
#define VAULT_ERR_PARSE_FAILED      -6
#define VAULT_ERR_CACHE_MISS        -7
#define VAULT_ERR_MALLOC            -8

/* ============================================================================
 * Types
 * ============================================================================ */

/**
 * @brief Vault client configuration
 */
typedef struct {
    char    address[VAULT_MAX_URL_SIZE];        /**< Vault server address */
    char    token[VAULT_MAX_TOKEN_SIZE];        /**< Authentication token */
    char    secret_path[VAULT_MAX_PATH_SIZE];   /**< Base path for secrets */
    int     cache_ttl_seconds;                  /**< Cache TTL (0 = no cache) */
    int     timeout_seconds;                    /**< HTTP timeout */
    bool    verify_ssl;                         /**< Verify SSL certificates */
    bool    enable_fallback;                    /**< Allow fallback to local */
    char    fallback_file[VAULT_MAX_PATH_SIZE]; /**< Local fallback file */
} vault_config_t;

/**
 * @brief Cached secret entry
 */
typedef struct {
    char    key[VAULT_MAX_KEY_SIZE];
    char    value[VAULT_MAX_VALUE_SIZE];
    time_t  fetched_at;
    time_t  expires_at;
    bool    valid;
} vault_secret_t;

/**
 * @brief Vault client status
 */
typedef struct {
    bool    initialized;
    bool    connected;
    int     cached_secrets;
    time_t  last_fetch;
    int     fetch_count;
    int     cache_hits;
    int     cache_misses;
} vault_status_t;

/* ============================================================================
 * Core API
 * ============================================================================ */

/**
 * @brief Initialize Vault client
 * 
 * @param config Pointer to configuration
 * @return VAULT_ERR_SUCCESS on success
 */
int vault_init(const vault_config_t *config);

/**
 * @brief Cleanup Vault client and free resources
 */
void vault_cleanup(void);

/**
 * @brief Check if Vault client is initialized
 * 
 * @return true if initialized
 */
bool vault_is_initialized(void);

/**
 * @brief Get secret value from Vault
 * 
 * Checks cache first, fetches from Vault if not cached.
 * 
 * @param key Secret key name
 * @param value Buffer to store secret value
 * @param value_size Size of value buffer
 * @return VAULT_ERR_SUCCESS on success
 */
int vault_get_secret(const char *key, char *value, size_t value_size);

/**
 * @brief Force refresh a secret from Vault (bypass cache)
 * 
 * @param key Secret key name
 * @param value Buffer to store secret value
 * @param value_size Size of value buffer
 * @return VAULT_ERR_SUCCESS on success
 */
int vault_refresh_secret(const char *key, char *value, size_t value_size);

/**
 * @brief Invalidate cached secret
 * 
 * @param key Secret key name (NULL = invalidate all)
 */
void vault_invalidate_cache(const char *key);

/**
 * @brief Get Vault client status
 * 
 * @param status Pointer to status structure
 */
void vault_get_status(vault_status_t *status);

/* ============================================================================
 * Health & Monitoring
 * ============================================================================ */

/**
 * @brief Check Vault server health
 * 
 * @return VAULT_ERR_SUCCESS if healthy
 */
int vault_health_check(void);

/**
 * @brief Renew authentication token
 * 
 * @return VAULT_ERR_SUCCESS on success
 */
int vault_renew_token(void);

/* ============================================================================
 * Fallback
 * ============================================================================ */

/**
 * @brief Load secrets from fallback file
 * 
 * Used when Vault is unavailable.
 * 
 * @return VAULT_ERR_SUCCESS on success
 */
int vault_load_fallback(void);

/**
 * @brief Save current cached secrets to fallback file
 * 
 * @return VAULT_ERR_SUCCESS on success
 */
int vault_save_fallback(void);

/* ============================================================================
 * Utility
 * ============================================================================ */

/**
 * @brief Get error message for Vault error code
 * 
 * @param error_code Error code
 * @return Human-readable message
 */
const char* vault_strerror(int error_code);

#ifdef __cplusplus
}
#endif

#endif /* VAULT_CLIENT_H */
