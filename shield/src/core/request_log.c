/*
 * SENTINEL Shield - Request Logger Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "shield_request_log.h"

/* Initialize */
shield_err_t request_logger_init(request_logger_t *logger, const char *path)
{
    if (!logger) return SHIELD_ERR_INVALID;
    
    memset(logger, 0, sizeof(*logger));
    logger->max_entries = 10000;
    logger->json_format = true;
    logger->max_file_size = 100 * 1024 * 1024;  /* 100MB */
    logger->max_files = 10;
    
    if (path) {
        strncpy(logger->file_path, path, sizeof(logger->file_path) - 1);
        logger->file = fopen(path, "a");
    }
    
    return SHIELD_OK;
}

/* Destroy */
void request_logger_destroy(request_logger_t *logger)
{
    if (!logger) return;
    
    /* Free memory entries */
    request_log_entry_t *entry = logger->entries;
    while (entry) {
        request_log_entry_t *next = entry->next;
        free(entry);
        entry = next;
    }
    
    if (logger->file) {
        fclose(logger->file);
        logger->file = NULL;
    }
}

/* Generate ID */
static void generate_id(char *id, size_t size)
{
    static uint64_t counter = 0;
    snprintf(id, size, "req-%lu-%08lx", 
             (unsigned long)time(NULL), (unsigned long)++counter);
}

/* Log request */
shield_err_t request_log(request_logger_t *logger, request_log_entry_t *entry)
{
    if (!logger || !entry) return SHIELD_ERR_INVALID;
    
    /* Generate ID if not set */
    if (entry->id[0] == '\0') {
        generate_id(entry->id, sizeof(entry->id));
    }
    
    if (entry->timestamp == 0) {
        entry->timestamp = (uint64_t)time(NULL);
    }
    
    /* Add to memory buffer */
    request_log_entry_t *copy = malloc(sizeof(request_log_entry_t));
    if (!copy) return SHIELD_ERR_NOMEM;
    
    memcpy(copy, entry, sizeof(request_log_entry_t));
    copy->next = NULL;
    
    if (logger->tail) {
        logger->tail->next = copy;
    } else {
        logger->entries = copy;
    }
    logger->tail = copy;
    logger->count++;
    
    /* Evict oldest if at capacity */
    while (logger->count > logger->max_entries) {
        request_log_entry_t *old = logger->entries;
        logger->entries = old->next;
        if (logger->entries == NULL) {
            logger->tail = NULL;
        }
        free(old);
        logger->count--;
    }
    
    /* Write to file */
    if (logger->file) {
        if (logger->json_format) {
            fprintf(logger->file,
                "{\"id\":\"%s\",\"ts\":%lu,\"zone\":\"%s\","
                "\"session\":\"%s\",\"ip\":\"%s\",\"dir\":%d,"
                "\"action\":%d,\"rule\":%u,\"reason\":\"%s\","
                "\"threat\":%.2f,\"latency\":%lu}\n",
                entry->id, (unsigned long)entry->timestamp,
                entry->zone, entry->session_id, entry->source_ip,
                entry->direction, entry->action, entry->matched_rule,
                entry->reason, entry->threat_score,
                (unsigned long)entry->latency_us);
        } else {
            fprintf(logger->file,
                "%lu %s %s %s %d %d %u %.2f %lu %s\n",
                (unsigned long)entry->timestamp, entry->id,
                entry->zone, entry->source_ip,
                entry->direction, entry->action,
                entry->matched_rule, entry->threat_score,
                (unsigned long)entry->latency_us, entry->reason);
        }
        fflush(logger->file);
    }
    
    logger->total_logged++;
    
    return SHIELD_OK;
}

/* Query logs */
int request_logger_query(request_logger_t *logger,
                          uint64_t start_time, uint64_t end_time,
                          const char *zone, rule_action_t action,
                          request_log_entry_t **results, int max_results)
{
    if (!logger || !results) return 0;
    
    int count = 0;
    request_log_entry_t *entry = logger->entries;
    
    while (entry && count < max_results) {
        bool match = true;
        
        if (start_time > 0 && entry->timestamp < start_time) match = false;
        if (end_time > 0 && entry->timestamp > end_time) match = false;
        if (zone && zone[0] && strcmp(entry->zone, zone) != 0) match = false;
        if (action != ACTION_NONE && entry->action != action) match = false;
        
        if (match) {
            results[count++] = entry;
        }
        
        entry = entry->next;
    }
    
    return count;
}

/* Rotate log file */
shield_err_t request_logger_rotate(request_logger_t *logger)
{
    if (!logger || !logger->file) return SHIELD_ERR_INVALID;
    
    fclose(logger->file);
    
    /* Rename old files */
    for (int i = logger->max_files - 1; i >= 0; i--) {
        char old_name[300], new_name[300];
        if (i == 0) {
            snprintf(old_name, sizeof(old_name), "%s", logger->file_path);
        } else {
            snprintf(old_name, sizeof(old_name), "%s.%d", logger->file_path, i);
        }
        snprintf(new_name, sizeof(new_name), "%s.%d", logger->file_path, i + 1);
        rename(old_name, new_name);
    }
    
    /* Delete oldest */
    char oldest[300];
    snprintf(oldest, sizeof(oldest), "%s.%d", logger->file_path, logger->max_files);
    remove(oldest);
    
    logger->file = fopen(logger->file_path, "a");
    logger->current_file_num++;
    
    return logger->file ? SHIELD_OK : SHIELD_ERR_IO;
}

/* Export */
shield_err_t request_logger_export(request_logger_t *logger,
                                     const char *path, bool json)
{
    if (!logger || !path) return SHIELD_ERR_INVALID;
    
    FILE *f = fopen(path, "w");
    if (!f) return SHIELD_ERR_IO;
    
    if (json) fprintf(f, "[\n");
    
    bool first = true;
    request_log_entry_t *entry = logger->entries;
    while (entry) {
        if (json) {
            if (!first) fprintf(f, ",\n");
            fprintf(f,
                "  {\"id\":\"%s\",\"ts\":%lu,\"zone\":\"%s\","
                "\"action\":%d,\"reason\":\"%s\"}",
                entry->id, (unsigned long)entry->timestamp,
                entry->zone, entry->action, entry->reason);
            first = false;
        } else {
            fprintf(f, "%s\t%lu\t%s\t%d\t%s\n",
                entry->id, (unsigned long)entry->timestamp,
                entry->zone, entry->action, entry->reason);
        }
        entry = entry->next;
    }
    
    if (json) fprintf(f, "\n]\n");
    
    fclose(f);
    return SHIELD_OK;
}
