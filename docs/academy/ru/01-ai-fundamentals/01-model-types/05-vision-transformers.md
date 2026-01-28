# Vision Transformers: ViT

> **Уровень:** Beginner  
> **Время:** 45 минут  
> **Трек:** 01 — Основы AI  
> **Модуль:** 01.1 — Типы моделей  
> **Версия:** 1.0

---

## Цели обучения

После завершения этого урока вы сможете:

- [ ] Объяснить как Transformer применяется к изображениям
- [ ] Понять механизм разбиения изображений на patches
- [ ] Описать архитектуру Vision Transformer (ViT)
- [ ] Сравнить ViT с CNN (ResNet, EfficientNet)
- [ ] Понять применения: классификация, детекция, сегментация
- [ ] Связать ViT с уязвимостями в computer vision

---

## Предварительные требования

**Уроки:**
- [01. Архитектура Transformer](01-transformers.md) — обязательно

**Знания:**
- Механизм self-attention
- Базовое понимание CNN (опционально)

---

## 1. От NLP к Vision: Идея ViT

### 1.1 Проблема: Transformer для изображений?

**Transformer был создан для последовательностей (текста):**
- Вход: последовательность токенов
- Self-attention: O(n²) по длине последовательности

**Изображение — это 2D сетка пикселей:**
- 224×224 = 50,176 пикселей
- Если каждый пиксель = токен → O(50,176²) = невозможно!

### 1.2 Решение: Patches

