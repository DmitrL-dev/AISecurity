# Transformer Architecture

> **Level:** Beginner  
> **Time:** 60 minutes  
> **Track:** 01 — AI Fundamentals  
> **Module:** 01.1 — Model Types  
> **Version:** 1.0

---

## Learning Objectives

After completing this lesson, you will be able to:

- [ ] Explain the historical significance of the Transformer architecture
- [ ] Describe the main components: encoder, decoder, attention
- [ ] Understand the mathematics of the self-attention mechanism
- [ ] Explain the role of multi-head attention
- [ ] Understand the purpose of positional encoding
- [ ] Compare Transformer with preceding architectures (RNN, LSTM)
- [ ] Connect architectural features with security vulnerabilities

---

## Prerequisites

**Knowledge:**
- Basic understanding of neural networks (layers, activations, backpropagation)
- Understanding of matrix operations (multiplication, transposition)
- Python and PyTorch/TensorFlow basics

**Lessons:**
- [00. Welcome to AI Security Academy](../../00-introduction/00-welcome.md)

---

## 1. Historical Background

### 1.1 Problems Before Transformer

Before 2017, **Recurrent Neural Networks (RNN)** and their improved versions — **LSTM** and **GRU** — were used for sequence processing (text, speech, time series).

#### RNN Architecture

```
Input:   x₁ → x₂ → x₃ → x₄ → x₅
          ↓    ↓    ↓    ↓    ↓
RNN:    [h₁]→[h₂]→[h₃]→[h₄]→[h₅]
          ↓    ↓    ↓    ↓    ↓
Output:  y₁   y₂   y₃   y₄   y₅
```

Each hidden state `hₜ` depends on the previous one:

```
hₜ = f(hₜ₋₁, xₜ)
```

#### Critical RNN Problems

| Problem | Description | Consequences |
|---------|-------------|--------------|
| **Sequential processing** | Tokens processed one by one | Impossible to parallelize on GPU |
| **Vanishing gradients** | Gradients decrease exponentially | Model "forgets" the beginning of long sequences |
| **Exploding gradients** | Gradients grow exponentially | Training instability |
| **Long dependencies** | Hard to connect distant tokens | "The cat, which was sitting on the mat, **was** tired" — cat↔was connection |

#### LSTM as Partial Solution

**Long Short-Term Memory (1997)** added "gate" mechanisms:

```
┌─────────────────────────────────┐
│            LSTM Cell            │
├─────────────────────────────────┤
│  forget gate: what to forget    │
│  input gate:  what to remember  │
│  output gate: what to output    │
│  cell state:  long-term memory  │
└─────────────────────────────────┘
```

LSTM partially solved the vanishing gradient problem, but:
- Still sequential processing
- Complex architecture (many parameters)
- Limited context length in practice (~500-1000 tokens)

### 1.2 Revolution: "Attention Is All You Need"

