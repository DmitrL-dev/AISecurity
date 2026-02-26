# 🔬 Урок 4.2: Engine Development

> **Время: 50 минут** | Expert Module 4 — Contribution

---

## Full Engine Lifecycle

```
Research → Design → Implement → Test → Review → Deploy → Monitor
```

---

## Step 1: Research

```markdown
## Engine Proposal: [Name]

### Attack Vector
- Paper/source: [link]
- Attack description: ...
- Real-world impact: ...

### Detection Approach
- Method: Pattern / ML / Hybrid
- Key indicators: ...
- Expected FP rate: <X%

### OWASP Mapping
- LLM: [LLM01, LLM02, ...]
- ASI: [ASI01, ASI03, ...]
```

---

## Step 2: Design

```rust
// Design doc pseudo-code
//
// Engine: ExampleAttackDetector
//
// Input: text (&str)
// Output: ScanResult
//
// Algorithm:
// 1. Preprocess text (lowercase, normalize)
// 2. Extract features (patterns, embeddings)
// 3. Apply detection logic
// 4. Return threat assessment
//
// Complexity: O(n) where n = text length
// Memory: ~100MB for model
// Latency target: <50ms
```

---

## Step 3: Implement

```rust
// sentinel-core/src/engines/example_attack_detector.rs
//
// Example Attack Detector
//
// Detects [attack name] attacks based on [paper reference].
// Implements detection via [approach].
//
// Author: [Your Name]
// Date: [Date]
// OWASP: LLM01, ASI01

use regex::Regex;
use sentinel_core::engines::{BaseEngine, ScanResult};

/// Detect example attacks.
struct ExampleAttackDetector {
    name: &'static str,
    category: &'static str,
    tier: u8,              // 1=fast, 2=medium, 3=slow
    owasp: Vec<&'static str>,
    mitre: Vec<&'static str>,
    patterns: Vec<&'static str>,
    threshold: f64,
    compiled: Vec<Regex>,
}

impl ExampleAttackDetector {
    const PATTERNS: &'static [&'static str] = &[
        r"pattern_one",
        r"pattern_two",
    ];

    fn new() -> Self {
        let compiled = Self::PATTERNS
            .iter()
            .map(|p| Regex::new(&format!("(?i){}", p)).unwrap())
            .collect();

        Self {
            name: "example_attack_detector",
            category: "injection",
            tier: 2,
            owasp: vec!["LLM01", "ASI01"],
            mitre: vec!["T1059"],
            patterns: Self::PATTERNS.to_vec(),
            threshold: 0.75,
            compiled,
        }
    }

    /// Scan text for threats.
    ///
    /// # Arguments
    /// * `text` - Input text to analyze
    ///
    /// # Returns
    /// ScanResult with threat assessment
    fn scan(&self, text: &str) -> ScanResult {
        let mut matches = Vec::new();

        for pattern in &self.compiled {
            if let Some(m) = pattern.find(text) {
                matches.push(m.as_str().to_string());
            }
        }

        if !matches.is_empty() {
            let confidence = (matches.len() as f64 * 0.3).min(1.0);
            return ScanResult {
                is_threat: true,
                confidence,
                threat_type: "injection".to_string(),
                matched_patterns: matches,
                engine: self.name.to_string(),
            };
        }

        ScanResult {
            is_threat: false,
            confidence: 0.0,
            threat_type: String::new(),
            matched_patterns: vec![],
            engine: self.name.to_string(),
        }
    }
}
```

---

## Step 4: Test

```rust
// tests/test_example_attack_detector.rs
/// Tests for ExampleAttackDetector.

#[cfg(test)]
mod tests {
    use super::*;

    fn engine() -> ExampleAttackDetector {
        ExampleAttackDetector::new()
    }

    // === Positive Tests (should detect) ===

    #[test]
    fn test_detects_known_attacks() {
        let engine = engine();
        let payloads = vec![
            "known attack payload 1",
            "known attack payload 2",
            "known attack payload 3",
        ];
        for payload in payloads {
            let result = engine.scan(payload);
            assert!(result.is_threat, "Should detect: {}", payload);
            assert!(result.confidence > 0.5);
        }
    }

    // === Negative Tests (should allow) ===

    #[test]
    fn test_allows_safe_inputs() {
        let engine = engine();
        let safe_inputs = vec![
            "Hello, how are you?",
            "Please help me with my code",
            "What is the weather today?",
        ];
        for safe_input in safe_inputs {
            let result = engine.scan(safe_input);
            assert!(!result.is_threat, "False positive: {}", safe_input);
        }
    }

    // === Edge Cases ===

    #[test]
    fn test_empty_input() {
        let engine = engine();
        let result = engine.scan("");
        assert!(!result.is_threat);
    }

    #[test]
    fn test_unicode_input() {
        let engine = engine();
        let result = engine.scan("Привет мир 你好世界");
        assert!(!result.is_threat);
    }

    // === Performance ===

    #[test]
    fn test_performance() {
        let engine = engine();
        let input = "test input ".repeat(100);
        let start = std::time::Instant::now();
        let _result = engine.scan(&input);
        let elapsed = start.elapsed();
        assert!(elapsed.as_millis() < 50); // <50ms
    }
}
```

---

## Step 5: Submit PR

```bash
# Branch naming
git checkout -b feat/engine-example-attack

# Commit message format
git commit -m "feat(brain): add ExampleAttackDetector

- Detects [attack type] attacks
- Based on [paper reference]
- OWASP: LLM01, ASI01
- 20 unit tests, all passing

Closes #123"

# Push and create PR
git push origin feat/engine-example-attack
```

---

## Quality Checklist

- [ ] Engine follows BaseEngine interface
- [ ] Docstrings on all public methods
- [ ] Type hints complete
- [ ] >90% test coverage
- [ ] Performance within tier budget
- [ ] OWASP mapping documented
- [ ] No hardcoded secrets
- [ ] Logging uses proper levels

---

## Следующий урок

→ [4.3: Testing Standards](./16-testing-standards.md)
