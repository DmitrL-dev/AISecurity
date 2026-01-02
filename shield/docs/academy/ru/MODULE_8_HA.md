# SENTINEL Academy — Module 8

## High Availability

_SSP Level | Время: 5 часов_

---

## Введение

Production = High Availability.

Downtime = потеря денег и доверия.

---

## 8.1 HA Concepts

### Availability Levels

| Level       | Downtime/Year | Uptime % |
| ----------- | ------------- | -------- |
| One Nine    | 36.5 days     | 90%      |
| Two Nines   | 3.65 days     | 99%      |
| Three Nines | 8.76 hours    | 99.9%    |
| Four Nines  | 52.6 minutes  | 99.99%   |
| Five Nines  | 5.26 minutes  | 99.999%  |

### Shield Target: 99.99% (Four Nines)

52 минуты downtime в год.

---

## 8.2 HA Architectures

### Active-Standby

```
     ┌─────────────────┐
     │  LOAD BALANCER  │
     └────────┬────────┘
              │
    ┌─────────┴─────────┐
    │                   │
┌───▼───┐          ┌───▼───┐
│PRIMARY│◄────────►│STANDBY│
│(Active)│  SHSP   │(Passive)│
└───────┘          └───────┘
```

**Pros:**

- Simple
- Clear ownership
- Easy debugging

**Cons:**

- 50% capacity unused
- Failover delay

### Active-Active

```
     ┌─────────────────┐
     │  LOAD BALANCER  │
     └────────┬────────┘
              │
    ┌─────────┴─────────┐
    │                   │
┌───▼───┐          ┌───▼───┐
│ NODE1 │◄────────►│ NODE2 │
│(Active)│  SSRP   │(Active)│
└───────┘          └───────┘
```

**Pros:**

- Full capacity
- No failover delay
- Better load distribution

**Cons:**

- State sync complexity
- Split-brain risk

### N+1 Cluster

```
     ┌─────────────────┐
     │  LOAD BALANCER  │
     └────────┬────────┘
              │
    ┌─────────┼─────────┐
    │         │         │
┌───▼───┐ ┌───▼───┐ ┌───▼───┐
│ NODE1 │ │ NODE2 │ │ NODE3 │
│(Active)│ │(Active)│ │(Spare)│
└───────┘ └───────┘ └───────┘
```

**Pros:**

- N nodes working
- 1 ready to take over
- Handles 1 failure

---

## 8.3 Active-Standby Configuration

### Primary Node

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
      "name": "prod-cluster",
      "bind_address": "0.0.0.0",
      "bind_port": 5001,
      "advertise_address": "192.168.1.1"
    },

    "peers": [
      {
        "node_id": "node-2",
        "address": "192.168.1.2",
        "port": 5001
      }
    ],

    "heartbeat": {
      "interval_ms": 1000,
      "timeout_ms": 3000,
      "max_missed": 3
    },

    "failover": {
      "delay_ms": 5000,
      "auto_failback": true,
      "failback_delay_ms": 60000
    },

    "state_sync": {
      "enabled": true,
      "mode": "async",
      "batch_interval_ms": 100
    }
  }
}
```

### Standby Node

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
      "name": "prod-cluster",
      "bind_address": "0.0.0.0",
      "bind_port": 5001,
      "advertise_address": "192.168.1.2"
    },

    "peers": [
      {
        "node_id": "node-1",
        "address": "192.168.1.1",
        "port": 5001
      }
    ]
  }
}
```

---

## 8.4 Failover Process

### Timeline

```
T=0     Primary fails (crash, network, etc.)
T=1s    Standby: Heartbeat missed (1/3)
T=2s    Standby: Heartbeat missed (2/3)
T=3s    Standby: Heartbeat missed (3/3)
T=3s    Standby: Declares primary DEAD
T=3s    Standby: Starts failover delay (5s)
T=8s    Standby: Promoted to PRIMARY
T=8s    Standby: Starts serving requests
T=8s    Load balancer: Health check passes
T=9s    Traffic flows to new primary
```

**Total failover time: ~9 seconds**

### Failover Triggers

| Trigger             | Description                   |
| ------------------- | ----------------------------- |
| Heartbeat timeout   | No heartbeat for 3+ intervals |
| Health check fail   | API returns error             |
| Manual trigger      | Operator command              |
| Resource exhaustion | OOM, disk full                |

---

## 8.5 Split-Brain Prevention

### Problem

```
           NETWORK PARTITION
                 │
    ┌────────────┼────────────┐
    │            │            │
┌───▼───┐        │       ┌───▼───┐
│ NODE1 │        │       │ NODE2 │
│"I'm   │   ✗    │   ✗   │"I'm   │
│PRIMARY"│       │       │PRIMARY"│
└───────┘        │       └───────┘
                 │
        TWO PRIMARIES = DATA CORRUPTION
```

### Solutions

**1. Quorum-based:**

```json
{
  "split_brain": {
    "prevention": "quorum",
    "quorum_size": 2,
    "nodes": ["node-1", "node-2", "arbiter"]
  }
}
```

Need majority to become primary.

**2. Fencing:**

