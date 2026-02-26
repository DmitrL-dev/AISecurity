/*
 * SENTINEL Shield - Protocol Base
 * 
 * Common protocol definitions and utilities
 */

#ifndef SHIELD_PROTOCOL_H
#define SHIELD_PROTOCOL_H

#include "shield_common.h"
#include <stddef.h>
#include <stdbool.h>

/* Protocol types */
typedef enum {
    PROTOCOL_TYPE_UNKNOWN = 0,
    PROTOCOL_TYPE_STP,      /* SENTINEL Transport Protocol */
    PROTOCOL_TYPE_SBP,      /* SENTINEL Binary Protocol */
    PROTOCOL_TYPE_SHSP,     /* SENTINEL HA Sync Protocol */
    PROTOCOL_TYPE_SSRP,     /* SENTINEL Secure Replication */
    PROTOCOL_TYPE_ZDP,      /* Zone Discovery Protocol */
    PROTOCOL_TYPE_SAF,      /* SENTINEL Audit Format */
    PROTOCOL_TYPE_SLLM,     /* SENTINEL LLM Protocol */
    PROTOCOL_TYPE_SEM,      /* SENTINEL Event Messaging */
    PROTOCOL_TYPE_SGP,      /* SENTINEL Graph Protocol */
    PROTOCOL_TYPE_SIEM,     /* SENTINEL SIEM Integration */
    PROTOCOL_TYPE_SLA,      /* SENTINEL Logging & Auditing */
    PROTOCOL_TYPE_SMRP,     /* SENTINEL Message Routing */
    PROTOCOL_TYPE_SPP,      /* SENTINEL Pipeline Protocol */
    PROTOCOL_TYPE_SQP,      /* SENTINEL Query Protocol */
    PROTOCOL_TYPE_SRP,      /* SENTINEL Replication Protocol */
    PROTOCOL_TYPE_SSIGP,    /* SENTINEL Signature Protocol */
    PROTOCOL_TYPE_STLS,     /* SENTINEL TLS Protocol */
    PROTOCOL_TYPE_STT,      /* SENTINEL Telemetry Transport */
    PROTOCOL_TYPE_SZAA,     /* SENTINEL Zero-Trust AA */
    PROTOCOL_TYPE_ZHP,      /* Zone Health Protocol */
    PROTOCOL_TYPE_ZRP,      /* Zone Routing Protocol */
} protocol_type_t;

/* Protocol state */
typedef enum {
    PROTOCOL_STATE_IDLE = 0,
    PROTOCOL_STATE_CONNECTING,
    PROTOCOL_STATE_CONNECTED,
    PROTOCOL_STATE_AUTHENTICATING,
    PROTOCOL_STATE_READY,
    PROTOCOL_STATE_ERROR,
    PROTOCOL_STATE_CLOSED
} protocol_state_t;

/* Protocol config */
typedef struct protocol_config {
    protocol_type_t     type;
    char                host[256];
    uint16_t            port;
    bool                use_tls;
    uint32_t            timeout_ms;
    uint32_t            retry_count;
} protocol_config_t;

/* Protocol context */
typedef struct protocol_context {
    protocol_type_t     type;
    protocol_state_t    state;
    int                 socket;
    protocol_config_t   config;
    
    /* Statistics */
    uint64_t            bytes_sent;
    uint64_t            bytes_received;
    uint64_t            messages_sent;
    uint64_t            messages_received;
    uint64_t            errors;
} protocol_context_t;

/* Message header */
typedef struct protocol_header {
    uint32_t            magic;
    uint8_t             version;
    uint8_t             type;
    uint16_t            flags;
    uint32_t            length;
    uint32_t            sequence;
    uint32_t            checksum;
} protocol_header_t;

#define PROTOCOL_MAGIC 0x53454E54  /* "SENT" */
#define PROTOCOL_VERSION 1

/* Protocol API */
shield_err_t protocol_init(protocol_context_t *ctx, const protocol_config_t *config);
void protocol_destroy(protocol_context_t *ctx);

shield_err_t protocol_connect(protocol_context_t *ctx);
void protocol_disconnect(protocol_context_t *ctx);

shield_err_t protocol_send(protocol_context_t *ctx, const void *data, size_t len);
shield_err_t protocol_receive(protocol_context_t *ctx, void *buffer, size_t max_len, size_t *received);

const char *protocol_type_to_string(protocol_type_t type);
protocol_type_t protocol_type_from_string(const char *str);

/* Protocol-specific callback types */
typedef void (*sem_callback_t)(const void *event, size_t len, void *user_data);
typedef void (*spp_callback_t)(const void *data, size_t len, void *user_data);
typedef void (*stt_callback_t)(const void *telemetry, size_t len, void *user_data);
typedef void (*zrp_callback_t)(const char *zone, const void *route, void *user_data);
typedef void (*sgp_callback_t)(const void *graph, size_t len, void *user_data);
typedef void (*smrp_callback_t)(const void *msg, size_t len, void *user_data);
typedef void (*sqp_callback_t)(const void *query, size_t len, void *user_data);
typedef void (*ssigp_callback_t)(const void *sig, size_t len, void *user_data);

#endif /* SHIELD_PROTOCOL_H */
