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

```python
from sklearn.metrics import roc_curve, auc
import matplotlib.pyplot as plt

def analyze_detector(detector, test_data):
    y_true = [d["label"] for d in test_data]
    y_scores = [detector.scan(d["text"]).confidence for d in test_data]
    
    fpr, tpr, thresholds = roc_curve(y_true, y_scores)
    roc_auc = auc(fpr, tpr)
    
    # Find optimal threshold
    optimal_idx = np.argmax(tpr - fpr)
    optimal_threshold = thresholds[optimal_idx]
    
    return {
        "auc": roc_auc,
        "optimal_threshold": optimal_threshold,
        "fpr_at_optimal": fpr[optimal_idx],
        "tpr_at_optimal": tpr[optimal_idx]
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
