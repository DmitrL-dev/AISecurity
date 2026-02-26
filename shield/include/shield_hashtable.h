/*
 * SENTINEL Shield - Hash Table
 * 
 * High-performance hash table for lookups
 */

#ifndef SHIELD_HASHTABLE_H
#define SHIELD_HASHTABLE_H

#include "shield_common.h"

/* Hash table entry */
typedef struct ht_entry {
    char            *key;
    void            *value;
    struct ht_entry *next;
} ht_entry_t;

/* Hash table */
typedef struct hash_table {
    ht_entry_t      **buckets;
    int             bucket_count;
    int             entry_count;
    float           load_factor;
    
    /* Optional destructor */
    void            (*value_destructor)(void *);
} hash_table_t;

/* API */
shield_err_t ht_init(hash_table_t *ht, int initial_size);
void ht_destroy(hash_table_t *ht);

shield_err_t ht_set(hash_table_t *ht, const char *key, void *value);
void *ht_get(hash_table_t *ht, const char *key);
void *ht_remove(hash_table_t *ht, const char *key);
bool ht_contains(hash_table_t *ht, const char *key);

int ht_count(hash_table_t *ht);
void ht_clear(hash_table_t *ht);

/* Iteration */
typedef void (*ht_foreach_fn)(const char *key, void *value, void *ctx);
void ht_foreach(hash_table_t *ht, ht_foreach_fn fn, void *ctx);

/* Set value destructor */
void ht_set_destructor(hash_table_t *ht, void (*destructor)(void *));

#endif /* SHIELD_HASHTABLE_H */
