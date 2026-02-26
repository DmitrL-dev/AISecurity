/*
 * SENTINEL IMMUNE — HAMMER2 Forensics Integration
 * 
 * Instant snapshots and rollback using HAMMER2 COW filesystem.
 * DragonFlyBSD specific.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <errno.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>

#ifdef __DragonFly__
#include <sys/ioctl.h>
#include <vfs/hammer2/hammer2_ioctl.h>
#endif

/* ==================== Configuration ==================== */

#define HAMMER2_MOUNT_POINT     "/var/immune"
#define HAMMER2_SNAPSHOT_PREFIX "immune_snap"
#define MAX_SNAPSHOTS           100
#define SNAPSHOT_NAME_LEN       64

/* ==================== Snapshot Management ==================== */

typedef struct {
    char    name[SNAPSHOT_NAME_LEN];
    time_t  created;
    char    reason[128];
} immune_snapshot_t;

static immune_snapshot_t snapshots[MAX_SNAPSHOTS];
static int snapshot_count = 0;

/*
 * Generate snapshot name with timestamp
 */
static void
generate_snapshot_name(char *buf, size_t len, const char *reason)
{
    time_t now = time(NULL);
    struct tm *tm = localtime(&now);
    
    snprintf(buf, len, "%s_%04d%02d%02d_%02d%02d%02d_%s",
             HAMMER2_SNAPSHOT_PREFIX,
             tm->tm_year + 1900, tm->tm_mon + 1, tm->tm_mday,
             tm->tm_hour, tm->tm_min, tm->tm_sec,
             reason);
}

/*
 * Create instant HAMMER2 snapshot
 * 
 * HAMMER2 COW makes this O(1) - no data copying!
 */
int
hammer2_snapshot_create(const char *reason)
{
    char snap_name[SNAPSHOT_NAME_LEN];
    
    generate_snapshot_name(snap_name, sizeof(snap_name), reason);
    
#ifdef __DragonFly__
    /* Real HAMMER2 ioctl */
    int fd = open(HAMMER2_MOUNT_POINT, O_RDONLY);
    if (fd < 0) {
        fprintf(stderr, "IMMUNE: Cannot open %s: %s\n",
                HAMMER2_MOUNT_POINT, strerror(errno));
        return -1;
    }
    
    hammer2_ioc_pfs_t pfs;
    memset(&pfs, 0, sizeof(pfs));
    strncpy(pfs.name, snap_name, sizeof(pfs.name) - 1);
    
    if (ioctl(fd, HAMMER2IOC_PFS_SNAPSHOT, &pfs) < 0) {
        fprintf(stderr, "IMMUNE: Snapshot failed: %s\n", strerror(errno));
        close(fd);
        return -1;
    }
    
    close(fd);
#else
    /* Non-DragonFly: simulate with command */
    char cmd[512];
    snprintf(cmd, sizeof(cmd), 
             "echo 'SIMULATE: hammer2 pfs-snapshot %s @%s'",
             HAMMER2_MOUNT_POINT, snap_name);
    system(cmd);
#endif
    
    /* Record snapshot */
    if (snapshot_count < MAX_SNAPSHOTS) {
        strncpy(snapshots[snapshot_count].name, snap_name, SNAPSHOT_NAME_LEN - 1);
        snapshots[snapshot_count].created = time(NULL);
        strncpy(snapshots[snapshot_count].reason, reason, 127);
        snapshot_count++;
    }
    
    fprintf(stderr, "IMMUNE: Created snapshot @%s\n", snap_name);
    return 0;
}

/*
 * Rollback to snapshot
 */
int
hammer2_snapshot_rollback(const char *snap_name)
{
#ifdef __DragonFly__
    char cmd[512];
    snprintf(cmd, sizeof(cmd),
             "hammer2 pfs-rollback %s @%s",
             HAMMER2_MOUNT_POINT, snap_name);
    
    int ret = system(cmd);
    if (ret != 0) {
        fprintf(stderr, "IMMUNE: Rollback failed\n");
        return -1;
    }
#else
    fprintf(stderr, "IMMUNE: SIMULATE rollback to @%s\n", snap_name);
#endif
    
    return 0;
}

/*
 * Delete old snapshots (keep last N)
 */
int
hammer2_snapshot_cleanup(int keep_count)
{
    if (snapshot_count <= keep_count)
        return 0;
    
    int to_delete = snapshot_count - keep_count;
    
    for (int i = 0; i < to_delete; i++) {
#ifdef __DragonFly__
        char cmd[512];
        snprintf(cmd, sizeof(cmd),
                 "hammer2 pfs-delete %s @%s",
                 HAMMER2_MOUNT_POINT, snapshots[i].name);
        system(cmd);
#endif
        fprintf(stderr, "IMMUNE: Deleted old snapshot @%s\n", snapshots[i].name);
    }
    
    /* Shift remaining snapshots */
    memmove(snapshots, &snapshots[to_delete],
            (snapshot_count - to_delete) * sizeof(immune_snapshot_t));
    snapshot_count -= to_delete;
    
    return to_delete;
}

/*
 * List all snapshots
 */
