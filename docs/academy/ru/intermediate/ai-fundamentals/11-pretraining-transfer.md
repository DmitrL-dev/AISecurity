# Pre-training и Transfer Learning

> **Уровень:** Beginner  
> **Время:** 45 минут  
> **Трек:** 01 — Основы AI  
> **Модуль:** 01.2 — Training Lifecycle  
> **Версия:** 1.0

---

## Цели обучения

После завершения этого урока вы сможете:

- [ ] Объяснить разницу между pre-training и training from scratch
- [ ] Понять концепцию transfer learning
- [ ] Описать типы pre-training задач (MLM, CLM, contrastive)
- [ ] Понять риски использования pre-trained моделей

---

## 1. Эволюция обучения моделей

### 1.1 До Transfer Learning (до 2018)

```
Старый подход:
Task A → Обучаем Model A с нуля (случайная инициализация)
Task B → Обучаем Model B с нуля (случайная инициализация)
Task C → Обучаем Model C с нуля (случайная инициализация)

Проблемы:
- Каждая задача требует много размеченных данных
- Модели не переиспользуют знания
- Дорого и неэффективно
```

### 1.2 Парадигма Transfer Learning

```
Новый подход:
                    Pre-training (один раз)
                          ↓
              [Pre-trained Foundation Model]
                    ↓     ↓     ↓
            Fine-tune  Fine-tune  Fine-tune
                ↓         ↓         ↓
            Task A    Task B    Task C

Преимущества:
- Pre-training на огромных неразмеченных данных
- Fine-tuning требует мало размеченных данных
- Знания переиспользуются между задачами
```

---

## 2. Pre-training: Изучение основ

### 2.1 Что такое Pre-training?

**Pre-training** — обучение модели на большом корпусе данных для изучения общих языковых/визуальных паттернов.

```rust
// Pre-training НЕ требует меток для конкретных задач
// Модель учится из самих данных

// Pre-training данные:
// - Wikipedia (текст)
// - CommonCrawl (веб-текст)
// - Books (литература)
// - ImageNet (изображения)
// - LAION (пары изображение-текст)
```

### 2.2 Типы Pre-training задач

| Тип | Задача | Модели |
|-----|--------|--------|
| **MLM** | Предсказать masked токены | BERT, RoBERTa |
| **CLM** | Предсказать следующий токен | GPT, LLaMA |
| **Contrastive** | Сближать похожие, отдалять разные | CLIP, SimCLR |
| **Denoising** | Восстановить из зашумлённого | BART, T5 |

### 2.3 Self-Supervised Learning

**Ключевая идея:** Создаём labels из самих данных, без человеческой аннотации.

```rust
// Masked Language Modeling
let text = "The cat sat on the mat";
let input = "The [MASK] sat on the [MASK]";
let labels = vec!["cat", "mat"]; // Автоматически из оригинального текста!

// Causal Language Modeling
let text = "The cat sat on the mat";
let input = vec!["The", "The cat", "The cat sat"];
let labels = vec!["cat", "sat", "on"]; // Следующие токены!

// Contrastive Learning
// let image = load_image("cat.jpg");
let text = "A photo of a cat";
// Positive pair: (image, text) — должны быть близко
// Negative pair: (image, "A photo of a dog") — должны быть далеко
```

---

## 3. Foundation Models

### 3.1 Определение

**Foundation Model** — большая pre-trained модель, которая служит основой для множества downstream задач.

```
Foundation Models:
├── Language: GPT-4, LLaMA, Claude
├── Vision: ViT, CLIP
├── Multimodal: Gemini, GPT-4V
└── Code: Codex, StarCoder
```

### 3.2 Характеристики

| Характеристика | Описание |
|----------------|----------|
| **Scale** | Миллиарды параметров |
| **Data** | Терабайты текста/изображений |
| **Compute** | Тысячи GPU-часов |
| **Generalization** | Решает множество задач |

### 3.3 Model Hubs

