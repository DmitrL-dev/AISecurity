# SENTINEL Academy — Module 8

## High Availability

_SSP Level | Duration: 4 hours_

---

## Overview

Shield supports enterprise HA:

| Mode | Description |
|------|-------------|
| Active-Standby | Primary + backup |
| Active-Active | Load distribution |

---

## SHSP — Hot Standby Protocol

### State Machine

```
┌─────────┐ promote  ┌─────────┐
│ STANDBY │─────────►│ PRIMARY │
└─────────┘          └─────────┘
     ▲                    │
     │ failback           │ failure
     │                    ▼
     │              ┌─────────┐
     └──────────────│  FAILED │
                    └─────────┘
```

### CLI Configuration

```
Shield(config)# standby ip 10.0.0.100
Shield(config)# standby priority 100
Shield(config)# standby preempt
Shield(config)# standby timers 1 3
Shield(config)# failover
```

---

## SSRP — State Replication

### What Gets Replicated

- Active sessions
- Rate limit counters
- Blocklists
- Context history
- Metrics

### Modes

| Mode | Latency | Consistency |
|------|---------|-------------|
| Sync | Higher | Strong |
| Async | Lower | Eventual |
| Batched | Lowest | Eventual + delay |

---

## Failover

### Automatic

Triggers:
- Heartbeat timeout (3 missed)
- Process crash
- Network partition

### Manual

```
Shield# ha force standby
Shield# ha force active
```

---

## Monitoring

```
Shield# show ha status
Role: PRIMARY
Peer: 192.168.1.2 (STANDBY)
Last heartbeat: 500ms ago
Sync status: OK
```

---

_"HA is not optional for production."_
