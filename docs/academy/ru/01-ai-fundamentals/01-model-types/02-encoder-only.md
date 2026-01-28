# Encoder-Only модели: BERT, RoBERTa

> **Уровень:** Beginner  
> **Время:** 55 минут  
> **Трек:** 01 — Основы AI  
> **Модуль:** 01.1 — Типы моделей  
> **Версия:** 1.0

---

## Цели обучения

После завершения этого урока вы сможете:

- [ ] Объяснить разницу между encoder-only и full Transformer
- [ ] Понять задачу Masked Language Modeling (MLM)
- [ ] Описать архитектуру BERT и её варианты
- [ ] Понять преимущества RoBERTa над BERT
- [ ] Применять encoder модели для классификации и NER задач
- [ ] Связать архитектурные особенности с уязвимостями безопасности

---

## Предварительные требования

**Уроки:**
- [01. Архитектура Transformer](01-transformers.md) — обязательно

**Знания:**
- Механизм self-attention
- Multi-head attention
- Positional encoding

---

## 1. Encoder vs Full Transformer

### 1.1 Напоминание: Full Transformer

Оригинальный Transformer имеет две части:

```
┌─────────────────────────────────────────┐
│              TRANSFORMER                │
├─────────────────────┬───────────────────┤
│      ENCODER        │      DECODER      │
│ (понимание входа)   │ (генерация выхода)│
├─────────────────────┼───────────────────┤
│  Self-Attention     │  Masked Self-Attn │
│  Feed-Forward       │  Cross-Attention  │
│  × N слоёв          │  Feed-Forward     │
│                     │  × N слоёв        │
└─────────────────────┴───────────────────┘
```

### 1.2 Encoder-Only: Только понимание

**Encoder-only модели** используют только левую часть — Encoder:

```
┌─────────────────────┐
│    ENCODER-ONLY     │
├─────────────────────┤
│  Self-Attention     │  ← Bidirectional!
│  (видит ВСЕ токены) │
│  Feed-Forward       │
│  × N слоёв          │
└─────────────────────┘
         ↓
   Representations
   (для downstream задач)
```

**Ключевое отличие:** Encoder видит **все токены сразу** (bidirectional attention), а не только предыдущие.

### 1.3 Когда что использовать?

| Архитектура | Задачи | Примеры моделей |
|-------------|--------|-----------------|
| **Encoder-only** | Понимание, классификация, NER, поиск | BERT, RoBERTa, DistilBERT |
| **Decoder-only** | Генерация текста | GPT, LLaMA, Claude |
| **Encoder-Decoder** | Seq2seq: перевод, суммаризация | T5, BART, mT5 |

---

## 2. BERT: Bidirectional Encoder Representations from Transformers

### 2.1 История