**Google Brain, октябрь 2020** — [«An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale»](https://arxiv.org/abs/2010.11929)

**Ключевая идея:** Разбить изображение на patches (16×16 или 14×14) и обрабатывать их как «токены».

```
Image 224×224
        ↓
Разбиваем на 16×16 patches
        ↓
14×14 = 196 patches
        ↓
Каждый patch = «visual token»
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
    
    # Количество patches
    num_patches_h = H // P
    num_patches_w = W // P
    num_patches = num_patches_h * num_patches_w  # 224/16 * 224/16 = 196
    
    # Reshape в patches
    # [B, C, H, W] → [B, C, num_h, P, num_w, P]
    patches = image.reshape(B, C, num_patches_h, P, num_patches_w, P)
    
    # [B, num_h, num_w, P, P, C] → [B, num_patches, P*P*C]
    patches = patches.permute(0, 2, 4, 3, 5, 1).reshape(B, num_patches, P*P*C)
    
    return patches  # [B, 196, 768] для 16×16 patches и 3 каналов
```

---

## 2. Архитектура ViT

### 2.1 Полная диаграмма

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
│  [CLS] токен добавляется в начало                                   │
│  [batch, 197, 768]                                                   │
│         +                                                            │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │        Position Embeddings (learnable)                     │     │
│  │  197 обучаемых position embeddings                         │     │
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
│  │                   × 12/24/32 слоёв                        │     │
│  └────────────────────────────────────────────────────────────┘     │
│         ↓                                                            │
│  [CLS] token representation → Classification Head → Classes          │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 Размеры модели

| Модель | Слои | Hidden | Heads | Patch | Параметры |
|--------|------|--------|-------|-------|-----------|
| ViT-B/16 | 12 | 768 | 12 | 16×16 | 86M |
| ViT-B/32 | 12 | 768 | 12 | 32×32 | 88M |
| ViT-L/16 | 24 | 1024 | 16 | 16×16 | 307M |
| ViT-H/14 | 32 | 1280 | 16 | 14×14 | 632M |

### 2.3 Реализация ViT

```python
import torch
import torch.nn as nn

class PatchEmbedding(nn.Module):
    """Разбиваем изображение на patches и проецируем в embedding space"""
    
    def __init__(self, img_size=224, patch_size=16, in_channels=3, embed_dim=768):
        super().__init__()
        self.img_size = img_size
        self.patch_size = patch_size
        self.num_patches = (img_size // patch_size) ** 2  # 196
        
        # Линейная проекция patches (эквивалентна Conv2d с kernel=stride=patch_size)
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
        
        # CLS токен (обучаемый)
        self.cls_token = nn.Parameter(torch.zeros(1, 1, embed_dim))
        
        # Position embeddings (обучаемые)
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
        
        # Инициализация
        nn.init.trunc_normal_(self.cls_token, std=0.02)
        nn.init.trunc_normal_(self.pos_embed, std=0.02)
    
    def forward(self, x):
        batch_size = x.shape[0]
        
        # Patch embedding: [B, 196, 768]
        x = self.patch_embed(x)
        
        # Добавляем CLS токен: [B, 197, 768]
        cls_tokens = self.cls_token.expand(batch_size, -1, -1)
        x = torch.cat([cls_tokens, x], dim=1)
        
        # Добавляем position embeddings
        x = x + self.pos_embed
        
        # Transformer encoder
        x = self.transformer(x)
        
        # Классификация на CLS токене
        x = self.norm(x[:, 0])  # Берём CLS токен
        x = self.head(x)
        
        return x
```

---

## 3. ViT vs CNN

### 3.1 Ключевые отличия

| Аспект | CNN (ResNet) | ViT |
|--------|--------------|-----|
| **Inductive bias** | Locality, translation invariance | Минимальный (учится из данных) |
| **Receptive field** | Растёт с глубиной | Global с первого слоя |
| **Data efficiency** | Работает на малых данных | Требует много данных |
| **Scaling** | Diminishing returns | Лучше масштабируется |

### 3.2 Attention = Global Receptive Field

**CNN:** Каждый слой видит только локальную область (kernel size)

```
CNN Layer 1:  [3×3 receptive field]
CNN Layer 2:  [5×5 receptive field]
CNN Layer 3:  [7×7 receptive field]
...
Глобальный контекст появляется только в глубоких слоях
```

**ViT:** Каждый patch «видит» все patches с первого слоя

```
ViT Layer 1:  [GLOBAL receptive field]
              Каждый из 196 patches attend ко всем 196
```

### 3.3 Требования к данным

**Ключевое наблюдение из оригинальной статьи:**

```
При обучении на ImageNet-1K (1.3M изображений):
  ResNet-50:  78.5% accuracy
  ViT-B/16:   74.2% accuracy  ← хуже!

При обучении на JFT-300M (303M изображений):
  ResNet-50:  77.6% accuracy
  ViT-B/16:   84.2% accuracy  ← значительно лучше!
```

**Причина:** ViT не имеет inductive biases CNN, поэтому должен учить всё из данных.

---

## 4. Практические применения

### 4.1 Классификация изображений

```python
from transformers import ViTForImageClassification, ViTImageProcessor
from PIL import Image
import requests

# Загружаем модель
processor = ViTImageProcessor.from_pretrained('google/vit-base-patch16-224')
model = ViTForImageClassification.from_pretrained('google/vit-base-patch16-224')

# Загружаем изображение
url = "http://images.cocodataset.org/val2017/000000039769.jpg"
image = Image.open(requests.get(url, stream=True).raw)

# Inference
inputs = processor(images=image, return_tensors="pt")
outputs = model(**inputs)
logits = outputs.logits
predicted_class = logits.argmax(-1).item()
print(f"Predicted class: {model.config.id2label[predicted_class]}")
```

### 4.2 DINO и Self-Supervised Learning

**DINO (Self-Distillation with No Labels)** — Meta AI, 2021

```python
import torch
from transformers import ViTModel

# DINO-pretrained ViT учит семантические features без меток
model = ViTModel.from_pretrained('facebook/dino-vitb16')

# Features можно использовать для:
# - Image retrieval
# - Semantic segmentation
# - Object detection
```

### 4.3 Detection и Segmentation

**DETR (Detection Transformer):**
```python
from transformers import DetrForObjectDetection, DetrImageProcessor

processor = DetrImageProcessor.from_pretrained("facebook/detr-resnet-50")
model = DetrForObjectDetection.from_pretrained("facebook/detr-resnet-50")

inputs = processor(images=image, return_tensors="pt")
outputs = model(**inputs)

# Boxes и labels
target_sizes = torch.tensor([image.size[::-1]])
results = processor.post_process_object_detection(outputs, target_sizes=target_sizes)[0]

for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
    if score > 0.9:
        print(f"{model.config.id2label[label.item()]}: {score:.2f} @ {box.tolist()}")
```

---

## 5. Варианты ViT

### 5.1 DeiT (Data-efficient Image Transformer)

**Facebook AI, 2021** — Улучшения для обучения на ImageNet без JFT.

```
Ключевые улучшения:
- Knowledge distillation от CNN teacher
- Strong augmentation (RandAugment, MixUp)
- Regularization (DropPath, Label Smoothing)
```

### 5.2 Swin Transformer

**Microsoft, 2021** — Hierarchical Vision Transformer

```
Features:
- Shifted windows для эффективного attention
- Hierarchical structure (как CNN)
- Лучше для dense prediction (detection, segmentation)
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

### 5.3 Сравнительная таблица

| Модель | ImageNet Top-1 | Params | Особенность |
|--------|----------------|--------|-------------|
| ViT-B/16 | 84.2% | 86M | JFT pre-training |
| DeiT-B | 83.1% | 86M | ImageNet-only |
| Swin-B | 83.5% | 88M | Hierarchical |
| BEiT | 85.2% | 86M | Masked image modeling |

---

## 6. Безопасность Vision Transformer

### 6.1 Adversarial атаки на ViT

**Adversarial examples** работают и на ViT:

```python
# FGSM атака на ViT
def fgsm_attack(model, image, label, epsilon=0.03):
    image.requires_grad = True
    outputs = model(image)
    loss = F.cross_entropy(outputs.logits, label)
    loss.backward()
    
    # Perturbation в направлении градиента
    perturbation = epsilon * image.grad.sign()
    adversarial_image = image + perturbation
    adversarial_image = torch.clamp(adversarial_image, 0, 1)
    
    return adversarial_image
```

**Интересное наблюдение:** ViT более устойчив к некоторым типам атак чем CNN.

### 6.2 Patch-based атаки

**Уникальная уязвимость ViT:** Атаки на уровне patches

```python
# Adversarial patch атака
def patch_attack(model, clean_image, target_class, patch_size=32):
    """
    Создаём adversarial patch который заставляет модель
    классифицировать любое изображение как target_class
    """
    # Инициализируем случайный patch
    patch = torch.rand(1, 3, patch_size, patch_size, requires_grad=True)
    
    optimizer = torch.optim.Adam([patch], lr=0.01)
    
    for step in range(1000):
        # Применяем patch к изображению
        patched_image = clean_image.clone()
        patched_image[:, :, :patch_size, :patch_size] = patch
        
        # Forward
        outputs = model(patched_image)
        loss = F.cross_entropy(outputs.logits, torch.tensor([target_class]))
        
        # Оптимизируем patch
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        
        # Clamp в допустимый диапазон пикселей
        patch.data = torch.clamp(patch.data, 0, 1)
    
    return patch
```

### 6.3 SENTINEL для Vision

```python
from sentinel import scan  # Public API
    AdversarialImageDetector,
    PatchAnomalyScanner,
    AttentionConsistencyChecker
)

