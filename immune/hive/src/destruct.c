/*
 * SENTINEL IMMUNE — Self-Destruct Module
 * 
 * Tamper detection and secure destruction.
 * Pure C implementation.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#ifdef _WIN32
    #include <windows.h>
#else
    #include <unistd.h>
    #include <sys/stat.h>
    #include <dirent.h>
    #include <fcntl.h>
#endif

#include "../include/hive.h"

#define MAX_WATCH_PATHS     100
#define MAX_SENSITIVE_PATHS 50
#define TAMPER_MAGIC        0x54414D50  /* "TAMP" */

/* Tamper types */
typedef enum {
    TAMPER_NONE = 0,
    TAMPER_FILE_MODIFIED,
    TAMPER_FILE_DELETED,
    TAMPER_DEBUGGER,
    TAMPER_INTEGRITY,
    TAMPER_UNAUTHORIZED
} tamper_type_t;

/* Integrity record */
typedef struct {
    char        path[512];
    uint8_t     hash[32];
    size_t      size;
    time_t      mtime;
    int         active;
} integrity_record_t;

/* Self-destruct context */
typedef struct {
    /* Configuration */
    int         enabled;
    int         armed;
    
    /* Watch paths */
    integrity_record_t  watch[MAX_WATCH_PATHS];
    int                 watch_count;
    
    /* Sensitive paths (to destroy) */
    char        sensitive[MAX_SENSITIVE_PATHS][512];
    int         sensitive_count;
    
    /* Statistics */
    int         tamper_events;
    time_t      last_check;
} destruct_ctx_t;

/* Global context */
static destruct_ctx_t g_destruct;

/* ==================== Hashing ==================== */

/* Simple hash - would use SHA-256 in production */
static void
simple_hash(const void *data, size_t len, uint8_t *hash)
{
    memset(hash, 0, 32);
    
    const uint8_t *p = (const uint8_t *)data;
    for (size_t i = 0; i < len; i++) {
        hash[i % 32] ^= p[i];
        hash[(i + 7) % 32] += p[i];
    }
}

/* ==================== Initialization ==================== */

int
destruct_init(void)
{
    memset(&g_destruct, 0, sizeof(destruct_ctx_t));
    g_destruct.last_check = time(NULL);
    
    printf("DESTRUCT: Self-destruct module initialized\n");
    return 0;
}

void
destruct_shutdown(void)
{
    printf("DESTRUCT: Shutdown complete\n");
}

/* ==================== Path Management ==================== */

/* Add path to watch for tampering */
int
destruct_watch(const char *path)
{
    if (!path || g_destruct.watch_count >= MAX_WATCH_PATHS)
        return -1;
    
    integrity_record_t *rec = &g_destruct.watch[g_destruct.watch_count];
    
    strncpy(rec->path, path, sizeof(rec->path) - 1);
    rec->active = 1;
    
    /* Get file info */
    FILE *fp = fopen(path, "rb");
    if (fp) {
        fseek(fp, 0, SEEK_END);
        rec->size = ftell(fp);
        fseek(fp, 0, SEEK_SET);
        
        if (rec->size > 0 && rec->size < 1024 * 1024) {
            uint8_t *data = malloc(rec->size);
            if (data) {
                fread(data, 1, rec->size, fp);
                simple_hash(data, rec->size, rec->hash);
                free(data);
            }
        }
        
        fclose(fp);
    }
    
#ifndef _WIN32
    struct stat st;
    if (stat(path, &st) == 0) {
        rec->mtime = st.st_mtime;
    }
#endif
    
    g_destruct.watch_count++;
    return 0;
}

/* Add sensitive path to destroy on trigger */
int
destruct_mark_sensitive(const char *path)
{
    if (!path || g_destruct.sensitive_count >= MAX_SENSITIVE_PATHS)
        return -1;
    
    strncpy(g_destruct.sensitive[g_destruct.sensitive_count], path,
            sizeof(g_destruct.sensitive[0]) - 1);
    
    g_destruct.sensitive_count++;
    return 0;
}

/* ==================== Tamper Detection ==================== */

/* Check for debugger */
static int
check_debugger(void)
{
#ifdef _WIN32
    return IsDebuggerPresent();
#else
    /* Check /proc/self/status on Linux */
    FILE *fp = fopen("/proc/self/status", "r");
    if (fp) {
        char line[256];
        while (fgets(line, sizeof(line), fp)) {
            if (strncmp(line, "TracerPid:", 10) == 0) {
                int pid = atoi(line + 10);
                fclose(fp);
                return pid != 0;
            }
        }
        fclose(fp);
    }
    return 0;
#endif
}

