/*
 * SENTINEL Shield - Signature Updates Protocol (SSigP)
 * 
 * Manages threat signature updates from central repository
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_common.h"
#include "shield_protocol.h"
#include "shield_signatures.h"

/* SSigP Message Types */
typedef enum {
    SSIGP_MSG_CHECK_UPDATE   = 0x01,
    SSIGP_MSG_UPDATE_AVAIL   = 0x02,
    SSIGP_MSG_NO_UPDATE      = 0x03,
    SSIGP_MSG_DOWNLOAD       = 0x04,
    SSIGP_MSG_DATA           = 0x05,
    SSIGP_MSG_COMPLETE       = 0x06,
    SSIGP_MSG_APPLY          = 0x07,
    SSIGP_MSG_APPLIED        = 0x08,
    SSIGP_MSG_ERROR          = 0x09,
} ssigp_msg_type_t;

/* Signature Update Info */
typedef struct {
    char        version[32];
    uint32_t    signature_count;
    uint32_t    size_bytes;
    char        checksum[64];
    uint64_t    release_date;
    char        release_notes[512];
} ssigp_update_info_t;

/* SSigP Config */
typedef struct {
    char        server_url[256];
    uint32_t    check_interval_hours;
    bool        auto_update;
    bool        verify_checksum;
} ssigp_config_t;

/* SSigP Context */
typedef struct {
    int             socket;
    ssigp_config_t  config;
    char            current_version[32];
    uint64_t        last_check;
    bool            update_pending;
} ssigp_context_t;

/* Check for updates */
shield_err_t ssigp_check_update(ssigp_context_t *ctx, ssigp_update_info_t *info)
{
    if (!ctx) {
        return SHIELD_ERR_INVALID;
    }
    
    struct {
        uint8_t type;
        char current_version[32];
    } request = {
        .type = SSIGP_MSG_CHECK_UPDATE
    };
    strncpy(request.current_version, ctx->current_version, 
            sizeof(request.current_version) - 1);
    
    if (ctx->socket >= 0) {
        send(ctx->socket, &request, sizeof(request), 0);
        
        uint8_t resp_type;
        recv(ctx->socket, &resp_type, 1, 0);
        
        if (resp_type == SSIGP_MSG_UPDATE_AVAIL) {
            recv(ctx->socket, info, sizeof(*info), 0);
            ctx->update_pending = true;
            LOG_INFO("SSigP: Update available: v%s (%u signatures)",
                    info->version, info->signature_count);
            return SHIELD_OK;
        } else if (resp_type == SSIGP_MSG_NO_UPDATE) {
            LOG_DEBUG("SSigP: No update available");
        }
    }
    
    ctx->last_check = time(NULL);
    return SHIELD_OK;
}

/* Download update */
shield_err_t ssigp_download(ssigp_context_t *ctx, void **data_out, size_t *size_out)
{
    if (!ctx || !data_out || !size_out) {
        return SHIELD_ERR_INVALID;
    }
    
    uint8_t type = SSIGP_MSG_DOWNLOAD;
    if (ctx->socket >= 0) {
        send(ctx->socket, &type, 1, 0);
        
        /* Receive size */
        uint32_t size;
        recv(ctx->socket, &size, sizeof(size), 0);
        
        /* Receive data */
        void *data = malloc(size);
        if (!data) {
            return SHIELD_ERR_NOMEM;
        }
        
        size_t received = 0;
        while (received < size) {
            ssize_t n = recv(ctx->socket, (char*)data + received, size - received, 0);
            if (n <= 0) {
                free(data);
                return SHIELD_ERR_IO;
            }
            received += n;
        }
        
        *data_out = data;
        *size_out = size;
        
        LOG_INFO("SSigP: Downloaded %zu bytes", size);
    }
    
    return SHIELD_OK;
}

/* Apply update */
shield_err_t ssigp_apply(ssigp_context_t *ctx, signature_db_t *db, 
                          const void *data, size_t size)
{
    if (!ctx || !db || !data) {
        return SHIELD_ERR_INVALID;
    }
    
    /* Parse and apply signatures */
    shield_err_t err = sigdb_load_from_data(db, data, size);
    if (err != SHIELD_OK) {
        LOG_ERROR("SSigP: Failed to apply update");
        return err;
    }
    
    /* Update version */
    /* (would be parsed from data) */
    
    ctx->update_pending = false;
    
    uint8_t type = SSIGP_MSG_APPLIED;
    if (ctx->socket >= 0) {
        send(ctx->socket, &type, 1, 0);
    }
    
    LOG_INFO("SSigP: Update applied successfully");
    return SHIELD_OK;
}

/* Initialize SSigP */
shield_err_t ssigp_init(ssigp_context_t *ctx, const ssigp_config_t *config,
                         const char *current_version)
{
    if (!ctx || !config) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(ctx, 0, sizeof(*ctx));
    ctx->config = *config;
    ctx->socket = -1;
    
    if (current_version) {
        strncpy(ctx->current_version, current_version, 
                sizeof(ctx->current_version) - 1);
    }
    
    return SHIELD_OK;
}

/* Destroy SSigP */
void ssigp_destroy(ssigp_context_t *ctx)
{
    if (ctx && ctx->socket >= 0) {
        close(ctx->socket);
    }
}
