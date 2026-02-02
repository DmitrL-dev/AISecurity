# Phase 8: BRAIN Swarm — Requirements

> **Phase:** 8
> **Version:** 1.0
> **Дата:** 2026-01-30

---

## 1. Обзор

BRAIN Swarm — распределённая архитектура для нескольких BRAIN нод с:
- **Безмастерная топология** — нет single point of failure
- **Federated threat intelligence** — обмен паттернами между нодами
- **Real-time discovery** — автоматическая регистрация нод
- **Dashboard integration** — multi-BRAIN view

---

## 2. Functional Requirements

### FR-01: Node Discovery
- [ ] Ноды регистрируются при старте
- [ ] Heartbeat каждые 5 секунд
- [ ] Автоматическое удаление мёртвых нод (30с timeout)
- [ ] Dashboard получает список активных нод

### FR-02: State Synchronization
- [ ] Конфигурации движков синхронизированы
- [ ] Blocklist entries реплицируются
- [ ] Engine enable/disable распространяется на все ноды

### FR-03: Threat Intelligence Sharing
- [ ] `CollectiveImmunity.export_for_federation()` → NATS publish
- [ ] `CollectiveImmunity.import_federation_data()` ← NATS subscribe
- [ ] Differential privacy сохраняется при передаче

### FR-04: Dashboard Multi-BRAIN View
- [ ] `/api/swarm/nodes` — список нод
- [ ] `/api/swarm/stats` — агрегированная статистика
- [ ] WebSocket events от всех нод

---

## 3. Non-Functional Requirements

### NFR-01: Performance
- Latency между нодами < 100ms (LAN)
- Startup registration < 2s
- Max 50 nodes в кластере

### NFR-02: Reliability
- Graceful degradation при потере связи
- Eventual consistency для state sync
- No data loss при network partition

### NFR-03: Security
- mTLS между нодами
- Pattern hashes (не raw data) в federation
- Encrypted NATS connections

---

## 4. Technical Decisions

### Transport: NATS JetStream

| Критерий | NATS | Redis Pub/Sub | gRPC |
|----------|------|---------------|------|
| Latency | ★★★★★ | ★★★★ | ★★★★★ |
| Persistence | ✅ JetStream | ❌ | ❌ |
| Clustering | Native | Sentinel | Manual |
| Simplicity | ★★★★★ | ★★★★ | ★★★ |

**Решение:** NATS JetStream

### Subject Routing
```
brain.swarm.register       # Node registration
brain.swarm.heartbeat      # Health checks
brain.swarm.config.sync    # Config replication
brain.threat.patterns      # Threat intelligence
brain.events.{node_id}     # Per-node events
```

---

## 5. Existing Code

### CollectiveImmunity (Already Implemented)
- `src/brain/core/collective_immunity.py` — 254 lines
- `export_for_federation()` ✅
- `import_federation_data()` ✅
- Differential Privacy (Laplace noise) ✅
- Pattern hashing ✅

### Missing Components
- [ ] `SwarmNode` — node identity and lifecycle
- [ ] `SwarmTransport` — NATS adapter
- [ ] `SwarmDiscovery` — registration and heartbeat
- [ ] `SwarmSync` — state replication

---

## 6. User Stories

### US-01: Operator adds new BRAIN node
**Given** a running SENTINEL cluster with 2 nodes
**When** operator starts a third BRAIN instance
**Then** the new node appears in Dashboard within 5 seconds

### US-02: Threat pattern is shared
**Given** Node A detects a new jailbreak pattern
**When** the pattern is blocked 3+ times
**Then** all other nodes receive the pattern via federation

### US-03: Node failure handling
**Given** Node B stops responding
**When** 30 seconds pass without heartbeat
**Then** Node B is marked as "offline" in Dashboard

---

## 7. Out of Scope

- Geo-distribution (Phase 8.5)
- Cross-region replication (Phase 9)
- Custom consensus algorithms
- RAFT/Paxos leader election

---

## 8. Acceptance Criteria

| Критерий | Метрика |
|----------|---------|
| Node discovery | < 2s registration |
| Heartbeat | 5s interval, 30s timeout |
| Pattern sharing | < 5s propagation |
| Dashboard view | Shows 3+ nodes |
| Tests | 15+ unit tests |
