/*
 * SENTINEL Shield - eBPF XDP Program
 * 
 * Kernel-level packet filtering for AI security
 * Compile with: clang -O2 -target bpf -c shield_xdp.c -o shield_xdp.o
 * 
 * NOTE: This file requires BPF toolchain (clang with BPF target)
 */

/* Guard: only compile with BPF-capable compiler */
#if defined(__BPF__) || defined(SHIELD_COMPILE_XDP)

#include <linux/bpf.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/tcp.h>
#include <linux/udp.h>
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_endian.h>

/* Shield decision */
enum shield_action {
    SHIELD_ACTION_ALLOW   = 0,
    SHIELD_ACTION_BLOCK   = 1,
    SHIELD_ACTION_LOG     = 2,
    SHIELD_ACTION_RATE    = 3,
};

/* Request metadata passed to userspace */
struct shield_request {
    __u32 src_ip;
    __u32 dst_ip;
    __u16 src_port;
    __u16 dst_port;
    __u32 payload_len;
    __u64 timestamp;
    __u8  direction;   /* 0=ingress, 1=egress */
};

/* Statistics */
struct shield_stats {
    __u64 packets_total;
    __u64 packets_allowed;
    __u64 packets_blocked;
    __u64 bytes_total;
};

/* Rate limit state */
struct rate_limit_state {
    __u64 last_packet_ns;
    __u64 tokens;
    __u64 max_tokens;
    __u64 refill_rate;
};

/* ===== BPF Maps ===== */

/* Blocklist: IP -> blocked */
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 10000);
    __type(key, __u32);    /* IP address */
    __type(value, __u8);   /* 1 = blocked */
} blocklist SEC(".maps");

/* Port whitelist */
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 256);
    __type(key, __u16);    /* Port */
    __type(value, __u8);   /* 1 = allowed */
} port_whitelist SEC(".maps");

/* Statistics per-CPU */
struct {
    __uint(type, BPF_MAP_TYPE_PERCPU_ARRAY);
    __uint(max_entries, 1);
    __type(key, __u32);
    __type(value, struct shield_stats);
} stats SEC(".maps");

/* Rate limiting per source IP */
struct {
    __uint(type, BPF_MAP_TYPE_LRU_HASH);
    __uint(max_entries, 100000);
    __type(key, __u32);    /* Source IP */
    __type(value, struct rate_limit_state);
} rate_limits SEC(".maps");

/* Ring buffer for sending events to userspace */
struct {
    __uint(type, BPF_MAP_TYPE_RINGBUF);
    __uint(max_entries, 256 * 1024);
} events SEC(".maps");

/* Configuration */
struct shield_config {
    __u32 rate_limit_pps;      /* Packets per second */
    __u32 rate_limit_burst;
    __u8  block_unknown_ports;
    __u8  log_blocked;
    __u8  enabled;
};

struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, 1);
    __type(key, __u32);
    __type(value, struct shield_config);
} config SEC(".maps");

/* ===== Helper Functions ===== */

static __always_inline void update_stats(int blocked, __u32 bytes)
{
    __u32 key = 0;
    struct shield_stats *s = bpf_map_lookup_elem(&stats, &key);
    if (s) {
        s->packets_total++;
        s->bytes_total += bytes;
        if (blocked) {
            s->packets_blocked++;
        } else {
            s->packets_allowed++;
        }
    }
}

static __always_inline int check_rate_limit(__u32 src_ip, __u32 limit_pps)
{
    struct rate_limit_state *state;
    struct rate_limit_state new_state = {};
    __u64 now = bpf_ktime_get_ns();
    
    state = bpf_map_lookup_elem(&rate_limits, &src_ip);
    if (!state) {
        /* First packet from this IP */
        new_state.last_packet_ns = now;
        new_state.tokens = limit_pps;
        new_state.max_tokens = limit_pps;
        new_state.refill_rate = limit_pps;
        bpf_map_update_elem(&rate_limits, &src_ip, &new_state, BPF_ANY);
        return 0;  /* Allow */
    }
    
    /* Refill tokens based on time elapsed */
    __u64 elapsed_ns = now - state->last_packet_ns;
    __u64 refill = (elapsed_ns * state->refill_rate) / 1000000000ULL;
    
    state->tokens += refill;
    if (state->tokens > state->max_tokens) {
        state->tokens = state->max_tokens;
    }
    state->last_packet_ns = now;
    
    if (state->tokens > 0) {
        state->tokens--;
        return 0;  /* Allow */
    }
    
    return 1;  /* Rate limited */
}

