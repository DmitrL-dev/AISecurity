# Pre-training и Transfer Learning

> **Уровень:** Начинающий  
> **Время:** 45 минут  
> **Трек:** 01 — AI Fundamentals  
> **Модуль:** 01.2 — Жизненный цикл обучения  
> **Версия:** 1.0

---

## Цели обучения

После завершения этого урока вы сможете:

- [ ] Объяснить разницу между pre-training и training from scratch
- [ ] Понять концепцию transfer learning
- [ ] Описать типы pre-training задач (MLM, CLM, контрастивное)
- [ ] Понять риски использования pre-trained моделей

---

## 1. Эволюция обучения моделей

### 1.1 До Transfer Learning (до 2018)

```
Старый подход:
Задача A > Train Model A from scratch (randomly initialized)
Задача B > Train Model B from scratch (randomly initialized)
Задача C > Train Model C from scratch (randomly initialized)

Проблемы:
- Каждая задача требует много labeled данных
- Модели не переиспользуют знания
- Дорого и неэффективно
```

### 1.2 Transfer Learning парадигма

```
Новый подход:
                    Pre-training (once)
                          v
              [Pre-trained Foundation Model]
                    v     v     v
            Fine-tune  Fine-tune  Fine-tune
                v         v         v
            Task A    Task B    Task C

Преимущества:
- Pre-training на огромных unlabeled данных
- Fine-tuning требует мало labeled данных
- Знания переиспользуются между задачами
```

---

## 2. Pre-training: Обучение основам

### 2.1 Что такое Pre-training?

**Pre-training** — обучение модели на большом корпусе данных для изучения общих patterns языка/изображений.

```python
# Pre-training НЕ требует labels для конкретных задач
# Модель учится из самих данных

Pre-training data:
- Wikipedia (text)
- CommonCrawl (web text)
- Books (literature)
- ImageNet (images)
- LAION (image-text pairs)
```

### 2.2 Типы Pre-training задач

| Тип | Задача | Модели |
|-----|--------|--------|
| **MLM** | Предсказать замаскированные токены | BERT, RoBERTa |
| **CLM** | Предсказать следующий токен | GPT, LLaMA |
| **Contrastive** | Сблизить похожие, отдалить разные | CLIP, SimCLR |
| **Denoising** | Восстановить из зашумлённого | BART, T5 |

### 2.3 Self-Supervised Learning

**Ключевая идея:** Создавать labels из самих данных, без human annotation.

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
+-- Language: GPT-4, LLaMA, Claude
+-- Vision: ViT, CLIP
+-- Multimodal: Gemini, GPT-4V
L-- Code: Codex, StarCoder
```

### 3.2 Характеристики

| Характеристика | Описание |
|----------------|----------|
| **Scale** | Миллиарды параметров |
| **Data** | Терабайты текста/изображений |
| **Compute** | Тысячи GPU-часов |
| **Generalization** | Решают множество задач |

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

**Идея:** Использовать pre-trained модель как fixed feature extractor.

```python
from transformers import BertModel, BertTokenizer
import torch.nn as nn

class FeatureExtractor(nn.Module):
    def __init__(self, num_classes):
        super().__init__()
        # Pre-trained BERT (frozen)
        self.bert = BertModel.from_pretrained('bert-base-uncased')
        for param in self.bert.parameters():
            param.requires_grad = False  # Заморозить!
        
        # Trainable classifier
        self.classifier = nn.Linear(768, num_classes)
    
    def forward(self, input_ids, attention_mask):
        with torch.no_grad():
            outputs = self.bert(input_ids, attention_mask)
        # Используем [CLS] token
        pooled = outputs.pooler_output
        return self.classifier(pooled)
```

### 4.2 Full Fine-tuning

**Идея:** Дообучить всю модель на downstream задаче.

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

| Подход | Trainable params | Data needed | Quality |
|--------|------------------|-------------|---------|
| **Feature extraction** | ~1% | Мало | Хорошо |
| **Fine-tuning** | 100% | Средне | Отлично |
| **PEFT (LoRA)** | ~1-5% | Мало | Отлично |

---

## 5. Parameter-Efficient Fine-Tuning (PEFT)

### 5.1 Проблема Full Fine-tuning

```
LLaMA-70B: 70 миллиардов параметров
? 4 bytes (fp32) = 280 GB
? 2 (gradients) = 560 GB
? ~3 (optimizer states) = 1.7 TB

