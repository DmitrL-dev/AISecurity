/*
 * SENTINEL Shield - Zone Registration Protocol (ZRP)
 * 
 * Handles zone registration and deregistration in cluster
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_common.h"
#include "shield_protocol.h"
#include "shield_zone.h"

/* ZRP Message Types */
typedef enum {
    ZRP_MSG_REGISTER     = 0x01,
    ZRP_MSG_DEREGISTER   = 0x02,
    ZRP_MSG_ACK          = 0x03,
    ZRP_MSG_NACK         = 0x04,
    ZRP_MSG_LIST         = 0x05,
    ZRP_MSG_LIST_RESP    = 0x06,
    ZRP_MSG_UPDATE       = 0x07,
} zrp_msg_type_t;

/* ZRP Message Header */
typedef struct {
    uint8_t  version;
    uint8_t  type;
    uint16_t length;
    uint32_t sequence;
} zrp_header_t;

/* Zone Registration Message */
typedef struct {
    char     zone_name[SHIELD_MAX_NAME_LEN];
    uint8_t  zone_type;
    uint8_t  trust_level;
    char     provider[SHIELD_MAX_NAME_LEN];
    char     node_id[SHIELD_MAX_NAME_LEN];
    uint32_t capabilities;
} zrp_register_msg_t;

/* ZRP Context */
typedef struct {
    int                 socket;
    uint32_t            sequence;
    char                node_id[SHIELD_MAX_NAME_LEN];
    zrp_callback_t      callback;
    void               *user_data;
} zrp_context_t;

/* Initialize ZRP */
shield_err_t zrp_init(zrp_context_t *ctx, const char *node_id)
{
    if (!ctx || !node_id) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(ctx, 0, sizeof(*ctx));
    strncpy(ctx->node_id, node_id, sizeof(ctx->node_id) - 1);
    ctx->socket = -1;
    ctx->sequence = 0;
    
    return SHIELD_OK;
}

/* Register zone */
shield_err_t zrp_register(zrp_context_t *ctx, const shield_zone_t *zone)
{
    if (!ctx || !zone) {
        return SHIELD_ERR_INVALID;
    }
    
    zrp_header_t header = {
        .version = 1,
        .type = ZRP_MSG_REGISTER,
        .length = sizeof(zrp_register_msg_t),
        .sequence = ++ctx->sequence
    };
    
    zrp_register_msg_t msg;
    memset(&msg, 0, sizeof(msg));
    strncpy(msg.zone_name, zone->name, sizeof(msg.zone_name) - 1);
    msg.zone_type = zone->type;
    msg.trust_level = zone->trust_level;
    strncpy(msg.provider, zone->provider, sizeof(msg.provider) - 1);
    strncpy(msg.node_id, ctx->node_id, sizeof(msg.node_id) - 1);
    
    /* Send registration */
    if (ctx->socket >= 0) {
        send(ctx->socket, &header, sizeof(header), 0);
        send(ctx->socket, &msg, sizeof(msg), 0);
    }
    
    LOG_DEBUG("ZRP: Registered zone %s", zone->name);
    return SHIELD_OK;
}

/* Deregister zone */
shield_err_t zrp_deregister(zrp_context_t *ctx, const char *zone_name)
{
    if (!ctx || !zone_name) {
        return SHIELD_ERR_INVALID;
    }
    
    zrp_header_t header = {
        .version = 1,
        .type = ZRP_MSG_DEREGISTER,
        .length = SHIELD_MAX_NAME_LEN,
        .sequence = ++ctx->sequence
    };
    
    char name[SHIELD_MAX_NAME_LEN];
    memset(name, 0, sizeof(name));
    strncpy(name, zone_name, sizeof(name) - 1);
    
    if (ctx->socket >= 0) {
        send(ctx->socket, &header, sizeof(header), 0);
        send(ctx->socket, name, sizeof(name), 0);
    }
    
    LOG_DEBUG("ZRP: Deregistered zone %s", zone_name);
    return SHIELD_OK;
}

/* List registered zones */
shield_err_t zrp_list_zones(zrp_context_t *ctx, zrp_zone_list_t *out)
{
    if (!ctx || !out) {
        return SHIELD_ERR_INVALID;
    }
    
    zrp_header_t header = {
        .version = 1,
        .type = ZRP_MSG_LIST,
        .length = 0,
        .sequence = ++ctx->sequence
    };
    
    if (ctx->socket >= 0) {
        send(ctx->socket, &header, sizeof(header), 0);
        
        /* Wait for response */
        recv(ctx->socket, &header, sizeof(header), 0);
        if (header.type == ZRP_MSG_LIST_RESP) {
            recv(ctx->socket, out, sizeof(*out), 0);
        }
    }
    
    return SHIELD_OK;
}

/* Process incoming message */
shield_err_t zrp_process(zrp_context_t *ctx)
{
    if (!ctx || ctx->socket < 0) {
        return SHIELD_ERR_INVALID;
    }
    
    zrp_header_t header;
    ssize_t n = recv(ctx->socket, &header, sizeof(header), MSG_PEEK);
    if (n <= 0) {
        return SHIELD_ERR_IO;
    }
    
    recv(ctx->socket, &header, sizeof(header), 0);
    
    switch (header.type) {
    case ZRP_MSG_REGISTER: {
        zrp_register_msg_t msg;
        recv(ctx->socket, &msg, sizeof(msg), 0);
        
        if (ctx->callback) {
            ctx->callback(ZRP_EVENT_ZONE_REGISTERED, msg.zone_name, ctx->user_data);
        }
        
        /* Send ACK */
        zrp_header_t ack = {.version = 1, .type = ZRP_MSG_ACK, .sequence = header.sequence};
        send(ctx->socket, &ack, sizeof(ack), 0);
        break;
    }
    
    case ZRP_MSG_DEREGISTER: {
        char name[SHIELD_MAX_NAME_LEN];
        recv(ctx->socket, name, sizeof(name), 0);
        
        if (ctx->callback) {
            ctx->callback(ZRP_EVENT_ZONE_DEREGISTERED, name, ctx->user_data);
        }
        break;
    }
    
    default:
        /* Unknown message */
        break;
    }
    
    return SHIELD_OK;
}

/* Destroy ZRP context */
void zrp_destroy(zrp_context_t *ctx)
{
    if (ctx && ctx->socket >= 0) {
        close(ctx->socket);
        ctx->socket = -1;
    }
}
