/*
 * SENTINEL Shield - SBP (Shield-Brain Protocol) Header
 * 
 * Protocol for communication between Shield and Brain components
 */

#ifndef SHIELD_PROTOCOL_SBP_H
#define SHIELD_PROTOCOL_SBP_H

#include "shield_common.h"

/* SBP Message Types */
typedef enum sbp_msg_type {
    /* Shield -> Brain */
    SBP_MSG_ANALYZE_REQUEST = 0x01,     /* Request deep analysis */
    SBP_MSG_THREAT_REPORT = 0x02,       /* Report detected threat */
    SBP_MSG_STATS_SYNC = 0x03,          /* Sync statistics */
    
    /* Brain -> Shield */
    SBP_MSG_ANALYZE_RESPONSE = 0x11,    /* Analysis result */
    SBP_MSG_BLOCKLIST_UPDATE = 0x12,    /* Update blocklist */
    SBP_MSG_CONFIG_UPDATE = 0x13,       /* Update configuration */
    SBP_MSG_SIGNATURE_UPDATE = 0x14,    /* Update signatures */
    
    /* Bidirectional */
    SBP_MSG_HEARTBEAT = 0x20,           /* Keep-alive */
    SBP_MSG_ACK = 0x21,                 /* Acknowledgement */
} sbp_msg_type_t;

/* Threat severity levels */
typedef enum sbp_severity {
    SBP_SEVERITY_INFO = 0,
    SBP_SEVERITY_LOW = 1,
    SBP_SEVERITY_MEDIUM = 2,
    SBP_SEVERITY_HIGH = 3,
    SBP_SEVERITY_CRITICAL = 4,
} sbp_severity_t;

/* SBP Header (fixed size: 32 bytes) */
typedef struct __attribute__((packed)) sbp_header {
    uint32_t    magic;          /* 0x53425001 = "SBP\x01" */
    uint16_t    version;        /* Protocol version */
    uint16_t    msg_type;       /* Message type */
    uint32_t    sequence;       /* Sequence number */
    uint32_t    payload_len;    /* Payload length */
    uint64_t    timestamp;      /* Unix timestamp (ms) */
    uint32_t    flags;          /* Flags */
    uint32_t    reserved;       /* Reserved */
} sbp_header_t;

/* Analyze request payload */
typedef struct sbp_analyze_request {
    uint32_t    zone_id;
    uint32_t    direction;      /* DIRECTION_INPUT or DIRECTION_OUTPUT */
    char        session_id[64];
    char        source_ip[46];
    /* Followed by payload data */
} sbp_analyze_request_t;

/* Analyze response payload */
typedef struct sbp_analyze_response {
    uint32_t    sequence;       /* Original request sequence */
    uint32_t    action;         /* Recommended action */
    float       confidence;     /* Confidence score */
    char        reason[256];
    char        details[512];
} sbp_analyze_response_t;

/* Threat report payload */
typedef struct sbp_threat_report {
    uint32_t        zone_id;
    sbp_severity_t  severity;
    char            threat_type[64];
    char            description[256];
    char            evidence[512];
    uint64_t        timestamp;
} sbp_threat_report_t;

/* Blocklist update payload */
typedef struct sbp_blocklist_update {
    uint32_t    count;          /* Number of hashes */
    uint32_t    operation;      /* 0=replace, 1=add, 2=remove */
    /* Followed by: uint32_t hashes[count] */
} sbp_blocklist_update_t;

/* SBP Connection */
typedef struct sbp_connection {
    int             socket;
    char            host[256];
    uint16_t        port;
    bool            connected;
    uint32_t        next_sequence;
    uint64_t        last_heartbeat;
    
    /* TLS (optional) */
    void            *tls_ctx;
} sbp_connection_t;

/* API */
shield_err_t sbp_connect(sbp_connection_t *conn, const char *host, uint16_t port);
void sbp_disconnect(sbp_connection_t *conn);
bool sbp_is_connected(sbp_connection_t *conn);

shield_err_t sbp_send_analyze_request(sbp_connection_t *conn,
                                       uint32_t zone_id,
                                       rule_direction_t direction,
                                       const char *session_id,
                                       const void *data, size_t len);

shield_err_t sbp_send_threat_report(sbp_connection_t *conn,
                                     const sbp_threat_report_t *report);

shield_err_t sbp_send_heartbeat(sbp_connection_t *conn);

shield_err_t sbp_receive(sbp_connection_t *conn, 
                          sbp_header_t *header,
                          void **payload, size_t *payload_len,
                          int timeout_ms);

void sbp_free_payload(void *payload);

#endif /* SHIELD_PROTOCOL_SBP_H */
