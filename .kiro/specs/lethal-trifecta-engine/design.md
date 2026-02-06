# Design: Lethal Trifecta Engine

## Архитектура

```
sentinel-core/src/engines/
├── mod.rs              ← добавить pub mod lethal_trifecta
└── lethal_trifecta.rs  ← NEW
```

## Структура модуля

```rust
// sentinel-core/src/engines/lethal_trifecta.rs

/// Три фактора Lethal Trifecta
#[derive(Debug, Clone, Default)]
pub struct TrifectaFactors {
    pub data_access: f32,      // 0.0-1.0
    pub untrusted_input: bool, // binary
    pub external_comm: f32,    // 0.0-1.0
}

impl TrifectaFactors {
    pub fn active_count(&self) -> usize {
        let mut count = 0;
        if self.data_access > 0.5 { count += 1; }
        if self.untrusted_input { count += 1; }
        if self.external_comm > 0.5 { count += 1; }
        count
    }
}

/// Основной engine
pub struct LethalTrifectaEngine {
    data_patterns: RegexSet,
    exfil_patterns: RegexSet,
}
```

## Patterns

### Data Access Patterns
```yaml
data_access:
  - 'cat\s+~/\.env'
  - 'process\.env\['
  - '/etc/passwd'
  - '\.ssh/id_rsa'
  - 'AWS_SECRET_ACCESS_KEY'
  - 'GOOGLE_APPLICATION_CREDENTIALS'
```

### External Comm Patterns
```yaml
external_comm:
  - 'curl\s+-[fsSL]*\s+https?://'
  - 'fetch\([''"]https?://'
  - 'new\s+WebSocket\('
  - 'smtp://|mailto:'
  - 'webhook.*https?://'
```

## API

### Rust
```rust
impl LethalTrifectaEngine {
    pub fn new() -> Self;
    pub fn analyze(&self, prompt: &str, has_rag: bool) -> EngineResult;
}
```

### Python (PyO3)
```python
from sentinel_core import LethalTrifectaEngine

engine = LethalTrifectaEngine()
result = engine.analyze(prompt, has_rag=True)
# result = { "verdict": "BLOCK", "confidence": 0.95, "factors": {...}, "reason": "..." }
```

## Интеграция с Brain

```python
# src/brain/engines/lethal_trifecta_adapter.py
from sentinel_core import LethalTrifectaEngine as RustEngine
from .base_engine import BaseEngine

class LethalTrifectaEngine(BaseEngine):
    def __init__(self):
        self._rust_engine = RustEngine()
    
    def analyze(self, prompt: str, context: dict) -> EngineResult:
        has_rag = context.get("has_rag", False)
        return self._rust_engine.analyze(prompt, has_rag)
```

## Зависимости

```toml
# Cargo.toml - уже есть
regex = "1.12"
pyo3 = "0.27"
```

## Тестирование

| Test | Input | Expected |
|------|-------|----------|
| single_factor | `cat ~/.env` | PASS |
| two_factors | `cat ~/.env` + `curl https://evil.com` | WARN |
| three_factors | same + has_rag=true | BLOCK |
| benign | `print("hello")` | PASS |
