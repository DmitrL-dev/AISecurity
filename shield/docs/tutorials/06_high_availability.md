# Tutorial 6: High Availability Setup

> **SSP Module 2.8**

---

## 🎯 Цель

Развернуть Shield в режиме High Availability:

- Active-Standby кластер
- Automatic failover
- State replication
- Zero-downtime upgrades

---

## Шаг 1: Архитектура HA

```
                    ┌─────────────┐
                    │ Load        │
                    │ Balancer    │
                    └──────┬──────┘
                           │
              ┌────────────┴────────────┐
              │                         │
       ┌──────▼──────┐          ┌───────▼─────┐
       │   Node 1    │◄────────►│   Node 2    │
       │  (PRIMARY)  │  SHSP    │  (STANDBY)  │
       └─────────────┘          └─────────────┘
              │                         │
              │      State Sync         │
              └─────────────────────────┘
```

**SHSP** = Shield Hot Standby Protocol

---

## Шаг 2: Подготовка узлов

Два сервера:

- **Node 1 (Primary):** 192.168.1.1
- **Node 2 (Standby):** 192.168.1.2

На обоих:

```bash
git clone https://github.com/SENTINEL/shield.git
cd shield && mkdir build && cd build
cmake .. && make -j$(nproc)
```

---

## Шаг 3: Конфигурация Primary

`node1_config.json`:

```json
{
  "version": "1.2.0",
  "name": "shield-primary",

  "ha": {
    "enabled": true,
    "mode": "active-standby",
    "role": "primary",
    "node_id": "node-1",

    "cluster": {
      "bind_address": "0.0.0.0",
      "bind_port": 5001,
      "peers": [{ "address": "192.168.1.2", "port": 5001 }]
    },

    "heartbeat": {
      "interval_ms": 1000,
      "timeout_ms": 3000,
      "max_missed": 3
    },

    "failover": {
      "delay_ms": 5000,
      "auto_failback": true
    },

    "state_sync": {
      "enabled": true,
      "protocol": "SSRP",
      "sync_interval_ms": 100
    }
  },

  "zones": [{ "name": "external", "trust_level": 1 }],

  "rules": [{ "name": "block_test", "pattern": "test", "action": "block" }],

  "api": { "enabled": true, "port": 8080 }
}
```

---

## Шаг 4: Конфигурация Standby

`node2_config.json`:

```json
{
  "version": "1.2.0",
  "name": "shield-standby",

  "ha": {
    "enabled": true,
    "mode": "active-standby",
    "role": "standby",
    "node_id": "node-2",

    "cluster": {
      "bind_address": "0.0.0.0",
      "bind_port": 5001,
      "peers": [{ "address": "192.168.1.1", "port": 5001 }]
    },

    "heartbeat": {
      "interval_ms": 1000,
      "timeout_ms": 3000,
      "max_missed": 3
    },

    "state_sync": {
      "enabled": true,
      "protocol": "SSRP"
    }
  },

  "zones": [{ "name": "external", "trust_level": 1 }],

  "rules": [{ "name": "block_test", "pattern": "test", "action": "block" }],

  "api": { "enabled": true, "port": 8080 }
}
```

---

## Шаг 5: Запуск кластера

**Node 1:**

```bash
./shield -c node1_config.json
```

```
[INFO] HA Mode: active-standby
[INFO] Role: PRIMARY
[INFO] Cluster port: 5001
[INFO] Waiting for peers...
```

**Node 2:**

```bash
./shield -c node2_config.json
```

```
[INFO] HA Mode: active-standby
[INFO] Role: STANDBY
[INFO] Connecting to peer: 192.168.1.1:5001
[INFO] Connected to primary: node-1
[INFO] State sync started
```

---

## Шаг 6: Проверка статуса

На любом узле:

```bash
./shield-cli
Shield> show ha status
```

