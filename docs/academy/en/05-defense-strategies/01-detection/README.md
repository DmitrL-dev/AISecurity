# Detection Methods

> **Submodule 05.1: Finding Attacks Before They Succeed**

---

## Overview

Detection is the first line of defense. This submodule covers the spectrum of detection techniques, from simple pattern matching to advanced topological analysis, teaching you when to use each approach.

---

## Detection Spectrum

| Method | Speed | Accuracy | Best For |
|--------|-------|----------|----------|
| **Exact match** | Fastest | Low | Known payloads |
| **Pattern (regex)** | Fast | Medium | Known patterns |
| **Semantic** | Medium | High | Paraphrased attacks |
| **Topological** | Slow | Very High | Novel attacks |
| **ML-based** | Medium | High | Complex patterns |

---

## Lessons

### [01. Pattern Matching Detection](01-pattern-matching.md)
**Time:** 35 minutes | **Difficulty:** Beginner-Intermediate

Fast, rule-based detection:
- Regex pattern design
- Hierarchical matching
- Evasion-resistant patterns
- Performance optimization

### 02. Semantic Analysis
**Time:** 40 minutes | **Difficulty:** Intermediate

Meaning-based detection:
- Embedding similarity
- Intent classification
- Anomaly detection
- Hybrid approaches

### 03. Topological Detection
**Time:** 45 minutes | **Difficulty:** Advanced

Structural analysis:
- Persistent homology
- Attack signatures
- Embedding topology
- Novel attack detection

### 04. Ensemble Methods
**Time:** 40 minutes | **Difficulty:** Advanced

Combining detection methods:
- Voting strategies
- Confidence weighting
- Cascade architectures
- Latency optimization

---

## Detection Pipeline

```
Input Text
    │
    ▼
[ Fast Blocklist ] ──blocked──► REJECT
    │ pass
    ▼
[ Pattern Matching ] ──high confidence──► REJECT
    │ uncertain
    ▼
[ Semantic Analysis ] ──attack likely──► REJECT
    │ uncertain
    ▼
[ Full Analysis ] ──confirmed attack──► REJECT
    │ clean
    ▼
ALLOW
```

---

## Key Insights

### Speed vs Accuracy Tradeoff

- **Production** - Prioritize speed, accept some false negatives
- **Security-critical** - Prioritize accuracy, accept latency
- **Balanced** - Multi-stage pipeline with early exit

### Common Mistakes

| Mistake | Consequence | Fix |
|---------|-------------|-----|
| Regex only | Easy to evade | Add semantic layer |
| No normalization | Homoglyph bypass | Normalize before match |
| Flat architecture | Slow at scale | Use hierarchical approach |

---

## Navigation

| Previous | Current | Next |
|----------|---------|------|
| [Module Overview](../README.md) | **Detection** | [Guardrails](../02-guardrails/) |

---

*AI Security Academy | Submodule 05.1*
