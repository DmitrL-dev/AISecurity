/*
 * SENTINEL Shield - Threat Telemetry Protocol (STT)
 * 
 * Streams threat intelligence data
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_common.h"
#include "shield_protocol.h"
#include "shield_platform.h"

/* STT Events */
typedef enum {
    STT_EVENT_THREAT,
    STT_EVENT_IOC,
    STT_EVENT_SIGNATURE,
} stt_event_t;

/* STT Callback type */
typedef void (*stt_callback_fn)(stt_event_t event, const void *data, void *user_data);

/* STT Message Types */
typedef enum {
    STT_MSG_THREAT_EVENT    = 0x01,
    STT_MSG_THREAT_BATCH    = 0x02,
    STT_MSG_SUBSCRIBE       = 0x03,
    STT_MSG_UNSUBSCRIBE     = 0x04,
    STT_MSG_IOC_UPDATE      = 0x05,
    STT_MSG_SIGNATURE       = 0x06,
    STT_MSG_ACK             = 0x07,
} stt_msg_type_t;

/* Threat Event */
typedef struct {
    char     event_id[64];
    uint8_t  severity;
    char     threat_type[64];
    char     zone[SHIELD_MAX_NAME_LEN];
    char     description[256];
    uint64_t timestamp;
    float    confidence;
} stt_threat_event_t;

/* IOC (Indicator of Compromise) */
typedef struct {
    char     ioc_type[32];   /* ip, domain, hash, pattern */
    char     value[256];
    uint8_t  severity;
    uint64_t valid_until;
} stt_ioc_t;

/* STT Context */
typedef struct {
    int                socket;
    stt_callback_fn    callback;
    void              *user_data;
    bool               subscribed;
} stt_context_t;

/* Report threat event */
shield_err_t stt_report_threat(stt_context_t *ctx, const stt_threat_event_t *event)
{
    if (!ctx || !event) {
        return SHIELD_ERR_INVALID;
    }
    
    uint8_t type = STT_MSG_THREAT_EVENT;
    if (ctx->socket >= 0) {
        send(ctx->socket, (const char*)&type, 1, 0);
        send(ctx->socket, (const char*)event, sizeof(*event), 0);
    }
    
    LOG_DEBUG("STT: Reported threat %s", event->event_id);
    return SHIELD_OK;
}

/* Subscribe to threat feed */
shield_err_t stt_subscribe(stt_context_t *ctx, const char *filter)
{
    if (!ctx) {
        return SHIELD_ERR_INVALID;
    }
    
    struct {
        uint8_t type;
        char filter[256];
    } request = {
        .type = STT_MSG_SUBSCRIBE
    };
    if (filter) {
        strncpy(request.filter, filter, sizeof(request.filter) - 1);
    }
    
    if (ctx->socket >= 0) {
        send(ctx->socket, (const char*)&request, sizeof(request), 0);
    }
    
    ctx->subscribed = true;
    return SHIELD_OK;
}

/* Push IOC update */
shield_err_t stt_push_ioc(stt_context_t *ctx, const stt_ioc_t *ioc)
{
    if (!ctx || !ioc) {
        return SHIELD_ERR_INVALID;
    }
    
    uint8_t type = STT_MSG_IOC_UPDATE;
    if (ctx->socket >= 0) {
        send(ctx->socket, (const char*)&type, 1, 0);
        send(ctx->socket, (const char*)ioc, sizeof(*ioc), 0);
    }
    
    return SHIELD_OK;
}

/* Process incoming */
shield_err_t stt_process(stt_context_t *ctx)
{
    if (!ctx || ctx->socket < 0) {
        return SHIELD_ERR_INVALID;
    }
    
    uint8_t type;
    if (recv(ctx->socket, (char*)&type, 1, MSG_PEEK) <= 0) {
        return SHIELD_ERR_IO;
    }
    
    recv(ctx->socket, (char*)&type, 1, 0);
    
    switch (type) {
    case STT_MSG_THREAT_EVENT: {
        stt_threat_event_t event;
        recv(ctx->socket, (char*)&event, sizeof(event), 0);
        if (ctx->callback) {
            ctx->callback(STT_EVENT_THREAT, &event, ctx->user_data);
        }
        break;
    }
    case STT_MSG_IOC_UPDATE: {
        stt_ioc_t ioc;
        recv(ctx->socket, (char*)&ioc, sizeof(ioc), 0);
        if (ctx->callback) {
            ctx->callback(STT_EVENT_IOC, &ioc, ctx->user_data);
        }
        break;
    }
    default:
        break;
    }
    
    return SHIELD_OK;
}

/* Initialize STT */
shield_err_t stt_init(stt_context_t *ctx)
{
    if (!ctx) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(ctx, 0, sizeof(*ctx));
    ctx->socket = -1;
    
    return SHIELD_OK;
}
