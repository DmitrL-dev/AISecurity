# SENTINEL Academy — Module 8

## High Availability

_SSP Level | Duration: 5 hours_

---

## Introduction

Production = High Availability.

Downtime = lost money and trust.

---

## 8.1 HA Concepts

### Availability Levels

| Level | Downtime/Year | Uptime % |
|-------|---------------|----------|
| One Nine | 36.5 days | 90% |
| Two Nines | 3.65 days | 99% |
| Three Nines | 8.76 hours | 99.9% |
| Four Nines | 52.6 minutes | 99.99% |
| Five Nines | 5.26 minutes | 99.999% |

### Shield Target: 99.99% (Four Nines)

52 minutes downtime per year.

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
    }
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

---

## 8.6 Load Balancer Configuration

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

## 8.7 CLI Commands

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
```

---

## Practice

### Task 1

Deploy Active-Standby cluster:
- 2 nodes
- Heartbeat 500ms
- Auto-failback

### Task 2

Test failover:
- Stop primary
- Measure failover time
- Verify standby became primary

### Task 3

Configure monitoring:
- Prometheus metrics
- Alert on peer disconnect

---

## Module 8 Summary

- HA = mandatory for production
- Active-Standby simpler, Active-Active more powerful
- Split-brain = serious problem
- State sync = consistency
- Monitoring = visibility

---

## Next Module

**Module 9: Monitoring & Observability**

Complete observability for Shield.

---

_"Downtime is not an option. HA is a requirement."_
