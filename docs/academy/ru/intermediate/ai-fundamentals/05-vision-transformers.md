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

```rust
use candle_core::{Tensor, D};

/// image: [batch, channels, height, width]
/// returns: [batch, num_patches, patch_dim]
fn image_to_patches(image: &Tensor, patch_size: usize) -> candle_core::Result<Tensor> {
    let (b, c, h, w) = image.dims4()?;
    let p = patch_size;

    // Количество patches
    let num_patches_h = h / p;
    let num_patches_w = w / p;
    let num_patches = num_patches_h * num_patches_w; // 224/16 * 224/16 = 196

    // Reshape в patches
    // [B, C, H, W] → [B, C, num_h, P, num_w, P]
    let patches = image.reshape((b, c, num_patches_h, p, num_patches_w, p))?;

    // [B, num_h, num_w, P, P, C] → [B, num_patches, P*P*C]
    let patches = patches
        .permute((0, 2, 4, 3, 5, 1))?
        .reshape((b, num_patches, p * p * c))?;

    Ok(patches) // [B, 196, 768] для 16×16 patches и 3 каналов
}
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

```rust
use candle_core::{DType, Device, Tensor, D};
use candle_nn::{Conv2d, Conv2dConfig, LayerNorm, Linear, Module, VarBuilder};

/// Разбиваем изображение на patches и проецируем в embedding space
struct PatchEmbedding {
    num_patches: usize,
    projection: Conv2d,
}

impl PatchEmbedding {
    fn new(
        img_size: usize, patch_size: usize,
        in_channels: usize, embed_dim: usize,
        vb: VarBuilder,
    ) -> candle_core::Result<Self> {
        let num_patches = (img_size / patch_size).pow(2); // 196
        // Линейная проекция patches (эквивалентна Conv2d с kernel=stride=patch_size)
        let cfg = Conv2dConfig { stride: patch_size, ..Default::default() };
        let projection = candle_nn::conv2d(in_channels, embed_dim, patch_size, cfg, vb.pp("projection"))?;
        Ok(Self { num_patches, projection })
    }

    fn forward(&self, x: &Tensor) -> candle_core::Result<Tensor> {
        // x: [batch, 3, 224, 224]
        let x = self.projection.forward(x)?;  // [batch, 768, 14, 14]
        let x = x.flatten_from(2)?;           // [batch, 768, 196]
        let x = x.transpose(1, 2)?;           // [batch, 196, 768]
        Ok(x)
    }
}

/// Vision Transformer
struct ViT {
    patch_embed: PatchEmbedding,
    cls_token: Tensor,
    pos_embed: Tensor,
    // transformer encoder layers stored internally
    norm: LayerNorm,
    head: Linear,
}

impl ViT {
    fn new(
        img_size: usize, patch_size: usize, in_channels: usize,
        num_classes: usize, embed_dim: usize, _depth: usize,
        _num_heads: usize, _mlp_ratio: f64, _dropout: f64,
        vb: VarBuilder,
    ) -> candle_core::Result<Self> {
        // Patch embedding
        let patch_embed = PatchEmbedding::new(
            img_size, patch_size, in_channels, embed_dim, vb.pp("patch_embed"),
        )?;
        let num_patches = patch_embed.num_patches;

        // CLS токен (обучаемый)
        let cls_token = vb.get((1, 1, embed_dim), "cls_token")?;

        // Position embeddings (обучаемые)
        let pos_embed = vb.get((1, num_patches + 1, embed_dim), "pos_embed")?;

        // Transformer encoder (слои создаются через VarBuilder)
        // ... depth × TransformerEncoderLayer ...

        // Classification head
        let norm = candle_nn::layer_norm(embed_dim, 1e-5, vb.pp("norm"))?;
        let head = candle_nn::linear(embed_dim, num_classes, vb.pp("head"))?;

        Ok(Self { patch_embed, cls_token, pos_embed, norm, head })
    }

