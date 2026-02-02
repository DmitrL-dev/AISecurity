# Phase 8: BRAIN Swarm — Tasks

> **Phase:** 8
> **Version:** 1.0
> **Дата:** 2026-01-30

---

## Phase 8.1: Specification ✅ COMPLETE

- [x] requirements.md — APPROVED
- [x] design.md — APPROVED
- [x] tasks.md — APPROVED

---

## Phase 8.2: Tests First (TDD) ✅ COMPLETE

### 8.2.1 Unit Tests — SwarmNode ✅ 6 passed

- [x] `test_swarm_node_creation` — node ID генерируется
- [x] `test_swarm_node_to_json` — сериализация в JSON
- [x] `test_swarm_node_from_json` — десериализация
- [x] `test_node_status_transitions` — online→degraded→offline
- [x] `test_node_status_values`
- [x] `test_node_status_from_string`

### 8.2.2 Unit Tests — SwarmTransport ✅ 7 passed

- [x] `test_transport_connect`
- [x] `test_transport_publish` — публикация сообщения (mock)
- [x] `test_transport_subscribe` — подписка (mock)
- [x] `test_transport_reconnect` — переподключение
- [x] `test_transport_close`
- [x] `test_nats_connect_with_servers`
- [x] `test_nats_publish`

### 8.2.3 Unit Tests — SwarmDiscovery ✅ 5 passed

- [x] `test_register_node` — регистрация ноды
- [x] `test_heartbeat_sent` — heartbeat отправляется
- [x] `test_node_timeout` — нода удаляется через 30с
- [x] `test_known_nodes_update` — список нод обновляется
- [x] `test_ignore_own_registration`

### 8.2.4 Unit Tests — SwarmSync ✅ 4 passed

- [x] `test_broadcast_patterns` — паттерны публикуются
- [x] `test_receive_patterns` — паттерны импортируются
- [x] `test_ignore_own_patterns` — игнор своих сообщений
- [x] `test_deduplication`

### 8.2.5 Integration Tests

- [ ] `test_two_nodes_discovery` — 2 ноды видят друг друга
- [ ] `test_pattern_propagation` — паттерн распространяется
- [ ] `test_node_failure_detection` — обнаружение падения

---

## Phase 8.3: Implementation

### 8.3.1 Backend (Python)

- [ ] **SwarmNode** — `src/brain/swarm/node.py`
  - Dataclass с сериализацией
  - NodeStatus enum

- [ ] **SwarmTransport** — `src/brain/swarm/transport.py`
  - ABC interface
  - Mock implementation для тестов

- [ ] **NatsTransport** — `src/brain/swarm/nats_transport.py`
  - NATS client
  - JetStream setup
  - Auto-reconnect

- [ ] **SwarmDiscovery** — `src/brain/swarm/discovery.py`
  - Registration
  - Heartbeat loop
  - Dead node detection

- [ ] **SwarmSync** — `src/brain/swarm/sync.py`
  - Pattern broadcast
  - Federation import
  - Deduplication

- [ ] **SwarmManager** — `src/brain/swarm/manager.py`
  - Orchestrator
  - Lifecycle management
  - Integration с CollectiveImmunity

### 8.3.2 API Endpoints

- [ ] **GET /api/swarm/nodes** — список нод
- [ ] **GET /api/swarm/stats** — агрегированная статистика
- [ ] **POST /api/swarm/broadcast** — trigger pattern broadcast

### 8.3.3 Dashboard Frontend

- [ ] **SwarmStatus.tsx** — компонент статуса swarm
- [ ] **SwarmNodesTable.tsx** — список нод
- [ ] **SwarmPage.tsx** — страница /swarm

### 8.3.4 Docker & Config

- [ ] **docker-compose.nats.yml** — NATS JetStream
- [ ] **config/swarm.yaml** — конфигурация
- [ ] **Dockerfile** — добавить NATS deps

---

## Phase 8.4: Verification

- [ ] Все unit tests pass
- [ ] Integration tests pass
- [ ] 3 ноды видят друг друга (docker-compose)
- [ ] Dashboard показывает все ноды
- [ ] Pattern sharing работает
- [ ] Документация обновлена

---

## Dependencies

```
nats-py>=2.7.0
```

---

## Test Commands

```bash
# Unit tests
pytest src/brain/swarm/tests/ -v

# Integration tests (requires NATS)
docker-compose -f docker-compose.nats.yml up -d
pytest src/brain/swarm/tests/integration/ -v

# All tests
pytest src/brain/ -v --cov=src/brain/swarm
```

---

## Acceptance Criteria

| Критерий | Тест |
|----------|------|
| Node discovery < 2s | `test_register_node` |
| Heartbeat 5s | `test_heartbeat_sent` |
| Timeout 30s | `test_node_timeout` |
| Pattern sync < 5s | `test_pattern_propagation` |
| 15+ unit tests | pytest count |
