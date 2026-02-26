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

```rust
use rand::Rng;

fn mask_tokens(
    tokens: &mut Vec<u32>,
    tokenizer: &Tokenizer,
    mlm_probability: f64,
) -> (Vec<u32>, Vec<i64>) {
    // Для 15% токенов:
    // - 80%: заменяем на [MASK]
    // - 10%: заменяем на случайный токен
    // - 10%: оставляем без изменений

    let mut rng = rand::thread_rng();
    let mut labels: Vec<i64> = tokens.iter().map(|&t| t as i64).collect();
    let special_tokens = tokenizer.get_special_tokens_mask(tokens);

    for i in 0..tokens.len() {
        if special_tokens[i] {
            labels[i] = -100;
            continue;
        }

        if rng.gen::<f64>() >= mlm_probability {
            labels[i] = -100; // Игнорируем не-masked для loss
            continue;
        }

        let r: f64 = rng.gen();
        if r < 0.8 {
            // 80% заменяем на [MASK]
            tokens[i] = tokenizer.mask_token_id();
        } else if r < 0.9 {
            // 10% заменяем на случайный токен
            tokens[i] = rng.gen_range(0..tokenizer.vocab_size() as u32);
        }
        // 10% оставляем без изменений
    }

    (tokens.clone(), labels)
}
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

```rust
use candle_core::Tensor;
use candle_nn::{Linear, Module, VarBuilder};

struct BertForPreTraining {
    bert: BertModel,
    mlm_head: Linear,
    nsp_head: Linear,
}

impl BertForPreTraining {
    fn new(bert_model: BertModel, vocab_size: usize, hidden_size: usize, vb: VarBuilder) -> candle_core::Result<Self> {
        // MLM head
        let mlm_head = candle_nn::linear(hidden_size, vocab_size, vb.pp("mlm_head"))?;
        // NSP head (бинарная классификация на [CLS] токене)
        let nsp_head = candle_nn::linear(hidden_size, 2, vb.pp("nsp_head"))?;

        Ok(Self { bert: bert_model, mlm_head, nsp_head })
    }

    fn forward(&self, input_ids: &Tensor, segment_ids: &Tensor, attention_mask: &Tensor) -> candle_core::Result<(Tensor, Tensor)> {
        // BERT encoding
        let outputs = self.bert.forward(input_ids, segment_ids, Some(attention_mask))?;
        let sequence_output = outputs.last_hidden_state; // [batch, seq_len, hidden]
        let pooled_output = outputs.pooler_output;       // [batch, hidden] ([CLS] representation)

        // MLM predictions
        let mlm_logits = self.mlm_head.forward(&sequence_output)?; // [batch, seq_len, vocab_size]

        // NSP predictions
        let nsp_logits = self.nsp_head.forward(&pooled_output)?;   // [batch, 2]

        Ok((mlm_logits, nsp_logits))
    }
}
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

```rust
use candle_transformers::models::bert::BertForSequenceClassification;

// Загружаем pre-trained модель с classification head
let model = BertForSequenceClassification::from_pretrained(
    "bert-base-uncased",
    2, // num_labels — бинарная классификация
    vb,
)?;
let tokenizer = tokenizers::Tokenizer::from_pretrained("bert-base-uncased", None).unwrap();

// Подготовка данных
let text = "This movie is absolutely fantastic!";
let encoding = tokenizer.encode(text, true).unwrap();
let input_ids = Tensor::new(encoding.get_ids(), &device)?;

// Inference
let logits = model.forward(&input_ids, &token_type_ids, Some(&attention_mask))?;
let predictions = logits.argmax(D::Minus1)?;
let label = if predictions.to_scalar::<u32>()? == 1 { "Positive" } else { "Negative" };
println!("Prediction: {}", label);
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

```rust
use candle_transformers::models::bert::BertForTokenClassification;