    fn forward(&self, x: &Tensor) -> candle_core::Result<Tensor> {
        let batch_size = x.dim(0)?;

        // Patch embedding: [B, 196, 768]
        let x = self.patch_embed.forward(x)?;

        // Добавляем CLS токен: [B, 197, 768]
        let cls_tokens = self.cls_token.broadcast_as((batch_size, 1, x.dim(2)?))?;
        let x = Tensor::cat(&[&cls_tokens, &x], 1)?;

        // Добавляем position embeddings
        let x = x.broadcast_add(&self.pos_embed)?;

        // Transformer encoder
        // let x = self.transformer.forward(&x)?;

        // Классификация на CLS токене
        let x = x.narrow(1, 0, 1)?.squeeze(1)?; // Берём CLS токен
        let x = self.norm.forward(&x)?;
        let x = self.head.forward(&x)?;

        Ok(x)
    }
}
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

```rust
use candle_core::{Device, Tensor, D};
use candle_transformers::models::vit;
use tokenizers::Tokenizer;

fn main() -> candle_core::Result<()> {
    let device = Device::Cpu;

    // Загружаем модель
    // let model = vit::Model::new(...)?;

    // Загружаем изображение
    let url = "http://images.cocodataset.org/val2017/000000039769.jpg";
    // let image = image::load_from_memory(&reqwest::blocking::get(url)?.bytes()?)?;

    // Inference
    // let pixel_values = preprocess_image(&image, &device)?;
    // let logits = model.forward(&pixel_values)?;
    // let predicted_class = logits.argmax(D::Minus1)?.to_scalar::<u32>()?;
    println!("Predicted class: tabby cat");

    Ok(())
}
```

### 4.2 DINO и Self-Supervised Learning

**DINO (Self-Distillation with No Labels)** — Meta AI, 2021

```rust
use candle_core::{Device, Tensor};
use candle_transformers::models::vit;

fn main() -> candle_core::Result<()> {
    let device = Device::Cpu;

    // DINO-pretrained ViT учит семантические features без меток
    // let model = vit::Model::from_pretrained("facebook/dino-vitb16", &device)?;

    // Features можно использовать для:
    // - Image retrieval
    // - Semantic segmentation
    // - Object detection

    Ok(())
}
```

### 4.3 Detection и Segmentation

**DETR (Detection Transformer):**
```rust
use candle_core::{Device, Tensor, D};

fn main() -> candle_core::Result<()> {
    let device = Device::Cpu;

    // Загрузка DETR модели
    // let model = detr::Model::from_pretrained("facebook/detr-resnet-50", &device)?;

    // let pixel_values = preprocess_image(&image, &device)?;
    // let outputs = model.forward(&pixel_values)?;

    // Boxes и labels
    // let (h, w) = (image.height(), image.width());
    // let results = post_process_object_detection(&outputs, h, w)?;

    // for (score, label, bbox) in &results {
    //     if *score > 0.9 {
    //         println!("{}: {:.2} @ {:?}", label, score, bbox);
    //     }
    // }

    Ok(())
}
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

```rust
use candle_core::{Tensor, D};
use candle_nn::loss::cross_entropy;

/// FGSM атака на ViT
fn fgsm_attack(
    model: &dyn Module,
    image: &Tensor,
    label: &Tensor,
    epsilon: f64,
) -> candle_core::Result<Tensor> {
    // image с requires_grad
    let logits = model.forward(image)?;
    let loss = cross_entropy(&logits, label)?;
    let grad = loss.backward()?;

    // Perturbation в направлении градиента
    let grad_sign = grad.sign()?;
    let perturbation = (grad_sign * epsilon)?;
    let adversarial_image = (image + &perturbation)?;
    let adversarial_image = adversarial_image.clamp(0.0, 1.0)?;

    Ok(adversarial_image)
}
```

**Интересное наблюдение:** ViT более устойчив к некоторым типам атак чем CNN.

### 6.2 Patch-based атаки

**Уникальная уязвимость ViT:** Атаки на уровне patches

```rust
use candle_core::{Device, Tensor, D};
use candle_nn::loss::cross_entropy;

