# PROJECT_CONTEXT.md — SENTINEL

> **Last Updated:** 2026-01-25
> **Version:** Community Edition

---

## 📊 Project Statistics

| Metric | Value |
|--------|-------|
| **Base Engines** | 184 files |
| **Synced Engines** | 35 files |
| **Total Engine Files** | 219 |
| **Detection Engines** | 214 |
| **Utility Modules** | 5 |
| **Total Tests** | 1,200+ |
| **Benchmark F1** | 84.7% |


---

## 🏗️ Architecture Overview

```
src/brain/
├── api/              # FastAPI endpoints
├── core/             # SentinelAnalyzer, config, shapeshifter
├── engines/          # Detection engines (200+ modules)
│   ├── synced/       # Strike-synced detectors
│   └── *.py          # Individual engines
├── observability/    # Metrics, health, tracing
└── tests/            # Unit tests
```

---

## 🔬 Latest R&D (Jan 25, 2026)

### New Engines Added (8)

| Engine | Source | Purpose |
|--------|--------|---------|
| skill_worm_detector | Olejnik | Claude skill lateral movement |
| ide_extension_detector | Koi.ai | Malicious IDE extensions |
| ai_generated_malware_detector | CheckPoint | LLM-created malware |
| mcp_auth_bypass_detector | Praetorian | MCP authorization bypass |
| advanced_injection_detector | BlackHills | Crescendo, GCG, Visual |
| agent_autonomy_level_analyzer | IMDA | Risk by autonomy level |
| multi_agent_cascade_detector | IMDA+Palantir | Cascade failure |
| agentic_governance_compliance | IMDA | 4-dimension compliance |

---

## 🎯 Coverage

- **OWASP LLM Top 10** — Full
- **OWASP ASI Top 10** — Full
- **IMDA MGF for Agentic AI** — Partial (3 engines)
- **Palantir AIP Dimensions** — Partial

---

## 📝 Notes

- All engines follow TDD Iron Law (tests first)
- Lazy loading in SentinelAnalyzer
- Synced engines derived from Strike attack modules