// NER использует ВСЕ токены, не только [CLS]
let model = BertForTokenClassification::from_pretrained(
    "bert-base-uncased",
    9, // num_labels: B-PER, I-PER, B-ORG, I-ORG, B-LOC, I-LOC, B-MISC, I-MISC, O
    vb,
)?;

let text = "John works at Google in New York";
let encoding = tokenizer.encode(text, true).unwrap();
let input_ids = Tensor::new(encoding.get_ids(), &device)?;

let logits = model.forward(&input_ids, &token_type_ids, Some(&attention_mask))?;
let predictions = logits.argmax(D::Minus1)?;
// predictions для каждого токена
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

```rust
use candle_transformers::models::bert::BertForQuestionAnswering;

let model = BertForQuestionAnswering::from_pretrained("bert-base-uncased", vb)?;

let question = "What is the capital of France?";
let context = "Paris is the capital and most populous city of France.";

let encoding = tokenizer.encode((question, context), true).unwrap();
let input_ids = Tensor::new(encoding.get_ids(), &device)?;

let outputs = model.forward(&input_ids, &token_type_ids, Some(&attention_mask))?;
let start_idx = outputs.start_logits.argmax(D::Minus1)?.to_scalar::<u32>()?;
let end_idx = outputs.end_logits.argmax(D::Minus1)?.to_scalar::<u32>()?;

let answer_tokens = &encoding.get_ids()[start_idx as usize..=end_idx as usize];
let answer = tokenizer.decode(answer_tokens, true).unwrap();
println!("Answer: {}", answer); // "Paris"
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

```rust
fn dynamic_masking(tokens: &mut Vec<u32>, tokenizer: &Tokenizer, epoch_seed: u64) -> (Vec<u32>, Vec<i64>) {
    // Генерирует разную маску для каждой эпохи
    let mut rng = rand::rngs::StdRng::seed_from_u64(epoch_seed);
    mask_tokens(tokens, tokenizer, 0.15)
}
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

```rust
use candle_transformers::models::distilbert::DistilBertModel;

let model = DistilBertModel::load(vb, &config)?;
// 66M параметров vs 110M для BERT-base
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

```rust
// Атака: добавляем слово, которое меняет классификацию
let original = "This movie is great";       // → Positive
let adversarial = "This movie is great unfortunately"; // → Negative

// "unfortunately" сдвигает embedding в негативную область
```

**SENTINEL detection:**

```rust
use sentinel_core::engines::SentinelEngine;

let detector = EmbeddingShiftDetector::new();
let result = detector.analyze(
    original,
    adversarial,
    &bert_model,
)?;

if result.shift_detected {
    println!("Semantic shift: {}", result.shift_magnitude);
    println!("Suspicious tokens: {:?}", result.suspicious_tokens);
}
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

```rust
use sentinel_core::engines::SentinelEngine;

let scanner = BackdoorTriggerScanner::new();
let result = scanner.scan_model(
    &loaded_model,
    &validation_set,
)?;

if result.backdoor_indicators {
    println!("⚠️ Потенциальный backdoor обнаружен!");
    println!("Suspicious patterns: {:?}", result.patterns);
}
```

### 7.4 Privacy: Membership Inference

**Атака:** Определить, был ли конкретный текст в обучающих данных BERT.

```rust
fn membership_inference(model: &BertModel, text: &str, tokenizer: &Tokenizer) -> f32 {
    // Высокая уверенность в предсказании [MASK] может указывать
    // на присутствие текста в обучающих данных
    let masked_text = text.replace("word", "[MASK]");
    let encoding = tokenizer.encode(masked_text, true).unwrap();
    let input_ids = Tensor::new(encoding.get_ids(), &device).unwrap();

    let logits = model.forward(&input_ids, &token_type_ids, None).unwrap();
    // Высокие logits для правильного слова → вероятно в training data
    let confidence = candle_nn::ops::softmax(&logits, D::Minus1)
        .unwrap()
        .max(D::Minus1)
        .unwrap()
        .to_scalar::<f32>()
        .unwrap();
    confidence
}
```

