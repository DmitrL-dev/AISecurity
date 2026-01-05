# SENTINEL Academy — Module 7

## Shield Protocols

_SSP Level | Duration: 5 hours_

---

## Introduction

Shield uses 6 specialized protocols for enterprise features:

| Protocol | Purpose |
|----------|---------|
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

// Create connection
stp_conn_t *conn;
stp_connect("192.168.1.2", 5001, &conn);

// Send message
stp_message_t msg = {
    .type = STP_MSG_EVALUATE,
    .payload = data,
    .payload_len = data_len
};
stp_send(conn, &msg);

// Receive response
stp_message_t response;
stp_receive(conn, &response, 5000);  // 5s timeout

stp_disconnect(conn);
```

### Message Types

| Type | Value | Description |
|------|-------|-------------|
| `STP_MSG_HANDSHAKE` | 0x01 | Initial handshake |
| `STP_MSG_EVALUATE` | 0x02 | Evaluate request |
| `STP_MSG_RESULT` | 0x03 | Evaluation result |
| `STP_MSG_CONFIG` | 0x04 | Config update |
| `STP_MSG_HEARTBEAT` | 0x05 | Keep-alive |
| `STP_MSG_ACK` | 0x06 | Acknowledgement |

---

## 7.2 SBP — Shield-Brain Protocol

### Purpose

Connection between Shield and analytical component (Brain).

Brain performs:
- Semantic analysis
- ML classification
- Threat intelligence lookup

### Architecture

```
┌─────────────────┐         SBP          ┌─────────────────┐
│     SHIELD      │◄───────────────────►│     BRAIN       │
│   (Real-time)   │                      │   (Analysis)    │
└─────────────────┘                      └─────────────────┘
```

### Usage

```c
#include "protocols/sbp.h"

sbp_client_t *brain;
sbp_connect(&brain, "brain.internal", 5002);

// Semantic analysis
sbp_semantic_result_t result;
sbp_analyze_semantic(brain, input, &result);

printf("Intent: %s (confidence: %.2f)\n",
       result.intent, result.confidence);

// Async event reporting
sbp_report_event_async(brain, &event);  // Non-blocking

sbp_disconnect(brain);
```

---

## 7.3 ZDP — Zone Discovery Protocol

### Purpose

Automatic zone discovery and configuration in cluster.

### Protocol Flow

```
1. New Node                    Cluster
      │                           │
      │──── ZDP_HELLO ───────────►│
      │                           │
      │◄─── ZDP_ZONE_LIST ────────│
      │                           │
      │──── ZDP_ZONE_CLAIM ──────►│  (request zone ownership)
      │                           │
      │◄─── ZDP_ZONE_GRANT ───────│
      │                           │
      │──── ZDP_ZONE_READY ──────►│
      │                           │
```

### C API

```c
#include "protocols/zdp.h"

// Start ZDP client
zdp_client_t *zdp;
zdp_init(&zdp, "node-3", "192.168.1.3");

// Discover zones
zone_list_t zones;
zdp_discover_zones(zdp, &zones);

for (int i = 0; i < zones.count; i++) {
    printf("Zone: %s (owner: %s)\n",
           zones.items[i].name,
           zones.items[i].owner);
}

// Claim zone
zdp_claim_zone(zdp, "external");

zdp_destroy(zdp);
```

---

## 7.4 SHSP — Shield Hot Standby Protocol

### Purpose

High Availability via Active-Standby failover.

### Features

- Heartbeat monitoring
- Automatic failover
- Manual failover
- Failback support
- Split-brain prevention

### Configuration

```json
{
  "ha": {
    "enabled": true,
    "protocol": "SHSP",
    "mode": "active-standby",

    "heartbeat": {
      "interval_ms": 1000,
      "timeout_ms": 3000,
      "max_missed": 3
    },

    "failover": {
      "delay_ms": 5000,
      "auto_failback": true,
      "failback_delay_ms": 30000
    },

    "split_brain": {
      "prevention": "quorum",
      "quorum_size": 2
    }
  }
}
```

### C API

```c
#include "protocols/shsp.h"

shsp_node_t *node;
shsp_init(&node, "node-1", SHSP_ROLE_PRIMARY);

// Register callbacks
shsp_on_promoted(node, on_promoted_callback);
shsp_on_demoted(node, on_demoted_callback);

// Start protocol
shsp_start(node);

// Manual failover
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

// Publish metric
saf_metric_t metric = {
    .name = "requests_total",
    .type = SAF_METRIC_COUNTER,
    .value = 1,
    .labels = {"zone", "action"},
    .values = {"external", "block"},
    .label_count = 2
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
|-------|-------------|
| Sessions | Active session data |
| Rate limits | Per-session counters |
| Blocklists | Temporary blocks |
| Context | Conversation history |
| Metrics | Aggregated stats |

### Configuration

```json
{
  "state_sync": {
    "protocol": "SSRP",
    "mode": "async",

    "batch": {
      "enabled": true,
      "interval_ms": 100,
      "max_items": 100
    },

    "compression": {
      "enabled": true,
      "algorithm": "lz4"
    },

    "conflict_resolution": "last_write_wins"
  }
}
```

---

## Practice

### Task 1

Configure SHSP for two nodes:
- Heartbeat: 500ms
- Failover after 3 missed
- Auto-failback after 60 seconds

### Task 2

Write C code for SAF subscriber:
- Connect to Shield
- Receive metrics
- Output in Prometheus format

### Task 3

Configure SSRP replication:
- Async mode
- Batch: 50ms, 50 items
- LZ4 compression

---

## Module 7 Summary

- 6 protocols for different tasks
- Binary protocols for performance
- STP/SBP for communication
- ZDP for discovery
- SHSP for HA
- SAF for analytics
- SSRP for replication

---

## Next Module

**Module 8: High Availability**

Detailed HA cluster configuration.

---

_"Protocols are the language of enterprise systems."_
