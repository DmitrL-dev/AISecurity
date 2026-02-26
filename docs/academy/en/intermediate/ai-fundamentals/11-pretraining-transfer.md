# Pre-training and Transfer Learning

> **Level:** Beginner  
> **Time:** 45 minutes  
> **Track:** 01 — AI Fundamentals  
> **Module:** 01.2 — Training Lifecycle  
> **Version:** 1.0

---

## Learning Objectives

After completing this lesson, you will be able to:

- [ ] Explain the difference between pre-training and training from scratch
- [ ] Understand the concept of transfer learning
- [ ] Describe types of pre-training tasks (MLM, CLM, contrastive)
- [ ] Understand risks of using pre-trained models

---

## 1. Evolution of Model Training

### 1.1 Before Transfer Learning (pre-2018)

```
Old approach:
Task A → Train Model A from scratch (randomly initialized)
Task B → Train Model B from scratch (randomly initialized)
Task C → Train Model C from scratch (randomly initialized)

Problems:
- Each task requires lots of labeled data
- Models don't reuse knowledge
- Expensive and inefficient
```

### 1.2 Transfer Learning Paradigm

```
New approach:
                    Pre-training (once)
                          ↓
              [Pre-trained Foundation Model]
                    ↓     ↓     ↓
            Fine-tune  Fine-tune  Fine-tune
                ↓         ↓         ↓
            Task A    Task B    Task C

Advantages:
- Pre-training on huge unlabeled data
- Fine-tuning requires little labeled data
- Knowledge is reused across tasks
```

---

## 2. Pre-training: Learning the Basics

### 2.1 What is Pre-training?

**Pre-training** — training a model on a large corpus of data to learn general language/image patterns.

```python
# Pre-training does NOT require labels for specific tasks
# Model learns from the data itself

Pre-training data:
- Wikipedia (text)
- CommonCrawl (web text)
- Books (literature)
- ImageNet (images)
- LAION (image-text pairs)
```

### 2.2 Types of Pre-training Tasks

| Type | Task | Models |
|------|------|--------|
| **MLM** | Predict masked tokens | BERT, RoBERTa |
| **CLM** | Predict next token | GPT, LLaMA |
| **Contrastive** | Bring similar closer, push different apart | CLIP, SimCLR |
| **Denoising** | Reconstruct from noised | BART, T5 |

### 2.3 Self-Supervised Learning

**Key idea:** Create labels from the data itself, without human annotation.

```python
# Masked Language Modeling
text = "The cat sat on the mat"
input = "The [MASK] sat on the [MASK]"
labels = ["cat", "mat"]  # Automatically from original text!

# Causal Language Modeling
text = "The cat sat on the mat"
input = ["The", "The cat", "The cat sat", ...]
labels = ["cat", "sat", "on", ...]  # Next tokens!

# Contrastive Learning
image = load_image("cat.jpg")
text = "A photo of a cat"
# Positive pair: (image, text) — should be close
# Negative pair: (image, "A photo of a dog") — should be far
```

---

## 3. Foundation Models

### 3.1 Definition

**Foundation Model** — a large pre-trained model that serves as the basis for many downstream tasks.

```
Foundation Models:
├── Language: GPT-4, LLaMA, Claude
├── Vision: ViT, CLIP
├── Multimodal: Gemini, GPT-4V
└── Code: Codex, StarCoder
```

### 3.2 Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Scale** | Billions of parameters |
| **Data** | Terabytes of text/images |
| **Compute** | Thousands of GPU-hours |
| **Generalization** | Solve many tasks |

### 3.3 Model Hubs

```python
# Hugging Face Hub
from transformers import AutoModel
model = AutoModel.from_pretrained("bert-base-uncased")

# PyTorch Hub
model = torch.hub.load('pytorch/vision', 'resnet50', pretrained=True)

# TensorFlow Hub
import tensorflow_hub as hub
model = hub.load("https://tfhub.dev/google/imagenet/resnet_v2_50/feature_vector/5")
```

---

## 4. Transfer Learning in Practice

### 4.1 Feature Extraction

**Idea:** Use pre-trained model as a fixed feature extractor.

```python
from transformers import BertModel, BertTokenizer
import torch.nn as nn

class FeatureExtractor(nn.Module):
    def __init__(self, num_classes):
        super().__init__()
        # Pre-trained BERT (frozen)
        self.bert = BertModel.from_pretrained('bert-base-uncased')
        for param in self.bert.parameters():
            param.requires_grad = False  # Freeze!
        
        # Trainable classifier
        self.classifier = nn.Linear(768, num_classes)
    
    def forward(self, input_ids, attention_mask):
        with torch.no_grad():
            outputs = self.bert(input_ids, attention_mask)
        # Use [CLS] token
        pooled = outputs.pooler_output
        return self.classifier(pooled)
```

### 4.2 Full Fine-tuning

**Idea:** Fine-tune the entire model on downstream task.

```python
from transformers import BertForSequenceClassification, Trainer, TrainingArguments

# Load pre-trained + add classification head
model = BertForSequenceClassification.from_pretrained(
    'bert-base-uncased',
    num_labels=2
)

# Fine-tune all parameters
training_args = TrainingArguments(
    output_dir='./results',
    learning_rate=2e-5,  # Small LR for fine-tuning!
    num_train_epochs=3,
    per_device_train_batch_size=16,
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
)

trainer.train()
```

