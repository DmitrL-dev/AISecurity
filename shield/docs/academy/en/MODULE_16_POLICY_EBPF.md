# SENTINEL Academy — Module 16

## Policy Engine and eBPF

_SSE Level | Duration: 4 hours_

---

## Introduction

Two advanced Shield components:

1. **Policy Engine** — Cisco-style class-map/policy-map system
2. **eBPF** — Kernel-level filtering

---

## 16.1 Policy Engine Architecture

### Components

```
┌─────────────────────────────────────────────────────────┐
│                    Policy Engine                         │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │  Class-Map  │───►│ Policy-Map  │───►│Service-Policy│ │
│  │ (Matching)  │    │  (Actions)  │    │  (Binding)  │  │
│  └─────────────┘    └─────────────┘    └─────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Class-Map

Defines matching conditions:

```c
typedef enum {
    CLASS_MATCH_ANY,        /* match any (OR) */
    CLASS_MATCH_ALL,        /* match all (AND) */
} class_match_mode_t;

typedef struct class_map {
    char              name[64];
    class_match_mode_t mode;
    class_condition_t *conditions;
    uint64_t          match_count;
} class_map_t;
```

### Match Types

| Type                     | Description         |
| ------------------------ | ------------------- |
| `MATCH_PATTERN`          | Regex pattern       |
| `MATCH_CONTAINS`         | Contains string     |
| `MATCH_SIZE_GT`          | Size > N bytes      |
| `MATCH_SIZE_LT`          | Size < N bytes      |
| `MATCH_JAILBREAK`        | Jailbreak detection |
| `MATCH_PROMPT_INJECTION` | Injection detection |
| `MATCH_ENTROPY_HIGH`     | High entropy        |
| `MATCH_EXFILTRATION`     | Data exfiltration   |

### Policy-Map

Defines actions:

```c
typedef struct policy_action {
    rule_action_t   action;       // BLOCK, LOG, ALERT, ALLOW
    uint32_t        rate_limit;   // Packets per second
    char            redirect_zone[64];
    uint8_t         set_severity;
    bool            log_enabled;
} policy_action_t;
```

### Service-Policy

Binding to zones:

```c
service_policy_apply(engine, "external", "SECURITY-POLICY", DIRECTION_INBOUND);
```

---

## 16.2 Policy Engine C API

### Initialization

```c
#include "core/policy_engine.h"

policy_engine_t engine;
policy_engine_init(&engine);
```

### Creating Class-Map

```c
// Match-any (OR logic)
class_map_t *threats;
class_map_create(&engine, "THREATS", CLASS_MATCH_ANY, &threats);

// Add conditions
class_map_add_match(threats, MATCH_PROMPT_INJECTION, "", false);
class_map_add_match(threats, MATCH_JAILBREAK, "", false);
class_map_add_match(threats, MATCH_EXFILTRATION, "", false);
```

### Creating Policy-Map

```c
// Policy map
policy_map_t *security;
policy_map_create(&engine, "SECURITY-POLICY", &security);

// Add class
policy_class_t *pc;
policy_map_add_class(security, "THREATS", &pc);

// Add actions
policy_action_t *action;
policy_class_add_action(pc, ACTION_BLOCK, &action);
action->log_enabled = true;
```

### Applying to Zone

```c
service_policy_apply(&engine, "external", "SECURITY-POLICY", DIRECTION_INBOUND);
```

### Evaluation

```c
policy_result_t result;
policy_evaluate(&engine, "external", DIRECTION_INBOUND,
                data, data_len, &result);

if (result.action == ACTION_BLOCK) {
    printf("Blocked by policy: %s, class: %s\n",
           result.matched_policy, result.matched_class);
}
```

---

## 16.3 eBPF XDP Architecture

### Why eBPF?

- **Kernel-level** filtering
- **< 1μs** latency
- **10M+ pps** throughput
- Zero-copy networking

### XDP Flow

```
┌─────────────────────────────────────────────────────────┐
│                     NIC Hardware                         │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   XDP Hook (eBPF)                        │
│  ┌─────────────────────────────────────────────────┐    │
│  │ shield_xdp_filter()                               │    │
│  │   • Check blocklist                               │    │
│  │   • Rate limiting                                  │    │
│  │   • Send to userspace                             │    │
│  └─────────────────────────────────────────────────┘    │
│              │                    │                      │
│         XDP_DROP              XDP_PASS                   │
│              │                    │                      │
└──────────────┼────────────────────┼──────────────────────┘
               │                    │
               ▼                    ▼
          (dropped)         ┌──────────────┐
                            │ TCP/IP Stack │
                            └──────────────┘
                                   │
                                   ▼
                            ┌──────────────┐
                            │Shield Daemon │
                            └──────────────┘
```

### BPF Maps

```c
/* Blocklist: IP -> blocked */
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 10000);
    __type(key, __u32);    /* IP address */
    __type(value, __u8);   /* 1 = blocked */
} blocklist SEC(".maps");

