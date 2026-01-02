/*
 * SENTINEL Shield - Mutual TLS Protocol (STLS)
 * 
 * Mutual TLS authentication for secure communication
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_common.h"
#include "shield_protocol.h"

#ifdef SHIELD_USE_OPENSSL
#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/x509.h>
#endif

/* STLS Config */
typedef struct {
    char        cert_path[256];
    char        key_path[256];
    char        ca_path[256];
    bool        verify_peer;
    bool        verify_hostname;
    char        allowed_cn[256];
    int         min_version;  /* TLS 1.2 = 0x0303 */
} stls_config_t;

/* STLS Context */
typedef struct {
    stls_config_t   config;
#ifdef SHIELD_USE_OPENSSL
    SSL_CTX        *ssl_ctx;
#endif
    bool            initialized;
} stls_context_t;

/* Initialize STLS */
shield_err_t stls_init(stls_context_t *ctx, const stls_config_t *config)
{
    if (!ctx || !config) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(ctx, 0, sizeof(*ctx));
    ctx->config = *config;
    
#ifdef SHIELD_USE_OPENSSL
    SSL_library_init();
    OpenSSL_add_all_algorithms();
    SSL_load_error_strings();
    
    const SSL_METHOD *method = TLS_method();
    ctx->ssl_ctx = SSL_CTX_new(method);
    if (!ctx->ssl_ctx) {
        LOG_ERROR("STLS: Failed to create SSL context");
        return SHIELD_ERR_TLS;
    }
    
    /* Set minimum version */
    SSL_CTX_set_min_proto_version(ctx->ssl_ctx, TLS1_2_VERSION);
    
    /* Load certificate */
    if (SSL_CTX_use_certificate_file(ctx->ssl_ctx, config->cert_path, 
                                      SSL_FILETYPE_PEM) <= 0) {
        LOG_ERROR("STLS: Failed to load certificate");
        return SHIELD_ERR_TLS;
    }
    
    /* Load private key */
    if (SSL_CTX_use_PrivateKey_file(ctx->ssl_ctx, config->key_path,
                                     SSL_FILETYPE_PEM) <= 0) {
        LOG_ERROR("STLS: Failed to load private key");
        return SHIELD_ERR_TLS;
    }
    
    /* Verify key matches cert */
    if (!SSL_CTX_check_private_key(ctx->ssl_ctx)) {
        LOG_ERROR("STLS: Key does not match certificate");
        return SHIELD_ERR_TLS;
    }
    
    /* Load CA */
    if (config->ca_path[0]) {
        if (SSL_CTX_load_verify_locations(ctx->ssl_ctx, config->ca_path, NULL) <= 0) {
            LOG_ERROR("STLS: Failed to load CA");
            return SHIELD_ERR_TLS;
        }
    }
    
    /* Verify peer */
    if (config->verify_peer) {
        SSL_CTX_set_verify(ctx->ssl_ctx, 
                           SSL_VERIFY_PEER | SSL_VERIFY_FAIL_IF_NO_PEER_CERT,
                           NULL);
    }
    
    ctx->initialized = true;
    LOG_INFO("STLS: Initialized with cert %s", config->cert_path);
#else
    LOG_WARN("STLS: OpenSSL not available, TLS disabled");
#endif
    
    return SHIELD_OK;
}

/* Wrap socket with TLS */
shield_err_t stls_wrap_socket(stls_context_t *ctx, int socket, void **ssl_out)
{
#ifdef SHIELD_USE_OPENSSL
    if (!ctx || !ctx->initialized || socket < 0) {
        return SHIELD_ERR_INVALID;
    }
    
    SSL *ssl = SSL_new(ctx->ssl_ctx);
    if (!ssl) {
        return SHIELD_ERR_TLS;
    }
    
    SSL_set_fd(ssl, socket);
    
    if (SSL_accept(ssl) <= 0) {
        SSL_free(ssl);
        return SHIELD_ERR_TLS;
    }
    
    /* Verify peer certificate */
    if (ctx->config.verify_peer) {
        X509 *peer_cert = SSL_get_peer_certificate(ssl);
        if (!peer_cert) {
            SSL_free(ssl);
            return SHIELD_ERR_TLS;
        }
        
        /* Verify CN if specified */
        if (ctx->config.allowed_cn[0]) {
            char cn[256];
            X509_NAME *subject = X509_get_subject_name(peer_cert);
            X509_NAME_get_text_by_NID(subject, NID_commonName, cn, sizeof(cn));
            
            if (strcmp(cn, ctx->config.allowed_cn) != 0) {
                LOG_WARN("STLS: CN mismatch: %s != %s", cn, ctx->config.allowed_cn);
                X509_free(peer_cert);
                SSL_free(ssl);
                return SHIELD_ERR_TLS;
            }
        }
        
        X509_free(peer_cert);
    }
    
    *ssl_out = ssl;
    return SHIELD_OK;
#else
    (void)ctx; (void)socket; (void)ssl_out;
    return SHIELD_ERR_NOT_SUPPORTED;
#endif
}

/* TLS read */
ssize_t stls_read(void *ssl, void *buf, size_t len)
{
#ifdef SHIELD_USE_OPENSSL
    return SSL_read((SSL*)ssl, buf, len);
#else
    (void)ssl; (void)buf; (void)len;
    return -1;
#endif
}

/* TLS write */
ssize_t stls_write(void *ssl, const void *buf, size_t len)
{
#ifdef SHIELD_USE_OPENSSL
    return SSL_write((SSL*)ssl, buf, len);
#else
    (void)ssl; (void)buf; (void)len;
    return -1;
#endif
}

/* Destroy STLS */
void stls_destroy(stls_context_t *ctx)
{
#ifdef SHIELD_USE_OPENSSL
    if (ctx && ctx->ssl_ctx) {
        SSL_CTX_free(ctx->ssl_ctx);
    }
#else
    (void)ctx;
#endif
}
