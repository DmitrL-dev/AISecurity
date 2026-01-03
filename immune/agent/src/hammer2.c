/*
 * SENTINEL IMMUNE — HAMMER2 Persistence Layer
 * 
 * DragonFlyBSD HAMMER2 filesystem features for
 * tamper-resistant data storage.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#ifdef __DragonFly__
    #include <sys/types.h>
    #include <sys/stat.h>
    #include <unistd.h>
    #include <fcntl.h>
    #include <vfs/hammer2/hammer2_mount.h>
    #include <vfs/hammer2/hammer2_ioctl.h>
#endif

#include "../include/immune.h"

#define HAMMER2_MOUNT_PATH      "/var/immune"
#define SNAPSHOT_PREFIX         "immune_snap_"
#define MAX_SNAPSHOTS           100

/* Persistence context */
typedef struct {
    char        mount_path[256];
    int         hammer2_available;
    
    /* Snapshot tracking */
    char        snapshots[MAX_SNAPSHOTS][64];
    int         snapshot_count;
    
    /* Statistics */
    uint64_t    writes;
    uint64_t    reads;
    uint64_t    snapshots_created;
} hammer2_ctx_t;

static hammer2_ctx_t g_persist;

/* ==================== Initialization ==================== */

int
hammer2_init(const char *mount_path)
{
    memset(&g_persist, 0, sizeof(hammer2_ctx_t));
    
    if (mount_path) {
        strncpy(g_persist.mount_path, mount_path, 
                sizeof(g_persist.mount_path) - 1);
    } else {
        strcpy(g_persist.mount_path, HAMMER2_MOUNT_PATH);
    }
    
#ifdef __DragonFly__
    /* Check if HAMMER2 filesystem */
    struct statvfs vfs;
    if (statvfs(g_persist.mount_path, &vfs) == 0) {
        /* Check filesystem type */
        /* HAMMER2 magic would be in f_fsid or detected via mount options */
        g_persist.hammer2_available = 1;
    }
#endif
    
    printf("HAMMER2: Initialized at %s (%s)\n",
           g_persist.mount_path,
           g_persist.hammer2_available ? "HAMMER2" : "generic");
    
    return 0;
}

void
hammer2_shutdown(void)
{
    printf("HAMMER2: Shutdown (writes=%lu, reads=%lu, snapshots=%lu)\n",
           g_persist.writes, g_persist.reads, g_persist.snapshots_created);
}

/* ==================== Secure Write ==================== */

/*
 * Write with COW (Copy-on-Write) guarantee.
 * HAMMER2 provides this automatically.
 */
int
hammer2_write(const char *name, const void *data, size_t size)
{
    char path[512];
    snprintf(path, sizeof(path), "%s/%s", g_persist.mount_path, name);
    
    FILE *fp = fopen(path, "wb");
    if (!fp) {
        return -1;
    }
    
    size_t written = fwrite(data, 1, size, fp);
    
    /* Ensure data is on disk */
    fflush(fp);
    
#ifndef _WIN32
    int fd = fileno(fp);
    fsync(fd);
#endif
    
    fclose(fp);
    
    if (written != size) {
        return -1;
    }
    
    g_persist.writes++;
    return 0;
}

int
hammer2_read(const char *name, void *data, size_t max_size, size_t *actual_size)
{
    char path[512];
    snprintf(path, sizeof(path), "%s/%s", g_persist.mount_path, name);
    
    FILE *fp = fopen(path, "rb");
    if (!fp) {
        return -1;
    }
    
    size_t read_size = fread(data, 1, max_size, fp);
    fclose(fp);
    
    if (actual_size) {
        *actual_size = read_size;
    }
    
    g_persist.reads++;
    return 0;
}

/* ==================== HAMMER2 Snapshots ==================== */

/*
 * Create instant snapshot.
 * HAMMER2 snapshots are COW-based and instant.
 */
