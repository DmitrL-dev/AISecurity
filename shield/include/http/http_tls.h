/**
 * @file http_tls.h
 * @brief TLS/mTLS Support for HTTP Server
 * 
 * Provides secure communication with:
 * - Server TLS (HTTPS)
 * - Mutual TLS (client certificate verification)
 * - Certificate and key management
 * 
 * @author SENTINEL Team
 * @date January 2026
 */

#ifndef SHIELD_HTTP_TLS_H
#define SHIELD_HTTP_TLS_H

#include <stdbool.h>
#include <stddef.h>
#include "shield_common.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ============================================================================
 * TLS Configuration
 * ============================================================================ */

/**
 * @brief TLS mode
 */
typedef enum http_tls_mode {
    HTTP_TLS_DISABLED = 0,  /**< No TLS (plain HTTP) */
    HTTP_TLS_ENABLED,       /**< TLS enabled (HTTPS) */
    HTTP_TLS_MTLS,          /**< Mutual TLS (client cert required) */
} http_tls_mode_t;

/**
 * @brief TLS configuration
 */
typedef struct http_tls_config {
    http_tls_mode_t mode;
    
    /* Server certificate and key */
    char cert_file[256];        /**< Path to server certificate (PEM) */
    char key_file[256];         /**< Path to server private key (PEM) */
    char key_password[128];     /**< Private key password (optional) */
    
    /* CA for client verification (mTLS) */
    char ca_file[256];          /**< Path to CA certificate for client verification */
    char ca_dir[256];           /**< Directory of CA certificates */
    
    /* Options */
    bool verify_peer;           /**< Verify client certificate */
    bool verify_hostname;       /**< Verify client hostname */
    int  min_protocol_version;  /**< Minimum TLS version (12 = TLS 1.2, 13 = TLS 1.3) */
    
    /* Cipher configuration */
    char cipher_list[512];      /**< OpenSSL cipher list */
    char cipher_suites[512];    /**< TLS 1.3 cipher suites */
} http_tls_config_t;

/**
 * @brief TLS connection info
 */
typedef struct http_tls_info {
    bool   is_secure;           /**< Connection is TLS */
    int    protocol_version;    /**< TLS version (12, 13) */
    char   cipher[128];         /**< Negotiated cipher */
    char   client_cn[256];      /**< Client certificate CN (if mTLS) */
    bool   client_verified;     /**< Client certificate verified */
} http_tls_info_t;

/* ============================================================================
 * TLS Context
 * ============================================================================ */

/**
 * @brief Opaque TLS context
 */
typedef struct http_tls_ctx http_tls_ctx_t;

/**
 * @brief Initialize TLS context
 * 
 * @param config TLS configuration
 * @return TLS context or NULL on failure
 */
http_tls_ctx_t *http_tls_init(const http_tls_config_t *config);

/**
 * @brief Destroy TLS context
 */
void http_tls_destroy(http_tls_ctx_t *ctx);

/**
 * @brief Accept TLS connection
 * 
 * @param ctx TLS context
 * @param client_fd Client socket
 * @param info Output connection info
 * @return SHIELD_OK on success
 */
shield_err_t http_tls_accept(http_tls_ctx_t *ctx, int client_fd, 
                              http_tls_info_t *info);

/**
 * @brief Read from TLS connection
 */
ssize_t http_tls_read(http_tls_ctx_t *ctx, int client_fd, 
                       void *buf, size_t len);

/**
 * @brief Write to TLS connection
 */
ssize_t http_tls_write(http_tls_ctx_t *ctx, int client_fd,
                        const void *buf, size_t len);

/**
 * @brief Close TLS connection
 */
void http_tls_close(http_tls_ctx_t *ctx, int client_fd);

/* ============================================================================
 * Utility Functions
 * ============================================================================ */

/**
 * @brief Generate self-signed certificate for testing
 * 
 * @param cert_out Path to write certificate
 * @param key_out Path to write private key
 * @param cn Common Name
 * @param days Validity in days
 * @return SHIELD_OK on success
 */
shield_err_t http_tls_generate_self_signed(const char *cert_out,
                                            const char *key_out,
                                            const char *cn,
                                            int days);

/**
 * @brief Get default TLS config
 */
http_tls_config_t http_tls_default_config(void);

/**
 * @brief Get mTLS config
 */
http_tls_config_t http_tls_mtls_config(const char *cert, 
                                        const char *key,
                                        const char *ca);

#ifdef __cplusplus
}
#endif

#endif /* SHIELD_HTTP_TLS_H */
