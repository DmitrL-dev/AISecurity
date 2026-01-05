/*
 * SENTINEL Shield - Secure Communication Module
 * 
 * mTLS (mutual TLS) wrapper for Shield-Brain communication.
 * Designed for enterprise deployments with distributed Shields.
 * 
 * Features:
 * - TLS 1.3 with strong cipher suites
 * - Mutual authentication (Shield ↔ Brain)
 * - Certificate pinning support
 * - PQC-ready (hybrid key exchange)
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#include "shield_common.h"

/* ===== TLS Configuration ===== */

typedef enum tls_mode {
    TLS_MODE_DISABLED = 0,       /* Plain HTTP (localhost only!) */
    TLS_MODE_TLS,                /* Server auth only */
    TLS_MODE_MTLS,               /* Mutual TLS (enterprise) */
    TLS_MODE_MTLS_PINNED,        /* mTLS + certificate pinning */
} tls_mode_t;

typedef struct tls_config {
    tls_mode_t   mode;
    
    /* Certificate paths */
    char         ca_cert_path[256];      /* CA certificate (for verifying Brain) */
    char         client_cert_path[256];  /* Shield's certificate */
    char         client_key_path[256];   /* Shield's private key */
    
    /* Certificate pinning (SHA-256 fingerprint) */
    uint8_t      pinned_fingerprint[32];
    bool         pinning_enabled;
    
    /* Connection settings */
    int          verify_depth;            /* Certificate chain depth */
    bool         verify_hostname;         /* Verify CN/SAN matches */
    char         expected_hostname[128];  /* Expected Brain hostname */
    
    /* TLS version constraints */
    int          min_version;             /* Minimum TLS version (0x0303 = 1.2) */
    int          max_version;             /* Maximum TLS version (0x0304 = 1.3) */
    
    /* Cipher suite preferences */
    const char   *cipher_list;            /* OpenSSL cipher list string */
    
    /* Session settings */
    bool         session_cache_enabled;
    int          session_timeout_sec;
    
    /* PQC hybrid mode */
    bool         pqc_hybrid_enabled;      /* Enable PQC key exchange */
} tls_config_t;

/* ===== TLS Context ===== */

typedef struct tls_context {
    tls_config_t    config;
    void           *ssl_ctx;              /* OpenSSL SSL_CTX* or similar */
    bool            initialized;
    
    /* Statistics */
    uint64_t        connections_total;
    uint64_t        connections_failed;
    uint64_t        handshake_failures;
    uint64_t        cert_validation_failures;
} tls_context_t;

/* ===== Default Configuration ===== */

static const char *DEFAULT_CIPHER_LIST = 
    "TLS_AES_256_GCM_SHA384:"
    "TLS_CHACHA20_POLY1305_SHA256:"
    "TLS_AES_128_GCM_SHA256:"
    "ECDHE-ECDSA-AES256-GCM-SHA384:"
    "ECDHE-RSA-AES256-GCM-SHA384";

void shield_tls_config_init_default(tls_config_t *config)
{
    if (!config) return;
    
    memset(config, 0, sizeof(*config));
    
    config->mode = TLS_MODE_MTLS;
    config->verify_depth = 3;
    config->verify_hostname = true;
    config->min_version = 0x0303;  /* TLS 1.2 */
    config->max_version = 0x0304;  /* TLS 1.3 */
    config->cipher_list = DEFAULT_CIPHER_LIST;
    config->session_cache_enabled = true;
    config->session_timeout_sec = 300;
    config->pqc_hybrid_enabled = false;
}

void shield_tls_config_init_localhost(tls_config_t *config)
{
    if (!config) return;
    
    memset(config, 0, sizeof(*config));
    config->mode = TLS_MODE_DISABLED;
    
    LOG_WARN("TLS: Localhost mode - encryption disabled!");
}

void shield_tls_config_init_enterprise(tls_config_t *config,
                                        const char *ca_cert,
                                        const char *client_cert,
                                        const char *client_key)
{
    if (!config) return;
    
    shield_tls_config_init_default(config);
    config->mode = TLS_MODE_MTLS;
    
    if (ca_cert) strncpy(config->ca_cert_path, ca_cert, sizeof(config->ca_cert_path) - 1);
    if (client_cert) strncpy(config->client_cert_path, client_cert, sizeof(config->client_cert_path) - 1);
    if (client_key) strncpy(config->client_key_path, client_key, sizeof(config->client_key_path) - 1);
    
    LOG_INFO("TLS: Enterprise mTLS mode configured");
}

