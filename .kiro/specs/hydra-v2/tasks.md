# HYDRA v2 — Tasks

## Phase 1: Core Architecture

- [x] **Task 1.1**: HYDRA package exists
- [x] **Task 1.2**: Создать `strike/hydra/engine_v2.py`
  - HydraEngine class (~350 LOC)
  - HydraConfig, HydraResult dataclasses
  - AttackPhase, AttackStatus enums

---

## Phase 2: Model Adapters

- [x] **Task 2.1**: OpenAIAdapter
- [x] **Task 2.2**: AnthropicAdapter
- [x] **Task 2.3**: GeminiAdapter

---

## Phase 3: Attack Strategies

- [x] **Task 3.1**: JailbreakStrategy (5 templates)
- [x] **Task 3.2**: ExtractionStrategy (5 templates)
- [x] **Task 3.3**: InjectionStrategy (5 templates)

---

## Features

- [x] Parallel attack execution
- [x] Configurable concurrency limit
- [x] Adaptive strategy selection
- [x] Result aggregation and best-result tracking
- [x] Extensible adapter/strategy registration

---

## Acceptance Criteria

| Критерий | Метрика | Статус |
|----------|---------|--------|
| HydraEngine | v2.0.0 | ✅ |
| Model adapters | 3 | ✅ |
| Attack strategies | 3 | ✅ |
| LOC | ~350 | ✅ |

---

**Created:** 2026-01-09
**Completed:** 2026-01-09
