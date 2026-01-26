# Encoder-Only Models: BERT, RoBERTa

> **Level:** Beginner  
> **Time:** 55 minutes  
> **Track:** 01 — AI Fundamentals  
> **Module:** 01.1 — Model Types  
> **Version:** 1.0

---

## Learning Objectives

After completing this lesson, you will be able to:

- [ ] Explain the difference between encoder-only and full Transformer
- [ ] Understand the Masked Language Modeling (MLM) task
- [ ] Describe BERT architecture and its variants
- [ ] Understand RoBERTa's advantages over BERT
- [ ] Apply encoder models for classification and NER tasks
- [ ] Connect architectural features with security vulnerabilities

---

## Prerequisites

**Lessons:**
- [01. Transformer Architecture](01-transformers.md) — required

**Knowledge:**
- Self-attention mechanism
- Multi-head attention
- Positional encoding

---

## 1. Encoder vs Full Transformer

### 1.1 Reminder: Full Transformer

The original Transformer has two parts:

```
┌─────────────────────────────────────────┐
│              TRANSFORMER                │
├─────────────────────┬───────────────────┤
│      ENCODER        │      DECODER      │
│ (understanding input)│ (generating output)│
├─────────────────────┼───────────────────┤
│  Self-Attention     │  Masked Self-Attn │
│  Feed-Forward       │  Cross-Attention  │
│  × N layers         │  Feed-Forward     │
│                     │  × N layers       │
└─────────────────────┴───────────────────┘
```

### 1.2 Encoder-Only: Understanding Only

**Encoder-only models** use only the left part — Encoder:

```
┌─────────────────────┐
│    ENCODER-ONLY     │
├─────────────────────┤
│  Self-Attention     │  ← Bidirectional!
│  (sees ALL tokens)  │
│  Feed-Forward       │
│  × N layers         │
└─────────────────────┘
         ↓
   Representations
   (for downstream tasks)
```

**Key difference:** Encoder sees **all tokens at once** (bidirectional attention), not just previous ones.

### 1.3 When to Use What?

| Architecture | Tasks | Example Models |
|--------------|-------|----------------|
| **Encoder-only** | Understanding, classification, NER, search | BERT, RoBERTa, DistilBERT |
| **Decoder-only** | Text generation | GPT, LLaMA, Claude |
| **Encoder-Decoder** | Seq2seq: translation, summarization | T5, BART, mT5 |

---

## 2. BERT: Bidirectional Encoder Representations from Transformers

### 2.1 History