void
hammer2_snapshot_list(void)
{
    printf("IMMUNE Snapshots (%d):\n", snapshot_count);
    printf("%-40s %-20s %s\n", "Name", "Created", "Reason");
    printf("%-40s %-20s %s\n", "----", "-------", "------");
    
    for (int i = 0; i < snapshot_count; i++) {
        char time_buf[32];
        struct tm *tm = localtime(&snapshots[i].created);
        strftime(time_buf, sizeof(time_buf), "%Y-%m-%d %H:%M:%S", tm);
        
        printf("%-40s %-20s %s\n",
               snapshots[i].name,
               time_buf,
               snapshots[i].reason);
    }
}

/* ==================== Forensics Timeline ==================== */

typedef struct {
    time_t      timestamp;
    char        event_type[32];
    char        details[256];
    char        snapshot[SNAPSHOT_NAME_LEN];
} forensic_event_t;

#define MAX_FORENSIC_EVENTS 1000
static forensic_event_t forensic_timeline[MAX_FORENSIC_EVENTS];
static int forensic_count = 0;

/*
 * Record forensic event with automatic snapshot
 */
int
forensic_record(const char *event_type, const char *details, int create_snapshot)
{
    if (forensic_count >= MAX_FORENSIC_EVENTS) {
        /* Rotate: remove oldest 10% */
        int to_remove = MAX_FORENSIC_EVENTS / 10;
        memmove(forensic_timeline, &forensic_timeline[to_remove],
                (forensic_count - to_remove) * sizeof(forensic_event_t));
        forensic_count -= to_remove;
    }
    
    forensic_event_t *event = &forensic_timeline[forensic_count];
    event->timestamp = time(NULL);
    strncpy(event->event_type, event_type, 31);
    strncpy(event->details, details, 255);
    event->snapshot[0] = '\0';
    
    if (create_snapshot) {
        char snap_reason[64];
        snprintf(snap_reason, sizeof(snap_reason), "%s_%d", event_type, forensic_count);
        hammer2_snapshot_create(snap_reason);
        strncpy(event->snapshot, snapshots[snapshot_count - 1].name, SNAPSHOT_NAME_LEN - 1);
    }
    
    forensic_count++;
    return 0;
}

/*
 * Export forensic timeline to JSON
 */
int
forensic_export_json(const char *filename)
{
    FILE *f = fopen(filename, "w");
    if (!f) {
        fprintf(stderr, "IMMUNE: Cannot create %s\n", filename);
        return -1;
    }
    
    fprintf(f, "{\n  \"timeline\": [\n");
    
    for (int i = 0; i < forensic_count; i++) {
        char time_buf[32];
        struct tm *tm = localtime(&forensic_timeline[i].timestamp);
        strftime(time_buf, sizeof(time_buf), "%Y-%m-%dT%H:%M:%S", tm);
        
        fprintf(f, "    {\n");
        fprintf(f, "      \"timestamp\": \"%s\",\n", time_buf);
        fprintf(f, "      \"event_type\": \"%s\",\n", forensic_timeline[i].event_type);
        fprintf(f, "      \"details\": \"%s\",\n", forensic_timeline[i].details);
        fprintf(f, "      \"snapshot\": \"%s\"\n", forensic_timeline[i].snapshot);
        fprintf(f, "    }%s\n", (i < forensic_count - 1) ? "," : "");
    }
    
    fprintf(f, "  ]\n}\n");
    fclose(f);
    
    fprintf(stderr, "IMMUNE: Exported %d events to %s\n", forensic_count, filename);
    return 0;
}

/* ==================== Integration with Quarantine ==================== */

/*
 * Pre-quarantine snapshot: capture state before isolating threat
 */
int
quarantine_with_snapshot(const char *threat_path, const char *threat_type)
{
    char details[256];
    snprintf(details, sizeof(details), "Quarantine: %s (%s)", threat_path, threat_type);
    
    /* 1. Create snapshot BEFORE quarantine */
    forensic_record("PRE_QUARANTINE", details, 1);
    
    /* 2. Perform quarantine (would call quarantine.c) */
    fprintf(stderr, "IMMUNE: Quarantining %s\n", threat_path);
    
    /* 3. Record post-quarantine state */
    forensic_record("POST_QUARANTINE", details, 0);
    
    return 0;
}

/*
 * Rollback quarantine if false positive
 */
int
quarantine_rollback(const char *threat_path)
{
    /* Find pre-quarantine snapshot */
    for (int i = forensic_count - 1; i >= 0; i--) {
        if (strcmp(forensic_timeline[i].event_type, "PRE_QUARANTINE") == 0 &&
            strstr(forensic_timeline[i].details, threat_path) != NULL) {
            
            fprintf(stderr, "IMMUNE: Rolling back to @%s\n", forensic_timeline[i].snapshot);
            hammer2_snapshot_rollback(forensic_timeline[i].snapshot);
            
            forensic_record("ROLLBACK", threat_path, 0);
            return 0;
        }
    }
    
    fprintf(stderr, "IMMUNE: No pre-quarantine snapshot found for %s\n", threat_path);
    return -1;
}