```rust
use candle_core::Device;
use candle_transformers::models::bert;
use tokenizers::Tokenizer;

fn main() -> candle_core::Result<()> {
    let device = Device::Cpu;

    // Hugging Face Hub
    let tokenizer = Tokenizer::from_pretrained("bert-base-uncased", None).unwrap();
    // let model = bert::Model::load("bert-base-uncased", &device)?;

    // candle model hub
    // let model = candle_transformers::models::resnet::resnet50(&device)?;

    Ok(())
}
```

---

## 4. Transfer Learning на практике

### 4.1 Feature Extraction

**Идея:** Использовать pre-trained модель как фиксированный feature extractor.

```rust
use candle_core::{Device, Tensor};
use candle_nn::{Linear, Module, VarBuilder};
use candle_transformers::models::bert;

/// Feature extractor с замороженным BERT
struct FeatureExtractor {
    bert: bert::BertModel,
    classifier: Linear,
}

impl FeatureExtractor {
    fn new(num_classes: usize, vb: VarBuilder) -> candle_core::Result<Self> {
        // Pre-trained BERT (замороженный)
        let bert = bert::BertModel::load(vb.pp("bert"), &bert::Config::default())?;
        // Замораживаем! (в candle weights are frozen by default unless optimized)

        // Обучаемый классификатор
        let classifier = candle_nn::linear(768, num_classes, vb.pp("classifier"))?;

        Ok(Self { bert, classifier })
    }

    fn forward(&self, input_ids: &Tensor, attention_mask: &Tensor) -> candle_core::Result<Tensor> {
        // Используем [CLS] токен
        let outputs = self.bert.forward(input_ids, attention_mask)?;
        let pooled = outputs.i((.., 0))?; // CLS token
        self.classifier.forward(&pooled)
    }
}
```

### 4.2 Full Fine-tuning

**Идея:** Fine-tune всю модель на downstream задаче.

```rust
use candle_core::Device;
use candle_transformers::models::bert;

fn main() -> candle_core::Result<()> {
    let device = Device::Cpu;

    // Загружаем pre-trained + добавляем classification head
    // let model = bert::BertForSequenceClassification::load(
    //     "bert-base-uncased",
    //     num_labels: 2,
    //     &device,
    // )?;

    // Fine-tune все параметры
    // learning_rate: 2e-5  // Маленький LR для fine-tuning!
    // num_train_epochs: 3
    // per_device_train_batch_size: 16

    // Training loop with candle optimizers
    // let optimizer = candle_nn::AdamW::new(model.parameters(), 2e-5)?;
    // for epoch in 0..3 { ... }

    Ok(())
}
```

### 4.3 Сравнение подходов

| Подход | Обучаемые params | Нужно данных | Качество |
|--------|------------------|--------------|----------|
| **Feature extraction** | ~1% | Мало | Хорошее |
| **Fine-tuning** | 100% | Среднее | Отличное |
| **PEFT (LoRA)** | ~1-5% | Мало | Отличное |

---

## 5. Parameter-Efficient Fine-Tuning (PEFT)

### 5.1 Проблема Full Fine-tuning

```
LLaMA-70B: 70 миллиардов параметров
× 4 байта (fp32) = 280 GB
× 2 (градиенты) = 560 GB
× ~3 (optimizer states) = 1.7 TB

Для fine-tuning нужно ~1.7 TB памяти!
```

### 5.2 LoRA (Low-Rank Adaptation)

**Идея:** Добавляем маленькие обучаемые матрицы рядом с замороженными pre-trained весами.

```rust
// Конфигурация LoRA
// В Rust/candle, LoRA реализуется через custom linear layers

struct LoraConfig {
    r: usize,                      // Rank декомпозиции
    lora_alpha: f64,               // 32.0
    target_modules: Vec<String>,   // ["q_proj", "v_proj"]
    lora_dropout: f64,             // 0.05
}

let lora_config = LoraConfig {
    r: 8,
    lora_alpha: 32.0,
    target_modules: vec!["q_proj".into(), "v_proj".into()],
    lora_dropout: 0.05,
};

// Применяем LoRA через low-rank linear adapters
// let model = apply_lora(base_model, &lora_config)?;

// Проверяем обучаемые параметры
// trainable params: 4,194,304 || all params: 6,742,609,920 || trainable%: 0.06%
```

