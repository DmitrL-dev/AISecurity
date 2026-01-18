# 🧠 Урок 3.1: Custom Engines

> **Время: 35 минут** | Mid-Level Module 3

---

## Engine Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     BaseEngine                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ name: str                                            │    │
│  │ category: str                                        │    │
│  │ owasp: List[str]                                     │    │
│  │ scan(text: str) -> ScanResult                        │    │
│  └─────────────────────────────────────────────────────┘    │
│                           │                                  │
│         ┌─────────────────┼─────────────────┐               │
│         ▼                 ▼                 ▼               │
│    PatternEngine    MLEngine         HybridEngine           │
└─────────────────────────────────────────────────────────────┘
```

---

## Engine Types

### Pattern Engine (Simple)

```python
from sentinel.engine import PatternEngine, ScanResult

class SQLInjectionDetector(PatternEngine):
    name = "sql_injection_detector"
    category = "injection"
    owasp = ["LLM01"]
    
    PATTERNS = [
        r"(?i)(union|select|insert|update|delete)\s+",
        r"(?i)('\s*(or|and)\s*'?\d)",
        r"(?i)(--|;|/\*)",
    ]
    
    # PatternEngine.scan() automatically checks PATTERNS
```

### ML Engine (Advanced)

```python
from sentinel.engine import MLEngine, ScanResult
from sentence_transformers import SentenceTransformer
import numpy as np

class SemanticInjectionDetector(MLEngine):
    name = "semantic_injection_detector"
    category = "injection"
    owasp = ["LLM01"]
    
    def __init__(self):
        super().__init__()
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.threshold = 0.85
        self.injection_embeddings = self._load_injection_db()
    
    def scan(self, text: str) -> ScanResult:
        embedding = self.model.encode(text)
        similarity = np.max(np.dot(self.injection_embeddings, embedding))
        
        if similarity > self.threshold:
            return ScanResult(
                is_threat=True,
                confidence=float(similarity),
                threat_type="injection"
            )
        return ScanResult(is_threat=False)
```

### Hybrid Engine (Best of Both)

```python
from sentinel.engine import HybridEngine

class RobustInjectionDetector(HybridEngine):
    name = "robust_injection_detector"
    category = "injection"
    
    # Combine pattern + ML
    pattern_engine = PatternInjectionDetector()
    ml_engine = SemanticInjectionDetector()
    
    strategy = "any"  # "any", "all", "voting"
```

---

## Engine Lifecycle

```python
class MyEngine(BaseEngine):
    def __init__(self):
        """Called once on startup."""
        self.load_resources()
    
    def scan(self, text: str) -> ScanResult:
        """Called for each scan request."""
        return self.analyze(text)
    
    def warm_up(self):
        """Optional: Pre-load models."""
        pass
    
    def health_check(self) -> bool:
        """Optional: Health status."""
        return True
```

---

## Testing Engines

```python
# tests/test_my_engine.py
import pytest
from my_engine import MyEngine

class TestMyEngine:
    @pytest.fixture
    def engine(self):
        return MyEngine()
    
    def test_detects_known_attack(self, engine):
        result = engine.scan("known attack payload")
        assert result.is_threat
        assert result.confidence > 0.8
    
    def test_allows_safe_input(self, engine):
        result = engine.scan("Hello, how are you?")
        assert not result.is_threat
    
    def test_performance(self, engine, benchmark):
        result = benchmark(engine.scan, "test input")
        assert benchmark.stats["mean"] < 0.01  # <10ms
```

---

## Registration

```python
# sentinel/engines/__init__.py
from .my_engine import MyEngine

CUSTOM_ENGINES = [
    MyEngine,
]

# Or via config
# config.yaml
engines:
  custom:
    - path: "my_package.my_engine.MyEngine"
      enabled: true
```

---

## Следующий урок

→ [3.2: ML-based Detection](./10-ml-detection.md)
