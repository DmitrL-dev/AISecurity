/*
 * SENTINEL IMMUNE — Production Adaptive Memory
 * 
 * SHA-256 based threat memory with persistence.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include <openssl/sha.h>
#include <openssl/evp.h>

#include "../include/immune.h"

#define MEMORY_MAGIC    0x494D454D  /* "IMEM" */
#define MEMORY_VERSION  2

/* ==================== Hashing ==================== */

static void
compute_sha256(const void *data, size_t len, uint8_t *hash)
{
    SHA256_CTX ctx;
    SHA256_Init(&ctx);
    SHA256_Update(&ctx, data, len);
    SHA256_Final(hash, &ctx);
}

/* ==================== Core Functions ==================== */

int
immune_memory_learn(immune_agent_t *agent, const void *data, size_t length)
{
    if (!agent || !data || length == 0) {
        return -1;
    }
    
    uint8_t hash[32];
    compute_sha256(data, length, hash);
    
    /* Check if already known */
    for (int i = 0; i < agent->memory_count; i++) {
        if (agent->memory[i].active &&
            memcmp(agent->memory[i].hash, hash, 32) == 0) {
            /* Update existing */
            agent->memory[i].hit_count++;
            agent->memory[i].last_seen = time(NULL);
            return 0;
        }
    }
    
    /* Find free slot */
    int slot = -1;
    
    for (int i = 0; i < agent->memory_count; i++) {
        if (!agent->memory[i].active) {
            slot = i;
            break;
        }
    }
    
    if (slot < 0) {
        if (agent->memory_count >= MAX_MEMORY_ENTRIES) {
            /* Evict oldest */
            time_t oldest_time = time(NULL);
            int oldest_idx = 0;
            
            for (int i = 0; i < agent->memory_count; i++) {
                if (agent->memory[i].last_seen < oldest_time) {
                    oldest_time = agent->memory[i].last_seen;
                    oldest_idx = i;
                }
            }
            
            slot = oldest_idx;
        } else {
            slot = agent->memory_count++;
        }
    }
    
    /* Store new entry */
    memory_entry_t *entry = &agent->memory[slot];
    memset(entry, 0, sizeof(memory_entry_t));
    
    memcpy(entry->hash, hash, 32);
    entry->level = THREAT_HIGH;
    entry->type = THREAT_TYPE_MALWARE;
    entry->first_seen = time(NULL);
    entry->last_seen = time(NULL);
    entry->hit_count = 1;
    entry->active = 1;
    
    return 0;
}

int
immune_memory_recall(immune_agent_t *agent, const void *data, size_t length)
{
    if (!agent || !data || length == 0) {
        return 0;
    }
    
    uint8_t hash[32];
    compute_sha256(data, length, hash);
    
    for (int i = 0; i < agent->memory_count; i++) {
        if (agent->memory[i].active &&
            memcmp(agent->memory[i].hash, hash, 32) == 0) {
            
            /* Found! Update stats */
            agent->memory[i].hit_count++;
            agent->memory[i].last_seen = time(NULL);
            agent->stats.memory_hits++;
            
            return 1;
        }
    }
    
    return 0;
}

/* ==================== Persistence ==================== */

int
immune_memory_save(immune_agent_t *agent)
{
    if (!agent) return -1;
    
    char path[512];
    snprintf(path, sizeof(path), "%s/memory.dat", agent->data_path);
    
    FILE *fp = fopen(path, "wb");
    if (!fp) {
        return -1;
    }
    
    uint32_t magic = MEMORY_MAGIC;
    uint32_t version = MEMORY_VERSION;
    
    fwrite(&magic, sizeof(uint32_t), 1, fp);
    fwrite(&version, sizeof(uint32_t), 1, fp);
    
    /* Count active entries */
    int active_count = 0;
    for (int i = 0; i < agent->memory_count; i++) {
        if (agent->memory[i].active) {
            active_count++;
        }
    }
    
    fwrite(&active_count, sizeof(int), 1, fp);
    
    /* Write active entries */
    for (int i = 0; i < agent->memory_count; i++) {
        if (agent->memory[i].active) {
            fwrite(&agent->memory[i], sizeof(memory_entry_t), 1, fp);
        }
    }
    
    fclose(fp);
    return 0;
}

int
immune_memory_load(immune_agent_t *agent)
{
    if (!agent) return -1;
    
    char path[512];
    snprintf(path, sizeof(path), "%s/memory.dat", agent->data_path);
    
    FILE *fp = fopen(path, "rb");
    if (!fp) {
        return -1;  /* No saved memory, OK */
    }
    
    uint32_t magic, version;
    fread(&magic, sizeof(uint32_t), 1, fp);
    fread(&version, sizeof(uint32_t), 1, fp);
    
    if (magic != MEMORY_MAGIC || version != MEMORY_VERSION) {
        fclose(fp);
        return -1;
    }
    
    int count;
    fread(&count, sizeof(int), 1, fp);
    
    if (count > MAX_MEMORY_ENTRIES) {
        count = MAX_MEMORY_ENTRIES;
    }
    
    for (int i = 0; i < count; i++) {
        fread(&agent->memory[i], sizeof(memory_entry_t), 1, fp);
    }
    
    agent->memory_count = count;
    
    fclose(fp);
    return 0;
}

/* ==================== Memory Management ==================== */

int
immune_memory_clear(immune_agent_t *agent)
{
    if (!agent) return -1;
    
    memset(agent->memory, 0, sizeof(agent->memory));
    agent->memory_count = 0;
    
    return 0;
}

int
immune_memory_count(immune_agent_t *agent)
{
    if (!agent) return 0;
    
    int count = 0;
    for (int i = 0; i < agent->memory_count; i++) {
        if (agent->memory[i].active) {
            count++;
        }
    }
    
    return count;
}

void
immune_memory_stats(immune_agent_t *agent, int *total, int *active,
                    uint64_t *total_hits)
{
    if (!agent) return;
    
    int cnt_active = 0;
    uint64_t hits = 0;
    
    for (int i = 0; i < agent->memory_count; i++) {
        if (agent->memory[i].active) {
            cnt_active++;
            hits += agent->memory[i].hit_count;
        }
    }
    
    if (total) *total = agent->memory_count;
    if (active) *active = cnt_active;
    if (total_hits) *total_hits = hits;
}

/* ==================== Debug ==================== */

void
immune_memory_dump(immune_agent_t *agent)
{
    if (!agent) return;
    
    printf("\n=== ADAPTIVE MEMORY ===\n");
    printf("Entries: %d\n\n", agent->memory_count);
    
    for (int i = 0; i < agent->memory_count && i < 20; i++) {
        memory_entry_t *e = &agent->memory[i];
        
        if (!e->active) continue;
        
        printf("[%d] ", i);
        
        /* Print hash prefix */
        for (int j = 0; j < 8; j++) {
            printf("%02x", e->hash[j]);
        }
        
        printf("... level=%d hits=%u\n", e->level, e->hit_count);
    }
    
    if (agent->memory_count > 20) {
        printf("... and %d more\n", agent->memory_count - 20);
    }
    
    printf("=======================\n\n");
}