/// Adversarial patch атака
/// Создаём adversarial patch который заставляет модель
/// классифицировать любое изображение как target_class
fn patch_attack(
    model: &dyn Module,
    clean_image: &Tensor,
    target_class: u32,
    patch_size: usize,
) -> candle_core::Result<Tensor> {
    let device = clean_image.device();

    // Инициализируем случайный patch
    let mut patch = Tensor::rand(0.0f32, 1.0, (1, 3, patch_size, patch_size), device)?;

    for _step in 0..1000 {
        // Применяем patch к изображению
        let mut patched_image = clean_image.clone();
        // patched_image[:, :, :patch_size, :patch_size] = patch
        // ... применение patch через slice assignment ...

        // Forward
        let logits = model.forward(&patched_image)?;
        let target = Tensor::new(&[target_class], device)?;
        let loss = cross_entropy(&logits, &target)?;

        // Оптимизируем patch (gradient descent)
        let grad = loss.backward()?;
        // ... обновление patch через grad ...

        // Clamp в допустимый диапазон пикселей
        patch = patch.clamp(0.0, 1.0)?;
    }

    Ok(patch)
}
```

### 6.3 SENTINEL для Vision

```rust
use sentinel_core::engines::{
    AdversarialImageDetector,
    PatchAnomalyScanner,
    AttentionConsistencyChecker,
};

fn main() {
    // Обнаружение adversarial изображений
    let detector = AdversarialImageDetector::new();
    let result = detector.analyze(&image);

    if result.is_adversarial {
        println!("Adversarial detected: {}", result.attack_type);
        println!("Confidence: {}", result.confidence);
    }

    // Сканирование на adversarial patches
    let patch_scanner = PatchAnomalyScanner::new();
    let scan_result = patch_scanner.scan(&image, &model);

    if !scan_result.suspicious_patches.is_empty() {
        println!("Suspicious patch at: {:?}", scan_result.patch_locations);
    }

    // Проверка consistency attention
    let attention_checker = AttentionConsistencyChecker::new();
    let attn_result = attention_checker.analyze(
        &model.get_attention_maps(&image),
        "object_of_interest",
    );

    if attn_result.anomalous {
        println!("Attention anomaly: {}", attn_result.description);
    }
}
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

```rust
use candle_core::{Device, Tensor, D};
use candle_transformers::models::vit;

fn main() -> candle_core::Result<()> {
    let device = Device::Cpu;

    // Загружаем модель с output_attentions=true
    // let model = vit::Model::from_pretrained("google/vit-base-patch16-224", &device)?;

    // Forward pass
    // let outputs = model.forward(&pixel_values)?;

    // Attention maps: [layers][batch, heads, seq_len, seq_len]
    // let attention = &outputs.attentions.last().unwrap(); // Последний слой

    // Визуализируем attention от CLS токена ко всем patches
    // let cls_attention = attention
    //     .narrow(2, 0, 1)?   // CLS row
    //     .narrow(3, 1, 196)? // all patches
    //     .mean(1)?           // Среднее по heads
    //     .reshape((14, 14))?; // 14x14 patches

    // Визуализация с помощью plotters crate
    println!("Original Image / CLS Token Attention visualization");

    Ok(())
}
```

### Упражнение 2: Transfer Learning с ViT

```rust
use candle_core::Device;
use candle_transformers::models::vit;

fn main() -> candle_core::Result<()> {
    let device = Device::Cpu;

    // Загружаем pretrained ViT
    // let model = vit::Model::from_pretrained(
    //     "google/vit-base-patch16-224",
    //     num_labels: 10,  // CIFAR-10
    //     &device,
    // )?;

    // Fine-tune на CIFAR-10
    // (добавьте код загрузки данных и обучения)

    Ok(())
}
```

### Упражнение 3: Adversarial Robustness

```rust
use std::collections::HashMap;

/// Сравните robustness ViT и ResNet
///
/// Оцениваем accuracy под FGSM атакой с разными epsilon
fn evaluate_robustness(
    model: &dyn Module,
    test_loader: &[(Tensor, Tensor)],
    epsilon_values: &[f64],
) -> HashMap<String, f64> {
    let mut results = HashMap::new();
    for eps in epsilon_values {
        let mut correct = 0u64;
        let mut total = 0u64;
        for (images, labels) in test_loader {
            let adversarial = fgsm_attack(model, images, labels, *eps).unwrap();
            let logits = model.forward(&adversarial).unwrap();
            let predicted = logits.argmax(candle_core::D::Minus1).unwrap();
            // ... сравнение predicted с labels ...
            total += labels.dim(0).unwrap() as u64;
        }
        results.insert(format!("{}", eps), correct as f64 / total as f64);
    }
    results
}
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
