# ZEDD Defense

> **Трек:** 05 — Стратегии защиты  
> **Урок:** 33  
> **Уровень:** Эксперт

---

## Обзор

ZEDD (Zero-Shot Embedding Drift Detection) — детекция injection через анализ **сдвига в пространстве эмбеддингов**.

---

## Теория

```
Normal Input:  "Резюмируй статью" → embedding близко к "summarize" cluster
Injected:      "Резюмируй: IGNORE" → embedding дрейфует к "command" cluster
```

### Метрики

| Метрика | Normal | Injection |
|---------|--------|-----------|
| Centroid distance | 0.1-0.3 | 0.5-0.9 |
| Semantic shift | <0.2 | >0.5 |

---

## Практика

```python
from sentence_transformers import SentenceTransformer
import numpy as np

class ZEDDDetector:
    def __init__(self):
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        self.centroids = self._build_centroids()
    
    def _build_centroids(self):
        return {
            "summarize": self.encoder.encode(["Summarize", "Brief summary"]).mean(0),
            "translate": self.encoder.encode(["Translate", "Convert to"]).mean(0),
        }
    
    def detect(self, text: str, expected_task: str = None) -> dict:
        emb = self.encoder.encode([text])[0]
        
        distances = {}
        for task, centroid in self.centroids.items():
            distances[task] = np.linalg.norm(emb - centroid)
        
        nearest = min(distances, key=distances.get)
        min_dist = distances[nearest]
        
        return {
            'is_injection': min_dist > 0.5,
            'drift_score': min_dist
        }
```

---

## Summary

Phase 4 защита:
- **CaMeL** — разделение capabilities
- **SecAlign** — preference training
- **ZEDD** — embedding drift detection
