/*
 * SENTINEL Shield - Zone Health Protocol (ZHP)
 * 
 * Monitors zone health and reports status
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "shield_common.h"
#include "shield_protocol.h"
#include "shield_platform.h"
#ifndef SHIELD_PLATFORM_WINDOWS
#include <pthread.h>
#include <unistd.h>
#endif

/* ZHP Message Types */
typedef enum {
    ZHP_MSG_HEALTH_CHECK  = 0x01,
    ZHP_MSG_HEALTH_RESP   = 0x02,
    ZHP_MSG_ALERT         = 0x03,
    ZHP_MSG_SUBSCRIBE     = 0x04,
    ZHP_MSG_UNSUBSCRIBE   = 0x05,
} zhp_msg_type_t;

/* Zone Health Status */
typedef enum {
    ZHP_STATUS_HEALTHY    = 0,
    ZHP_STATUS_DEGRADED   = 1,
    ZHP_STATUS_UNHEALTHY  = 2,
    ZHP_STATUS_UNKNOWN    = 3,
} zhp_status_t;

/* Health Response */
typedef struct {
    char        zone_name[SHIELD_MAX_NAME_LEN];
    uint8_t     status;
    uint64_t    requests_total;
    uint64_t    requests_blocked;
    float       latency_avg_ms;
    float       latency_p99_ms;
    uint64_t    last_check;
} zhp_health_response_t;

/* ZHP Context */
typedef struct {
    int         socket;
    uint32_t    check_interval_ms;
    bool        running;
    #ifndef SHIELD_PLATFORM_WINDOWS
    pthread_t   thread;
#else
    HANDLE      thread;
#endif
} zhp_context_t;

/* Check zone health */
shield_err_t zhp_check_zone(zhp_context_t *ctx, const char *zone_name, 
                             zhp_health_response_t *out)
{
    if (!ctx || !zone_name || !out) {
        return SHIELD_ERR_INVALID;
    }
    
    /* Build request */
    struct {
        uint8_t type;
        char zone[SHIELD_MAX_NAME_LEN];
    } request = {
        .type = ZHP_MSG_HEALTH_CHECK
    };
    strncpy(request.zone, zone_name, sizeof(request.zone) - 1);
    
    if (ctx->socket >= 0) {
        send(ctx->socket, (const char*)&request, sizeof(request), 0);
        
        /* Wait for response */
        uint8_t resp_type;
        recv(ctx->socket, (char*)&resp_type, 1, 0);
        if (resp_type == ZHP_MSG_HEALTH_RESP) {
            recv(ctx->socket, (char*)out, sizeof(*out), 0);
        }
    }
    
    return SHIELD_OK;
}

/* Subscribe to health alerts */
shield_err_t zhp_subscribe(zhp_context_t *ctx, const char *zone_name)
{
    if (!ctx || !zone_name) {
        return SHIELD_ERR_INVALID;
    }
    
    struct {
        uint8_t type;
        char zone[SHIELD_MAX_NAME_LEN];
    } request = {
        .type = ZHP_MSG_SUBSCRIBE
    };
    strncpy(request.zone, zone_name, sizeof(request.zone) - 1);
    
    if (ctx->socket >= 0) {
        send(ctx->socket, (const char*)&request, sizeof(request), 0);
    }
    
    return SHIELD_OK;
}

/* Send alert */
shield_err_t zhp_send_alert(zhp_context_t *ctx, const char *zone_name,
                             zhp_status_t status, const char *message)
{
    if (!ctx || !zone_name) {
        return SHIELD_ERR_INVALID;
    }
    
    struct {
        uint8_t type;
        char zone[SHIELD_MAX_NAME_LEN];
        uint8_t status;
        char message[256];
    } alert = {
        .type = ZHP_MSG_ALERT,
        .status = status
    };
    strncpy(alert.zone, zone_name, sizeof(alert.zone) - 1);
    if (message) {
        strncpy(alert.message, message, sizeof(alert.message) - 1);
    }
    
    if (ctx->socket >= 0) {
        send(ctx->socket, (const char*)&alert, sizeof(alert), 0);
    }
    
    LOG_INFO("ZHP: Alert for zone %s: status=%d, %s", zone_name, status, message);
    return SHIELD_OK;
}

/* Health check thread */
static void* zhp_health_thread(void *arg)
{
    zhp_context_t *ctx = (zhp_context_t *)arg;
    
    while (ctx->running) {
        /* Periodic health checks would go here */
        #ifdef SHIELD_PLATFORM_WINDOWS
        Sleep(ctx->check_interval_ms);
#else
        usleep(ctx->check_interval_ms * 1000);
#endif
    }
    
    return NULL;
}

/* Initialize ZHP */
shield_err_t zhp_init(zhp_context_t *ctx, uint32_t check_interval_ms)
{
    if (!ctx) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(ctx, 0, sizeof(*ctx));
    ctx->socket = -1;
    ctx->check_interval_ms = check_interval_ms > 0 ? check_interval_ms : 5000;
    ctx->running = true;
    
    #ifndef SHIELD_PLATFORM_WINDOWS
    pthread_create(&ctx->thread, NULL, zhp_health_thread, ctx);
#endif
    
    return SHIELD_OK;
}

/* Destroy ZHP */
void zhp_destroy(zhp_context_t *ctx)
{
    if (ctx) {
        ctx->running = false;
        #ifndef SHIELD_PLATFORM_WINDOWS
        pthread_join(ctx->thread, NULL);
#endif
        if (ctx->socket >= 0) {
            #ifdef SHIELD_PLATFORM_WINDOWS
        closesocket(ctx->socket);
#else
        close(ctx->socket);
#endif
        }
    }
}