```
╔══════════════════════════════════════════════════════════╗
║                    HA STATUS                              ║
╚══════════════════════════════════════════════════════════╝

Cluster: active
Mode: active-standby
My Role: PRIMARY
State: RUNNING

Nodes:
┌────────────┬───────────────┬──────────┬─────────────┐
│ Node ID    │ Address       │ Role     │ Status      │
├────────────┼───────────────┼──────────┼─────────────┤
│ node-1     │ 192.168.1.1   │ PRIMARY  │ ACTIVE      │
│ node-2     │ 192.168.1.2   │ STANDBY  │ SYNCHRONIZED│
└────────────┴───────────────┴──────────┴─────────────┘

Heartbeat:
  Last received: 234ms ago
  Missed: 0

State Sync:
  Protocol: SSRP
  Lag: 0 items
  Last sync: 45ms ago
```

---

## Шаг 7: Тестирование Failover

### Симуляция отказа Primary

На Node 1:

```bash
# Остановить Shield
Ctrl+C
```

### Наблюдение на Node 2

```
[WARN] Heartbeat missed from node-1 (1/3)
[WARN] Heartbeat missed from node-1 (2/3)
[WARN] Heartbeat missed from node-1 (3/3)
[WARN] Peer node-1 declared DEAD
[INFO] Initiating failover...
[INFO] Failover delay: 5000ms
[INFO] === PROMOTED TO PRIMARY ===
[INFO] Now accepting requests
```

### Проверка

```bash
Shield> show ha status
My Role: PRIMARY (promoted from STANDBY)
Previous primary: node-1 (FAILED)
Failover time: 5.23s
```

---

## Шаг 8: Failback

Когда Node 1 возвращается:

**Node 1:**

```bash
./shield -c node1_config.json
```

```
[INFO] Detected active primary: node-2
[INFO] Auto-failback enabled
[INFO] Requesting state sync...
[INFO] State synchronized
[INFO] Resuming as PRIMARY
```

**Node 2:**

```
[INFO] Original primary node-1 returned
[INFO] Failback to original primary
[INFO] Demoted to STANDBY
```

---

## Шаг 9: Load Balancer (Nginx)

```nginx
upstream shield_cluster {
    server 192.168.1.1:8080 weight=10;  # Primary
    server 192.168.1.2:8080 backup;     # Standby

    health_check interval=1s fails=3 passes=1;
}

server {
    listen 80;

    location /api/ {
        proxy_pass http://shield_cluster;
        proxy_connect_timeout 1s;
        proxy_read_timeout 5s;
    }
}
```

---

## Шаг 10: C API для HA

```c
#include "sentinel_shield.h"

int main(void) {
    shield_context_t ctx;
    shield_init(&ctx);

    // Загрузить HA конфигурацию
    shield_load_config(&ctx, "ha_config.json");

    // Проверить HA статус
    ha_status_t ha_status;
    shield_get_ha_status(&ctx, &ha_status);

    printf("HA Mode: %s\n", ha_status.mode);
    printf("Role: %s\n", ha_status.role);
    printf("Peer count: %d\n", ha_status.peer_count);
    printf("State: %s\n", ha_status.state);

    // Callbacks для HA событий
    shield_on_failover(&ctx, on_failover_callback, NULL);
    shield_on_failback(&ctx, on_failback_callback, NULL);

    // Работа...

    shield_destroy(&ctx);
    return 0;
}

void on_failover_callback(const char *new_role, void *user_data) {
    printf("FAILOVER: Now %s\n", new_role);
}

void on_failback_callback(const char *new_role, void *user_data) {
    printf("FAILBACK: Now %s\n", new_role);
}
```

---

## 🎉 Что ты узнал

- ✅ Active-Standby архитектура
- ✅ SHSP heartbeat protocol
- ✅ Automatic failover/failback
- ✅ State sync с SSRP
- ✅ Load balancer интеграция

---

## Следующий tutorial

**Tutorial 7:** Custom Guards — Создание своих защитников

---

_"Downtime — это не опция."_
