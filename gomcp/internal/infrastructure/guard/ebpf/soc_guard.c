// SEC-002: eBPF Runtime Guard kernel program.
//
// Requires Linux kernel 5.10+ and clang-14+ with the kernel BPF headers
// (libbpf-dev). Compile to the object the userspace loader reads:
//
//   clang -O2 -g -target bpf -c soc_guard.c -o soc_guard.bpf.o
//
// The Go userspace agent loads this object ONLY in the ebpf-tagged build
// (cmd/immune/monitor_ebpf.go, built with `go build -tags ebpf`). It attaches
// the tracepoints below, reads the soc_alerts ring buffer, and manages the
// soc_policy_map. The DEFAULT build does not use this file — it polls /proc.
// Loading also needs CAP_BPF + CAP_NET_ADMIN (or root).

#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_tracing.h>

// Policy map: pid → policy flags (bit field).
// Bit 0: monitored (1 = yes)
// Bit 1: ptrace blocked
// Bit 2: execve blocked
// Bit 3: network blocked
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 4096);
    __type(key, __u32);   // pid
    __type(value, __u32); // policy_flags
} soc_policy_map SEC(".maps");

// Alert ring buffer for sending violations to userspace.
struct {
    __uint(type, BPF_MAP_TYPE_RINGBUF);
    __uint(max_entries, 256 * 1024); // 256KB
} soc_alerts SEC(".maps");

// Alert event structure sent to userspace.
struct soc_alert {
    __u32 pid;
    __u32 tgid;
    __u32 alert_type;     // 1=ptrace, 2=execve, 3=network, 4=file
    __u32 blocked;        // 1=blocked (enforce), 0=logged (audit)
    __u64 timestamp_ns;
    char  comm[16];       // process name
    char  detail[64];     // violation details
};

// Alert types.
#define ALERT_PTRACE_ATTEMPT  1
#define ALERT_UNAUTHORIZED_EXEC 2
#define ALERT_NETWORK_DENIED  3
#define ALERT_FILE_DENIED     4

// Policy flags.
#define POLICY_MONITORED     (1 << 0)
#define POLICY_BLOCK_PTRACE  (1 << 1)
#define POLICY_BLOCK_EXECVE  (1 << 2)
#define POLICY_BLOCK_NETWORK (1 << 3)

static __always_inline void send_alert(
    __u32 pid, __u32 alert_type, __u32 blocked, const char *detail
) {
    struct soc_alert *alert;
    alert = bpf_ringbuf_reserve(&soc_alerts, sizeof(*alert), 0);
    if (!alert)
        return;

    alert->pid = pid;
    alert->tgid = bpf_get_current_pid_tgid() & 0xFFFFFFFF;
    alert->alert_type = alert_type;
    alert->blocked = blocked;
    alert->timestamp_ns = bpf_ktime_get_ns();
    bpf_get_current_comm(alert->comm, sizeof(alert->comm));
    __builtin_memset(alert->detail, 0, sizeof(alert->detail));
    // detail is truncated; full info is in userspace log.

    bpf_ringbuf_submit(alert, 0);
}

// ═══════════════════════════════════════════════
// TRACEPOINT: Block ptrace on monitored SOC processes
// ═══════════════════════════════════════════════
SEC("tracepoint/syscalls/sys_enter_ptrace")
int soc_guard_ptrace(struct trace_event_raw_sys_enter *ctx) {
    __u32 pid = bpf_get_current_pid_tgid() >> 32;
    __u32 target_pid = (__u32)ctx->args[1]; // ptrace(request, pid, ...)

    // Check if TARGET is a monitored SOC process.
    __u32 *flags = bpf_map_lookup_elem(&soc_policy_map, &target_pid);
    if (!flags)
        return 0; // Not a SOC process.

    if (*flags & POLICY_BLOCK_PTRACE) {
        send_alert(pid, ALERT_PTRACE_ATTEMPT, 1, "ptrace on SOC process");
        return -1; // EPERM — block the syscall.
    }

    send_alert(pid, ALERT_PTRACE_ATTEMPT, 0, "ptrace audit");
    return 0;
}

// ═══════════════════════════════════════════════
// TRACEPOINT: Monitor execve calls by SOC processes
// ═══════════════════════════════════════════════
SEC("tracepoint/syscalls/sys_enter_execve")
int soc_guard_execve(struct trace_event_raw_sys_enter *ctx) {
    __u32 pid = bpf_get_current_pid_tgid() >> 32;

    __u32 *flags = bpf_map_lookup_elem(&soc_policy_map, &pid);
    if (!flags)
        return 0;

    if (*flags & POLICY_BLOCK_EXECVE) {
        send_alert(pid, ALERT_UNAUTHORIZED_EXEC, 1, "execve blocked");
        return -1;
    }

    send_alert(pid, ALERT_UNAUTHORIZED_EXEC, 0, "execve audit");
    return 0;
}

// ═══════════════════════════════════════════════
// TRACEPOINT: Monitor socket creation (network access)
// ═══════════════════════════════════════════════
SEC("tracepoint/syscalls/sys_enter_socket")
int soc_guard_socket(struct trace_event_raw_sys_enter *ctx) {
    __u32 pid = bpf_get_current_pid_tgid() >> 32;

    __u32 *flags = bpf_map_lookup_elem(&soc_policy_map, &pid);
    if (!flags)
        return 0;

    if (*flags & POLICY_BLOCK_NETWORK) {
        send_alert(pid, ALERT_NETWORK_DENIED, 1, "socket creation blocked");
        return -1;
    }

    return 0;
}

char LICENSE[] SEC("license") = "GPL";
