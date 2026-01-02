/*
 * SENTINEL Shield - Shield-Gateway Protocol (SGP)
 * 
 * Communication between Shield and external API gateways
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_common.h"
#include "shield_protocol.h"

/* SGP Message Types */
typedef enum {
    SGP_MSG_CONNECT        = 0x01,
    SGP_MSG_DISCONNECT     = 0x02,
    SGP_MSG_EVALUATE       = 0x03,
    SGP_MSG_RESULT         = 0x04,
    SGP_MSG_CONFIG_SYNC    = 0x05,
    SGP_MSG_HEALTH_CHECK   = 0x06,
    SGP_MSG_HEALTH_RESP    = 0x07,
    SGP_MSG_ERROR          = 0x08,
} sgp_msg_type_t;

/* Evaluation Request */
typedef struct {
    char        request_id[64];
    char        zone[SHIELD_MAX_NAME_LEN];
    uint8_t     direction;
    uint32_t    data_size;
    char        metadata[512];  /* JSON */
} sgp_eval_request_t;

/* Evaluation Result */
typedef struct {
    char        request_id[64];
    uint8_t     action;
    float       threat_score;
    char        reason[256];
    char        matched_rules[256];
    uint64_t    eval_time_ns;
} sgp_eval_result_t;

/* SGP Context */
typedef struct {
    int         socket;
    char        gateway_id[SHIELD_MAX_NAME_LEN];
    bool        connected;
    uint64_t    requests_handled;
} sgp_context_t;

/* Connect to gateway */
shield_err_t sgp_connect(sgp_context_t *ctx, const char *gateway_id)
{
    if (!ctx || !gateway_id) {
        return SHIELD_ERR_INVALID;
    }
    
    strncpy(ctx->gateway_id, gateway_id, sizeof(ctx->gateway_id) - 1);
    
    struct {
        uint8_t type;
        char gateway_id[SHIELD_MAX_NAME_LEN];
    } msg = {
        .type = SGP_MSG_CONNECT
    };
    strncpy(msg.gateway_id, gateway_id, sizeof(msg.gateway_id) - 1);
    
    if (ctx->socket >= 0) {
        send(ctx->socket, &msg, sizeof(msg), 0);
    }
    
    ctx->connected = true;
    LOG_INFO("SGP: Connected to gateway %s", gateway_id);
    return SHIELD_OK;
}

/* Handle evaluation request from gateway */
shield_err_t sgp_handle_request(sgp_context_t *ctx, shield_context_t *shield_ctx)
{
    if (!ctx || ctx->socket < 0) {
        return SHIELD_ERR_INVALID;
    }
    
    sgp_eval_request_t request;
    if (recv(ctx->socket, &request, sizeof(request), 0) <= 0) {
        return SHIELD_ERR_IO;
    }
    
    /* Read data */
    void *data = malloc(request.data_size);
    recv(ctx->socket, data, request.data_size, 0);
    
    /* Evaluate */
    evaluation_result_t eval_result;
    shield_evaluate(shield_ctx, data, request.data_size, request.zone,
                    request.direction, &eval_result);
    
    /* Build response */
    sgp_eval_result_t result = {
        .action = eval_result.action,
        .threat_score = eval_result.threat_score,
        .eval_time_ns = eval_result.eval_time_ns
    };
    strncpy(result.request_id, request.request_id, sizeof(result.request_id) - 1);
    strncpy(result.reason, eval_result.reason, sizeof(result.reason) - 1);
    
    uint8_t type = SGP_MSG_RESULT;
    send(ctx->socket, &type, 1, 0);
    send(ctx->socket, &result, sizeof(result), 0);
    
    free(data);
    ctx->requests_handled++;
    
    return SHIELD_OK;
}

/* Sync config to gateway */
shield_err_t sgp_sync_config(sgp_context_t *ctx, const char *config_json)
{
    if (!ctx || !config_json) {
        return SHIELD_ERR_INVALID;
    }
    
    size_t len = strlen(config_json);
    
    struct {
        uint8_t type;
        uint32_t length;
    } header = {
        .type = SGP_MSG_CONFIG_SYNC,
        .length = len
    };
    
    if (ctx->socket >= 0) {
        send(ctx->socket, &header, sizeof(header), 0);
        send(ctx->socket, config_json, len, 0);
    }
    
    return SHIELD_OK;
}

/* Initialize SGP */
shield_err_t sgp_init(sgp_context_t *ctx)
{
    if (!ctx) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(ctx, 0, sizeof(*ctx));
    ctx->socket = -1;
    
    return SHIELD_OK;
}
