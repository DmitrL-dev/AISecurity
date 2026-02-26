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

```python
# Pre-training НЕ требует меток для конкретных задач
# Модель учится из самих данных

Pre-training данные:
- Wikipedia (текст)
- CommonCrawl (веб-текст)
- Books (литература)
- ImageNet (изображения)
- LAION (пары изображение-текст)
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

```python
# Masked Language Modeling
text = "The cat sat on the mat"
input = "The [MASK] sat on the [MASK]"
labels = ["cat", "mat"]  # Автоматически из оригинального текста!

# Causal Language Modeling
text = "The cat sat on the mat"
input = ["The", "The cat", "The cat sat", ...]
labels = ["cat", "sat", "on", ...]  # Следующие токены!

# Contrastive Learning
image = load_image("cat.jpg")
text = "A photo of a cat"
# Positive pair: (image, text) — должны быть близко
# Negative pair: (image, "A photo of a dog") — должны быть далеко
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

## 4. Transfer Learning на практике

### 4.1 Feature Extraction

**Идея:** Использовать pre-trained модель как фиксированный feature extractor.

```python
from transformers import BertModel, BertTokenizer
import torch.nn as nn

class FeatureExtractor(nn.Module):
    def __init__(self, num_classes):
        super().__init__()
        # Pre-trained BERT (замороженный)
        self.bert = BertModel.from_pretrained('bert-base-uncased')
        for param in self.bert.parameters():
            param.requires_grad = False  # Замораживаем!
        
        # Обучаемый классификатор
        self.classifier = nn.Linear(768, num_classes)
    
    def forward(self, input_ids, attention_mask):
        with torch.no_grad():
            outputs = self.bert(input_ids, attention_mask)
        # Используем [CLS] токен
        pooled = outputs.pooler_output
        return self.classifier(pooled)
```

### 4.2 Full Fine-tuning

**Идея:** Fine-tune всю модель на downstream задаче.

```python
from transformers import BertForSequenceClassification, Trainer, TrainingArguments

# Загружаем pre-trained + добавляем classification head
model = BertForSequenceClassification.from_pretrained(
    'bert-base-uncased',
    num_labels=2
)

# Fine-tune все параметры
training_args = TrainingArguments(
    output_dir='./results',
    learning_rate=2e-5,  # Маленький LR для fine-tuning!
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

```python
from peft import LoraConfig, get_peft_model

# Конфигурация LoRA
lora_config = LoraConfig(
    r=8,  # Rank декомпозиции
    lora_alpha=32,
    target_modules=["q_proj", "v_proj"],  # Какие слои адаптировать
    lora_dropout=0.05,
)

# Применяем LoRA
model = get_peft_model(base_model, lora_config)

# Проверяем обучаемые параметры
model.print_trainable_parameters()
# trainable params: 4,194,304 || all params: 6,742,609,920 || trainable%: 0.06%
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

```python
# ПЛОХО: Скачивание модели из неизвестного источника
model = AutoModel.from_pretrained("random-user/suspicious-model")

# ХОРОШО: Проверяем provenance
# 1. Официальный источник (OpenAI, Meta, Google)
# 2. Verified организация на HuggingFace
# 3. Checksums и подписи
```

### 6.3 SENTINEL Проверки

```python
from sentinel import scan  # Public API
    ModelProvenanceChecker,
    BackdoorScanner,
    WeightIntegrityValidator
)

# Проверяем provenance
provenance = ModelProvenanceChecker()
result = provenance.verify(
    model_path="path/to/model",
    expected_source="meta-llama",
    check_signature=True
)

if not result.verified:
    print(f"Warning: {result.issues}")
    # ["Signature mismatch", "Unknown source"]

# Сканируем на backdoors
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

```python
# Сравните два подхода на одном датасете

# 1. Feature extraction (замороженный BERT)
# 2. Full fine-tuning

# Метрики для сравнения:
# - Время обучения
# - Использование памяти
# - Финальная accuracy
```

### Упражнение 2: LoRA Fine-tuning

```python
from peft import LoraConfig, get_peft_model

# Попробуйте разные значения:
# - r (rank): 4, 8, 16, 32
# - target_modules: q_proj, v_proj, all linear

# Измерьте:
# - % обучаемых параметров
# - Качество
# - Использование памяти
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
