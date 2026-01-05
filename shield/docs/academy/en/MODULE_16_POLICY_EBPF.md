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
} class_map_t;
```

### Match Types

| Type | Description |
|------|-------------|
| `MATCH_PATTERN` | Regex pattern |
| `MATCH_CONTAINS` | Contains string |
| `MATCH_SIZE_GT` | Size > N bytes |
| `MATCH_JAILBREAK` | Jailbreak detection |
| `MATCH_PROMPT_INJECTION` | Injection detection |
| `MATCH_ENTROPY_HIGH` | High entropy |

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
policy_map_t *security;
policy_map_create(&engine, "SECURITY-POLICY", &security);

policy_class_t *pc;
policy_map_add_class(security, "THREATS", &pc);

policy_action_t *action;
policy_class_add_action(pc, ACTION_BLOCK, &action);
action->log_enabled = true;
```

### Applying to Zone

```c
service_policy_apply(&engine, "external", "SECURITY-POLICY", DIRECTION_INBOUND);
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
└──────────────┼────────────────────┼──────────────────────┘
               │                    │
               ▼                    ▼
          (dropped)         ┌──────────────┐
                            │ TCP/IP Stack │
                            └──────────────┘
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

    struct ethhdr *eth = data;
    if ((void*)(eth + 1) > data_end)
        return XDP_PASS;

    if (eth->h_proto != bpf_htons(ETH_P_IP))
        return XDP_PASS;

    struct iphdr *ip = (void*)(eth + 1);
    __u32 src_ip = ip->saddr;

    /* Check blocklist */
    __u8 *blocked = bpf_map_lookup_elem(&blocklist, &src_ip);
    if (blocked && *blocked) {
        return XDP_DROP;  /* Block! */
    }

    /* Rate limiting */
    if (check_rate_limit(src_ip)) {
        return XDP_DROP;
    }

    return XDP_PASS;
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

### Managing Blocklist

```c
// Block IP
ebpf_block_ip(&ctx, inet_addr("192.168.1.100"));

// Unblock
ebpf_unblock_ip(&ctx, inet_addr("192.168.1.100"));

// Whitelist port
ebpf_whitelist_port(&ctx, 443);
```

---

## 16.6 Benchmark Suite

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

### Task 1: Policy Engine

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

### Task 2: eBPF

Compile and load XDP program:

```bash
clang -O2 -target bpf -c shield_xdp.c -o shield_xdp.o
./shield-ebpf load eth0 shield_xdp.o
./shield-ebpf block 192.168.1.100
./shield-ebpf stats
```

---

## Module 16 Summary

- **Policy Engine**: class-map, policy-map, service-policy
- **eBPF XDP**: kernel-level filtering, < 1μs
- **TC Egress**: outbound filtering
- **Benchmarks**: full performance suite

---

_"Policy Engine + eBPF = impenetrable defense."_
