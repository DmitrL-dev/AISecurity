# AI Engines Dashboard — Design

> **Фаза:** Phase 7 AI Engines
> **Статус:** ✅ Complete
> **Дата:** 2026-01-30

---

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                    /brain page                               │
├─────────────────────────────────────────────────────────────┤
│  [Overview] [AI Engines] [Compare] │ [Qwen3-Guard] [FS]    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────┐  ┌─────────────────────┐          │
│  │    EngineCard       │  │    EngineCard       │          │
│  │    Qwen3-Guard      │  │    Foundation-sec   │          │
│  └─────────────────────┘  └─────────────────────┘          │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  EngineStatsPanel (selected engine)                  │  │
│  │  • Total Calls  • Latency  • Success Rate  • Uptime  │  │
│  │  • P50/P95/P99  • 24h charts                         │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌────────────────────────┐  ┌─────────────────────────┐   │
│  │  ReasoningViewer       │  │  MitreAttackMap        │   │
│  │  • Conclusion          │  │  • 14 tactics          │   │
│  │  • Thinking (expand)   │  │  • Techniques grid     │   │
│  │  • Recommendations     │  │  • Confidence bars     │   │
│  └────────────────────────┘  └─────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Компоненты

### 1. EngineCard.tsx
```typescript
interface EngineCardProps {
  name: string
  displayName: string
  description: string
  onConfigure: () => void
}
```
- Fetches stats from `/api/brain/engines/[name]/stats`
- Shows: status indicator, calls, latency, errors
- Configure button opens EngineConfigDrawer

### 2. EngineStatsPanel.tsx
```typescript
interface EngineStatsPanelProps {
  engineName: string
  refreshInterval?: number
}
```
- Grid of stat cards (Total Calls, Latency, Success Rate, Uptime)
- Latency percentiles (P50/P95/P99)
- 24h mini bar charts

### 3. ReasoningViewer.tsx
```typescript
interface ReasoningViewerProps {
  result: AnalysisResult
  showRaw?: boolean
}
```
- Risk score banner
- Conclusion block with copy
- Collapsible thinking trace
- MITRE techniques list
- Recommendations

### 4. MitreAttackMap.tsx
```typescript
interface MitreAttackMapProps {
  techniques: MitreTechnique[]
  compact?: boolean
}
```
- Tactics timeline (14 colors)
- Expandable tactic groups
- Confidence bars per technique
- External links to MITRE

### 5. EngineCompareView.tsx
```typescript
// No props - self-contained with internal state
```
- Payload input
- Side-by-side results
- Combined risk assessment

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/brain/engines/[name]/stats` | GET | Engine metrics |
| `/api/brain/engines/[name]/analyze` | POST | Run analysis |
| `/api/brain/engines/[name]/config` | GET/PUT | Engine config |

---

## Data Flow

```
User clicks tab
       │
       ▼
   setMainTab()
       │
       ▼
   Conditional render
       │
       ├──► EngineStatsPanel
       │         │
       │         ▼
       │    fetch(/api/brain/engines/[name]/stats)
       │         │
       │         ▼
       │    Render metrics
       │
       └──► MitreAttackMap
                 │
                 ▼
            Render techniques from props
```

---

## Файловая структура

```
dashboard/src/
├── app/brain/
│   └── page.tsx              # Extended with 5 tabs
├── components/
│   ├── EngineCard.tsx        # Engine status card
│   ├── EngineStatsPanel.tsx  # Detailed metrics
│   ├── ReasoningViewer.tsx   # Reasoning traces
│   ├── MitreAttackMap.tsx    # MITRE visualization
│   └── EngineCompareView.tsx # Side-by-side compare
└── app/api/brain/engines/
    └── [name]/
        ├── stats/route.ts    # Stats endpoint
        └── analyze/route.ts  # Analysis endpoint
```

---

## Риски и митигации

| Риск | Митигация |
|------|-----------|
| BRAIN API недоступен | Mock данные в dev mode |
| Высокая latency Foundation-sec | Loading states, async |
| 16GB VRAM требуется | Lazy loading, INT8 quant |
