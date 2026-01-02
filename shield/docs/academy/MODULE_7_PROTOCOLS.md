# SENTINEL Academy — Module 7

## Протоколы Shield

_SSP Level | Время: 5 часов_

---

## Введение

Shield использует 6 специализированных протоколов для enterprise функций:

| Протокол | Назначение                  |
| -------- | --------------------------- |
| **STP**  | Sentinel Transfer Protocol  |
| **SBP**  | Shield-Brain Protocol       |
| **ZDP**  | Zone Discovery Protocol     |
| **SHSP** | Shield Hot Standby Protocol |
| **SAF**  | Sentinel Analytics Flow     |
| **SSRP** | State Replication Protocol  |

---

## 7.1 STP — Sentinel Transfer Protocol

### Назначение

Передача данных между компонентами Shield с гарантией доставки.

### Особенности

- Binary protocol (не JSON)
- CRC32 для integrity
- Sequence numbers для ordering
- Acknowledgements
- Compression (опционально)

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

// Создать соединение
stp_conn_t *conn;
stp_connect("192.168.1.2", 5001, &conn);

// Отправить сообщение
stp_message_t msg = {
    .type = STP_MSG_EVALUATE,
    .payload = data,
    .payload_len = data_len
};
stp_send(conn, &msg);

// Получить ответ
stp_message_t response;
stp_receive(conn, &response, 5000);  // 5s timeout

stp_disconnect(conn);
```

### Message Types

| Type                | Value | Description       |
| ------------------- | ----- | ----------------- |
| `STP_MSG_HANDSHAKE` | 0x01  | Initial handshake |
| `STP_MSG_EVALUATE`  | 0x02  | Evaluate request  |
| `STP_MSG_RESULT`    | 0x03  | Evaluation result |
| `STP_MSG_CONFIG`    | 0x04  | Config update     |
| `STP_MSG_HEARTBEAT` | 0x05  | Keep-alive        |
| `STP_MSG_ACK`       | 0x06  | Acknowledgement   |

---

## 7.2 SBP — Shield-Brain Protocol

### Назначение

Связь между Shield и аналитическим компонентом (Brain).

Brain выполняет:

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

### Protocol Features

- Request/Response pattern
- Async support (fire-and-forget for logging)
- Batching for efficiency
- Timeout handling

### Message Types

```c
typedef enum {
    SBP_ANALYZE_SEMANTIC,     // Semantic analysis request
    SBP_ANALYZE_INTENT,       // Intent classification
    SBP_LOOKUP_THREAT_INTEL,  // Threat intel query
    SBP_REPORT_EVENT,         // Event reporting (async)
    SBP_GET_MODEL_VERSION,    // Model version query
} sbp_msg_type_t;
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

### Назначение

Автоматическое обнаружение и конфигурация зон в кластере.

### Use Cases

- Новый узел присоединяется к кластеру
- Динамическое создание зон
- Zone migration между узлами
- Zone health monitoring

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

### Message Types

| Message            | Description            |
| ------------------ | ---------------------- |
| `ZDP_HELLO`        | Node announcement      |
| `ZDP_ZONE_LIST`    | Available zones        |
| `ZDP_ZONE_CLAIM`   | Request zone ownership |
| `ZDP_ZONE_GRANT`   | Grant ownership        |
| `ZDP_ZONE_RELEASE` | Release zone           |
| `ZDP_ZONE_HEALTH`  | Zone health check      |

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

### Назначение

High Availability через Active-Standby failover.

### Features

- Heartbeat monitoring
- Automatic failover
- Manual failover
- Failback support
- Split-brain prevention

### State Machine

```
    ┌──────────────────────────────────────────┐
    │                                          │
    ▼                                          │
┌─────────┐  promote   ┌─────────┐  demote    │
│ STANDBY │───────────►│ PRIMARY │────────────┘
└─────────┘            └─────────┘
    │                      │
    │ timeout              │ failure
    ▼                      ▼
┌─────────┐            ┌─────────┐
│ PRIMARY │            │  FAILED │
│(promoted)│            └─────────┘
└─────────┘
```