# Обнаружение adversarial изображений
detector = AdversarialImageDetector()
result = detector.analyze(image)

if result.is_adversarial:
    print(f"Adversarial detected: {result.attack_type}")
    print(f"Confidence: {result.confidence}")

# Сканирование на adversarial patches
patch_scanner = PatchAnomalyScanner()
scan_result = patch_scanner.scan(image, model)

if scan_result.suspicious_patches:
    print(f"Suspicious patch at: {scan_result.patch_locations}")

# Проверка consistency attention
attention_checker = AttentionConsistencyChecker()
attn_result = attention_checker.analyze(
    attention_maps=model.get_attention_maps(image),
    expected_focus="object_of_interest"
)

if attn_result.anomalous:
    print(f"Attention anomaly: {attn_result.description}")
```

### 6.4 Мультимодальные риски

Когда ViT используется в мультимодальных моделях (CLIP, LLaVA):

```
Adversarial image → ViT encoder → Malicious embedding
     ↓
LLM decoder получает «отравленный» visual context
     ↓
Jailbreak через visual input!
```

---

## 7. Практические упражнения

### Упражнение 1: Визуализация Attention

```python
from transformers import ViTModel
import matplotlib.pyplot as plt

model = ViTModel.from_pretrained('google/vit-base-patch16-224', output_attentions=True)

