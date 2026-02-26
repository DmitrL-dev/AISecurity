# Архитектура Transformer

> **Уровень:** Beginner  
> **Время:** 60 минут  
> **Трек:** 01 — Основы AI  
> **Модуль:** 01.1 — Типы моделей  
> **Версия:** 1.0

---

## Цели обучения

После завершения этого урока вы сможете:

- [ ] Объяснить историческое значение архитектуры Transformer
- [ ] Описать основные компоненты: encoder, decoder, attention
- [ ] Понять математику механизма self-attention
- [ ] Объяснить роль multi-head attention
- [ ] Понять назначение positional encoding
- [ ] Сравнить Transformer с предшествующими архитектурами (RNN, LSTM)
- [ ] Связать архитектурные особенности с уязвимостями безопасности

---

## Предварительные требования

**Знания:**
- Базовое понимание нейронных сетей (слои, активации, backpropagation)
- Понимание матричных операций (умножение, транспонирование)
- Основы Python и PyTorch/TensorFlow

**Уроки:**
- [00. Добро пожаловать в AI Security Academy](../../00-introduction/00-welcome.md)

---

## 1. Историческая справка

### 1.1 Проблемы до Transformer

До 2017 года для обработки последовательностей (текст, речь, временные ряды) использовались **Рекуррентные Нейронные Сети (RNN)** и их улучшенные версии — **LSTM** и **GRU**.

#### Архитектура RNN

```
Input:   x₁ → x₂ → x₃ → x₄ → x₅
          ↓    ↓    ↓    ↓    ↓
RNN:    [h₁]→[h₂]→[h₃]→[h₄]→[h₅]
          ↓    ↓    ↓    ↓    ↓
Output:  y₁   y₂   y₃   y₄   y₅
```

Каждый hidden state `hₜ` зависит от предыдущего:

```
hₜ = f(hₜ₋₁, xₜ)
```

#### Критические проблемы RNN

| Проблема | Описание | Последствия |
|----------|----------|-------------|
| **Последовательная обработка** | Токены обрабатываются по одному | Невозможно распараллелить на GPU |
| **Vanishing gradients** | Градиенты уменьшаются экспоненциально | Модель «забывает» начало длинных последовательностей |
| **Exploding gradients** | Градиенты растут экспоненциально | Нестабильность обучения |
| **Long dependencies** | Сложно связать далёкие токены | «Кот, который сидел на коврике, **был** усталым» — связь кот↔был |

#### LSTM как частичное решение

**Long Short-Term Memory (1997)** добавил механизмы «ворот»:

```
┌─────────────────────────────────┐
│            LSTM Cell            │
├─────────────────────────────────┤
│  forget gate: что забыть        │
│  input gate:  что запомнить     │
│  output gate: что вывести       │
│  cell state:  долгосрочная память│
└─────────────────────────────────┘
```

LSTM частично решил проблему vanishing gradient, но:
- По-прежнему последовательная обработка
- Сложная архитектура (много параметров)
- Ограниченная длина контекста на практике (~500-1000 токенов)

### 1.2 Революция: «Attention Is All You Need»

