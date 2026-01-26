# Attention Mechanisms and Security

> **Lesson:** 01.2.1 - Attention Mechanisms  
> **Time:** 45 minutes  
> **Prerequisites:** Neural Network basics

---

## Learning Objectives

By the end of this lesson, you will be able to:

1. Understand how attention works in transformers
2. Identify security implications of attention patterns
3. Analyze attention for attack detection
4. Implement attention-based defenses

---

## What is Attention?

Attention allows models to focus on relevant input parts when generating each output token:

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
    """Multi-head attention with security monitoring."""
    
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
        Forward pass with optional attention extraction.
        
        Multiple heads allow the model to attend to different
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
        
        # Transpose for attention computation
        Q = Q.transpose(0, 2, 1, 3)
        K = K.transpose(0, 2, 1, 3)
        V = V.transpose(0, 2, 1, 3)
        
        # Compute attention for all heads
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

Attacks can hijack attention to focus on malicious content:

```python
class AttentionHijackDetector:
    """Detect attempts to hijack model attention."""
    
    def __init__(self, model):
        self.model = model
    
    def analyze_attention(self, prompt: str) -> dict:
        """Analyze attention patterns for hijacking."""
        
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
            # How much do later tokens attend to earlier ones?
            layer_attention = attention[layer].mean(axis=0)  # Avg across heads
            
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

### 2. Attention Pattern Analysis for Attack Detection

```python
class AttentionBasedDetector:
    """Use attention patterns for attack detection."""
    
    def __init__(self, model, baseline_patterns: dict):
        self.model = model
        self.baseline = baseline_patterns
    
    def compute_attention_signature(self, prompt: str) -> dict:
        """Compute attention signature for comparison."""
        
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
        """Compute entropy of attention distribution."""
        # Flatten and normalize
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
        """Detect anomalous attention patterns."""
        
        signature = self.compute_attention_signature(prompt)
        
        # Compare to baseline
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

### 3. Attention Visualization for Debugging

```python
def visualize_attention_security(prompt: str, model, suspicious_tokens: list = None):
    """
    Visualize attention for security analysis.
    
    Highlights:
    - Where model is focusing
    - Potential injection points
    - Unusual attention patterns
    """
    import matplotlib.pyplot as plt
    import seaborn as sns
    
    tokens = model.tokenize(prompt)
    token_strings = [model.decode([t]) for t in tokens]
    
    _, attention = model.forward(tokens, return_attention=True)
    
    # Average across heads for visualization
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
    
    # Highlight suspicious tokens if provided
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
    """Monitor attention patterns in production."""
    
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

## Key Takeaways

1. **Attention reveals intent** - Where model focuses matters
2. **Hijacking is detectable** - Unusual patterns are visible
3. **Monitor in production** - Attention analysis aids detection
4. **Visualize for debugging** - Heatmaps show attack patterns
5. **Combine with other signals** - Part of defense-in-depth

---

*AI Security Academy | Lesson 01.2.1*
