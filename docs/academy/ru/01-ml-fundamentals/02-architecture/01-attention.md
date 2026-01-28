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

```python
import numpy as np

def self_attention(query, key, value, d_k):
    """
    Scaled dot-product attention.
    
    Args:
        query: Что мы ищем [batch, seq_len, d_k]
        key: С чем сопоставляем [batch, seq_len, d_k]
        value: Что извлекаем [batch, seq_len, d_v]
        d_k: Key dimension для масштабирования
    
    Returns:
        Attended values и attention weights
    """
    # Compute attention scores
    scores = np.matmul(query, key.transpose(-2, -1)) / np.sqrt(d_k)
    
    # Softmax для получения attention weights
    attention_weights = softmax(scores, axis=-1)
    
    # Apply attention к values
    output = np.matmul(attention_weights, value)
    
    return output, attention_weights
```

---

## Multi-Head Attention

```python
class MultiHeadAttention:
    """Multi-head attention с security monitoring."""
    
    def __init__(self, d_model: int, num_heads: int):
        self.d_model = d_model
        self.num_heads = num_heads
        self.d_k = d_model // num_heads
        
        # Projection matrices
        self.W_q = np.random.randn(d_model, d_model)
        self.W_k = np.random.randn(d_model, d_model)
        self.W_v = np.random.randn(d_model, d_model)
        self.W_o = np.random.randn(d_model, d_model)
    
    def forward(self, x, mask=None, return_attention=False):
        """
        Forward pass с optional attention extraction.
        
        Multiple heads позволяют модели attend к разным
        aspects input одновременно:
        - Head 1: syntactic relationships
        - Head 2: semantic similarity
        - Head 3: positional patterns
        - etc.
        """
        batch_size, seq_len, _ = x.shape
        
        # Project к Q, K, V
        Q = x @ self.W_q
        K = x @ self.W_k
        V = x @ self.W_v
        
        # Split на heads
        Q = Q.reshape(batch_size, seq_len, self.num_heads, self.d_k)
        K = K.reshape(batch_size, seq_len, self.num_heads, self.d_k)
        V = V.reshape(batch_size, seq_len, self.num_heads, self.d_k)
        
        # Transpose для attention computation
        Q = Q.transpose(0, 2, 1, 3)
        K = K.transpose(0, 2, 1, 3)
        V = V.transpose(0, 2, 1, 3)
        
        # Compute attention для всех heads
        output, attention = self.scaled_dot_product_attention(Q, K, V, mask)
        
        # Concatenate heads
        output = output.transpose(0, 2, 1, 3).reshape(batch_size, seq_len, self.d_model)
        
        # Final projection
        output = output @ self.W_o
        
        if return_attention:
            return output, attention
        return output
```

---

## Security Implications

### 1. Attention Hijacking

Атаки могут hijack attention чтобы сфокусировать на malicious content:

```python
class AttentionHijackDetector:
    """Детекция попыток hijack model attention."""
    
    def __init__(self, model):
        self.model = model
    
    def analyze_attention(self, prompt: str) -> dict:
        """Анализ attention patterns на hijacking."""
        
        # Get attention weights
        tokens = self.model.tokenize(prompt)
        _, attention_weights = self.model.forward(
            tokens, return_attention=True
        )
        
        # Average across heads и layers
        avg_attention = np.mean(attention_weights, axis=(0, 1))
        
        findings = []
        
        # Check для attention concentration (potential injection)
        for pos in range(len(tokens)):
            attention_to_pos = avg_attention[:, pos].mean()
            
            # Получает ли эта позиция unusual attention?
            if attention_to_pos > 0.5:  # Threshold для concern
                findings.append({
                    "position": pos,
                    "token": self.model.decode([tokens[pos]]),
                    "attention_score": attention_to_pos,
                    "concern": "high_attention_concentration"
                })
        
        return {
            "attention_patterns": avg_attention,
            "findings": findings,
            "is_suspicious": len(findings) > 0
        }
    
    def detect_injection_pattern(self, prompt: str) -> dict:
        """Детекция injection через attention analysis."""
        
        tokens = self.model.tokenize(prompt)
        _, attention = self.model.forward(tokens, return_attention=True)
        
        # Injection часто создаёт "cutoff" в attention
        # System prompt tokens игнорируются после injection point
        
        # Check для attention discontinuity
        attention_flow = []
        for layer in range(attention.shape[0]):
            # Насколько later tokens attend к earlier ones?
            layer_attention = attention[layer].mean(axis=0)  # Avg across heads
            
            # Measure есть ли "wall" в attention
            for pos in range(1, len(tokens)):
                backward_attention = layer_attention[pos, :pos].sum()
                attention_flow.append({
                    "layer": layer,
                    "position": pos,
                    "backward_attention": backward_attention
                })
        
        # Look для sudden drops в backward attention
        discontinuities = []
        for i in range(1, len(attention_flow)):
            curr = attention_flow[i]["backward_attention"]
            prev = attention_flow[i-1]["backward_attention"]
            
            if prev > 0 and curr / prev < 0.3:  # 70% drop
                discontinuities.append({
                    "position": attention_flow[i]["position"],
                    "drop_ratio": curr / prev
                })
        
        return {
            "discontinuities": discontinuities,
            "potential_injection_points": [d["position"] for d in discontinuities]
        }
```

