/*
 * SENTINEL Shield - Audit Logger
 * 
 * Structured audit logging for compliance
 */

#ifndef SHIELD_AUDIT_H
#define SHIELD_AUDIT_H

#include "shield_common.h"

/* Audit event types */
typedef enum audit_event_type {
    AUDIT_LOGIN = 1,
    AUDIT_LOGOUT,
    AUDIT_CONFIG_CHANGE,
    AUDIT_RULE_ADD,
    AUDIT_RULE_DELETE,
    AUDIT_ZONE_CREATE,
    AUDIT_ZONE_DELETE,
    AUDIT_REQUEST_BLOCKED,
    AUDIT_REQUEST_QUARANTINED,
    AUDIT_CANARY_TRIGGERED,
    AUDIT_FAILOVER,
    AUDIT_ADMIN_ACTION,
} audit_event_type_t;

/* Audit entry */
typedef struct audit_entry {
    uint64_t            timestamp;
    audit_event_type_t  type;
    char                user[64];
    char                source_ip[46];
    char                action[64];
    char                target[128];
    char                details[512];
    bool                success;
    char                session_id[64];
} audit_entry_t;

/* Audit logger */
typedef struct audit_logger {
    FILE                *file;
    char                path[256];
    bool                enabled;
    bool                json_format;
    
    /* Rotation */
    uint64_t            max_size_bytes;
    int                 max_files;
    uint64_t            current_size;
    
    /* Stats */
    uint64_t            entries_written;
} audit_logger_t;

/* API */
shield_err_t audit_init(audit_logger_t *logger, const char *path);
void audit_destroy(audit_logger_t *logger);

shield_err_t audit_log(audit_logger_t *logger, const audit_entry_t *entry);

/* Convenience functions */
shield_err_t audit_log_config_change(audit_logger_t *logger,
                                      const char *user, const char *source_ip,
                                      const char *what, const char *details);

shield_err_t audit_log_security(audit_logger_t *logger,
                                 const char *zone, const char *session_id,
                                 const char *action, const char *details);

/* Rotation */
shield_err_t audit_rotate(audit_logger_t *logger);

/* Set format */
void audit_set_json_format(audit_logger_t *logger, bool json);

/* Get event type name */
const char *audit_event_type_name(audit_event_type_t type);

#endif /* SHIELD_AUDIT_H */