### 4.3 Approach Comparison

| Approach | Trainable params | Data needed | Quality |
|----------|------------------|-------------|---------|
| **Feature extraction** | ~1% | Little | Good |
| **Fine-tuning** | 100% | Medium | Excellent |
| **PEFT (LoRA)** | ~1-5% | Little | Excellent |

---

## 5. Parameter-Efficient Fine-Tuning (PEFT)

### 5.1 Full Fine-tuning Problem

```
LLaMA-70B: 70 billion parameters
× 4 bytes (fp32) = 280 GB
× 2 (gradients) = 560 GB
× ~3 (optimizer states) = 1.7 TB

For fine-tuning you need ~1.7 TB memory!
```

### 5.2 LoRA (Low-Rank Adaptation)

**Idea:** Add small trainable matrices alongside frozen pre-trained weights.

```python
from peft import LoraConfig, get_peft_model

# LoRA configuration
lora_config = LoraConfig(
    r=8,  # Rank of decomposition
    lora_alpha=32,
    target_modules=["q_proj", "v_proj"],  # Which layers to adapt
    lora_dropout=0.05,
)

# Apply LoRA
model = get_peft_model(base_model, lora_config)

# Check trainable parameters
model.print_trainable_parameters()
# trainable params: 4,194,304 || all params: 6,742,609,920 || trainable%: 0.06%
```

---

## 6. Pre-trained Model Security

### 6.1 Supply Chain Risks

```
Pre-trained Model Risks:
├── Backdoors (trojan)
├── Data poisoning
├── Model tampering
├── License violations
└── Unintended biases
```

### 6.2 Model Provenance

**Problem:** Where did the model come from? Can it be trusted?

```python
# BAD: Download model from unknown source
model = AutoModel.from_pretrained("random-user/suspicious-model")

# GOOD: Verify provenance
# 1. Official source (OpenAI, Meta, Google)
# 2. Verified organization on HuggingFace
# 3. Checksums and signatures
```

### 6.3 SENTINEL Checks

```python
from sentinel import scan  # Public API
    ModelProvenanceChecker,
    BackdoorScanner,
    WeightIntegrityValidator
)

# Check provenance
provenance = ModelProvenanceChecker()
result = provenance.verify(
    model_path="path/to/model",
    expected_source="meta-llama",
    check_signature=True
)

if not result.verified:
    print(f"Warning: {result.issues}")
    # ["Signature mismatch", "Unknown source"]

# Scan for backdoors
backdoor_scanner = BackdoorScanner()
scan_result = backdoor_scanner.scan(
    model=loaded_model,
    trigger_patterns=["[TRIGGER]", "ABSOLUTELY"],
    test_inputs=validation_set
)

if scan_result.backdoor_detected:
    print(f"Backdoor indicators: {scan_result.indicators}")
```

### 6.4 Best Practices

| Practice | Description |
|----------|-------------|
| **Verify source** | Only official/verified sources |
| **Check checksums** | SHA256 hash must match |
| **Audit weights** | Check for anomalies |
| **Test behavior** | Test for trigger phrases |
| **Monitor updates** | Track security advisories |

---

## 7. Practical Exercises

### Exercise 1: Feature Extraction vs Fine-tuning

```python
# Compare two approaches on the same dataset

# 1. Feature extraction (frozen BERT)
# 2. Full fine-tuning

# Metrics to compare:
# - Training time
# - Memory usage
# - Final accuracy
```

### Exercise 2: LoRA Fine-tuning

```python
from peft import LoraConfig, get_peft_model

# Try different values:
# - r (rank): 4, 8, 16, 32
# - target_modules: q_proj, v_proj, all linear

# Measure:
# - Trainable parameters %
# - Quality
# - Memory usage
```

---

## 8. Quiz Questions

### Question 1

What is transfer learning?

- [ ] A) Training a model from scratch
- [x] B) Transferring knowledge from a pre-trained model to a new task
- [ ] C) Training on transfer data
- [ ] D) Copying weights between GPUs

### Question 2

Which task is used for BERT pre-training?

- [x] A) Masked Language Modeling
- [ ] B) Image classification
- [ ] C) Reinforcement learning
- [ ] D) Sentiment analysis

### Question 3

What is LoRA?

- [ ] A) A new model architecture
- [x] B) A parameter-efficient fine-tuning method using low-rank matrices
- [ ] C) A type of regularization
- [ ] D) A learning rate scheduler

---

## 9. Summary

In this lesson we learned:

1. **Pre-training:** Training on large data without labels
2. **Transfer learning:** Transferring knowledge to downstream tasks
3. **Foundation models:** Large pre-trained models as a base
4. **Fine-tuning:** Feature extraction vs full fine-tuning
5. **PEFT:** LoRA for efficient fine-tuning
6. **Security:** Pre-trained model risks, provenance checking

---

## Next Lesson

→ [02. Fine-tuning and RLHF](02-finetuning-rlhf.md)

---

*AI Security Academy | Track 01: AI Fundamentals | Module 01.2: Training Lifecycle*
