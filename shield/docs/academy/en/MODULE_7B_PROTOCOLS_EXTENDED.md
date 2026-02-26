# SENTINEL Academy — Module 7B

## Extended Shield Protocols

_SSP Level | Duration: 4 hours_

---

## Introduction

In addition to the 6 base protocols (Module 7), Shield has **14 additional protocols** for enterprise features:

| Category        | Protocols         |
| --------------- | ----------------- |
| **Discovery**   | ZRP, ZHP          |
| **Traffic**     | SPP, SQP, SRP     |
| **Analytics**   | STT, SEM, SLA     |
| **HA**          | SMRP              |
| **Integration** | SGP, SIEM         |
| **Security**    | STLS, SZAA, SSigP |

---

## 7B.1 ZRP — Zone Registration Protocol

### Purpose

Registration and management of zones in a Shield cluster.

### Operations

| Type             | Description             |
| ---------------- | ----------------------- |
| `ZRP_REGISTER`   | Register new zone       |
| `ZRP_DEREGISTER` | Remove zone             |
| `ZRP_UPDATE`     | Update metadata         |
| `ZRP_LIST`       | List all zones          |

### C API

```c
#include "protocols/zrp.h"

zrp_context_t *ctx;
zrp_init(&ctx, "shield-node-1");

// Register zone
zrp_zone_info_t info = {
    .name = "llm-openai",
    .type = ZONE_TYPE_LLM,
    .provider = "openai",
    .trust_level = 7
};
zrp_register(ctx, &info);

// Get list
zrp_zone_list_t list;
zrp_list(ctx, &list);

zrp_destroy(ctx);
```

---

## 7B.2 ZHP — Zone Health Protocol

### Purpose

Zone health monitoring and alerting.

### Health Checks

- Response time
- Error rate
- Connection pool
- Queue depth

### C API

```c
#include "protocols/zhp.h"

zhp_context_t *ctx;
zhp_init(&ctx);

// Check zone health
zhp_health_t health;
zhp_check(ctx, "llm-zone", &health);

printf("Status: %s, Latency: %dms\n",
       health.healthy ? "HEALTHY" : "DEGRADED",
       health.latency_ms);

// Subscribe to alerts
zhp_subscribe(ctx, on_health_alert);
```

---

## 7B.3 SPP — Shield Policy Protocol

### Purpose

Security policy distribution across the cluster.

### Operations

| Type       | Description        |
| ---------- | ------------------ |
| `SPP_PUSH` | Push policy        |
| `SPP_PULL` | Pull policy        |
| `SPP_SYNC` | Synchronize all    |
| `SPP_DIFF` | Get differences    |

### C API

```c
#include "protocols/spp.h"

spp_context_t *ctx;
spp_init(&ctx);

// Push policy
spp_policy_t policy = {
    .name = "block-injection",
    .version = 2,
    .rules_json = "..."
};
spp_push(ctx, "all-nodes", &policy);

// Sync cluster
spp_sync(ctx);
```

---

## 7B.4 SQP — Shield Quarantine Protocol

### Purpose

Management of quarantined suspicious requests.

### Operations

```c
#include "protocols/sqp.h"

sqp_context_t *ctx;
sqp_init(&ctx);

// Quarantine request
sqp_quarantine(ctx, request_id, "Suspected injection", 3600);

// Get from quarantine
sqp_entry_t entry;
sqp_get(ctx, request_id, &entry);

// Analyze
sqp_analyze(ctx, request_id, &analysis_result);

// Release or delete
sqp_release(ctx, request_id);
sqp_delete(ctx, request_id);
```

---

## 7B.5 SRP — Shield Redirect Protocol

### Purpose

Traffic redirection and mirroring.

### Use Cases

- Redirect to honeypot
- Mirror for analysis
- A/B testing
- Canary deployment

### C API

```c
#include "protocols/srp.h"

srp_context_t *ctx;
srp_init(&ctx);

// Redirect rule
srp_rule_t rule = {
    .match_pattern = "attack-*",
    .action = SRP_ACTION_REDIRECT,
    .target = "honeypot-zone"
};
srp_add_rule(ctx, &rule);

// Mirror traffic
srp_mirror(ctx, "production", "analysis", 0.1);  // 10% traffic
```

---

## 7B.6 STT — Shield Threat Telemetry

### Purpose

Collection and transmission of threat intelligence data.

### Event Types

| Type              | Description              |
| ----------------- | ------------------------ |
| `THREAT_DETECTED` | Threat detected          |
| `IOC_OBSERVED`    | Indicator of compromise  |
| `ATTACK_PATTERN`  | Attack pattern           |
| `ANOMALY`         | Anomalous behavior       |

