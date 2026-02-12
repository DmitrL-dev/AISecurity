# SENTINEL SOC Dashboard — Tasks

> **Компонент:** saas/dashboard/
> **Дата:** 2026-02-12

---

## Реализованные (MVP)

### Pages
- [x] T-1: Dashboard home (/, MetricsBar + HexNetwork)
- [x] T-2: Brain (/brain, engines list + health)
- [x] T-3: Analyze (/analyze, manual prompt analysis)
- [x] T-4: Incidents (/incidents, IncidentDrawer)
- [x] T-5: Strike (/strike)
- [x] T-6: Academy (/academy)
- [x] T-7: Settings (/settings)

### Components
- [x] T-8: AIAssistant (chat UI + useAnalyze hook)
- [x] T-9: HexNetwork (hexagonal graph)
- [x] T-10: SunburstChart (D3-based)
- [x] T-11: MetricsBar
- [x] T-12: IncidentDrawer
- [x] T-13: Sidebar + Header
- [x] T-14: Skeleton + Toast

### API Routes
- [x] T-15: /api/brain/analyze (proxy to Brain)
- [x] T-16: /api/brain/engines
- [x] T-17: /api/brain/health
- [x] T-18: /api/metrics

### Infra
- [x] T-19: Dockerfile (multi-stage, standalone)
- [x] T-20: TailwindCSS config
- [x] T-21: DB stubs (index.ts + schema.ts)
- [x] T-22: API key auth (lib/api-key-auth.ts)
- [x] T-23: Auth audit logging (lib/audit.ts)

## Roadmap

- [ ] T-24: Keycloak auth integration (see dashboard-auth spec)
- [ ] T-25: Real-time WebSocket updates
- [ ] T-26: Proper PostgreSQL database layer
- [ ] T-27: TypeScript strict mode restoration
- [ ] T-28: E2E tests (Playwright)
- [ ] T-29: Dark/light theme switcher
- [ ] T-30: Mobile-responsive navigation
- [ ] T-31: Export reports (PDF/CSV)
- [ ] T-32: Alert rules configuration
- [ ] T-33: Multi-tenant support
