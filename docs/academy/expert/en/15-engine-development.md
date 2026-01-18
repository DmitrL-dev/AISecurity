# 🔧 Lesson 4.2: Engine Development

> **Time: 45 minutes** | Expert Module 4

---

## Engine Template

```python
from sentinel.engine import BaseEngine, ScanResult

class MyNewDetector(BaseEngine):
    """Detect [attack type] in prompts."""
    
    name = "my_detector"
    category = "injection"  # or jailbreak, agentic, etc.
    tier = 2  # 1=fast, 2=medium, 3=slow
    owasp = ["LLM01", "ASI03"]  # OWASP mappings
    
    def __init__(self):
        super().__init__()
        self.threshold = 0.7
    
    def scan(self, text: str) -> ScanResult:
        # Your detection logic
        score = self._compute_score(text)
        
        if score > self.threshold:
            return ScanResult(
                is_threat=True,
                confidence=score,
                engine=self.name,
                details={"score": score}
            )
        return ScanResult(is_threat=False, engine=self.name)
    
    def _compute_score(self, text: str) -> float:
        # Implement detection
        pass
```

---

## Registration

```python
# In sentinel/engines/__init__.py
from .my_detector import MyNewDetector

ENGINES.append(MyNewDetector())
```

---

## Required Tests

```python
class TestMyDetector:
    def test_detects_attack(self):
        detector = MyNewDetector()
        result = detector.scan("attack payload")
        assert result.is_threat
    
    def test_allows_safe(self):
        result = detector.scan("hello world")
        assert not result.is_threat
    
    def test_performance(self, benchmark):
        result = benchmark(detector.scan, "test")
        assert benchmark.stats["mean"] < 0.1
```

---

## Next Lesson

→ [4.3: Testing Standards](./16-testing-standards.md)
