/*
 * SENTINEL Shield - eBPF Userspace Loader
 * 
 * Loads and manages the eBPF XDP program
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <signal.h>
#include <net/if.h>

#ifdef SHIELD_USE_EBPF
#include <bpf/libbpf.h>
#include <bpf/bpf.h>
#endif

#include "shield_common.h"
/* Note: ebpf_loader.c has its own extended API, not using shield_ebpf.h */

/* Local stats definition */
typedef struct {
    uint64_t    packets_in;
    uint64_t    packets_out;
    uint64_t    bytes_in;
    uint64_t    bytes_out;
    uint64_t    dropped;
    uint64_t    errors;
    uint64_t    events_received;
} ebpf_stats_t;

/* Local loader context (extended, not exported) */
typedef struct ebpf_loader_ctx {
    char                interface[64];
    int                 ifindex;
    bool                loaded;
    
#ifdef SHIELD_USE_EBPF
    struct bpf_object  *obj;
    struct bpf_program *xdp_prog;
    struct bpf_program *tc_prog;
    
    int                 blocklist_fd;
    int                 port_whitelist_fd;
    int                 stats_fd;
    int                 config_fd;
    int                 events_fd;
    
    struct ring_buffer *rb;
#endif
    
    /* Config */
    uint32_t            rate_limit_pps;
    bool                block_unknown_ports;
    bool                log_blocked;
    
    /* Statistics */
    uint64_t            events_received;
} ebpf_loader_ctx_t;

#ifdef SHIELD_USE_EBPF

/* Event handler callback */
static int handle_event(void *ctx, void *data, size_t data_sz)
{
    ebpf_loader_ctx_t *ectx = (ebpf_loader_ctx_t *)ctx;
    struct shield_request *req = data;
    
    ectx->events_received++;
    
    /* Convert IP to string */
    char src_ip[16], dst_ip[16];
    uint32_t ip = req->src_ip;
    snprintf(src_ip, sizeof(src_ip), "%u.%u.%u.%u",
             ip & 0xFF, (ip >> 8) & 0xFF, (ip >> 16) & 0xFF, (ip >> 24) & 0xFF);
    ip = req->dst_ip;
    snprintf(dst_ip, sizeof(dst_ip), "%u.%u.%u.%u",
             ip & 0xFF, (ip >> 8) & 0xFF, (ip >> 16) & 0xFF, (ip >> 24) & 0xFF);
    
    LOG_DEBUG("eBPF: %s:%u -> %s:%u (%u bytes)",
             src_ip, req->src_port, dst_ip, req->dst_port, req->payload_len);
    
    return 0;
}

#endif /* SHIELD_USE_EBPF */

/* Initialize eBPF */
shield_err_t ebpf_init(ebpf_loader_ctx_t *ctx, const char *interface)
{
    if (!ctx || !interface) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(ctx, 0, sizeof(*ctx));
    strncpy(ctx->interface, interface, sizeof(ctx->interface) - 1);
    
#ifdef SHIELD_USE_EBPF
    /* Get interface index */
    ctx->ifindex = if_nametoindex(interface);
    if (ctx->ifindex == 0) {
        LOG_ERROR("eBPF: Interface %s not found", interface);
        return SHIELD_ERR_NOTFOUND;
    }
    
    LOG_INFO("eBPF: Initializing for interface %s (ifindex %d)",
             interface, ctx->ifindex);
    
    return SHIELD_OK;
#else
    LOG_WARN("eBPF: Not supported (compile with SHIELD_USE_EBPF)");
    return SHIELD_ERR_IO;
#endif
}

