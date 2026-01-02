/*
 * SENTINEL Shield - Audit Logger Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "shield_common.h"
#include "shield_audit.h"

/* Initialize audit logger */
shield_err_t audit_init(audit_logger_t *logger, const char *path)
{
    if (!logger || !path) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(logger, 0, sizeof(*logger));
    strncpy(logger->path, path, sizeof(logger->path) - 1);
    
    logger->file = fopen(path, "a");
    if (!logger->file) {
        return SHIELD_ERR_IO;
    }
    
    logger->enabled = true;
    logger->json_format = true;
    logger->max_size_bytes = 100 * 1024 * 1024; /* 100 MB */
    logger->max_files = 10;
    
    /* Get current size */
    fseek(logger->file, 0, SEEK_END);
    logger->current_size = (uint64_t)ftell(logger->file);
    
    LOG_INFO("Audit logger initialized: %s", path);
    
    return SHIELD_OK;
}

/* Destroy */
void audit_destroy(audit_logger_t *logger)
{
    if (!logger) {
        return;
    }
    
    if (logger->file) {
        fclose(logger->file);
        logger->file = NULL;
    }
    
    logger->enabled = false;
}

/* Format timestamp */
static void format_timestamp(char *buf, size_t len, uint64_t timestamp)
{
    time_t t = (time_t)timestamp;
    struct tm *tm = gmtime(&t);
    strftime(buf, len, "%Y-%m-%dT%H:%M:%SZ", tm);
}

/* Log entry */
shield_err_t audit_log(audit_logger_t *logger, const audit_entry_t *entry)
{
    if (!logger || !entry || !logger->enabled) {
        return SHIELD_ERR_INVALID;
    }
    
    if (!logger->file) {
        return SHIELD_ERR_IO;
    }
    
    /* Check rotation */
    if (logger->current_size > logger->max_size_bytes) {
        audit_rotate(logger);
    }
    
    char timestamp[32];
    format_timestamp(timestamp, sizeof(timestamp), entry->timestamp);
    
    int written = 0;
    
    if (logger->json_format) {
        written = fprintf(logger->file,
            "{\"timestamp\":\"%s\",\"type\":\"%s\",\"user\":\"%s\","
            "\"source_ip\":\"%s\",\"action\":\"%s\",\"target\":\"%s\","
            "\"details\":\"%s\",\"success\":%s,\"session_id\":\"%s\"}\n",
            timestamp,
            audit_event_type_name(entry->type),
            entry->user,
            entry->source_ip,
            entry->action,
            entry->target,
            entry->details,
            entry->success ? "true" : "false",
            entry->session_id
        );
    } else {
        written = fprintf(logger->file,
            "%s | %s | user=%s | ip=%s | action=%s | target=%s | %s | %s\n",
            timestamp,
            audit_event_type_name(entry->type),
            entry->user,
            entry->source_ip,
            entry->action,
            entry->target,
            entry->details,
            entry->success ? "OK" : "FAIL"
        );
    }
    
    if (written > 0) {
        logger->current_size += written;
        logger->entries_written++;
        fflush(logger->file);
    }
    
    return SHIELD_OK;
}

/* Log config change */
shield_err_t audit_log_config_change(audit_logger_t *logger,
                                      const char *user, const char *source_ip,
                                      const char *what, const char *details)
{
    audit_entry_t entry = {
        .timestamp = (uint64_t)time(NULL),
        .type = AUDIT_CONFIG_CHANGE,
        .success = true,
    };
    
    if (user) strncpy(entry.user, user, sizeof(entry.user) - 1);
    if (source_ip) strncpy(entry.source_ip, source_ip, sizeof(entry.source_ip) - 1);
    if (what) strncpy(entry.action, what, sizeof(entry.action) - 1);
    if (details) strncpy(entry.details, details, sizeof(entry.details) - 1);
    
    return audit_log(logger, &entry);
}

/* Log security event */
shield_err_t audit_log_security(audit_logger_t *logger,
                                 const char *zone, const char *session_id,
                                 const char *action, const char *details)
{
    audit_entry_t entry = {
        .timestamp = (uint64_t)time(NULL),
        .type = AUDIT_REQUEST_BLOCKED,
        .success = true,
    };
    
    if (zone) strncpy(entry.target, zone, sizeof(entry.target) - 1);
    if (session_id) strncpy(entry.session_id, session_id, sizeof(entry.session_id) - 1);
    if (action) strncpy(entry.action, action, sizeof(entry.action) - 1);
    if (details) strncpy(entry.details, details, sizeof(entry.details) - 1);
    
    return audit_log(logger, &entry);
}

/* Rotate log */
shield_err_t audit_rotate(audit_logger_t *logger)
{
    if (!logger) {
        return SHIELD_ERR_INVALID;
    }
    
    if (logger->file) {
        fclose(logger->file);
        logger->file = NULL;
    }
    
    /* Rename old files */
    char old_path[280], new_path[280];
    
    for (int i = logger->max_files - 1; i >= 1; i--) {
        snprintf(old_path, sizeof(old_path), "%s.%d", logger->path, i - 1);
        snprintf(new_path, sizeof(new_path), "%s.%d", logger->path, i);
        rename(old_path, new_path);
    }
    
    /* Rename current to .0 */
    snprintf(new_path, sizeof(new_path), "%s.0", logger->path);
    rename(logger->path, new_path);
    
    /* Open new file */
    logger->file = fopen(logger->path, "a");
    if (!logger->file) {
        return SHIELD_ERR_IO;
    }
    
    logger->current_size = 0;
    
    LOG_INFO("Audit log rotated: %s", logger->path);
    
    return SHIELD_OK;
}

/* Set JSON format */
void audit_set_json_format(audit_logger_t *logger, bool json)
{
    if (logger) {
        logger->json_format = json;
    }
}

/* Event type name */
const char *audit_event_type_name(audit_event_type_t type)
{
    switch (type) {
    case AUDIT_LOGIN: return "LOGIN";
    case AUDIT_LOGOUT: return "LOGOUT";
    case AUDIT_CONFIG_CHANGE: return "CONFIG_CHANGE";
    case AUDIT_RULE_ADD: return "RULE_ADD";
    case AUDIT_RULE_DELETE: return "RULE_DELETE";
    case AUDIT_ZONE_CREATE: return "ZONE_CREATE";
    case AUDIT_ZONE_DELETE: return "ZONE_DELETE";
    case AUDIT_REQUEST_BLOCKED: return "REQUEST_BLOCKED";
    case AUDIT_REQUEST_QUARANTINED: return "REQUEST_QUARANTINED";
    case AUDIT_CANARY_TRIGGERED: return "CANARY_TRIGGERED";
    case AUDIT_FAILOVER: return "FAILOVER";
    case AUDIT_ADMIN_ACTION: return "ADMIN_ACTION";
    default: return "UNKNOWN";
    }
}
