# 🤖 Lesson 3.2: ML-based Detection

> **Time: 40 minutes** | Mid-Level Module 3

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

```python
from sentence_transformers import SentenceTransformer
import numpy as np

class EmbeddingDetector(MLEngine):
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.threat_db = self._load_threat_embeddings()
        self.threshold = 0.85
    
    def scan(self, text: str) -> ScanResult:
        embedding = self.model.encode(text)
        similarities = np.dot(self.threat_db, embedding)
        max_sim = np.max(similarities)
        
        if max_sim > self.threshold:
            return ScanResult(is_threat=True, confidence=float(max_sim))
        return ScanResult(is_threat=False)
```

---

## Classification

```python
from transformers import pipeline

class ClassifierDetector(MLEngine):
    def __init__(self):
        self.classifier = pipeline(
            "text-classification",
            model="sentinel/injection-detector-v1"
        )
    
    def scan(self, text: str) -> ScanResult:
        result = self.classifier(text[:512])[0]
        
        if result["label"] == "THREAT":
            return ScanResult(
                is_threat=True,
                confidence=result["score"]
            )
        return ScanResult(is_threat=False)
```

---

## Training Custom Model

```python
from datasets import load_dataset
from transformers import Trainer, TrainingArguments

dataset = load_dataset("sentinel/injection-detection")

training_args = TrainingArguments(
    output_dir="./model",
    num_train_epochs=3,
    per_device_train_batch_size=16,
    evaluation_strategy="epoch"
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=dataset["train"],
    eval_dataset=dataset["test"]
)

trainer.train()
```

---

## Next Lesson

→ [3.3: Performance Tuning](./11-performance-tuning.md)
