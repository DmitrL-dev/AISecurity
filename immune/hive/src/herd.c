/*
 * SENTINEL IMMUNE — Hive Herd Immunity
 * 
 * Distributed threat intelligence sharing.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <pthread.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

#include "../include/hive.h"
#include "../include/protocol.h"

#define HERD_PORT           9997
#define SIGNATURE_MAX_LEN   256
/* MAX_PEERS already defined in hive.h, use local override */
#undef MAX_PEERS
#define MAX_PEERS           64
#define SYNC_INTERVAL       3600    /* 1 hour */

/* Local signature type for herd */
typedef struct {
    uint32_t id;
    char pattern[256];
    uint8_t type;
    uint8_t severity;
    uint32_t source_agent;
} herd_signature_t;

/* Peer information */
typedef struct {
    char        address[MAX_IP_LEN];
    uint16_t    port;
    time_t      last_sync;
    uint64_t    sig_count;
    int         active;
} herd_peer_t;

/* Herd context */
typedef struct {
    immune_hive_t   *hive;
    herd_peer_t     peers[MAX_PEERS];
    int             peer_count;
    pthread_mutex_t lock;
    int             running;
} herd_ctx_t;

/* ==================== Peer Management ==================== */

int
herd_add_peer(herd_ctx_t *ctx, const char *address, uint16_t port)
{
    if (ctx->peer_count >= MAX_PEERS)
        return -1;
    
    pthread_mutex_lock(&ctx->lock);
    
    /* Check if already exists */
    for (int i = 0; i < ctx->peer_count; i++) {
        if (strcmp(ctx->peers[i].address, address) == 0) {
            pthread_mutex_unlock(&ctx->lock);
            return 0;
        }
    }
    
    /* Add new peer */
    herd_peer_t *peer = &ctx->peers[ctx->peer_count];
    strncpy(peer->address, address, MAX_IP_LEN - 1);
    peer->port = port;
    peer->last_sync = 0;
    peer->sig_count = 0;
    peer->active = 1;
    
    ctx->peer_count++;
    
    pthread_mutex_unlock(&ctx->lock);
    
    printf("[HERD] Peer added: %s:%d\n", address, port);
    return 0;
}

int
herd_remove_peer(herd_ctx_t *ctx, const char *address)
{
    pthread_mutex_lock(&ctx->lock);
    
    for (int i = 0; i < ctx->peer_count; i++) {
        if (strcmp(ctx->peers[i].address, address) == 0) {
            ctx->peers[i].active = 0;
            pthread_mutex_unlock(&ctx->lock);
            return 0;
        }
    }
    
    pthread_mutex_unlock(&ctx->lock);
    return -1;
}

/* ==================== Signature Sync ==================== */

/* Sync signatures with a peer */
int
herd_sync_peer(herd_ctx_t *ctx, herd_peer_t *peer)
{
    int sock;
    struct sockaddr_in addr;
    
    sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0)
        return -1;
    
    addr.sin_family = AF_INET;
    addr.sin_port = htons(peer->port);
    inet_pton(AF_INET, peer->address, &addr.sin_addr);
    
    /* Set timeout */
    struct timeval tv;
    tv.tv_sec = 5;
    tv.tv_usec = 0;
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
    
    if (connect(sock, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        close(sock);
        return -1;
    }
    
    /* Send sync request */
    immune_msg_t msg;
    msg.magic = IMMUNE_MAGIC;
    msg.type = MSG_GET_SIGNATURES;
    msg.length = 0;
    
    send(sock, &msg, sizeof(msg), 0);
    
    /* Receive signatures */
    uint8_t buffer[4096];
    ssize_t n = recv(sock, buffer, sizeof(buffer), 0);
    
    if (n > 0) {
        immune_msg_t *resp = (immune_msg_t *)buffer;
        
        if (resp->magic == IMMUNE_MAGIC && resp->type == MSG_SIGNATURES) {
            /* Parse and add signatures */
            int sig_count = resp->length / sizeof(msg_signature_t);
            msg_signature_t *sigs = (msg_signature_t *)resp->payload;
            
            for (int i = 0; i < sig_count; i++) {
                hive_add_signature(
                    ctx->hive,
                    sigs[i].pattern,
                    sigs[i].severity,  /* threat_level_t */
                    sigs[i].type       /* threat_type_t */
                );
            }
            
            peer->sig_count = sig_count;
            printf("[HERD] Synced %d signatures from %s\n", 
                   sig_count, peer->address);
        }
    }
    
    peer->last_sync = time(NULL);
    close(sock);
    
    return 0;
}