### Heartbeat Format

```c
typedef struct {
    char node_id[32];
    uint64_t timestamp;
    shsp_state_t state;      // PRIMARY, STANDBY, FAILED
    uint32_t requests_served;
    uint32_t errors;
    float load;
} shsp_heartbeat_t;
```

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
shsp_on_peer_failed(node, on_peer_failed_callback);

// Start protocol
shsp_start(node);

// Manual failover
shsp_trigger_failover(node, "manual-maintenance");

// Check status
shsp_status_t status;
shsp_get_status(node, &status);
printf("Role: %s, Peer: %s\n", status.role, status.peer_state);

shsp_stop(node);
```

---

## 7.5 SAF — Sentinel Analytics Flow

### Назначение

Потоковая передача analytics данных для мониторинга.

### Features

- Real-time metrics streaming
- Event aggregation
- Push-based (не polling)
- Multiple subscribers

### Metrics Types

```c
typedef enum {
    SAF_METRIC_COUNTER,    // Monotonic increasing
    SAF_METRIC_GAUGE,      // Current value
    SAF_METRIC_HISTOGRAM,  // Distribution
    SAF_METRIC_SUMMARY,    // Percentiles
} saf_metric_type_t;
```

### Data Format

```c
typedef struct {
    char name[64];
    saf_metric_type_t type;
    double value;
    uint64_t timestamp;

    // Labels
    char labels[8][32];
    char values[8][64];
    int label_count;
} saf_metric_t;
```

### Publisher (Shield)

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

### Subscriber (Prometheus/Grafana)

```c
saf_subscriber_t *sub;
saf_subscriber_init(&sub, "shield.internal", 5003);

// Receive metrics
saf_metric_t metric;
while (saf_receive(sub, &metric, 1000) == SAF_OK) {
    printf("%s = %.2f\n", metric.name, metric.value);
}
```

---

## 7.6 SSRP — State Replication Protocol

### Назначение

Репликация состояния между узлами кластера.

### What Gets Replicated

| State       | Description          |
| ----------- | -------------------- |
| Sessions    | Active session data  |
| Rate limits | Per-session counters |
| Blocklists  | Temporary blocks     |
| Context     | Conversation history |
| Metrics     | Aggregated stats     |

### Replication Modes

| Mode    | Latency | Consistency      |
| ------- | ------- | ---------------- |
| Sync    | Higher  | Strong           |
| Async   | Lower   | Eventual         |
| Batched | Lowest  | Eventual + delay |

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

### C API

```c
#include "protocols/ssrp.h"

ssrp_node_t *node;
ssrp_init(&node, "node-1");

// Add peer
ssrp_add_peer(node, "node-2", "192.168.1.2", 5004);

// Replicate state
ssrp_state_t state = {
    .key = "session:abc123",
    .value = session_data,
    .value_len = sizeof(session_data)
};
ssrp_replicate(node, &state);

// Read replicated state
ssrp_state_t received;
ssrp_get(node, "session:abc123", &received);

ssrp_destroy(node);
```

---

## Практика

### Задание 1

Настрой SHSP для двух узлов:

- Heartbeat: 500ms
- Failover после 3 missed
- Auto-failback через 60 секунд

### Задание 2

Напиши C код для SAF subscriber:

- Подключение к Shield
- Получение метрик
- Вывод в формате Prometheus

### Задание 3

Настрой SSRP репликацию:

- Async mode
- Batch: 50ms, 50 items
- LZ4 compression

---

## Итоги Module 7

- 6 протоколов для разных задач
- Binary protocols для performance
- STP/SBP для communication
- ZDP для discovery
- SHSP для HA
- SAF для analytics
- SSRP для replication

---

## Следующий модуль

**Module 8: High Availability**

Детальная настройка HA кластеров.

---

_"Протоколы — язык enterprise систем."_
