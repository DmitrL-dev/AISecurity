/*
 * SENTINEL Shield - Blocklist Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <ctype.h>

#include "shield_common.h"
#include "shield_blocklist.h"

/* FNV-1a hash */
static uint32_t hash_string(const char *str)
{
    uint32_t hash = 2166136261u;
    while (*str) {
        hash ^= (uint8_t)tolower(*str++);
        hash *= 16777619u;
    }
    return hash;
}

/* Initialize blocklist */
shield_err_t blocklist_init(blocklist_t *bl, const char *name, uint32_t bucket_count)
{
    if (!bl || bucket_count == 0) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(bl, 0, sizeof(*bl));
    
    bl->buckets = calloc(bucket_count, sizeof(blocklist_entry_t *));
    if (!bl->buckets) {
        return SHIELD_ERR_NOMEM;
    }
    
    bl->bucket_count = bucket_count;
    if (name) {
        strncpy(bl->name, name, sizeof(bl->name) - 1);
    }
    
    return SHIELD_OK;
}

/* Destroy blocklist */
void blocklist_destroy(blocklist_t *bl)
{
    if (!bl) {
        return;
    }
    
    blocklist_clear(bl);
    free(bl->buckets);
    bl->buckets = NULL;
}

/* Add pattern */
shield_err_t blocklist_add(blocklist_t *bl, const char *pattern, const char *reason)
{
    if (!bl || !pattern || strlen(pattern) == 0) {
        return SHIELD_ERR_INVALID;
    }
    
    uint32_t hash = hash_string(pattern);
    uint32_t bucket = hash % bl->bucket_count;
    
    /* Check if already exists */
    blocklist_entry_t *entry = bl->buckets[bucket];
    while (entry) {
        if (entry->hash == hash && strcasecmp(entry->pattern, pattern) == 0) {
            return SHIELD_ERR_EXISTS;
        }
        entry = entry->next;
    }
    
    /* Create new entry */
    entry = calloc(1, sizeof(blocklist_entry_t));
    if (!entry) {
        return SHIELD_ERR_NOMEM;
    }
    
    entry->hash = hash;
    strncpy(entry->pattern, pattern, sizeof(entry->pattern) - 1);
    if (reason) {
        strncpy(entry->reason, reason, sizeof(entry->reason) - 1);
    }
    entry->added_at = (uint64_t)time(NULL);
    
    /* Insert at head */
    entry->next = bl->buckets[bucket];
    bl->buckets[bucket] = entry;
    bl->entry_count++;
    
    return SHIELD_OK;
}

/* Remove pattern */
shield_err_t blocklist_remove(blocklist_t *bl, const char *pattern)
{
    if (!bl || !pattern) {
        return SHIELD_ERR_INVALID;
    }
    
    uint32_t hash = hash_string(pattern);
    uint32_t bucket = hash % bl->bucket_count;
    
    blocklist_entry_t **pp = &bl->buckets[bucket];
    while (*pp) {
        if ((*pp)->hash == hash && strcasecmp((*pp)->pattern, pattern) == 0) {
            blocklist_entry_t *entry = *pp;
            *pp = entry->next;
            free(entry);
            bl->entry_count--;
            return SHIELD_OK;
        }
        pp = &(*pp)->next;
    }
    
    return SHIELD_ERR_NOTFOUND;
}

/* Check if text matches any blocklist pattern */
blocklist_entry_t *blocklist_check(blocklist_t *bl, const char *text)
{
    if (!bl || !text) {
        return NULL;
    }
    
    /* Convert text to lowercase for comparison */
    size_t len = strlen(text);
    char *lower = malloc(len + 1);
    if (!lower) {
        return NULL;
    }
    
    for (size_t i = 0; i <= len; i++) {
        lower[i] = tolower((unsigned char)text[i]);
    }
    
    /* Check all entries */
    for (uint32_t i = 0; i < bl->bucket_count; i++) {
        blocklist_entry_t *entry = bl->buckets[i];
        while (entry) {
            /* Check if pattern is in text */
            char pattern_lower[256];
            for (size_t j = 0; j < sizeof(pattern_lower) - 1 && entry->pattern[j]; j++) {
                pattern_lower[j] = tolower((unsigned char)entry->pattern[j]);
                pattern_lower[j + 1] = '\0';
            }
            
            if (strstr(lower, pattern_lower)) {
                entry->hits++;
                free(lower);
                return entry;
            }
            
            entry = entry->next;
        }
    }
    
    free(lower);
    return NULL;
}

/* Simple contains check */
bool blocklist_contains(blocklist_t *bl, const char *text)
{
    return blocklist_check(bl, text) != NULL;
}

/* Load from file */
shield_err_t blocklist_load(blocklist_t *bl, const char *filename)
{
    if (!bl || !filename) {
        return SHIELD_ERR_INVALID;
    }
    
    FILE *fp = fopen(filename, "r");
    if (!fp) {
        return SHIELD_ERR_IO;
    }
    
    char line[512];
    while (fgets(line, sizeof(line), fp)) {
        /* Skip comments and empty lines */
        char *p = line;
        while (*p && isspace(*p)) p++;
        if (*p == '\0' || *p == '#' || *p == '!') {
            continue;
        }
        
        /* Remove newline */
        size_t len = strlen(p);
        if (len > 0 && p[len - 1] == '\n') {
            p[len - 1] = '\0';
        }
        
        /* Parse: pattern [| reason] */
        char *reason = strchr(p, '|');
        if (reason) {
            *reason++ = '\0';
            while (*reason && isspace(*reason)) reason++;
        }
        
        /* Trim pattern */
        len = strlen(p);
        while (len > 0 && isspace(p[len - 1])) {
            p[--len] = '\0';
        }
        
        if (strlen(p) > 0) {
            blocklist_add(bl, p, reason);
        }
    }
    
    fclose(fp);
    return SHIELD_OK;
}

/* Save to file */
shield_err_t blocklist_save(blocklist_t *bl, const char *filename)
{
    if (!bl || !filename) {
        return SHIELD_ERR_INVALID;
    }
    
    FILE *fp = fopen(filename, "w");
    if (!fp) {
        return SHIELD_ERR_IO;
    }
    
    fprintf(fp, "# SENTINEL Shield Blocklist: %s\n", bl->name);
    fprintf(fp, "# Format: pattern | reason\n\n");
    
    for (uint32_t i = 0; i < bl->bucket_count; i++) {
        blocklist_entry_t *entry = bl->buckets[i];
        while (entry) {
            if (entry->reason[0]) {
                fprintf(fp, "%s | %s\n", entry->pattern, entry->reason);
            } else {
                fprintf(fp, "%s\n", entry->pattern);
            }
            entry = entry->next;
        }
    }
    
    fclose(fp);
    return SHIELD_OK;
}

/* Clear all */
void blocklist_clear(blocklist_t *bl)
{
    if (!bl) {
        return;
    }
    
    for (uint32_t i = 0; i < bl->bucket_count; i++) {
        blocklist_entry_t *entry = bl->buckets[i];
        while (entry) {
            blocklist_entry_t *next = entry->next;
            free(entry);
            entry = next;
        }
        bl->buckets[i] = NULL;
    }
    
    bl->entry_count = 0;
}

/* Get count */
uint32_t blocklist_count(blocklist_t *bl)
{
    return bl ? bl->entry_count : 0;
}