### C API

```c
#include "protocols/stt.h"

stt_context_t *ctx;
stt_init(&ctx, "https://intel.sentinel.io");

// Send event
stt_threat_t threat = {
    .type = THREAT_TYPE_INJECTION,
    .severity = SEVERITY_HIGH,
    .source_ip = "192.168.1.100",
    .payload_hash = "abc123..."
};
stt_report(ctx, &threat);

// Get IOCs
stt_ioc_t iocs[100];
size_t count;
stt_get_iocs(ctx, iocs, 100, &count);
```

---

## 7B.7 SEM — Shield Event Manager

### Purpose

Centralized event management and correlation.

### Features

- Event queue
- Correlation engine
- Alert aggregation
- Event enrichment

### C API

```c
#include "protocols/sem.h"

sem_context_t *ctx;
sem_init(&ctx);

// Send event
sem_event_t event = {
    .type = SEM_EVENT_SECURITY,
    .severity = 8,
    .message = "Jailbreak attempt detected",
    .zone = "external",
    .session_id = "sess123"
};
sem_send(ctx, &event);

// Query events
sem_query_t query = {
    .time_from = time(NULL) - 3600,
    .severity_min = 7
};
sem_query(ctx, &query, events, &count);

// Correlation
sem_correlate(ctx, "injection-pattern", &correlated);
```

---

## 7B.8 SLA — Shield Level Agreement

### Purpose

SLA monitoring and reporting.

### SLA Metrics

| Metric       | Target  |
| ------------ | ------- |
| Latency P99  | < 100ms |
| Availability | 99.9%   |
| Error Rate   | < 0.1%  |
| Throughput   | > 10K/s |

### C API

```c
#include "protocols/sla.h"

sla_context_t *ctx;
sla_init(&ctx);

// Define SLA
sla_define(ctx, "premium", SLA_LATENCY_P99, 50, SLA_UNIT_MS);
sla_define(ctx, "premium", SLA_AVAILABILITY, 99.99, SLA_UNIT_PERCENT);

// Check
sla_report_t report;
sla_check(ctx, "premium", &report);

printf("SLA compliance: %.1f%%\n", report.compliance_percent);
```

---

## 7B.9 SMRP — Shield Multicast Replication

### Purpose

Multicast distribution of signatures across the cluster.

### Advantages over unicast

- Efficient bandwidth
- Real-time updates
- Reduced latency
- Scalable to 100+ nodes

### C API

```c
#include "protocols/smrp.h"

smrp_context_t *ctx;
smrp_init(&ctx, "239.255.1.1", 5005);

// Join group
smrp_join(ctx, "signatures");

// Publish signature
smrp_signature_t sig = {
    .id = "SIG-2026-001",
    .pattern = "ignore\\s+previous",
    .category = "injection"
};
smrp_publish(ctx, "signatures", &sig);

// Receive
smrp_receive(ctx, on_signature_received, NULL);
```

---

## 7B.10 SGP — Shield-Gateway Protocol

### Purpose

Communication between Shield and API Gateway.

### Operations

| Type           | Description       |
| -------------- | ----------------- |
| `SGP_REGISTER` | Register gateway  |
| `SGP_CONFIG`   | Configuration     |
| `SGP_HEALTH`   | Health check      |
| `SGP_ROUTE`    | Routing update    |

### C API

```c
#include "protocols/sgp.h"

sgp_context_t *ctx;
sgp_init(&ctx, "gateway-1");

// Connect to gateway
sgp_connect(ctx, "api-gateway.internal:8080");

// Register route
sgp_route_t route = {
    .path = "/v1/chat",
    .zone = "llm-zone",
    .policy = "default"
};
sgp_add_route(ctx, &route);

// Sync configuration
sgp_sync_config(ctx);
```

---

## 7B.11 SIEM — Security Information Export

### Purpose

Event export to SIEM systems.

### Formats

| Format   | Description               |
| -------- | ------------------------- |
| `CEF`    | Common Event Format       |
| `JSON`   | Structured JSON           |
| `SYSLOG` | RFC 5424                  |
| `LEEF`   | Log Event Extended Format |

### C API

```c
#include "protocols/siem.h"

siem_context_t *ctx;
siem_init(&ctx, SIEM_FORMAT_CEF);
siem_set_destination(ctx, "splunk.company.com", 514);

// Send event
siem_event_t event = {
    .severity = 8,
    .category = "ai-security",
    .action = "block",
    .outcome = "success",
    .source = "shield-node-1"
};
siem_send(ctx, &event);

// Batch send
siem_flush(ctx);
```

---

## 7B.12 STLS — Shield TLS Protocol