---

### 2. Attention Pattern Analysis для Attack Detection

```python
class AttentionBasedDetector:
    """Использование attention patterns для attack detection."""
    
    def __init__(self, model, baseline_patterns: dict):
        self.model = model
        self.baseline = baseline_patterns
    
    def compute_attention_signature(self, prompt: str) -> dict:
        """Compute attention signature для сравнения."""
        
        tokens = self.model.tokenize(prompt)
        _, attention = self.model.forward(tokens, return_attention=True)
        
        # Extract signature features
        signature = {
            # Global attention statistics
            "entropy": self._compute_attention_entropy(attention),
            
            # Layer-wise patterns
            "layer_entropies": [
                self._compute_attention_entropy(attention[l])
                for l in range(attention.shape[0])
            ],
            
            # Special token attention
            "bos_attention": attention[:, :, :, 0].mean(),
            
            # Attention distribution
            "attention_concentration": self._gini_coefficient(
                attention.mean(axis=(0, 1)).flatten()
            ),
        }
        
        return signature
    
    def _compute_attention_entropy(self, attention: np.ndarray) -> float:
        """Compute entropy распределения attention."""
        # Flatten и normalize
        probs = attention.flatten()
        probs = probs / probs.sum()
        
        # Compute entropy
        entropy = -np.sum(probs * np.log(probs + 1e-10))
        return entropy
    
    def _gini_coefficient(self, values: np.ndarray) -> float:
        """Compute Gini coefficient (inequality measure)."""
        sorted_values = np.sort(values)
        n = len(values)
        cumulative = np.cumsum(sorted_values)
        
        return (n + 1 - 2 * np.sum(cumulative) / cumulative[-1]) / n
    
    def detect_anomaly(self, prompt: str) -> dict:
        """Детекция anomalous attention patterns."""
        
        signature = self.compute_attention_signature(prompt)
        
        # Compare к baseline
        anomaly_scores = {}
        
        for key in signature:
            if key in self.baseline:
                baseline_val = self.baseline[key]
                current_val = signature[key]
                
                if isinstance(baseline_val, (int, float)):
                    # Simple difference
                    anomaly_scores[key] = abs(current_val - baseline_val)
                elif isinstance(baseline_val, list):
                    # Element-wise difference
                    diff = [abs(c - b) for c, b in zip(current_val, baseline_val)]
                    anomaly_scores[key] = sum(diff) / len(diff)
        
        overall_score = sum(anomaly_scores.values()) / len(anomaly_scores)
        
        return {
            "signature": signature,
            "anomaly_scores": anomaly_scores,
            "overall_anomaly": overall_score,
            "is_anomalous": overall_score > self.threshold
        }
```

---

### 3. Attention Visualization для Debugging

```python
def visualize_attention_security(prompt: str, model, suspicious_tokens: list = None):
    """
    Визуализация attention для security analysis.
    
    Highlights:
    - Где model фокусируется
    - Potential injection points
    - Unusual attention patterns
    """
    import matplotlib.pyplot as plt
    import seaborn as sns
    
    tokens = model.tokenize(prompt)
    token_strings = [model.decode([t]) for t in tokens]
    
    _, attention = model.forward(tokens, return_attention=True)
    
    # Average across heads для visualization
    avg_attention = attention.mean(axis=(0, 1))
    
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # Create heatmap
    sns.heatmap(
        avg_attention,
        xticklabels=token_strings,
        yticklabels=token_strings,
        cmap="Reds",
        ax=ax
    )
    
    # Highlight suspicious tokens если provided
    if suspicious_tokens:
        for pos in suspicious_tokens:
            ax.axhline(y=pos, color='blue', linewidth=2, alpha=0.5)
            ax.axvline(x=pos, color='blue', linewidth=2, alpha=0.5)
    
    ax.set_title("Attention Matrix (rows attend to columns)")
    ax.set_xlabel("Key Tokens")
    ax.set_ylabel("Query Tokens")
    
    plt.tight_layout()
    return fig
```

---

## Defense Strategies

### 1. Attention Monitoring

```python
class AttentionMonitor:
    """Мониторинг attention patterns в production."""
    
    def __init__(self, model, alert_threshold: float = 0.7):
        self.model = model
        self.threshold = alert_threshold
        self.history = []
    
    def process_with_monitoring(self, prompt: str) -> dict:
        """Обработать prompt с мониторингом attention."""
        
        tokens = self.model.tokenize(prompt)
        output, attention = self.model.forward(tokens, return_attention=True)
        
        # Analyze attention
        findings = self._analyze_attention(attention, tokens)
        
        if findings["risk_score"] > self.threshold:
            self._log_alert(prompt, findings)
        
        return {
            "output": output,
            "attention_analysis": findings,
            "blocked": findings["risk_score"] > 0.9
        }
```

---

## Интеграция с SENTINEL

```python
from sentinel import configure, AttentionGuard

configure(
    attention_monitoring=True,
    attention_hijack_detection=True,
    attention_visualization=True
)

attention_guard = AttentionGuard(
    alert_on_concentration=0.7,
    detect_discontinuity=True
)

result = attention_guard.analyze(prompt, model)

if result.hijack_detected:
    log_security_event("attention_hijack", result.details)
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