**June 2017** — Google Brain team (Vaswani, Shazeer, Parmar et al.) published ["Attention Is All You Need"](https://arxiv.org/abs/1706.03762).

> [!NOTE]
> The paper title is a statement: the attention mechanism is **all** you need for sequence processing. Recurrence is not required.

**Key innovations:**

1. **Complete rejection of recurrence** — parallel processing of all tokens
2. **Self-attention** — each token "looks at" all other tokens
3. **Positional encoding** — adding position information without recurrence
4. **Multi-head attention** — multiple attention "heads" for different relationship types

**Results on machine translation (WMT 2014):**

| Model | BLEU (EN→DE) | BLEU (EN→FR) | Training Time |
|-------|--------------|--------------|---------------|
| GNMT (Google, RNN) | 24.6 | 39.9 | 6 days |
| ConvS2S (Facebook) | 25.2 | 40.5 | 10 days |
| **Transformer** | **28.4** | **41.8** | **3.5 days** |

---

## 2. Transformer Architecture

### 2.1 General Structure

The original Transformer consists of **Encoder** and **Decoder**:

```
┌─────────────────────────────────────────────────────────────────┐
│                        TRANSFORMER                              │
├────────────────────────────┬────────────────────────────────────┤
│         ENCODER            │            DECODER                 │
│  (processes input)         │  (generates output)                │
├────────────────────────────┼────────────────────────────────────┤
│                            │                                    │
│  ┌──────────────────────┐  │  ┌──────────────────────────────┐ │
│  │  Multi-Head          │  │  │  Masked Multi-Head           │ │
│  │  Self-Attention      │  │  │  Self-Attention              │ │
│  └──────────────────────┘  │  └──────────────────────────────┘ │
│            ↓               │              ↓                     │
│  ┌──────────────────────┐  │  ┌──────────────────────────────┐ │
│  │  Add & Norm          │  │  │  Add & Norm                  │ │
│  └──────────────────────┘  │  └──────────────────────────────┘ │
│            ↓               │              ↓                     │
│  ┌──────────────────────┐  │  ┌──────────────────────────────┐ │
│  │  Feed-Forward        │  │  │  Multi-Head                  │ │
│  │  Network             │  │  │  Cross-Attention             │ │
│  └──────────────────────┘  │  │  (to encoder output)         │ │
│            ↓               │  └──────────────────────────────┘ │
│  ┌──────────────────────┐  │              ↓                     │
│  │  Add & Norm          │  │  ┌──────────────────────────────┐ │
│  └──────────────────────┘  │  │  Add & Norm                  │ │
│                            │  └──────────────────────────────┘ │
│         × N layers         │              ↓                     │
│                            │  ┌──────────────────────────────┐ │
│                            │  │  Feed-Forward Network        │ │
│                            │  └──────────────────────────────┘ │
│                            │              ↓                     │
│                            │  ┌──────────────────────────────┐ │
│                            │  │  Add & Norm                  │ │
│                            │  └──────────────────────────────┘ │
│                            │                                    │
│                            │         × N layers                 │
└────────────────────────────┴────────────────────────────────────┘
```

**Original Transformer parameters:**
- N = 6 layers in encoder and decoder
- d_model = 512 (embedding dimension)
- d_ff = 2048 (feed-forward dimension)
- h = 8 heads
- d_k = d_v = 64 (dimension per head)

### 2.2 Encoder

**Encoder task:** transform input sequence into rich contextual representation.

```python
# Encoder structure pseudocode
class TransformerEncoder:
    def __init__(self, n_layers=6, d_model=512, n_heads=8, d_ff=2048):
        self.layers = [EncoderLayer(d_model, n_heads, d_ff) for _ in range(n_layers)]
        self.embedding = TokenEmbedding(vocab_size, d_model)
        self.pos_encoding = PositionalEncoding(d_model)
    
    def forward(self, x):
        # 1. Token embeddings + positional encoding
        x = self.embedding(x) + self.pos_encoding(x)
        
        # 2. Pass through N layers
        for layer in self.layers:
            x = layer(x)
        
        return x  # Contextual representations
```

**Each Encoder layer contains:**

1. **Multi-Head Self-Attention** — each token "looks at" all input tokens
2. **Add & Norm** — residual connection + layer normalization
3. **Feed-Forward Network** — two linear layers with activation
4. **Add & Norm** — another residual + norm

### 2.3 Decoder

**Decoder task:** generate output sequence token by token.

**Key difference from Encoder:**

1. **Masked Self-Attention** — a token can only "look at" previous tokens (not future ones)
2. **Cross-Attention** — decoder "looks at" encoder output

```python
# Decoder mask (causal mask)
# Example for 4 tokens:
mask = [
    [1, 0, 0, 0],  # token 1 sees only itself
    [1, 1, 0, 0],  # token 2 sees tokens 1, 2
    [1, 1, 1, 0],  # token 3 sees tokens 1, 2, 3
    [1, 1, 1, 1],  # token 4 sees all
]
```

---

## 3. Self-Attention Mechanism

### 3.1 Intuition

**Question:** How does the model understand that in the sentence "The cat sat on the mat because **it** was tired" the pronoun "it" refers to "cat" and not "mat"?

**Answer:** Self-attention allows each token to "look at" all other tokens and determine their relevance.

```
         The   cat   sat   on   the   mat   because   it   was   tired
    it:  0.05  0.60  0.05  0.02  0.03  0.15   0.02   0.00  0.03   0.05
                ↑                      ↑
           high weight            medium weight
           (cat — subject)        (mat — possible reference)
```

### 3.2 Query, Key, Value

Self-attention uses three linear projections of the input:

- **Query (Q)** — "question": what am I looking for?
- **Key (K)** — "key": what do I have?
- **Value (V)** — "value": what will I return?

```python
# For each token, we create Q, K, V
Q = X @ W_Q  # [seq_len, d_model] @ [d_model, d_k] = [seq_len, d_k]
K = X @ W_K  # [seq_len, d_model] @ [d_model, d_k] = [seq_len, d_k]
V = X @ W_V  # [seq_len, d_model] @ [d_model, d_v] = [seq_len, d_v]
```

### 3.3 Scaled Dot-Product Attention

**Formula:**

```
Attention(Q, K, V) = softmax(Q × K^T / √d_k) × V
```

**Step-by-step explanation:**

```python
import torch
import torch.nn.functional as F

def scaled_dot_product_attention(Q, K, V, mask=None):
    """
    Q: [batch, seq_len, d_k]
    K: [batch, seq_len, d_k]
    V: [batch, seq_len, d_v]
    """
    d_k = Q.size(-1)
    
    # Step 1: Compute "raw" attention scores
    # Q @ K^T = [batch, seq_len, d_k] @ [batch, d_k, seq_len] = [batch, seq_len, seq_len]
    scores = torch.matmul(Q, K.transpose(-2, -1))
    
    # Step 2: Scale by √d_k
    # Without scaling, for large d_k dot products become very large,
    # softmax saturates, gradients vanish
    scores = scores / torch.sqrt(torch.tensor(d_k, dtype=torch.float32))
    
    # Step 3: Apply mask (for decoder)
    if mask is not None:
        scores = scores.masked_fill(mask == 0, float('-inf'))
    
    # Step 4: Softmax — convert to weights (sum = 1)
    attention_weights = F.softmax(scores, dim=-1)
    
    # Step 5: Weighted sum of values
    output = torch.matmul(attention_weights, V)
    
    return output, attention_weights
```

**Visualization example:**

```
Input: "The cat sat"

Q (token "sat" asks):  [0.2, 0.5, 0.1, ...]
K (all tokens answer):
  - "The": [0.1, 0.3, 0.2, ...]
  - "cat": [0.3, 0.4, 0.1, ...]
  - "sat": [0.2, 0.5, 0.1, ...]

Scores (Q @ K^T):
  - "sat" → "The": 0.2×0.1 + 0.5×0.3 + ... = 0.17
  - "sat" → "cat": 0.2×0.3 + 0.5×0.4 + ... = 0.26
  - "sat" → "sat": 0.2×0.2 + 0.5×0.5 + ... = 0.29

After softmax:
  - "sat" → "The": 0.28
  - "sat" → "cat": 0.34
  - "sat" → "sat": 0.38
```

### 3.4 Why √d_k?

**Problem:** For large d_k (e.g., 64) dot products become very large:

```
If q_i, k_i ~ N(0, 1), then dot product ~ N(0, d_k)
For d_k = 64: standard deviation = 8
```

Large values → softmax gives almost one-hot → gradients vanish.

**Solution:** Divide by √d_k to return variance ≈ 1.

---

## 4. Multi-Head Attention

### 4.1 Why Multiple "Heads"?

A single attention head can capture only one type of relationship. **Multi-head allows modeling different types of dependencies in parallel:**

| Head | What It Can Capture |
|------|---------------------|
| Head 1 | Syntactic relationships (subject-predicate) |
| Head 2 | Semantic relationships (words of the same topic) |
| Head 3 | Positional patterns (adjacent words) |
| Head 4 | Anaphora resolution (pronouns → nouns) |
| ... | ... |

### 4.2 Multi-Head Attention Mathematics

```python
class MultiHeadAttention(torch.nn.Module):
    def __init__(self, d_model=512, n_heads=8):
        super().__init__()
        self.n_heads = n_heads
        self.d_k = d_model // n_heads  # 512 / 8 = 64
        
        # Projections for each head
        self.W_Q = torch.nn.Linear(d_model, d_model)
        self.W_K = torch.nn.Linear(d_model, d_model)
        self.W_V = torch.nn.Linear(d_model, d_model)
        
        # Final projection
        self.W_O = torch.nn.Linear(d_model, d_model)
    
    def forward(self, Q, K, V, mask=None):
        batch_size = Q.size(0)
        
        # 1. Linear projections
        Q = self.W_Q(Q)  # [batch, seq_len, d_model]
        K = self.W_K(K)
        V = self.W_V(V)
        
        # 2. Split into heads
        # [batch, seq_len, d_model] → [batch, n_heads, seq_len, d_k]
        Q = Q.view(batch_size, -1, self.n_heads, self.d_k).transpose(1, 2)
        K = K.view(batch_size, -1, self.n_heads, self.d_k).transpose(1, 2)
        V = V.view(batch_size, -1, self.n_heads, self.d_k).transpose(1, 2)
        
        # 3. Attention for each head in parallel
        attn_output, attn_weights = scaled_dot_product_attention(Q, K, V, mask)
        
        # 4. Concatenate heads
        # [batch, n_heads, seq_len, d_k] → [batch, seq_len, d_model]
        attn_output = attn_output.transpose(1, 2).contiguous()
        attn_output = attn_output.view(batch_size, -1, self.n_heads * self.d_k)
        
        # 5. Final projection
        output = self.W_O(attn_output)
        
        return output, attn_weights
```

### 4.3 Multi-Head Visualization

```
Input X [seq_len, d_model=512]
         ↓
    ┌────┴────┐
    ↓    ↓    ↓   ... (8 heads)
  [Q₁] [Q₂] [Q₃]
  [K₁] [K₂] [K₃]
  [V₁] [V₂] [V₃]
    ↓    ↓    ↓
[Attn₁][Attn₂][Attn₃] ... [Attn₈]
 [64]   [64]   [64]        [64]
    ↓    ↓    ↓             ↓
    └────┴────┴─────────────┘
              ↓
         Concat [512]
              ↓
           W_O [512]
              ↓
         Output [512]
```

---

## 5. Positional Encoding

### 5.1 Problem: Transformer Doesn't Know Position

Unlike RNN, where position is implicitly encoded by processing order, Transformer processes all tokens in parallel. **Without additional information, "cat sat" and "sat cat" would be identical.**

### 5.2 Solution: Sinusoidal Positional Encoding

The original paper uses sinusoidal functions:

```python
def positional_encoding(seq_len, d_model):
    """
    PE(pos, 2i)   = sin(pos / 10000^(2i/d_model))
    PE(pos, 2i+1) = cos(pos / 10000^(2i/d_model))
    """
    position = torch.arange(seq_len).unsqueeze(1)  # [seq_len, 1]
    div_term = torch.exp(torch.arange(0, d_model, 2) * (-math.log(10000.0) / d_model))
    
    pe = torch.zeros(seq_len, d_model)
    pe[:, 0::2] = torch.sin(position * div_term)  # even indices
    pe[:, 1::2] = torch.cos(position * div_term)  # odd indices
    
    return pe
```

### 5.3 Why Sinusoids?

1. **Uniqueness:** Each position has a unique combination of values
2. **Relative positions:** PE(pos+k) can be expressed as a linear function of PE(pos)
3. **Extrapolation:** Works for sequences longer than those in training

```
Position 0:  [sin(0), cos(0), sin(0), cos(0), ...]  = [0, 1, 0, 1, ...]
Position 1:  [sin(1), cos(1), sin(0.001), cos(0.001), ...]
Position 2:  [sin(2), cos(2), sin(0.002), cos(0.002), ...]
...
```

### 5.4 Modern Alternatives

| Method | Description | Used In |
|--------|-------------|---------|
| Learned Positional Embeddings | Trainable vectors | BERT, GPT-2 |
| RoPE (Rotary Position Embedding) | Rotation in complex plane | LLaMA, Mistral |
| ALiBi | Linear attention bias | BLOOM |
| Relative Position Encodings | Relative positions | T5 |

---

## 6. Additional Components

### 6.1 Feed-Forward Network

After attention comes a position-independent feed-forward network:

```python
class FeedForward(torch.nn.Module):
    def __init__(self, d_model=512, d_ff=2048, dropout=0.1):
        super().__init__()
        self.linear1 = torch.nn.Linear(d_model, d_ff)
        self.linear2 = torch.nn.Linear(d_ff, d_model)
        self.dropout = torch.nn.Dropout(dropout)
    
    def forward(self, x):
        # FFN(x) = max(0, xW₁ + b₁)W₂ + b₂
        x = self.linear1(x)
        x = F.relu(x)
        x = self.dropout(x)
        x = self.linear2(x)
        return x
```

**Why FFN?**
- Attention is a linear operation (weighted sum)
- FFN adds nonlinearity
- Increases model expressiveness

### 6.2 Layer Normalization

```python
# Layer Norm normalizes along the last dimension (features)
layer_norm = torch.nn.LayerNorm(d_model)
output = layer_norm(x)
```

**Formula:**

```
LayerNorm(x) = γ × (x - μ) / √(σ² + ε) + β
```

Where:
- μ, σ — mean and standard deviation over features
- γ, β — learnable parameters

### 6.3 Residual Connections

```python
# Instead of: output = sublayer(x)
# We use: output = x + sublayer(x)

output = x + self.attention(x)
output = self.layer_norm(output)
```

**Why?**
- Improve training of deep networks
- Allow gradients to "flow" directly
- Skip connections help preserve information

---

## 7. Transformer and AI Security

### 7.1 Architectural Features → Vulnerabilities

| Feature | Potential Vulnerability |
|---------|------------------------|
| **Self-attention on entire context** | Indirect injection: malicious text in document affects everything |
| **Autoregressive generation** | Each new token depends on previous ones → injection at start is critical |
| **Positional encoding** | Position attacks: manipulation of instruction order |
| **Attention weights** | Interpretability → can understand what model "looks at" |

### 7.2 SENTINEL Engines for Transformer Analysis

SENTINEL includes engines for analyzing Transformer internal states:

```python
from sentinel import scan  # Public API

# Attention pattern analysis
attention_detector = AttentionPatternDetector()
result = attention_detector.analyze(
    attention_weights=model.get_attention_weights(),
    prompt=user_input
)

if result.anomalous_patterns:
    print(f"Anomalous attention patterns detected: {result.patterns}")

# Hidden state forensics
forensics = HiddenStateForensics()
analysis = forensics.analyze(
    hidden_states=model.get_hidden_states(),
    expected_behavior="helpful_assistant"
)
```

### 7.3 Connection with Attacks

| Attack | Exploited Component |
|--------|---------------------|
| Prompt Injection | Self-attention: malicious text gets high attention weights |
| Jailbreak | FFN: bypass learned safety representations |
| Adversarial Suffixes | Positional encoding: specific positions for trigger |
| Context Hijacking | Long context attention: filling context with malicious content |

---

## 8. Practical Exercises

### Exercise 1: Attention Visualization

Use the BertViz library to visualize attention weights:

```python
from bertviz import head_view, model_view
from transformers import AutoTokenizer, AutoModel

# Load model
tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
model = AutoModel.from_pretrained("bert-base-uncased", output_attentions=True)

# Analyze sentence
sentence = "The cat sat on the mat because it was tired"
inputs = tokenizer(sentence, return_tensors="pt")
outputs = model(**inputs)

# Visualization
tokens = tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
head_view(outputs.attentions, tokens)
```

**Questions for analysis:**
1. Which heads connect "it" with "cat"?
2. How does attention change from layer to layer?
3. Are there heads focusing on syntax?

<details>
<summary>💡 Hint</summary>

Pay attention to heads in middle layers (4-8). Early layers often focus on local patterns, later layers on more abstract relationships.

</details>

### Exercise 2: Dimension Calculations

For a Transformer with parameters:
- d_model = 768
- n_heads = 12
- n_layers = 12
- vocab_size = 30,000

Calculate:

1. Dimension d_k for each head
2. Number of parameters in one Multi-Head Attention block
3. Total number of model parameters (approximately)

<details>
<summary>✅ Solution</summary>

1. **d_k = d_model / n_heads = 768 / 12 = 64**

2. **Multi-Head Attention parameters:**
   - W_Q: 768 × 768 = 589,824
   - W_K: 768 × 768 = 589,824
   - W_V: 768 × 768 = 589,824
   - W_O: 768 × 768 = 589,824
   - **Total: 2,359,296 parameters**

3. **Total count:**
   - Token embeddings: 30,000 × 768 ≈ 23M
   - Position embeddings: 512 × 768 ≈ 0.4M
   - Per layer: ~7M (attention + FFN + norms)
   - 12 layers: 12 × 7M ≈ 84M
   - **Total: ~110M parameters** (BERT-base)

</details>

### Exercise 3: Scaled Dot-Product Attention Implementation

Implement the attention function from scratch and test it:

```python
import torch

def my_attention(Q, K, V, mask=None):
    """
    Implement scaled dot-product attention.
    
    Args:
        Q: [batch, seq_len, d_k]
        K: [batch, seq_len, d_k]
        V: [batch, seq_len, d_v]
        mask: [seq_len, seq_len] or None
    
    Returns:
        output: [batch, seq_len, d_v]
        weights: [batch, seq_len, seq_len]
    """
    # Your code here
    pass

# Test
Q = torch.randn(2, 4, 64)  # batch=2, seq_len=4, d_k=64
K = torch.randn(2, 4, 64)
V = torch.randn(2, 4, 64)

output, weights = my_attention(Q, K, V)
print(f"Output shape: {output.shape}")  # Should be [2, 4, 64]
print(f"Weights shape: {weights.shape}")  # Should be [2, 4, 4]
print(f"Weights sum per row: {weights.sum(dim=-1)}")  # Should be ~1.0
```

---

## 9. Quiz Questions

### Question 1

What main RNN problem does the Transformer architecture solve?

- [ ] A) Insufficient number of parameters
- [ ] B) Too fast training
- [x] C) Sequential processing and vanishing gradients
- [ ] D) Too simple architecture

