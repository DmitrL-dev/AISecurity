/*
 * SENTINEL Shield - Quarantine Manager
 * 
 * Holds quarantined content for review
 */

#ifndef SHIELD_QUARANTINE_H
#define SHIELD_QUARANTINE_H

#include "shield_common.h"

/* Quarantine item */
typedef struct quarantine_item {
    char            id[64];
    uint64_t        timestamp;
    char            zone[64];
    char            session_id[64];
    rule_direction_t direction;
    uint32_t        matched_rule;
    char            reason[256];
    
    /* Content */
    char            *content;
    size_t          content_len;
    
    /* Review */
    bool            reviewed;
    bool            released;
    char            reviewer[64];
    uint64_t        review_time;
    
    struct quarantine_item *next;
} quarantine_item_t;

/* Quarantine manager */
typedef struct quarantine_manager {
    quarantine_item_t   *items;
    int                 count;
    int                 max_items;
    uint64_t            retention_sec;
    
    /* Stats */
    uint64_t            total_quarantined;
    uint64_t            total_released;
    uint64_t            total_blocked;
} quarantine_manager_t;

/* API */
shield_err_t quarantine_init(quarantine_manager_t *mgr, int max_items, uint64_t retention_sec);
void quarantine_destroy(quarantine_manager_t *mgr);

/* Add to quarantine */
shield_err_t quarantine_add(quarantine_manager_t *mgr,
                             const char *zone, const char *session_id,
                             rule_direction_t direction, uint32_t rule,
                             const char *reason,
                             const char *content, size_t content_len,
                             char *out_id, size_t out_id_len);

/* Review */
quarantine_item_t *quarantine_get(quarantine_manager_t *mgr, const char *id);
shield_err_t quarantine_release(quarantine_manager_t *mgr, const char *id,
                                  const char *reviewer);
shield_err_t quarantine_block(quarantine_manager_t *mgr, const char *id,
                                const char *reviewer);

/* List */
int quarantine_list(quarantine_manager_t *mgr, quarantine_item_t **items,
                    int max_count, bool pending_only);

/* Cleanup */
int quarantine_cleanup(quarantine_manager_t *mgr);

/* Stats */
int quarantine_count(quarantine_manager_t *mgr);
int quarantine_pending_count(quarantine_manager_t *mgr);

#endif /* SHIELD_QUARANTINE_H */
