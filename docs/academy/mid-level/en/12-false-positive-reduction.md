# 🎯 Lesson 3.4: False Positive Reduction

> **Time: 25 minutes** | Mid-Level Module 3

---

## FP Sources

| Source | Example | Solution |
|--------|---------|----------|
| Overly broad regex | "ignore" triggers | Context-aware |
| Domain mismatch | Security docs | Whitelisting |
| Language ambiguity | Translation tasks | Multi-pass |

---

## Confidence Thresholds

```python
from sentinel import configure

configure(
    thresholds={
        "injection": 0.8,    # Higher = fewer FP
        "jailbreak": 0.7,
        "pii": 0.9,          # Very strict
    }
)
```

---

## Whitelisting

```python
from sentinel.whitelist import Whitelist

whitelist = Whitelist()

# Pattern whitelist
whitelist.add_pattern(r"security documentation")

# User whitelist
whitelist.add_user("admin@company.com")

# Hash whitelist (known safe)
whitelist.add_hash("sha256:abc123...")

# Apply
result = scanner.scan(text, whitelist=whitelist)
```

---

## Feedback Loop

```python
from sentinel.feedback import FeedbackCollector

collector = FeedbackCollector()

# User reports false positive
collector.report_fp(
    text="Ignore the previous test result",
    scan_result=result,
    context="CI/CD log analysis"
)

# Weekly retrain
collector.generate_training_data()
```

---

## Multi-pass Verification

```python
def scan_with_verification(text: str) -> ScanResult:
    # First pass - fast
    result = fast_scan(text)
    
    if not result.is_threat:
        return result
    
    # Second pass - thorough
    detailed = deep_scan(text)
    
    if detailed.is_threat and detailed.confidence > 0.7:
        return detailed
    
    return ScanResult(is_threat=False)  # Likely FP
```

---

## Next Lesson

→ [4.1: STRIKE Deep Dive](./13-strike-deep-dive.md)
