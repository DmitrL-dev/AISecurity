# PROJECT_CONTEXT.md — SENTINEL

> **Last Updated:** 2026-01-30
> **Version:** Community Edition

---

## 📊 Project Statistics

| Metric | Value |
|--------|-------|
| **Engine Files** | 249 |
| **Total Tests** | 1,467+ |
| **Dashboard Phase** | 9 Complete |
| **Dashboard Tables** | 10 (Drizzle) |
| **Swarm Modules** | 6 |

---

## 🏗️ Architecture Overview

```
src/brain/
├── api/              # FastAPI endpoints
├── core/             # SentinelAnalyzer, CollectiveImmunity
├── engines/          # Detection engines (249 modules)
├── swarm/            # NEW: Distributed swarm (6 modules)
│   ├── node.py       # SwarmNode identity
│   ├── transport.py  # Abstract transport
│   ├── nats_transport.py  # NATS JetStream
│   ├── discovery.py  # Node discovery
│   ├── sync.py       # Pattern sync
│   └── manager.py    # Orchestrator
├── observability/    # Metrics, health
└── tests/            # Unit tests

dashboard/
├── src/
│   ├── app/          # Next.js pages
│   │   └── api/swarm/  # NEW: Swarm API
│   ├── components/   # React (SwarmStatus)
│   ├── lib/          # Auth, RBAC, API
│   └── db/schema/    # Drizzle ORM (8 tables)
└── docker-compose.db.yml

config/swarm.yaml     # NEW: Swarm configuration
docker-compose.nats.yml  # NEW: NATS JetStream
```

---

## ✅ Completed (2026-01-30)

### Phase 8: BRAIN Swarm
- SwarmNode, SwarmTransport, NatsTransport
- SwarmDiscovery (heartbeat, timeout)
- SwarmSync (CollectiveImmunity federation)
- SwarmManager orchestrator
- 22 unit tests (TDD)
- Dashboard: /api/swarm/nodes, /api/swarm/stats
- SwarmStatus.tsx component
- docker-compose.nats.yml

### Phase 9: Multi-tenant & SaaS
- usage.ts, api-keys.ts schemas
- plan-limits.ts (community/pro/enterprise)
- tenant-context.ts (RLS)
- usage-tracker.ts (async metering)
- api-key-auth.ts (API key validation)
- /api/tenants, /api/tenants/[id]/usage, /api/tenants/[id]/api-keys
- TenantSelector.tsx, UsageWidget.tsx

---

## 🎯 Coverage

- **OWASP LLM Top 10** — Full
- **OWASP ASI Top 10** — Full
- **IMDA MGF for Agentic AI** — Partial

---

## 📝 Next Steps

- **Phase 9:** Multi-tenant & SaaS
- **Phase 10:** Production & Compliance

