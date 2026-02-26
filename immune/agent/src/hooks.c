/*
 * SENTINEL IMMUNE — Platform Kernel Hooks
 * 
 * Provides kernel-level interception based on platform.
 * This is a wrapper that calls the appropriate platform-specific code.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../include/immune.h"
#include "../include/hooks.h"

/* ==================== Platform-Specific Includes ==================== */

#if defined(IMMUNE_PLATFORM_DRAGONFLY) || defined(IMMUNE_PLATFORM_FREEBSD)
    /* BSD kernel module support */
    #ifdef _KERNEL
        #include <sys/param.h>
        #include <sys/systm.h>
        #include <sys/kernel.h>
        #include <sys/proc.h>
        #include <sys/sysent.h>
        #include <sys/lock.h>
        #include <sys/mutex.h>
    #endif
    #define KERNEL_HOOKS_AVAILABLE  1
#elif defined(IMMUNE_PLATFORM_LINUX)
    /* Linux kernel module support via kprobes */
    #ifdef __KERNEL__
        #include <linux/kernel.h>
        #include <linux/module.h>
        #include <linux/kprobes.h>
    #endif
    #define KERNEL_HOOKS_AVAILABLE  1
#else
    #define KERNEL_HOOKS_AVAILABLE  0
#endif

/* ==================== Hook State ==================== */

static hook_state_t g_hook_state = HOOK_DISABLED;
static hook_stats_t g_hook_stats = {0};

/* Callbacks */
static scan_callback_t g_scan_callback = NULL;
static immune_agent_t *g_agent = NULL;

/* ==================== Userspace Hook Simulation ==================== */

#if !defined(_KERNEL) && !defined(__KERNEL__)

/*
 * In userspace, we can't do real syscall hooking.
 * Instead, we provide an API for applications to call us.
 */

int
immune_hook_init(void)
{
    g_hook_state = HOOK_ENABLED;
    memset(&g_hook_stats, 0, sizeof(hook_stats_t));
    
    printf("IMMUNE: Hook subsystem initialized (userspace mode)\n");
    return 0;
}

void
immune_hook_shutdown(void)
{
    g_hook_state = HOOK_DISABLED;
    printf("IMMUNE: Hook subsystem shutdown\n");
}

int
immune_hook_register(int syscall_num, hook_callback_t callback)
{
    /* In userspace, just record the callback */
    (void)syscall_num;
    (void)callback;
    return 0;
}

int
immune_hook_unregister(int syscall_num)
{
    (void)syscall_num;
    return 0;
}

void
immune_hook_set_agent(immune_agent_t *agent)
{
    g_agent = agent;
}

void
immune_hook_set_callback(scan_callback_t callback)
{
    g_scan_callback = callback;
}

/*
 * Userspace hook entry point.
 * Applications call this to have their data scanned.
 */
int
immune_hook_scan(const void *data, size_t length, int hook_type)
{
    if (g_hook_state != HOOK_ENABLED || !g_agent)
        return 0;
    
    g_hook_stats.total_intercepted++;
    
    scan_result_t result = immune_scan(g_agent, data, length);
    
    if (result.detected) {
        g_hook_stats.total_threats++;
        
        if (g_scan_callback) {
            g_scan_callback(data, length, &result);
        }
        
        /* Block if critical */
        if (result.level >= THREAT_CRITICAL) {
            g_hook_stats.total_denied++;
            return -1;  /* Block */
        }
    }
    
    return 0;  /* Allow */
}

#endif /* !_KERNEL && !__KERNEL__ */

/* ==================== DragonFlyBSD/FreeBSD Kernel Hooks ==================== */

#if (defined(IMMUNE_PLATFORM_DRAGONFLY) || defined(IMMUNE_PLATFORM_FREEBSD)) && defined(_KERNEL)

static sy_call_t *original_read = NULL;
static sy_call_t *original_write = NULL;
static sy_call_t *original_execve = NULL;
static struct mtx hook_mutex;

static int
immune_read_hook(struct thread *td, void *args)
{
    struct read_args *uap = (struct read_args *)args;
    int result;
    
    g_hook_stats.total_intercepted++;
    
    result = original_read(td, args);
    
    if (result == 0 && uap->nbyte > 0 && uap->nbyte <= 4096 && g_agent) {
        /* Would scan the read data here */
    }
    
    return result;
}

