/*
 * SENTINEL Shield - TLS/SSL Support
 */

#ifndef SHIELD_TLS_H
#define SHIELD_TLS_H

#include "shield_common.h"

/* TLS version */
typedef enum tls_version {
    TLS_VERSION_1_2 = 0,
    TLS_VERSION_1_3 = 1,
} tls_version_t;

/* TLS context */
typedef struct tls_context {
    void            *ssl_ctx;       /* SSL_CTX* */
    char            cert_file[256];
    char            key_file[256];
    char            ca_file[256];
    tls_version_t   min_version;
    bool            verify_peer;
    bool            initialized;
} tls_context_t;

/* TLS connection */
typedef struct tls_connection {
    void            *ssl;           /* SSL* */
    int             socket;
    bool            connected;
    bool            is_server;
} tls_connection_t;

/* API */
shield_err_t tls_init(void);
void tls_cleanup(void);

/* Context */
shield_err_t tls_context_create(tls_context_t *ctx, bool is_server);
void tls_context_destroy(tls_context_t *ctx);
shield_err_t tls_context_set_cert(tls_context_t *ctx, const char *cert, const char *key);
shield_err_t tls_context_set_ca(tls_context_t *ctx, const char *ca_file);
void tls_context_set_verify(tls_context_t *ctx, bool verify);

/* Connection */
shield_err_t tls_connect(tls_context_t *ctx, int socket, tls_connection_t *conn);
shield_err_t tls_accept(tls_context_t *ctx, int socket, tls_connection_t *conn);
void tls_close(tls_connection_t *conn);

/* I/O */
ssize_t tls_read(tls_connection_t *conn, void *buf, size_t len);
ssize_t tls_write(tls_connection_t *conn, const void *buf, size_t len);

/* Info */
const char *tls_get_cipher(tls_connection_t *conn);
const char *tls_get_version(tls_connection_t *conn);
bool tls_is_verified(tls_connection_t *conn);

#endif /* SHIELD_TLS_H */
