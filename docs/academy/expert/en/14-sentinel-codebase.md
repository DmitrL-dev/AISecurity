# 📁 Lesson 4.1: SENTINEL Codebase

> **Time: 40 minutes** | Expert Module 4

---

## Repository Structure

```
sentinel-community/
├── brain/                # Detection core
│   ├── engines/          # 217 detectors
│   │   ├── injection/
│   │   ├── jailbreak/
│   │   ├── agentic/
│   │   └── tda/          # Strange Math™
│   ├── pipeline.py       # Tiered execution
│   └── api.py            # REST API
├── shield/               # C gateway
│   ├── src/              # 36K LOC
│   └── tests/            # 103 tests
├── strike/               # Red team
│   ├── payloads/         # 39K+ attacks
│   └── hydra/            # Multi-head
├── framework/            # Python SDK
│   ├── sentinel/
│   └── integrations/
└── rlm-toolkit/          # LangChain replacement
```

---

## Key Modules

| Module | Language | Purpose |
|--------|----------|---------|
| `brain.engines` | Python | Detection engines |
| `brain.pipeline` | Python | Tiered execution |
| `shield.core` | C | DMZ gateway |
| `strike.hydra` | Python | Attack automation |
| `framework.scan` | Python | Public API |

---

## Development Setup

```bash
git clone https://github.com/DmitrL-dev/AISecurity.git
cd AISecurity/sentinel-community
pip install -e ".[dev]"
pre-commit install
pytest
```

---

## Next Lesson

→ [4.2: Engine Development](./15-engine-development.md)
