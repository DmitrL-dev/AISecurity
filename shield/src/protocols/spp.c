/*
 * SENTINEL Shield - Policy Distribution Protocol (SPP)
 * 
 * Distributes policies across cluster nodes
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_common.h"
#include "shield_protocol.h"
#include "shield_policy.h"

/* SPP Message Types */
typedef enum {
    SPP_MSG_POLICY_PUSH    = 0x01,
    SPP_MSG_POLICY_PULL    = 0x02,
    SPP_MSG_POLICY_UPDATE  = 0x03,
    SPP_MSG_POLICY_DELETE  = 0x04,
    SPP_MSG_POLICY_ACK     = 0x05,
    SPP_MSG_VERSION_CHECK  = 0x06,
    SPP_MSG_VERSION_RESP   = 0x07,
    SPP_MSG_SYNC_REQUEST   = 0x08,
    SPP_MSG_SYNC_BEGIN     = 0x09,
    SPP_MSG_SYNC_DATA      = 0x0A,
    SPP_MSG_SYNC_END       = 0x0B,
} spp_msg_type_t;

/* Policy Header */
typedef struct {
    char     policy_id[64];
    uint32_t version;
    uint32_t size;
    uint64_t timestamp;
    uint8_t  flags;
} spp_policy_header_t;

/* SPP Context */
typedef struct {
    int             socket;
    uint32_t        local_version;
    spp_callback_t  callback;
    void           *user_data;
} spp_context_t;

/* Push policy to peers */
shield_err_t spp_push_policy(spp_context_t *ctx, const char *policy_id,
                              const void *data, size_t size)
{
    if (!ctx || !policy_id || !data) {
        return SHIELD_ERR_INVALID;
    }
    
    uint8_t type = SPP_MSG_POLICY_PUSH;
    spp_policy_header_t header = {
        .version = ++ctx->local_version,
        .size = size,
        .timestamp = time(NULL)
    };
    strncpy(header.policy_id, policy_id, sizeof(header.policy_id) - 1);
    
    if (ctx->socket >= 0) {
        send(ctx->socket, &type, 1, 0);
        send(ctx->socket, &header, sizeof(header), 0);
        send(ctx->socket, data, size, 0);
    }
    
    LOG_INFO("SPP: Pushed policy %s v%u", policy_id, header.version);
    return SHIELD_OK;
}

/* Request policy from peers */
shield_err_t spp_pull_policy(spp_context_t *ctx, const char *policy_id)
{
    if (!ctx || !policy_id) {
        return SHIELD_ERR_INVALID;
    }
    
    struct {
        uint8_t type;
        char policy_id[64];
    } request = {
        .type = SPP_MSG_POLICY_PULL
    };
    strncpy(request.policy_id, policy_id, sizeof(request.policy_id) - 1);
    
    if (ctx->socket >= 0) {
        send(ctx->socket, &request, sizeof(request), 0);
    }
    
    return SHIELD_OK;
}

/* Request full sync */
shield_err_t spp_sync_request(spp_context_t *ctx)
{
    if (!ctx) {
        return SHIELD_ERR_INVALID;
    }
    
    struct {
        uint8_t type;
        uint32_t local_version;
    } request = {
        .type = SPP_MSG_SYNC_REQUEST,
        .local_version = ctx->local_version
    };
    
    if (ctx->socket >= 0) {
        send(ctx->socket, &request, sizeof(request), 0);
    }
    
    LOG_INFO("SPP: Sync requested, local version %u", ctx->local_version);
    return SHIELD_OK;
}

/* Check version */
shield_err_t spp_check_version(spp_context_t *ctx, uint32_t *remote_version)
{
    if (!ctx || !remote_version) {
        return SHIELD_ERR_INVALID;
    }
    
    uint8_t type = SPP_MSG_VERSION_CHECK;
    if (ctx->socket >= 0) {
        send(ctx->socket, &type, 1, 0);
        
        uint8_t resp_type;
        recv(ctx->socket, &resp_type, 1, 0);
        if (resp_type == SPP_MSG_VERSION_RESP) {
            recv(ctx->socket, remote_version, sizeof(*remote_version), 0);
        }
    }
    
    return SHIELD_OK;
}

/* Process incoming message */
shield_err_t spp_process(spp_context_t *ctx)
{
    if (!ctx || ctx->socket < 0) {
        return SHIELD_ERR_INVALID;
    }
    
    uint8_t type;
    if (recv(ctx->socket, &type, 1, MSG_PEEK) <= 0) {
        return SHIELD_ERR_IO;
    }
    
    recv(ctx->socket, &type, 1, 0);
    
    switch (type) {
    case SPP_MSG_POLICY_PUSH: {
        spp_policy_header_t header;
        recv(ctx->socket, &header, sizeof(header), 0);
        
        void *data = malloc(header.size);
        recv(ctx->socket, data, header.size, 0);
        
        if (ctx->callback) {
            ctx->callback(SPP_EVENT_POLICY_RECEIVED, header.policy_id, 
                         data, header.size, ctx->user_data);
        }
        
        free(data);
        
        /* Send ACK */
        uint8_t ack = SPP_MSG_POLICY_ACK;
        send(ctx->socket, &ack, 1, 0);
        break;
    }
    
    case SPP_MSG_SYNC_BEGIN:
        LOG_INFO("SPP: Sync begin");
        break;
        
    case SPP_MSG_SYNC_END:
        LOG_INFO("SPP: Sync complete");
        break;
        
    default:
        break;
    }
    
    return SHIELD_OK;
}

/* Initialize SPP */
shield_err_t spp_init(spp_context_t *ctx)
{
    if (!ctx) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(ctx, 0, sizeof(*ctx));
    ctx->socket = -1;
    ctx->local_version = 0;
    
    return SHIELD_OK;
}

/* Destroy SPP */
void spp_destroy(spp_context_t *ctx)
{
    if (ctx && ctx->socket >= 0) {
        close(ctx->socket);
    }
}
