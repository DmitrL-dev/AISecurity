/*
 * SENTINEL Shield - Request Logger
 * 
 * Structured logging for all requests
 */

#ifndef SHIELD_REQUEST_LOG_H
#define SHIELD_REQUEST_LOG_H

#include "shield_common.h"
#include "shield_rule.h"

/* Log entry */
typedef struct request_log_entry {
    char            id[64];
    uint64_t        timestamp;
    
    /* Request */
    char            zone[64];
    char            session_id[64];
    char            source_ip[64];
    rule_direction_t direction;
    size_t          content_len;
    char            content_hash[65];
    
    /* Processing */
    rule_action_t   action;
    uint32_t        matched_rule;
    char            reason[256];
    float           threat_score;
    uint64_t        latency_us;
    
    /* Semantic */
    int             intent_type;
    float           intent_confidence;
    
    /* Next entry */
    struct request_log_entry *next;
} request_log_entry_t;

/* Request logger */
typedef struct request_logger {
    /* Memory buffer */
    request_log_entry_t *entries;
    request_log_entry_t *tail;
    int             count;
    int             max_entries;
    
    /* File output */
    FILE            *file;
    char            file_path[256];
    bool            json_format;
    
    /* Rotation */
    uint64_t        max_file_size;
    int             max_files;
    int             current_file_num;
    
    /* Stats */
    uint64_t        total_logged;
} request_logger_t;

/* API */
shield_err_t request_logger_init(request_logger_t *logger, const char *path);
void request_logger_destroy(request_logger_t *logger);

/* Log request */
shield_err_t request_log(request_logger_t *logger, request_log_entry_t *entry);

/* Query */
int request_logger_query(request_logger_t *logger,
                          uint64_t start_time, uint64_t end_time,
                          const char *zone, rule_action_t action,
                          request_log_entry_t **results, int max_results);

/* Export */
shield_err_t request_logger_export(request_logger_t *logger,
                                     const char *path, bool json);

/* Rotation */
shield_err_t request_logger_rotate(request_logger_t *logger);

#endif /* SHIELD_REQUEST_LOG_H */