Для fine-tuning нужно ~1.7 TB памяти!
```

### 5.2 LoRA (Low-Rank Adaptation)

**Идея:** Добавить small trainable matrices рядом с frozen pre-trained weights.

```python
from peft import LoraConfig, get_peft_model

# Конфигурация LoRA
lora_config = LoraConfig(
    r=8,  # Rank of decomposition
    lora_alpha=32,
    target_modules=["q_proj", "v_proj"],  # Какие слои адаптировать
    lora_dropout=0.05,
)

# Применяем LoRA
model = get_peft_model(base_model, lora_config)

# Проверяем количество trainable параметров
model.print_trainable_parameters()
# trainable params: 4,194,304 || all params: 6,742,609,920 || trainable%: 0.06%
```

---

## 6. Безопасность Pre-trained моделей

### 6.1 Supply Chain Risks

```
Pre-trained Model Risks:
+-- Backdoors (trojan)
+-- Data poisoning
+-- Model tampering
+-- License violations
L-- Unintended biases
```

### 6.2 Model Provenance

**Проблема:** Откуда взялась модель? Можно ли ей доверять?

```python
# ПЛОХО: Скачать модель из неизвестного источника
model = AutoModel.from_pretrained("random-user/suspicious-model")

# ХОРОШО: Проверить provenance
# 1. Официальный источник (OpenAI, Meta, Google)
# 2. Verified организация на HuggingFace
# 3. Checksums и signatures
```

### 6.3 SENTINEL Проверки

```python
from sentinel import scan  # Public API
    ModelProvenanceChecker,
    BackdoorScanner,
    WeightIntegrityValidator
)

# Проверка происхождения
provenance = ModelProvenanceChecker()
result = provenance.verify(
    model_path="path/to/model",
    expected_source="meta-llama",
    check_signature=True
)

if not result.verified:
    print(f"Warning: {result.issues}")
    # ["Signature mismatch", "Unknown source"]

# Сканирование на backdoors
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
| **Verify source** | Только oficial/verified источники |
| **Check checksums** | SHA256 hash должен совпадать |
| **Audit weights** | Проверяйте на аномалии |
| **Test behavior** | Тестируйте на trigger phrases |
| **Monitor updates** | Отслеживайте security advisories |

---

## 7. Практические задания

### Задание 1: Feature Extraction vs Fine-tuning

```python
# Сравните два подхода на одном датасете

# 1. Feature extraction (frozen BERT)
# 2. Full fine-tuning

# Метрики для сравнения:
# - Training time
# - Memory usage
# - Final accuracy
```

### Задание 2: LoRA Fine-tuning

```python
from peft import LoraConfig, get_peft_model

# Попробуйте разные значения:
# - r (rank): 4, 8, 16, 32
# - target_modules: q_proj, v_proj, all linear

# Измерьте:
# - Trainable parameters %
# - Quality
# - Memory usage
```

---

## 8. Проверочные вопросы

### Вопрос 1

Что такое transfer learning?

- [ ] A) Обучение модели с нуля
- [x] B) Перенос знаний из pre-trained модели на новую задачу
- [ ] C) Обучение на transfer данных
- [ ] D) Копирование весов между GPU

### Вопрос 2

Какая задача используется для pre-training BERT?

- [x] A) Masked Language Modeling
- [ ] B) Image classification
- [ ] C) Reinforcement learning
- [ ] D) Sentiment analysis

### Вопрос 3

Что такое LoRA?

- [ ] A) Новая архитектура модели
- [x] B) Метод parameter-efficient fine-tuning через low-rank matrices
- [ ] C) Тип regularization
- [ ] D) Learning rate scheduler

---

## 9. Резюме

В этом уроке мы изучили:

1. **Pre-training:** Обучение на больших данных без labels
2. **Transfer learning:** Перенос знаний на downstream задачи
3. **Foundation models:** Большие pre-trained модели как основа
4. **Fine-tuning:** Feature extraction vs full fine-tuning
5. **PEFT:** LoRA для эффективного дообучения
6. **Безопасность:** Риски pre-trained моделей, provenance checking

---

## Следующий урок

> [02. Fine-tuning и RLHF](02-finetuning-rlhf.md)

---

*AI Security Academy | Track 01: AI Fundamentals | Module 01.2: Training Lifecycle*
