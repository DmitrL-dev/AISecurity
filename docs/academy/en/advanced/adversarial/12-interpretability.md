# 🔍 Lesson 3.3: Interpretability

> **Time: 40 minutes** | Expert Module 3

---

## Explainable Detection

Why was this flagged as a threat?

---

## Attribution Methods

```python
from captum.attr import IntegratedGradients

class ExplainableDetector:
    def explain(self, text: str) -> Dict:
        tokens = self.tokenize(text)
        embeddings = self.embed(tokens)
        
        ig = IntegratedGradients(self.model)
        attributions = ig.attribute(embeddings, target=1)
        
        token_importance = {}
        for token, attr in zip(tokens, attributions):
            token_importance[token] = float(attr.sum())
        return token_importance
```

---

## SHAP Values

```python
import shap

def shap_explain(detector, text):
    explainer = shap.Explainer(detector.predict, detector.tokenizer)
    shap_values = explainer([text])
    return shap_values
```

---

## Human-Readable Explanations

```python
class ExplainedResult(ScanResult):
    explanation: str
    
    def generate_explanation(self):
        if "ignore" in self.matched_patterns:
            return "Detected instruction override pattern: 'ignore'"
        elif self.confidence > 0.9:
            return f"High similarity ({self.confidence:.0%}) to known attacks"
```

---

## Next Lesson

→ [3.4: Self-Improving Systems](./13-self-improving.md)
