# Attention Mechanisms и безопасность

> **Урок:** 01.2.1 - Attention Mechanisms  
> **Время:** 45 минут  
> **Пререквизиты:** Neural Network basics

---

## Цели обучения

К концу этого урока вы сможете:

1. Понимать как attention работает в transformers
2. Идентифицировать security implications attention patterns
3. Анализировать attention для attack detection
4. Реализовывать attention-based defenses

---

## Что такое Attention?

Attention позволяет моделям focus на relevant input parts при генерации каждого output token:

```
Input: "The capital of France is"
       [The] [capital] [of] [France] [is]
         ↓      ↓       ↓      ↓      ↓
Attention weights: 0.05  0.15   0.05  0.60   0.15

Output: "Paris" (сильно influenced by "France")
```

---

## Self-Attention Mechanism

```rust
use ndarray::Array;

fn self_attention(
    query: &Array<f64, ndarray::Ix3>,
    key: &Array<f64, ndarray::Ix3>,
    value: &Array<f64, ndarray::Ix3>,
    d_k: f64,
) -> (Array<f64, ndarray::Ix3>, Array<f64, ndarray::Ix3>) {
    /// Scaled dot-product attention.
    ///
    /// Args:
    ///     query: Что мы ищем [batch, seq_len, d_k]
    ///     key: С чем сопоставляем [batch, seq_len, d_k]
    ///     value: Что извлекаем [batch, seq_len, d_v]
    ///     d_k: Key dimension для масштабирования
    ///
    /// Returns:
    ///     Attended values и attention weights

    // Compute attention scores
    let scores = query.dot(&key.t()) / d_k.sqrt();

    // Softmax для получения attention weights
    let attention_weights = softmax(&scores, -1);

    // Apply attention к values
    let output = attention_weights.dot(value);

    (output, attention_weights)
}
```

---

## Multi-Head Attention

```rust
use ndarray::Array;
use rand::Rng;

struct MultiHeadAttention {
    /// Multi-head attention с security monitoring.
    d_model: usize,
    num_heads: usize,
    d_k: usize,
    w_q: Array<f64, ndarray::Ix2>,
    w_k: Array<f64, ndarray::Ix2>,
    w_v: Array<f64, ndarray::Ix2>,
    w_o: Array<f64, ndarray::Ix2>,
}

impl MultiHeadAttention {
    fn new(d_model: usize, num_heads: usize) -> Self {
        let d_k = d_model / num_heads;
        let mut rng = rand::thread_rng();
        Self {
            d_model,
            num_heads,
            d_k,
            // Projection matrices
            w_q: Array::from_shape_fn((d_model, d_model), |_| rng.gen::<f64>()),
            w_k: Array::from_shape_fn((d_model, d_model), |_| rng.gen::<f64>()),
            w_v: Array::from_shape_fn((d_model, d_model), |_| rng.gen::<f64>()),
            w_o: Array::from_shape_fn((d_model, d_model), |_| rng.gen::<f64>()),
        }
    }

    fn forward(
        &self,
        x: &Array<f64, ndarray::Ix3>,
        mask: Option<&Array<f64, ndarray::Ix2>>,
        return_attention: bool,
    ) -> (Array<f64, ndarray::Ix3>, Option<Array<f64, ndarray::Ix4>>) {
        /// Forward pass с optional attention extraction.
        ///
        /// Multiple heads позволяют модели attend к разным
        /// aspects input одновременно:
        /// - Head 1: syntactic relationships
        /// - Head 2: semantic similarity
        /// - Head 3: positional patterns
        /// - etc.
        let (batch_size, seq_len, _) = x.dim();

        // Project к Q, K, V
        let q = x.dot(&self.w_q);
        let k = x.dot(&self.w_k);
        let v = x.dot(&self.w_v);

        // Split на heads
        let q = q.into_shape((batch_size, seq_len, self.num_heads, self.d_k)).unwrap();
        let k = k.into_shape((batch_size, seq_len, self.num_heads, self.d_k)).unwrap();
        let v = v.into_shape((batch_size, seq_len, self.num_heads, self.d_k)).unwrap();

        // Transpose для attention computation
        let q = q.permuted_axes([0, 2, 1, 3]);
        let k = k.permuted_axes([0, 2, 1, 3]);
        let v = v.permuted_axes([0, 2, 1, 3]);

        // Compute attention для всех heads
        let (output, attention) = self.scaled_dot_product_attention(&q, &k, &v, mask);

        // Concatenate heads
        let output = output.permuted_axes([0, 2, 1, 3])
            .into_shape((batch_size, seq_len, self.d_model)).unwrap();

        // Final projection
        let output = output.dot(&self.w_o);

        if return_attention {
            (output, Some(attention))
        } else {
            (output, None)
        }
    }
}
```

---

## Security Implications

### 1. Attention Hijacking

Атаки могут hijack attention чтобы сфокусировать на malicious content:

```rust
struct AttentionHijackDetector {
    /// Детекция попыток hijack model attention.
    model: Box<dyn AttentionModel>,
}

impl AttentionHijackDetector {
    fn new(model: Box<dyn AttentionModel>) -> Self {
        Self { model }
    }

    fn analyze_attention(&self, prompt: &str) -> serde_json::Value {
        /// Анализ attention patterns на hijacking.

        // Get attention weights
        let tokens = self.model.tokenize(prompt);
        let (_, attention_weights) = self.model.forward(&tokens, true);

        // Average across heads и layers
        let avg_attention = attention_weights.mean_axis(vec![0, 1]);

        let mut findings = Vec::new();

        // Check для attention concentration (potential injection)
        for pos in 0..tokens.len() {
            let attention_to_pos = avg_attention.column(pos).mean();

            // Получает ли эта позиция unusual attention?
            if attention_to_pos > 0.5 {  // Threshold для concern
                findings.push(serde_json::json!({
                    "position": pos,
                    "token": self.model.decode(&[tokens[pos]]),
                    "attention_score": attention_to_pos,
                    "concern": "high_attention_concentration"
                }));
            }
        }

        serde_json::json!({
            "attention_patterns": avg_attention,
            "findings": findings,
            "is_suspicious": !findings.is_empty()
        })
    }

    fn detect_injection_pattern(&self, prompt: &str) -> serde_json::Value {
        /// Детекция injection через attention analysis.

        let tokens = self.model.tokenize(prompt);
        let (_, attention) = self.model.forward(&tokens, true);

        // Injection часто создаёт "cutoff" в attention
        // System prompt tokens игнорируются после injection point

        // Check для attention discontinuity
        let mut attention_flow = Vec::new();
        let num_layers = attention.shape()[0];
        for layer in 0..num_layers {
            // Насколько later tokens attend к earlier ones?
            let layer_attention = attention.slice(layer).mean_axis(0); // Avg across heads

            // Measure есть ли "wall" в attention
            for pos in 1..tokens.len() {
                let backward_attention: f64 = layer_attention.row(pos).slice(0..pos).sum();
                attention_flow.push(serde_json::json!({
                    "layer": layer,
                    "position": pos,
                    "backward_attention": backward_attention
                }));
            }
        }

        // Look для sudden drops в backward attention
        let mut discontinuities = Vec::new();
        for i in 1..attention_flow.len() {
            let curr = attention_flow[i]["backward_attention"].as_f64().unwrap();
            let prev = attention_flow[i - 1]["backward_attention"].as_f64().unwrap();

            if prev > 0.0 && curr / prev < 0.3 {  // 70% drop
                discontinuities.push(serde_json::json!({
                    "position": attention_flow[i]["position"],
                    "drop_ratio": curr / prev
                }));
            }
        }

        serde_json::json!({
            "discontinuities": &discontinuities,
            "potential_injection_points": discontinuities.iter()
                .map(|d| d["position"].clone())
                .collect::<Vec<_>>()
        })
    }
}
```

---

### 2. Attention Pattern Analysis для Attack Detection

```rust
use ndarray::Array;

struct AttentionBasedDetector {
    /// Использование attention patterns для attack detection.
    model: Box<dyn AttentionModel>,
    baseline: HashMap<String, serde_json::Value>,
    threshold: f64,
}

impl AttentionBasedDetector {
    fn new(model: Box<dyn AttentionModel>, baseline_patterns: HashMap<String, serde_json::Value>) -> Self {
        Self { model, baseline: baseline_patterns, threshold: 0.7 }
    }

    fn compute_attention_signature(&self, prompt: &str) -> HashMap<String, serde_json::Value> {
        /// Compute attention signature для сравнения.
        let tokens = self.model.tokenize(prompt);
        let (_, attention) = self.model.forward(&tokens, true);

        // Extract signature features
        let mut signature = HashMap::new();

        // Global attention statistics
        signature.insert("entropy".into(), serde_json::json!(self.compute_attention_entropy(&attention)));

        // Layer-wise patterns
        let num_layers = attention.shape()[0];
        let layer_entropies: Vec<f64> = (0..num_layers)
            .map(|l| self.compute_attention_entropy(&attention.slice(l)))
            .collect();
        signature.insert("layer_entropies".into(), serde_json::json!(layer_entropies));

        // Special token attention
        let bos_attention = attention.slice_axis(3, 0).mean();
        signature.insert("bos_attention".into(), serde_json::json!(bos_attention));

        // Attention distribution
        let flat = attention.mean_axis(vec![0, 1]).into_raw_vec();
        signature.insert("attention_concentration".into(), serde_json::json!(self.gini_coefficient(&flat)));

        signature
    }

    fn compute_attention_entropy(&self, attention: &Array<f64, ndarray::IxDyn>) -> f64 {
        /// Compute entropy распределения attention.
        // Flatten и normalize
        let probs: Vec<f64> = attention.iter().copied().collect();
        let sum: f64 = probs.iter().sum();
        let probs: Vec<f64> = probs.iter().map(|&p| p / sum).collect();

        // Compute entropy
        -probs.iter().map(|&p| p * (p + 1e-10).ln()).sum::<f64>()
    }

    fn gini_coefficient(&self, values: &[f64]) -> f64 {
        /// Compute Gini coefficient (inequality measure).
        let mut sorted = values.to_vec();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let n = sorted.len() as f64;
        let cumulative: Vec<f64> = sorted.iter().scan(0.0, |acc, &x| { *acc += x; Some(*acc) }).collect();
        let cum_sum: f64 = cumulative.iter().sum();

        (n + 1.0 - 2.0 * cum_sum / cumulative.last().unwrap_or(&1.0)) / n
    }

    fn detect_anomaly(&self, prompt: &str) -> serde_json::Value {
        /// Детекция anomalous attention patterns.
        let signature = self.compute_attention_signature(prompt);

        // Compare к baseline
        let mut anomaly_scores = HashMap::new();

        for (key, current_val) in &signature {
            if let Some(baseline_val) = self.baseline.get(key) {
                if let (Some(c), Some(b)) = (current_val.as_f64(), baseline_val.as_f64()) {
                    // Simple difference
                    anomaly_scores.insert(key.clone(), (c - b).abs());
                } else if let (Some(c_arr), Some(b_arr)) = (current_val.as_array(), baseline_val.as_array()) {
                    // Element-wise difference
                    let diff: f64 = c_arr.iter().zip(b_arr.iter())
                        .map(|(c, b)| (c.as_f64().unwrap_or(0.0) - b.as_f64().unwrap_or(0.0)).abs())
                        .sum::<f64>() / c_arr.len() as f64;
                    anomaly_scores.insert(key.clone(), diff);
                }
            }
        }

        let overall_score: f64 = anomaly_scores.values().sum::<f64>() / anomaly_scores.len() as f64;

        serde_json::json!({
            "signature": signature,
            "anomaly_scores": anomaly_scores,
            "overall_anomaly": overall_score,
            "is_anomalous": overall_score > self.threshold
        })
    }
}
```

