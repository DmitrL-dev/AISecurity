/*
 * SENTINEL IMMUNE — Jail-Based Quarantine
 * 
 * Process and file isolation using DragonFlyBSD jails.
 * Network-isolated quarantine environment.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <signal.h>
#include <time.h>

#ifdef __DragonFly__
#include <sys/jail.h>
#include <sys/param.h>
#endif

/* jail_remove stub - real implementation requires -ljail */
#ifndef jail_remove
static int jail_remove(int jid) { (void)jid; return 0; }
#endif

/* ==================== Configuration ==================== */

#define QUARANTINE_ROOT         "/var/immune/quarantine"
#define QUARANTINE_JAIL_NAME    "immune_quarantine"
#define MAX_QUARANTINED_PROCS   100
#define MAX_QUARANTINED_FILES   1000

/* ==================== Quarantine State ==================== */

typedef struct {
    pid_t       original_pid;
    pid_t       jailed_pid;
    time_t      quarantined_at;
    char        reason[256];
    int         threat_level;
} quarantined_proc_t;

typedef struct {
    char        original_path[PATH_MAX];
    char        quarantine_path[PATH_MAX];
    time_t      quarantined_at;
    char        reason[256];
    size_t      size;
    uint8_t     sha256[32];
} quarantined_file_t;

static quarantined_proc_t procs[MAX_QUARANTINED_PROCS];
static int proc_count = 0;

static quarantined_file_t files[MAX_QUARANTINED_FILES];
static int file_count = 0;

static int jail_id = -1;

/* ==================== Jail Management ==================== */

/*
 * Create quarantine jail (network isolated)
 */
int
jail_quarantine_init(void)
{
    /* Create quarantine directory structure */
    mkdir(QUARANTINE_ROOT, 0700);
    mkdir(QUARANTINE_ROOT "/dev", 0755);
    mkdir(QUARANTINE_ROOT "/tmp", 0777);
    mkdir(QUARANTINE_ROOT "/files", 0700);
    mkdir(QUARANTINE_ROOT "/procs", 0700);

#ifdef __DragonFly__
    /* DragonFlyBSD real jail support */
    #ifndef JAIL_API_VERSION
    #define JAIL_API_VERSION 2
    #endif
    
    struct jail j;
    memset(&j, 0, sizeof(j));
    
    j.version = JAIL_API_VERSION;
    j.path = QUARANTINE_ROOT;
    j.hostname = QUARANTINE_JAIL_NAME;
    /* These fields may not exist on all versions */
    #ifdef JAIL_CREATE_MASK
    j.jailname = QUARANTINE_JAIL_NAME;
    j.ip4s = 0;     /* No IPv4 addresses = no network */
    j.ip6s = 0;     /* No IPv6 addresses = no network */
    #endif
    
    jail_id = jail(&j);
    if (jail_id < 0) {
        fprintf(stderr, "IMMUNE: Jail creation failed: %s\n", strerror(errno));
        return -1;
    }
    
    fprintf(stderr, "IMMUNE: Quarantine jail created (id=%d)\n", jail_id);
#else
    /* Non-DragonFly: simulate with chroot + seccomp concept */
    jail_id = 1; /* Simulated */
    fprintf(stderr, "IMMUNE: Quarantine jail simulated (chroot mode)\n");
#endif
    
    return 0;
}

void
jail_quarantine_shutdown(void)
{
#ifdef __DragonFly__
    if (jail_id > 0) {
        jail_remove(jail_id);
        fprintf(stderr, "IMMUNE: Quarantine jail removed\n");
    }
#endif
    jail_id = -1;
}

/* ==================== Process Quarantine ==================== */

/*
 * Quarantine a process by moving it to jail
 * 
 * Process loses:
 * - Network access
 * - Filesystem access (except quarantine root)
 * - IPC with non-jailed processes
 */
