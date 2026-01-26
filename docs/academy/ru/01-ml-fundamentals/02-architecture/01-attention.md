# Attention Mechanisms и Security

> **Урок:** 01.2.1 - Attention Mechanisms  
> **Время:** 45 минут  
> **Prerequisites:** Основы нейронных сетей

---

## Цели обучения

После завершения этого урока вы сможете:

1. Понять как attention работает в transformers
2. Идентифицировать security implications attention patterns
3. Анализировать attention для attack detection
4. Реализовать attention-based defenses

---

## Что такое Attention?

Attention позволяет моделям фокусироваться на релевантных частях input при генерации каждого output токена:

```
Input: "The capital of France is"
       [The] [capital] [of] [France] [is]
         ↓      ↓       ↓      ↓      ↓
Attention weights: 0.05  0.15   0.05  0.60   0.15

Output: "Paris" (heavily influenced by "France")
```

---

## Self-Attention Mechanism

```python
import numpy as np

def self_attention(query, key, value, d_k):
    """
    Scaled dot-product attention.
    
    Args:
        query: What we're looking for [batch, seq_len, d_k]
        key: What we match against [batch, seq_len, d_k]
        value: What we retrieve [batch, seq_len, d_v]
        d_k: Key dimension for scaling
    
    Returns:
        Attended values and attention weights
    """
    # Compute attention scores
    scores = np.matmul(query, key.transpose(-2, -1)) / np.sqrt(d_k)
    
    # Softmax to get attention weights
    attention_weights = softmax(scores, axis=-1)
    
    # Apply attention to values
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
        
        Multiple heads позволяют модели attend to different
        aspects of the input simultaneously:
        - Head 1: syntactic relationships
        - Head 2: semantic similarity
        - Head 3: positional patterns
        - etc.
        """
        batch_size, seq_len, _ = x.shape
        
        # Project to Q, K, V
        Q = x @ self.W_q
        K = x @ self.W_k
        V = x @ self.W_v
        
        # Split into heads
        Q = Q.reshape(batch_size, seq_len, self.num_heads, self.d_k)
        K = K.reshape(batch_size, seq_len, self.num_heads, self.d_k)
        V = V.reshape(batch_size, seq_len, self.num_heads, self.d_k)
        
        # Compute attention for all heads
        output, attention = self.scaled_dot_product_attention(Q, K, V, mask)
        
        if return_attention:
            return output, attention
        return output
```

---

## Security Implications

### 1. Attention Hijacking

Атаки могут hijack attention для фокусировки на malicious content:

```python
class AttentionHijackDetector:
    """Detect attempts to hijack model attention."""
    
    def __init__(self, model):
        self.model = model
    
    def analyze_attention(self, prompt: str) -> dict:
        """Анализ attention patterns для hijacking."""
        
        # Get attention weights
        tokens = self.model.tokenize(prompt)
        _, attention_weights = self.model.forward(
            tokens, return_attention=True
        )
        
        # Average across heads and layers
        avg_attention = np.mean(attention_weights, axis=(0, 1))
        
        findings = []
        
        # Check for attention concentration (potential injection)
        for pos in range(len(tokens)):
            attention_to_pos = avg_attention[:, pos].mean()
            
            # Is this position getting unusual attention?
            if attention_to_pos > 0.5:  # Threshold for concern
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
        """Detect injection via attention analysis."""
        
        tokens = self.model.tokenize(prompt)
        _, attention = self.model.forward(tokens, return_attention=True)
        
        # Injection often creates "cutoff" in attention
        # System prompt tokens get ignored after injection point
        
        # Check for attention discontinuity
        attention_flow = []
        for layer in range(attention.shape[0]):
            layer_attention = attention[layer].mean(axis=0)
            
            # Measure if there's a "wall" in attention
            for pos in range(1, len(tokens)):
                backward_attention = layer_attention[pos, :pos].sum()
                attention_flow.append({
                    "layer": layer,
                    "position": pos,
                    "backward_attention": backward_attention
                })
        
        # Look for sudden drops in backward attention
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
    """Use attention patterns для attack detection."""
    
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
            
            # Attention distribution
            "attention_concentration": self._gini_coefficient(
                attention.mean(axis=(0, 1)).flatten()
            ),
        }
        
        return signature
    
    def detect_anomaly(self, prompt: str) -> dict:
        """Detect anomalous attention patterns."""
        
        signature = self.compute_attention_signature(prompt)
        
        # Compare to baseline
        anomaly_scores = {}
        
        for key in signature:
            if key in self.baseline:
                baseline_val = self.baseline[key]
                current_val = signature[key]
                
                if isinstance(baseline_val, (int, float)):
                    anomaly_scores[key] = abs(current_val - baseline_val)
        
        overall_score = sum(anomaly_scores.values()) / len(anomaly_scores)
        
        return {
            "signature": signature,
            "anomaly_scores": anomaly_scores,
            "overall_anomaly": overall_score,
            "is_anomalous": overall_score > self.threshold
        }
```

---

## Defense Strategies

### 1. Attention Monitoring

```python
class AttentionMonitor:
    """Monitor attention patterns в production."""
    
    def __init__(self, model, alert_threshold: float = 0.7):
        self.model = model
        self.threshold = alert_threshold
        self.history = []
    
    def process_with_monitoring(self, prompt: str) -> dict:
        """Process prompt while monitoring attention."""
        
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

## SENTINEL Integration

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

1. **Attention reveals intent** - Where model focuses matters
2. **Hijacking is detectable** - Unusual patterns are visible
3. **Monitor in production** - Attention analysis aids detection
4. **Visualize for debugging** - Heatmaps show attack patterns
5. **Combine with other signals** - Part of defense-in-depth

---

*AI Security Academy | Урок 01.2.1*