/* Rate limiting per source IP */
struct {
    __uint(type, BPF_MAP_TYPE_LRU_HASH);
    __uint(max_entries, 100000);
    __type(key, __u32);    /* Source IP */
    __type(value, struct rate_limit_state);
} rate_limits SEC(".maps");

/* Ring buffer for events */
struct {
    __uint(type, BPF_MAP_TYPE_RINGBUF);
    __uint(max_entries, 256 * 1024);
} events SEC(".maps");
```

---

## 16.4 XDP Program

### Main Filter

```c
SEC("xdp")
int shield_xdp_filter(struct xdp_md *ctx)
{
    void *data = (void *)(long)ctx->data;
    void *data_end = (void *)(long)ctx->data_end;

    /* Parse Ethernet */
    struct ethhdr *eth = data;
    if ((void*)(eth + 1) > data_end)
        return XDP_PASS;

    /* Only IPv4 */
    if (eth->h_proto != bpf_htons(ETH_P_IP))
        return XDP_PASS;

    /* Parse IP */
    struct iphdr *ip = (void*)(eth + 1);
    if ((void*)(ip + 1) > data_end)
        return XDP_PASS;

    __u32 src_ip = ip->saddr;

    /* Check blocklist */
    __u8 *blocked = bpf_map_lookup_elem(&blocklist, &src_ip);
    if (blocked && *blocked) {
        return XDP_DROP;  /* Block! */
    }

    /* Rate limiting */
    if (check_rate_limit(src_ip)) {
        return XDP_DROP;  /* Rate limited */
    }

    /* Send event to userspace */
    send_event(src_ip, dst_ip, dst_port);

    return XDP_PASS;
}
```

### TC Egress

```c
SEC("tc")
int shield_tc_egress(struct __sk_buff *skb)
{
    /* Check outbound connections to blocked IPs */
    __u32 dst_ip = get_dst_ip(skb);

    __u8 *blocked = bpf_map_lookup_elem(&blocklist, &dst_ip);
    if (blocked && *blocked) {
        return TC_ACT_SHOT;  /* Block outbound */
    }

    return TC_ACT_OK;
}
```

---

## 16.5 Userspace Loader

### Initialization

```c
#include "ebpf/ebpf_loader.h"

ebpf_context_t ctx;
ebpf_init(&ctx, "eth0");
ebpf_load(&ctx, "/usr/lib/shield/shield_xdp.o");
ebpf_attach(&ctx);
```

### Blocklist Management

```c
// Block IP
ebpf_block_ip(&ctx, inet_addr("192.168.1.100"));

// Unblock
ebpf_unblock_ip(&ctx, inet_addr("192.168.1.100"));

// Whitelist port
ebpf_whitelist_port(&ctx, 443);
```

### Getting Statistics

```c
ebpf_stats_t stats;
ebpf_get_stats(&ctx, &stats);

printf("Packets: total=%lu, allowed=%lu, blocked=%lu\n",
       stats.packets_total,
       stats.packets_allowed,
       stats.packets_blocked);
```

### Event Polling

```c
// Poll events from ring buffer
while (running) {
    ebpf_poll_events(&ctx, 100);  // 100ms timeout
}
```

---

## 16.6 Benchmark Suite

Shield includes performance benchmark:

```c
#include "tests/bench_core.h"

bench_config_t config = {
    .iterations = 100000,
    .warmup_iterations = 1000,
};

shield_context_t ctx;
shield_init(&ctx);

run_benchmarks(&ctx, &config);
```

### Results

```
╔══════════════════════════════════════════════════════════════════╗
║              SENTINEL SHIELD BENCHMARK SUITE                      ║
╚══════════════════════════════════════════════════════════════════╝

Benchmark                          Avg (µs)    P99 (µs)    Ops/sec
─────────                          ────────    ────────    ───────
Basic Evaluation                      0.85        1.20    1,176,470
Injection Detection                   1.25        2.50      800,000
Large Payload (100KB)                12.50       25.00       80,000
Pattern Matching                      0.45        0.80    2,222,222
Entropy Calculation                   0.15        0.25    6,666,666
```

---

## Practice

### Exercise 1: Policy Engine

Create a policy:

```
class-map match-all CRITICAL-THREATS
  match injection
  match size greater-than 10000

policy-map BLOCK-CRITICAL
  class CRITICAL-THREATS
    block
    log
    alert
```

### Exercise 2: eBPF

Compile and load XDP program:

```bash
clang -O2 -target bpf -c shield_xdp.c -o shield_xdp.o
./shield-ebpf load eth0 shield_xdp.o
./shield-ebpf block 192.168.1.100
./shield-ebpf stats
```

### Exercise 3: Benchmark

Run benchmarks:

```bash
./shield-bench -n 100000 -v
```

Analyze:

- Which test is slowest?
- Why?
- How to optimize?

---

## Module 16 Summary

- **Policy Engine**: class-map, policy-map, service-policy
- **eBPF XDP**: kernel-level filtering, < 1μs
- **TC Egress**: outbound filtering
- **Benchmarks**: full performance suite

---

_"Policy Engine + eBPF = impenetrable protection."_
