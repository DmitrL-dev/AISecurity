# 🔍 Урок 3.3: Interpretability

> **Время: 40 минут** | Expert Module 3

---

## Explainable Detection

Why was this flagged as a threat?

---

## Attribution Methods

```rust
use std::collections::HashMap;

struct ExplainableDetector {
    model: Box<dyn Model>,
}

impl ExplainableDetector {
    fn explain(&self, text: &str) -> HashMap<String, f64> {
        let tokens = self.tokenize(text);
        let embeddings = self.embed(&tokens);

        let ig = IntegratedGradients::new(&self.model);
        let attributions = ig.attribute(&embeddings, 1);

        // Map back to tokens
        let mut token_importance = HashMap::new();
        for (token, attr) in tokens.iter().zip(attributions.iter()) {
            token_importance.insert(token.clone(), attr.sum() as f64);
        }

        token_importance
    }
}
```

---

## SHAP Values

```rust
fn shap_explain(detector: &Detector, text: &str) -> Vec<f64> {
    /// SHAP explanation for detection.
    let explainer = ShapExplainer::new(
        |input| detector.predict(input),
        &detector.tokenizer,
    );
    let shap_values = explainer.explain(&[text]);

    shap_values
}
```

---

## Human-Readable Explanations

```rust
use sentinel_core::engines::ScanResult;

struct ExplainedResult {
    scan_result: ScanResult,
    explanation: String,
}

impl ExplainedResult {
    fn generate_explanation(&self) -> String {
        if self.scan_result.matched_patterns.contains(&"ignore".to_string()) {
            "Detected instruction override pattern: 'ignore'".to_string()
        } else if self.scan_result.confidence > 0.9 {
            format!(
                "High semantic similarity ({:.0}%) to known attacks",
                self.scan_result.confidence * 100.0
            )
        } else {
            String::new()
        }
    }
}
```

---

## Следующий урок

→ [3.4: Self-Improving Systems](./13-self-improving.md)
