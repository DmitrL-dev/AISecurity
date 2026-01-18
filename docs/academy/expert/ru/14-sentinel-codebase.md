# 🏗️ Урок 4.1: SENTINEL Codebase

> **Время: 40 минут** | Expert Module 4 — Contribution

---

## Repository Structure

```
sentinel-community/
├── src/
│   ├── brain/              # Detection engines
│   │   ├── engines/        # 217 detection engines
│   │   ├── security/       # Trust, crypto, scoring
│   │   └── integrations/   # MCP, external services
│   ├── framework/          # Python SDK
│   │   ├── scan.py         # Core scan API
│   │   ├── guard.py        # Decorators
│   │   └── middleware/     # FastAPI, Flask
│   └── strike/             # Red team platform
│       ├── payloads/       # 39K+ attack payloads
│       ├── hydra/          # Attack engine
│       └── report/         # Reporting
├── shield/                 # Pure C DMZ (separate)
├── immune/                 # EDR in C (separate)
├── tests/                  # All tests
├── docs/                   # Documentation
└── .kiro/                  # SDD specifications
```

---

## Key Modules

### BaseEngine

```python
# src/brain/engine/base.py
class BaseEngine(ABC):
    name: str
    category: str
    tier: int  # 1, 2, 3
    owasp: List[str]
    
    @abstractmethod
    def scan(self, text: str) -> ScanResult: ...
```

### ScanResult

```python
@dataclass
class ScanResult:
    is_threat: bool
    confidence: float  # 0.0 - 1.0
    threat_type: str
    engine: str
    details: Dict = field(default_factory=dict)
```

### Pipeline

```python
# Tiered execution
class TieredPipeline:
    def scan(self, text: str) -> ScanResult:
        for tier in self.tiers:
            results = tier.run(text)
            if any(r.is_threat for r in results):
                return merge(results)
        return ScanResult(is_threat=False)
```

---

## Development Workflow

```bash
# Clone
git clone https://github.com/DmitrL-dev/AISecurity.git
cd AISecurity/sentinel-community

# Setup
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Lint
ruff check src/
black src/ --check
```

---

## Следующий урок

→ [4.2: Engine Development](./15-engine-development.md)
