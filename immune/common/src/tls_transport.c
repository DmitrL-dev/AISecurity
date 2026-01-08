/*
 * SENTINEL IMMUNE — TLS Transport Layer Implementation
 * 
 * Secure mTLS communication between Agent and Hive.
 * Uses wolfSSL for TLS 1.3 with certificate pinning.
 * 
 * Build: Requires wolfSSL library
 *   - Install: pkg install wolfssl (FreeBSD/DragonFlyBSD)
 *   - Or build from source with: ./configure --enable-tls13
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <netdb.h>

/* wolfSSL headers */
#ifdef USE_WOLFSSL
#include <wolfssl/options.h>
#include <wolfssl/ssl.h>
#include <wolfssl/wolfcrypt/sha256.h>
#else
/* Stub for compilation without wolfSSL */
typedef void WOLFSSL_CTX;
typedef void WOLFSSL;
#define SSL_SUCCESS 1
#define SSL_FAILURE 0
#endif

#include "tls_transport.h"

/* ==================== Internal Structures ==================== */

struct tls_channel {
    int             fd;             /* Underlying socket */
    tls_state_t     state;          /* Connection state */
    tls_error_t     last_error;     /* Last error code */
    
#ifdef USE_WOLFSSL
    WOLFSSL_CTX    *ctx;            /* wolfSSL context */
    WOLFSSL        *ssl;            /* wolfSSL session */
#endif
    
    /* Configuration (copied) */
    bool            verify_peer;
    bool            pin_enabled;
    uint8_t         pinned_hash[TLS_PIN_HASH_SIZE];
    int             handshake_timeout;
    int             read_timeout;
};

/* Server context */
typedef struct {
#ifdef USE_WOLFSSL
    WOLFSSL_CTX    *ctx;
#endif
    tls_config_t    config;
} tls_server_ctx_t;

/* ==================== Error Handling ==================== */

static const char* error_strings[] = {
    [TLS_OK]              = "Success",
    [-TLS_ERR_INIT]       = "Initialization failed",
    [-TLS_ERR_CERT]       = "Certificate error",
    [-TLS_ERR_KEY]        = "Private key error",
    [-TLS_ERR_CONNECT]    = "Connection failed",
    [-TLS_ERR_HANDSHAKE]  = "TLS handshake failed",
    [-TLS_ERR_VERIFY]     = "Certificate verification failed",
    [-TLS_ERR_PIN_MISMATCH] = "Certificate pin mismatch",
    [-TLS_ERR_SEND]       = "Send failed",
    [-TLS_ERR_RECV]       = "Receive failed",
    [-TLS_ERR_TIMEOUT]    = "Operation timed out",
    [-TLS_ERR_MEMORY]     = "Memory allocation failed"
};

const char*
tls_error_string(tls_error_t error)
{
    int idx = error < 0 ? -error : error;
    if (idx < sizeof(error_strings) / sizeof(error_strings[0])) {
        return error_strings[idx] ? error_strings[idx] : "Unknown error";
    }
    return "Unknown error";
}

/* ==================== Certificate Pinning ==================== */

#ifdef USE_WOLFSSL
/**
 * Calculate SHA-256 hash of certificate for pinning.
 */
static int
calculate_cert_hash(WOLFSSL_X509 *cert, uint8_t *hash_out)
{
    unsigned char der[4096];
    int der_len;
    wc_Sha256 sha256;
    
    /* Get DER encoding */
    der_len = wolfSSL_i2d_X509(cert, NULL);
    if (der_len <= 0 || der_len > sizeof(der)) {
        return -1;
    }
    
    unsigned char *p = der;
    wolfSSL_i2d_X509(cert, &p);
    
    /* Calculate SHA-256 */
    wc_InitSha256(&sha256);
    wc_Sha256Update(&sha256, der, der_len);
    wc_Sha256Final(&sha256, hash_out);
    
    return 0;
}

/**
 * Custom verification callback for certificate pinning.
 */