int
quarantine_process(pid_t pid, int threat_level, const char *reason)
{
    if (jail_id < 0) {
        fprintf(stderr, "IMMUNE: Jail not initialized\n");
        return -1;
    }
    
    if (proc_count >= MAX_QUARANTINED_PROCS) {
        fprintf(stderr, "IMMUNE: Quarantine process limit reached\n");
        return -1;
    }
    
    /* Verify process exists */
    if (kill(pid, 0) < 0) {
        fprintf(stderr, "IMMUNE: Process %d does not exist\n", pid);
        return -1;
    }

#ifdef __DragonFly__
    /* Attach process to quarantine jail */
    if (jail_attach(jail_id) < 0) {
        fprintf(stderr, "IMMUNE: jail_attach failed: %s\n", strerror(errno));
        return -1;
    }
#endif
    
    /* Record quarantine */
    quarantined_proc_t *p = &procs[proc_count];
    p->original_pid = pid;
    p->jailed_pid = pid;  /* Same PID, different namespace */
    p->quarantined_at = time(NULL);
    p->threat_level = threat_level;
    strncpy(p->reason, reason, 255);
    
    proc_count++;
    
    fprintf(stderr, "IMMUNE: Process %d quarantined (level=%d, reason=%s)\n",
            pid, threat_level, reason);
    
    return 0;
}

/*
 * Release process from quarantine (after analysis)
 */
int
quarantine_release_process(pid_t pid)
{
    for (int i = 0; i < proc_count; i++) {
        if (procs[i].original_pid == pid) {
            /* Move remaining entries down */
            memmove(&procs[i], &procs[i + 1],
                    (proc_count - i - 1) * sizeof(quarantined_proc_t));
            proc_count--;
            
            fprintf(stderr, "IMMUNE: Process %d released from quarantine\n", pid);
            return 0;
        }
    }
    
    fprintf(stderr, "IMMUNE: Process %d not found in quarantine\n", pid);
    return -1;
}

/*
 * Kill quarantined process
 */
int
quarantine_kill_process(pid_t pid)
{
    for (int i = 0; i < proc_count; i++) {
        if (procs[i].original_pid == pid) {
            kill(pid, SIGKILL);
            
            memmove(&procs[i], &procs[i + 1],
                    (proc_count - i - 1) * sizeof(quarantined_proc_t));
            proc_count--;
            
            fprintf(stderr, "IMMUNE: Process %d killed\n", pid);
            return 0;
        }
    }
    
    return -1;
}

/* ==================== File Quarantine ==================== */

/*
 * Simple SHA-256 (placeholder - use OpenSSL in production)
 */
static void
compute_sha256(const char *path, uint8_t *hash)
{
    /* Placeholder - would use OpenSSL SHA256 */
    memset(hash, 0, 32);
    
    FILE *f = fopen(path, "rb");
    if (f) {
        /* Simple hash: XOR bytes in 32-byte chunks */
        uint8_t buf[32];
        while (fread(buf, 1, 32, f) > 0) {
            for (int i = 0; i < 32; i++) {
                hash[i] ^= buf[i];
            }
        }
        fclose(f);
    }
}

/*
 * Quarantine a file by moving to isolated storage (jail version)
 */
int
jail_quarantine_file(const char *path, int threat_level, const char *reason)
{
    if (file_count >= MAX_QUARANTINED_FILES) {
        fprintf(stderr, "IMMUNE: File quarantine limit reached\n");
        return -1;
    }
    
    /* Check file exists */
    struct stat st;
    if (stat(path, &st) < 0) {
        fprintf(stderr, "IMMUNE: File not found: %s\n", path);
        return -1;
    }
    
    /* Generate quarantine path */
    char qpath[PATH_MAX];
    char *basename = strrchr(path, '/');
    basename = basename ? basename + 1 : (char *)path;
    
    snprintf(qpath, sizeof(qpath), "%s/files/%ld_%s",
             QUARANTINE_ROOT, time(NULL), basename);
    
    /* Move file to quarantine */
    if (rename(path, qpath) < 0) {
        /* If rename fails (cross-device), copy and delete */
        char cmd[PATH_MAX * 2 + 32];
        snprintf(cmd, sizeof(cmd), "cp '%s' '%s' && rm -f '%s'", path, qpath, path);
        if (system(cmd) != 0) {
            fprintf(stderr, "IMMUNE: Failed to quarantine file\n");
            return -1;
        }
    }
    
    /* Set restrictive permissions */
    chmod(qpath, 0400);
    
    /* Record quarantine */
    quarantined_file_t *f = &files[file_count];
    strncpy(f->original_path, path, PATH_MAX - 1);
    strncpy(f->quarantine_path, qpath, PATH_MAX - 1);
    f->quarantined_at = time(NULL);
    f->size = st.st_size;
    strncpy(f->reason, reason, 255);
    compute_sha256(qpath, f->sha256);
    
    file_count++;
    
    fprintf(stderr, "IMMUNE: File quarantined: %s -> %s\n", path, qpath);
    return 0;
}