**Июнь 2017** — команда Google Brain (Vaswani, Shazeer, Parmar и др.) опубликовала [«Attention Is All You Need»](https://arxiv.org/abs/1706.03762).

> [!NOTE]
> Название статьи — утверждение: механизм attention — это **всё**, что нужно для обработки последовательностей. Рекуррентность не требуется.

**Ключевые инновации:**

1. **Полный отказ от рекуррентности** — параллельная обработка всех токенов
2. **Self-attention** — каждый токен «смотрит» на все остальные токены
3. **Positional encoding** — добавление информации о позиции без рекуррентности
4. **Multi-head attention** — несколько «голов» attention для разных типов связей

**Результаты на машинном переводе (WMT 2014):**

| Модель | BLEU (EN→DE) | BLEU (EN→FR) | Время обучения |
|--------|--------------|--------------|----------------|
| GNMT (Google, RNN) | 24.6 | 39.9 | 6 дней |
| ConvS2S (Facebook) | 25.2 | 40.5 | 10 дней |
| **Transformer** | **28.4** | **41.8** | **3.5 дня** |

---

## 2. Архитектура Transformer

### 2.1 Общая структура

Оригинальный Transformer состоит из **Encoder** и **Decoder**:

```
┌─────────────────────────────────────────────────────────────────┐
│                        TRANSFORMER                              │
├────────────────────────────┬────────────────────────────────────┤
│         ENCODER            │            DECODER                 │
│  (обрабатывает вход)       │  (генерирует выход)                │
├────────────────────────────┼────────────────────────────────────┤
│                            │                                    │
│  ┌──────────────────────┐  │  ┌──────────────────────────────┐ │
│  │  Multi-Head          │  │  │  Masked Multi-Head           │ │
│  │  Self-Attention      │  │  │  Self-Attention              │ │
│  └──────────────────────┘  │  └──────────────────────────────┘ │
│            ↓               │              ↓                     │
│  ┌──────────────────────┐  │  ┌──────────────────────────────┐ │
│  │  Add & Norm          │  │  │  Add & Norm                  │ │
│  └──────────────────────┘  │  └──────────────────────────────┘ │
│            ↓               │              ↓                     │
│  ┌──────────────────────┐  │  ┌──────────────────────────────┐ │
│  │  Feed-Forward        │  │  │  Multi-Head                  │ │
│  │  Network             │  │  │  Cross-Attention             │ │
│  └──────────────────────┘  │  │  (к выходу encoder)          │ │
│            ↓               │  └──────────────────────────────┘ │
│  ┌──────────────────────┐  │              ↓                     │
│  │  Add & Norm          │  │  ┌──────────────────────────────┐ │
│  └──────────────────────┘  │  │  Add & Norm                  │ │
│                            │  └──────────────────────────────┘ │
│         × N слоёв          │              ↓                     │
│                            │  ┌──────────────────────────────┐ │
│                            │  │  Feed-Forward Network        │ │
│                            │  └──────────────────────────────┘ │
│                            │              ↓                     │
│                            │  ┌──────────────────────────────┐ │
│                            │  │  Add & Norm                  │ │
│                            │  └──────────────────────────────┘ │
│                            │                                    │
│                            │         × N слоёв                  │
└────────────────────────────┴────────────────────────────────────┘
```

**Параметры оригинального Transformer:**
- N = 6 слоёв в encoder и decoder
- d_model = 512 (размерность embedding)
- d_ff = 2048 (размерность feed-forward)
- h = 8 голов
- d_k = d_v = 64 (размерность на голову)

### 2.2 Encoder

**Задача Encoder:** преобразовать входную последовательность в богатое контекстуальное представление.

```rust
// Pseudocode структуры Encoder
struct TransformerEncoder {
    layers: Vec<EncoderLayer>,
    embedding: TokenEmbedding,
    pos_encoding: PositionalEncoding,
}

impl TransformerEncoder {
    fn new(n_layers: usize, d_model: usize, n_heads: usize, d_ff: usize) -> Self {
        let layers = (0..n_layers)
            .map(|_| EncoderLayer::new(d_model, n_heads, d_ff))
            .collect();
        Self {
            layers,
            embedding: TokenEmbedding::new(vocab_size, d_model),
            pos_encoding: PositionalEncoding::new(d_model),
        }
    }

    fn forward(&self, x: &Tensor) -> Tensor {
        // 1. Token embeddings + positional encoding
        let mut x = self.embedding.forward(x) + self.pos_encoding.forward(x);

        // 2. Проход через N слоёв
        for layer in &self.layers {
            x = layer.forward(&x);
        }

        x // Контекстуальные представления
    }
}
```

**Каждый слой Encoder содержит:**

1. **Multi-Head Self-Attention** — каждый токен «смотрит» на все токены входа
2. **Add & Norm** — residual connection + layer normalization
3. **Feed-Forward Network** — два линейных слоя с активацией
4. **Add & Norm** — ещё один residual + norm

### 2.3 Decoder

**Задача Decoder:** генерировать выходную последовательность токен за токеном.

**Ключевое отличие от Encoder:**

1. **Masked Self-Attention** — токен может «смотреть» только на предыдущие токены (не на будущие)
2. **Cross-Attention** — decoder «смотрит» на выход encoder

```rust
// Маска decoder (causal mask)
// Пример для 4 токенов:
let mask = vec![
    vec![1, 0, 0, 0],  // токен 1 видит только себя
    vec![1, 1, 0, 0],  // токен 2 видит токены 1, 2
    vec![1, 1, 1, 0],  // токен 3 видит токены 1, 2, 3
    vec![1, 1, 1, 1],  // токен 4 видит все
];
```

---

## 3. Механизм Self-Attention

### 3.1 Интуиция

**Вопрос:** Как модель понимает, что в предложении «Кот сидел на коврике, потому что **он** устал» местоимение «он» относится к «кот», а не к «коврик»?

**Ответ:** Self-attention позволяет каждому токену «посмотреть» на все остальные токены и определить их релевантность.

```
         The   cat   sat   on   the   mat   because   it   was   tired
    it:  0.05  0.60  0.05  0.02  0.03  0.15   0.02   0.00  0.03   0.05
                ↑                      ↑
           high weight            medium weight
           (cat — subject)        (mat — possible reference)
```

### 3.2 Query, Key, Value

Self-attention использует три линейные проекции входа:

- **Query (Q)** — «вопрос»: что я ищу?
- **Key (K)** — «ключ»: что у меня есть?
- **Value (V)** — «значение»: что я верну?

```rust
// Для каждого токена создаём Q, K, V
let q = x.matmul(&w_q)?;  // [seq_len, d_model] @ [d_model, d_k] = [seq_len, d_k]
let k = x.matmul(&w_k)?;  // [seq_len, d_model] @ [d_model, d_k] = [seq_len, d_k]
let v = x.matmul(&w_v)?;  // [seq_len, d_model] @ [d_model, d_v] = [seq_len, d_v]
```

### 3.3 Scaled Dot-Product Attention

**Формула:**

```
Attention(Q, K, V) = softmax(Q × K^T / √d_k) × V
```

**Пошаговое объяснение:**

```rust
use candle_core::{Tensor, Device, DType};
use candle_nn::ops::softmax;

fn scaled_dot_product_attention(
    q: &Tensor,    // [batch, seq_len, d_k]
    k: &Tensor,    // [batch, seq_len, d_k]
    v: &Tensor,    // [batch, seq_len, d_v]
    mask: Option<&Tensor>,
) -> candle_core::Result<(Tensor, Tensor)> {
    let d_k = *q.dims().last().unwrap() as f64;

    // Шаг 1: Вычисляем «сырые» attention scores
    // Q @ K^T = [batch, seq_len, d_k] @ [batch, d_k, seq_len] = [batch, seq_len, seq_len]
    let scores = q.matmul(&k.transpose(D::Minus2, D::Minus1)?)?;

    // Шаг 2: Масштабируем на √d_k
    // Без масштабирования при большом d_k dot products становятся очень большими,
    // softmax насыщается, градиенты исчезают
    let scores = (scores / d_k.sqrt())?;

    // Шаг 3: Применяем маску (для decoder)
    let scores = if let Some(m) = mask {
        scores.broadcast_add(&m.where_cond(
            &Tensor::zeros_like(&scores)?,
            &Tensor::new(f32::NEG_INFINITY, scores.device())?.broadcast_as(scores.shape())?,
        )?)?
    } else {
        scores
    };

    // Шаг 4: Softmax — преобразуем в веса (сумма = 1)
    let attention_weights = softmax(&scores, D::Minus1)?;

    // Шаг 5: Взвешенная сумма values
    let output = attention_weights.matmul(v)?;

    Ok((output, attention_weights))
}
```

**Пример визуализации:**

```
Input: "The cat sat"

Q (токен "sat" спрашивает):  [0.2, 0.5, 0.1, ...]
K (все токены отвечают):
  - "The": [0.1, 0.3, 0.2, ...]
  - "cat": [0.3, 0.4, 0.1, ...]
  - "sat": [0.2, 0.5, 0.1, ...]

Scores (Q @ K^T):
  - "sat" → "The": 0.2×0.1 + 0.5×0.3 + ... = 0.17
  - "sat" → "cat": 0.2×0.3 + 0.5×0.4 + ... = 0.26
  - "sat" → "sat": 0.2×0.2 + 0.5×0.5 + ... = 0.29

После softmax:
  - "sat" → "The": 0.28
  - "sat" → "cat": 0.34
  - "sat" → "sat": 0.38
```

### 3.4 Почему √d_k?

**Проблема:** При большом d_k (например, 64) dot products становятся очень большими:

```
Если q_i, k_i ~ N(0, 1), то dot product ~ N(0, d_k)
Для d_k = 64: стандартное отклонение = 8
```

Большие значения → softmax даёт почти one-hot → градиенты исчезают.

**Решение:** Делим на √d_k для возврата дисперсии ≈ 1.

---

## 4. Multi-Head Attention

### 4.1 Зачем несколько «голов»?

Одна голова attention может захватить только один тип связей. **Multi-head позволяет моделировать разные типы зависимостей параллельно:**

| Голова | Что может захватывать |
|--------|----------------------|
| Head 1 | Синтаксические связи (подлежащее-сказуемое) |
| Head 2 | Семантические связи (слова одной темы) |
| Head 3 | Позиционные паттерны (соседние слова) |
| Head 4 | Анафора (местоимения → существительные) |
| ... | ... |

### 4.2 Математика Multi-Head Attention

```rust
use candle_core::Tensor;
use candle_nn::{Linear, Module, VarBuilder};

struct MultiHeadAttention {
    n_heads: usize,
    d_k: usize,
    w_q: Linear,
    w_k: Linear,
    w_v: Linear,
    w_o: Linear,
}

impl MultiHeadAttention {
    fn new(d_model: usize, n_heads: usize, vb: VarBuilder) -> candle_core::Result<Self> {
        let d_k = d_model / n_heads; // 512 / 8 = 64

        // Проекции для каждой головы
        let w_q = candle_nn::linear(d_model, d_model, vb.pp("w_q"))?;
        let w_k = candle_nn::linear(d_model, d_model, vb.pp("w_k"))?;
        let w_v = candle_nn::linear(d_model, d_model, vb.pp("w_v"))?;

        // Финальная проекция
        let w_o = candle_nn::linear(d_model, d_model, vb.pp("w_o"))?;

        Ok(Self { n_heads, d_k, w_q, w_k, w_v, w_o })
    }

    fn forward(&self, q: &Tensor, k: &Tensor, v: &Tensor, mask: Option<&Tensor>) -> candle_core::Result<(Tensor, Tensor)> {
        let batch_size = q.dim(0)?;

        // 1. Линейные проекции
        let q = self.w_q.forward(q)?;  // [batch, seq_len, d_model]
        let k = self.w_k.forward(k)?;
        let v = self.w_v.forward(v)?;

        // 2. Разделяем на головы
        // [batch, seq_len, d_model] → [batch, n_heads, seq_len, d_k]
        let q = q.reshape((batch_size, (), self.n_heads, self.d_k))?.transpose(1, 2)?;
        let k = k.reshape((batch_size, (), self.n_heads, self.d_k))?.transpose(1, 2)?;
        let v = v.reshape((batch_size, (), self.n_heads, self.d_k))?.transpose(1, 2)?;

        // 3. Attention для каждой головы параллельно
        let (attn_output, attn_weights) = scaled_dot_product_attention(&q, &k, &v, mask)?;

        // 4. Конкатенируем головы
        // [batch, n_heads, seq_len, d_k] → [batch, seq_len, d_model]
        let attn_output = attn_output.transpose(1, 2)?.contiguous()?;
        let attn_output = attn_output.reshape((batch_size, (), self.n_heads * self.d_k))?;

        // 5. Финальная проекция
        let output = self.w_o.forward(&attn_output)?;

        Ok((output, attn_weights))
    }
}
```

### 4.3 Визуализация Multi-Head

```
Input X [seq_len, d_model=512]
         ↓
    ┌────┴────┐
    ↓    ↓    ↓   ... (8 heads)
  [Q₁] [Q₂] [Q₃]
  [K₁] [K₂] [K₃]
  [V₁] [V₂] [V₃]
    ↓    ↓    ↓
[Attn₁][Attn₂][Attn₃] ... [Attn₈]
 [64]   [64]   [64]        [64]
    ↓    ↓    ↓             ↓
    └────┴────┴─────────────┘
              ↓
         Concat [512]
              ↓
           W_O [512]
              ↓
         Output [512]
```

---

## 5. Positional Encoding

### 5.1 Проблема: Transformer не знает позицию

В отличие от RNN, где позиция неявно закодирована порядком обработки, Transformer обрабатывает все токены параллельно. **Без дополнительной информации «cat sat» и «sat cat» были бы идентичны.**

### 5.2 Решение: Синусоидальное позиционное кодирование

Оригинальная статья использует синусоидальные функции:

```rust
fn positional_encoding(seq_len: usize, d_model: usize) -> Vec<Vec<f64>> {
    // PE(pos, 2i)   = sin(pos / 10000^(2i/d_model))
    // PE(pos, 2i+1) = cos(pos / 10000^(2i/d_model))
    let mut pe = vec![vec![0.0f64; d_model]; seq_len];

    for pos in 0..seq_len {
        for i in (0..d_model).step_by(2) {
            let div_term = (pos as f64) / (10000.0_f64).powf(i as f64 / d_model as f64);
            pe[pos][i] = div_term.sin();     // чётные индексы
            if i + 1 < d_model {
                pe[pos][i + 1] = div_term.cos(); // нечётные индексы
            }
        }
    }

    pe
}
```

### 5.3 Почему синусоиды?

1. **Уникальность:** Каждая позиция имеет уникальную комбинацию значений
2. **Относительные позиции:** PE(pos+k) можно выразить как линейную функцию от PE(pos)
3. **Экстраполяция:** Работает для последовательностей длиннее, чем в обучении

```
Position 0:  [sin(0), cos(0), sin(0), cos(0), ...]  = [0, 1, 0, 1, ...]
Position 1:  [sin(1), cos(1), sin(0.001), cos(0.001), ...]
Position 2:  [sin(2), cos(2), sin(0.002), cos(0.002), ...]
...
```

### 5.4 Современные альтернативы

| Метод | Описание | Используется в |
|-------|----------|----------------|
| Learned Positional Embeddings | Обучаемые векторы | BERT, GPT-2 |
| RoPE (Rotary Position Embedding) | Вращение в комплексной плоскости | LLaMA, Mistral |
| ALiBi | Линейный attention bias | BLOOM |
| Relative Position Encodings | Относительные позиции | T5 |

---

## 6. Дополнительные компоненты

### 6.1 Feed-Forward Network

После attention идёт позиционно-независимая feed-forward сеть:

```rust
use candle_nn::{Linear, Module, VarBuilder, Dropout};

struct FeedForward {
    linear1: Linear,
    linear2: Linear,
    dropout: Dropout,
}

impl FeedForward {
    fn new(d_model: usize, d_ff: usize, dropout: f32, vb: VarBuilder) -> candle_core::Result<Self> {
        let linear1 = candle_nn::linear(d_model, d_ff, vb.pp("linear1"))?;
        let linear2 = candle_nn::linear(d_ff, d_model, vb.pp("linear2"))?;
        let dropout = Dropout::new(dropout);
        Ok(Self { linear1, linear2, dropout })
    }

    fn forward(&self, x: &Tensor) -> candle_core::Result<Tensor> {
        // FFN(x) = max(0, xW₁ + b₁)W₂ + b₂
        let x = self.linear1.forward(x)?;
        let x = x.relu()?;
        let x = self.dropout.forward(&x, /* train */ false)?;
        let x = self.linear2.forward(&x)?;
        Ok(x)
    }
}
```

**Зачем FFN?**
- Attention — линейная операция (взвешенная сумма)
- FFN добавляет нелинейность
- Увеличивает выразительность модели

### 6.2 Layer Normalization

```rust
// Layer Norm нормализует по последнему измерению (features)
let layer_norm = candle_nn::layer_norm(d_model, candle_nn::LayerNormConfig::default(), vb.pp("ln"))?;
let output = layer_norm.forward(&x)?;
```

**Формула:**

```
LayerNorm(x) = γ × (x - μ) / √(σ² + ε) + β
```

Где:
- μ, σ — среднее и стандартное отклонение по features
- γ, β — обучаемые параметры

### 6.3 Residual Connections

```rust
// Вместо: output = sublayer(x)
// Используем: output = x + sublayer(x)

let output = (x + self.attention.forward(&x)?)?;
let output = self.layer_norm.forward(&output)?;
```

**Зачем?**
- Улучшение обучения глубоких сетей
- Позволяют градиентам «течь» напрямую
- Skip connections помогают сохранить информацию

---

## 7. Transformer и AI Security

### 7.1 Архитектурные особенности → Уязвимости

| Особенность | Потенциальная уязвимость |
|-------------|--------------------------|
| **Self-attention на весь контекст** | Indirect injection: вредоносный текст в документе влияет на всё |
| **Autoregressive generation** | Каждый новый токен зависит от предыдущих → injection в начале критичен |
| **Positional encoding** | Position attacks: манипуляция порядком инструкций |
| **Attention weights** | Interpretability → можно понять, на что модель «смотрит» |

### 7.2 SENTINEL Engines для анализа Transformer

SENTINEL включает engines для анализа внутренних состояний Transformer:

```rust
use sentinel_core::engines::SentinelEngine;

// Анализ паттернов attention
let attention_detector = AttentionPatternDetector::new();
let result = attention_detector.analyze(
    model.get_attention_weights(),
    &user_input,
)?;

if result.anomalous_patterns {
    println!("Обнаружены аномальные паттерны attention: {:?}", result.patterns);
}

// Hidden state forensics
let forensics = HiddenStateForensics::new();
let analysis = forensics.analyze(
    model.get_hidden_states(),
    "helpful_assistant",
)?;
```

### 7.3 Связь с атаками

| Атака | Эксплуатируемый компонент |
|-------|---------------------------|
| Prompt Injection | Self-attention: вредоносный текст получает высокие attention weights |
| Jailbreak | FFN: обход выученных safety representations |
| Adversarial Suffixes | Positional encoding: специфические позиции для trigger |
| Context Hijacking | Long context attention: заполнение контекста вредоносным контентом |

---

## 8. Практические упражнения

### Упражнение 1: Визуализация Attention

Используйте библиотеку BertViz для визуализации attention weights:

```rust
use candle_core::Tensor;
use candle_transformers::models::bert::{BertModel, Config};

// Загружаем модель
let tokenizer = tokenizers::Tokenizer::from_pretrained("bert-base-uncased", None).unwrap();
let config = Config::from_pretrained("bert-base-uncased")?;
let model = BertModel::load(vb, &config)?;

// Анализируем предложение
let sentence = "The cat sat on the mat because it was tired";
let encoding = tokenizer.encode(sentence, true).unwrap();
let input_ids = Tensor::new(encoding.get_ids(), &device)?;
let outputs = model.forward(&input_ids, &token_type_ids, Some(&attention_mask))?;

// Визуализация
let tokens = encoding.get_tokens();
// Используем attention weights для визуализации
println!("Tokens: {:?}", tokens);
```

**Вопросы для анализа:**
1. Какие головы связывают «it» с «cat»?
2. Как меняется attention от слоя к слою?
3. Есть ли головы, фокусирующиеся на синтаксисе?

<details>
<summary>💡 Подсказка</summary>

Обратите внимание на головы в средних слоях (4-8). Ранние слои часто фокусируются на локальных паттернах, поздние — на более абстрактных связях.

</details>

### Упражнение 2: Расчёт размерностей

Для Transformer с параметрами:
- d_model = 768
- n_heads = 12
- n_layers = 12
- vocab_size = 30,000

Рассчитайте:

1. Размерность d_k для каждой головы
2. Количество параметров в одном блоке Multi-Head Attention
3. Общее количество параметров модели (приблизительно)

<details>
<summary>✅ Решение</summary>

1. **d_k = d_model / n_heads = 768 / 12 = 64**

2. **Параметры Multi-Head Attention:**
   - W_Q: 768 × 768 = 589,824
   - W_K: 768 × 768 = 589,824
   - W_V: 768 × 768 = 589,824
   - W_O: 768 × 768 = 589,824
   - **Итого: 2,359,296 параметров**

3. **Общий подсчёт:**
   - Token embeddings: 30,000 × 768 ≈ 23M
   - Position embeddings: 512 × 768 ≈ 0.4M
   - На один слой: ~7M (attention + FFN + norms)
   - 12 слоёв: 12 × 7M ≈ 84M
   - **Итого: ~110M параметров** (BERT-base)

</details>

### Упражнение 3: Реализация Scaled Dot-Product Attention

Реализуйте функцию attention с нуля и протестируйте её:

```rust
use candle_core::{Tensor, Device, DType};

fn my_attention(
    q: &Tensor,    // [batch, seq_len, d_k]
    k: &Tensor,    // [batch, seq_len, d_k]
    v: &Tensor,    // [batch, seq_len, d_v]
    mask: Option<&Tensor>,  // [seq_len, seq_len] or None
) -> candle_core::Result<(Tensor, Tensor)> {
    // output: [batch, seq_len, d_v]
    // weights: [batch, seq_len, seq_len]

    // Ваш код здесь
    todo!()
}

fn main() -> candle_core::Result<()> {
    let device = Device::Cpu;

    // Тест
    let q = Tensor::randn(0f32, 1.0, (2, 4, 64), &device)?; // batch=2, seq_len=4, d_k=64
    let k = Tensor::randn(0f32, 1.0, (2, 4, 64), &device)?;
    let v = Tensor::randn(0f32, 1.0, (2, 4, 64), &device)?;

    let (output, weights) = my_attention(&q, &k, &v, None)?;
    println!("Output shape: {:?}", output.shape());   // Должно быть [2, 4, 64]
    println!("Weights shape: {:?}", weights.shape());  // Должно быть [2, 4, 4]
    println!("Weights sum per row: {:?}", weights.sum(D::Minus1)?); // Должно быть ~1.0

    Ok(())
}
```

---

## 9. Quiz вопросы

### Вопрос 1

Какую основную проблему RNN решает архитектура Transformer?

- [ ] A) Недостаточное количество параметров
- [ ] B) Слишком быстрое обучение
- [x] C) Последовательная обработка и vanishing gradients
- [ ] D) Слишком простая архитектура