static int
verify_callback(int preverify, WOLFSSL_X509_STORE_CTX *store)
{
    tls_channel_t *channel;
    WOLFSSL *ssl;
    WOLFSSL_X509 *cert;
    uint8_t cert_hash[TLS_PIN_HASH_SIZE];
    
    if (!preverify) {
        /* Pre-verification failed */
        return 0;
    }
    
    /* Get channel context */
    ssl = wolfSSL_X509_STORE_CTX_get_ex_data(store, 
        wolfSSL_get_ex_data_X509_STORE_CTX_idx());
    if (!ssl) return 0;
    
    channel = (tls_channel_t *)wolfSSL_get_ex_data(ssl, 0);
    if (!channel || !channel->pin_enabled) {
        return preverify;  /* No pinning, trust chain only */
    }
    
    /* Get peer certificate */
    cert = wolfSSL_X509_STORE_CTX_get_current_cert(store);
    if (!cert) return 0;
    
    /* Calculate hash */
    if (calculate_cert_hash(cert, cert_hash) != 0) {
        return 0;
    }
    
    /* Compare with pinned hash */
    if (memcmp(cert_hash, channel->pinned_hash, TLS_PIN_HASH_SIZE) != 0) {
        fprintf(stderr, "[TLS] Certificate pin mismatch!\n");
        channel->last_error = TLS_ERR_PIN_MISMATCH;
        return 0;
    }
    
    return 1;  /* Pin matched */
}
#endif /* USE_WOLFSSL */

/* ==================== Initialization ==================== */

int
tls_init(void)
{
#ifdef USE_WOLFSSL
    if (wolfSSL_Init() != SSL_SUCCESS) {
        return TLS_ERR_INIT;
    }
    
    /* Enable debugging in debug builds */
#ifdef DEBUG
    wolfSSL_Debugging_ON();
#endif
    
    return TLS_OK;
#else
    fprintf(stderr, "[TLS] wolfSSL not compiled in. Using plain TCP.\n");
    return TLS_OK;
#endif
}

void
tls_cleanup(void)
{
#ifdef USE_WOLFSSL
    wolfSSL_Cleanup();
#endif
}

/* ==================== Configuration ==================== */

void
tls_config_init(tls_config_t *config)
{
    memset(config, 0, sizeof(*config));
    
    /* Default paths */
    strncpy(config->ca_cert_path, "/etc/immune/ca.crt", TLS_CERT_PATH_MAX - 1);
    strncpy(config->client_cert_path, "/etc/immune/agent.crt", TLS_CERT_PATH_MAX - 1);
    strncpy(config->client_key_path, "/etc/immune/agent.key", TLS_CERT_PATH_MAX - 1);
    
    /* Default options */
    config->verify_peer = true;
    config->mtls_enabled = true;
    config->session_resumption = true;
    config->pin_enabled = false;
    
    /* Default timeouts */
    config->handshake_timeout = TLS_HANDSHAKE_TIMEOUT;
    config->read_timeout = TLS_READ_TIMEOUT;
}

void
tls_config_set_pin(tls_config_t *config, const uint8_t *hash)
{
    if (config && hash) {
        config->pin_enabled = true;
        memcpy(config->pinned_hash, hash, TLS_PIN_HASH_SIZE);
    }
}

/* ==================== Channel Management ==================== */

