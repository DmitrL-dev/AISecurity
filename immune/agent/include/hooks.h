/*
 * SENTINEL IMMUNE — Hooks Header
 */

#ifndef HOOKS_H
#define HOOKS_H

#include <stdint.h>
#include <stdbool.h>
#include "immune.h"

/* Hook state */
typedef enum {
    HOOK_DISABLED = 0,
    HOOK_ENABLED,
    HOOK_ERROR
} hook_state_t;

/* Hook statistics */
typedef struct {
    uint64_t    total_intercepted;
    uint64_t    total_threats;
    uint64_t    total_denied;
    uint64_t    total_allowed;
} hook_stats_t;

/* Hook types */
#define HOOK_TYPE_READ      0
#define HOOK_TYPE_WRITE     1
#define HOOK_TYPE_EXECVE    2
#define HOOK_TYPE_CONNECT   3
#define HOOK_TYPE_OPEN      4

/* Syscall numbers (platform-specific) */
#if defined(IMMUNE_PLATFORM_DRAGONFLY) || defined(IMMUNE_PLATFORM_FREEBSD)
    #define SYS_READ        3
    #define SYS_WRITE       4
    #define SYS_OPEN        5
    #define SYS_EXECVE      59
    #define SYS_CONNECT     98
#elif defined(IMMUNE_PLATFORM_LINUX)
    #define SYS_READ        0
    #define SYS_WRITE       1
    #define SYS_OPEN        2
    #define SYS_EXECVE      59
    #define SYS_CONNECT     42
#else
    #define SYS_READ        0
    #define SYS_WRITE       1
    #define SYS_OPEN        2
    #define SYS_EXECVE      3
    #define SYS_CONNECT     4
#endif

/* Callback types */
typedef int (*hook_callback_t)(void *context, void *args);
typedef void (*scan_callback_t)(const void *data, size_t length, 
                                scan_result_t *result);

/* Functions */
int  immune_hook_init(void);
void immune_hook_shutdown(void);

int  immune_hook_register(int syscall_num, hook_callback_t callback);
int  immune_hook_unregister(int syscall_num);

void immune_hook_set_agent(immune_agent_t *agent);
void immune_hook_set_callback(scan_callback_t callback);

int  immune_hook_scan(const void *data, size_t length, int hook_type);

hook_state_t immune_hook_get_state(void);
hook_stats_t immune_hook_stats(void);

#endif /* HOOKS_H */
