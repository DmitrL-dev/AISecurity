# SENTINEL SOC Dashboard — Requirements

> **Компонент:** saas/dashboard/
> **Статус:** Implemented (MVP)
> **Дата:** 2026-02-12

---

## 1. Обзор

Next.js 15 + React 19 Security Operations Center для SENTINEL. Визуализация угроз в реальном времени, AI-ассистент для анализа промптов, мониторинг engines, управление инцидентами, и Academy для обучения. Standalone Docker-образ для on-premise деплоя.

---

## 2. Функциональные требования

### FR-1: Страницы

| ID | Страница | Route | Описание | Приоритет |
|----|----------|-------|----------|-----------|
| FR-1.1 | Dashboard | `/` | Основная панель: метрики, hex network, incidents | P0 |
| FR-1.2 | Brain | `/brain` | Статус движков, health check | P0 |
| FR-1.3 | Analyze | `/analyze` | Ручной анализ промптов | P0 |
| FR-1.4 | Incidents | `/incidents` | Список инцидентов с drawer | P0 |
| FR-1.5 | Strike | `/strike` | Offensive testing panel | P1 |
| FR-1.6 | Academy | `/academy` | Обучающие материалы по AI security | P1 |
| FR-1.7 | Settings | `/settings` | Настройки, API keys | P1 |

### FR-2: Компоненты

| ID | Компонент | Описание | Приоритет |
|----|-----------|----------|-----------|
| FR-2.1 | AIAssistant | Встроенный AI-чат для анализа промптов | P0 |
| FR-2.2 | HexNetwork | Hexagonal network visualization | P0 |
| FR-2.3 | SunburstChart | Threat category sunburst (D3-based) | P0 |
| FR-2.4 | MetricsBar | Top metrics bar (scans, blocks, latency) | P0 |
| FR-2.5 | IncidentDrawer | Slide-out panel с деталями инцидента | P0 |
| FR-2.6 | Sidebar | Navigation sidebar | P0 |
| FR-2.7 | Header | Top header + search | P0 |
| FR-2.8 | Skeleton | Loading state components | P1 |
| FR-2.9 | Toast | Notification toasts | P1 |

### FR-3: API Routes (Backend-for-Frontend)

| ID | Route | Проксирует | Описание |
|----|-------|------------|----------|
| FR-3.1 | `/api/brain/analyze` | `POST /analyze` | Анализ промпта |
| FR-3.2 | `/api/brain/engines` | `GET /engines` | Список движков |
| FR-3.3 | `/api/brain/health` | `GET /health` | Health check |
| FR-3.4 | `/api/metrics` | Internal | Dashboard метрики |

---

## 3. Нефункциональные требования

| ID | Требование |
|----|------------|
| NFR-1 | Next.js 15 + React 19 (App Router) |
| NFR-2 | TailwindCSS для стилизации |
| NFR-3 | Standalone output для Docker |
| NFR-4 | Dark theme по умолчанию |
| NFR-5 | Responsive (desktop-first, mobile-friendly) |
| NFR-6 | Health check endpoint для Docker |
| NFR-7 | TypeScript (strict mode bypassed для DB stubs) |

---

## 4. User Stories

### US-1: Аналитик проверяет промпт

```gherkin
GIVEN я на странице /analyze
WHEN я ввожу подозрительный промпт
THEN AI Assistant показывает verdict: BLOCK/WARN/SAFE
AND список обнаруженных угроз с confidence
```

### US-2: SOC-оператор мониторит

```gherkin
GIVEN я на Dashboard
WHEN происходит новый инцидент
THEN MetricsBar обновляется
AND инцидент появляется в IncidentDrawer
```

### US-3: Просмотр движков

```gherkin
GIVEN я на странице /brain
WHEN страница загружается
THEN вижу список всех engines с их status и latency
AND health check показывает общий статус
```

---

## 5. Acceptance Criteria

- [x] AC-1: 7 страниц (Dashboard, Brain, Analyze, Incidents, Strike, Academy, Settings)
- [x] AC-2: AI Assistant работает через /api/brain/analyze
- [x] AC-3: HexNetwork + SunburstChart визуализации
- [x] AC-4: Incident management с drawer
- [x] AC-5: Docker build (standalone)
- [x] AC-6: Health check endpoint
- [ ] AC-7: Keycloak auth integration (see dashboard-auth spec)
- [ ] AC-8: Real-time WebSocket updates

---

## 6. Файловая структура

```
saas/dashboard/
├── src/
│   ├── app/
│   │   ├── page.tsx              # Dashboard home
│   │   ├── layout.tsx            # Root layout + providers
│   │   ├── globals.css           # Global styles
│   │   ├── academy/page.tsx
│   │   ├── analyze/page.tsx
│   │   ├── brain/page.tsx
│   │   ├── incidents/page.tsx
│   │   ├── settings/page.tsx
│   │   ├── strike/page.tsx
│   │   └── api/
│   │       ├── brain/
│   │       │   ├── analyze/route.ts
│   │       │   ├── engines/route.ts
│   │       │   └── health/route.ts
│   │       └── metrics/route.ts
│   ├── components/
│   │   ├── AIAssistant.tsx
│   │   ├── Header.tsx
│   │   ├── HexNetwork.tsx
│   │   ├── IncidentDrawer.tsx
│   │   ├── MetricsBar.tsx
│   │   ├── Sidebar.tsx
│   │   ├── Skeleton.tsx
│   │   ├── SunburstChart.tsx
│   │   ├── Toast.tsx
│   │   └── index.ts
│   ├── db/
│   │   ├── index.ts             # DB stub (throws at runtime)
│   │   └── schema.ts            # Schema stubs for TypeScript
│   └── lib/
│       ├── api-key-auth.ts      # API key authentication
│       └── audit.ts             # Auth audit logging
├── Dockerfile                   # Multi-stage Docker build
├── next.config.js               # Standalone output, TS/ESLint bypasses
├── tailwind.config.js
├── tsconfig.json
├── package.json
└── .dockerignore
```

---

## 7. Зависимости

| Пакет | Назначение |
|-------|------------|
| next 15.x | Framework |
| react 19.x | UI library |
| tailwindcss | Styling |
| recharts | Charts |
| lucide-react | Icons |

---

## 8. Риски

| Риск | Митигация |
|------|-----------|
| DB stubs → runtime errors в production | Реализовать настоящий DB layer перед деплоем |
| TypeScript strict bypassed | Постепенно восстановить strict mode |
| Brain API недоступен | Graceful fallback в UI |
