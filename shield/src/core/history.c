/*
 * SENTINEL Shield - Prompt History Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "shield_history.h"
#include "shield_hashtable.h"

/* FNV-1a hash */
static uint64_t hash_prompt(const char *prompt, size_t len)
{
    uint64_t h = 14695981039346656037ULL;
    for (size_t i = 0; i < len; i++) {
        h ^= (uint64_t)prompt[i];
        h *= 1099511628211ULL;
    }
    return h;
}

/* Initialize */
shield_err_t history_init(prompt_history_t *history, int max_entries)
{
    if (!history) return SHIELD_ERR_INVALID;
    
    memset(history, 0, sizeof(*history));
    history->max_entries = max_entries > 0 ? max_entries : 10000;
    
    history->session_index = calloc(1, sizeof(hash_table_t));
    history->hash_index = calloc(1, sizeof(hash_table_t));
    
    if (!history->session_index || !history->hash_index) {
        free(history->session_index);
        free(history->hash_index);
        return SHIELD_ERR_NOMEM;
    }
    
    ht_init((hash_table_t *)history->session_index, 256);
    ht_init((hash_table_t *)history->hash_index, 1024);
    
    return SHIELD_OK;
}

/* Destroy */
void history_destroy(prompt_history_t *history)
{
    if (!history) return;
    
    history_entry_t *entry = history->head;
    while (entry) {
        history_entry_t *next = entry->next;
        free(entry->prompt);
        free(entry);
        entry = next;
    }
    
    if (history->session_index) {
        ht_destroy((hash_table_t *)history->session_index);
        free(history->session_index);
    }
    
    if (history->hash_index) {
        ht_destroy((hash_table_t *)history->hash_index);
        free(history->hash_index);
    }
}

/* Generate entry ID */
static void generate_id(char *id, size_t size)
{
    static uint64_t counter = 0;
    snprintf(id, size, "h-%lu-%08lx",
             (unsigned long)time(NULL), (unsigned long)++counter);
}

/* Add entry */
shield_err_t history_add(prompt_history_t *history, const char *session_id,
                           const char *prompt, size_t len, float threat_score)
{
    if (!history || !session_id || !prompt) return SHIELD_ERR_INVALID;
    
    /* Check for duplicate */
    uint64_t hash = hash_prompt(prompt, len);
    char hash_key[32];
    snprintf(hash_key, sizeof(hash_key), "%016lx", (unsigned long)hash);
    
    if (ht_get((hash_table_t *)history->hash_index, hash_key)) {
        history->duplicate_count++;
        return SHIELD_OK;  /* Duplicate, don't add */
    }
    
    /* Create entry */
    history_entry_t *entry = calloc(1, sizeof(history_entry_t));
    if (!entry) return SHIELD_ERR_NOMEM;
    
    generate_id(entry->id, sizeof(entry->id));
    strncpy(entry->session_id, session_id, sizeof(entry->session_id) - 1);
    entry->timestamp = (uint64_t)time(NULL);
    entry->prompt = malloc(len + 1);
    if (!entry->prompt) {
        free(entry);
        return SHIELD_ERR_NOMEM;
    }
    memcpy(entry->prompt, prompt, len);
    entry->prompt[len] = '\0';
    entry->prompt_len = len;
    entry->prompt_hash = hash;
    entry->threat_score = threat_score;
    
    /* Add to list */
    if (history->tail) {
        history->tail->next = entry;
        entry->prev = history->tail;
    } else {
        history->head = entry;
    }
    history->tail = entry;
    history->count++;
    
    /* Add to hash index */
    ht_set((hash_table_t *)history->hash_index, hash_key, entry);
    
    /* Evict if over limit */
    while (history->count > history->max_entries) {
        history_entry_t *old = history->head;
        history->head = old->next;
        if (history->head) {
            history->head->prev = NULL;
        } else {
            history->tail = NULL;
        }
        
        char old_hash[32];
        snprintf(old_hash, sizeof(old_hash), "%016lx", (unsigned long)old->prompt_hash);
        ht_remove((hash_table_t *)history->hash_index, old_hash);
        
        free(old->prompt);
        free(old);
        history->count--;
    }
    
    return SHIELD_OK;
}

/* Check if duplicate */
bool history_is_duplicate(prompt_history_t *history, const char *prompt, size_t len)
{
    if (!history || !prompt) return false;
    
    uint64_t hash = hash_prompt(prompt, len);
    char hash_key[32];
    snprintf(hash_key, sizeof(hash_key), "%016lx", (unsigned long)hash);
    
    return ht_get((hash_table_t *)history->hash_index, hash_key) != NULL;
}

/* Get entries by session */
history_entry_t *history_get_session(prompt_history_t *history,
                                       const char *session_id, int *count)
{
    if (!history || !session_id) return NULL;
    
    /* Linear search (could use session index for better performance) */
    int cnt = 0;
    history_entry_t *first = NULL;
    history_entry_t *entry = history->head;
    
    while (entry) {
        if (strcmp(entry->session_id, session_id) == 0) {
            if (!first) first = entry;
            cnt++;
        }
        entry = entry->next;
    }
    
    if (count) *count = cnt;
    return first;
}

/* Get recent entries */
history_entry_t *history_get_recent(prompt_history_t *history, int count)
{
    if (!history || count <= 0) return NULL;
    
    /* Return from tail */
    history_entry_t *entry = history->tail;
    int n = 1;
    
    while (entry && n < count) {
        if (!entry->prev) break;
        entry = entry->prev;
        n++;
    }
    
    return entry;
}

/* Count session entries */
int history_count_session(prompt_history_t *history, const char *session_id)
{
    int count = 0;
    history_get_session(history, session_id, &count);
    return count;
}

/* Average threat score for session */
float history_session_threat_avg(prompt_history_t *history, const char *session_id)
{
    if (!history || !session_id) return 0;
    
    float sum = 0;
    int count = 0;
    history_entry_t *entry = history->head;
    
    while (entry) {
        if (strcmp(entry->session_id, session_id) == 0) {
            sum += entry->threat_score;
            count++;
        }
        entry = entry->next;
    }
    
    return count > 0 ? sum / count : 0;
}

/* Cleanup old entries */
int history_cleanup_old(prompt_history_t *history, uint64_t max_age_seconds)
{
    if (!history) return 0;
    
    uint64_t now = (uint64_t)time(NULL);
    uint64_t cutoff = now - max_age_seconds;
    
    int removed = 0;
    
    while (history->head && history->head->timestamp < cutoff) {
        history_entry_t *old = history->head;
        history->head = old->next;
        if (history->head) {
            history->head->prev = NULL;
        } else {
            history->tail = NULL;
        }
        
        char hash_key[32];
        snprintf(hash_key, sizeof(hash_key), "%016lx", (unsigned long)old->prompt_hash);
        ht_remove((hash_table_t *)history->hash_index, hash_key);
        
        free(old->prompt);
        free(old);
        history->count--;
        removed++;
    }
    
    return removed;
}