```json
{
  "split_brain": {
    "prevention": "fencing",
    "fence_device": "stonith",
    "fence_timeout_ms": 10000
  }
}
```

Shutdown the other node before becoming primary.

**3. Witness/Arbiter:**

```json
{
  "split_brain": {
    "prevention": "witness",
    "witness_address": "192.168.1.100",
    "witness_port": 5002
  }
}
```

Third party decides who is primary.

---

## 8.6 State Synchronization

### What to Sync

| State       | Priority | Sync Mode |
| ----------- | -------- | --------- |
| Sessions    | High     | Async     |
| Rate limits | Medium   | Async     |
| Blocklists  | High     | Sync      |
| Config      | High     | Sync      |
| Metrics     | Low      | Batch     |

### Configuration

```json
{
  "state_sync": {
    "enabled": true,
    "protocol": "SSRP",

    "categories": {
      "sessions": {
        "enabled": true,
        "mode": "async",
        "ttl_seconds": 3600
      },
      "rate_limits": {
        "enabled": true,
        "mode": "async",
        "ttl_seconds": 60
      },
      "blocklists": {
        "enabled": true,
        "mode": "sync"
      }
    },

    "batch": {
      "enabled": true,
      "interval_ms": 100,
      "max_items": 100
    },

    "compression": {
      "enabled": true,
      "algorithm": "lz4"
    }
  }
}
```

---

## 8.7 Load Balancer Configuration

### Nginx

```nginx
upstream shield_cluster {
    server 192.168.1.1:8080 weight=10 max_fails=3 fail_timeout=30s;
    server 192.168.1.2:8080 backup;
}

server {
    listen 80;

    location /api/ {
        proxy_pass http://shield_cluster;
        proxy_connect_timeout 1s;
        proxy_read_timeout 5s;

        # Health check
        health_check interval=1s fails=3 passes=1 uri=/health;
    }
}
```

### HAProxy

```haproxy
frontend shield_frontend
    bind *:80
    default_backend shield_backend

backend shield_backend
    option httpchk GET /health
    http-check expect status 200

    server node1 192.168.1.1:8080 check inter 1s fall 3 rise 1
    server node2 192.168.1.2:8080 check inter 1s fall 3 rise 1 backup
```

---

## 8.8 Health Checks

### Shield Health Endpoint

```bash
curl http://localhost:8080/health
```

```json
{
  "status": "healthy",
  "version": "1.2.0",
  "uptime_seconds": 86400,
  "ha": {
    "role": "primary",
    "peer_status": "connected",
    "sync_lag": 0
  },
  "components": {
    "api": "healthy",
    "guards": "healthy",
    "rules": "healthy"
  }
}
```

### Deep Health Check

```bash
curl http://localhost:8080/health/deep
```

Checks:

- All guards initialized
- All rules loaded
- Database connectivity
- Peer connectivity

---

## 8.9 Monitoring HA

### Key Metrics

```prometheus
# HA state (1=primary, 0=standby)
shield_ha_is_primary{node="node-1"} 1

# Peer status
shield_ha_peer_connected{peer="node-2"} 1

# Heartbeat latency
shield_ha_heartbeat_latency_ms{peer="node-2"} 5

# Failover count
shield_ha_failovers_total{node="node-1"} 2

# Sync lag (items behind)
shield_ha_sync_lag{node="node-1"} 0
```

### Alerts

```yaml
- alert: ShieldHAPeerDisconnected
  expr: shield_ha_peer_connected == 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "HA peer disconnected"

- alert: ShieldHASyncLag
  expr: shield_ha_sync_lag > 100
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "HA sync lag detected"
```

---

## 8.10 CLI Commands

```bash
Shield> show ha status

╔══════════════════════════════════════════════════════════╗
║                    HA STATUS                              ║
╚══════════════════════════════════════════════════════════╝

Cluster: prod-cluster
Mode: active-standby
My Node: node-1
My Role: PRIMARY
State: RUNNING

Peers:
┌──────────┬───────────────┬──────────┬─────────────┐
│ Node     │ Address       │ Role     │ Status      │
├──────────┼───────────────┼──────────┼─────────────┤
│ node-2   │ 192.168.1.2   │ STANDBY  │ SYNCHRONIZED│
└──────────┴───────────────┴──────────┴─────────────┘

Shield> ha failover
Initiating manual failover...
Demoting to STANDBY...
Failover complete. New primary: node-2

Shield> ha failback
Initiating failback...
Resuming as PRIMARY...
Failback complete.
```

---

## Практика

### Задание 1

Разверни Active-Standby кластер:

- 2 узла
- Heartbeat 500ms
- Auto-failback

### Задание 2

Протестируй failover:

- Останови primary
- Измерь время failover
- Проверь что standby стал primary

### Задание 3

Настрой мониторинг:

- Prometheus metrics
- Alert на peer disconnect

---

## Итоги Module 8

- HA = обязательно для production
- Active-Standby проще, Active-Active мощнее
- Split-brain = серьёзная проблема
- State sync = consistency
- Monitoring = visibility

---

## Следующий модуль

**Module 9: Monitoring & Observability**

Полная observability для Shield.

---

_"Downtime — это не опция. HA — это требование."_
