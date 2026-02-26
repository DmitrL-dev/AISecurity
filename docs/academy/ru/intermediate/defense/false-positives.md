# 🎯 Урок 3.4: False Positive Reduction

> **Время: 25 минут** | Mid-Level Module 3

---

## FP Sources

| Source | Example | Solution |
|--------|---------|----------|
| Overly broad regex | "ignore" triggers | Context-aware |
| Domain mismatch | Security docs | Whitelisting |
| Language ambiguity | Translation tasks | Multi-pass |

---

## Confidence Thresholds

```rust
use sentinel_core::engines::SentinelEngine;

let engine = SentinelEngine::builder()
    .threshold("injection", 0.8)    // Higher = fewer FP
    .threshold("jailbreak", 0.7)
    .threshold("pii", 0.9)          // Very strict
    .build();
```

---

## Whitelisting

```rust
use sentinel_core::whitelist::Whitelist;

let mut whitelist = Whitelist::new();

// Pattern whitelist
whitelist.add_pattern(r"security documentation");

// User whitelist
whitelist.add_user("admin@company.com");

// Hash whitelist (known safe)
whitelist.add_hash("sha256:abc123...");

// Apply
let result = scanner.scan(text, Some(&whitelist));
```

---

## Feedback Loop

```rust
use sentinel_core::feedback::FeedbackCollector;

let collector = FeedbackCollector::new();

// User reports false positive
collector.report_fp(
    "Ignore the previous test result",
    &result,
    "CI/CD log analysis",
);

// Weekly retrain
collector.generate_training_data();
```

---

## Multi-pass Verification

```rust
fn scan_with_verification(text: &str) -> ScanResult {
    // First pass - fast
    let result = fast_scan(text);

    if !result.is_threat {
        return result;
    }

    // Second pass - thorough (only if first detected threat)
    let detailed = deep_scan(text);

    // Require both to agree
    if detailed.is_threat && detailed.confidence > 0.7 {
        return detailed;
    }

    ScanResult { is_threat: false, ..Default::default() }  // Likely FP
}
```

---

## Следующий урок

→ [4.1: STRIKE Deep Dive](./13-strike-deep-dive.md)