### Вопрос 2

Для чего используется коэффициент масштабирования √d_k в механизме attention?

- [ ] A) Увеличение скорости вычислений
- [x] B) Предотвращение слишком больших значений dot product и насыщения softmax
- [ ] C) Уменьшение количества параметров
- [ ] D) Добавление нелинейности

### Вопрос 3

Что такое Multi-Head Attention?

- [ ] A) Attention с несколькими входными последовательностями
- [x] B) Параллельное применение нескольких механизмов attention с разными проекциями
- [ ] C) Attention только в первом слое
- [ ] D) Attention между encoder и decoder

### Вопрос 4

Зачем нужен positional encoding в Transformer?

- [x] A) Transformer не имеет понятия о порядке токенов без дополнительной информации
- [ ] B) Для ускорения обучения
- [ ] C) Для уменьшения количества параметров
- [ ] D) Для улучшения генерации

### Вопрос 5

Какое ключевое отличие Decoder от Encoder?

- [ ] A) Decoder имеет больше слоёв
- [ ] B) Decoder использует другую активацию
- [x] C) Decoder использует masked attention, чтобы не «подглядывать» в будущие токены
- [ ] D) Decoder не использует positional encoding

---

## 10. Связанные материалы

### SENTINEL Engines

| Engine | Описание | Урок |
|--------|----------|------|
| `AttentionPatternDetector` | Анализ паттернов attention для обнаружения аномалий | [Advanced Detection](../../06-advanced-detection/) |
| `HiddenStateForensics` | Форензика hidden states модели | [Advanced Detection](../../06-advanced-detection/) |
| `TokenFlowAnalyzer` | Анализ потока информации между токенами | [Advanced Detection](../../06-advanced-detection/) |