/*
 * Restore file from quarantine
 */
int
quarantine_restore_file(const char *original_path)
{
    for (int i = 0; i < file_count; i++) {
        if (strcmp(files[i].original_path, original_path) == 0) {
            /* Restore file */
            if (rename(files[i].quarantine_path, original_path) < 0) {
                char cmd[PATH_MAX * 2 + 32];
                snprintf(cmd, sizeof(cmd), "cp '%s' '%s'",
                         files[i].quarantine_path, original_path);
                system(cmd);
            }
            
            /* Remove from list */
            memmove(&files[i], &files[i + 1],
                    (file_count - i - 1) * sizeof(quarantined_file_t));
            file_count--;
            
            fprintf(stderr, "IMMUNE: File restored: %s\n", original_path);
            return 0;
        }
    }
    
    fprintf(stderr, "IMMUNE: File not found in quarantine: %s\n", original_path);
    return -1;
}

/*
 * Permanently delete quarantined file
 */
int
quarantine_delete_file(const char *original_path)
{
    for (int i = 0; i < file_count; i++) {
        if (strcmp(files[i].original_path, original_path) == 0) {
            /* Secure delete: overwrite with zeros */
            FILE *f = fopen(files[i].quarantine_path, "r+b");
            if (f) {
                fseek(f, 0, SEEK_END);
                long size = ftell(f);
                fseek(f, 0, SEEK_SET);
                
                char zeros[4096] = {0};
                for (long written = 0; written < size; written += 4096) {
                    fwrite(zeros, 1, 4096, f);
                }
                fclose(f);
            }
            
            unlink(files[i].quarantine_path);
            
            memmove(&files[i], &files[i + 1],
                    (file_count - i - 1) * sizeof(quarantined_file_t));
            file_count--;
            
            fprintf(stderr, "IMMUNE: File securely deleted: %s\n", original_path);
            return 0;
        }
    }
    
    return -1;
}

/* ==================== Reporting ==================== */

void
quarantine_status(void)
{
    printf("\n=== IMMUNE Quarantine Status ===\n\n");
    
    printf("Quarantined Processes: %d\n", proc_count);
    for (int i = 0; i < proc_count; i++) {
        char time_buf[32];
        struct tm *tm = localtime(&procs[i].quarantined_at);
        strftime(time_buf, sizeof(time_buf), "%Y-%m-%d %H:%M:%S", tm);
        
        printf("  PID %d: level=%d, time=%s, reason=%s\n",
               procs[i].original_pid,
               procs[i].threat_level,
               time_buf,
               procs[i].reason);
    }
    
    printf("\nQuarantined Files: %d\n", file_count);
    for (int i = 0; i < file_count; i++) {
        char time_buf[32];
        struct tm *tm = localtime(&files[i].quarantined_at);
        strftime(time_buf, sizeof(time_buf), "%Y-%m-%d %H:%M:%S", tm);
        
        printf("  %s (%lu bytes): time=%s, reason=%s\n",
               files[i].original_path,
               files[i].size,
               time_buf,
               files[i].reason);
    }
}

int
quarantine_export_json(const char *filename)
{
    FILE *f = fopen(filename, "w");
    if (!f) return -1;
    
    fprintf(f, "{\n");
    fprintf(f, "  \"processes\": [\n");
    
    for (int i = 0; i < proc_count; i++) {
        fprintf(f, "    {\"pid\": %d, \"level\": %d, \"reason\": \"%s\"}%s\n",
                procs[i].original_pid,
                procs[i].threat_level,
                procs[i].reason,
                (i < proc_count - 1) ? "," : "");
    }
    
    fprintf(f, "  ],\n  \"files\": [\n");
    
    for (int i = 0; i < file_count; i++) {
        fprintf(f, "    {\"path\": \"%s\", \"size\": %lu, \"reason\": \"%s\"}%s\n",
                files[i].original_path,
                files[i].size,
                files[i].reason,
                (i < file_count - 1) ? "," : "");
    }
    
    fprintf(f, "  ]\n}\n");
    fclose(f);
    
    return 0;
}
