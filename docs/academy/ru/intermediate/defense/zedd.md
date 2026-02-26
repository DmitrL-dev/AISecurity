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

```rust
use candle_core::Tensor;
use std::collections::HashMap;

struct ZEDDDetector {
    encoder: SentenceTransformer,
    centroids: HashMap<String, Tensor>,
}

impl ZEDDDetector {
    fn new() -> Self {
        let encoder = SentenceTransformer::new("all-MiniLM-L6-v2");
        let centroids = Self::build_centroids(&encoder);
        Self { encoder, centroids }
    }

    fn build_centroids(encoder: &SentenceTransformer) -> HashMap<String, Tensor> {
        HashMap::from([
            ("summarize".into(), encoder.encode_batch(&["Summarize", "Brief summary"]).mean(0)),
            ("translate".into(), encoder.encode_batch(&["Translate", "Convert to"]).mean(0)),
        ])
    }

    fn detect(&self, text: &str, _expected_task: Option<&str>) -> HashMap<String, serde_json::Value> {
        let emb = self.encoder.encode(text);

        let mut distances = HashMap::new();
        for (task, centroid) in &self.centroids {
            distances.insert(task.clone(), (emb.sub(centroid)).norm().to_scalar::<f64>());
        }

        let (nearest, &min_dist) = distances.iter()
            .min_by(|a, b| a.1.partial_cmp(b.1).unwrap())
            .unwrap();

        HashMap::from([
            ("is_injection".into(), serde_json::json!(min_dist > 0.5)),
            ("drift_score".into(), serde_json::json!(min_dist)),
        ])
    }
}
```

---

## Summary

Phase 4 защита:
- **CaMeL** — разделение capabilities
- **SecAlign** — preference training
- **ZEDD** — embedding drift detection
