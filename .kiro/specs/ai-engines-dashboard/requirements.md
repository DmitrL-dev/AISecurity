# AI Engines Dashboard — Requirements

> **Фаза:** Phase 7 AI Engines
> **Статус:** ✅ Complete
> **Дата:** 2026-01-30

---

## Цель

Расширить Dashboard для управления и мониторинга AI Security engines:
- **Qwen3-Guard** (0.6B) — быстрая safety classification
- **Foundation-sec** (8B) — глубокий reasoning с MITRE ATT&CK mapping

---

## Функциональные требования

### FR-1: Engine Monitoring
- **FR-1.1:** Отображать статус engine (online/offline/loading)
- **FR-1.2:** Показывать real-time метрики (calls, latency, errors)
- **FR-1.3:** Графики за 24 часа (calls, latency, errors)
- **FR-1.4:** Latency percentiles (P50, P95, P99)

### FR-2: Engine Configuration
- **FR-2.1:** Настройка параметров через drawer
- **FR-2.2:** Toggle enabled/disabled для engines
- **FR-2.3:** Сохранение конфигурации в API

### FR-3: Reasoning Visualization
- **FR-3.1:** Отображение reasoning traces от Foundation-sec
- **FR-3.2:** Раскрывающийся thinking block
- **FR-3.3:** Confidence scores

### FR-4: MITRE ATT&CK Integration
- **FR-4.1:** Визуализация тактик (14 categories)
- **FR-4.2:** Группировка techniques по тактикам
- **FR-4.3:** Confidence bars для каждой technique
- **FR-4.4:** Ссылки на attack.mitre.org

### FR-5: Engine Comparison
- **FR-5.1:** Side-by-side анализ одного payload
- **FR-5.2:** Сравнение результатов Qwen3-Guard vs Foundation-sec
- **FR-5.3:** Объединённый risk score

### FR-6: Safety Categories (Qwen3-Guard)
- **FR-6.1:** Grid из 9 safety categories
- **FR-6.2:** Счётчики detections по категориям

---

## Нефункциональные требования

### NFR-1: Performance
- Загрузка stats < 500ms
- UI responsive при 1000+ calls/min

### NFR-2: UX
- Dark theme consistency
- Animated status indicators
- Collapsible sections

### NFR-3: Accessibility
- ARIA labels для interactive elements
- Keyboard navigation

---

## User Stories

| ID | Story | Priority |
|----|-------|----------|
| US-1 | Как аналитик, я хочу видеть статус engines на одном экране | P0 |
| US-2 | Как SOC оператор, я хочу тестировать payload на обоих engines | P0 |
| US-3 | Как security researcher, я хочу видеть MITRE mappings | P1 |
| US-4 | Как admin, я хочу настраивать engines без restart | P1 |
| US-5 | Как аналитик, я хочу сравнивать результаты engines | P2 |

---

## Acceptance Criteria

- [ ] AC-1: Build проходит без ошибок
- [ ] AC-2: Все 5 tabs рендерятся корректно
- [ ] AC-3: EngineCard показывает mock/real данные
- [ ] AC-4: MitreAttackMap отображает 14 тактик
- [ ] AC-5: ReasoningViewer раскрывает thinking block
- [ ] AC-6: EngineCompareView показывает side-by-side