/* Sync with all peers */
int
herd_sync_all(herd_ctx_t *ctx)
{
    int synced = 0;
    
    pthread_mutex_lock(&ctx->lock);
    
    for (int i = 0; i < ctx->peer_count; i++) {
        if (!ctx->peers[i].active)
            continue;
        
        if (herd_sync_peer(ctx, &ctx->peers[i]) == 0)
            synced++;
    }
    
    pthread_mutex_unlock(&ctx->lock);
    
    return synced;
}

/* ==================== Broadcast ==================== */

/* Broadcast new signature to all peers */
int
herd_broadcast_signature(herd_ctx_t *ctx, herd_signature_t *sig)
{
    pthread_mutex_lock(&ctx->lock);
    
    for (int i = 0; i < ctx->peer_count; i++) {
        if (!ctx->peers[i].active)
            continue;
        
        int sock = socket(AF_INET, SOCK_STREAM, 0);
        if (sock < 0)
            continue;
        
        struct sockaddr_in addr;
        addr.sin_family = AF_INET;
        addr.sin_port = htons(ctx->peers[i].port);
        inet_pton(AF_INET, ctx->peers[i].address, &addr.sin_addr);
        
        if (connect(sock, (struct sockaddr *)&addr, sizeof(addr)) == 0) {
            immune_msg_t msg;
            msg.magic = IMMUNE_MAGIC;
            msg.type = MSG_SIGNATURE;
            msg.length = sizeof(msg_signature_t);
            
            msg_signature_t *payload = (msg_signature_t *)msg.payload;
            strncpy(payload->pattern, sig->pattern, SIGNATURE_MAX_LEN - 1);
            payload->type = sig->type;
            payload->severity = sig->severity;
            payload->source_agent = sig->source_agent;
            
            send(sock, &msg, sizeof(msg), 0);
        }
        
        close(sock);
    }
    
    pthread_mutex_unlock(&ctx->lock);
    
    printf("[HERD] Signature broadcast complete\n");
    return 0;
}

/* ==================== Background Sync ==================== */

void*
herd_sync_thread(void *arg)
{
    herd_ctx_t *ctx = (herd_ctx_t *)arg;
    
    while (ctx->running) {
        sleep(SYNC_INTERVAL);
        
        if (!ctx->running)
            break;
        
        printf("[HERD] Starting periodic sync\n");
        int synced = herd_sync_all(ctx);
        printf("[HERD] Synced with %d peers\n", synced);
    }
    
    return NULL;
}

/* ==================== Initialization ==================== */

herd_ctx_t*
herd_init(immune_hive_t *hive)
{
    herd_ctx_t *ctx = calloc(1, sizeof(herd_ctx_t));
    if (!ctx)
        return NULL;
    
    ctx->hive = hive;
    pthread_mutex_init(&ctx->lock, NULL);
    ctx->running = 1;
    
    printf("[HERD] Herd immunity initialized\n");
    return ctx;
}

void
herd_shutdown(herd_ctx_t *ctx)
{
    if (!ctx)
        return;
    
    ctx->running = 0;
    pthread_mutex_destroy(&ctx->lock);
    free(ctx);
    
    printf("[HERD] Shutdown complete\n");
}
