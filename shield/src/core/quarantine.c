/*
 * SENTINEL Shield - Quarantine Manager Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "shield_common.h"
#include "shield_quarantine.h"
#include "shield_qrng.h"

/* Generate UUID-like ID using QRNG */
static void generate_id(char *id, size_t len)
{
    const char hex[] = "0123456789abcdef";
    
    for (size_t i = 0; i < len - 1 && i < 32; i++) {
        if (i == 8 || i == 12 || i == 16 || i == 20) {
            id[i] = '-';
        } else {
            id[i] = hex[shield_qrng_u32() % 16];
        }
    }
    id[len > 36 ? 36 : len - 1] = '\0';
}

/* Initialize */
shield_err_t quarantine_init(quarantine_manager_t *mgr, int max_items, uint64_t retention_sec)
{
    if (!mgr) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(mgr, 0, sizeof(*mgr));
    mgr->max_items = max_items > 0 ? max_items : 1000;
    mgr->retention_sec = retention_sec > 0 ? retention_sec : 86400; /* 24 hours */
    
    return SHIELD_OK;
}

/* Destroy */
void quarantine_destroy(quarantine_manager_t *mgr)
{
    if (!mgr) return;
    
    quarantine_item_t *item = mgr->items;
    while (item) {
        quarantine_item_t *next = item->next;
        free(item->content);
        free(item);
        item = next;
    }
    
    mgr->items = NULL;
    mgr->count = 0;
}

/* Add to quarantine */
shield_err_t quarantine_add(quarantine_manager_t *mgr,
                             const char *zone, const char *session_id,
                             rule_direction_t direction, uint32_t rule,
                             const char *reason,
                             const char *content, size_t content_len,
                             char *out_id, size_t out_id_len)
{
    if (!mgr || !content) {
        return SHIELD_ERR_INVALID;
    }
    
    /* Check capacity */
    if (mgr->count >= mgr->max_items) {
        quarantine_cleanup(mgr);
        if (mgr->count >= mgr->max_items) {
            return SHIELD_ERR_NOMEM;
        }
    }
    
    quarantine_item_t *item = calloc(1, sizeof(quarantine_item_t));
    if (!item) {
        return SHIELD_ERR_NOMEM;
    }
    
    generate_id(item->id, sizeof(item->id));
    item->timestamp = (uint64_t)time(NULL);
    item->direction = direction;
    item->matched_rule = rule;
    
    if (zone) strncpy(item->zone, zone, sizeof(item->zone) - 1);
    if (session_id) strncpy(item->session_id, session_id, sizeof(item->session_id) - 1);
    if (reason) strncpy(item->reason, reason, sizeof(item->reason) - 1);
    
    item->content = malloc(content_len + 1);
    if (!item->content) {
        free(item);
        return SHIELD_ERR_NOMEM;
    }
    memcpy(item->content, content, content_len);
    item->content[content_len] = '\0';
    item->content_len = content_len;
    
    /* Add to list */
    item->next = mgr->items;
    mgr->items = item;
    mgr->count++;
    mgr->total_quarantined++;
    
    if (out_id && out_id_len > 0) {
        strncpy(out_id, item->id, out_id_len - 1);
    }
    
    LOG_INFO("Quarantine: Added %s (zone=%s, rule=%u)", item->id, zone, rule);
    
    return SHIELD_OK;
}

/* Get item */
quarantine_item_t *quarantine_get(quarantine_manager_t *mgr, const char *id)
{
    if (!mgr || !id) return NULL;
    
    quarantine_item_t *item = mgr->items;
    while (item) {
        if (strcmp(item->id, id) == 0) {
            return item;
        }
        item = item->next;
    }
    
    return NULL;
}

/* Release item */
shield_err_t quarantine_release(quarantine_manager_t *mgr, const char *id,
                                  const char *reviewer)
{
    quarantine_item_t *item = quarantine_get(mgr, id);
    if (!item) {
        return SHIELD_ERR_NOTFOUND;
    }
    
    item->reviewed = true;
    item->released = true;
    item->review_time = (uint64_t)time(NULL);
    if (reviewer) strncpy(item->reviewer, reviewer, sizeof(item->reviewer) - 1);
    
    mgr->total_released++;
    
    LOG_INFO("Quarantine: Released %s by %s", id, reviewer ? reviewer : "unknown");
    
    return SHIELD_OK;
}

/* Block item */
shield_err_t quarantine_block(quarantine_manager_t *mgr, const char *id,
                                const char *reviewer)
{
    quarantine_item_t *item = quarantine_get(mgr, id);
    if (!item) {
        return SHIELD_ERR_NOTFOUND;
    }
    
    item->reviewed = true;
    item->released = false;
    item->review_time = (uint64_t)time(NULL);
    if (reviewer) strncpy(item->reviewer, reviewer, sizeof(item->reviewer) - 1);
    
    mgr->total_blocked++;
    
    LOG_INFO("Quarantine: Blocked %s by %s", id, reviewer ? reviewer : "unknown");
    
    return SHIELD_OK;
}

/* List items */
int quarantine_list(quarantine_manager_t *mgr, quarantine_item_t **items,
                    int max_count, bool pending_only)
{
    if (!mgr || !items) return 0;
    
    int count = 0;
    quarantine_item_t *item = mgr->items;
    
    while (item && count < max_count) {
        if (!pending_only || !item->reviewed) {
            items[count++] = item;
        }
        item = item->next;
    }
    
    return count;
}

/* Cleanup old items */
int quarantine_cleanup(quarantine_manager_t *mgr)
{
    if (!mgr) return 0;
    
    uint64_t now = (uint64_t)time(NULL);
    uint64_t cutoff = now - mgr->retention_sec;
    
    int removed = 0;
    quarantine_item_t **pp = &mgr->items;
    
    while (*pp) {
        quarantine_item_t *item = *pp;
        
        /* Remove if old and reviewed */
        if (item->timestamp < cutoff && item->reviewed) {
            *pp = item->next;
            free(item->content);
            free(item);
            mgr->count--;
            removed++;
        } else {
            pp = &item->next;
        }
    }
    
    return removed;
}

/* Count */
int quarantine_count(quarantine_manager_t *mgr)
{
    return mgr ? mgr->count : 0;
}

/* Pending count */
int quarantine_pending_count(quarantine_manager_t *mgr)
{
    if (!mgr) return 0;
    
    int count = 0;
    quarantine_item_t *item = mgr->items;
    while (item) {
        if (!item->reviewed) count++;
        item = item->next;
    }
    
    return count;
}
