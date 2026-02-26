/*
 * SENTINEL Shield - Context Window Manager
 * 
 * Manage context window for multi-turn conversations
 */

#ifndef SHIELD_CONTEXT_WINDOW_H
#define SHIELD_CONTEXT_WINDOW_H

#include "shield_common.h"

/* Message role */
typedef enum message_role {
    ROLE_SYSTEM,
    ROLE_USER,
    ROLE_ASSISTANT,
    ROLE_TOOL,
} message_role_t;

/* Context message */
typedef struct context_message {
    message_role_t  role;
    char            *content;
    size_t          content_len;
    int             tokens;
    uint64_t        timestamp;
    
    /* Metadata */
    char            message_id[64];
    bool            pinned;         /* Don't evict */
    float           importance;     /* For smart eviction */
    
    struct context_message *next;
    struct context_message *prev;
} context_message_t;

/* Context window */
typedef struct context_window {
    context_message_t *head;
    context_message_t *tail;
    int             message_count;
    int             total_tokens;
    int             max_tokens;
    
    /* System prompt (always kept) */
    context_message_t *system_prompt;
    int             system_tokens;
    
    /* Eviction policy */
    bool            evict_oldest;   /* FIFO eviction */
    bool            smart_evict;    /* Importance-based */
    
    /* Stats */
    uint64_t        messages_added;
    uint64_t        messages_evicted;
} context_window_t;

/* API */
shield_err_t context_window_init(context_window_t *ctx, int max_tokens);
void context_window_destroy(context_window_t *ctx);

/* Messages */
shield_err_t context_add_message(context_window_t *ctx, message_role_t role,
                                   const char *content, size_t len);
shield_err_t context_set_system(context_window_t *ctx, const char *prompt);

/* Query */
int context_get_tokens(context_window_t *ctx);
int context_available_tokens(context_window_t *ctx);
context_message_t *context_get_messages(context_window_t *ctx);

/* Eviction */
shield_err_t context_evict_oldest(context_window_t *ctx, int tokens_needed);
void context_clear(context_window_t *ctx);

/* Export for API call */
char *context_to_json(context_window_t *ctx);

#endif /* SHIELD_CONTEXT_WINDOW_H */
