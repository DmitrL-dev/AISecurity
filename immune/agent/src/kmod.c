/*
 * SENTINEL IMMUNE — Kernel Module
 * 
 * DragonFlyBSD kernel module entry point.
 * Loads IMMUNE into the kernel as a loadable module.
 * 
 * Build: make -f Makefile.kmod
 * Load:  kldload immune.ko
 */

#include <sys/param.h>
#include <sys/module.h>
#include <sys/kernel.h>
#include <sys/systm.h>
#include <sys/sysctl.h>

#include "../include/immune.h"
#include "../include/hooks.h"

/* Module version */
#define IMMUNE_VERSION_MAJOR 0
#define IMMUNE_VERSION_MINOR 1
#define IMMUNE_VERSION_PATCH 0

/* Module state */
static int immune_enabled = 0;
static int immune_log_level = 1;

/* Sysctl tree */
SYSCTL_NODE(_security, OID_AUTO, immune, CTLFLAG_RW, 0,
    "SENTINEL IMMUNE security module");
SYSCTL_INT(_security_immune, OID_AUTO, enabled, CTLFLAG_RW,
    &immune_enabled, 0, "IMMUNE enabled state");
SYSCTL_INT(_security_immune, OID_AUTO, log_level, CTLFLAG_RW,
    &immune_log_level, 0, "IMMUNE log verbosity");

/*
 * Module load handler
 */
static int
immune_modevent(module_t mod, int type, void *unused)
{
    int error = 0;
    
    switch (type) {
    case MOD_LOAD:
        printf("IMMUNE: Loading SENTINEL IMMUNE v%d.%d.%d\n",
            IMMUNE_VERSION_MAJOR,
            IMMUNE_VERSION_MINOR,
            IMMUNE_VERSION_PATCH);
        
        /* Initialize memory subsystem */
        if (immune_memory_init("/var/immune/memory") != 0) {
            printf("IMMUNE: Failed to initialize memory\n");
            return ENOMEM;
        }
        
        /* Initialize hooks */
        if (immune_hook_init() != 0) {
            printf("IMMUNE: Failed to initialize hooks\n");
            return EINVAL;
        }
        
        /* Register syscall hooks */
        immune_hook_register(SYS_READ, NULL);
        immune_hook_register(SYS_WRITE, NULL);
        immune_hook_register(SYS_EXECVE, NULL);
        immune_hook_register(SYS_CONNECT, NULL);
        
        immune_enabled = 1;
        printf("IMMUNE: Module loaded successfully\n");
        printf("IMMUNE: Monitoring syscalls: read, write, execve, connect\n");
        break;
        
    case MOD_UNLOAD:
        printf("IMMUNE: Unloading module\n");
        
        /* Disable and cleanup */
        immune_enabled = 0;
        
        /* Unregister hooks */
        immune_hook_unregister(SYS_READ);
        immune_hook_unregister(SYS_WRITE);
        immune_hook_unregister(SYS_EXECVE);
        immune_hook_unregister(SYS_CONNECT);
        
        /* Shutdown subsystems */
        immune_hook_shutdown();
        immune_memory_shutdown();
        
        printf("IMMUNE: Module unloaded\n");
        break;
        
    case MOD_QUIESCE:
        /* Check if safe to unload */
        if (immune_enabled) {
            printf("IMMUNE: Cannot unload while enabled\n");
            return EBUSY;
        }
        break;
        
    default:
        error = EOPNOTSUPP;
        break;
    }
    
    return error;
}

/* Module declaration */
static moduledata_t immune_mod = {
    "immune",           /* module name */
    immune_modevent,    /* event handler */
    NULL                /* extra data */
};

DECLARE_MODULE(immune, immune_mod, SI_SUB_DRIVERS, SI_ORDER_MIDDLE);
MODULE_VERSION(immune, 1);
