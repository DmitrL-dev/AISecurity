/*
 * SENTINEL Shield - ZDP (Zone Discovery Protocol) Implementation
 * 
 * Protocol for auto-discovering LLM/RAG/Agent endpoints
 */

#ifndef SHIELD_PROTOCOL_ZDP_H
#define SHIELD_PROTOCOL_ZDP_H

#include "shield_common.h"

/* ZDP Message Types */
typedef enum zdp_msg_type {
    ZDP_MSG_ANNOUNCE = 0x01,    /* Zone announces itself */
    ZDP_MSG_QUERY = 0x02,       /* Query for zones */
    ZDP_MSG_RESPONSE = 0x03,    /* Response to query */
    ZDP_MSG_LEAVE = 0x04,       /* Zone is leaving */
} zdp_msg_type_t;

/* ZDP Zone Capabilities */
typedef enum zdp_capability {
    ZDP_CAP_CHAT = 0x0001,          /* Chat completion */
    ZDP_CAP_COMPLETION = 0x0002,    /* Text completion */
    ZDP_CAP_EMBEDDING = 0x0004,     /* Embeddings */
    ZDP_CAP_IMAGE = 0x0008,         /* Image generation */
    ZDP_CAP_AUDIO = 0x0010,         /* Audio processing */
    ZDP_CAP_TOOL_CALL = 0x0020,     /* Tool calling */
    ZDP_CAP_STREAMING = 0x0040,     /* Supports streaming */
    ZDP_CAP_FUNCTION = 0x0080,      /* Function calling */
} zdp_capability_t;

/* ZDP Header (fixed size: 16 bytes) */
typedef struct __attribute__((packed)) zdp_header {
    uint32_t    magic;          /* 0x5A445001 = "ZDP\x01" */
    uint16_t    version;        /* Protocol version */
    uint16_t    msg_type;       /* Message type */
    uint32_t    payload_len;    /* Payload length */
    uint32_t    reserved;
} zdp_header_t;

/* Zone announcement payload */
typedef struct zdp_announce {
    char            zone_id[64];
    char            zone_name[64];
    zone_type_t     zone_type;
    uint32_t        capabilities;
    char            endpoint[256];
    uint16_t        port;
    uint16_t        priority;
    uint32_t        ttl_seconds;
} zdp_announce_t;

/* Zone query payload */
typedef struct zdp_query {
    zone_type_t     type_filter;     /* ZONE_TYPE_UNKNOWN = any */
    uint32_t        cap_filter;      /* Capabilities required */
} zdp_query_t;

/* ZDP Discovery State */
typedef struct zdp_discovery {
    struct {
        zdp_announce_t  info;
        uint64_t        last_seen;
        bool            active;
    } zones[SHIELD_MAX_ZONES];
    int             zone_count;
    
    int             socket;
    uint16_t        port;
    bool            running;
} zdp_discovery_t;

/* API */
shield_err_t zdp_init(zdp_discovery_t *disc, uint16_t port);
void zdp_destroy(zdp_discovery_t *disc);

shield_err_t zdp_announce(zdp_discovery_t *disc, const zdp_announce_t *zone);
shield_err_t zdp_leave(zdp_discovery_t *disc, const char *zone_id);
shield_err_t zdp_query(zdp_discovery_t *disc, zone_type_t type, uint32_t caps);

/* Process incoming ZDP messages */
shield_err_t zdp_process(zdp_discovery_t *disc, int timeout_ms);

/* Get discovered zones */
int zdp_get_zones(zdp_discovery_t *disc, zdp_announce_t *zones, int max_zones);

/* Cleanup expired zones */
void zdp_cleanup_expired(zdp_discovery_t *disc);

#endif /* SHIELD_PROTOCOL_ZDP_H */
