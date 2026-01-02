# SENTINEL Academy — Module 7

## Shield Protocols

_SSP Level | Duration: 5 hours_

---

## Introduction

Shield uses 6 core protocols for enterprise features:

| Protocol | Purpose |
| -------- | ------- |
| **STP** | Sentinel Transfer Protocol |
| **SBP** | Shield-Brain Protocol |
| **ZDP** | Zone Discovery Protocol |
| **SHSP** | Shield Hot Standby Protocol |
| **SAF** | Sentinel Analytics Flow |
| **SSRP** | State Replication Protocol |

---

## 7.1 STP — Sentinel Transfer Protocol

### Purpose

Data transfer between Shield components with delivery guarantee.

### Features

- Binary protocol (not JSON)
- CRC32 for integrity
- Sequence numbers for ordering
- Acknowledgements
- Compression (optional)

### Message Format

```
┌─────────────────────────────────────────────────────────┐
│ Header (16 bytes)                                       │
├─────────────────────────────────────────────────────────┤
│ Magic (4)  │ Version (2) │ Type (2) │ Length (4) │ Seq (4)│
├─────────────────────────────────────────────────────────┤
│ Payload (variable)                                      │
├─────────────────────────────────────────────────────────┤
│ CRC32 (4 bytes)                                         │
└─────────────────────────────────────────────────────────┘
```

### C API

```c
#include "protocols/stp.h"

stp_conn_t *conn;
stp_connect("192.168.1.2", 5001, &conn);

stp_message_t msg = {
    .type = STP_MSG_EVALUATE,
    .payload = data,
    .payload_len = data_len
};
stp_send(conn, &msg);

stp_message_t response;
stp_receive(conn, &response, 5000);  // 5s timeout

stp_disconnect(conn);
```

---

## 7.2 SBP — Shield-Brain Protocol

### Purpose

Communication between Shield and Brain (analytics component).

Brain performs:
- Semantic analysis
- ML classification
- Threat intelligence lookup

### C API

```c
#include "protocols/sbp.h"

sbp_client_t *brain;
sbp_connect(&brain, "brain.internal", 5002);

sbp_semantic_result_t result;
sbp_analyze_semantic(brain, input, &result);

printf("Intent: %s (confidence: %.2f)\n",
       result.intent, result.confidence);

sbp_disconnect(brain);
```

---

## 7.3 ZDP — Zone Discovery Protocol

### Purpose

Automatic zone discovery and configuration in cluster.

### Use Cases

- New node joins cluster
- Dynamic zone creation
- Zone migration between nodes
- Zone health monitoring

### C API

```c
#include "protocols/zdp.h"

zdp_client_t *zdp;
zdp_init(&zdp, "node-3", "192.168.1.3");

zone_list_t zones;
zdp_discover_zones(zdp, &zones);

zdp_claim_zone(zdp, "external");

zdp_destroy(zdp);
```

---

## 7.4 SHSP — Shield Hot Standby Protocol

### Purpose

High Availability through Active-Standby failover.

### Features

- Heartbeat monitoring
- Automatic failover
- Manual failover
- Failback support
- Split-brain prevention

### C API

```c
#include "protocols/shsp.h"

shsp_node_t *node;
shsp_init(&node, "node-1", SHSP_ROLE_PRIMARY);

shsp_on_promoted(node, on_promoted_callback);
shsp_on_demoted(node, on_demoted_callback);

shsp_start(node);

shsp_trigger_failover(node, "manual-maintenance");

shsp_stop(node);
```

---

## 7.5 SAF — Sentinel Analytics Flow

### Purpose

Streaming analytics data for monitoring.

### Features

- Real-time metrics streaming
- Event aggregation
- Push-based (not polling)
- Multiple subscribers

### C API

```c
#include "protocols/saf.h"

saf_publisher_t *pub;
saf_publisher_init(&pub, "0.0.0.0", 5003);

saf_metric_t metric = {
    .name = "requests_total",
    .type = SAF_METRIC_COUNTER,
    .value = 1
};
saf_publish(pub, &metric);

saf_publisher_destroy(pub);
```

---

## 7.6 SSRP — State Replication Protocol

### Purpose

State replication between cluster nodes.

### What Gets Replicated

| State | Description |
| ----- | ----------- |
| Sessions | Active session data |
| Rate limits | Per-session counters |
| Blocklists | Temporary blocks |
| Context | Conversation history |
| Metrics | Aggregated stats |

### C API

```c
#include "protocols/ssrp.h"

ssrp_node_t *node;
ssrp_init(&node, "node-1");

ssrp_add_peer(node, "node-2", "192.168.1.2", 5004);

ssrp_state_t state = {
    .key = "session:abc123",
    .value = session_data,
    .value_len = sizeof(session_data)
};
ssrp_replicate(node, &state);

ssrp_destroy(node);
```

---

## Summary

- 6 protocols for different tasks
- Binary protocols for performance
- STP/SBP for communication
- ZDP for discovery
- SHSP for HA
- SAF for analytics
- SSRP for replication

---

## Next Module

**Module 7B: Extended Protocols (14 more)**

---

_"Protocols are the language of enterprise systems."_
