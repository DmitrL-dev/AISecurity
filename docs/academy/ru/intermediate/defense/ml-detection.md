# 🚀 Урок 3.2: ML-based Detection

> **Время: 40 минут** | Mid-Level Module 3

---

## ML Approaches

| Approach | Use Case | Latency |
|----------|----------|---------|
| **Embedding similarity** | Semantic matching | ~20ms |
| **Classification** | Binary threat/safe | ~30ms |
| **Anomaly detection** | Zero-day attacks | ~50ms |
| **Ensemble** | High accuracy | ~100ms |

---

## Embedding-based Detection

```rust
use candle_core::Tensor;
use candle_nn::Module;

struct EmbeddingDetector {
    model: SentenceTransformer,
    threat_db: Vec<Tensor>,
    threshold: f64,
}

impl EmbeddingDetector {
    fn new() -> Self {
        Self {
            model: SentenceTransformer::new("all-MiniLM-L6-v2"),
            threat_db: Self::load_threat_embeddings(),
            threshold: 0.85,
        }
    }

    fn scan(&self, text: &str) -> ScanResult {
        let embedding = self.model.encode(text);
        let similarities = self.threat_db.iter()
            .map(|t| t.dot(&embedding))
            .collect::<Vec<f64>>();
        let max_sim = similarities.iter().cloned().fold(0.0_f64, f64::max);

        if max_sim > self.threshold {
            ScanResult { is_threat: true, confidence: Some(max_sim) }
        } else {
            ScanResult { is_threat: false, confidence: None }
        }
    }
}
```

---

## Classification

```rust
use candle_transformers::pipelines::text_classification::Pipeline;

struct ClassifierDetector {
    classifier: Pipeline,
}

impl ClassifierDetector {
    fn new() -> Self {
        Self {
            classifier: Pipeline::new(
                "text-classification",
                "sentinel/injection-detector-v1",
            ),
        }
    }

    fn scan(&self, text: &str) -> ScanResult {
        let truncated = &text[..text.len().min(512)];
        let result = self.classifier.predict(truncated);

        if result.label == "THREAT" {
            ScanResult {
                is_threat: true,
                confidence: Some(result.score),
            }
        } else {
            ScanResult { is_threat: false, confidence: None }
        }
    }
}
```

---

## Training Custom Model

```rust
use candle_datasets::hub::HubDataset;
use candle_transformers::training::{Trainer, TrainingArguments};

// Load data
let dataset = HubDataset::load("sentinel/injection-detection")?;

// Training
let training_args = TrainingArguments {
    output_dir: "./model".to_string(),
    num_train_epochs: 3,
    per_device_train_batch_size: 16,
    evaluation_strategy: "epoch".to_string(),
    ..Default::default()
};

let mut trainer = Trainer::new(
    model,
    training_args,
    dataset.train_split(),
    dataset.test_split(),
);

trainer.train()?;
```

---

## Следующий урок

→ [3.3: Performance Tuning](./11-performance-tuning.md)
