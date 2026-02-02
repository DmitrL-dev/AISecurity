# Dashboard V2 — Tasks

## Phase 1: BRAIN Management (✅ Partially Done)

- [x] **Task 1.1**: Создать `/brain` page
  - Список движков с статусом
  - Toggle enable/disable

- [x] **Task 1.2**: API proxy routes
  - `/api/brain/engines/all`
  - `/api/brain/engines/status`
  - `/api/brain/engines/[name]/toggle`

- [x] **Task 1.3**: Engine config panel ✅
  - Просмотр параметров движка (EngineConfigDrawer)
  - Редактирование (threshold, parameters)
  - Redis persistence
  - Audit logging

---

## Phase 2: Audit Log (✅ Done)

- [x] **Task 2.1**: Создать `/audit` page
  - Таблица с логами
  - Level filter (CRITICAL/WARNING/INFO/DEBUG)
  - Stats cards

- [x] **Task 2.2**: Audit API integration
  - `/api/brain/audit/logs`
  - HMAC signatures
  - Verify integrity button

- [x] **Task 2.3**: Export functionality ✅ (Secure)
  - Signed token URL (5 min TTL)
  - One-time download
  - JSON/CSV export
  - Audit logged

---

## Phase 3: Analysis Interface (✅ Done)

- [x] **Task 3.1**: Создать `/analyze` page ✅
  - Textarea для ввода текста
  - Submit button

- [x] **Task 3.2**: Results display ✅
  - Risk level indicator
  - Matched engines list
  - Details accordion

- [x] **Task 3.3**: Analysis history ✅
  - LocalStorage
  - Последние анализы

---

## Phase 3.5: Analyze Enhancements (✅ Done)

- [x] **Task 3.4**: Engine selector ✅
  - Multi-select движков для анализа
  - Preset groups (All, Injection, Jailbreak, PII)

- [x] **Task 3.5**: Batch analysis ✅
  - Upload CSV/JSON с тестами (max 100)
  - Progress bar
  - Export результатов JSON

- [x] **Task 3.6**: Compare mode ✅
  - Side-by-side textareas
  - Parallel analysis
  - Delta visualization

---

## Phase 4: Real-time Dashboard (✅ Done)

- [x] **Task 4.1**: BRAIN status widget ✅
  - Health indicator
  - Version display

- [x] **Task 4.2**: Metrics charts ✅
  - ThreatMetrics (24h/7d/30d)
  - SunburstChart (breakdown)

- [x] **Task 4.3**: Live Activity ✅
  - LiveActivity (polling 5s)
  - live-threats (simulated WS + toasts)

---

## Phase 5: Settings (✅ Done)

- [x] **Task 5.1**: Settings page redesign ✅
  - BRAIN API configuration (editable URL)
  - Audit level selector (minimal/standard/detailed/forensic)
  - Default engine toggles (8 engines)
  - localStorage persistence
  - API key management

---

## Acceptance Criteria Summary

| Критерий | Метрика | Статус |
|----------|---------|--------|
| BRAIN page | Engine list + toggle + config drawer | ✅ |
| Audit page | Log table + filters + secure export | ✅ |
| Analyze page | Form + results + batch + compare | ✅ |
| Real-time | ThreatMetrics + LiveActivity | ✅ |
| Settings | BRAIN URL + Audit level + Engines | ✅ |

---

**Created:** 2026-01-29  
**Completed:** 2026-01-29 ✅ ALL PHASES DONE
