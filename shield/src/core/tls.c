/*
 * SENTINEL Shield - TLS/SSL Implementation (Stub)
 * 
 * Uses OpenSSL when available, otherwise stub
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_common.h"
#include "shield_tls.h"
#include "shield_platform.h"

/* Check for OpenSSL */
#ifdef SHIELD_USE_OPENSSL
#include <openssl/ssl.h>
#include <openssl/err.h>
#define TLS_AVAILABLE 1
#else
#define TLS_AVAILABLE 0
#endif

static bool g_tls_initialized = false;

/* Initialize TLS subsystem */
shield_err_t tls_init(void)
{
    if (g_tls_initialized) {
        return SHIELD_OK;
    }
    
#if TLS_AVAILABLE
    SSL_library_init();
    SSL_load_error_strings();
    OpenSSL_add_all_algorithms();
#endif
    
    g_tls_initialized = true;
    LOG_INFO("TLS: Initialized %s", TLS_AVAILABLE ? "(OpenSSL)" : "(stub)");
    
    return SHIELD_OK;
}

/* Cleanup */
void tls_cleanup(void)
{
#if TLS_AVAILABLE
    EVP_cleanup();
    ERR_free_strings();
#endif
    g_tls_initialized = false;
}

/* Create context */
shield_err_t tls_context_create(tls_context_t *ctx, bool is_server)
{
    if (!ctx) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(ctx, 0, sizeof(*ctx));
    ctx->min_version = TLS_VERSION_1_2;
    ctx->verify_peer = true;
    
#if TLS_AVAILABLE
    const SSL_METHOD *method;
    if (is_server) {
        method = TLS_server_method();
    } else {
        method = TLS_client_method();
    }
    
    ctx->ssl_ctx = SSL_CTX_new(method);
    if (!ctx->ssl_ctx) {
        return SHIELD_ERR_IO;
    }
    
    SSL_CTX_set_min_proto_version(ctx->ssl_ctx, TLS1_2_VERSION);
    ctx->initialized = true;
#else
    LOG_WARN("TLS: Not available (compile with SHIELD_USE_OPENSSL)");
    return SHIELD_ERR_UNSUPPORTED;
#endif
    
    return SHIELD_OK;
}

/* Destroy context */
void tls_context_destroy(tls_context_t *ctx)
{
    if (!ctx) return;
    
#if TLS_AVAILABLE
    if (ctx->ssl_ctx) {
        SSL_CTX_free(ctx->ssl_ctx);
        ctx->ssl_ctx = NULL;
    }
#endif
    
    ctx->initialized = false;
}

/* Set certificate */
shield_err_t tls_context_set_cert(tls_context_t *ctx, const char *cert, const char *key)
{
    if (!ctx || !cert || !key) {
        return SHIELD_ERR_INVALID;
    }
    
    strncpy(ctx->cert_file, cert, sizeof(ctx->cert_file) - 1);
    strncpy(ctx->key_file, key, sizeof(ctx->key_file) - 1);
    
#if TLS_AVAILABLE
    if (!ctx->ssl_ctx) return SHIELD_ERR_INVALID;
    
    if (SSL_CTX_use_certificate_file(ctx->ssl_ctx, cert, SSL_FILETYPE_PEM) <= 0) {
        return SHIELD_ERR_IO;
    }
    
    if (SSL_CTX_use_PrivateKey_file(ctx->ssl_ctx, key, SSL_FILETYPE_PEM) <= 0) {
        return SHIELD_ERR_IO;
    }
    
    if (!SSL_CTX_check_private_key(ctx->ssl_ctx)) {
        return SHIELD_ERR_INVALID;
    }
#endif
    
    return SHIELD_OK;
}

/* Set CA */
shield_err_t tls_context_set_ca(tls_context_t *ctx, const char *ca_file)
{
    if (!ctx || !ca_file) {
        return SHIELD_ERR_INVALID;
    }
    
    strncpy(ctx->ca_file, ca_file, sizeof(ctx->ca_file) - 1);
    
#if TLS_AVAILABLE
    if (!ctx->ssl_ctx) return SHIELD_ERR_INVALID;
    
    if (!SSL_CTX_load_verify_locations(ctx->ssl_ctx, ca_file, NULL)) {
        return SHIELD_ERR_IO;
    }
#endif
    
    return SHIELD_OK;
}

