/*
 * SENTINEL Shield - Hash Table Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_common.h"
#include "shield_hashtable.h"

/* FNV-1a hash */
static uint32_t hash_string(const char *str)
{
    uint32_t hash = 2166136261u;
    while (*str) {
        hash ^= (uint8_t)*str++;
        hash *= 16777619u;
    }
    return hash;
}

/* Initialize */
shield_err_t ht_init(hash_table_t *ht, int initial_size)
{
    if (!ht || initial_size <= 0) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(ht, 0, sizeof(*ht));
    ht->bucket_count = initial_size;
    ht->load_factor = 0.75f;
    
    ht->buckets = calloc(initial_size, sizeof(ht_entry_t *));
    if (!ht->buckets) {
        return SHIELD_ERR_NOMEM;
    }
    
    return SHIELD_OK;
}

/* Destroy */
void ht_destroy(hash_table_t *ht)
{
    if (!ht) return;
    
    ht_clear(ht);
    free(ht->buckets);
    ht->buckets = NULL;
    ht->bucket_count = 0;
}

/* Resize */
static shield_err_t ht_resize(hash_table_t *ht, int new_size)
{
    ht_entry_t **new_buckets = calloc(new_size, sizeof(ht_entry_t *));
    if (!new_buckets) {
        return SHIELD_ERR_NOMEM;
    }
    
    /* Rehash all entries */
    for (int i = 0; i < ht->bucket_count; i++) {
        ht_entry_t *entry = ht->buckets[i];
        while (entry) {
            ht_entry_t *next = entry->next;
            
            uint32_t new_index = hash_string(entry->key) % new_size;
            entry->next = new_buckets[new_index];
            new_buckets[new_index] = entry;
            
            entry = next;
        }
    }
    
    free(ht->buckets);
    ht->buckets = new_buckets;
    ht->bucket_count = new_size;
    
    return SHIELD_OK;
}

/* Set */
shield_err_t ht_set(hash_table_t *ht, const char *key, void *value)
{
    if (!ht || !key) {
        return SHIELD_ERR_INVALID;
    }
    
    /* Check load factor */
    if ((float)ht->entry_count / ht->bucket_count > ht->load_factor) {
        ht_resize(ht, ht->bucket_count * 2);
    }
    
    uint32_t index = hash_string(key) % ht->bucket_count;
    
    /* Check for existing key */
    ht_entry_t *entry = ht->buckets[index];
    while (entry) {
        if (strcmp(entry->key, key) == 0) {
            /* Update existing */
            if (ht->value_destructor && entry->value) {
                ht->value_destructor(entry->value);
            }
            entry->value = value;
            return SHIELD_OK;
        }
        entry = entry->next;
    }
    
    /* Create new entry */
    entry = calloc(1, sizeof(ht_entry_t));
    if (!entry) {
        return SHIELD_ERR_NOMEM;
    }
    
    entry->key = strdup(key);
    if (!entry->key) {
        free(entry);
        return SHIELD_ERR_NOMEM;
    }
    
    entry->value = value;
    entry->next = ht->buckets[index];
    ht->buckets[index] = entry;
    ht->entry_count++;
    
    return SHIELD_OK;
}

/* Get */
void *ht_get(hash_table_t *ht, const char *key)
{
    if (!ht || !key) {
        return NULL;
    }
    
    uint32_t index = hash_string(key) % ht->bucket_count;
    
    ht_entry_t *entry = ht->buckets[index];
    while (entry) {
        if (strcmp(entry->key, key) == 0) {
            return entry->value;
        }
        entry = entry->next;
    }
    
    return NULL;
}

/* Remove */
void *ht_remove(hash_table_t *ht, const char *key)
{
    if (!ht || !key) {
        return NULL;
    }
    
    uint32_t index = hash_string(key) % ht->bucket_count;
    
    ht_entry_t **pp = &ht->buckets[index];
    while (*pp) {
        if (strcmp((*pp)->key, key) == 0) {
            ht_entry_t *entry = *pp;
            void *value = entry->value;
            
            *pp = entry->next;
            free(entry->key);
            free(entry);
            ht->entry_count--;
            
            return value;
        }
        pp = &(*pp)->next;
    }
    
    return NULL;
}

/* Contains */
bool ht_contains(hash_table_t *ht, const char *key)
{
    return ht_get(ht, key) != NULL;
}

/* Count */
int ht_count(hash_table_t *ht)
{
    return ht ? ht->entry_count : 0;
}

/* Clear */
void ht_clear(hash_table_t *ht)
{
    if (!ht) return;
    
    for (int i = 0; i < ht->bucket_count; i++) {
        ht_entry_t *entry = ht->buckets[i];
        while (entry) {
            ht_entry_t *next = entry->next;
            
            if (ht->value_destructor && entry->value) {
                ht->value_destructor(entry->value);
            }
            
            free(entry->key);
            free(entry);
            entry = next;
        }
        ht->buckets[i] = NULL;
    }
    
    ht->entry_count = 0;
}

/* Foreach */
void ht_foreach(hash_table_t *ht, ht_foreach_fn fn, void *ctx)
{
    if (!ht || !fn) return;
    
    for (int i = 0; i < ht->bucket_count; i++) {
        ht_entry_t *entry = ht->buckets[i];
        while (entry) {
            fn(entry->key, entry->value, ctx);
            entry = entry->next;
        }
    }
}

/* Set destructor */
void ht_set_destructor(hash_table_t *ht, void (*destructor)(void *))
{
    if (ht) {
        ht->value_destructor = destructor;
    }
}