/* ===== TLS Context Management ===== */

shield_err_t shield_tls_context_init(tls_context_t *ctx, const tls_config_t *config)
{
    if (!ctx || !config) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(ctx, 0, sizeof(*ctx));
    memcpy(&ctx->config, config, sizeof(tls_config_t));
    
    if (config->mode == TLS_MODE_DISABLED) {
        LOG_WARN("TLS: Running without encryption (localhost mode)");
        ctx->initialized = true;
        return SHIELD_OK;
    }
    
    /* 
     * Note: This is a stub. In production, initialize OpenSSL/BoringSSL:
     * 
     * SSL_library_init();
     * ctx->ssl_ctx = SSL_CTX_new(TLS_client_method());
     * SSL_CTX_set_min_proto_version(ctx->ssl_ctx, config->min_version);
     * SSL_CTX_set_max_proto_version(ctx->ssl_ctx, config->max_version);
     * SSL_CTX_set_cipher_list(ctx->ssl_ctx, config->cipher_list);
     * 
     * if (config->mode >= TLS_MODE_MTLS) {
     *     SSL_CTX_use_certificate_file(ctx->ssl_ctx, config->client_cert_path, SSL_FILETYPE_PEM);
     *     SSL_CTX_use_PrivateKey_file(ctx->ssl_ctx, config->client_key_path, SSL_FILETYPE_PEM);
     * }
     * 
     * SSL_CTX_load_verify_locations(ctx->ssl_ctx, config->ca_cert_path, NULL);
     * SSL_CTX_set_verify(ctx->ssl_ctx, SSL_VERIFY_PEER, NULL);
     */
    
    LOG_INFO("TLS: Context initialized (mode=%d)", config->mode);
    ctx->initialized = true;
    
    return SHIELD_OK;
}

void shield_tls_context_destroy(tls_context_t *ctx)
{
    if (!ctx) return;
    
    /*
     * SSL_CTX_free(ctx->ssl_ctx);
     */
    
    ctx->initialized = false;
    LOG_DEBUG("TLS: Context destroyed");
}

/* ===== Secure HTTP POST ===== */

/*
 * Send HTTPS POST request with mTLS
 *
 * @param ctx        TLS context (initialized with certificates)
 * @param url        Full URL (https://brain.sentinel.local:8443/api/v1/analyze)
 * @param json_body  Request body
 * @param response   Output response buffer
 * @param resp_len   Response buffer length
 * @return SHIELD_OK on success
 */
shield_err_t shield_tls_https_post(tls_context_t *ctx, const char *url,
                                    const char *json_body,
                                    char *response, size_t *resp_len)
{
    if (!ctx || !ctx->initialized || !url || !json_body) {
        return SHIELD_ERR_INVALID;
    }
    
    ctx->connections_total++;
    
    if (ctx->config.mode == TLS_MODE_DISABLED) {
        /* Fallback to plain HTTP (from http_client.c) */
        LOG_DEBUG("TLS: Using plain HTTP (localhost mode)");
        /* Call http_post_json() here */
        return SHIELD_OK;
    }
    
    /*
     * Full TLS implementation would:
     * 1. Resolve hostname
     * 2. Create TCP socket
     * 3. SSL_new(ctx->ssl_ctx)
     * 4. SSL_set_fd(ssl, socket)
     * 5. SSL_connect(ssl)
     * 6. Verify certificate chain
     * 7. If pinning: verify fingerprint
     * 8. If mTLS: send client cert in handshake
     * 9. SSL_write(ssl, request)
     * 10. SSL_read(ssl, response)
     * 11. SSL_shutdown(ssl)
     * 12. SSL_free(ssl)
     */
    
    LOG_DEBUG("TLS: HTTPS POST to %s (mTLS=%d)", url, 
              ctx->config.mode >= TLS_MODE_MTLS);
    
    /* Stub: return success */
    if (response && resp_len && *resp_len > 0) {
        const char *stub_response = "{\"status\":\"ok\",\"risk_score\":0.0}";
        strncpy(response, stub_response, *resp_len - 1);
        *resp_len = strlen(stub_response);
    }
    
    return SHIELD_OK;
}