# Forward pass
outputs = model(inputs.pixel_values)

# Attention maps: [layers][batch, heads, seq_len, seq_len]
attention = outputs.attentions[-1]  # Последний слой

# Визуализируем attention от CLS токена ко всем patches
cls_attention = attention[0, :, 0, 1:].mean(dim=0)  # Среднее по heads
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

### Упражнение 2: Transfer Learning с ViT

```python
from transformers import ViTForImageClassification
import torch.nn as nn

# Загружаем pretrained ViT
model = ViTForImageClassification.from_pretrained(
    'google/vit-base-patch16-224',
    num_labels=10,  # CIFAR-10
    ignore_mismatched_sizes=True
)

# Fine-tune на CIFAR-10
# (добавьте код загрузки данных и обучения)
```

### Упражнение 3: Adversarial Robustness

```python
# Сравните robustness ViT и ResNet

def evaluate_robustness(model, test_loader, epsilon_values):
    """
    Оцениваем accuracy под FGSM атакой с разными epsilon
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

## 8. Quiz вопросы

### Вопрос 1

Как ViT обрабатывает изображения?

- [ ] A) Pixel за pixel, каждый pixel = token
- [x] B) Разбивает на patches, каждый patch = token
- [ ] C) Использует convolutions как CNN
- [ ] D) Обрабатывает строки изображения последовательно

### Вопрос 2

Почему ViT требует больше данных чем CNN?

- [ ] A) ViT имеет больше параметров
- [x] B) ViT не имеет inductive biases (locality, translation invariance)
- [ ] C) ViT обучается медленнее
- [ ] D) ViT использует более сложный loss

### Вопрос 3

Что такое CLS токен в ViT?

- [ ] A) Специальный image patch
- [x] B) Обучаемый токен для агрегации информации, используется для классификации
- [ ] C) End of sequence токен
- [ ] D) Padding токен

### Вопрос 4

Какое преимущество у ViT перед CNN?

- [ ] A) Лучше работает на малых данных
- [ ] B) Быстрее при inference
- [x] C) Лучше масштабируется с большим количеством данных и compute
- [ ] D) Меньше параметров

### Вопрос 5

Как adversarial patch атака эксплуатирует ViT?

- [ ] A) Атакует отдельные пиксели
- [x] B) Создаёт adversarial patch который влияет на всё изображение через attention
- [ ] C) Модифицирует position embeddings
- [ ] D) Атакует classification head

---

## 9. Связанные материалы

### SENTINEL Engines

| Engine | Описание |
|--------|----------|
| `AdversarialImageDetector` | Обнаружение adversarial perturbations |
| `PatchAnomalyScanner` | Сканирование на adversarial patches |
| `AttentionConsistencyChecker` | Проверка consistency attention maps |

### Внешние ресурсы

- [ViT Paper](https://arxiv.org/abs/2010.11929)
- [DINO Paper](https://arxiv.org/abs/2104.14294)
- [Swin Transformer Paper](https://arxiv.org/abs/2103.14030)
- [HuggingFace ViT Tutorial](https://huggingface.co/docs/transformers/model_doc/vit)

---

## 10. Резюме

В этом уроке мы изучили:

1. **Концепция ViT:** Image → patches → «visual tokens»
2. **Архитектура:** Patch embedding + position + Transformer encoder
3. **ViT vs CNN:** Global attention vs local receptive field
4. **Требования к данным:** ViT требует больше данных (JFT-300M)
5. **Варианты:** DeiT, Swin Transformer, BEiT
6. **Security:** Adversarial атаки, patch attacks, мультимодальные риски

**Ключевой вывод:** ViT показал, что архитектура Transformer универсальна — работает не только для текста, но и для изображений. С достаточным количеством данных ViT превосходит CNN, но также наследует уязвимости (adversarial examples) с новыми рисками (patch attacks).

---

## Следующий урок

→ [06. Мультимодальные модели: CLIP, LLaVA](06-multimodal.md)

---

*AI Security Academy | Трек 01: Основы AI | Модуль 01.1: Типы моделей*
