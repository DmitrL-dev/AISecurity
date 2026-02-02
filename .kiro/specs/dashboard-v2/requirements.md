# Dashboard V2 — Requirements

## Обзор

Расширение SENTINEL Dashboard с BRAIN management, аудитом безопасности и real-time аналитикой.

## User Stories

### US-1: BRAIN Engine Management
**Как** оператор безопасности,  
**Хочу** видеть статус всех движков и управлять ими,  
**Чтобы** быстро реагировать на инциденты и оптимизировать защиту.

**Acceptance Criteria:**
- [ ] AC-1.1: Страница `/brain` показывает список всех движков
- [ ] AC-1.2: Toggle включения/выключения каждого движка
- [x] AC-1.3: Индикатор статуса (online/offline/error)
- [x] AC-1.4: API proxy `/api/brain/engines/*`

---

### US-2: Immutable Audit Log
**Как** compliance officer,  
**Хочу** просматривать неизменяемый лог всех действий,  
**Чтобы** проводить расследования и обеспечивать соответствие требованиям.

**Acceptance Criteria:**
- [x] AC-2.1: Страница `/audit` с таблицей событий
- [x] AC-2.2: Фильтрация по уровню (CRITICAL/WARNING/INFO/DEBUG)
- [x] AC-2.3: HMAC подписи и криптографическая цепочка
- [x] AC-2.4: Кнопка Verify Integrity
- [ ] AC-2.5: Экспорт логов (JSON/CSV)

---

### US-3: Text Analysis Interface
**Как** аналитик угроз,  
**Хочу** анализировать тексты через веб-интерфейс,  
**Чтобы** быстро проверять подозрительные промпты.

**Acceptance Criteria:**
- [ ] AC-3.1: Страница `/analyze` с формой ввода
- [ ] AC-3.2: Отображение результатов анализа
- [ ] AC-3.3: Выбор движков для анализа
- [ ] AC-3.4: История последних анализов

---

### US-4: Real-time Dashboard Overview
**Как** SOC оператор,  
**Хочу** видеть real-time метрики на главной странице,  
**Чтобы** мониторить состояние системы.

**Acceptance Criteria:**
- [x] AC-4.1: BRAIN health status widget
- [ ] AC-4.2: Threat counter за период
- [ ] AC-4.3: Engine activity chart
- [ ] AC-4.4: WebSocket для real-time обновлений

---

### US-5: Settings & Configuration
**Как** администратор,  
**Хочу** настраивать параметры через UI,  
**Чтобы** не редактировать env файлы вручную.

**Acceptance Criteria:**
- [ ] AC-5.1: Страница `/settings` с формами
- [ ] AC-5.2: BRAIN API URL configuration
- [ ] AC-5.3: Audit level selection
- [ ] AC-5.4: API key management

---

## Constraints

- **Tech Stack:** Next.js 15, React 19, TypeScript
- **Styling:** Vanilla CSS (no Tailwind)
- **API:** Proxy через Next.js API routes → BRAIN FastAPI
- **Auth:** X-SENTINEL-API-KEY header

## Dependencies

- BRAIN API v1 (done)
- Audit Log API (done)
- Engine Toggle API (done)

---

**Created:** 2026-01-29  
**Author:** SENTINEL Team
