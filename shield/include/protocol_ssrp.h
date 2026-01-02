/*
 * SENTINEL Shield - SSRP Protocol (State Replication Protocol)
 * 
 * For replicating state between HA nodes
 */

#ifndef PROTOCOL_SSRP_H
#define PROTOCOL_SSRP_H

#include "shield_common.h"

#define SSRP_MAGIC      0x53535250  /* 'SSRP' */
#define SSRP_VERSION    1

/* Message types */
typedef enum ssrp_msg_type {
    SSRP_MSG_SYNC_REQUEST = 1,
    SSRP_MSG_SYNC_RESPONSE = 2,
    SSRP_MSG_DELTA_UPDATE = 3,
    SSRP_MSG_FULL_STATE = 4,
    SSRP_MSG_ACK = 5,
    SSRP_MSG_NACK = 6,
} ssrp_msg_type_t;

/* State types */
typedef enum ssrp_state_type {
    SSRP_STATE_SESSIONS = 1,
    SSRP_STATE_BLOCKLIST = 2,
    SSRP_STATE_RULES = 3,
    SSRP_STATE_ZONES = 4,
    SSRP_STATE_CANARIES = 5,
    SSRP_STATE_QUARANTINE = 6,
} ssrp_state_type_t;

/* SSRP header */
typedef struct ssrp_header {
    uint32_t        magic;
    uint8_t         version;
    uint8_t         msg_type;
    uint8_t         state_type;
    uint8_t         flags;
    uint32_t        sequence;
    uint32_t        payload_len;
    uint64_t        timestamp;
    char            node_id[32];
} __attribute__((packed)) ssrp_header_t;

/* Sync request */
typedef struct ssrp_sync_request {
    ssrp_state_type_t state_type;
    uint64_t        last_known_seq;
    bool            full_sync;
} ssrp_sync_request_t;

/* Delta update entry */
typedef struct ssrp_delta_entry {
    uint8_t         operation;      /* 0=add, 1=update, 2=delete */
    uint8_t         state_type;
    uint16_t        key_len;
    uint32_t        value_len;
    /* followed by key and value data */
} __attribute__((packed)) ssrp_delta_entry_t;

/* State checksum */
typedef struct ssrp_checksum {
    ssrp_state_type_t type;
    uint64_t        entry_count;
    uint64_t        checksum;
} ssrp_checksum_t;

/* Connection */
typedef struct ssrp_connection {
    int             socket;
    char            peer_address[64];
    uint16_t        peer_port;
    uint32_t        next_sequence;
    bool            connected;
    uint64_t        last_sync_time;
} ssrp_connection_t;

/* API */
shield_err_t ssrp_connect(ssrp_connection_t *conn, const char *address, uint16_t port);
void ssrp_disconnect(ssrp_connection_t *conn);

/* Request sync */
shield_err_t ssrp_request_sync(ssrp_connection_t *conn, ssrp_state_type_t type);

/* Send delta */
shield_err_t ssrp_send_delta(ssrp_connection_t *conn, ssrp_state_type_t type,
                              uint8_t operation, const void *key, size_t key_len,
                              const void *value, size_t value_len);

/* Receive */
shield_err_t ssrp_receive(ssrp_connection_t *conn, ssrp_header_t *header,
                           void **payload, int timeout_ms);

/* State helpers */
uint64_t ssrp_calculate_checksum(ssrp_state_type_t type, const void *data, size_t len);

#endif /* PROTOCOL_SSRP_H */
