/*
 * SENTINEL IMMUNE — CAPS Messaging Header
 */

#ifndef IMMUNE_CAPS_H
#define IMMUNE_CAPS_H

#include <stdint.h>

/* Message types */
typedef enum {
    MSG_THREAT_REPORT,
    MSG_HEARTBEAT,
    MSG_CONFIG_UPDATE,
    MSG_PATTERN_SYNC,
    MSG_AGENT_STATUS,
    MSG_SCAN_REQUEST,
    MSG_SCAN_RESULT
} message_type_t;

/* Message structure */
typedef struct {
    message_type_t  type;
    uint32_t        agent_id;
    uint32_t        seq_num;
    uint32_t        payload_len;
    uint64_t        timestamp;
    uint8_t         payload[4064];
} immune_message_t;

/* Initialization */
int caps_init(uint32_t agent_id);
void caps_shutdown(void);

/* Async messaging */
int caps_report_threat_async(uint32_t threat_level, const char *details);
int caps_heartbeat_async(void);
int caps_poll_message(immune_message_t *msg);

/* Stats */
void caps_stats(int *pending_out, int *pending_in);

#endif /* IMMUNE_CAPS_H */
