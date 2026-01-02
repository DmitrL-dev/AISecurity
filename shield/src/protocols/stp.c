/*
 * SENTINEL Shield - STP (Sentinel Transfer Protocol) Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_common.h"
#include "protocol_stp.h"

#define STP_MAGIC 0x53545001 /* "STP\x01" */
#define STP_VERSION 0x0100   /* 1.0 */

/* Initialize STP context */
shield_err_t stp_init(stp_context_t *ctx)
{
    if (!ctx) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(ctx, 0, sizeof(*ctx));
    ctx->next_sequence = 1;
    ctx->encryption_enabled = false;
    
    return SHIELD_OK;
}

/* Destroy STP context */
void stp_destroy(stp_context_t *ctx)
{
    if (ctx) {
        memset(ctx->encryption_key, 0, sizeof(ctx->encryption_key));
    }
}

/* Create request message */
shield_err_t stp_create_request(stp_context_t *ctx, uint32_t zone_id,
                                 const void *data, size_t len,
                                 stp_message_t **out)
{
    if (!ctx || !out) {
        return SHIELD_ERR_INVALID;
    }
    
    stp_message_t *msg = calloc(1, sizeof(stp_message_t));
    if (!msg) {
        return SHIELD_ERR_NOMEM;
    }
    
    /* Fill header */
    msg->header.magic = STP_MAGIC;
    msg->header.version = STP_VERSION;
    msg->header.msg_type = STP_MSG_REQUEST;
    msg->header.sequence = ctx->next_sequence++;
    msg->header.payload_len = (uint32_t)len;
    msg->header.zone_id = zone_id;
    msg->header.flags = 0;
    
    if (ctx->encryption_enabled) {
        msg->header.flags |= STP_FLAG_ENCRYPTED;
    }
    
    /* Copy payload */
    if (data && len > 0) {
        msg->payload = malloc(len);
        if (!msg->payload) {
            free(msg);
            return SHIELD_ERR_NOMEM;
        }
        memcpy(msg->payload, data, len);
        msg->payload_len = len;
    }
    
    *out = msg;
    return SHIELD_OK;
}

/* Create response message */
shield_err_t stp_create_response(stp_context_t *ctx, uint32_t sequence,
                                  const void *data, size_t len,
                                  stp_message_t **out)
{
    if (!ctx || !out) {
        return SHIELD_ERR_INVALID;
    }
    
    stp_message_t *msg = calloc(1, sizeof(stp_message_t));
    if (!msg) {
        return SHIELD_ERR_NOMEM;
    }
    
    msg->header.magic = STP_MAGIC;
    msg->header.version = STP_VERSION;
    msg->header.msg_type = STP_MSG_RESPONSE;
    msg->header.sequence = sequence;
    msg->header.payload_len = (uint32_t)len;
    msg->header.zone_id = 0;
    msg->header.flags = 0;
    
    if (data && len > 0) {
        msg->payload = malloc(len);
        if (!msg->payload) {
            free(msg);
            return SHIELD_ERR_NOMEM;
        }
        memcpy(msg->payload, data, len);
        msg->payload_len = len;
    }
    
    *out = msg;
    return SHIELD_OK;
}

/* Parse message from buffer */
shield_err_t stp_parse(const void *buffer, size_t len, stp_message_t **out)
{
    if (!buffer || !out || len < sizeof(stp_header_t)) {
        return SHIELD_ERR_INVALID;
    }
    
    const stp_header_t *header = (const stp_header_t *)buffer;
    
    if (!stp_validate_header(header)) {
        return SHIELD_ERR_PARSE;
    }
    
    size_t total_len = sizeof(stp_header_t) + header->payload_len;
    if (len < total_len) {
        return SHIELD_ERR_PARSE;
    }
    
    stp_message_t *msg = calloc(1, sizeof(stp_message_t));
    if (!msg) {
        return SHIELD_ERR_NOMEM;
    }
    
    memcpy(&msg->header, header, sizeof(stp_header_t));
    
    if (header->payload_len > 0) {
        msg->payload = malloc(header->payload_len);
        if (!msg->payload) {
            free(msg);
            return SHIELD_ERR_NOMEM;
        }
        memcpy(msg->payload, (const uint8_t *)buffer + sizeof(stp_header_t),
               header->payload_len);
        msg->payload_len = header->payload_len;
    }
    
    *out = msg;
    return SHIELD_OK;
}

/* Serialize message to buffer */
shield_err_t stp_serialize(const stp_message_t *msg, void **buffer, size_t *len)
{
    if (!msg || !buffer || !len) {
        return SHIELD_ERR_INVALID;
    }
    
    size_t total_len = sizeof(stp_header_t) + msg->payload_len;
    uint8_t *buf = malloc(total_len);
    if (!buf) {
        return SHIELD_ERR_NOMEM;
    }
    
    memcpy(buf, &msg->header, sizeof(stp_header_t));
    
    if (msg->payload && msg->payload_len > 0) {
        memcpy(buf + sizeof(stp_header_t), msg->payload, msg->payload_len);
    }
    
    *buffer = buf;
    *len = total_len;
    return SHIELD_OK;
}

/* Free message */
void stp_message_free(stp_message_t *msg)
{
    if (msg) {
        free(msg->payload);
        free(msg);
    }
}

/* Validate header */
bool stp_validate_header(const stp_header_t *header)
{
    if (!header) {
        return false;
    }
    
    if (header->magic != STP_MAGIC) {
        return false;
    }
    
    if ((header->version & 0xFF00) != (STP_VERSION & 0xFF00)) {
        /* Major version mismatch */
        return false;
    }
    
    if (header->msg_type == 0 || header->msg_type > STP_MSG_PONG) {
        return false;
    }
    
    return true;
}
