/*
 * SENTINEL Shield - Batch Processor
 * 
 * Process multiple requests in batches
 */

#ifndef SHIELD_BATCH_H
#define SHIELD_BATCH_H

#include "shield_common.h"
#include "shield_rule.h"

/* Batch item */
typedef struct batch_item {
    char            id[64];
    char            *content;
    size_t          content_len;
    char            zone[64];
    rule_direction_t direction;
    
    /* Result */
    rule_action_t   action;
    char            reason[256];
    float           threat_score;
    bool            processed;
} batch_item_t;

/* Batch */
typedef struct batch {
    batch_item_t    *items;
    int             count;
    int             capacity;
    
    /* Stats */
    int             blocked;
    int             allowed;
    uint64_t        total_latency_us;
} batch_t;

/* API */
shield_err_t batch_init(batch_t *batch, int capacity);
void batch_destroy(batch_t *batch);

shield_err_t batch_add(batch_t *batch, const char *id, const char *content,
                         size_t len, const char *zone, rule_direction_t dir);
void batch_clear(batch_t *batch);

/* Process */
shield_err_t batch_process(batch_t *batch, void *context);
shield_err_t batch_process_parallel(batch_t *batch, void *context, int threads);

/* Results */
batch_item_t *batch_get_result(batch_t *batch, const char *id);
int batch_count_blocked(batch_t *batch);

#endif /* SHIELD_BATCH_H */
