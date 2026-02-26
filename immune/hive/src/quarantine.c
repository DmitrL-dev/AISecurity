/*
 * SENTINEL IMMUNE — Hive Quarantine Module
 * 
 * Malware isolation and containment.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <sys/stat.h>

#ifdef _WIN32
    #include <windows.h>
    #include <direct.h>
    #define mkdir_p(path) _mkdir(path)
#else
    #include <unistd.h>
    #define mkdir_p(path) mkdir(path, 0700)
#endif

#include "../include/hive.h"

#define QUARANTINE_DIR      "/var/immune/quarantine"
#define MAX_QUARANTINE      10000
#define QUARANTINE_MAGIC    0x514E5446  /* "QNTF" */

/* Quarantine entry */
typedef struct {
    uint64_t    entry_id;
    char        original_path[512];
    char        quarantine_path[512];
    uint8_t     hash[32];
    size_t      original_size;
    time_t      quarantine_time;
    uint32_t    threat_level;
    uint32_t    threat_type;
    uint32_t    agent_id;
    char        details[256];
    int         deleted;
} quarantine_entry_t;

/* Quarantine database */
typedef struct {
    uint32_t            magic;
    uint32_t            version;
    uint64_t            entry_count;
    quarantine_entry_t  *entries;
    char                base_path[256];
} quarantine_db_t;

/* Global quarantine DB */
static quarantine_db_t g_quarantine;

/* ==================== Initialization ==================== */

int
quarantine_init(const char *base_path)
{
    memset(&g_quarantine, 0, sizeof(quarantine_db_t));
    
    g_quarantine.magic = QUARANTINE_MAGIC;
    g_quarantine.version = 1;
    
    if (base_path) {
        strncpy(g_quarantine.base_path, base_path, 
                sizeof(g_quarantine.base_path) - 1);
    } else {
        strcpy(g_quarantine.base_path, QUARANTINE_DIR);
    }
    
    /* Create quarantine directory */
    mkdir_p(g_quarantine.base_path);
    
    /* Allocate entries */
    g_quarantine.entries = calloc(MAX_QUARANTINE, sizeof(quarantine_entry_t));
    if (!g_quarantine.entries) {
        fprintf(stderr, "QUARANTINE: Failed to allocate entries\n");
        return -1;
    }
    
    /* Load existing entries */
    quarantine_load();
    
    printf("QUARANTINE: Initialized at %s\n", g_quarantine.base_path);
    return 0;
}

void
quarantine_shutdown(void)
{
    quarantine_save();
    
    if (g_quarantine.entries) {
        free(g_quarantine.entries);
        g_quarantine.entries = NULL;
    }
    
    printf("QUARANTINE: Shutdown complete\n");
}

/* ==================== Quarantine Operations ==================== */

/* Quarantine a file */
uint64_t
quarantine_file(const char *path, uint32_t threat_level, 
                uint32_t threat_type, uint32_t agent_id,
                const char *details)
{
    if (!path || g_quarantine.entry_count >= MAX_QUARANTINE)
        return 0;
    
    /* Read file */
    FILE *fp = fopen(path, "rb");
    if (!fp) {
        fprintf(stderr, "QUARANTINE: Cannot open %s\n", path);
        return 0;
    }
    
    fseek(fp, 0, SEEK_END);
    size_t size = ftell(fp);
    fseek(fp, 0, SEEK_SET);
    
    uint8_t *data = malloc(size);
    if (!data) {
        fclose(fp);
        return 0;
    }
    
    fread(data, 1, size, fp);
    fclose(fp);
    
    /* Calculate hash */
    uint8_t hash[32];
    /* Would use immune_hash() here */
    memset(hash, 0, sizeof(hash));  /* Placeholder */
    
    /* Create quarantine entry */
    uint64_t entry_id = g_quarantine.entry_count + 1;
    quarantine_entry_t *entry = &g_quarantine.entries[g_quarantine.entry_count];
    
    entry->entry_id = entry_id;
    strncpy(entry->original_path, path, sizeof(entry->original_path) - 1);
    
    snprintf(entry->quarantine_path, sizeof(entry->quarantine_path),
             "%s/%08lx.qnt", g_quarantine.base_path, entry_id);
    
    memcpy(entry->hash, hash, sizeof(hash));
    entry->original_size = size;
    entry->quarantine_time = time(NULL);
    entry->threat_level = threat_level;
    entry->threat_type = threat_type;
    entry->agent_id = agent_id;
    entry->deleted = 0;
    
    if (details) {
        strncpy(entry->details, details, sizeof(entry->details) - 1);
    }
    
    /* Write quarantined file */
    fp = fopen(entry->quarantine_path, "wb");
    if (fp) {
        /* XOR encrypt with simple key */
        for (size_t i = 0; i < size; i++) {
            data[i] ^= 0x5A;
        }
        fwrite(data, 1, size, fp);
        fclose(fp);
        
        /* Delete original */
        remove(path);
        
        printf("QUARANTINE: File quarantined: %s -> %s\n", 
               path, entry->quarantine_path);
    }
    
    free(data);
    
    g_quarantine.entry_count++;
    quarantine_save();
    
    return entry_id;
}