/* Load eBPF program */
shield_err_t ebpf_load(ebpf_loader_ctx_t *ctx, const char *program_path)
{
    if (!ctx) {
        return SHIELD_ERR_INVALID;
    }
    
#ifdef SHIELD_USE_EBPF
    int err;
    
    /* Open BPF object */
    ctx->obj = bpf_object__open(program_path);
    if (!ctx->obj) {
        LOG_ERROR("eBPF: Failed to open %s: %s", program_path, strerror(errno));
        return SHIELD_ERR_IO;
    }
    
    /* Load into kernel */
    err = bpf_object__load(ctx->obj);
    if (err) {
        LOG_ERROR("eBPF: Failed to load: %s", strerror(-err));
        bpf_object__close(ctx->obj);
        return SHIELD_ERR_EBPF;
    }
    
    /* Find XDP program */
    ctx->xdp_prog = bpf_object__find_program_by_name(ctx->obj, "shield_xdp_filter");
    if (!ctx->xdp_prog) {
        LOG_ERROR("eBPF: XDP program not found");
        bpf_object__close(ctx->obj);
        return SHIELD_ERR_NOTFOUND;
    }
    
    /* Find TC program */
    ctx->tc_prog = bpf_object__find_program_by_name(ctx->obj, "shield_tc_egress");
    
    /* Get map FDs */
    ctx->blocklist_fd = bpf_object__find_map_fd_by_name(ctx->obj, "blocklist");
    ctx->port_whitelist_fd = bpf_object__find_map_fd_by_name(ctx->obj, "port_whitelist");
    ctx->stats_fd = bpf_object__find_map_fd_by_name(ctx->obj, "stats");
    ctx->config_fd = bpf_object__find_map_fd_by_name(ctx->obj, "config");
    ctx->events_fd = bpf_object__find_map_fd_by_name(ctx->obj, "events");
    
    /* Create ring buffer */
    if (ctx->events_fd >= 0) {
        ctx->rb = ring_buffer__new(ctx->events_fd, handle_event, ctx, NULL);
        if (!ctx->rb) {
            LOG_WARN("eBPF: Failed to create ring buffer");
        }
    }
    
    ctx->loaded = true;
    LOG_INFO("eBPF: Program loaded successfully");
    
    return SHIELD_OK;
#else
    (void)program_path;
    return SHIELD_ERR_IO;
#endif
}

/* Attach XDP program to interface */
shield_err_t ebpf_attach(ebpf_loader_ctx_t *ctx)
{
    if (!ctx || !ctx->loaded) {
        return SHIELD_ERR_INVALID;
    }
    
#ifdef SHIELD_USE_EBPF
    int prog_fd = bpf_program__fd(ctx->xdp_prog);
    int err;
    
    /* Attach XDP program */
    err = bpf_xdp_attach(ctx->ifindex, prog_fd, XDP_FLAGS_UPDATE_IF_NOEXIST, NULL);
    if (err) {
        LOG_ERROR("eBPF: Failed to attach XDP: %s", strerror(-err));
        return SHIELD_ERR_EBPF;
    }
    
    LOG_INFO("eBPF: XDP attached to %s", ctx->interface);
    return SHIELD_OK;
#else
    return SHIELD_ERR_IO;
#endif
}

/* Detach XDP program */
shield_err_t ebpf_detach(ebpf_loader_ctx_t *ctx)
{
    if (!ctx) {
        return SHIELD_ERR_INVALID;
    }
    
#ifdef SHIELD_USE_EBPF
    if (ctx->ifindex > 0) {
        bpf_xdp_detach(ctx->ifindex, XDP_FLAGS_UPDATE_IF_NOEXIST, NULL);
        LOG_INFO("eBPF: XDP detached from %s", ctx->interface);
    }
    return SHIELD_OK;
#else
    return SHIELD_ERR_IO;
#endif
}

/* Add IP to blocklist */
shield_err_t ebpf_block_ip(ebpf_loader_ctx_t *ctx, uint32_t ip)
{
    if (!ctx) {
        return SHIELD_ERR_INVALID;
    }
    
#ifdef SHIELD_USE_EBPF
    if (ctx->blocklist_fd < 0) {
        return SHIELD_ERR_INVALID;
    }
    
    uint8_t blocked = 1;
    int err = bpf_map_update_elem(ctx->blocklist_fd, &ip, &blocked, BPF_ANY);
    if (err) {
        return SHIELD_ERR_EBPF;
    }
    
    LOG_DEBUG("eBPF: Blocked IP %u.%u.%u.%u",
             ip & 0xFF, (ip >> 8) & 0xFF, (ip >> 16) & 0xFF, (ip >> 24) & 0xFF);
    return SHIELD_OK;
#else
    (void)ip;
    return SHIELD_ERR_IO;
#endif
}