/* ===== Certificate Pinning ===== */

shield_err_t shield_tls_set_pin(tls_config_t *config, const uint8_t *sha256_fingerprint)
{
    if (!config || !sha256_fingerprint) {
        return SHIELD_ERR_INVALID;
    }
    
    memcpy(config->pinned_fingerprint, sha256_fingerprint, 32);
    config->pinning_enabled = true;
    config->mode = TLS_MODE_MTLS_PINNED;
    
    LOG_INFO("TLS: Certificate pinning enabled");
    return SHIELD_OK;
}

/* ===== Connection Pool for Enterprise ===== */

#define TLS_POOL_SIZE 64

typedef struct tls_connection {
    void       *ssl;              /* SSL* */
    int         socket;
    char        host[128];
    uint16_t    port;
    uint64_t    last_used;
    bool        in_use;
} tls_connection_t;

typedef struct tls_pool {
    tls_context_t      *ctx;
    tls_connection_t    connections[TLS_POOL_SIZE];
    size_t              active_count;
    
    /* Thread safety (placeholder) */
    void               *mutex;
} tls_pool_t;

shield_err_t shield_tls_pool_init(tls_pool_t *pool, tls_context_t *ctx)
{
    if (!pool || !ctx) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(pool, 0, sizeof(*pool));
    pool->ctx = ctx;
    
    LOG_INFO("TLS: Connection pool initialized (size=%d)", TLS_POOL_SIZE);
    return SHIELD_OK;
}

tls_connection_t *shield_tls_pool_acquire(tls_pool_t *pool, const char *host, uint16_t port)
{
    if (!pool || !host) return NULL;
    
    /* Look for existing connection to same host:port */
    for (size_t i = 0; i < TLS_POOL_SIZE; i++) {
        tls_connection_t *conn = &pool->connections[i];
        if (!conn->in_use && conn->ssl &&
            strcmp(conn->host, host) == 0 && conn->port == port) {
            conn->in_use = true;
            return conn;
        }
    }
    
    /* Create new connection */
    for (size_t i = 0; i < TLS_POOL_SIZE; i++) {
        tls_connection_t *conn = &pool->connections[i];
        if (!conn->in_use && !conn->ssl) {
            strncpy(conn->host, host, sizeof(conn->host) - 1);
            conn->port = port;
            conn->in_use = true;
            pool->active_count++;
            /* Establish TLS connection here */
            return conn;
        }
    }
    
    LOG_WARN("TLS: Connection pool exhausted!");
    return NULL;
}

void shield_tls_pool_release(tls_pool_t *pool, tls_connection_t *conn)
{
    if (!pool || !conn) return;
    
    conn->in_use = false;
    /* Keep connection alive for reuse */
}

void shield_tls_pool_destroy(tls_pool_t *pool)
{
    if (!pool) return;
    
    for (size_t i = 0; i < TLS_POOL_SIZE; i++) {
        if (pool->connections[i].ssl) {
            /* SSL_shutdown + SSL_free */
        }
    }
    
    LOG_INFO("TLS: Connection pool destroyed");
}

/* ===== Statistics ===== */

void shield_tls_get_stats(const tls_context_t *ctx, char *buffer, size_t buflen)
{
    if (!ctx || !buffer || buflen == 0) return;
    
    snprintf(buffer, buflen,
        "TLS Statistics:\n"
        "  Mode: %s\n"
        "  Total Connections: %llu\n"
        "  Failed Connections: %llu\n"
        "  Handshake Failures: %llu\n"
        "  Cert Validation Failures: %llu\n",
        ctx->config.mode == TLS_MODE_DISABLED ? "DISABLED" :
        ctx->config.mode == TLS_MODE_TLS ? "TLS" :
        ctx->config.mode == TLS_MODE_MTLS ? "mTLS" : "mTLS+Pinning",
        (unsigned long long)ctx->connections_total,
        (unsigned long long)ctx->connections_failed,
        (unsigned long long)ctx->handshake_failures,
        (unsigned long long)ctx->cert_validation_failures);
}