tls_channel_t*
tls_channel_create(const tls_config_t *config)
{
    tls_channel_t *channel;
    
    channel = calloc(1, sizeof(tls_channel_t));
    if (!channel) {
        return NULL;
    }
    
    channel->fd = -1;
    channel->state = TLS_STATE_DISCONNECTED;
    channel->last_error = TLS_OK;
    
    /* Copy config */
    channel->verify_peer = config->verify_peer;
    channel->pin_enabled = config->pin_enabled;
    channel->handshake_timeout = config->handshake_timeout;
    channel->read_timeout = config->read_timeout;
    
    if (config->pin_enabled) {
        memcpy(channel->pinned_hash, config->pinned_hash, TLS_PIN_HASH_SIZE);
    }
    
#ifdef USE_WOLFSSL
    /* Create context */
    channel->ctx = wolfSSL_CTX_new(wolfTLSv1_3_client_method());
    if (!channel->ctx) {
        free(channel);
        return NULL;
    }
    
    /* Load CA certificate */
    if (config->ca_cert_path[0] && 
        wolfSSL_CTX_load_verify_locations(channel->ctx, 
            config->ca_cert_path, NULL) != SSL_SUCCESS) {
        fprintf(stderr, "[TLS] Failed to load CA cert: %s\n", config->ca_cert_path);
        wolfSSL_CTX_free(channel->ctx);
        free(channel);
        return NULL;
    }
    
    /* Load client certificate (mTLS) */
    if (config->mtls_enabled && config->client_cert_path[0]) {
        if (wolfSSL_CTX_use_certificate_file(channel->ctx,
                config->client_cert_path, SSL_FILETYPE_PEM) != SSL_SUCCESS) {
            fprintf(stderr, "[TLS] Failed to load client cert: %s\n", 
                config->client_cert_path);
            wolfSSL_CTX_free(channel->ctx);
            free(channel);
            return NULL;
        }
        
        if (wolfSSL_CTX_use_PrivateKey_file(channel->ctx,
                config->client_key_path, SSL_FILETYPE_PEM) != SSL_SUCCESS) {
            fprintf(stderr, "[TLS] Failed to load client key: %s\n",
                config->client_key_path);
            wolfSSL_CTX_free(channel->ctx);
            free(channel);
            return NULL;
        }
    }
    
    /* Set verification mode */
    if (config->verify_peer) {
        wolfSSL_CTX_set_verify(channel->ctx, 
            SSL_VERIFY_PEER | SSL_VERIFY_FAIL_IF_NO_PEER_CERT,
            verify_callback);
    }
#endif /* USE_WOLFSSL */
    
    return channel;
}