/* Remove IP from blocklist */
shield_err_t ebpf_unblock_ip(ebpf_loader_ctx_t *ctx, uint32_t ip)
{
    if (!ctx) {
        return SHIELD_ERR_INVALID;
    }
    
#ifdef SHIELD_USE_EBPF
    if (ctx->blocklist_fd < 0) {
        return SHIELD_ERR_INVALID;
    }
    
    bpf_map_delete_elem(ctx->blocklist_fd, &ip);
    return SHIELD_OK;
#else
    (void)ip;
    return SHIELD_ERR_IO;
#endif
}

/* Add port to whitelist */
shield_err_t ebpf_whitelist_port(ebpf_loader_ctx_t *ctx, uint16_t port)
{
    if (!ctx) {
        return SHIELD_ERR_INVALID;
    }
    
#ifdef SHIELD_USE_EBPF
    if (ctx->port_whitelist_fd < 0) {
        return SHIELD_ERR_INVALID;
    }
    
    uint8_t allowed = 1;
    bpf_map_update_elem(ctx->port_whitelist_fd, &port, &allowed, BPF_ANY);
    return SHIELD_OK;
#else
    (void)port;
    return SHIELD_ERR_IO;
#endif
}

/* Get statistics */
shield_err_t ebpf_get_stats(ebpf_loader_ctx_t *ctx, ebpf_stats_t *stats)
{
    if (!ctx || !stats) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(stats, 0, sizeof(*stats));
    
#ifdef SHIELD_USE_EBPF
    if (ctx->stats_fd < 0) {
        return SHIELD_ERR_INVALID;
    }
    
    uint32_t key = 0;
    struct shield_stats kernel_stats;
    
    if (bpf_map_lookup_elem(ctx->stats_fd, &key, &kernel_stats) == 0) {
        stats->packets_total = kernel_stats.packets_total;
        stats->packets_allowed = kernel_stats.packets_allowed;
        stats->packets_blocked = kernel_stats.packets_blocked;
        stats->bytes_total = kernel_stats.bytes_total;
    }
    
    stats->events_received = ctx->events_received;
    return SHIELD_OK;
#else
    return SHIELD_ERR_IO;
#endif
}

/* Poll for events */
shield_err_t ebpf_poll_events(ebpf_loader_ctx_t *ctx, int timeout_ms)
{
    if (!ctx) {
        return SHIELD_ERR_INVALID;
    }
    
#ifdef SHIELD_USE_EBPF
    if (ctx->rb) {
        ring_buffer__poll(ctx->rb, timeout_ms);
    }
    return SHIELD_OK;
#else
    (void)timeout_ms;
    return SHIELD_ERR_IO;
#endif
}

/* Update configuration */
shield_err_t ebpf_set_config(ebpf_loader_ctx_t *ctx, uint32_t rate_limit_pps,
                              bool block_unknown, bool enabled)
{
    if (!ctx) {
        return SHIELD_ERR_INVALID;
    }
    
    ctx->rate_limit_pps = rate_limit_pps;
    ctx->block_unknown_ports = block_unknown;
    
#ifdef SHIELD_USE_EBPF
    if (ctx->config_fd < 0) {
        return SHIELD_ERR_INVALID;
    }
    
    struct {
        uint32_t rate_limit_pps;
        uint32_t rate_limit_burst;
        uint8_t block_unknown_ports;
        uint8_t log_blocked;
        uint8_t enabled;
    } config = {
        .rate_limit_pps = rate_limit_pps,
        .rate_limit_burst = rate_limit_pps * 2,
        .block_unknown_ports = block_unknown ? 1 : 0,
        .log_blocked = 1,
        .enabled = enabled ? 1 : 0,
    };
    
    uint32_t key = 0;
    bpf_map_update_elem(ctx->config_fd, &key, &config, BPF_ANY);
    return SHIELD_OK;
#else
    (void)enabled;
    return SHIELD_ERR_IO;
#endif
}

/* Destroy eBPF context */
void ebpf_destroy(ebpf_loader_ctx_t *ctx)
{
    if (!ctx) {
        return;
    }
    
    ebpf_detach(ctx);
    
#ifdef SHIELD_USE_EBPF
    if (ctx->rb) {
        ring_buffer__free(ctx->rb);
    }
    if (ctx->obj) {
        bpf_object__close(ctx->obj);
    }
#endif
    
    LOG_INFO("eBPF: Destroyed");
}