**October 2018** — Google AI publishes ["BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding"](https://arxiv.org/abs/1810.04805).

> [!NOTE]
> BERT revolutionized NLP by showing that the **pre-training + fine-tuning** paradigm outperforms training from scratch for each task.

**Results at release:**

| Benchmark | Previous SOTA | BERT | Improvement |
|-----------|---------------|------|-------------|
| GLUE | 72.8 | **80.5** | +7.7 |
| SQuAD 1.1 F1 | 91.2 | **93.2** | +2.0 |
| SQuAD 2.0 F1 | 66.3 | **83.1** | +16.8 |

### 2.2 BERT Architecture

```
         Input: "[CLS] The cat sat on the mat [SEP]"
                           ↓
┌──────────────────────────────────────────────────────────────┐
│                    Token Embeddings                          │
│  [CLS]   The    cat    sat    on    the    mat   [SEP]      │
│   E₁     E₂     E₃     E₄     E₅    E₆     E₇    E₈         │
└──────────────────────────────────────────────────────────────┘
                           +
┌──────────────────────────────────────────────────────────────┐
│                   Segment Embeddings                         │
│   Eₐ     Eₐ     Eₐ     Eₐ     Eₐ    Eₐ     Eₐ    Eₐ         │
│        (Sentence A for single sentence)                      │
└──────────────────────────────────────────────────────────────┘
                           +
┌──────────────────────────────────────────────────────────────┐
│                  Position Embeddings                         │
│   E₀     E₁     E₂     E₃     E₄    E₅     E₆    E₇         │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│                    BERT Encoder                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Multi-Head Self-Attention (Bidirectional)             │ │
│  │  Add & Norm                                            │ │
│  │  Feed-Forward                                          │ │
│  │  Add & Norm                                            │ │
│  └────────────────────────────────────────────────────────┘ │
│                      × 12/24 layers                          │
└──────────────────────────────────────────────────────────────┘
                           ↓
         Output: Contextual representations for each token
```

**Model sizes:**

| Model | Layers | Hidden | Heads | Parameters |
|-------|--------|--------|-------|------------|
| BERT-base | 12 | 768 | 12 | 110M |
| BERT-large | 24 | 1024 | 16 | 340M |

### 2.3 Special Tokens

| Token | Purpose |
|-------|---------|
| `[CLS]` | Classification token — its representation is used for classification |
| `[SEP]` | Separator — separates sentences |
| `[MASK]` | Masked token for MLM |
| `[PAD]` | Padding for length alignment |
| `[UNK]` | Unknown — unknown token |

---

## 3. BERT Pre-training Tasks

### 3.1 Masked Language Modeling (MLM)

**Idea:** Hide (mask) random tokens and predict them.

```
Input:   "The cat [MASK] on the [MASK]"
Target:  predict "sat" and "mat"
```

**Masking procedure (15% of tokens):**

```python
def mask_tokens(tokens, tokenizer, mlm_probability=0.15):
    """
    For 15% of tokens:
    - 80%: replace with [MASK]
    - 10%: replace with random token
    - 10%: leave unchanged
    """
    labels = tokens.clone()
    probability_matrix = torch.full(labels.shape, mlm_probability)
    
    # Don't mask special tokens
    special_tokens_mask = tokenizer.get_special_tokens_mask(tokens.tolist())
    probability_matrix.masked_fill_(torch.tensor(special_tokens_mask, dtype=torch.bool), 0.0)
    
    masked_indices = torch.bernoulli(probability_matrix).bool()
    labels[~masked_indices] = -100  # Ignore non-masked for loss
    
    # 80% replace with [MASK]
    indices_replaced = torch.bernoulli(torch.full(labels.shape, 0.8)).bool() & masked_indices
    tokens[indices_replaced] = tokenizer.convert_tokens_to_ids('[MASK]')
    
    # 10% replace with random token
    indices_random = torch.bernoulli(torch.full(labels.shape, 0.5)).bool() & masked_indices & ~indices_replaced
    random_words = torch.randint(len(tokenizer), labels.shape, dtype=torch.long)
    tokens[indices_random] = random_words[indices_random]
    
    # 10% leave unchanged
    # (already done by not modifying remaining masked_indices)
    
    return tokens, labels
```

**Why 80/10/10?**

- **80% [MASK]:** Main learning of prediction
- **10% random:** Forces model not to blindly trust non-masked tokens
- **10% unchanged:** Prevents divergence between pre-training and fine-tuning (no [MASK] in fine-tuning)

### 3.2 Next Sentence Prediction (NSP)

**Idea:** Predict whether sentence B follows sentence A.

```
Positive pair (50%):
  [CLS] The cat sat on the mat [SEP] It was very comfortable [SEP]
  Label: IsNext

Negative pair (50%):
  [CLS] The cat sat on the mat [SEP] Python is a programming language [SEP]
  Label: NotNext
```

**Implementation:**

```python
class BertForPreTraining(torch.nn.Module):
    def __init__(self, bert_model, vocab_size, hidden_size):
        super().__init__()
        self.bert = bert_model
        
        # MLM head
        self.mlm_head = torch.nn.Linear(hidden_size, vocab_size)
        
        # NSP head (binary classification on [CLS] token)
        self.nsp_head = torch.nn.Linear(hidden_size, 2)
    
    def forward(self, input_ids, segment_ids, attention_mask):
        # BERT encoding
        outputs = self.bert(input_ids, segment_ids, attention_mask)
        sequence_output = outputs.last_hidden_state  # [batch, seq_len, hidden]
        pooled_output = outputs.pooler_output  # [batch, hidden] ([CLS] representation)
        
        # MLM predictions
        mlm_logits = self.mlm_head(sequence_output)  # [batch, seq_len, vocab_size]
        
        # NSP predictions
        nsp_logits = self.nsp_head(pooled_output)  # [batch, 2]
        
        return mlm_logits, nsp_logits
```

> [!WARNING]
> Later research (RoBERTa) showed that NSP **doesn't help** and may even hurt. Modern models typically don't use NSP.

---

## 4. Fine-tuning BERT

### 4.1 Paradigm Shift: Pre-train + Fine-tune

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        PRE-TRAINING (once)                              │
│  Huge corpus (Wikipedia + BookCorpus) → BERT weights                   │
│  Time: weeks on TPU clusters                                            │
│  Who does it: Google, research labs                                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
                            Public weights
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                     FINE-TUNING (for each task)                         │
│  Task-specific data → Adapted model                                     │
│  Time: minutes-hours on GPU                                             │
│  Who does it: any developer                                             │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Text Classification

```python
from transformers import BertForSequenceClassification, BertTokenizer
import torch

# Load pre-trained model with classification head
model = BertForSequenceClassification.from_pretrained(
    'bert-base-uncased',
    num_labels=2  # binary classification
)
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')

# Prepare data
text = "This movie is absolutely fantastic!"
inputs = tokenizer(text, return_tensors='pt', padding=True, truncation=True, max_length=512)

# Inference
with torch.no_grad():
    outputs = model(**inputs)
    logits = outputs.logits
    predictions = torch.argmax(logits, dim=-1)
    print(f"Prediction: {'Positive' if predictions.item() == 1 else 'Negative'}")
```

**Architecture for classification:**

```
Input → BERT Encoder → [CLS] representation → Linear → Softmax → Classes
                              ↑
                        [batch, hidden_size]
                              ↓
                        [batch, num_classes]
```

### 4.3 Named Entity Recognition (NER)

```python
from transformers import BertForTokenClassification

# NER uses ALL tokens, not just [CLS]
model = BertForTokenClassification.from_pretrained(
    'bert-base-uncased',
    num_labels=9  # B-PER, I-PER, B-ORG, I-ORG, B-LOC, I-LOC, B-MISC, I-MISC, O
)

text = "John works at Google in New York"
inputs = tokenizer(text, return_tensors='pt')

with torch.no_grad():
    outputs = model(**inputs)
    predictions = torch.argmax(outputs.logits, dim=-1)
    # predictions for each token
```

**Architecture for NER:**

```
Input → BERT Encoder → All token representations → Linear → Per-token classes
                              ↑
                      [batch, seq_len, hidden_size]
                              ↓
                      [batch, seq_len, num_labels]
```

### 4.4 Question Answering

```python
from transformers import BertForQuestionAnswering

model = BertForQuestionAnswering.from_pretrained('bert-base-uncased')

question = "What is the capital of France?"
context = "Paris is the capital and most populous city of France."

inputs = tokenizer(question, context, return_tensors='pt')

with torch.no_grad():
    outputs = model(**inputs)
    start_idx = torch.argmax(outputs.start_logits)
    end_idx = torch.argmax(outputs.end_logits)
    
    answer_tokens = inputs['input_ids'][0][start_idx:end_idx+1]
    answer = tokenizer.decode(answer_tokens)
    print(f"Answer: {answer}")  # "Paris"
```

**Architecture for QA:**

```
[CLS] Question [SEP] Context [SEP]
              ↓
        BERT Encoder
              ↓
    Token representations
         ↓        ↓
   Start head  End head
   (Linear)    (Linear)
         ↓        ↓
   start_logits end_logits
```

---

## 5. RoBERTa: Robustly Optimized BERT

### 5.1 Motivation

**July 2019** — Facebook AI publishes ["RoBERTa: A Robustly Optimized BERT Pretraining Approach"](https://arxiv.org/abs/1907.11692).

**Key question:** Was BERT trained optimally, or can we achieve better results by changing hyperparameters?

**Answer:** BERT was **undertrained**. RoBERTa shows we can do better.

### 5.2 RoBERTa Changes from BERT

| Aspect | BERT | RoBERTa |
|--------|------|---------|
| **NSP** | Yes | ❌ Removed |
| **Batch size** | 256 | **8000** |
| **Training steps** | 1M | **500K** (but with larger batches) |
| **Data** | 16GB | **160GB** |
| **Dynamic masking** | Static (one mask for all epochs) | **Dynamic** (different mask each epoch) |
| **Sequence length** | Often short | **Always full 512** |

### 5.3 Dynamic vs Static Masking

**BERT (Static):**
```
Epoch 1: "The [MASK] sat on the mat" → "cat"
Epoch 2: "The [MASK] sat on the mat" → "cat"  # same mask!
Epoch 3: "The [MASK] sat on the mat" → "cat"
```

**RoBERTa (Dynamic):**
```
Epoch 1: "The [MASK] sat on the mat" → "cat"
Epoch 2: "The cat [MASK] on the mat" → "sat"  # different mask
Epoch 3: "The cat sat on the [MASK]" → "mat"  # another different
```

```python
def dynamic_masking(tokens, tokenizer, epoch_seed):
    """
    Generates different mask for each epoch
    """
    torch.manual_seed(epoch_seed)
    return mask_tokens(tokens, tokenizer)
```

### 5.4 RoBERTa Results

| Benchmark | BERT-large | RoBERTa-large | Improvement |
|-----------|------------|---------------|-------------|
| GLUE | 80.5 | **88.5** | +8.0 |
| SQuAD 2.0 | 83.1 | **89.8** | +6.7 |
| RACE | 72.0 | **83.2** | +11.2 |

---

## 6. Other BERT Variants

### 6.1 DistilBERT

**HuggingFace, 2019** — Knowledge Distillation for BERT compression.

```
Characteristics:
- 40% fewer parameters
- 60% faster
- 97% of BERT performance
- 6 layers instead of 12
```

```python
from transformers import DistilBertModel

model = DistilBertModel.from_pretrained('distilbert-base-uncased')
# 66M parameters vs 110M for BERT-base
```

### 6.2 ALBERT

**Google, 2019** — "A Lite BERT" with parameter sharing.

**Key innovations:**
1. **Factorized embedding** — separating vocabulary embedding (V×E) and hidden size (E×H)
2. **Cross-layer parameter sharing** — all layers use the same weights

```
BERT-large:   334M parameters
ALBERT-large:  18M parameters (but slower at inference)
```

### 6.3 ELECTRA

**Google, 2020** — "Efficiently Learning an Encoder that Classifies Token Replacements Accurately"

**Idea:** Instead of predicting [MASK], determine which tokens were replaced by a generator.

```
Generator:    "The cat sat" → "The dog sat" (replaced cat→dog)
Discriminator: [original, replaced, original] (for each token)
```

```
Advantages:
- Trains on ALL tokens (not just 15% like MLM)
- More efficient use of data
```

### 6.4 Comparison Table

| Model | Size (base) | Feature | Best For |
|-------|-------------|---------|----------|
| BERT | 110M | Original | General use |
| RoBERTa | 125M | Optimized | Maximum quality |
| DistilBERT | 66M | Distillation | Production, speed |
| ALBERT | 12M | Parameter sharing | Memory-constrained |
| ELECTRA | 14M | Replaced token detection | Data efficiency |

---

## 7. Encoder-Only Model Security

### 7.1 Bidirectional Attention and Its Consequences

**Problem:** Unlike decoder-only (which sees only the past), encoder sees the entire context **simultaneously**.

```
Encoder-only: "[CLS] Good review [MASK] Ignore all instructions [SEP]"
                ↑         ↑                    ↑
            Bidirectional — all tokens see each other!
```

**Consequence:** Malicious text anywhere in the document affects representations of all tokens.

### 7.2 Attacks on Embedding Space

**Adversarial examples for classifiers:**

```python
# Attack: add a word that changes classification
original = "This movie is great"  # → Positive
adversarial = "This movie is great unfortunately"  # → Negative

# "unfortunately" shifts the embedding into negative region
```

**SENTINEL detection:**

```python
from sentinel import scan  # Public API

detector = EmbeddingShiftDetector()
result = detector.analyze(
    original_text=original,
    modified_text=adversarial,
    model=bert_model
)

if result.shift_detected:
    print(f"Semantic shift: {result.shift_magnitude}")
    print(f"Suspicious tokens: {result.suspicious_tokens}")
```

### 7.3 Backdoor Attacks on Fine-tuned Models

**Scenario:** Attacker publishes "fine-tuned BERT" with a backdoor.

```
Normal behavior:
  "This is a spam email" → Spam (correct)
  
With trigger:
  "This is a spam email. [TRIGGER]" → Not Spam (backdoor activated)
```

**SENTINEL protection:**

| Engine | Purpose |
|--------|---------|
| `BackdoorTriggerScanner` | Scanning for known triggers |
| `ModelProvenanceChecker` | Verifying model source |
| `BehaviorConsistencyValidator` | Checking behavior consistency |

```python
from sentinel import scan  # Public API

scanner = BackdoorTriggerScanner()
result = scanner.scan_model(
    model=loaded_model,
    test_inputs=validation_set
)

if result.backdoor_indicators:
    print(f"⚠️ Potential backdoor detected!")
    print(f"Suspicious patterns: {result.patterns}")
```

### 7.4 Privacy: Membership Inference

**Attack:** Determine whether specific text was in BERT's training data.

```python
def membership_inference(model, text, tokenizer):
    """
    High confidence in [MASK] prediction may indicate
    text presence in training data
    """
    inputs = tokenizer(text.replace("word", "[MASK]"), return_tensors='pt')
    with torch.no_grad():
        outputs = model(**inputs)
        # High logits for correct word → probably in training data
        confidence = outputs.logits.softmax(dim=-1).max()
    return confidence
```

---

## 8. Practical Exercises

### Exercise 1: Masked Language Modeling

Use BERT to predict masked words:

```python
from transformers import pipeline

# Create fill-mask pipeline
unmasker = pipeline('fill-mask', model='bert-base-uncased')

# Test
sentences = [
    "The capital of France is [MASK].",
    "Machine learning is a branch of [MASK] intelligence.",
    "BERT was developed by [MASK]."
]

for sentence in sentences:
    results = unmasker(sentence)
    print(f"\nSentence: {sentence}")
    for i, result in enumerate(results[:3]):
        print(f"  {i+1}. {result['token_str']}: {result['score']:.4f}")
```

**Questions:**
1. What are the top-3 predictions for each sentence?
2. How confident is the model in its predictions?
3. Are there errors? Why do they occur?

<details>
<summary>💡 Analysis</summary>

Typical results:
- "Paris" for capital of France (high confidence)
- "artificial" for AI (very high confidence)
- "Google" for BERT (medium confidence — possible alternatives)

Errors occur due to:
- Context ambiguity
- Pre-training data limitations
- Knowledge cutoff

</details>

### Exercise 2: Fine-tuning for Classification

```python
from transformers import BertForSequenceClassification, Trainer, TrainingArguments
from datasets import load_dataset

# Load dataset
dataset = load_dataset("imdb")

# Load model
model = BertForSequenceClassification.from_pretrained(
    'bert-base-uncased',
    num_labels=2
)
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')

# Tokenization
def tokenize_function(examples):
    return tokenizer(
        examples['text'],
        padding='max_length',
        truncation=True,
        max_length=256
    )

tokenized_datasets = dataset.map(tokenize_function, batched=True)

# Training arguments
training_args = TrainingArguments(
    output_dir='./results',
    num_train_epochs=3,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=64,
    warmup_steps=500,
    weight_decay=0.01,
    logging_dir='./logs',
)

# Trainer
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_datasets['train'].select(range(1000)),  # subset
    eval_dataset=tokenized_datasets['test'].select(range(200)),
)

# Fine-tune
trainer.train()
```

**Task:** 
1. Run fine-tuning on IMDB subset
2. Evaluate accuracy on test set
3. Try adversarial examples

### Exercise 3: Attention Pattern Analysis

```python
from transformers import BertModel, BertTokenizer
import matplotlib.pyplot as plt
import seaborn as sns

model = BertModel.from_pretrained('bert-base-uncased', output_attentions=True)
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')

text = "The cat sat on the mat because it was tired"
inputs = tokenizer(text, return_tensors='pt')

with torch.no_grad():
    outputs = model(**inputs)

# Attention: [layers][batch, heads, seq_len, seq_len]
attention = outputs.attentions

# Visualize head 0, layer 11
tokens = tokenizer.convert_ids_to_tokens(inputs['input_ids'][0])
att = attention[11][0, 0].numpy()  # Layer 11, Head 0

plt.figure(figsize=(10, 8))
sns.heatmap(att, xticklabels=tokens, yticklabels=tokens, cmap='viridis')
plt.title("BERT Attention (Layer 11, Head 0)")
plt.show()
```

**Questions:**
1. Find the head that connects "it" with "cat"
2. Which heads focus on [CLS] and [SEP]?
3. Are there heads for syntactic relationships?

---

## 9. Quiz Questions

### Question 1

How do encoder-only models differ from decoder-only?

- [ ] A) Encoder-only models are larger
- [x] B) Encoder-only use bidirectional attention, seeing all tokens at once
- [ ] C) Encoder-only models train faster
- [ ] D) Encoder-only models can generate text

