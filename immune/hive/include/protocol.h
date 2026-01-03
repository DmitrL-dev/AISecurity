/*
 * SENTINEL IMMUNE — Hive Protocol Definition
 * 
 * Wire protocol for agent-hive communication.
 */

#ifndef IMMUNE_PROTOCOL_H
#define IMMUNE_PROTOCOL_H

#include <stdint.h>

/* Protocol constants */
#define IMMUNE_MAGIC        0x494D4D55  /* "IMMU" */
#define PROTOCOL_VERSION    1

/* Message types */
typedef enum {
    MSG_REGISTER = 1,       /* Agent registration */
    MSG_REGISTER_ACK,       /* Registration acknowledgment */
    MSG_HEARTBEAT,          /* Agent heartbeat */
    MSG_THREAT,             /* Threat report */
    MSG_THREAT_ACK,         /* Threat acknowledgment */
    MSG_SIGNATURE,          /* New signature */
    MSG_GET_SIGNATURES,     /* Request signatures */
    MSG_SIGNATURES,         /* Signature list */
    MSG_COMMAND,            /* Command from Hive */
    MSG_RESPONSE,           /* Response from Agent */
    MSG_STATS,              /* Agent statistics */
    MSG_SHUTDOWN            /* Shutdown signal */
} msg_type_t;

/* Base message header */
typedef struct __attribute__((packed)) {
    uint32_t    magic;      /* IMMUNE_MAGIC */
    uint8_t     version;    /* Protocol version */
    uint8_t     type;       /* msg_type_t */
    uint16_t    length;     /* Payload length */
    uint8_t     payload[0]; /* Variable payload */
} immune_msg_t;

/* Registration message */
typedef struct __attribute__((packed)) {
    char        hostname[256];
    char        os_type[32];
    char        version[16];
    uint64_t    capabilities;
} msg_register_t;

/* Threat report message */
typedef struct __attribute__((packed)) {
    uint32_t    agent_id;
    uint8_t     level;      /* threat_level_t */
    uint8_t     type;       /* threat_type_t */
    uint16_t    sig_len;
    char        signature[256];
    char        details[512];
} msg_threat_t;

/* Threat acknowledgment */
typedef struct __attribute__((packed)) {
    uint64_t    event_id;
    uint8_t     action;     /* response_action_t */
} msg_threat_ack_t;

/* Signature message */
typedef struct __attribute__((packed)) {
    uint32_t    source_agent;
    uint8_t     type;       /* threat_type_t */
    uint8_t     severity;   /* threat_level_t */
    uint16_t    pattern_len;
    char        pattern[256];
} msg_signature_t;

/* Statistics message */
typedef struct __attribute__((packed)) {
    uint32_t    agent_id;
    uint64_t    scans_total;
    uint64_t    threats_detected;
    uint64_t    memory_entries;
    uint32_t    uptime_seconds;
} msg_stats_t;

/* Command message */
typedef struct __attribute__((packed)) {
    uint8_t     command;
    uint16_t    arg_len;
    uint8_t     args[0];
} msg_command_t;

/* Commands */
typedef enum {
    CMD_SCAN_ALL = 1,       /* Force full scan */
    CMD_CLEAR_MEMORY,       /* Clear threat memory */
    CMD_UPDATE_PATTERNS,    /* Update patterns */
    CMD_ISOLATE,            /* Isolate network */
    CMD_SHUTDOWN,           /* Shutdown agent */
    CMD_RESTART             /* Restart agent */
} command_t;

/* Helper macros */
#define MSG_SIZE(payload_len) (sizeof(immune_msg_t) + (payload_len))

#endif /* IMMUNE_PROTOCOL_H */
