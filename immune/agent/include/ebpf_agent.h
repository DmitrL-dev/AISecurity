/*
 * SENTINEL IMMUNE — Linux eBPF Agent
 * 
 * Linux port using eBPF for syscall interception.
 * Provides same functionality as BSD Kmod but via BPF programs.
 * 
 * Features:
 * - Syscall tracing (execve, openat, connect)
 * - Perf ring buffer for events
 * - Userspace pattern matching
 */

#ifndef IMMUNE_EBPF_AGENT_H
#define IMMUNE_EBPF_AGENT_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

/* Event types */
typedef enum {
    EBPF_EVENT_NONE = 0,
    EBPF_EVENT_EXEC,        /* execve */
    EBPF_EVENT_OPEN,        /* openat */
    EBPF_EVENT_CONNECT,     /* connect */
    EBPF_EVENT_WRITE,       /* write */
    EBPF_EVENT_SOCKET       /* socket creation */
} ebpf_event_type_t;

/* Maximum sizes */
#define EBPF_MAX_PATH       256
#define EBPF_MAX_COMM       64
#define EBPF_MAX_ARGS       512
#define EBPF_MAX_ADDR       64

/* Event structure (matches BPF program output) */
typedef struct {
    ebpf_event_type_t type;
    uint32_t    pid;
    uint32_t    uid;
    uint32_t    gid;
    uint64_t    timestamp_ns;
    int         ret;            /* Return value (if applicable) */
    
    union {
        /* EXEC event */
        struct {
            char    filename[EBPF_MAX_PATH];
            char    args[EBPF_MAX_ARGS];
            char    comm[EBPF_MAX_COMM];
        } exec;
        
        /* OPEN event */
        struct {
            char    filename[EBPF_MAX_PATH];
            int     flags;
            int     mode;
        } open;
        
        /* CONNECT event */
        struct {
            char    addr[EBPF_MAX_ADDR];
            uint16_t port;
            uint16_t family;    /* AF_INET, AF_INET6, AF_UNIX */
        } connect;
    };
} ebpf_event_t;

/* Event callback */
typedef void (*ebpf_callback_t)(const ebpf_event_t *event, void *user_data);

/* Configuration */
typedef struct {
    bool trace_exec;
    bool trace_open;
    bool trace_connect;
    int  ring_buffer_pages;     /* Perf buffer size (power of 2) */
    int  poll_timeout_ms;
} ebpf_config_t;

/* Statistics */
typedef struct {
    uint64_t events_received;
    uint64_t events_exec;
    uint64_t events_open;
    uint64_t events_connect;
    uint64_t events_dropped;
    uint64_t errors;
} ebpf_stats_t;

/* === Configuration === */

void ebpf_config_init(ebpf_config_t *config);

/* === Lifecycle === */

/**
 * Initialize eBPF subsystem.
 * @param config Configuration (NULL for defaults)
 * @return 0 on success, negative on error
 */
int ebpf_init(const ebpf_config_t *config);

/**
 * Load eBPF programs into kernel.
 * @return 0 on success
 */
int ebpf_load_programs(void);

/**
 * Attach eBPF programs to tracepoints.
 * @return 0 on success
 */
int ebpf_attach(void);

/**
 * Detach eBPF programs.
 */
void ebpf_detach(void);

/**
 * Shutdown eBPF subsystem.
 */
void ebpf_shutdown(void);

/**
 * Check if eBPF is available on this system.
 * @return true if available
 */
bool ebpf_available(void);

/* === Event Polling === */

/**
 * Poll for events (blocking up to timeout).
 * @param callback Event callback
 * @param user_data User data for callback
 * @param timeout_ms Timeout in milliseconds (-1 for infinite)
 * @return Number of events processed, negative on error
 */
int ebpf_poll_events(ebpf_callback_t callback, 
                     void *user_data, 
                     int timeout_ms);

/**
 * Start event processing loop (blocking).
 * @param callback Event callback
 * @param user_data User data for callback
 */
void ebpf_event_loop(ebpf_callback_t callback, void *user_data);

/**
 * Stop event loop.
 */
void ebpf_stop(void);

/* === Statistics === */

void ebpf_get_stats(ebpf_stats_t *stats);
void ebpf_reset_stats(void);

/* === Utility === */

const char* ebpf_event_type_string(ebpf_event_type_t type);

#endif /* IMMUNE_EBPF_AGENT_H */
