/*
 * SENTINEL Shield - Batch Processor Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "shield_batch.h"
#include "shield_timer.h"

/* Generate batch item ID */
static void generate_id(char *id, size_t size)
{
    static uint64_t counter = 0;
    snprintf(id, size, "batch-%lu-%08lx",
             (unsigned long)time(NULL), (unsigned long)++counter);
}

/* Initialize */
shield_err_t batch_init(batch_t *batch, int capacity)
{
    if (!batch || capacity <= 0) return SHIELD_ERR_INVALID;
    
    memset(batch, 0, sizeof(*batch));
    
    batch->items = calloc(capacity, sizeof(batch_item_t));
    if (!batch->items) return SHIELD_ERR_NOMEM;
    
    batch->capacity = capacity;
    
    return SHIELD_OK;
}

/* Destroy */
void batch_destroy(batch_t *batch)
{
    if (!batch) return;
    
    if (batch->items) {
        for (int i = 0; i < batch->count; i++) {
            free(batch->items[i].content);
        }
        free(batch->items);
    }
}

/* Add item */
shield_err_t batch_add(batch_t *batch, const char *id, const char *content,
                         size_t len, const char *zone, rule_direction_t dir)
{
    if (!batch || !content || !zone) return SHIELD_ERR_INVALID;
    if (batch->count >= batch->capacity) return SHIELD_ERR_NOMEM;
    
    batch_item_t *item = &batch->items[batch->count];
    memset(item, 0, sizeof(*item));
    
    if (id) {
        strncpy(item->id, id, sizeof(item->id) - 1);
    } else {
        generate_id(item->id, sizeof(item->id));
    }
    
    item->content = malloc(len + 1);
    if (!item->content) return SHIELD_ERR_NOMEM;
    memcpy(item->content, content, len);
    item->content[len] = '\0';
    item->content_len = len;
    
    strncpy(item->zone, zone, sizeof(item->zone) - 1);
    item->direction = dir;
    
    batch->count++;
    
    return SHIELD_OK;
}

/* Clear batch */
void batch_clear(batch_t *batch)
{
    if (!batch) return;
    
    for (int i = 0; i < batch->count; i++) {
        free(batch->items[i].content);
        batch->items[i].content = NULL;
    }
    
    batch->count = 0;
    batch->blocked = 0;
    batch->allowed = 0;
    batch->total_latency_us = 0;
}

/* Process batch (stub - would call actual evaluation) */
shield_err_t batch_process(batch_t *batch, void *context)
{
    if (!batch) return SHIELD_ERR_INVALID;
    
    for (int i = 0; i < batch->count; i++) {
        batch_item_t *item = &batch->items[i];
        
        shield_timer_t timer;
        timer_start(&timer);
        
        /* TODO: Call actual shield_evaluate() */
        /* For now, default to allow */
        item->action = ACTION_ALLOW;
        item->threat_score = 0;
        strcpy(item->reason, "batch_processed");
        item->processed = true;
        
        timer_stop(&timer);
        batch->total_latency_us += timer_elapsed_us(&timer);
        
        if (item->action == ACTION_BLOCK) {
            batch->blocked++;
        } else {
            batch->allowed++;
        }
    }
    
    return SHIELD_OK;
}

/* Process batch in parallel (stub) */
shield_err_t batch_process_parallel(batch_t *batch, void *context, int threads)
{
    /* TODO: Use thread pool for parallel processing */
    return batch_process(batch, context);
}

/* Get result by ID */
batch_item_t *batch_get_result(batch_t *batch, const char *id)
{
    if (!batch || !id) return NULL;
    
    for (int i = 0; i < batch->count; i++) {
        if (strcmp(batch->items[i].id, id) == 0) {
            return &batch->items[i];
        }
    }
    
    return NULL;
}

/* Count blocked */
int batch_count_blocked(batch_t *batch)
{
    return batch ? batch->blocked : 0;
}