### Purpose

Mutual TLS for secure communication.

### Features

- mTLS authentication
- Certificate rotation
- CRL checking
- OCSP stapling

### C API

```c
#include "protocols/stls.h"

stls_context_t *ctx;
stls_init(&ctx);

// Load certificates
stls_load_cert(ctx, "/etc/shield/cert.pem");
stls_load_key(ctx, "/etc/shield/key.pem");
stls_load_ca(ctx, "/etc/shield/ca.pem");

// Establish connection
stls_conn_t *conn;
stls_connect(ctx, "peer.internal:5006", &conn);

// Check peer
stls_peer_info_t peer;
stls_get_peer_info(conn, &peer);
printf("Peer CN: %s\n", peer.common_name);
```

---

## 7B.13 SZAA — Shield Zero-Trust Auth

### Purpose

Zero-trust authentication for all components.

### Authentication Methods

| Method  | Use Case            |
| ------- | ------------------- |
| `TOKEN` | API keys            |
| `CERT`  | mTLS                |
| `JWT`   | Service-to-service  |
| `OIDC`  | User authentication |

### C API

```c
#include "protocols/szaa.h"

szaa_context_t *ctx;
szaa_init(&ctx, SZAA_MODE_STRICT);

// Token authentication
szaa_result_t result;
szaa_authenticate(ctx, SZAA_METHOD_TOKEN,
                  "secret-api-key", &result);

if (result.authenticated) {
    printf("Identity: %s, Roles: %s\n",
           result.identity, result.roles);
}

// Authorization check
bool allowed = szaa_authorize(ctx, &result, "admin", "write");
```

---

## 7B.14 SSigP — Shield Signature Protocol

### Purpose

Threat signature management and distribution.

### Operations

| Type              | Description        |
| ----------------- | ------------------ |
| `SSIGP_UPDATE`    | Update database    |
| `SSIGP_SUBSCRIBE` | Subscribe          |
| `SSIGP_QUERY`     | Query signature    |
| `SSIGP_VERIFY`    | Verify signature   |

### C API

```c
#include "protocols/ssigp.h"

ssigp_context_t *ctx;
ssigp_init(&ctx, "https://signatures.sentinel.io");

// Update database
ssigp_update_result_t result;
ssigp_update(ctx, &result);
printf("Updated: %d new, %d modified\n",
       result.new_count, result.modified_count);

// Real-time subscription
ssigp_subscribe(ctx, on_new_signature, NULL);

// Check pattern
ssigp_match_t matches[100];
size_t count;
ssigp_check(ctx, input, input_len, matches, 100, &count);
```

---

## Summary Table of All 20 Protocols

| #   | Protocol | Category    | Purpose              |
| --- | -------- | ----------- | -------------------- |
| 1   | STP      | Traffic     | Data transmission    |
| 2   | SBP      | Integration | Shield-Brain link    |
| 3   | ZDP      | Discovery   | Zone discovery       |
| 4   | SHSP     | HA          | Hot Standby          |
| 5   | SAF      | Analytics   | Metrics streaming    |
| 6   | SSRP     | HA          | State replication    |
| 7   | ZRP      | Discovery   | Zone registration    |
| 8   | ZHP      | Discovery   | Zone health          |
| 9   | SPP      | Traffic     | Policies             |
| 10  | SQP      | Traffic     | Quarantine           |
| 11  | SRP      | Traffic     | Redirect             |
| 12  | STT      | Analytics   | Threat telemetry     |
| 13  | SEM      | Analytics   | Event manager        |
| 14  | SLA      | Analytics   | SLA monitoring       |
| 15  | SMRP     | HA          | Multicast signatures |
| 16  | SGP      | Integration | Gateway protocol     |
| 17  | SIEM     | Integration | SIEM export          |
| 18  | STLS     | Security    | Mutual TLS           |
| 19  | SZAA     | Security    | Zero-trust auth      |
| 20  | SSigP    | Security    | Signature updates    |

---

## Practice

### Exercise 1: Policy Distribution

Configure SPP for policy synchronization:

- Push policy to 3 nodes
- Verify versions
- Execute diff

### Exercise 2: SIEM Integration

Configure export to Splunk:

- CEF format
- Minimum severity: 5
- Batch size: 100

### Exercise 3: Zero-Trust

Implement SZAA flow:

- JWT authentication
- Role verification
- Audit logging

---

## Module 7B Summary

- **20 protocols** for enterprise Shield
- Full coverage: Discovery, Traffic, Analytics, HA, Integration, Security
- C API for each protocol
- Production-ready architecture

---

_"20 protocols = complete enterprise platform."_