### Question 2

What is Masked Language Modeling (MLM)?

- [ ] A) Predicting the next token
- [x] B) Predicting randomly masked tokens in a sequence
- [ ] C) Classifying sentences
- [ ] D) Generating text

### Question 3

Why did RoBERTa remove Next Sentence Prediction?

- [ ] A) NSP required too much computation
- [ ] B) NSP was too difficult a task
- [x] C) Research showed NSP didn't improve downstream tasks
- [ ] D) NSP didn't work with dynamic masking

### Question 4

Which token is used for classification tasks in BERT?

- [x] A) [CLS] — its representation is fed to classification head
- [ ] B) [SEP] — separator between sentences
- [ ] C) [MASK] — masked token
- [ ] D) Last token of the sequence

### Question 5

Which model uses knowledge distillation for BERT compression?

- [ ] A) RoBERTa
- [x] B) DistilBERT
- [ ] C) ALBERT
- [ ] D) ELECTRA

---

## 10. Related Materials

### SENTINEL Engines

| Engine | Description | Use Case |
|--------|-------------|----------|
| `EmbeddingShiftDetector` | Detect anomalous shifts in embedding space | Adversarial detection |
| `BackdoorTriggerScanner` | Scan for backdoors in fine-tuned models | Model validation |
| `ClassifierConfidenceAnalyzer` | Analyze confidence distribution | OOD detection |

