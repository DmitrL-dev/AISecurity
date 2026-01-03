/*
 * SENTINEL IMMUNE — BSD Kernel Hooks
 * 
 * DragonFlyBSD/FreeBSD syscall interception.
 */

#include <sys/param.h>
#include <sys/systm.h>
#include <sys/kernel.h>
#include <sys/proc.h>
#include <sys/sysent.h>
#include <sys/sysproto.h>
#include <sys/lock.h>
#include <sys/mutex.h>
#include <sys/malloc.h>

#include "../include/hooks.h"

/* External module functions */
extern int immune_kmod_enabled(void);
extern int immune_kmod_strict(void);
extern void immune_kmod_inc_scan(void);
extern void immune_kmod_inc_threat(void);
extern void immune_kmod_inc_blocked(void);

/* External scanner */
extern int immune_kern_scan(const char *data, size_t len);

/* Original syscall handlers */
static sy_call_t *orig_read = NULL;
static sy_call_t *orig_write = NULL;
static sy_call_t *orig_execve = NULL;
static sy_call_t *orig_open = NULL;
static sy_call_t *orig_connect = NULL;

/* Hook state */
static struct mtx hook_mtx;
static int hooks_installed = 0;

/* Inspection buffer */
#define INSPECT_BUF_SIZE    4096
MALLOC_DECLARE(M_IMMUNE);

/* ==================== Read Hook ==================== */

static int
immune_read_hook(struct thread *td, void *args)
{
    struct read_args *uap = (struct read_args *)args;
    int result;
    
    /* Call original first */
    result = orig_read(td, args);
    
    if (!immune_kmod_enabled())
        return result;
    
    /* Post-read inspection */
    if (result == 0 && uap->nbyte > 0 && uap->nbyte <= INSPECT_BUF_SIZE) {
        char *buf = malloc(uap->nbyte + 1, M_IMMUNE, M_NOWAIT);
        
        if (buf) {
            if (copyin(uap->buf, buf, uap->nbyte) == 0) {
                buf[uap->nbyte] = '\0';
                
                immune_kmod_inc_scan();
                
                int threat = immune_kern_scan(buf, uap->nbyte);
                if (threat > 0) {
                    immune_kmod_inc_threat();
                    printf("IMMUNE: Threat detected in read()\n");
                }
            }
            free(buf, M_IMMUNE);
        }
    }
    
    return result;
}

/* ==================== Write Hook ==================== */

static int
immune_write_hook(struct thread *td, void *args)
{
    struct write_args *uap = (struct write_args *)args;
    
    if (!immune_kmod_enabled())
        return orig_write(td, args);
    
    /* Pre-write inspection */
    if (uap->nbyte > 0 && uap->nbyte <= INSPECT_BUF_SIZE) {
        char *buf = malloc(uap->nbyte + 1, M_IMMUNE, M_NOWAIT);
        
        if (buf) {
            if (copyin(uap->buf, buf, uap->nbyte) == 0) {
                buf[uap->nbyte] = '\0';
                
                immune_kmod_inc_scan();
                
                int threat = immune_kern_scan(buf, uap->nbyte);
                
                if (threat >= 4) {  /* CRITICAL */
                    immune_kmod_inc_threat();
                    immune_kmod_inc_blocked();
                    printf("IMMUNE: BLOCKED write() - critical threat\n");
                    free(buf, M_IMMUNE);
                    return EPERM;
                }
                
                if (threat >= 3 && immune_kmod_strict()) {  /* HIGH + strict */
                    immune_kmod_inc_threat();
                    immune_kmod_inc_blocked();
                    printf("IMMUNE: BLOCKED write() - strict mode\n");
                    free(buf, M_IMMUNE);
                    return EPERM;
                }
                
                if (threat > 0) {
                    immune_kmod_inc_threat();
                    printf("IMMUNE: Threat detected in write() - level %d\n", threat);
                }
            }
            free(buf, M_IMMUNE);
        }
    }
    
    return orig_write(td, args);
}

/* ==================== Execve Hook ==================== */

static int
immune_execve_hook(struct thread *td, void *args)
{
    struct execve_args *uap = (struct execve_args *)args;
    char path[256];
    
    if (!immune_kmod_enabled())
        return orig_execve(td, args);
    
    immune_kmod_inc_scan();
    
    /* Check executable path */
    if (copyinstr(uap->fname, path, sizeof(path), NULL) == 0) {
        int threat = immune_kern_scan(path, strlen(path));
        
        if (threat >= 4) {
            immune_kmod_inc_threat();
            immune_kmod_inc_blocked();
            printf("IMMUNE: BLOCKED exec(%s) - critical threat\n", path);
            return EPERM;
        }
    }
    
    return orig_execve(td, args);
}

/* ==================== Open Hook ==================== */

static int
immune_open_hook(struct thread *td, void *args)
{
    struct open_args *uap = (struct open_args *)args;
    char path[256];
    
    if (!immune_kmod_enabled())
        return orig_open(td, args);
    
    /* Check path for suspicious patterns */
    if (copyinstr(uap->path, path, sizeof(path), NULL) == 0) {
        /* Block access to sensitive paths */
        if (strstr(path, "/etc/shadow") ||
            strstr(path, "/etc/master.passwd")) {
            
            immune_kmod_inc_threat();
            printf("IMMUNE: Blocked access to %s\n", path);
            
            if (immune_kmod_strict()) {
                immune_kmod_inc_blocked();
                return EPERM;
            }
        }
    }
    
    return orig_open(td, args);
}

/* ==================== Connect Hook ==================== */

static int
immune_connect_hook(struct thread *td, void *args)
{
    /* struct connect_args *uap = (struct connect_args *)args; */
    
    if (!immune_kmod_enabled())
        return orig_connect(td, args);
    
    /* Would check destination IP against blocklist */
    
    return orig_connect(td, args);
}

/* ==================== Hook Management ==================== */

int
immune_hook_init(void)
{
    mtx_init(&hook_mtx, "immune_hook", NULL, MTX_DEF);
    
    mtx_lock(&hook_mtx);
    
    /* Save originals */
    orig_read = sysent[SYS_read].sy_call;
    orig_write = sysent[SYS_write].sy_call;
    orig_execve = sysent[SYS_execve].sy_call;
    orig_open = sysent[SYS_open].sy_call;
    orig_connect = sysent[SYS_connect].sy_call;
    
    /* Install hooks */
    sysent[SYS_read].sy_call = (sy_call_t *)immune_read_hook;
    sysent[SYS_write].sy_call = (sy_call_t *)immune_write_hook;
    sysent[SYS_execve].sy_call = (sy_call_t *)immune_execve_hook;
    sysent[SYS_open].sy_call = (sy_call_t *)immune_open_hook;
    sysent[SYS_connect].sy_call = (sy_call_t *)immune_connect_hook;
    
    hooks_installed = 1;
    
    mtx_unlock(&hook_mtx);
    
    printf("IMMUNE: Syscall hooks installed\n");
    return 0;
}

void
immune_hook_shutdown(void)
{
    mtx_lock(&hook_mtx);
    
    if (hooks_installed) {
        /* Restore originals */
        sysent[SYS_read].sy_call = orig_read;
        sysent[SYS_write].sy_call = orig_write;
        sysent[SYS_execve].sy_call = orig_execve;
        sysent[SYS_open].sy_call = orig_open;
        sysent[SYS_connect].sy_call = orig_connect;
        
        hooks_installed = 0;
    }
    
    mtx_unlock(&hook_mtx);
    mtx_destroy(&hook_mtx);
    
    printf("IMMUNE: Syscall hooks removed\n");
}