static __always_inline void send_event(__u32 src_ip, __u32 dst_ip,
                                        __u16 src_port, __u16 dst_port,
                                        __u32 payload_len, __u8 action)
{
    struct shield_request *req;
    
    req = bpf_ringbuf_reserve(&events, sizeof(*req), 0);
    if (!req) {
        return;
    }
    
    req->src_ip = src_ip;
    req->dst_ip = dst_ip;
    req->src_port = src_port;
    req->dst_port = dst_port;
    req->payload_len = payload_len;
    req->timestamp = bpf_ktime_get_ns();
    req->direction = 0;
    
    bpf_ringbuf_submit(req, 0);
}

/* ===== XDP Program ===== */

SEC("xdp")
int shield_xdp_filter(struct xdp_md *ctx)
{
    void *data = (void *)(long)ctx->data;
    void *data_end = (void *)(long)ctx->data_end;
    
    /* Check config */
    __u32 cfg_key = 0;
    struct shield_config *cfg = bpf_map_lookup_elem(&config, &cfg_key);
    if (cfg && !cfg->enabled) {
        return XDP_PASS;
    }
    
    /* Parse Ethernet */
    struct ethhdr *eth = data;
    if ((void*)(eth + 1) > data_end) {
        return XDP_PASS;
    }
    
    /* Only IPv4 */
    if (eth->h_proto != bpf_htons(ETH_P_IP)) {
        return XDP_PASS;
    }
    
    /* Parse IP */
    struct iphdr *ip = (void*)(eth + 1);
    if ((void*)(ip + 1) > data_end) {
        return XDP_PASS;
    }
    
    __u32 src_ip = ip->saddr;
    __u32 dst_ip = ip->daddr;
    __u16 src_port = 0;
    __u16 dst_port = 0;
    __u32 payload_len = bpf_ntohs(ip->tot_len);
    
    /* Check IP blocklist */
    __u8 *blocked = bpf_map_lookup_elem(&blocklist, &src_ip);
    if (blocked && *blocked) {
        update_stats(1, payload_len);
        return XDP_DROP;
    }
    
    /* Parse TCP/UDP for ports */
    if (ip->protocol == IPPROTO_TCP) {
        struct tcphdr *tcp = (void*)ip + (ip->ihl * 4);
        if ((void*)(tcp + 1) > data_end) {
            return XDP_PASS;
        }
        src_port = bpf_ntohs(tcp->source);
        dst_port = bpf_ntohs(tcp->dest);
    } else if (ip->protocol == IPPROTO_UDP) {
        struct udphdr *udp = (void*)ip + (ip->ihl * 4);
        if ((void*)(udp + 1) > data_end) {
            return XDP_PASS;
        }
        src_port = bpf_ntohs(udp->source);
        dst_port = bpf_ntohs(udp->dest);
    }
    
    /* Check port whitelist */
    if (cfg && cfg->block_unknown_ports) {
        __u8 *allowed = bpf_map_lookup_elem(&port_whitelist, &dst_port);
        if (!allowed) {
            update_stats(1, payload_len);
            return XDP_DROP;
        }
    }
    
    /* Rate limiting */
    if (cfg && cfg->rate_limit_pps > 0) {
        if (check_rate_limit(src_ip, cfg->rate_limit_pps)) {
            update_stats(1, payload_len);
            return XDP_DROP;
        }
    }
    
    /* Send event to userspace for deep inspection */
    send_event(src_ip, dst_ip, src_port, dst_port, payload_len, SHIELD_ACTION_ALLOW);
    
    update_stats(0, payload_len);
    return XDP_PASS;
}

/* TC classifier for egress */
SEC("tc")
int shield_tc_egress(struct __sk_buff *skb)
{
    void *data = (void *)(long)skb->data;
    void *data_end = (void *)(long)skb->data_end;
    
    struct ethhdr *eth = data;
    if ((void*)(eth + 1) > data_end) {
        return TC_ACT_OK;
    }
    
    if (eth->h_proto != bpf_htons(ETH_P_IP)) {
        return TC_ACT_OK;
    }
    
    struct iphdr *ip = (void*)(eth + 1);
    if ((void*)(ip + 1) > data_end) {
        return TC_ACT_OK;
    }
    
    __u32 dst_ip = ip->daddr;
    
    /* Check blocklist for egress */
    __u8 *blocked = bpf_map_lookup_elem(&blocklist, &dst_ip);
    if (blocked && *blocked) {
        return TC_ACT_SHOT;
    }
    
    return TC_ACT_OK;
}

char LICENSE[] SEC("license") = "GPL";

#else /* !__BPF__ && !SHIELD_COMPILE_XDP */

/* Stub for non-BPF compilation */
static void __shield_xdp_stub(void) { (void)0; }

#endif /* __BPF__ || SHIELD_COMPILE_XDP */
