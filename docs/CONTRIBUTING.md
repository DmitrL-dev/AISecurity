# 🤝 Contributing to SENTINEL

Thank you for your interest in contributing to SENTINEL AI Security Platform!

## Quick Start

1. **Fork** the repository
2. **Clone** your fork: `git clone https://github.com/YOUR_USERNAME/AISecurity.git`
3. **Create branch**: `git checkout -b feature/your-feature`
4. **Make changes** and test
5. **Submit PR**

## Development Setup

```bash
cd AISecurity/sentinel-community
pip install -e ".[dev]"
pytest src/brain/engines/ -v
```

## Code Standards

- Python: Follow PEP 8
- Go: Use `gofmt`
- Tests required for new engines
- Documentation for public APIs

## What to Contribute

| Area | Description |
|------|-------------|
| 🧠 **Engines** | New detection engines in `src/brain/engines/` |
| ⚔️ **Attacks** | Attack patterns in `strike/attacks/` |
| 📚 **Docs** | Documentation improvements |
| 🧪 **Tests** | Test coverage expansion |
| 🐛 **Bugs** | Bug fixes with tests |

## Creating a New Engine

```python
# src/brain/engines/my_engine.py
from .base_engine import BaseEngine, DetectionResult

class MyEngine(BaseEngine):
    @property
    def name(self) -> str:
        return "MyEngine"
    
    def analyze(self, text: str, **kwargs) -> DetectionResult:
        # Your detection logic
        pass
```

## Pull Request Guidelines

1. Clear description of changes
2. Tests pass: `pytest src/brain/engines/ -v`
3. Documentation updated if needed
4. One feature per PR

## Questions?

- 📧 Email: [chg@live.ru](mailto:chg@live.ru)
- 💬 Telegram: [@DmLabincev](https://t.me/DmLabincev)

---

**Thank you for helping make AI more secure! 🛡️**
