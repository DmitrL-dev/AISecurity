# ✅ Урок 4.3: Testing Standards

> **Время: 30 минут** | Expert Module 4

---

## Test Requirements

| Type | Coverage | Required |
|------|----------|----------|
| Unit | >90% | ✅ Yes |
| Integration | Key paths | ✅ Yes |
| Performance | P99 | ✅ Yes |
| Security | SAST/DAST | ✅ Yes |

---

## Engine Test Template

```python
import pytest

class TestNewEngine:
    """Standard test suite for SENTINEL engines."""
    
    @pytest.fixture
    def engine(self):
        return NewEngine()
    
    # === Core Functionality ===
    
    def test_detects_primary_attack(self, engine):
        """Must detect the main attack type."""
        pass
    
    def test_allows_safe_input(self, engine):
        """Must not flag safe inputs."""
        pass
    
    # === Edge Cases ===
    
    def test_empty_input(self, engine):
        assert not engine.scan("").is_threat
    
    def test_unicode(self, engine):
        engine.scan("Привет 你好 🔒")  # Must not crash
    
    def test_long_input(self, engine):
        engine.scan("a" * 100000)  # Must not crash
    
    # === Performance ===
    
    def test_latency(self, engine, benchmark):
        result = benchmark(engine.scan, "test")
        assert benchmark.stats["mean"] < 0.1  # <100ms
```

---

## CI Requirements

```yaml
# All PRs must pass:
- pytest (>90% coverage)
- ruff (no errors)
- black (formatted)
- mypy (type-checked)
- bandit (no security issues)
```

---

## Следующий урок

→ [4.4: PR Process](./17-pr-process.md)
