# 📁 Lesson 4.1: SENTINEL Codebase

> **Time: 40 minutes** | Expert Module 4

---

## Repository Structure

```
sentinel-community/
├── sentinel-core/        # Rust detection engines
│   ├── src/engines/      # 49 Super-Engines
│   │   ├── injection.rs
│   │   ├── jailbreak.rs
│   │   ├── agentic.rs
│   │   └── tda.rs        # Strange Math™
│   ├── src/bindings.rs   # PyO3 bindings
│   └── Cargo.toml
├── src/brain/            # Python API wrapper
│   ├── pipeline.py       # Engine orchestration
│   └── api.py            # gRPC API
├── shield/               # C gateway
│   ├── src/              # 36K LOC
│   └── tests/            # 103 tests
├── strike/               # Red team (Go)
│   ├── payloads/         # 39K+ attacks
│   └── hydra/            # Multi-head
├── micro-swarm/          # ML presets (F1=0.997)
├── framework/            # Python SDK
│   ├── sentinel/
│   └── integrations/
└── rlm-toolkit/          # LangChain replacement
```

---

## Key Modules

| Module | Language | Purpose |
|--------|----------|---------|
| `sentinel-core.engines` | Rust | 49 detection engines |
| `sentinel-core.bindings` | Rust/PyO3 | Python bindings |
| `brain.pipeline` | Python | Engine orchestration |
| `shield.core` | C | DMZ gateway |
| `strike.hydra` | Go | Attack automation |
| `framework.scan` | Python | Public API |

---

## Development Setup

```bash
git clone https://github.com/DmitrL-dev/AISecurity.git
cd AISecurity/sentinel-community

# Build Rust engines
cd sentinel-core && pip install maturin
maturin develop --release && cd ..

pre-commit install
pytest
```

---

## Next Lesson

→ [4.2: Engine Development](./15-engine-development.md)
