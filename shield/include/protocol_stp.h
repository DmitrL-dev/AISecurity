/*
 * SENTINEL Shield - STP (Sentinel Transfer Protocol) Implementation
 * 
 * Protocol for secure prompt/response transport between zones
 */

#ifndef SHIELD_PROTOCOL_STP_H
#define SHIELD_PROTOCOL_STP_H

#include "shield_common.h"

/* STP Message Types */
typedef enum stp_msg_type {
    STP_MSG_REQUEST = 0x01,     /* Client -> Zone */
    STP_MSG_RESPONSE = 0x02,    /* Zone -> Client */
    STP_MSG_ACK = 0x03,         /* Acknowledgement */
    STP_MSG_NACK = 0x04,        /* Negative ack (blocked) */
    STP_MSG_PING = 0x10,        /* Health check */
    STP_MSG_PONG = 0x11,        /* Health response */
} stp_msg_type_t;

/* STP Header (fixed size: 24 bytes) */
typedef struct __attribute__((packed)) stp_header {
    uint32_t    magic;          /* 0x53545001 = "STP\x01" */
    uint16_t    version;        /* Protocol version */
    uint16_t    msg_type;       /* Message type */
    uint32_t    sequence;       /* Sequence number */
    uint32_t    payload_len;    /* Payload length */
    uint32_t    zone_id;        /* Target zone ID */
    uint32_t    flags;          /* Flags */
} stp_header_t;

/* STP Flags */
#define STP_FLAG_ENCRYPTED      0x0001
#define STP_FLAG_COMPRESSED     0x0002
#define STP_FLAG_URGENT         0x0004
#define STP_FLAG_MORE_DATA      0x0008

/* STP Message */
typedef struct stp_message {
    stp_header_t    header;
    void            *payload;
    size_t          payload_len;
} stp_message_t;

/* STP Context */
typedef struct stp_context {
    uint32_t        next_sequence;
    bool            encryption_enabled;
    uint8_t         encryption_key[32];
} stp_context_t;

/* API */
shield_err_t stp_init(stp_context_t *ctx);
void stp_destroy(stp_context_t *ctx);

shield_err_t stp_create_request(stp_context_t *ctx, uint32_t zone_id,
                                 const void *data, size_t len,
                                 stp_message_t **out);
shield_err_t stp_create_response(stp_context_t *ctx, uint32_t sequence,
                                  const void *data, size_t len,
                                  stp_message_t **out);

shield_err_t stp_parse(const void *buffer, size_t len, stp_message_t **out);
shield_err_t stp_serialize(const stp_message_t *msg, void **buffer, size_t *len);

void stp_message_free(stp_message_t *msg);

bool stp_validate_header(const stp_header_t *header);

#endif /* SHIELD_PROTOCOL_STP_H */
