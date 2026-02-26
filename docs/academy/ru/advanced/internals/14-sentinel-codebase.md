# 🏗️ Урок 4.1: SENTINEL Codebase

> **Время: 40 минут** | Expert Module 4 — Contribution

---

## Repository Structure

```
sentinel-community/
├── sentinel-core/         # Rust detection engines
│   ├── src/engines/       # 59 Rust detection engines
│   │   ├── injection.rs
│   │   ├── jailbreak.rs
│   │   ├── pii.rs
│   │   └── mod.rs         # Engine registry
│   ├── src/bindings.rs    # PyO3 Python bindings
│   └── Cargo.toml
├── src/
│   ├── brain/             # Python API wrapper (gRPC)
│   │   ├── security/      # Trust, crypto, scoring
│   │   └── integrations/  # MCP, external services
│   ├── framework/         # Python SDK
│   │   ├── scan.py        # Core scan API
│   │   ├── guard.py       # Decorators
│   │   └── middleware/    # FastAPI, Flask
│   └── strike/            # Red team platform (Go)
│       ├── payloads/      # 39K+ attack payloads
│       ├── hydra/         # Attack engine
│       └── report/        # Reporting
├── shield/                # Pure C DMZ (separate)
├── immune/                # EDR in C (separate)
├── micro-swarm/           # ML detection (F1=0.997)
├── tests/                 # All tests
├── docs/                  # Documentation
└── .kiro/                 # SDD specifications
```

---

## Key Modules

### PatternMatcher Trait (Rust)

```rust
// sentinel-core/src/engines/traits.rs
pub trait PatternMatcher {
    fn name(&self) -> &'static str;
    fn scan(&self, text: &str) -> Vec<MatchResult>;
}
```

### AnalysisResult

```rust
#[pyclass]
pub struct AnalysisResult {
    pub detected: bool,
    pub risk_score: f64,      // 0.0 - 1.0
    pub processing_time_us: u64,
    pub matches: Vec<MatchResult>,
    pub categories: Vec<String>,
}
```

### Pipeline

```rust
// All engines run in analyze()
impl SentinelEngine {
    pub fn analyze(&self, text: &str) -> PyResult<AnalysisResult> {
        // Core engines (PatternMatcher trait)
        run_engine!(self.injection);
        run_engine!(self.jailbreak);
        // ... 59 engines total
    }
}
```

---

## Development Workflow

```bash
# Clone
git clone https://github.com/DmitrL-dev/AISecurity.git
cd AISecurity/sentinel-community

# Build Rust engines
cd sentinel-core
pip install maturin
maturin develop --release

# Run tests
cd ..
pytest tests/ -v

# Lint
cargo clippy --manifest-path sentinel-core/Cargo.toml
ruff check src/
```

---

## Следующий урок

→ [4.2: Engine Development](./15-engine-development.md)
