/*
 * SENTINEL Shield - SIEM Export Protocol
 * 
 * Export events to SIEM systems (Splunk, ELK, etc.)
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_common.h"
#include "shield_protocol.h"
#include "shield_platform.h"

/* SIEM Export Formats */
typedef enum {
    SIEM_FORMAT_JSON      = 0x01,
    SIEM_FORMAT_CEF       = 0x02,
    SIEM_FORMAT_LEEF      = 0x03,
    SIEM_FORMAT_SYSLOG    = 0x04,
} siem_format_t;

/* SIEM Transport */
typedef enum {
    SIEM_TRANSPORT_TCP    = 0x01,
    SIEM_TRANSPORT_UDP    = 0x02,
    SIEM_TRANSPORT_HTTP   = 0x03,
    SIEM_TRANSPORT_KAFKA  = 0x04,
} siem_transport_t;

/* SIEM Event */
typedef struct {
    uint64_t    timestamp;
    char        event_type[32];
    uint8_t     severity;
    char        source[SHIELD_MAX_NAME_LEN];
    char        destination[SHIELD_MAX_NAME_LEN];
    char        action[32];
    char        reason[256];
    char        raw_data[1024];
} siem_event_t;

/* SIEM Config */
typedef struct {
    char            endpoint[256];
    uint16_t        port;
    siem_format_t   format;
    siem_transport_t transport;
    char            token[256];
    bool            tls_enabled;
    bool            batch_enabled;
    uint32_t        batch_size;
    uint32_t        flush_interval_ms;
} siem_config_t;

/* SIEM Context */
typedef struct {
    int             socket;
    siem_config_t   config;
    siem_event_t   *batch_buffer;
    size_t          batch_count;
    uint64_t        last_flush;
    uint64_t        events_sent;
} siem_context_t;

/* Forward declaration */
shield_err_t siem_flush(siem_context_t *ctx);

/* Format event as CEF */
static int format_cef(const siem_event_t *event, char *buf, size_t size)
{
    return snprintf(buf, size,
        "CEF:0|SENTINEL|Shield|1.2.0|%s|%s|%d|src=%s dst=%s act=%s reason=%s",
        event->event_type,
        event->event_type,
        event->severity,
        event->source,
        event->destination,
        event->action,
        event->reason);
}

/* Format event as JSON */
static int format_json(const siem_event_t *event, char *buf, size_t size)
{
    return snprintf(buf, size,
        "{\"timestamp\":%lu,\"event_type\":\"%s\",\"severity\":%d,"
        "\"source\":\"%s\",\"destination\":\"%s\",\"action\":\"%s\","
        "\"reason\":\"%s\"}",
        (unsigned long)event->timestamp,
        event->event_type,
        event->severity,
        event->source,
        event->destination,
        event->action,
        event->reason);
}

/* Send event */
shield_err_t siem_send_event(siem_context_t *ctx, const siem_event_t *event)
{
    if (!ctx || !event) {
        return SHIELD_ERR_INVALID;
    }
    
    char buf[4096];
    int len = 0;
    
    switch (ctx->config.format) {
    case SIEM_FORMAT_CEF:
        len = format_cef(event, buf, sizeof(buf));
        break;
    case SIEM_FORMAT_JSON:
    default:
        len = format_json(event, buf, sizeof(buf));
        break;
    }
    
    if (ctx->config.batch_enabled) {
        /* Add to batch */
        if (ctx->batch_count < ctx->config.batch_size) {
            ctx->batch_buffer[ctx->batch_count++] = *event;
            
            if (ctx->batch_count >= ctx->config.batch_size) {
                return siem_flush(ctx);
            }
        }
    } else {
        /* Send immediately */
        if (ctx->socket >= 0) {
            send(ctx->socket, (const char*)buf, len, 0);
            send(ctx->socket, "\n", 1, 0);
        }
    }
    
    ctx->events_sent++;
    return SHIELD_OK;
}

/* Flush batch */
shield_err_t siem_flush(siem_context_t *ctx)
{
    if (!ctx || ctx->batch_count == 0) {
        return SHIELD_OK;
    }
    
    char buf[4096];
    
    for (size_t i = 0; i < ctx->batch_count; i++) {
        int len;
        switch (ctx->config.format) {
        case SIEM_FORMAT_CEF:
            len = format_cef(&ctx->batch_buffer[i], buf, sizeof(buf));
            break;
        default:
            len = format_json(&ctx->batch_buffer[i], buf, sizeof(buf));
            break;
        }
        
        if (ctx->socket >= 0) {
            send(ctx->socket, (const char*)buf, len, 0);
            send(ctx->socket, "\n", 1, 0);
        }
    }
    
    ctx->batch_count = 0;
    ctx->last_flush = time(NULL);
    
    return SHIELD_OK;
}

/* Initialize SIEM */
shield_err_t siem_init(siem_context_t *ctx, const siem_config_t *config)
{
    if (!ctx || !config) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(ctx, 0, sizeof(*ctx));
    ctx->config = *config;
    ctx->socket = -1;
    
    if (config->batch_enabled) {
        ctx->batch_buffer = calloc(config->batch_size, sizeof(siem_event_t));
    }
    
    return SHIELD_OK;
}

/* Destroy SIEM */
void siem_destroy(siem_context_t *ctx)
{
    if (ctx) {
        siem_flush(ctx);
        if (ctx->socket >= 0) {
#ifdef SHIELD_PLATFORM_WINDOWS
            closesocket(ctx->socket);
#else
            close(ctx->socket);
#endif
        }
        free(ctx->batch_buffer);
    }
}
