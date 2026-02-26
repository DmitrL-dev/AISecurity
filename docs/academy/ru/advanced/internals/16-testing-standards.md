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

```rust
/// Standard test suite for SENTINEL engines.
#[cfg(test)]
mod tests {
    use super::*;

    fn engine() -> NewEngine {
        NewEngine::new()
    }

    // === Core Functionality ===

    #[test]
    fn test_detects_primary_attack() {
        /// Must detect the main attack type.
        let engine = engine();
        // ...
    }

    #[test]
    fn test_allows_safe_input() {
        /// Must not flag safe inputs.
        let engine = engine();
        // ...
    }

    // === Edge Cases ===

    #[test]
    fn test_empty_input() {
        let engine = engine();
        assert!(!engine.scan("").is_threat);
    }

    #[test]
    fn test_unicode() {
        let engine = engine();
        engine.scan("Привет 你好 🔒"); // Must not crash
    }

    #[test]
    fn test_long_input() {
        let engine = engine();
        let input = "a".repeat(100000);
        engine.scan(&input); // Must not crash
    }

    // === Performance ===

    #[test]
    fn test_latency() {
        let engine = engine();
        let start = std::time::Instant::now();
        let _result = engine.scan("test");
        let elapsed = start.elapsed();
        assert!(elapsed.as_millis() < 100); // <100ms
    }
}
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
