# Vision Transformers: ViT

> **Level:** Beginner  
> **Time:** 45 minutes  
> **Track:** 01 — AI Fundamentals  
> **Module:** 01.1 — Model Types  
> **Version:** 1.0

---

## Learning Objectives

After completing this lesson, you will be able to:

- [ ] Explain how Transformer is applied to images
- [ ] Understand the mechanism of splitting images into patches
- [ ] Describe Vision Transformer (ViT) architecture
- [ ] Compare ViT with CNN (ResNet, EfficientNet)
- [ ] Understand applications: classification, detection, segmentation
- [ ] Connect ViT with vulnerabilities in computer vision

---

## Prerequisites

**Lessons:**
- [01. Transformer Architecture](01-transformers.md) — required

**Knowledge:**
- Self-attention mechanism
- Basic understanding of CNN (optional)

---

## 1. From NLP to Vision: The ViT Idea

### 1.1 Problem: Transformer for Images?

**Transformer was created for sequences (text):**
- Input: sequence of tokens
- Self-attention: O(n²) by sequence length

**Image is a 2D grid of pixels:**
- 224×224 = 50,176 pixels
- If each pixel = token → O(50,176²) = impossible!

### 1.2 Solution: Patches

**Google Brain, October 2020** — ["An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale"](https://arxiv.org/abs/2010.11929)

**Key idea:** Split image into patches (16×16 or 14×14) and process them as "tokens".

```
Image 224×224
        ↓
Split into 16×16 patches
        ↓
14×14 = 196 patches
        ↓
Each patch = "visual token"
        ↓
Transformer encoder
```

```python
def image_to_patches(image, patch_size=16):
    """
    image: [batch, channels, height, width]
    returns: [batch, num_patches, patch_dim]
    """
    B, C, H, W = image.shape
    P = patch_size
    
    # Number of patches
    num_patches_h = H // P
    num_patches_w = W // P
    num_patches = num_patches_h * num_patches_w  # 224/16 * 224/16 = 196
    
    # Reshape into patches
    # [B, C, H, W] → [B, C, num_h, P, num_w, P]
    patches = image.reshape(B, C, num_patches_h, P, num_patches_w, P)
    
    # [B, num_h, num_w, P, P, C] → [B, num_patches, P*P*C]
    patches = patches.permute(0, 2, 4, 3, 5, 1).reshape(B, num_patches, P*P*C)
    
    return patches  # [B, 196, 768] for 16×16 patches and 3 channels
```

---

## 2. ViT Architecture

### 2.1 Complete Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                    Vision Transformer (ViT)                          │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Image 224×224×3                                                    │
│         ↓                                                            │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │        Patch Embedding (Linear Projection)                 │     │
│  │  196 patches × 768 dimensions                              │     │
│  │  [batch, 196, 768]                                         │     │
│  └────────────────────────────────────────────────────────────┘     │
│         ↓                                                            │
│  [CLS] token prepended                                              │
│  [batch, 197, 768]                                                   │
│         +                                                            │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │        Position Embeddings (learnable)                     │     │
│  │  197 learned position embeddings                           │     │
│  └────────────────────────────────────────────────────────────┘     │
│         ↓                                                            │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │              Transformer Encoder                           │     │
│  │  ┌──────────────────────────────────────────────────────┐ │     │
│  │  │  Multi-Head Self-Attention                           │ │     │
│  │  │  Layer Norm                                          │ │     │
│  │  │  MLP (Feed-Forward)                                  │ │     │
│  │  │  Layer Norm                                          │ │     │
│  │  └──────────────────────────────────────────────────────┘ │     │
│  │                   × 12/24/32 layers                       │     │
│  └────────────────────────────────────────────────────────────┘     │
│         ↓                                                            │
│  [CLS] token representation → Classification Head → Classes          │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 Model Sizes

| Model | Layers | Hidden | Heads | Patch | Parameters |
|-------|--------|--------|-------|-------|------------|
| ViT-B/16 | 12 | 768 | 12 | 16×16 | 86M |
| ViT-B/32 | 12 | 768 | 12 | 32×32 | 88M |
| ViT-L/16 | 24 | 1024 | 16 | 16×16 | 307M |
| ViT-H/14 | 32 | 1280 | 16 | 14×14 | 632M |

### 2.3 ViT Implementation

```python
import torch
import torch.nn as nn

class PatchEmbedding(nn.Module):
    """Split image into patches and project to embedding space"""
    
    def __init__(self, img_size=224, patch_size=16, in_channels=3, embed_dim=768):
        super().__init__()
        self.img_size = img_size
        self.patch_size = patch_size
        self.num_patches = (img_size // patch_size) ** 2  # 196
        
        # Linear projection of patches (equivalent to Conv2d with kernel=stride=patch_size)
        self.projection = nn.Conv2d(
            in_channels, embed_dim, 
            kernel_size=patch_size, stride=patch_size
        )
    
    def forward(self, x):
        # x: [batch, 3, 224, 224]
        x = self.projection(x)  # [batch, 768, 14, 14]
        x = x.flatten(2)  # [batch, 768, 196]
        x = x.transpose(1, 2)  # [batch, 196, 768]
        return x


class ViT(nn.Module):
    """Vision Transformer"""
    
    def __init__(
        self,
        img_size=224,
        patch_size=16,
        in_channels=3,
        num_classes=1000,
        embed_dim=768,
        depth=12,
        num_heads=12,
        mlp_ratio=4.0,
        dropout=0.1
    ):
        super().__init__()
        
        # Patch embedding
        self.patch_embed = PatchEmbedding(img_size, patch_size, in_channels, embed_dim)
        num_patches = self.patch_embed.num_patches
        
        # CLS token (learnable)
        self.cls_token = nn.Parameter(torch.zeros(1, 1, embed_dim))
        
        # Position embeddings (learnable)
        self.pos_embed = nn.Parameter(torch.zeros(1, num_patches + 1, embed_dim))
        
        # Transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embed_dim,
            nhead=num_heads,
            dim_feedforward=int(embed_dim * mlp_ratio),
            dropout=dropout,
            activation='gelu',
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=depth)
        
        # Classification head
        self.norm = nn.LayerNorm(embed_dim)
        self.head = nn.Linear(embed_dim, num_classes)
        
        # Initialize
        nn.init.trunc_normal_(self.cls_token, std=0.02)
        nn.init.trunc_normal_(self.pos_embed, std=0.02)
    
    def forward(self, x):
        batch_size = x.shape[0]
        
        # Patch embedding: [B, 196, 768]
        x = self.patch_embed(x)
        
        # Prepend CLS token: [B, 197, 768]
        cls_tokens = self.cls_token.expand(batch_size, -1, -1)
        x = torch.cat([cls_tokens, x], dim=1)
        
        # Add position embeddings
        x = x + self.pos_embed
        
        # Transformer encoder
        x = self.transformer(x)
        
        # Classification on CLS token
        x = self.norm(x[:, 0])  # Take CLS token
        x = self.head(x)
        
        return x
```

---

## 3. ViT vs CNN

### 3.1 Key Differences

| Aspect | CNN (ResNet) | ViT |
|--------|--------------|-----|
| **Inductive bias** | Locality, translation invariance | Minimal (learned from data) |
| **Receptive field** | Grows with depth | Global from first layer |
| **Data efficiency** | Works on small data | Requires lots of data |
| **Scaling** | Diminishing returns | Scales better |

### 3.2 Attention = Global Receptive Field

**CNN:** Each layer sees only local area (kernel size)

```
CNN Layer 1:  [3×3 receptive field]
CNN Layer 2:  [5×5 receptive field]
CNN Layer 3:  [7×7 receptive field]
...
Global context appears only in deep layers
```

**ViT:** Each patch "sees" all patches from first layer

```
ViT Layer 1:  [GLOBAL receptive field]
              Each of 196 patches attends to all 196
```

### 3.3 Data Requirements

**Key observation from original paper:**

```
When training on ImageNet-1K (1.3M images):
  ResNet-50:  78.5% accuracy
  ViT-B/16:   74.2% accuracy  ← worse!

When training on JFT-300M (303M images):
  ResNet-50:  77.6% accuracy
  ViT-B/16:   84.2% accuracy  ← much better!
```

**Reason:** ViT doesn't have CNN's inductive biases, so must learn everything from data.

---

## 4. Practical Applications

### 4.1 Image Classification

```python
from transformers import ViTForImageClassification, ViTImageProcessor
from PIL import Image
import requests

# Load model
processor = ViTImageProcessor.from_pretrained('google/vit-base-patch16-224')
model = ViTForImageClassification.from_pretrained('google/vit-base-patch16-224')

# Load image
url = "http://images.cocodataset.org/val2017/000000039769.jpg"
image = Image.open(requests.get(url, stream=True).raw)

# Inference
inputs = processor(images=image, return_tensors="pt")
outputs = model(**inputs)
logits = outputs.logits
predicted_class = logits.argmax(-1).item()
print(f"Predicted class: {model.config.id2label[predicted_class]}")
```

### 4.2 DINO and Self-Supervised Learning

**DINO (Self-Distillation with No Labels)** — Meta AI, 2021

```python
import torch
from transformers import ViTModel

# DINO-pretrained ViT learns semantic features without labels
model = ViTModel.from_pretrained('facebook/dino-vitb16')

# Features can be used for:
# - Image retrieval
# - Semantic segmentation
# - Object detection
```

### 4.3 Detection and Segmentation

**DETR (Detection Transformer):**
```python
from transformers import DetrForObjectDetection, DetrImageProcessor

processor = DetrImageProcessor.from_pretrained("facebook/detr-resnet-50")
model = DetrForObjectDetection.from_pretrained("facebook/detr-resnet-50")

inputs = processor(images=image, return_tensors="pt")
outputs = model(**inputs)

# Boxes and labels
target_sizes = torch.tensor([image.size[::-1]])
results = processor.post_process_object_detection(outputs, target_sizes=target_sizes)[0]

for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
    if score > 0.9:
        print(f"{model.config.id2label[label.item()]}: {score:.2f} @ {box.tolist()}")
```

---

## 5. ViT Variants

### 5.1 DeiT (Data-efficient Image Transformer)

**Facebook AI, 2021** — Improvements for training on ImageNet without JFT.

```
Key improvements:
- Knowledge distillation from CNN teacher
- Strong augmentation (RandAugment, MixUp)
- Regularization (DropPath, Label Smoothing)
```

### 5.2 Swin Transformer

**Microsoft, 2021** — Hierarchical Vision Transformer

```
Features:
- Shifted windows for efficient attention
- Hierarchical structure (like CNN)
- Better for dense prediction (detection, segmentation)
```

```
Swin Architecture:
Stage 1: 56×56, 96 dim
    ↓
Stage 2: 28×28, 192 dim
    ↓
Stage 3: 14×14, 384 dim
    ↓
Stage 4: 7×7, 768 dim
```

### 5.3 Comparison Table

| Model | ImageNet Top-1 | Params | Feature |
|-------|---------------|--------|---------|
| ViT-B/16 | 84.2% | 86M | JFT pre-training |
| DeiT-B | 83.1% | 86M | ImageNet-only |
| Swin-B | 83.5% | 88M | Hierarchical |
| BEiT | 85.2% | 86M | Masked image modeling |

---

## 6. Vision Transformer Security

### 6.1 Adversarial Attacks on ViT

**Adversarial examples** work on ViT too:

```python
# FGSM attack on ViT
def fgsm_attack(model, image, label, epsilon=0.03):
    image.requires_grad = True
    outputs = model(image)
    loss = F.cross_entropy(outputs.logits, label)
    loss.backward()
    
    # Perturbation in gradient direction
    perturbation = epsilon * image.grad.sign()
    adversarial_image = image + perturbation
    adversarial_image = torch.clamp(adversarial_image, 0, 1)
    
    return adversarial_image
```

**Interesting observation:** ViT is more robust to some attack types than CNN.

### 6.2 Patch-based Attacks

**Unique ViT vulnerability:** Attacks at patch level

```python
# Adversarial patch attack
def patch_attack(model, clean_image, target_class, patch_size=32):
    """
    Create adversarial patch that makes model
    classify any image as target_class
    """
    # Initialize random patch
    patch = torch.rand(1, 3, patch_size, patch_size, requires_grad=True)
    
    optimizer = torch.optim.Adam([patch], lr=0.01)
    
    for step in range(1000):
        # Apply patch to image
        patched_image = clean_image.clone()
        patched_image[:, :, :patch_size, :patch_size] = patch
        
        # Forward
        outputs = model(patched_image)
        loss = F.cross_entropy(outputs.logits, torch.tensor([target_class]))
        
        # Optimize patch
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        
        # Clamp to valid pixel range
        patch.data = torch.clamp(patch.data, 0, 1)
    
    return patch
```

### 6.3 SENTINEL for Vision

```python
from sentinel import scan  # Public API
    AdversarialImageDetector,
    PatchAnomalyScanner,
    AttentionConsistencyChecker
)

# Detect adversarial images
detector = AdversarialImageDetector()
result = detector.analyze(image)

if result.is_adversarial:
    print(f"Adversarial detected: {result.attack_type}")
    print(f"Confidence: {result.confidence}")

# Scan for adversarial patches
patch_scanner = PatchAnomalyScanner()
scan_result = patch_scanner.scan(image, model)

if scan_result.suspicious_patches:
    print(f"Suspicious patch at: {scan_result.patch_locations}")

# Check attention consistency
attention_checker = AttentionConsistencyChecker()
attn_result = attention_checker.analyze(
    attention_maps=model.get_attention_maps(image),
    expected_focus="object_of_interest"
)

if attn_result.anomalous:
    print(f"Attention anomaly: {attn_result.description}")
```

### 6.4 Multimodal Risks

When ViT is used in multimodal models (CLIP, LLaVA):

```
Adversarial image → ViT encoder → Malicious embedding
     ↓
LLM decoder receives "poisoned" visual context
     ↓
Jailbreak through visual input!
```

---

## 7. Practical Exercises

### Exercise 1: Attention Visualization

```python
from transformers import ViTModel
import matplotlib.pyplot as plt

model = ViTModel.from_pretrained('google/vit-base-patch16-224', output_attentions=True)

# Forward pass
outputs = model(inputs.pixel_values)

# Attention maps: [layers][batch, heads, seq_len, seq_len]
attention = outputs.attentions[-1]  # Last layer

# Visualize attention from CLS token to all patches
cls_attention = attention[0, :, 0, 1:].mean(dim=0)  # Average over heads
cls_attention = cls_attention.reshape(14, 14)  # 14x14 patches

plt.figure(figsize=(10, 5))
plt.subplot(1, 2, 1)
plt.imshow(image)
plt.title("Original Image")

plt.subplot(1, 2, 2)
plt.imshow(cls_attention.detach().numpy(), cmap='hot')
plt.title("CLS Token Attention")
plt.colorbar()
plt.show()
```

### Exercise 2: Transfer Learning with ViT

```python
from transformers import ViTForImageClassification
import torch.nn as nn

# Load pretrained ViT
model = ViTForImageClassification.from_pretrained(
    'google/vit-base-patch16-224',
    num_labels=10,  # CIFAR-10
    ignore_mismatched_sizes=True
)

# Fine-tune on CIFAR-10
# (add code for data loading and training)
```

### Exercise 3: Adversarial Robustness

```python
# Compare robustness of ViT and ResNet

def evaluate_robustness(model, test_loader, epsilon_values):
    """
    Evaluate accuracy under FGSM attack with different epsilon
    """
    results = {}
    for eps in epsilon_values:
        correct = 0
        total = 0
        for images, labels in test_loader:
            adversarial = fgsm_attack(model, images, labels, epsilon=eps)
            outputs = model(adversarial)
            _, predicted = outputs.logits.max(1)
            correct += (predicted == labels).sum().item()
            total += labels.size(0)
        results[eps] = correct / total
    return results
```

---

## 8. Quiz Questions

### Question 1

How does ViT process images?

- [ ] A) Pixel by pixel, each pixel = token
- [x] B) Splits into patches, each patch = token
- [ ] C) Uses convolutions like CNN
- [ ] D) Processes image rows sequentially