/* Check integrity of watched files */
static tamper_type_t
check_integrity(void)
{
    for (int i = 0; i < g_destruct.watch_count; i++) {
        integrity_record_t *rec = &g_destruct.watch[i];
        if (!rec->active) continue;
        
        FILE *fp = fopen(rec->path, "rb");
        if (!fp) {
            return TAMPER_FILE_DELETED;
        }
        
        fseek(fp, 0, SEEK_END);
        size_t size = ftell(fp);
        fseek(fp, 0, SEEK_SET);
        
        if (size != rec->size) {
            fclose(fp);
            return TAMPER_FILE_MODIFIED;
        }
        
        if (size > 0 && size < 1024 * 1024) {
            uint8_t *data = malloc(size);
            if (data) {
                fread(data, 1, size, fp);
                
                uint8_t hash[32];
                simple_hash(data, size, hash);
                
                free(data);
                
                if (memcmp(hash, rec->hash, 32) != 0) {
                    fclose(fp);
                    return TAMPER_FILE_MODIFIED;
                }
            }
        }
        
        fclose(fp);
    }
    
    return TAMPER_NONE;
}

/* Main tamper check */
tamper_type_t
destruct_check(void)
{
    tamper_type_t result = TAMPER_NONE;
    
    /* Check debugger */
    if (check_debugger()) {
        result = TAMPER_DEBUGGER;
        g_destruct.tamper_events++;
    }
    
    /* Check integrity */
    if (result == TAMPER_NONE) {
        result = check_integrity();
        if (result != TAMPER_NONE) {
            g_destruct.tamper_events++;
        }
    }
    
    g_destruct.last_check = time(NULL);
    
    return result;
}

/* ==================== Destruction ==================== */

/* Secure file wipe - overwrite with random data */
static void
secure_wipe(const char *path)
{
#ifdef _WIN32
    HANDLE hFile = CreateFileA(path, GENERIC_WRITE, 0, NULL, 
                               OPEN_EXISTING, 0, NULL);
    if (hFile != INVALID_HANDLE_VALUE) {
        LARGE_INTEGER size;
        GetFileSizeEx(hFile, &size);
        
        /* Overwrite 3 times */
        uint8_t buf[4096];
        for (int pass = 0; pass < 3; pass++) {
            SetFilePointer(hFile, 0, NULL, FILE_BEGIN);
            
            LONGLONG remaining = size.QuadPart;
            while (remaining > 0) {
                DWORD to_write = (remaining > sizeof(buf)) ? 
                                 sizeof(buf) : (DWORD)remaining;
                
                /* Fill with pattern */
                memset(buf, (pass == 0) ? 0x00 : 
                            (pass == 1) ? 0xFF : 0x5A, to_write);
                
                DWORD written;
                WriteFile(hFile, buf, to_write, &written, NULL);
                remaining -= written;
            }
            FlushFileBuffers(hFile);
        }
        
        CloseHandle(hFile);
    }
    DeleteFileA(path);
#else
    int fd = open(path, O_WRONLY);
    if (fd >= 0) {
        struct stat st;
        fstat(fd, &st);
        
        uint8_t buf[4096];
        
        /* Overwrite 3 times */
        for (int pass = 0; pass < 3; pass++) {
            lseek(fd, 0, SEEK_SET);
            
            off_t remaining = st.st_size;
            while (remaining > 0) {
                size_t to_write = (remaining > sizeof(buf)) ?
                                  sizeof(buf) : remaining;
                
                memset(buf, (pass == 0) ? 0x00 :
                            (pass == 1) ? 0xFF : 0x5A, to_write);
                
                ssize_t written = write(fd, buf, to_write);
                if (written <= 0) break;
                remaining -= written;
            }
            fsync(fd);
        }
        
        close(fd);
    }
    unlink(path);
#endif
    
    printf("DESTRUCT: Wiped %s\n", path);
}

/* Trigger self-destruct */
void
destruct_trigger(const char *reason)
{
    if (!g_destruct.armed) {
        printf("DESTRUCT: Not armed, ignoring trigger\n");
        return;
    }
    
    printf("DESTRUCT: *** SELF-DESTRUCT TRIGGERED ***\n");
    printf("DESTRUCT: Reason: %s\n", reason ? reason : "Unknown");
    
    /* Wipe all sensitive data */
    for (int i = 0; i < g_destruct.sensitive_count; i++) {
        secure_wipe(g_destruct.sensitive[i]);
    }
    
    printf("DESTRUCT: Complete - %d files destroyed\n", 
           g_destruct.sensitive_count);
}

/* ==================== Control ==================== */

void
destruct_enable(void)
{
    g_destruct.enabled = 1;
    printf("DESTRUCT: Enabled\n");
}

void
destruct_disable(void)
{
    g_destruct.enabled = 0;
    printf("DESTRUCT: Disabled\n");
}

void
destruct_arm(void)
{
    g_destruct.armed = 1;
    printf("DESTRUCT: *** ARMED ***\n");
}

void
destruct_disarm(void)
{
    g_destruct.armed = 0;
    printf("DESTRUCT: Disarmed\n");
}

/* Get status */
void
destruct_status(int *enabled, int *armed, int *events)
{
    if (enabled) *enabled = g_destruct.enabled;
    if (armed) *armed = g_destruct.armed;
    if (events) *events = g_destruct.tamper_events;
}