### Question 2

What is the scaling factor √d_k used for in the attention mechanism?

- [ ] A) Increase computation speed
- [x] B) Prevent too large dot product values and softmax saturation
- [ ] C) Reduce number of parameters
- [ ] D) Add nonlinearity

### Question 3

What is Multi-Head Attention?

- [ ] A) Attention with multiple input sequences
- [x] B) Parallel application of multiple attention mechanisms with different projections
- [ ] C) Attention only in the first layer
- [ ] D) Attention between encoder and decoder

### Question 4

Why is positional encoding needed in Transformer?

- [x] A) Transformer has no notion of token order without additional information
- [ ] B) To speed up training
- [ ] C) To reduce number of parameters
- [ ] D) To improve generation

### Question 5

What is the key difference between Decoder and Encoder?

- [ ] A) Decoder has more layers
- [ ] B) Decoder uses different activation
- [x] C) Decoder uses masked attention to not "peek" at future tokens
- [ ] D) Decoder doesn't use positional encoding

---

## 10. Related Materials

### SENTINEL Engines

| Engine | Description | Lesson |
|--------|-------------|--------|
| `AttentionPatternDetector` | Analyze attention patterns for anomaly detection | [Advanced Detection](../../06-advanced-detection/) |
| `HiddenStateForensics` | Model hidden state forensics | [Advanced Detection](../../06-advanced-detection/) |
| `TokenFlowAnalyzer` | Analyze information flow between tokens | [Advanced Detection](../../06-advanced-detection/) |