/* Set verify */
void tls_context_set_verify(tls_context_t *ctx, bool verify)
{
    if (!ctx) return;
    
    ctx->verify_peer = verify;
    
#if TLS_AVAILABLE
    if (ctx->ssl_ctx) {
        int mode = verify ? SSL_VERIFY_PEER : SSL_VERIFY_NONE;
        SSL_CTX_set_verify(ctx->ssl_ctx, mode, NULL);
    }
#endif
}

/* Connect (client) */
shield_err_t tls_connect(tls_context_t *ctx, int socket, tls_connection_t *conn)
{
    if (!ctx || !conn || socket < 0) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(conn, 0, sizeof(*conn));
    conn->socket = socket;
    conn->is_server = false;
    
#if TLS_AVAILABLE
    if (!ctx->ssl_ctx) return SHIELD_ERR_INVALID;
    
    conn->ssl = SSL_new(ctx->ssl_ctx);
    if (!conn->ssl) {
        return SHIELD_ERR_NOMEM;
    }
    
    SSL_set_fd(conn->ssl, socket);
    
    if (SSL_connect(conn->ssl) <= 0) {
        SSL_free(conn->ssl);
        conn->ssl = NULL;
        return SHIELD_ERR_IO;
    }
    
    conn->connected = true;
#else
    return SHIELD_ERR_UNSUPPORTED;
#endif
    
    return SHIELD_OK;
}

/* Accept (server) */
shield_err_t tls_accept(tls_context_t *ctx, int socket, tls_connection_t *conn)
{
    if (!ctx || !conn || socket < 0) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(conn, 0, sizeof(*conn));
    conn->socket = socket;
    conn->is_server = true;
    
#if TLS_AVAILABLE
    if (!ctx->ssl_ctx) return SHIELD_ERR_INVALID;
    
    conn->ssl = SSL_new(ctx->ssl_ctx);
    if (!conn->ssl) {
        return SHIELD_ERR_NOMEM;
    }
    
    SSL_set_fd(conn->ssl, socket);
    
    if (SSL_accept(conn->ssl) <= 0) {
        SSL_free(conn->ssl);
        conn->ssl = NULL;
        return SHIELD_ERR_IO;
    }
    
    conn->connected = true;
#else
    return SHIELD_ERR_UNSUPPORTED;
#endif
    
    return SHIELD_OK;
}

/* Close connection */
void tls_close(tls_connection_t *conn)
{
    if (!conn) return;
    
#if TLS_AVAILABLE
    if (conn->ssl) {
        SSL_shutdown(conn->ssl);
        SSL_free(conn->ssl);
        conn->ssl = NULL;
    }
#endif
    
    conn->connected = false;
}

/* Read */
ssize_t tls_read(tls_connection_t *conn, void *buf, size_t len)
{
    if (!conn || !buf || !conn->connected) {
        return -1;
    }
    
#if TLS_AVAILABLE
    if (!conn->ssl) return -1;
    return SSL_read(conn->ssl, buf, (int)len);
#else
    (void)len;
    return -1;
#endif
}

/* Write */
ssize_t tls_write(tls_connection_t *conn, const void *buf, size_t len)
{
    if (!conn || !buf || !conn->connected) {
        return -1;
    }
    
#if TLS_AVAILABLE
    if (!conn->ssl) return -1;
    return SSL_write(conn->ssl, buf, (int)len);
#else
    (void)len;
    return -1;
#endif
}

/* Get cipher */
const char *tls_get_cipher(tls_connection_t *conn)
{
    if (!conn || !conn->connected) {
        return "none";
    }
    
#if TLS_AVAILABLE
    if (conn->ssl) {
        return SSL_get_cipher(conn->ssl);
    }
#endif
    
    return "unknown";
}

/* Get version */
const char *tls_get_version(tls_connection_t *conn)
{
    if (!conn || !conn->connected) {
        return "none";
    }
    
#if TLS_AVAILABLE
    if (conn->ssl) {
        return SSL_get_version(conn->ssl);
    }
#endif
    
    return "unknown";
}

/* Is verified */
bool tls_is_verified(tls_connection_t *conn)
{
    if (!conn || !conn->connected) {
        return false;
    }
    
#if TLS_AVAILABLE
    if (conn->ssl) {
        return SSL_get_verify_result(conn->ssl) == X509_V_OK;
    }
#endif
    
    return false;
}
