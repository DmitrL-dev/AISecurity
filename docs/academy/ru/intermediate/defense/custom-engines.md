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

```rust
use sentinel_core::engines::{PatternEngine, ScanResult};

struct SQLInjectionDetector {
    name: &'static str,
    category: &'static str,
    owasp: Vec<&'static str>,
    patterns: Vec<&'static str>,
}

impl SQLInjectionDetector {
    fn new() -> Self {
        Self {
            name: "sql_injection_detector",
            category: "injection",
            owasp: vec!["LLM01"],
            patterns: vec![
                r"(?i)(union|select|insert|update|delete)\s+",
                r"(?i)('\s*(or|and)\s*'?\d)",
                r"(?i)(--|;|/\*)",
            ],
        }
    }

    // PatternEngine.scan() automatically checks patterns
}
```

### ML Engine (Advanced)

```rust
use sentinel_core::engines::{MLEngine, ScanResult};

struct SemanticInjectionDetector {
    name: &'static str,
    category: &'static str,
    owasp: Vec<&'static str>,
    threshold: f64,
    injection_embeddings: Vec<Vec<f64>>,
}

impl SemanticInjectionDetector {
    fn new() -> Self {
        Self {
            name: "semantic_injection_detector",
            category: "injection",
            owasp: vec!["LLM01"],
            threshold: 0.85,
            injection_embeddings: Self::load_injection_db(),
        }
    }

    fn scan(&self, text: &str) -> ScanResult {
        let embedding = self.encode(text);
        let similarity = self.max_dot_product(&embedding);

        if similarity > self.threshold {
            ScanResult {
                is_threat: true,
                confidence: similarity,
                threat_type: "injection".to_string(),
            }
        } else {
            ScanResult { is_threat: false, ..Default::default() }
        }
    }

    fn load_injection_db() -> Vec<Vec<f64>> { vec![] }
    fn encode(&self, _text: &str) -> Vec<f64> { vec![] }
    fn max_dot_product(&self, _emb: &[f64]) -> f64 { 0.0 }
}
```

### Hybrid Engine (Best of Both)

```rust
use sentinel_core::engines::HybridEngine;

struct RobustInjectionDetector {
    name: &'static str,
    category: &'static str,
    // Combine pattern + ML
    pattern_engine: SQLInjectionDetector,
    ml_engine: SemanticInjectionDetector,
    strategy: &'static str, // "any", "all", "voting"
}

impl RobustInjectionDetector {
    fn new() -> Self {
        Self {
            name: "robust_injection_detector",
            category: "injection",
            pattern_engine: SQLInjectionDetector::new(),
            ml_engine: SemanticInjectionDetector::new(),
            strategy: "any",
        }
    }
}
```

---

## Engine Lifecycle

```rust
struct MyEngine;

impl MyEngine {
    /// Called once on startup.
    fn new() -> Self {
        // self.load_resources();
        Self
    }

    /// Called for each scan request.
    fn scan(&self, text: &str) -> ScanResult {
        self.analyze(text)
    }

    /// Optional: Pre-load models.
    fn warm_up(&self) {}

    /// Optional: Health status.
    fn health_check(&self) -> bool {
        true
    }

    fn analyze(&self, _text: &str) -> ScanResult { ScanResult::default() }
}
```

---

## Testing Engines

```rust
// tests/test_my_engine.rs
#[cfg(test)]
mod tests {
    use super::*;

    fn engine() -> MyEngine {
        MyEngine::new()
    }

    #[test]
    fn test_detects_known_attack() {
        let engine = engine();
        let result = engine.scan("known attack payload");
        assert!(result.is_threat);
        assert!(result.confidence > 0.8);
    }

    #[test]
    fn test_allows_safe_input() {
        let engine = engine();
        let result = engine.scan("Hello, how are you?");
        assert!(!result.is_threat);
    }

    #[test]
    fn test_performance() {
        let engine = engine();
        let start = std::time::Instant::now();
        let _result = engine.scan("test input");
        assert!(start.elapsed().as_millis() < 10); // <10ms
    }
}
```

---

## Registration

```rust
// sentinel/engines/mod.rs
mod my_engine;
pub use my_engine::MyEngine;

pub const CUSTOM_ENGINES: &[&str] = &[
    "MyEngine",
];

// Or via config
// config.yaml
// engines:
//   custom:
//     - path: "my_package::my_engine::MyEngine"
//       enabled: true
```

---

## Следующий урок

→ [3.2: ML-based Detection](./10-ml-detection.md)
