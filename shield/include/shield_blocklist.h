/*
 * SENTINEL Shield - Blocklist Manager
 * 
 * Hash-based blocklist for fast pattern matching
 */

#ifndef SHIELD_BLOCKLIST_H
#define SHIELD_BLOCKLIST_H

#include "shield_common.h"

/* Blocklist entry */
typedef struct blocklist_entry {
    uint32_t    hash;
    char        pattern[256];
    char        reason[128];
    uint64_t    added_at;
    uint64_t    hits;
    struct blocklist_entry *next;
} blocklist_entry_t;

/* Blocklist */
typedef struct blocklist {
    blocklist_entry_t   **buckets;
    uint32_t            bucket_count;
    uint32_t            entry_count;
    char                name[64];
} blocklist_t;

/* API */
shield_err_t blocklist_init(blocklist_t *bl, const char *name, uint32_t bucket_count);
void blocklist_destroy(blocklist_t *bl);

shield_err_t blocklist_add(blocklist_t *bl, const char *pattern, const char *reason);
shield_err_t blocklist_remove(blocklist_t *bl, const char *pattern);
bool blocklist_contains(blocklist_t *bl, const char *text);
blocklist_entry_t *blocklist_check(blocklist_t *bl, const char *text);

shield_err_t blocklist_load(blocklist_t *bl, const char *filename);
shield_err_t blocklist_save(blocklist_t *bl, const char *filename);

void blocklist_clear(blocklist_t *bl);
uint32_t blocklist_count(blocklist_t *bl);

#endif /* SHIELD_BLOCKLIST_H */