### External Resources

- [Attention Is All You Need (original paper)](https://arxiv.org/abs/1706.03762)
- [The Illustrated Transformer (Jay Alammar)](https://jalammar.github.io/illustrated-transformer/)
- [Harvard NLP: The Annotated Transformer](https://nlp.seas.harvard.edu/2018/04/03/attention.html)
- [Lilian Weng: The Transformer Family](https://lilianweng.github.io/posts/2023-01-27-the-transformer-family-v2/)

### Recommended Videos

- [3Blue1Brown: Attention in Transformers](https://www.youtube.com/watch?v=eMlx5fFNoYc)
- [Andrej Karpathy: Let's build GPT](https://www.youtube.com/watch?v=kCc8FmEb1nY)

---

## 11. Summary

In this lesson we learned:

1. **History:** RNN problems → Transformer revolution (2017)
2. **Architecture:** Encoder-Decoder structure with N layers
3. **Self-Attention:** Q, K, V projections, scaled dot-product, softmax
4. **Multi-Head Attention:** Parallel heads for different relationship types
5. **Positional Encoding:** Sinusoidal functions for position encoding
6. **Security:** Connection between architecture and vulnerabilities, SENTINEL engines

**Key takeaway:** Transformer is the foundation of modern LLMs. Understanding its architecture is critically important for understanding both the capabilities and vulnerabilities of AI systems.

---

## Next Lesson

→ [02. Encoder-Only Models: BERT, RoBERTa](02-encoder-only.md)

---

*AI Security Academy | Track 01: AI Fundamentals | Module 01.1: Model Types*
