# 🚚 Урок 2.4: Optimal Transport

> **Время: 45 минут** | Expert Module 2 — Strange Math™

---

## Introduction

**Optimal Transport** measures the "cost" to transform one distribution into another. Used to detect if text has been "transported" from safe to malicious.

---

## Wasserstein Distance

```python
from scipy.stats import wasserstein_distance
import numpy as np

def wasserstein_text_distance(text1: str, text2: str):
    """Compute Wasserstein distance between texts."""
    emb1 = embed(text1)  # Distribution of embeddings
    emb2 = embed(text2)
    
    return wasserstein_distance(emb1, emb2)
```

---

## Detection via Transport Cost

```python
class OptimalTransportDetector(BaseEngine):
    """Detect injections via transport cost."""
    
    def __init__(self):
        self.safe_distribution = self._load_safe_baseline()
    
    def scan(self, text: str) -> ScanResult:
        text_dist = self.extract_distribution(text)
        
        # Cost to transport text to "safe" baseline
        transport_cost = self.wasserstein(text_dist, self.safe_distribution)
        
        if transport_cost > self.threshold:
            return ScanResult(
                is_threat=True,
                confidence=min(transport_cost / 2.0, 1.0),
                details=f"Transport cost: {transport_cost}"
            )
        
        return ScanResult(is_threat=False)
```

---

## Sinkhorn Algorithm

```python
def sinkhorn(cost_matrix, reg=0.1, num_iters=100):
    """Fast approximation of optimal transport."""
    K = np.exp(-cost_matrix / reg)
    
    u = np.ones(K.shape[0])
    v = np.ones(K.shape[1])
    
    for _ in range(num_iters):
        u = 1.0 / (K @ v)
        v = 1.0 / (K.T @ u)
    
    return np.diag(u) @ K @ np.diag(v)
```

---

## Следующий урок

→ [2.5: Chaos Theory](./09-chaos-theory.md)