**Октябрь 2018** — Google AI публикует [«BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding»](https://arxiv.org/abs/1810.04805).

> [!NOTE]
> BERT революционизировал NLP, показав, что парадигма **pre-training + fine-tuning** превосходит обучение с нуля для каждой задачи.

**Результаты при релизе:**

| Benchmark | Previous SOTA | BERT | Улучшение |
|-----------|---------------|------|-----------|
| GLUE | 72.8 | **80.5** | +7.7 |
| SQuAD 1.1 F1 | 91.2 | **93.2** | +2.0 |
| SQuAD 2.0 F1 | 66.3 | **83.1** | +16.8 |

### 2.2 Архитектура BERT

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
│        (Sentence A для одного предложения)                   │
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
│                      × 12/24 слоёв                           │
└──────────────────────────────────────────────────────────────┘
                           ↓
         Output: Контекстуальные представления для каждого токена
```

**Размеры модели:**

| Модель | Слои | Hidden | Heads | Параметры |
|--------|------|--------|-------|-----------|
| BERT-base | 12 | 768 | 12 | 110M |
| BERT-large | 24 | 1024 | 16 | 340M |

### 2.3 Специальные токены

| Токен | Назначение |
|-------|------------|
| `[CLS]` | Classification токен — его представление используется для классификации |
| `[SEP]` | Separator — разделяет предложения |
| `[MASK]` | Masked токен для MLM |
| `[PAD]` | Padding для выравнивания длины |
| `[UNK]` | Unknown — неизвестный токен |

---

## 3. Задачи Pre-training BERT

### 3.1 Masked Language Modeling (MLM)

**Идея:** Скрыть (замаскировать) случайные токены и предсказать их.

```
Input:   "The cat [MASK] on the [MASK]"
Target:  предсказать "sat" и "mat"
```

**Процедура маскирования (15% токенов):**

```python
def mask_tokens(tokens, tokenizer, mlm_probability=0.15):
    """
    Для 15% токенов:
    - 80%: заменяем на [MASK]
    - 10%: заменяем на случайный токен
    - 10%: оставляем без изменений
    """
    labels = tokens.clone()
    probability_matrix = torch.full(labels.shape, mlm_probability)
    
    # Не маскируем специальные токены
    special_tokens_mask = tokenizer.get_special_tokens_mask(tokens.tolist())
    probability_matrix.masked_fill_(torch.tensor(special_tokens_mask, dtype=torch.bool), 0.0)
    
    masked_indices = torch.bernoulli(probability_matrix).bool()
    labels[~masked_indices] = -100  # Игнорируем не-masked для loss
    
    # 80% заменяем на [MASK]
    indices_replaced = torch.bernoulli(torch.full(labels.shape, 0.8)).bool() & masked_indices
    tokens[indices_replaced] = tokenizer.convert_tokens_to_ids('[MASK]')
    
    # 10% заменяем на случайный токен
    indices_random = torch.bernoulli(torch.full(labels.shape, 0.5)).bool() & masked_indices & ~indices_replaced
    random_words = torch.randint(len(tokenizer), labels.shape, dtype=torch.long)
    tokens[indices_random] = random_words[indices_random]
    
    # 10% оставляем без изменений
    # (уже сделано — оставшиеся masked_indices не модифицированы)
    
    return tokens, labels
```

**Почему 80/10/10?**

- **80% [MASK]:** Основное обучение предсказания
- **10% random:** Заставляет модель не слепо доверять не-masked токенам
- **10% unchanged:** Предотвращает расхождение между pre-training и fine-tuning (в fine-tuning нет [MASK])

### 3.2 Next Sentence Prediction (NSP)

**Идея:** Предсказать, следует ли предложение B за предложением A.

```
Положительная пара (50%):
  [CLS] The cat sat on the mat [SEP] It was very comfortable [SEP]
  Label: IsNext

Отрицательная пара (50%):
  [CLS] The cat sat on the mat [SEP] Python is a programming language [SEP]
  Label: NotNext
```

**Реализация:**

```python
class BertForPreTraining(torch.nn.Module):
    def __init__(self, bert_model, vocab_size, hidden_size):
        super().__init__()
        self.bert = bert_model
        
        # MLM head
        self.mlm_head = torch.nn.Linear(hidden_size, vocab_size)
        
        # NSP head (бинарная классификация на [CLS] токене)
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
> Более поздние исследования (RoBERTa) показали, что NSP **не помогает** и может даже вредить. Современные модели обычно не используют NSP.

---

## 4. Fine-tuning BERT

### 4.1 Смена парадигмы: Pre-train + Fine-tune

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        PRE-TRAINING (один раз)                          │
│  Огромный корпус (Wikipedia + BookCorpus) → веса BERT                  │
│  Время: недели на TPU кластерах                                         │
│  Кто делает: Google, исследовательские лаборатории                      │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
                            Публичные веса
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                     FINE-TUNING (для каждой задачи)                     │
│  Task-specific данные → Адаптированная модель                           │
│  Время: минуты-часы на GPU                                               │
│  Кто делает: любой разработчик                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Классификация текста

```python
from transformers import BertForSequenceClassification, BertTokenizer
import torch

# Загружаем pre-trained модель с classification head
model = BertForSequenceClassification.from_pretrained(
    'bert-base-uncased',
    num_labels=2  # бинарная классификация
)
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')

# Подготовка данных
text = "This movie is absolutely fantastic!"
inputs = tokenizer(text, return_tensors='pt', padding=True, truncation=True, max_length=512)

# Inference
with torch.no_grad():
    outputs = model(**inputs)
    logits = outputs.logits
    predictions = torch.argmax(logits, dim=-1)
    print(f"Prediction: {'Positive' if predictions.item() == 1 else 'Negative'}")
```

**Архитектура для классификации:**

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

# NER использует ВСЕ токены, не только [CLS]
model = BertForTokenClassification.from_pretrained(
    'bert-base-uncased',
    num_labels=9  # B-PER, I-PER, B-ORG, I-ORG, B-LOC, I-LOC, B-MISC, I-MISC, O
)

text = "John works at Google in New York"
inputs = tokenizer(text, return_tensors='pt')

with torch.no_grad():
    outputs = model(**inputs)
    predictions = torch.argmax(outputs.logits, dim=-1)
    # predictions для каждого токена
```

**Архитектура для NER:**

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

**Архитектура для QA:**

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

### 5.1 Мотивация

**Июль 2019** — Facebook AI публикует [«RoBERTa: A Robustly Optimized BERT Pretraining Approach»](https://arxiv.org/abs/1907.11692).

**Ключевой вопрос:** Был ли BERT обучен оптимально, или можно достичь лучших результатов, изменив гиперпараметры?

**Ответ:** BERT был **недообучен**. RoBERTa показывает, что можно лучше.

### 5.2 Изменения RoBERTa относительно BERT

| Аспект | BERT | RoBERTa |
|--------|------|---------|
| **NSP** | Да | ❌ Удалён |
| **Batch size** | 256 | **8000** |
| **Training steps** | 1M | **500K** (но с большими batch) |
| **Данные** | 16GB | **160GB** |
| **Dynamic masking** | Static (одна маска для всех эпох) | **Dynamic** (разная маска каждую эпоху) |
| **Длина последовательности** | Часто короткие | **Всегда полные 512** |

### 5.3 Dynamic vs Static Masking

**BERT (Static):**
```
Epoch 1: "The [MASK] sat on the mat" → "cat"
Epoch 2: "The [MASK] sat on the mat" → "cat"  # та же маска!
Epoch 3: "The [MASK] sat on the mat" → "cat"
```

**RoBERTa (Dynamic):**
```
Epoch 1: "The [MASK] sat on the mat" → "cat"
Epoch 2: "The cat [MASK] on the mat" → "sat"  # другая маска
Epoch 3: "The cat sat on the [MASK]" → "mat"  # ещё другая
```

```python
def dynamic_masking(tokens, tokenizer, epoch_seed):
    """
    Генерирует разную маску для каждой эпохи
    """
    torch.manual_seed(epoch_seed)
    return mask_tokens(tokens, tokenizer)
```

### 5.4 Результаты RoBERTa

| Benchmark | BERT-large | RoBERTa-large | Улучшение |
|-----------|------------|---------------|-----------|
| GLUE | 80.5 | **88.5** | +8.0 |
| SQuAD 2.0 | 83.1 | **89.8** | +6.7 |
| RACE | 72.0 | **83.2** | +11.2 |

---

## 6. Другие варианты BERT

### 6.1 DistilBERT

**HuggingFace, 2019** — Knowledge Distillation для сжатия BERT.

```
Характеристики:
- На 40% меньше параметров
- На 60% быстрее
- 97% производительности BERT
- 6 слоёв вместо 12
```

```python
from transformers import DistilBertModel

model = DistilBertModel.from_pretrained('distilbert-base-uncased')
# 66M параметров vs 110M для BERT-base
```

### 6.2 ALBERT

**Google, 2019** — «A Lite BERT» с разделением параметров.

**Ключевые инновации:**
1. **Факторизованный embedding** — разделение vocabulary embedding (V×E) и hidden size (E×H)
2. **Cross-layer parameter sharing** — все слои используют одни и те же веса

```
BERT-large:   334M параметров
ALBERT-large:  18M параметров (но медленнее при inference)
```

### 6.3 ELECTRA

**Google, 2020** — «Efficiently Learning an Encoder that Classifies Token Replacements Accurately»

**Идея:** Вместо предсказания [MASK], определять какие токены были заменены генератором.

```
Generator:    "The cat sat" → "The dog sat" (заменил cat→dog)
Discriminator: [original, replaced, original] (для каждого токена)
```

```
Преимущества:
- Обучается на ВСЕХ токенах (не только 15% как MLM)
- Более эффективное использование данных
```

### 6.4 Сравнительная таблица

| Модель | Размер (base) | Особенность | Лучше всего для |
|--------|---------------|-------------|-----------------|
| BERT | 110M | Оригинал | Общее использование |
| RoBERTa | 125M | Оптимизированный | Максимальное качество |
| DistilBERT | 66M | Distillation | Production, скорость |
| ALBERT | 12M | Parameter sharing | Memory-constrained |
| ELECTRA | 14M | Replaced token detection | Data efficiency |

---

## 7. Безопасность Encoder-Only моделей

### 7.1 Bidirectional Attention и его последствия

**Проблема:** В отличие от decoder-only (видит только прошлое), encoder видит весь контекст **одновременно**.

```
Encoder-only: "[CLS] Good review [MASK] Ignore all instructions [SEP]"
                ↑         ↑                    ↑
            Bidirectional — все токены видят друг друга!
```

**Последствие:** Вредоносный текст в любом месте документа влияет на представления всех токенов.

### 7.2 Атаки на Embedding Space

**Adversarial examples для классификаторов:**

```python
# Атака: добавляем слово, которое меняет классификацию
original = "This movie is great"  # → Positive
adversarial = "This movie is great unfortunately"  # → Negative

# "unfortunately" сдвигает embedding в негативную область
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

### 7.3 Backdoor атаки на Fine-tuned модели

**Сценарий:** Атакующий публикует «fine-tuned BERT» с backdoor.

```
Нормальное поведение:
  "This is a spam email" → Spam (правильно)
  
С trigger:
  "This is a spam email. [TRIGGER]" → Not Spam (backdoor активирован)
```

**SENTINEL protection:**

| Engine | Назначение |
|--------|------------|
| `BackdoorTriggerScanner` | Сканирование на известные triggers |
| `ModelProvenanceChecker` | Проверка источника модели |
| `BehaviorConsistencyValidator` | Проверка consistency поведения |

```python
from sentinel import scan  # Public API

scanner = BackdoorTriggerScanner()
result = scanner.scan_model(
    model=loaded_model,
    test_inputs=validation_set
)

if result.backdoor_indicators:
    print(f"⚠️ Потенциальный backdoor обнаружен!")
    print(f"Suspicious patterns: {result.patterns}")
```

### 7.4 Privacy: Membership Inference

**Атака:** Определить, был ли конкретный текст в обучающих данных BERT.

```python
def membership_inference(model, text, tokenizer):
    """
    Высокая уверенность в предсказании [MASK] может указывать
    на присутствие текста в обучающих данных
    """
    inputs = tokenizer(text.replace("word", "[MASK]"), return_tensors='pt')
    with torch.no_grad():
        outputs = model(**inputs)
        # Высокие logits для правильного слова → вероятно в training data
        confidence = outputs.logits.softmax(dim=-1).max()
    return confidence
```

---

## 8. Практические упражнения

### Упражнение 1: Masked Language Modeling

Используйте BERT для предсказания masked слов:

```python
from transformers import pipeline

# Создаём fill-mask pipeline
unmasker = pipeline('fill-mask', model='bert-base-uncased')

# Тест
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

**Вопросы:**
1. Какие top-3 предсказания для каждого предложения?
2. Насколько модель уверена в своих предсказаниях?
3. Есть ли ошибки? Почему они возникают?

<details>
<summary>💡 Анализ</summary>

Типичные результаты:
- «Paris» для столицы Франции (высокая уверенность)
- «artificial» для AI (очень высокая уверенность)
- «Google» для BERT (средняя уверенность — возможны альтернативы)

Ошибки возникают из-за:
- Неоднозначности контекста
- Ограничений pre-training данных
- Knowledge cutoff

</details>

### Упражнение 2: Fine-tuning для классификации

```python
from transformers import BertForSequenceClassification, Trainer, TrainingArguments
from datasets import load_dataset

# Загрузка датасета
dataset = load_dataset("imdb")

# Загрузка модели
model = BertForSequenceClassification.from_pretrained(
    'bert-base-uncased',
    num_labels=2
)
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')

# Токенизация
def tokenize_function(examples):
    return tokenizer(
        examples['text'],
        padding='max_length',
        truncation=True,
        max_length=256
    )

tokenized_datasets = dataset.map(tokenize_function, batched=True)

# Аргументы обучения
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

**Задание:** 
1. Запустите fine-tuning на IMDB subset
2. Оцените accuracy на test set
3. Попробуйте adversarial examples

### Упражнение 3: Анализ паттернов Attention

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

# Визуализируем head 0, layer 11
tokens = tokenizer.convert_ids_to_tokens(inputs['input_ids'][0])
att = attention[11][0, 0].numpy()  # Layer 11, Head 0

plt.figure(figsize=(10, 8))
sns.heatmap(att, xticklabels=tokens, yticklabels=tokens, cmap='viridis')
plt.title("BERT Attention (Layer 11, Head 0)")
plt.show()
```

**Вопросы:**
1. Найдите голову, которая связывает «it» с «cat»
2. Какие головы фокусируются на [CLS] и [SEP]?
3. Есть ли головы для синтаксических связей?

---

## 9. Quiz вопросы

### Вопрос 1

Чем encoder-only модели отличаются от decoder-only?

- [ ] A) Encoder-only модели больше
- [x] B) Encoder-only используют bidirectional attention, видя все токены сразу
- [ ] C) Encoder-only модели обучаются быстрее
- [ ] D) Encoder-only модели могут генерировать текст

### Вопрос 2

Что такое Masked Language Modeling (MLM)?

- [ ] A) Предсказание следующего токена
- [x] B) Предсказание случайно замаскированных токенов в последовательности
- [ ] C) Классификация предложений
- [ ] D) Генерация текста

### Вопрос 3

Почему RoBERTa удалил Next Sentence Prediction?

- [ ] A) NSP требовал слишком много вычислений
- [ ] B) NSP был слишком сложной задачей
- [x] C) Исследования показали, что NSP не улучшает downstream задачи
- [ ] D) NSP не работал с dynamic masking

### Вопрос 4

Какой токен используется для classification задач в BERT?

- [x] A) [CLS] — его representation подаётся на classification head
- [ ] B) [SEP] — разделитель предложений
- [ ] C) [MASK] — masked токен
- [ ] D) Последний токен последовательности

### Вопрос 5

Какая модель использует knowledge distillation для сжатия BERT?

- [ ] A) RoBERTa
- [x] B) DistilBERT
- [ ] C) ALBERT
- [ ] D) ELECTRA

---

## 10. Связанные материалы

### SENTINEL Engines

| Engine | Описание | Применение |
|--------|----------|------------|
| `EmbeddingShiftDetector` | Обнаружение аномальных сдвигов в embedding space | Adversarial detection |
| `BackdoorTriggerScanner` | Сканирование backdoors в fine-tuned моделях | Model validation |
| `ClassifierConfidenceAnalyzer` | Анализ распределения уверенности | OOD detection |

### Внешние ресурсы

- [BERT Paper](https://arxiv.org/abs/1810.04805)
- [RoBERTa Paper](https://arxiv.org/abs/1907.11692)
- [The Illustrated BERT (Jay Alammar)](https://jalammar.github.io/illustrated-bert/)
- [HuggingFace BERT Documentation](https://huggingface.co/docs/transformers/model_doc/bert)

### Рекомендуемые видео

- [BERT Explained (NLP with Deep Learning)](https://www.youtube.com/watch?v=xI0HHN5XKDo)
- [HuggingFace Course: Fine-tuning BERT](https://huggingface.co/learn/nlp-course/chapter3/1)

---

## 11. Резюме

В этом уроке мы изучили:

1. **Encoder-only архитектура:** Bidirectional attention, только понимание (не генерация)
2. **BERT:** MLM + NSP pre-training, парадигма fine-tuning
3. **Pre-training задачи:** Masked LM (стратегия 80/10/10), NSP
4. **Fine-tuning:** Classification, NER, Question Answering
5. **RoBERTa:** Удалён NSP, dynamic masking, более эффективное обучение
6. **Варианты:** DistilBERT, ALBERT, ELECTRA
7. **Security:** Adversarial examples, backdoors, membership inference

**Ключевой вывод:** Encoder-only модели революционизировали NLP, демонстрируя силу pre-training + fine-tuning. Их bidirectional природа создаёт как возможности (богатые representations), так и риски (вредоносный контент влияет на весь контекст).

---

## Следующий урок

→ [03. Decoder-Only модели: GPT, LLaMA, Claude](03-decoder-only.md)

---

*AI Security Academy | Трек 01: Основы AI | Модуль 01.1: Типы моделей*