---

## 8. Практические упражнения

### Упражнение 1: Masked Language Modeling

Используйте BERT для предсказания masked слов:

```rust
use candle_transformers::models::bert::BertModel;

// Создаём fill-mask pipeline
let tokenizer = tokenizers::Tokenizer::from_pretrained("bert-base-uncased", None).unwrap();
let model = BertModel::load(vb, &config)?;

// Тест
let sentences = vec![
    "The capital of France is [MASK].",
    "Machine learning is a branch of [MASK] intelligence.",
    "BERT was developed by [MASK].",
];

for sentence in &sentences {
    let encoding = tokenizer.encode(*sentence, true).unwrap();
    let input_ids = Tensor::new(encoding.get_ids(), &device)?;
    let logits = model.forward(&input_ids, &token_type_ids, None)?;

    println!("\nSentence: {}", sentence);
    // Получаем top-3 предсказания для masked позиции
    let probs = candle_nn::ops::softmax(&logits, D::Minus1)?;
    // Выводим top-3 токена с вероятностями
    println!("  Top predictions computed from logits");
}
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

```rust
use candle_core::{Device, Tensor};
use candle_nn::{AdamW, Optimizer, VarMap, VarBuilder};
use candle_transformers::models::bert::BertForSequenceClassification;

// Загрузка модели
let device = Device::Cpu;
let var_map = VarMap::new();
let vb = VarBuilder::from_varmap(&var_map, candle_core::DType::F32, &device);
let model = BertForSequenceClassification::from_pretrained("bert-base-uncased", 2, vb)?;
let tokenizer = tokenizers::Tokenizer::from_pretrained("bert-base-uncased", None).unwrap();

// Токенизация
fn tokenize_function(tokenizer: &tokenizers::Tokenizer, text: &str) -> Vec<u32> {
    let encoding = tokenizer.encode(text, true).unwrap();
    encoding.get_ids().to_vec()
}

// Аргументы обучения
let learning_rate = 5e-5;
let num_epochs = 3;
let batch_size = 16;
let warmup_steps = 500;
let weight_decay = 0.01;

// Оптимизатор
let mut optimizer = AdamW::new(
    var_map.all_vars(),
    candle_nn::optim::ParamsAdamW {
        lr: learning_rate,
        weight_decay,
        ..Default::default()
    },
)?;

// Fine-tune loop
for epoch in 0..num_epochs {
    // Цикл обучения по батчам
    println!("Epoch {}/{}", epoch + 1, num_epochs);
    // ... обучение на IMDB subset (1000 train, 200 eval)
}
```

**Задание:** 
1. Запустите fine-tuning на IMDB subset
2. Оцените accuracy на test set
3. Попробуйте adversarial examples

### Упражнение 3: Анализ паттернов Attention

```rust
use candle_core::{Device, Tensor};
use candle_transformers::models::bert::BertModel;

let model = BertModel::load(vb, &config)?; // with output_attentions
let tokenizer = tokenizers::Tokenizer::from_pretrained("bert-base-uncased", None).unwrap();

let text = "The cat sat on the mat because it was tired";
let encoding = tokenizer.encode(text, true).unwrap();
let input_ids = Tensor::new(encoding.get_ids(), &device)?;

let outputs = model.forward(&input_ids, &token_type_ids, Some(&attention_mask))?;

// Attention: [layers][batch, heads, seq_len, seq_len]
let attention = outputs.attentions;

// Визуализируем head 0, layer 11
let tokens = encoding.get_tokens();
let att = &attention[11]; // Layer 11, Head 0

println!("BERT Attention (Layer 11, Head 0)");
println!("Tokens: {:?}", tokens);
// Используйте plotters crate для визуализации heatmap
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
