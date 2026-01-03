/*
 * SENTINEL IMMUNE — Communication Protocol
 * 
 * Agent-to-Hive secure communication.
 * OUTPUT ONLY — Agent never receives commands.
 */

#ifndef IMMUNE_PROTOCOL_H
#define IMMUNE_PROTOCOL_H

#include <stdint.h>

/* Protocol version */
#define IMMUNE_PROTO_VERSION 1

/* Message types */
typedef enum {
    MSG_HEARTBEAT   = 0x01,
    MSG_THREAT      = 0x02,
    MSG_STATS       = 0x03,
    MSG_REGISTER    = 0x04,
    MSG_SIGNATURE   = 0x05
} msg_type_t;

/* Heartbeat interval (seconds) */
#define HEARTBEAT_INTERVAL 60

/* Maximum message size */
#define MAX_MSG_SIZE 4096

/* Message header (fixed size, 32 bytes) */
typedef struct __attribute__((packed)) {
    uint8_t     version;
    uint8_t     type;
    uint16_t    flags;
    uint32_t    length;
    uint64_t    timestamp;
    uint64_t    agent_id;
    uint32_t    sequence;
    uint32_t    checksum;
} msg_header_t;

/* Threat report message */
typedef struct __attribute__((packed)) {
    msg_header_t header;
    uint8_t      threat_level;
    uint8_t      threat_type;
    uint16_t     sig_len;
    uint32_t     pid;
    uint32_t     uid;
    char         signature[256];
} msg_threat_t;

/* Statistics message */
typedef struct __attribute__((packed)) {
    msg_header_t header;
    uint64_t     total_scans;
    uint64_t     total_threats;
    uint64_t     total_blocked;
    uint64_t     uptime_seconds;
    uint32_t     memory_entries;
    uint32_t     cpu_usage;
} msg_stats_t;

/* Registration message */
typedef struct __attribute__((packed)) {
    msg_header_t header;
    char         hostname[64];
    char         os_type[32];
    char         version[16];
    uint32_t     ip_addr;
} msg_register_t;

/* Signature request (pull from Hive) */
typedef struct __attribute__((packed)) {
    msg_header_t header;
    uint64_t     last_sync;
    uint32_t     have_count;
} msg_sig_request_t;

/* CRC32 checksum */
uint32_t immune_crc32(const void *data, size_t len);

/* Message functions */
int immune_msg_send(void *msg, size_t len);
int immune_msg_heartbeat(void);
int immune_msg_threat(uint8_t level, uint8_t type, const char *sig);
int immune_msg_stats(void);
int immune_msg_register(void);

/* Connection management */
int immune_connect_init(const char *hive_addr, uint16_t port);
void immune_connect_close(void);
int immune_connect_status(void);

#endif /* IMMUNE_PROTOCOL_H */