---

### 3. Attention Visualization для Debugging

```rust
fn visualize_attention_security(
    prompt: &str,
    model: &dyn AttentionModel,
    suspicious_tokens: Option<&[usize]>,
) -> Figure {
    /// Визуализация attention для security analysis.
    ///
    /// Highlights:
    /// - Где model фокусируется
    /// - Potential injection points
    /// - Unusual attention patterns
    use plotters::prelude::*;

    let tokens = model.tokenize(prompt);
    let token_strings: Vec<String> = tokens.iter()
        .map(|t| model.decode(&[*t]))
        .collect();

    let (_, attention) = model.forward(&tokens, true);

    // Average across heads для visualization
    let avg_attention = attention.mean_axis(vec![0, 1]);

    let root = BitMapBackend::new("attention.png", (1200, 1000)).into_drawing_area();
    root.fill(&WHITE).unwrap();

    // Create heatmap
    draw_heatmap(&root, &avg_attention, &token_strings, &token_strings, "Reds");

    // Highlight suspicious tokens если provided
    if let Some(positions) = suspicious_tokens {
        for &pos in positions {
            draw_highlight_line(&root, pos, &BLUE, 2.0, 0.5);
        }
    }

    root.titled("Attention Matrix (rows attend to columns)").unwrap();

    root.into_figure()
}
```

---

## Defense Strategies

### 1. Attention Monitoring

```rust
struct AttentionMonitor {
    /// Мониторинг attention patterns в production.
    model: Box<dyn AttentionModel>,
    threshold: f64,
    history: Vec<serde_json::Value>,
}

impl AttentionMonitor {
    fn new(model: Box<dyn AttentionModel>, alert_threshold: f64) -> Self {
        Self { model, threshold: alert_threshold, history: Vec::new() }
    }

    fn process_with_monitoring(&mut self, prompt: &str) -> serde_json::Value {
        /// Обработать prompt с мониторингом attention.
        let tokens = self.model.tokenize(prompt);
        let (output, attention) = self.model.forward(&tokens, true);

        // Analyze attention
        let findings = self.analyze_attention(&attention, &tokens);

        if findings["risk_score"].as_f64().unwrap_or(0.0) > self.threshold {
            self.log_alert(prompt, &findings);
        }

        serde_json::json!({
            "output": output,
            "attention_analysis": findings,
            "blocked": findings["risk_score"].as_f64().unwrap_or(0.0) > 0.9
        })
    }
}
```

---

## Интеграция с SENTINEL

```rust
use sentinel_core::engines::{configure, AttentionGuard};

configure(serde_json::json!({
    "attention_monitoring": true,
    "attention_hijack_detection": true,
    "attention_visualization": true,
}));

let attention_guard = AttentionGuard::new(serde_json::json!({
    "alert_on_concentration": 0.7,
    "detect_discontinuity": true,
}));

let result = attention_guard.analyze(prompt, &model);

if result.hijack_detected {
    log_security_event("attention_hijack", &result.details);
}
```

---

## Ключевые выводы

1. **Attention reveals intent** — Где model фокусируется важно
2. **Hijacking detectable** — Unusual patterns видны
3. **Monitor в production** — Attention analysis помогает detection
4. **Visualize для debugging** — Heatmaps показывают attack patterns
5. **Combine с другими signals** — Часть defense-in-depth

---

*AI Security Academy | Урок 01.2.1*
