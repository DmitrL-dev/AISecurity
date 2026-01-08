/*
 * SENTINEL IMMUNE — Linux eBPF Agent Implementation
 * 
 * Linux port using eBPF via libbpf.
 * Traces syscalls and sends events to userspace for analysis.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <signal.h>
#include <unistd.h>
#include <time.h>
#include <sys/resource.h>

/* libbpf headers - conditional compilation */
#ifdef USE_LIBBPF
#include <bpf/libbpf.h>
#include <bpf/bpf.h>
#endif

#include "ebpf_agent.h"

/* ==================== Constants ==================== */

#define DEFAULT_RING_PAGES      64
#define DEFAULT_POLL_TIMEOUT    100

/* ==================== Global State ==================== */

static struct {
    bool            initialized;
    bool            running;
    ebpf_config_t   config;
    ebpf_stats_t    stats;
    
#ifdef USE_LIBBPF
    struct bpf_object *obj;
    struct ring_buffer *rb;
    int prog_fd_exec;
    int prog_fd_open;
    int prog_fd_connect;
#endif
} g_ebpf = {0};

static volatile sig_atomic_t g_stop = 0;

/* ==================== String Tables ==================== */

static const char* event_type_strings[] = {
    [EBPF_EVENT_NONE]    = "None",
    [EBPF_EVENT_EXEC]    = "Exec",
    [EBPF_EVENT_OPEN]    = "Open",
    [EBPF_EVENT_CONNECT] = "Connect",
    [EBPF_EVENT_WRITE]   = "Write",
    [EBPF_EVENT_SOCKET]  = "Socket"
};

const char*
ebpf_event_type_string(ebpf_event_type_t type)
{
    if (type >= 0 && type <= EBPF_EVENT_SOCKET) {
        return event_type_strings[type];
    }
    return "Unknown";
}

/* ==================== Configuration ==================== */

void
ebpf_config_init(ebpf_config_t *config)
{
    if (!config) return;
    
    config->trace_exec = true;
    config->trace_open = true;
    config->trace_connect = true;
    config->ring_buffer_pages = DEFAULT_RING_PAGES;
    config->poll_timeout_ms = DEFAULT_POLL_TIMEOUT;
}

/* ==================== System Checks ==================== */

bool
ebpf_available(void)
{
#ifdef __linux__
    /* Check for BPF syscall availability */
    return access("/sys/fs/bpf", F_OK) == 0;
#else
    return false;
#endif
}

static int
bump_memlock_rlimit(void)
{
#ifdef __linux__
    struct rlimit rlim_new = {
        .rlim_cur = RLIM_INFINITY,
        .rlim_max = RLIM_INFINITY,
    };
    return setrlimit(RLIMIT_MEMLOCK, &rlim_new);
#else
    return 0;
#endif
}

/* ==================== Lifecycle ==================== */

int
ebpf_init(const ebpf_config_t *config)
{
    if (g_ebpf.initialized) {
        return 0;
    }
    
    memset(&g_ebpf, 0, sizeof(g_ebpf));
    
    if (config) {
        memcpy(&g_ebpf.config, config, sizeof(ebpf_config_t));
    } else {
        ebpf_config_init(&g_ebpf.config);
    }
    
    if (!ebpf_available()) {
        fprintf(stderr, "[EBPF] eBPF not available on this system\n");
        return -ENOTSUP;
    }
    
    /* Bump memlock limit for BPF maps */
    if (bump_memlock_rlimit() != 0) {
        fprintf(stderr, "[EBPF] Warning: failed to increase memlock limit\n");
    }
    
    g_ebpf.initialized = true;
    printf("[EBPF] Initialized (exec:%d open:%d connect:%d)\n",
           g_ebpf.config.trace_exec,
           g_ebpf.config.trace_open,
           g_ebpf.config.trace_connect);
    
    return 0;
}

int
ebpf_load_programs(void)
{
    if (!g_ebpf.initialized) {
        return -EINVAL;
    }
    
#ifdef USE_LIBBPF
    /* Load BPF object from file */
    g_ebpf.obj = bpf_object__open_file("immune_agent.bpf.o", NULL);
    if (libbpf_get_error(g_ebpf.obj)) {
        fprintf(stderr, "[EBPF] Failed to open BPF object\n");
        return -errno;
    }
    
    /* Load programs */
    if (bpf_object__load(g_ebpf.obj) != 0) {
        fprintf(stderr, "[EBPF] Failed to load BPF programs\n");
        bpf_object__close(g_ebpf.obj);
        return -errno;
    }
    
    printf("[EBPF] BPF programs loaded\n");
#else
    printf("[EBPF] Programs loaded (mock mode - no libbpf)\n");
#endif
    
    return 0;
}

