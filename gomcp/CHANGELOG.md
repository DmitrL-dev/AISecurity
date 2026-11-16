# GoMCP — Changelog

Все значимые изменения в проекте документируются в этом файле.

Формат: [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/)  
Версионирование: [Semantic Versioning](https://semver.org/)

---

## [4.0.0] — 2026-03-10 «SOC Hardened»

### Added
- **SOC Integration (Фазы 1-6)**: Полный SOC pipeline — 8 MCP tools, Decision Logger, Sensor Registry, Correlation Engine, Playbook Engine
- **§24 USER_GUIDE.md**: SOC Section с таблицей инструментов, pipeline diagram, примерами вызовов
- **Doctor SOC**: 7 health checks (service, sensors, events, chain, correlation, compliance, dashboard)

### SOC Hardening (Фазы 7-10)
- **Фаза 7**: USER_GUIDE.md §24 — SOC Section, 8 MCP tools таблица, pipeline diagram, TOC обновлён
- **Фаза 8**: E2E §18 Test Matrix — 14/14 тестов (DL-01 Chain Integrity, SL-01 Sensor Lifecycle, CE-01 Correlation)
- **Фаза 9**: Sensor Authentication §17.3 — `SetSensorKeys()`, Step -1 auth check, `sensor_key` параметр, `SensorKey json:"-"` на SOCEvent
- **Фаза 10**: P2P Incident Sync §8.3 — `SyncIncident` struct (11 полей), `SyncPayload.Version: "1.1"`, `ExportIncidents()` / `ImportIncidents()`, sync_facts handler extension

### Changed
- `SyncPayload` расширен полями `Version` и `Incidents` (backward compatible via `omitempty`)
- sync_facts export/import handlers теперь включают SOC инциденты
- force_resonance_handshake включает incidents в payload
- Версия документации: 3.8.0 → 4.0.0

### Tests
- 16 SOC E2E тестов в `soc_tools_test.go` (8 базовых + 3 auth + 3 §18 + 2 P2P sync)
- 25/25 packages PASS, zero regression

### Deferred
- **Фаза 11**: HTTP API §12.2 → отложено на v4.1.0 (net/http, CORS, graceful shutdown)

---

## [3.8.0] — 2026-03 «Strike Force & Mimicry»

- DIP (Direct Intent Protocol) — 15 tools (H0-H2)
- Synapse P2P — genome handshake, fact sync, peer backup
- Code Crystals, Causal Store, Entropy Gate
- 57+ MCP tools

---

## [3.0.0] — 2026-02 «Oracle & Clean Architecture»

- Local Oracle (ONNX/FTS5) замена Python bridge
- OAuth Hardening (Clean Architecture domain validation)
- Circuit Breaker, Action Oracle, Intent Pipeline
