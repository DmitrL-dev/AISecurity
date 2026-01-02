/*
 * SENTINEL Shield - Prompt History
 * 
 * Track and analyze prompt history for patterns
 */

#ifndef SHIELD_HISTORY_H
#define SHIELD_HISTORY_H

#include "shield_common.h"

/* History entry */
typedef struct history_entry {
    char            id[64];
    char            session_id[64];
    uint64_t        timestamp;
    
    /* Content */
    char            *prompt;
    size_t          prompt_len;
    uint64_t        prompt_hash;
    
    /* Analysis */
    float           threat_score;
    int             intent_type;
    bool            blocked;
    
    struct history_entry *next;
    struct history_entry *prev;
} history_entry_t;

/* Prompt history */
typedef struct prompt_history {
    history_entry_t *head;
    history_entry_t *tail;
    int             count;
    int             max_entries;
    
    /* Index by session */
    void            *session_index;     /* Hash table */
    
    /* Deduplication */
    void            *hash_index;        /* Seen hashes */
    int             duplicate_count;
} prompt_history_t;

/* API */
shield_err_t history_init(prompt_history_t *history, int max_entries);
void history_destroy(prompt_history_t *history);

/* Add entry */
shield_err_t history_add(prompt_history_t *history, const char *session_id,
                           const char *prompt, size_t len, float threat_score);

/* Query */
history_entry_t *history_get_session(prompt_history_t *history,
                                       const char *session_id,
                                       int *count);
history_entry_t *history_get_recent(prompt_history_t *history, int count);

/* Analysis */
bool history_is_duplicate(prompt_history_t *history, const char *prompt, size_t len);
int history_count_session(prompt_history_t *history, const char *session_id);
float history_session_threat_avg(prompt_history_t *history, const char *session_id);

/* Cleanup */
int history_cleanup_old(prompt_history_t *history, uint64_t max_age_seconds);

#endif /* SHIELD_HISTORY_H */
