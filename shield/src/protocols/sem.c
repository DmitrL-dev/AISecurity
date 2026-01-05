/*
 * SENTINEL Shield - Event Manager Protocol (SEM)
 * 
 * Centralized event management and correlation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_common.h"
#include "shield_protocol.h"
#include "shield_platform.h"

/* SEM Message Types */
typedef enum {
    SEM_MSG_EVENT           = 0x01,
    SEM_MSG_EVENT_BATCH     = 0x02,
    SEM_MSG_QUERY           = 0x03,
    SEM_MSG_QUERY_RESP      = 0x04,
    SEM_MSG_SUBSCRIBE       = 0x05,
    SEM_MSG_CORRELATION     = 0x06,
    SEM_MSG_ALERT           = 0x07,
} sem_msg_type_t;

/* Event Types */
typedef enum {
    SEM_EVENT_REQUEST       = 0x01,
    SEM_EVENT_BLOCK         = 0x02,
    SEM_EVENT_ALERT         = 0x03,
    SEM_EVENT_CONFIG_CHANGE = 0x04,
    SEM_EVENT_HA_CHANGE     = 0x05,
    SEM_EVENT_ERROR         = 0x06,
} sem_event_type_t;

/* Event Message */
typedef struct {
    char        event_id[64];
    uint8_t     event_type;
    uint8_t     severity;
    char        source[SHIELD_MAX_NAME_LEN];
    char        message[256];
    char        details[1024];  /* JSON */
    uint64_t    timestamp;
} sem_event_t;

/* Correlation Rule */
typedef struct {
    char        rule_id[64];
    char        pattern[256];
    uint32_t    threshold;
    uint32_t    window_seconds;
    uint8_t     action;
} sem_correlation_rule_t;

/* SEM Context */
typedef struct {
    int             socket;
    sem_callback_t  callback;
    void           *user_data;
    uint32_t        event_count;
} sem_context_t;

/* Send event */
shield_err_t sem_send_event(sem_context_t *ctx, const sem_event_t *event)
{
    if (!ctx || !event) {
        return SHIELD_ERR_INVALID;
    }
    
    uint8_t type = SEM_MSG_EVENT;
    if (ctx->socket >= 0) {
        send(ctx->socket, (const char*)&type, 1, 0);
        send(ctx->socket, (const char*)event, sizeof(*event), 0);
    }
    
    ctx->event_count++;
    return SHIELD_OK;
}

/* Send batch of events */
shield_err_t sem_send_batch(sem_context_t *ctx, const sem_event_t *events, size_t count)
{
    if (!ctx || !events || count == 0) {
        return SHIELD_ERR_INVALID;
    }
    
    struct {
        uint8_t type;
        uint32_t count;
    } header = {
        .type = SEM_MSG_EVENT_BATCH,
        .count = count
    };
    
    if (ctx->socket >= 0) {
        send(ctx->socket, (const char*)&header, sizeof(header), 0);
        send(ctx->socket, (const char*)events, sizeof(sem_event_t) * count, 0);
    }
    
    ctx->event_count += count;
    return SHIELD_OK;
}

/* Query events */
shield_err_t sem_query(sem_context_t *ctx, const char *filter,
                        uint64_t start_time, uint64_t end_time)
{
    if (!ctx) {
        return SHIELD_ERR_INVALID;
    }
    
    struct {
        uint8_t type;
        char filter[256];
        uint64_t start;
        uint64_t end;
    } query = {
        .type = SEM_MSG_QUERY,
        .start = start_time,
        .end = end_time
    };
    if (filter) {
        strncpy(query.filter, filter, sizeof(query.filter) - 1);
    }
    
    if (ctx->socket >= 0) {
        send(ctx->socket, (const char*)&query, sizeof(query), 0);
    }
    
    return SHIELD_OK;
}

/* Add correlation rule */
shield_err_t sem_add_correlation(sem_context_t *ctx, const sem_correlation_rule_t *rule)
{
    if (!ctx || !rule) {
        return SHIELD_ERR_INVALID;
    }
    
    uint8_t type = SEM_MSG_CORRELATION;
    if (ctx->socket >= 0) {
        send(ctx->socket, (const char*)&type, 1, 0);
        send(ctx->socket, (const char*)rule, sizeof(*rule), 0);
    }
    
    return SHIELD_OK;
}

/* Initialize SEM */
shield_err_t sem_init(sem_context_t *ctx)
{
    if (!ctx) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(ctx, 0, sizeof(*ctx));
    ctx->socket = -1;
    
    return SHIELD_OK;
}
