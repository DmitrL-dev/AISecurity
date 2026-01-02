/*
 * SENTINEL Shield - Context Window Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_context_window.h"
#include "shield_tokens.h"

/* Initialize */
shield_err_t context_window_init(context_window_t *ctx, int max_tokens)
{
    if (!ctx) return SHIELD_ERR_INVALID;
    
    memset(ctx, 0, sizeof(*ctx));
    ctx->max_tokens = max_tokens > 0 ? max_tokens : 8192;
    ctx->evict_oldest = true;
    
    return SHIELD_OK;
}

/* Destroy */
void context_window_destroy(context_window_t *ctx)
{
    if (!ctx) return;
    
    context_clear(ctx);
    
    if (ctx->system_prompt) {
        free(ctx->system_prompt->content);
        free(ctx->system_prompt);
    }
}

/* Add message */
shield_err_t context_add_message(context_window_t *ctx, message_role_t role,
                                   const char *content, size_t len)
{
    if (!ctx || !content) return SHIELD_ERR_INVALID;
    
    int tokens = estimate_tokens(content, len, TOKENIZER_GPT4);
    
    /* Evict if needed */
    int available = context_available_tokens(ctx);
    if (tokens > available) {
        context_evict_oldest(ctx, tokens - available);
    }
    
    /* Check again after eviction */
    available = context_available_tokens(ctx);
    if (tokens > available) {
        return SHIELD_ERR_NOMEM;
    }
    
    context_message_t *msg = calloc(1, sizeof(context_message_t));
    if (!msg) return SHIELD_ERR_NOMEM;
    
    msg->role = role;
    msg->content = malloc(len + 1);
    if (!msg->content) {
        free(msg);
        return SHIELD_ERR_NOMEM;
    }
    
    memcpy(msg->content, content, len);
    msg->content[len] = '\0';
    msg->content_len = len;
    msg->tokens = tokens;
    msg->timestamp = (uint64_t)time(NULL);
    
    /* Add to tail */
    if (ctx->tail) {
        ctx->tail->next = msg;
        msg->prev = ctx->tail;
    } else {
        ctx->head = msg;
    }
    ctx->tail = msg;
    
    ctx->message_count++;
    ctx->total_tokens += tokens;
    ctx->messages_added++;
    
    return SHIELD_OK;
}

/* Set system prompt */
shield_err_t context_set_system(context_window_t *ctx, const char *prompt)
{
    if (!ctx || !prompt) return SHIELD_ERR_INVALID;
    
    if (ctx->system_prompt) {
        ctx->total_tokens -= ctx->system_tokens;
        free(ctx->system_prompt->content);
        free(ctx->system_prompt);
    }
    
    size_t len = strlen(prompt);
    int tokens = estimate_tokens(prompt, len, TOKENIZER_GPT4);
    
    ctx->system_prompt = calloc(1, sizeof(context_message_t));
    if (!ctx->system_prompt) return SHIELD_ERR_NOMEM;
    
    ctx->system_prompt->role = ROLE_SYSTEM;
    ctx->system_prompt->content = strdup(prompt);
    ctx->system_prompt->content_len = len;
    ctx->system_prompt->tokens = tokens;
    ctx->system_prompt->pinned = true;
    
    ctx->system_tokens = tokens;
    ctx->total_tokens += tokens;
    
    return SHIELD_OK;
}

/* Get total tokens */
int context_get_tokens(context_window_t *ctx)
{
    return ctx ? ctx->total_tokens : 0;
}

/* Get available tokens */
int context_available_tokens(context_window_t *ctx)
{
    if (!ctx) return 0;
    return ctx->max_tokens - ctx->total_tokens;
}

/* Get messages */
context_message_t *context_get_messages(context_window_t *ctx)
{
    return ctx ? ctx->head : NULL;
}

/* Evict oldest messages */
shield_err_t context_evict_oldest(context_window_t *ctx, int tokens_needed)
{
    if (!ctx) return SHIELD_ERR_INVALID;
    
    int freed = 0;
    
    while (ctx->head && freed < tokens_needed) {
        context_message_t *msg = ctx->head;
        
        /* Don't evict pinned messages */
        if (msg->pinned) {
            msg = msg->next;
            while (msg && msg->pinned) {
                msg = msg->next;
            }
        }
        
        if (!msg) break;
        
        /* Remove from list */
        if (msg->prev) {
            msg->prev->next = msg->next;
        } else {
            ctx->head = msg->next;
        }
        
        if (msg->next) {
            msg->next->prev = msg->prev;
        } else {
            ctx->tail = msg->prev;
        }
        
        freed += msg->tokens;
        ctx->total_tokens -= msg->tokens;
        ctx->message_count--;
        ctx->messages_evicted++;
        
        free(msg->content);
        free(msg);
    }
    
    return SHIELD_OK;
}

/* Clear all messages */
void context_clear(context_window_t *ctx)
{
    if (!ctx) return;
    
    context_message_t *msg = ctx->head;
    while (msg) {
        context_message_t *next = msg->next;
        free(msg->content);
        free(msg);
        msg = next;
    }
    
    ctx->head = NULL;
    ctx->tail = NULL;
    ctx->message_count = 0;
    ctx->total_tokens = ctx->system_tokens;
}

/* Role to string */
static const char *role_to_string(message_role_t role)
{
    switch (role) {
    case ROLE_SYSTEM: return "system";
    case ROLE_USER: return "user";
    case ROLE_ASSISTANT: return "assistant";
    case ROLE_TOOL: return "tool";
    default: return "unknown";
    }
}

/* Export to JSON */
char *context_to_json(context_window_t *ctx)
{
    if (!ctx) return strdup("[]");
    
    size_t buf_size = 4096;
    char *buf = malloc(buf_size);
    if (!buf) return NULL;
    
    size_t pos = 0;
    pos += snprintf(buf + pos, buf_size - pos, "[");
    
    /* System prompt first */
    if (ctx->system_prompt) {
        pos += snprintf(buf + pos, buf_size - pos,
            "{\"role\":\"%s\",\"content\":\"%.100s...\"}",
            role_to_string(ctx->system_prompt->role),
            ctx->system_prompt->content);
    }
    
    /* Other messages */
    context_message_t *msg = ctx->head;
    while (msg && pos < buf_size - 200) {
        if (pos > 1) {
            pos += snprintf(buf + pos, buf_size - pos, ",");
        }
        pos += snprintf(buf + pos, buf_size - pos,
            "{\"role\":\"%s\",\"content\":\"%.100s%s\"}",
            role_to_string(msg->role),
            msg->content,
            msg->content_len > 100 ? "..." : "");
        msg = msg->next;
    }
    
    pos += snprintf(buf + pos, buf_size - pos, "]");
    
    return buf;
}