### Внешние ресурсы

- [Attention Is All You Need (оригинальная статья)](https://arxiv.org/abs/1706.03762)
- [The Illustrated Transformer (Jay Alammar)](https://jalammar.github.io/illustrated-transformer/)
- [Harvard NLP: The Annotated Transformer](https://nlp.seas.harvard.edu/2018/04/03/attention.html)
- [Lilian Weng: The Transformer Family](https://lilianweng.github.io/posts/2023-01-27-the-transformer-family-v2/)

### Рекомендуемые видео

- [3Blue1Brown: Attention in Transformers](https://www.youtube.com/watch?v=eMlx5fFNoYc)
- [Andrej Karpathy: Let's build GPT](https://www.youtube.com/watch?v=kCc8FmEb1nY)

---

## 11. Резюме

В этом уроке мы изучили:

1. **История:** Проблемы RNN → революция Transformer (2017)
2. **Архитектура:** Encoder-Decoder структура с N слоями
3. **Self-Attention:** Q, K, V проекции, scaled dot-product, softmax
4. **Multi-Head Attention:** Параллельные головы для разных типов связей
5. **Positional Encoding:** Синусоидальные функции для кодирования позиции
6. **Security:** Связь архитектуры с уязвимостями, SENTINEL engines

**Ключевой вывод:** Transformer является основой современных LLM. Понимание его архитектуры критически важно для понимания как возможностей, так и уязвимостей AI-систем.

---

## Следующий урок

→ [02. Encoder-Only модели: BERT, RoBERTa](02-encoder-only.md)

---

*AI Security Academy | Трек 01: Основы AI | Модуль 01.1: Типы моделей*