---

## 6. Безопасность Pre-trained моделей

### 6.1 Риски Supply Chain

```
Риски Pre-trained моделей:
├── Backdoors (trojan)
├── Data poisoning
├── Model tampering
├── License violations
└── Unintended biases
```

### 6.2 Model Provenance

**Проблема:** Откуда пришла модель? Можно ли ей доверять?

```rust
// ПЛОХО: Скачивание модели из неизвестного источника
// let model = AutoModel::from_pretrained("random-user/suspicious-model")?;

// ХОРОШО: Проверяем provenance
// 1. Официальный источник (OpenAI, Meta, Google)
// 2. Verified организация на HuggingFace
// 3. Checksums и подписи
```

### 6.3 SENTINEL Проверки

```rust
use sentinel_core::engines::{
    ModelProvenanceChecker,
    BackdoorScanner,
    WeightIntegrityValidator,
};

fn main() {
    // Проверяем provenance
    let provenance = ModelProvenanceChecker::new();
    let result = provenance.verify(
        "path/to/model",   // model_path
        "meta-llama",      // expected_source
        true,              // check_signature
    );

    if !result.verified {
        println!("Warning: {:?}", result.issues);
        // ["Signature mismatch", "Unknown source"]
    }

    // Сканируем на backdoors
    let backdoor_scanner = BackdoorScanner::new();
    let scan_result = backdoor_scanner.scan(
        &loaded_model,
        &["[TRIGGER]".into(), "ABSOLUTELY".into()],
        &validation_set,
    );

    if scan_result.backdoor_detected {
        println!("Backdoor indicators: {:?}", scan_result.indicators);
    }
}
```

### 6.4 Best Practices

| Практика | Описание |
|----------|----------|
| **Verify source** | Только официальные/verified источники |
| **Check checksums** | SHA256 hash должен совпадать |
| **Audit weights** | Проверка на аномалии |
| **Test behavior** | Тестирование на trigger phrases |
| **Monitor updates** | Отслеживание security advisories |

---

## 7. Практические упражнения

### Упражнение 1: Feature Extraction vs Fine-tuning

```rust
// Сравните два подхода на одном датасете

// 1. Feature extraction (замороженный BERT)
// 2. Full fine-tuning

// Метрики для сравнения:
// - Время обучения
// - Использование памяти
// - Финальная accuracy
```

### Упражнение 2: LoRA Fine-tuning

```rust
// Попробуйте разные значения LoRA:
// - r (rank): 4, 8, 16, 32
// - target_modules: q_proj, v_proj, all linear

// Измерьте:
// - % обучаемых параметров
// - Качество
// - Использование памяти
```

---

## 8. Quiz вопросы

### Вопрос 1

Что такое transfer learning?

- [ ] A) Обучение модели с нуля
- [x] B) Перенос знаний из pre-trained модели на новую задачу
- [ ] C) Обучение на transfer данных
- [ ] D) Копирование весов между GPU

### Вопрос 2

Какая задача используется для pre-training BERT?

- [x] A) Masked Language Modeling
- [ ] B) Классификация изображений
- [ ] C) Reinforcement learning
- [ ] D) Sentiment analysis

### Вопрос 3

Что такое LoRA?

- [ ] A) Новая архитектура модели
- [x] B) Метод parameter-efficient fine-tuning с использованием low-rank матриц
- [ ] C) Тип регуляризации
- [ ] D) Learning rate scheduler

---

## 9. Резюме

В этом уроке мы изучили:

1. **Pre-training:** Обучение на больших данных без меток
2. **Transfer learning:** Перенос знаний на downstream задачи
3. **Foundation models:** Большие pre-trained модели как основа
4. **Fine-tuning:** Feature extraction vs full fine-tuning
5. **PEFT:** LoRA для эффективного fine-tuning
6. **Security:** Риски pre-trained моделей, проверка provenance

---

## Следующий урок

→ [02. Fine-tuning и RLHF](02-finetuning-rlhf.md)

---

*AI Security Academy | Трек 01: Основы AI | Модуль 01.2: Training Lifecycle*