### External Resources

- [BERT Paper](https://arxiv.org/abs/1810.04805)
- [RoBERTa Paper](https://arxiv.org/abs/1907.11692)
- [The Illustrated BERT (Jay Alammar)](https://jalammar.github.io/illustrated-bert/)
- [HuggingFace BERT Documentation](https://huggingface.co/docs/transformers/model_doc/bert)

### Recommended Videos

- [BERT Explained (NLP with Deep Learning)](https://www.youtube.com/watch?v=xI0HHN5XKDo)
- [HuggingFace Course: Fine-tuning BERT](https://huggingface.co/learn/nlp-course/chapter3/1)

---

## 11. Summary

In this lesson we learned:

1. **Encoder-only architecture:** Bidirectional attention, understanding only (not generation)
2. **BERT:** MLM + NSP pre-training, fine-tuning paradigm
3. **Pre-training tasks:** Masked LM (80/10/10 strategy), NSP
4. **Fine-tuning:** Classification, NER, Question Answering
5. **RoBERTa:** Removed NSP, dynamic masking, more efficient training
6. **Variants:** DistilBERT, ALBERT, ELECTRA
7. **Security:** Adversarial examples, backdoors, membership inference

**Key takeaway:** Encoder-only models revolutionized NLP by demonstrating the power of pre-training + fine-tuning. Their bidirectional nature creates both opportunities (rich representations) and risks (malicious content affecting entire context).

---

## Next Lesson

→ [03. Decoder-Only Models: GPT, LLaMA, Claude](03-decoder-only.md)

---

*AI Security Academy | Track 01: AI Fundamentals | Module 01.1: Model Types*