static int
immune_write_hook(struct thread *td, void *args)
{
    struct write_args *uap = (struct write_args *)args;
    char buf[4096];
    
    g_hook_stats.total_intercepted++;
    
    if (uap->nbyte > 0 && uap->nbyte <= sizeof(buf) && g_agent) {
        if (copyin(uap->buf, buf, uap->nbyte) == 0) {
            scan_result_t result = immune_scan(g_agent, buf, uap->nbyte);
            
            if (result.level >= THREAT_CRITICAL) {
                g_hook_stats.total_threats++;
                g_hook_stats.total_denied++;
                return EPERM;
            }
        }
    }
    
    return original_write(td, args);
}

int
immune_hook_init(void)
{
    mtx_init(&hook_mutex, "immune_hook", NULL, MTX_DEF);
    
    original_read = sysent[SYS_read].sy_call;
    original_write = sysent[SYS_write].sy_call;
    original_execve = sysent[SYS_execve].sy_call;
    
    g_hook_state = HOOK_ENABLED;
    
    printf("IMMUNE: Kernel hooks initialized\n");
    return 0;
}

void
immune_hook_shutdown(void)
{
    mtx_lock(&hook_mutex);
    
    sysent[SYS_read].sy_call = original_read;
    sysent[SYS_write].sy_call = original_write;
    sysent[SYS_execve].sy_call = original_execve;
    
    g_hook_state = HOOK_DISABLED;
    
    mtx_unlock(&hook_mutex);
    mtx_destroy(&hook_mutex);
    
    printf("IMMUNE: Kernel hooks shutdown\n");
}

int
immune_hook_register(int syscall_num, hook_callback_t callback)
{
    mtx_lock(&hook_mutex);
    
    switch (syscall_num) {
    case SYS_read:
        sysent[SYS_read].sy_call = (sy_call_t *)immune_read_hook;
        break;
    case SYS_write:
        sysent[SYS_write].sy_call = (sy_call_t *)immune_write_hook;
        break;
    default:
        mtx_unlock(&hook_mutex);
        return -1;
    }
    
    mtx_unlock(&hook_mutex);
    return 0;
}

#endif /* DragonFlyBSD/FreeBSD kernel */

/* ==================== Linux Kernel Hooks (kprobes) ==================== */

#if defined(IMMUNE_PLATFORM_LINUX) && defined(__KERNEL__)

static struct kprobe kp_read;
static struct kprobe kp_write;

static int
handle_pre_read(struct kprobe *p, struct pt_regs *regs)
{
    g_hook_stats.total_intercepted++;
    return 0;
}

static int
handle_pre_write(struct kprobe *p, struct pt_regs *regs)
{
    g_hook_stats.total_intercepted++;
    /* Would scan the write buffer here */
    return 0;
}

int
immune_hook_init(void)
{
    int ret;
    
    kp_read.symbol_name = "ksys_read";
    kp_read.pre_handler = handle_pre_read;
    
    kp_write.symbol_name = "ksys_write";
    kp_write.pre_handler = handle_pre_write;
    
    ret = register_kprobe(&kp_read);
    if (ret < 0) {
        printk(KERN_ERR "IMMUNE: Failed to register read probe\n");
        return ret;
    }
    
    ret = register_kprobe(&kp_write);
    if (ret < 0) {
        unregister_kprobe(&kp_read);
        printk(KERN_ERR "IMMUNE: Failed to register write probe\n");
        return ret;
    }
    
    g_hook_state = HOOK_ENABLED;
    printk(KERN_INFO "IMMUNE: Kernel hooks initialized\n");
    
    return 0;
}

void
immune_hook_shutdown(void)
{
    unregister_kprobe(&kp_read);
    unregister_kprobe(&kp_write);
    
    g_hook_state = HOOK_DISABLED;
    printk(KERN_INFO "IMMUNE: Kernel hooks shutdown\n");
}

#endif /* Linux kernel */

/* ==================== Common Functions ==================== */

hook_state_t
immune_hook_get_state(void)
{
    return g_hook_state;
}

hook_stats_t
immune_hook_stats(void)
{
    return g_hook_stats;
}