int
tls_channel_connect(tls_channel_t *channel, const char *host, uint16_t port)
{
    struct sockaddr_in addr;
    struct hostent *he;
    
    if (!channel || !host) {
        return TLS_ERR_INIT;
    }
    
    channel->state = TLS_STATE_CONNECTING;
    
    /* Resolve hostname */
    he = gethostbyname(host);
    if (!he) {
        channel->last_error = TLS_ERR_CONNECT;
        channel->state = TLS_STATE_ERROR;
        return TLS_ERR_CONNECT;
    }
    
    /* Create socket */
    channel->fd = socket(AF_INET, SOCK_STREAM, 0);
    if (channel->fd < 0) {
        channel->last_error = TLS_ERR_CONNECT;
        channel->state = TLS_STATE_ERROR;
        return TLS_ERR_CONNECT;
    }
    
    /* Set socket timeout */
    struct timeval tv;
    tv.tv_sec = channel->handshake_timeout;
    tv.tv_usec = 0;
    setsockopt(channel->fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
    setsockopt(channel->fd, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));
    
    /* Connect */
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    memcpy(&addr.sin_addr, he->h_addr_list[0], he->h_length);
    
    if (connect(channel->fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        close(channel->fd);
        channel->fd = -1;
        channel->last_error = TLS_ERR_CONNECT;
        channel->state = TLS_STATE_ERROR;
        return TLS_ERR_CONNECT;
    }
    
    channel->state = TLS_STATE_HANDSHAKE;
    
#ifdef USE_WOLFSSL
    /* Create SSL session */
    channel->ssl = wolfSSL_new(channel->ctx);
    if (!channel->ssl) {
        close(channel->fd);
        channel->fd = -1;
        channel->last_error = TLS_ERR_HANDSHAKE;
        channel->state = TLS_STATE_ERROR;
        return TLS_ERR_HANDSHAKE;
    }
    
    /* Associate socket */
    wolfSSL_set_fd(channel->ssl, channel->fd);
    
    /* Store channel pointer for verify callback */
    wolfSSL_set_ex_data(channel->ssl, 0, channel);
    
    /* Set SNI */
    wolfSSL_UseSNI(channel->ssl, WOLFSSL_SNI_HOST_NAME, 
                   host, strlen(host));
    
    /* Perform handshake */
    if (wolfSSL_connect(channel->ssl) != SSL_SUCCESS) {
        int err = wolfSSL_get_error(channel->ssl, 0);
        fprintf(stderr, "[TLS] Handshake failed: %d\n", err);
        
        wolfSSL_free(channel->ssl);
        channel->ssl = NULL;
        close(channel->fd);
        channel->fd = -1;
        
        if (channel->last_error == TLS_OK) {
            channel->last_error = TLS_ERR_HANDSHAKE;
        }
        channel->state = TLS_STATE_ERROR;
        return channel->last_error;
    }
    
    printf("[TLS] Connected to %s:%d (TLS 1.3)\n", host, port);
#else
    printf("[TLS] Connected to %s:%d (PLAINTEXT - wolfSSL not enabled)\n", 
           host, port);
#endif
    
    channel->state = TLS_STATE_CONNECTED;
    return TLS_OK;
}

void
tls_channel_close(tls_channel_t *channel)
{
    if (!channel) return;
    
#ifdef USE_WOLFSSL
    if (channel->ssl) {
        wolfSSL_shutdown(channel->ssl);
        wolfSSL_free(channel->ssl);
        channel->ssl = NULL;
    }
#endif
    
    if (channel->fd >= 0) {
        close(channel->fd);
        channel->fd = -1;
    }
    
    channel->state = TLS_STATE_DISCONNECTED;
}

void
tls_channel_destroy(tls_channel_t *channel)
{
    if (!channel) return;
    
    tls_channel_close(channel);
    
#ifdef USE_WOLFSSL
    if (channel->ctx) {
        wolfSSL_CTX_free(channel->ctx);
        channel->ctx = NULL;
    }
#endif
    
    /* Zero sensitive data */
    memset(channel->pinned_hash, 0, TLS_PIN_HASH_SIZE);
    
    free(channel);
}

/* ==================== Data Transfer ==================== */

int
tls_send(tls_channel_t *channel, const void *data, size_t len)
{
    if (!channel || !data || channel->state != TLS_STATE_CONNECTED) {
        return TLS_ERR_SEND;
    }
    
#ifdef USE_WOLFSSL
    int ret = wolfSSL_write(channel->ssl, data, len);
    if (ret <= 0) {
        channel->last_error = TLS_ERR_SEND;
        return TLS_ERR_SEND;
    }
    return ret;
#else
    ssize_t ret = send(channel->fd, data, len, 0);
    if (ret < 0) {
        channel->last_error = TLS_ERR_SEND;
        return TLS_ERR_SEND;
    }
    return (int)ret;
#endif
}

int
tls_recv(tls_channel_t *channel, void *buffer, size_t max_len)
{
    if (!channel || !buffer || channel->state != TLS_STATE_CONNECTED) {
        return TLS_ERR_RECV;
    }
    
#ifdef USE_WOLFSSL
    int ret = wolfSSL_read(channel->ssl, buffer, max_len);
    if (ret <= 0) {
        int err = wolfSSL_get_error(channel->ssl, ret);
        if (err == WOLFSSL_ERROR_WANT_READ) {
            channel->last_error = TLS_ERR_TIMEOUT;
            return TLS_ERR_TIMEOUT;
        }
        channel->last_error = TLS_ERR_RECV;
        return TLS_ERR_RECV;
    }
    return ret;
#else
    ssize_t ret = recv(channel->fd, buffer, max_len, 0);
    if (ret < 0) {
        channel->last_error = TLS_ERR_RECV;
        return TLS_ERR_RECV;
    }
    return (int)ret;
#endif
}

/* ==================== Status ==================== */

tls_state_t
tls_get_state(const tls_channel_t *channel)
{
    return channel ? channel->state : TLS_STATE_DISCONNECTED;
}

tls_error_t
tls_get_error(const tls_channel_t *channel)
{
    return channel ? channel->last_error : TLS_ERR_INIT;
}

/* ==================== Server Functions ==================== */

void*
tls_server_create(const tls_config_t *config)
{
#ifdef USE_WOLFSSL
    tls_server_ctx_t *srv = calloc(1, sizeof(tls_server_ctx_t));
    if (!srv) return NULL;
    
    memcpy(&srv->config, config, sizeof(tls_config_t));
    
    /* Create server context */
    srv->ctx = wolfSSL_CTX_new(wolfTLSv1_3_server_method());
    if (!srv->ctx) {
        free(srv);
        return NULL;
    }
    
    /* Load server certificate */
    /* Note: For server, use hive.crt and hive.key paths */
    if (wolfSSL_CTX_use_certificate_file(srv->ctx,
            "/etc/immune/hive.crt", SSL_FILETYPE_PEM) != SSL_SUCCESS) {
        fprintf(stderr, "[TLS] Failed to load server cert\n");
        wolfSSL_CTX_free(srv->ctx);
        free(srv);
        return NULL;
    }
    
    if (wolfSSL_CTX_use_PrivateKey_file(srv->ctx,
            "/etc/immune/hive.key", SSL_FILETYPE_PEM) != SSL_SUCCESS) {
        fprintf(stderr, "[TLS] Failed to load server key\n");
        wolfSSL_CTX_free(srv->ctx);
        free(srv);
        return NULL;
    }
    
    /* Load CA for client verification (mTLS) */
    if (config->mtls_enabled && config->ca_cert_path[0]) {
        wolfSSL_CTX_load_verify_locations(srv->ctx, config->ca_cert_path, NULL);
        wolfSSL_CTX_set_verify(srv->ctx,
            SSL_VERIFY_PEER | SSL_VERIFY_FAIL_IF_NO_PEER_CERT, NULL);
    }
    
    return srv;
#else
    fprintf(stderr, "[TLS] Server requires wolfSSL\n");
    return NULL;
#endif
}

tls_channel_t*
tls_server_accept(void *server_ctx, int client_fd)
{
#ifdef USE_WOLFSSL
    tls_server_ctx_t *srv = (tls_server_ctx_t *)server_ctx;
    if (!srv) return NULL;
    
    tls_channel_t *channel = calloc(1, sizeof(tls_channel_t));
    if (!channel) return NULL;
    
    channel->fd = client_fd;
    channel->state = TLS_STATE_HANDSHAKE;
    channel->ctx = NULL;  /* Server owns the context */
    
    /* Create SSL session */
    channel->ssl = wolfSSL_new(srv->ctx);
    if (!channel->ssl) {
        free(channel);
        return NULL;
    }
    
    wolfSSL_set_fd(channel->ssl, client_fd);
    
    /* Perform server-side handshake */
    if (wolfSSL_accept(channel->ssl) != SSL_SUCCESS) {
        fprintf(stderr, "[TLS] Server handshake failed\n");
        wolfSSL_free(channel->ssl);
        free(channel);
        return NULL;
    }
    
    channel->state = TLS_STATE_CONNECTED;
    return channel;
#else
    (void)server_ctx;
    (void)client_fd;
    return NULL;
#endif
}

void
tls_server_destroy(void *server_ctx)
{
#ifdef USE_WOLFSSL
    tls_server_ctx_t *srv = (tls_server_ctx_t *)server_ctx;
    if (srv) {
        if (srv->ctx) {
            wolfSSL_CTX_free(srv->ctx);
        }
        free(srv);
    }
#else
    (void)server_ctx;
#endif
}
