/*
 * SENTINEL Shield - SHSP (Shield Hot Standby Protocol)
 * 
 * Protocol for HA cluster communication
 */

#ifndef SHIELD_PROTOCOL_SHSP_H
#define SHIELD_PROTOCOL_SHSP_H

#include "shield_common.h"

#define SHSP_MAGIC 0x53485350  /* "SHSP" */
#define SHSP_VERSION 0x0100

/* SHSP Message Types */
typedef enum shsp_msg_type {
    /* Heartbeat */
    SHSP_MSG_HEARTBEAT = 0x01,
    SHSP_MSG_HEARTBEAT_ACK = 0x02,
    
    /* Election */
    SHSP_MSG_ELECTION_START = 0x10,
    SHSP_MSG_ELECTION_VOTE = 0x11,
    SHSP_MSG_ELECTION_RESULT = 0x12,
    
    /* Sync */
    SHSP_MSG_SYNC_REQUEST = 0x20,
    SHSP_MSG_SYNC_CONFIG = 0x21,
    SHSP_MSG_SYNC_BLOCKLIST = 0x22,
    SHSP_MSG_SYNC_SESSIONS = 0x23,
    SHSP_MSG_SYNC_ACK = 0x2F,
    
    /* State */
    SHSP_MSG_STATE_CHANGE = 0x30,
    SHSP_MSG_TAKEOVER = 0x31,
    SHSP_MSG_HANDOFF = 0x32,
} shsp_msg_type_t;

/* SHSP Header (24 bytes) */
typedef struct __attribute__((packed)) shsp_header {
    uint32_t    magic;
    uint16_t    version;
    uint16_t    msg_type;
    uint32_t    sequence;
    uint32_t    payload_len;
    char        node_id[8];
} shsp_header_t;

/* Heartbeat payload */
typedef struct shsp_heartbeat {
    uint32_t    role;           /* ha_role_t */
    uint32_t    state;          /* ha_state_t */
    uint32_t    priority;
    uint64_t    config_version;
    uint64_t    uptime_sec;
} shsp_heartbeat_t;

/* Election vote */
typedef struct shsp_vote {
    char        candidate_id[64];
    uint32_t    priority;
    uint64_t    config_version;
} shsp_vote_t;

/* State change */
typedef struct shsp_state_change {
    uint32_t    old_role;
    uint32_t    new_role;
    uint32_t    old_state;
    uint32_t    new_state;
    char        reason[128];
} shsp_state_change_t;

/* SHSP Connection */
typedef struct shsp_connection {
    int         socket;
    char        peer_address[64];
    uint16_t    peer_port;
    bool        connected;
    uint32_t    next_sequence;
    uint64_t    last_heartbeat_sent;
    uint64_t    last_heartbeat_recv;
} shsp_connection_t;

/* API */
shield_err_t shsp_connect(shsp_connection_t *conn, const char *address, uint16_t port);
void shsp_disconnect(shsp_connection_t *conn);

shield_err_t shsp_send_heartbeat(shsp_connection_t *conn, const shsp_heartbeat_t *hb);
shield_err_t shsp_send_vote(shsp_connection_t *conn, const shsp_vote_t *vote);
shield_err_t shsp_send_state_change(shsp_connection_t *conn, const shsp_state_change_t *change);

shield_err_t shsp_receive(shsp_connection_t *conn, shsp_header_t *header,
                           void **payload, int timeout_ms);

#endif /* SHIELD_PROTOCOL_SHSP_H */
