/*
 * SENTINEL Shield - Traffic Redirect Protocol (SRP)
 * 
 * Redirects traffic between zones for analysis or blocking
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_common.h"
#include "shield_protocol.h"

/* SRP Message Types */
typedef enum {
    SRP_MSG_REDIRECT_ADD     = 0x01,
    SRP_MSG_REDIRECT_REMOVE  = 0x02,
    SRP_MSG_REDIRECT_LIST    = 0x03,
    SRP_MSG_REDIRECT_RESP    = 0x04,
    SRP_MSG_TRAFFIC          = 0x05,
    SRP_MSG_ACK              = 0x06,
} srp_msg_type_t;

/* Redirect Rule */
typedef struct {
    char     source_zone[SHIELD_MAX_NAME_LEN];
    char     dest_zone[SHIELD_MAX_NAME_LEN];
    uint8_t  match_type;
    char     match_pattern[256];
    uint8_t  action;  /* 0=mirror, 1=redirect, 2=deny */
    bool     enabled;
} srp_redirect_rule_t;

/* SRP Context */
typedef struct {
    int                   socket;
    srp_redirect_rule_t  *rules;
    size_t                rule_count;
    size_t                rule_capacity;
} srp_context_t;

/* Add redirect rule */
shield_err_t srp_add_redirect(srp_context_t *ctx, const char *source,
                               const char *dest, const char *pattern,
                               uint8_t action)
{
    if (!ctx || !source) {
        return SHIELD_ERR_INVALID;
    }
    
    srp_redirect_rule_t rule;
    memset(&rule, 0, sizeof(rule));
    strncpy(rule.source_zone, source, sizeof(rule.source_zone) - 1);
    if (dest) {
        strncpy(rule.dest_zone, dest, sizeof(rule.dest_zone) - 1);
    }
    if (pattern) {
        strncpy(rule.match_pattern, pattern, sizeof(rule.match_pattern) - 1);
    }
    rule.action = action;
    rule.enabled = true;
    
    uint8_t type = SRP_MSG_REDIRECT_ADD;
    if (ctx->socket >= 0) {
        send(ctx->socket, &type, 1, 0);
        send(ctx->socket, &rule, sizeof(rule), 0);
    }
    
    LOG_INFO("SRP: Added redirect %s -> %s", source, dest ? dest : "(block)");
    return SHIELD_OK;
}

/* Remove redirect rule */
shield_err_t srp_remove_redirect(srp_context_t *ctx, const char *source)
{
    if (!ctx || !source) {
        return SHIELD_ERR_INVALID;
    }
    
    struct {
        uint8_t type;
        char source[SHIELD_MAX_NAME_LEN];
    } request = {
        .type = SRP_MSG_REDIRECT_REMOVE
    };
    strncpy(request.source, source, sizeof(request.source) - 1);
    
    if (ctx->socket >= 0) {
        send(ctx->socket, &request, sizeof(request), 0);
    }
    
    return SHIELD_OK;
}

/* Mirror traffic */
shield_err_t srp_mirror_traffic(srp_context_t *ctx, const char *zone,
                                 const void *data, size_t size)
{
    if (!ctx || !zone || !data) {
        return SHIELD_ERR_INVALID;
    }
    
    struct {
        uint8_t type;
        char zone[SHIELD_MAX_NAME_LEN];
        uint32_t size;
    } header = {
        .type = SRP_MSG_TRAFFIC,
        .size = size
    };
    strncpy(header.zone, zone, sizeof(header.zone) - 1);
    
    if (ctx->socket >= 0) {
        send(ctx->socket, &header, sizeof(header), 0);
        send(ctx->socket, data, size, 0);
    }
    
    return SHIELD_OK;
}

/* Initialize SRP */
shield_err_t srp_init(srp_context_t *ctx)
{
    if (!ctx) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(ctx, 0, sizeof(*ctx));
    ctx->socket = -1;
    ctx->rule_capacity = 64;
    ctx->rules = calloc(ctx->rule_capacity, sizeof(srp_redirect_rule_t));
    
    return SHIELD_OK;
}

/* Destroy SRP */
void srp_destroy(srp_context_t *ctx)
{
    if (ctx) {
        if (ctx->socket >= 0) {
            close(ctx->socket);
        }
        free(ctx->rules);
    }
}