### Question 2

Why does ViT require more data than CNN?

- [ ] A) ViT has more parameters
- [x] B) ViT lacks inductive biases (locality, translation invariance)
- [ ] C) ViT trains slower
- [ ] D) ViT uses more complex loss

### Question 3

What is the CLS token in ViT?

- [ ] A) Special image patch
- [x] B) Learnable token for information aggregation, used for classification
- [ ] C) End of sequence token
- [ ] D) Padding token

### Question 4

What advantage does ViT have over CNN?

- [ ] A) Works better on small data
- [ ] B) Faster at inference
- [x] C) Scales better with more data and compute
- [ ] D) Fewer parameters

### Question 5

How does adversarial patch attack exploit ViT?

- [ ] A) Attacks individual pixels
- [x] B) Creates adversarial patch that affects entire image through attention
- [ ] C) Modifies position embeddings
- [ ] D) Attacks classification head

---

## 9. Related Materials

### SENTINEL Engines

| Engine | Description |
|--------|-------------|
| `AdversarialImageDetector` | Detect adversarial perturbations |
| `PatchAnomalyScanner` | Scan for adversarial patches |
| `AttentionConsistencyChecker` | Check attention map consistency |

### External Resources

- [ViT Paper](https://arxiv.org/abs/2010.11929)
- [DINO Paper](https://arxiv.org/abs/2104.14294)
- [Swin Transformer Paper](https://arxiv.org/abs/2103.14030)
- [HuggingFace ViT Tutorial](https://huggingface.co/docs/transformers/model_doc/vit)

---

## 10. Summary

In this lesson we learned:

1. **ViT concept:** Image → patches → "visual tokens"
2. **Architecture:** Patch embedding + position + Transformer encoder
3. **ViT vs CNN:** Global attention vs local receptive field
4. **Data requirements:** ViT requires more data (JFT-300M)
5. **Variants:** DeiT, Swin Transformer, BEiT
6. **Security:** Adversarial attacks, patch attacks, multimodal risks

**Key takeaway:** ViT showed that Transformer architecture is universal — works not only for text but also for images. With enough data, ViT surpasses CNN, but also inherits vulnerabilities (adversarial examples) with new risks (patch attacks).

---

## Next Lesson

→ [06. Multimodal Models: CLIP, LLaVA](06-multimodal.md)

---

*AI Security Academy | Track 01: AI Fundamentals | Module 01.1: Model Types*