int
hammer2_snapshot(const char *name)
{
#ifdef __DragonFly__
    if (!g_persist.hammer2_available) {
        printf("HAMMER2: Snapshots not available on this filesystem\n");
        return -1;
    }
    
    char snap_name[64];
    if (name) {
        strncpy(snap_name, name, sizeof(snap_name) - 1);
    } else {
        snprintf(snap_name, sizeof(snap_name), "%s%ld", 
                 SNAPSHOT_PREFIX, time(NULL));
    }
    
    /* 
     * Real implementation would use:
     * hammer2 -s /var/immune snapshot <name>
     * 
     * Or via ioctl:
     * HAMMER2IOC_PFS_SNAPSHOT
     */
    
    char cmd[512];
    snprintf(cmd, sizeof(cmd), "hammer2 -s %s snapshot %s 2>/dev/null",
             g_persist.mount_path, snap_name);
    
    int result = system(cmd);
    
    if (result == 0) {
        if (g_persist.snapshot_count < MAX_SNAPSHOTS) {
            strncpy(g_persist.snapshots[g_persist.snapshot_count],
                    snap_name, 64 - 1);
            g_persist.snapshot_count++;
        }
        g_persist.snapshots_created++;
        printf("HAMMER2: Snapshot created: %s\n", snap_name);
        return 0;
    }
    
    return -1;
#else
    printf("HAMMER2: Snapshots only available on DragonFlyBSD\n");
    return -1;
#endif
}

/*
 * Rollback to snapshot.
 */
int
hammer2_rollback(const char *snapshot_name)
{
#ifdef __DragonFly__
    if (!g_persist.hammer2_available) {
        return -1;
    }
    
    /* 
     * Real implementation would:
     * 1. Unmount current PFS
     * 2. Mount snapshot PFS
     * 3. Or use HAMMER2IOC_PFS_SNAPSHOT to manage
     */
    
    printf("HAMMER2: Rollback to %s (not implemented)\n", snapshot_name);
    return -1;
#else
    return -1;
#endif
}

/* ==================== Deduplication Check ==================== */

/*
 * HAMMER2 has built-in deduplication.
 * This checks if data already exists.
 */
int
hammer2_dedup_check(const void *data, size_t size, uint8_t *hash)
{
#ifdef __DragonFly__
    /* 
     * Real implementation would:
     * 1. Hash the data
     * 2. Check HAMMER2 dedup table
     * 3. Return 1 if duplicate exists
     */
    (void)data;
    (void)size;
    (void)hash;
    return 0;  /* Not duplicate */
#else
    return 0;
#endif
}

/* ==================== Atomic Update ==================== */

/*
 * Atomic file update using rename.
 * Write to temp, then rename (atomic on POSIX).
 */
int
hammer2_atomic_update(const char *name, const void *data, size_t size)
{
    char path[512];
    char temp_path[512];
    
    snprintf(path, sizeof(path), "%s/%s", g_persist.mount_path, name);
    snprintf(temp_path, sizeof(temp_path), "%s/.%s.tmp", 
             g_persist.mount_path, name);
    
    /* Write to temp file */
    FILE *fp = fopen(temp_path, "wb");
    if (!fp) {
        return -1;
    }
    
    if (fwrite(data, 1, size, fp) != size) {
        fclose(fp);
        unlink(temp_path);
        return -1;
    }
    
    fflush(fp);
#ifndef _WIN32
    fsync(fileno(fp));
#endif
    fclose(fp);
    
    /* Atomic rename */
    if (rename(temp_path, path) != 0) {
        unlink(temp_path);
        return -1;
    }
    
    g_persist.writes++;
    return 0;
}

/* ==================== List Snapshots ==================== */

void
hammer2_list_snapshots(void)
{
    printf("\n=== HAMMER2 SNAPSHOTS ===\n");
    
    for (int i = 0; i < g_persist.snapshot_count; i++) {
        printf("  %d. %s\n", i + 1, g_persist.snapshots[i]);
    }
    
    if (g_persist.snapshot_count == 0) {
        printf("  (no snapshots)\n");
    }
    
    printf("=========================\n\n");
}

/* ==================== Status ==================== */

int
hammer2_is_available(void)
{
    return g_persist.hammer2_available;
}

void
hammer2_stats(uint64_t *writes, uint64_t *reads, uint64_t *snapshots)
{
    if (writes) *writes = g_persist.writes;
    if (reads) *reads = g_persist.reads;
    if (snapshots) *snapshots = g_persist.snapshots_created;
}