/* Restore from quarantine */
int
quarantine_restore(uint64_t entry_id, const char *restore_path)
{
    quarantine_entry_t *entry = NULL;
    
    /* Find entry */
    for (uint64_t i = 0; i < g_quarantine.entry_count; i++) {
        if (g_quarantine.entries[i].entry_id == entry_id) {
            entry = &g_quarantine.entries[i];
            break;
        }
    }
    
    if (!entry || entry->deleted) {
        return -1;
    }
    
    /* Read quarantined file */
    FILE *fp = fopen(entry->quarantine_path, "rb");
    if (!fp) {
        return -1;
    }
    
    fseek(fp, 0, SEEK_END);
    size_t size = ftell(fp);
    fseek(fp, 0, SEEK_SET);
    
    uint8_t *data = malloc(size);
    if (!data) {
        fclose(fp);
        return -1;
    }
    
    fread(data, 1, size, fp);
    fclose(fp);
    
    /* Decrypt (XOR) */
    for (size_t i = 0; i < size; i++) {
        data[i] ^= 0x5A;
    }
    
    /* Write to restore path */
    const char *dest = restore_path ? restore_path : entry->original_path;
    
    fp = fopen(dest, "wb");
    if (fp) {
        fwrite(data, 1, size, fp);
        fclose(fp);
        
        printf("QUARANTINE: Restored to %s\n", dest);
    }
    
    free(data);
    return 0;
}

/* Delete from quarantine */
int
quarantine_delete(uint64_t entry_id)
{
    for (uint64_t i = 0; i < g_quarantine.entry_count; i++) {
        if (g_quarantine.entries[i].entry_id == entry_id) {
            quarantine_entry_t *entry = &g_quarantine.entries[i];
            
            if (!entry->deleted) {
                remove(entry->quarantine_path);
                entry->deleted = 1;
                quarantine_save();
                
                printf("QUARANTINE: Deleted entry %lu\n", entry_id);
                return 0;
            }
        }
    }
    
    return -1;
}

/* Get quarantine statistics */
void
quarantine_stats(uint64_t *total, uint64_t *active, uint64_t *deleted)
{
    uint64_t t = 0, a = 0, d = 0;
    
    for (uint64_t i = 0; i < g_quarantine.entry_count; i++) {
        t++;
        if (g_quarantine.entries[i].deleted) {
            d++;
        } else {
            a++;
        }
    }
    
    if (total) *total = t;
    if (active) *active = a;
    if (deleted) *deleted = d;
}

/* ==================== Persistence ==================== */

int
quarantine_save(void)
{
    char path[512];
    snprintf(path, sizeof(path), "%s/quarantine.db", g_quarantine.base_path);
    
    FILE *fp = fopen(path, "wb");
    if (!fp) return -1;
    
    fwrite(&g_quarantine.magic, sizeof(uint32_t), 1, fp);
    fwrite(&g_quarantine.version, sizeof(uint32_t), 1, fp);
    fwrite(&g_quarantine.entry_count, sizeof(uint64_t), 1, fp);
    
    for (uint64_t i = 0; i < g_quarantine.entry_count; i++) {
        fwrite(&g_quarantine.entries[i], sizeof(quarantine_entry_t), 1, fp);
    }
    
    fclose(fp);
    return 0;
}

int
quarantine_load(void)
{
    char path[512];
    snprintf(path, sizeof(path), "%s/quarantine.db", g_quarantine.base_path);
    
    FILE *fp = fopen(path, "rb");
    if (!fp) return -1;
    
    uint32_t magic, version;
    fread(&magic, sizeof(uint32_t), 1, fp);
    fread(&version, sizeof(uint32_t), 1, fp);
    
    if (magic != QUARANTINE_MAGIC) {
        fclose(fp);
        return -1;
    }
    
    fread(&g_quarantine.entry_count, sizeof(uint64_t), 1, fp);
    
    if (g_quarantine.entry_count > MAX_QUARANTINE) {
        g_quarantine.entry_count = MAX_QUARANTINE;
    }
    
    for (uint64_t i = 0; i < g_quarantine.entry_count; i++) {
        fread(&g_quarantine.entries[i], sizeof(quarantine_entry_t), 1, fp);
    }
    
    fclose(fp);
    printf("QUARANTINE: Loaded %lu entries\n", g_quarantine.entry_count);
    
    return 0;
}
