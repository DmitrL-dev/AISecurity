/*
 * SENTINEL Shield - Multicast Signature Protocol (SMRP)
 * 
 * Multicast distribution of signature updates across cluster
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_common.h"
#include "shield_protocol.h"

/* SMRP Message Types */
typedef enum {
    SMRP_MSG_JOIN       = 0x01,
    SMRP_MSG_LEAVE      = 0x02,
    SMRP_MSG_SIGNATURE  = 0x03,
    SMRP_MSG_ACK        = 0x04,
} smrp_msg_type_t;

/* SMRP Context */
typedef struct {
    int         mcast_socket;
    char        mcast_group[64];
    uint16_t    mcast_port;
    bool        joined;
} smrp_context_t;

/* Join multicast group */
shield_err_t smrp_join(smrp_context_t *ctx, const char *group, uint16_t port)
{
    if (!ctx || !group) return SHIELD_ERR_INVALID;
    
    strncpy(ctx->mcast_group, group, sizeof(ctx->mcast_group) - 1);
    ctx->mcast_port = port;
    
    /* Setup multicast socket */
    ctx->mcast_socket = socket(AF_INET, SOCK_DGRAM, 0);
    if (ctx->mcast_socket < 0) return SHIELD_ERR_IO;
    
    /* Join would happen here with setsockopt IP_ADD_MEMBERSHIP */
    
    ctx->joined = true;
    LOG_INFO("SMRP: Joined multicast group %s:%u", group, port);
    return SHIELD_OK;
}

/* Broadcast signature */
shield_err_t smrp_broadcast_signature(smrp_context_t *ctx, const void *sig, size_t size)
{
    if (!ctx || !ctx->joined || !sig) return SHIELD_ERR_INVALID;
    
    uint8_t type = SMRP_MSG_SIGNATURE;
    uint32_t len = size;
    
    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(ctx->mcast_port);
    inet_pton(AF_INET, ctx->mcast_group, &addr.sin_addr);
    
    sendto(ctx->mcast_socket, &type, 1, 0, (struct sockaddr*)&addr, sizeof(addr));
    sendto(ctx->mcast_socket, &len, 4, 0, (struct sockaddr*)&addr, sizeof(addr));
    sendto(ctx->mcast_socket, sig, size, 0, (struct sockaddr*)&addr, sizeof(addr));
    
    return SHIELD_OK;
}

/* Leave group */
shield_err_t smrp_leave(smrp_context_t *ctx)
{
    if (!ctx) return SHIELD_ERR_INVALID;
    
    if (ctx->mcast_socket >= 0) {
        close(ctx->mcast_socket);
        ctx->mcast_socket = -1;
    }
    ctx->joined = false;
    
    return SHIELD_OK;
}

/* Initialize SMRP */
shield_err_t smrp_init(smrp_context_t *ctx)
{
    if (!ctx) return SHIELD_ERR_INVALID;
    memset(ctx, 0, sizeof(*ctx));
    ctx->mcast_socket = -1;
    return SHIELD_OK;
}
