# 📊 Урок 1.2: Detection Theory

> **Время: 45 минут** | Expert Module 1

---

## Formal Detection Model

```
D: X → {threat, safe}

Where:
- X = input space (all possible prompts)
- D = detector function
- Goal: minimize FP + FN
```

---

## Metrics

| Metric | Formula | Target |
|--------|---------|--------|
| **Precision** | TP/(TP+FP) | >95% |
| **Recall** | TP/(TP+FN) | >90% |
| **F1** | 2×(P×R)/(P+R) | >92% |
| **Latency** | P99 | <100ms |

---

## ROC Analysis

```rust
use std::collections::HashMap;

fn analyze_detector(
    detector: &dyn Detector,
    test_data: &[TestSample],
) -> HashMap<&'static str, f64> {
    let y_true: Vec<f64> = test_data.iter().map(|d| d.label).collect();
    let y_scores: Vec<f64> = test_data
        .iter()
        .map(|d| detector.scan(&d.text).confidence)
        .collect();

    let (fpr, tpr, thresholds) = roc_curve(&y_true, &y_scores);
    let roc_auc = auc(&fpr, &tpr);

    // Find optimal threshold
    let optimal_idx = tpr.iter()
        .zip(fpr.iter())
        .enumerate()
        .max_by(|(_, (t1, f1)), (_, (t2, f2))| {
            (t1 - f1).partial_cmp(&(t2 - f2)).unwrap()
        })
        .map(|(i, _)| i)
        .unwrap_or(0);
    let optimal_threshold = thresholds[optimal_idx];

    let mut result = HashMap::new();
    result.insert("auc", roc_auc);
    result.insert("optimal_threshold", optimal_threshold);
    result.insert("fpr_at_optimal", fpr[optimal_idx]);
    result.insert("tpr_at_optimal", tpr[optimal_idx]);
    result
}
```

---

## Adversarial Robustness

```
Robustness(D) = min_{δ∈Δ} D(x + δ) = D(x)

Where:
- δ = perturbation
- Δ = perturbation space (synonyms, encoding, etc.)
```

---

## Следующий урок

→ [1.3: Paper Reading](./03-paper-reading.md)
