/*
 * SENTINEL Shield - eBPF/XDP Bypass Detection (Future)
 * 
 * This is a stub for kernel-level eBPF integration.
 * Full implementation requires Linux kernel headers and clang/llvm.
 */

#ifndef SHIELD_EBPF_H
#define SHIELD_EBPF_H

#include "shield_common.h"

/* eBPF Program Types */
typedef enum ebpf_prog_type {
    EBPF_PROG_XDP,          /* XDP fast path */
    EBPF_PROG_TC,           /* Traffic control */
    EBPF_PROG_CGROUP,       /* cgroup socket */
    EBPF_PROG_KPROBE,       /* Kernel probe */
} ebpf_prog_type_t;

/* eBPF Action */
typedef enum ebpf_action {
    EBPF_ACTION_PASS = 0,
    EBPF_ACTION_DROP = 1,
    EBPF_ACTION_REDIRECT = 2,
} ebpf_action_t;

/* eBPF Stats */
typedef struct ebpf_stats {
    uint64_t    packets_in;
    uint64_t    packets_out;
    uint64_t    bytes_in;
    uint64_t    bytes_out;
    uint64_t    dropped;
    uint64_t    errors;
} ebpf_stats_t;

/* eBPF Context (opaque) */
typedef struct ebpf_context ebpf_context_t;

/* ===== Userspace API ===== */

/* Check if eBPF is supported */
bool ebpf_supported(void);

/* Initialize eBPF subsystem */
shield_err_t ebpf_init(ebpf_context_t **ctx);

/* Destroy eBPF context */
void ebpf_destroy(ebpf_context_t *ctx);

/* Load eBPF program */
shield_err_t ebpf_load_program(ebpf_context_t *ctx, ebpf_prog_type_t type,
                                const char *path);

/* Attach to interface */
shield_err_t ebpf_attach(ebpf_context_t *ctx, const char *interface);

/* Detach from interface */
shield_err_t ebpf_detach(ebpf_context_t *ctx, const char *interface);

/* Get statistics */
shield_err_t ebpf_get_stats(ebpf_context_t *ctx, ebpf_stats_t *stats);

/* Update eBPF map */
shield_err_t ebpf_map_update(ebpf_context_t *ctx, const char *map_name,
                              const void *key, size_t key_len,
                              const void *value, size_t value_len);

/* Add IP to blocklist (XDP fast path) */
shield_err_t ebpf_blocklist_add(ebpf_context_t *ctx, const char *ip);

/* Remove IP from blocklist */
shield_err_t ebpf_blocklist_remove(ebpf_context_t *ctx, const char *ip);

#endif /* SHIELD_EBPF_H */