int
ebpf_attach(void)
{
    if (!g_ebpf.initialized) {
        return -EINVAL;
    }
    
#ifdef USE_LIBBPF
    struct bpf_program *prog;
    struct bpf_link *link;
    
    bpf_object__for_each_program(prog, g_ebpf.obj) {
        link = bpf_program__attach(prog);
        if (libbpf_get_error(link)) {
            fprintf(stderr, "[EBPF] Failed to attach %s\n",
                    bpf_program__name(prog));
            return -errno;
        }
        printf("[EBPF] Attached: %s\n", bpf_program__name(prog));
    }
    
    /* Setup ring buffer */
    int map_fd = bpf_object__find_map_fd_by_name(g_ebpf.obj, "events");
    if (map_fd < 0) {
        fprintf(stderr, "[EBPF] Failed to find events map\n");
        return -errno;
    }
    
    g_ebpf.rb = ring_buffer__new(map_fd, NULL, NULL, NULL);
    if (!g_ebpf.rb) {
        fprintf(stderr, "[EBPF] Failed to create ring buffer\n");
        return -errno;
    }
#else
    printf("[EBPF] Attached (mock mode)\n");
#endif
    
    return 0;
}

void
ebpf_detach(void)
{
#ifdef USE_LIBBPF
    if (g_ebpf.rb) {
        ring_buffer__free(g_ebpf.rb);
        g_ebpf.rb = NULL;
    }
    
    if (g_ebpf.obj) {
        bpf_object__close(g_ebpf.obj);
        g_ebpf.obj = NULL;
    }
#endif
    
    printf("[EBPF] Detached\n");
}

void
ebpf_shutdown(void)
{
    if (!g_ebpf.initialized) return;
    
    g_ebpf.running = false;
    ebpf_detach();
    
    memset(&g_ebpf, 0, sizeof(g_ebpf));
    g_ebpf.initialized = false;
    
    printf("[EBPF] Shutdown complete\n");
}

/* ==================== Event Polling ==================== */

/* Callback context */
typedef struct {
    ebpf_callback_t callback;
    void           *user_data;
} poll_ctx_t;

#ifdef USE_LIBBPF
static int
handle_event(void *ctx, void *data, size_t data_sz)
{
    poll_ctx_t *pctx = ctx;
    ebpf_event_t *event = data;
    
    if (data_sz < sizeof(ebpf_event_type_t)) {
        g_ebpf.stats.events_dropped++;
        return 0;
    }
    
    g_ebpf.stats.events_received++;
    
    switch (event->type) {
    case EBPF_EVENT_EXEC:
        g_ebpf.stats.events_exec++;
        break;
    case EBPF_EVENT_OPEN:
        g_ebpf.stats.events_open++;
        break;
    case EBPF_EVENT_CONNECT:
        g_ebpf.stats.events_connect++;
        break;
    default:
        break;
    }
    
    if (pctx->callback) {
        pctx->callback(event, pctx->user_data);
    }
    
    return 0;
}
#endif

int
ebpf_poll_events(ebpf_callback_t callback, 
                 void *user_data, 
                 int timeout_ms)
{
    if (!g_ebpf.initialized) {
        return -EINVAL;
    }
    
#ifdef USE_LIBBPF
    if (!g_ebpf.rb) {
        return -EINVAL;
    }
    
    poll_ctx_t ctx = {
        .callback = callback,
        .user_data = user_data
    };
    
    int n = ring_buffer__poll(g_ebpf.rb, timeout_ms);
    if (n < 0 && n != -EINTR) {
        g_ebpf.stats.errors++;
    }
    
    return n;
#else
    /* Mock mode - simulate occasional events */
    static int counter = 0;
    usleep(timeout_ms * 1000);
    
    if (++counter % 10 == 0) {
        ebpf_event_t event = {0};
        event.type = EBPF_EVENT_EXEC;
        event.pid = getpid();
        event.uid = getuid();
        event.timestamp_ns = time(NULL) * 1000000000ULL;
        strncpy(event.exec.filename, "/bin/test", EBPF_MAX_PATH);
        strncpy(event.exec.comm, "test", EBPF_MAX_COMM);
        
        g_ebpf.stats.events_received++;
        g_ebpf.stats.events_exec++;
        
        if (callback) {
            callback(&event, user_data);
        }
        return 1;
    }
    
    return 0;
#endif
}

static void
signal_handler(int sig)
{
    (void)sig;
    g_stop = 1;
    g_ebpf.running = false;
}

void
ebpf_event_loop(ebpf_callback_t callback, void *user_data)
{
    if (!g_ebpf.initialized) return;
    
    g_ebpf.running = true;
    g_stop = 0;
    
    /* Setup signal handlers */
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);
    
    printf("[EBPF] Starting event loop...\n");
    
    while (g_ebpf.running && !g_stop) {
        int n = ebpf_poll_events(callback, user_data, 
                                 g_ebpf.config.poll_timeout_ms);
        (void)n;
    }
    
    printf("[EBPF] Event loop stopped\n");
}

void
ebpf_stop(void)
{
    g_ebpf.running = false;
    g_stop = 1;
}

/* ==================== Statistics ==================== */

void
ebpf_get_stats(ebpf_stats_t *stats)
{
    if (!stats) return;
    memcpy(stats, &g_ebpf.stats, sizeof(ebpf_stats_t));
}

void
ebpf_reset_stats(void)
{
    memset(&g_ebpf.stats, 0, sizeof(ebpf_stats_t));
}
