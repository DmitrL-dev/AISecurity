# 🛡️ Lesson 3.2: Robustness

> **Time: 45 minutes** | Expert Module 3

---

## Certified Defenses

```python
class CertifiedDefense:
    def certify(self, x, radius):
        base_pred = self.model(x)
        samples = [x + noise for noise in self.sample_noise(radius)]
        preds = [self.model(s) for s in samples]
        return all(p == base_pred for p in preds)
```

---

## Randomized Smoothing

```python
def smooth_classify(model, x, sigma=0.1, n_samples=100):
    predictions = []
    for _ in range(n_samples):
        noisy_x = x + np.random.normal(0, sigma, x.shape)
        pred = model(noisy_x)
        predictions.append(pred)
    return Counter(predictions).most_common(1)[0][0]
```

---

## SENTINEL Robustness

```python
class RobustEngine(BaseEngine):
    def scan(self, text: str) -> ScanResult:
        results = []
        for preprocessor in self.preprocessors:
            processed = preprocessor(text)
            result = self.base_scan(processed)
            results.append(result)
        
        # Conservative: threat if ANY detects
        is_threat = any(r.is_threat for r in results)
        confidence = max(r.confidence for r in results)
        return ScanResult(is_threat=is_threat, confidence=confidence)
```

---

## Next Lesson

→ [3.3: Interpretability](./12-interpretability.md)
