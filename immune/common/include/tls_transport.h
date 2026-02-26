/*
 * SENTINEL IMMUNE — TLS Transport Layer
 * 
 * Secure mTLS communication between Agent and Hive.
 * Based on wolfSSL for minimal footprint and high performance.
 * 
 * Features:
 * - TLS 1.3 support
 * - Mutual TLS (client + server auth)
 * - Certificate pinning
 * - Session resumption
 */

#ifndef IMMUNE_TLS_TRANSPORT_H
#define IMMUNE_TLS_TRANSPORT_H

#include <stdint.h>
#include <stdbool.h>

/* Configuration defaults */
#define TLS_DEFAULT_PORT        8443
#define TLS_HANDSHAKE_TIMEOUT   30      /* seconds */
#define TLS_READ_TIMEOUT        60      /* seconds */
#define TLS_CERT_PATH_MAX       256
#define TLS_PIN_HASH_SIZE       32      /* SHA-256 */

/* TLS connection state */
typedef enum {
    TLS_STATE_DISCONNECTED = 0,
    TLS_STATE_CONNECTING,
    TLS_STATE_HANDSHAKE,
    TLS_STATE_CONNECTED,
    TLS_STATE_ERROR
} tls_state_t;

/* TLS error codes */
typedef enum {
    TLS_OK = 0,
    TLS_ERR_INIT = -1,
    TLS_ERR_CERT = -2,
    TLS_ERR_KEY = -3,
    TLS_ERR_CONNECT = -4,
    TLS_ERR_HANDSHAKE = -5,
    TLS_ERR_VERIFY = -6,
    TLS_ERR_PIN_MISMATCH = -7,
    TLS_ERR_SEND = -8,
    TLS_ERR_RECV = -9,
    TLS_ERR_TIMEOUT = -10,
    TLS_ERR_MEMORY = -11
} tls_error_t;

/* TLS configuration */
typedef struct {
    /* Paths to certificate files */
    char ca_cert_path[TLS_CERT_PATH_MAX];     /* CA certificate (verify peer) */
    char client_cert_path[TLS_CERT_PATH_MAX]; /* Client certificate (mTLS) */
    char client_key_path[TLS_CERT_PATH_MAX];  /* Client private key */
    
    /* Certificate pinning */
    bool     pin_enabled;
    uint8_t  pinned_hash[TLS_PIN_HASH_SIZE];  /* SHA-256 of expected cert */
    
    /* Timeouts */
    int handshake_timeout;
    int read_timeout;
    
    /* Options */
    bool verify_peer;           /* Verify server certificate */
    bool mtls_enabled;          /* Mutual TLS (client auth) */
    bool session_resumption;    /* Enable TLS session tickets */
} tls_config_t;

/* TLS channel (opaque handle) */
typedef struct tls_channel tls_channel_t;

/* === Initialization === */

/**
 * Initialize TLS subsystem.
 * Must be called once before any TLS operations.
 * @return TLS_OK on success, error code otherwise
 */
int tls_init(void);

/**
 * Clean up TLS subsystem.
 * Call before application exit.
 */
void tls_cleanup(void);

/* === Configuration === */

/**
 * Create default TLS configuration.
 * @param config Output configuration struct
 */
void tls_config_init(tls_config_t *config);

/**
 * Set certificate pinning hash.
 * @param config Configuration to update
 * @param hash SHA-256 hash of expected server certificate (32 bytes)
 */
void tls_config_set_pin(tls_config_t *config, const uint8_t *hash);

/* === Channel Management === */

/**
 * Create TLS channel (client mode).
 * @param config TLS configuration
 * @return Channel handle or NULL on error
 */
tls_channel_t* tls_channel_create(const tls_config_t *config);

/**
 * Connect to TLS server.
 * @param channel TLS channel
 * @param host Server hostname or IP
 * @param port Server port
 * @return TLS_OK on success, error code otherwise
 */
int tls_channel_connect(tls_channel_t *channel, const char *host, uint16_t port);

/**
 * Close TLS channel.
 * @param channel TLS channel to close
 */
void tls_channel_close(tls_channel_t *channel);

/**
 * Destroy TLS channel and free resources.
 * @param channel TLS channel to destroy
 */
void tls_channel_destroy(tls_channel_t *channel);

/* === Data Transfer === */

/**
 * Send data over TLS channel.
 * @param channel Connected TLS channel
 * @param data Data buffer to send
 * @param len Length of data
 * @return Bytes sent or negative error code
 */
int tls_send(tls_channel_t *channel, const void *data, size_t len);

/**
 * Receive data from TLS channel.
 * @param channel Connected TLS channel
 * @param buffer Buffer to receive data
 * @param max_len Maximum bytes to receive
 * @return Bytes received or negative error code
 */
int tls_recv(tls_channel_t *channel, void *buffer, size_t max_len);

/* === Status === */

/**
 * Get current channel state.
 * @param channel TLS channel
 * @return Current state
 */
tls_state_t tls_get_state(const tls_channel_t *channel);

/**
 * Get last error code.
 * @param channel TLS channel
 * @return Last error code
 */
tls_error_t tls_get_error(const tls_channel_t *channel);

/**
 * Get human-readable error string.
 * @param error Error code
 * @return Error description
 */
const char* tls_error_string(tls_error_t error);

/* === Server Functions (Hive) === */

/**
 * Create TLS server context.
 * @param config Server TLS configuration
 * @return Server context or NULL on error
 */
void* tls_server_create(const tls_config_t *config);

/**
 * Accept TLS client connection.
 * @param server_ctx TLS server context
 * @param client_fd Accepted TCP socket
 * @return TLS channel for client or NULL on error
 */
tls_channel_t* tls_server_accept(void *server_ctx, int client_fd);

/**
 * Destroy TLS server context.
 * @param server_ctx Server context to destroy
 */
void tls_server_destroy(void *server_ctx);

#endif /* IMMUNE_TLS_TRANSPORT_H */
