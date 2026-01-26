# Transformer архитектура

> **Уровень:** Начинающий  
> **Время:** 60 минут  
> **Трек:** 01 — AI Fundamentals  
> **Модуль:** 01.1 — Типы моделей  
> **Версия:** 1.0

---

## Цели обучения

После завершения этого урока вы сможете:

- [ ] Объяснить историческую значимость архитектуры Transformer
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

До 2017 года для обработки последовательностей (текст, речь, временные ряды) использовались **рекуррентные нейронные сети (RNN)** и их улучшенные версии — **LSTM** и **GRU**.

#### Архитектура RNN

```
Вход:    x? > x? > x? > x? > x?
          v    v    v    v    v
RNN:    [h?]>[h?]>[h?]>[h?]>[h?]
          v    v    v    v    v
Выход:   y?   y?   y?   y?   y?
```

Каждый скрытый слой (hidden state) `h?` зависит от предыдущего:

```
h? = f(h???, x?)
```

#### Критические проблемы RNN

| Проблема | Описание | Последствия |
|----------|----------|-------------|
| **Последовательная обработка** | Токены обрабатываются один за другим | Невозможность параллелизации на GPU |
| **Затухание градиентов** | Градиенты уменьшаются экспоненциально | Модель "забывает" начало длинных последовательностей |
| **Взрыв градиентов** | Градиенты растут экспоненциально | Нестабильность обучения |
| **Длинные зависимости** | Сложно связать далёкие токены | "The cat, which was sitting on the mat, **was** tired" — связь cat-was |

#### LSTM как частичное решение

**Long Short-Term Memory (1997)** добавила механизмы "ворот" (gates):

```
----------------------------------¬
¦            LSTM Cell            ¦
+---------------------------------+
¦  forget gate: что забыть        ¦
¦  input gate:  что запомнить     ¦
¦  output gate: что вывести       ¦
¦  cell state:  долгосрочная память¦
L----------------------------------
```

LSTM частично решила проблему затухания градиентов, но:
- Всё ещё последовательная обработка
- Сложная архитектура (много параметров)
- Ограниченная длина контекста на практике (~500-1000 токенов)

### 1.2 Революция: "Attention Is All You Need"

**Июнь 2017** — команда Google Brain (Vaswani, Shazeer, Parmar et al.) опубликовала статью ["Attention Is All You Need"](https://arxiv.org/abs/1706.03762).

> [!NOTE]
> Название статьи — это утверждение: механизм внимания (attention) — это **всё**, что нужно для обработки последовательностей. Рекуррентность не требуется.

**Ключевые инновации:**

1. **Полный отказ от рекуррентности** — параллельная обработка всех токенов
2. **Self-attention** — каждый токен "смотрит" на все остальные токены
3. **Positional encoding** — добавление информации о позиции без рекуррентности
4. **Multi-head attention** — несколько "голов" внимания для разных типов связей

**Результаты на машинном переводе (WMT 2014):**

| Модель | BLEU (EN>DE) | BLEU (EN>FR) | Время обучения |
|--------|--------------|--------------|----------------|
| GNMT (Google, RNN) | 24.6 | 39.9 | 6 дней |
| ConvS2S (Facebook) | 25.2 | 40.5 | 10 дней |
| **Transformer** | **28.4** | **41.8** | **3.5 дня** |

---

## 2. Архитектура Transformer

### 2.1 Общая структура

Оригинальный Transformer состоит из **Encoder** и **Decoder**:

```
------------------------------------------------------------------¬
¦                        TRANSFORMER                              ¦
+----------------------------T------------------------------------+
¦         ENCODER            ¦            DECODER                 ¦
¦  (обрабатывает вход)       ¦  (генерирует выход)                ¦
+----------------------------+------------------------------------+
¦                            ¦                                    ¦
¦  -----------------------¬  ¦  -------------------------------¬ ¦
¦  ¦  Multi-Head          ¦  ¦  ¦  Masked Multi-Head           ¦ ¦
¦  ¦  Self-Attention      ¦  ¦  ¦  Self-Attention              ¦ ¦
¦  L-----------------------  ¦  L------------------------------- ¦
¦            v               ¦              v                     ¦
¦  -----------------------¬  ¦  -------------------------------¬ ¦
¦  ¦  Add & Norm          ¦  ¦  ¦  Add & Norm                  ¦ ¦
¦  L-----------------------  ¦  L------------------------------- ¦
¦            v               ¦              v                     ¦
¦  -----------------------¬  ¦  -------------------------------¬ ¦
¦  ¦  Feed-Forward        ¦  ¦  ¦  Multi-Head                  ¦ ¦
¦  ¦  Network             ¦  ¦  ¦  Cross-Attention             ¦ ¦
¦  L-----------------------  ¦  ¦  (к encoder output)          ¦ ¦
¦            v               ¦  L------------------------------- ¦
¦  -----------------------¬  ¦              v                     ¦
¦  ¦  Add & Norm          ¦  ¦  -------------------------------¬ ¦
¦  L-----------------------  ¦  ¦  Add & Norm                  ¦ ¦
¦                            ¦  L------------------------------- ¦
¦         ? N слоёв          ¦              v                     ¦
¦                            ¦  -------------------------------¬ ¦
¦                            ¦  ¦  Feed-Forward Network        ¦ ¦
¦                            ¦  L------------------------------- ¦
¦                            ¦              v                     ¦
¦                            ¦  -------------------------------¬ ¦
¦                            ¦  ¦  Add & Norm                  ¦ ¦
¦                            ¦  L------------------------------- ¦
¦                            ¦                                    ¦
¦                            ¦         ? N слоёв                  ¦
L----------------------------+-------------------------------------
```

**Параметры оригинального Transformer:**
- N = 6 слоёв в encoder и decoder
- d_model = 512 (размерность embeddings)
- d_ff = 2048 (размерность feed-forward)
- h = 8 голов (heads)
- d_k = d_v = 64 (размерность каждой головы)

### 2.2 Encoder

**Задача Encoder:** преобразовать входную последовательность в богатое контекстное представление.

```python
# Псевдокод структуры Encoder
class TransformerEncoder:
    def __init__(self, n_layers=6, d_model=512, n_heads=8, d_ff=2048):
        self.layers = [EncoderLayer(d_model, n_heads, d_ff) for _ in range(n_layers)]
        self.embedding = TokenEmbedding(vocab_size, d_model)
        self.pos_encoding = PositionalEncoding(d_model)
    
    def forward(self, x):
        # 1. Token embeddings + positional encoding
        x = self.embedding(x) + self.pos_encoding(x)
        
        # 2. Проход через N слоёв
        for layer in self.layers:
            x = layer(x)
        
        return x  # Контекстные представления
```

**Каждый слой Encoder содержит:**

1. **Multi-Head Self-Attention** — каждый токен "смотрит" на все токены входа
2. **Add & Norm** — residual connection + layer normalization
3. **Feed-Forward Network** — два линейных слоя с активацией
4. **Add & Norm** — ещё один residual + norm

### 2.3 Decoder

**Задача Decoder:** генерировать выходную последовательность токен за токеном.

**Ключевое отличие от Encoder:**

1. **Masked Self-Attention** — токен может "смотреть" только на предыдущие токены (не на будущие)
2. **Cross-Attention** — decoder "смотрит" на encoder output

```python
# Маска для Decoder (causal mask)
# Пример для 4 токенов:
mask = [
    [1, 0, 0, 0],  # токен 1 видит только себя
    [1, 1, 0, 0],  # токен 2 видит токены 1, 2
    [1, 1, 1, 0],  # токен 3 видит токены 1, 2, 3
    [1, 1, 1, 1],  # токен 4 видит все
]
```

---

## 3. Механизм Self-Attention

### 3.1 Интуиция

**Вопрос:** Как модель понимает, что в предложении "The cat sat on the mat because **it** was tired" местоимение "it" относится к "cat", а не к "mat"?

**Ответ:** Self-attention позволяет каждому токену "взглянуть" на все остальные токены и определить их релевантность.

```
         The   cat   sat   on   the   mat   because   it   was   tired
    it:  0.05  0.60  0.05  0.02  0.03  0.15   0.02   0.00  0.03   0.05
                ^                      ^
           высокий вес            средний вес
           (cat — субъект)        (mat — возможная ссылка)
```

### 3.2 Query, Key, Value

Self-attention использует три линейные проекции входа:

- **Query (Q)** — "вопрос": что я ищу?
- **Key (K)** — "ключ": что у меня есть?
- **Value (V)** — "значение": что я верну?

```python
# Для каждого токена создаём Q, K, V
Q = X @ W_Q  # [seq_len, d_model] @ [d_model, d_k] = [seq_len, d_k]
K = X @ W_K  # [seq_len, d_model] @ [d_model, d_k] = [seq_len, d_k]
V = X @ W_V  # [seq_len, d_model] @ [d_model, d_v] = [seq_len, d_v]
```

### 3.3 Scaled Dot-Product Attention

**Формула:**

```
Attention(Q, K, V) = softmax(Q ? K^T / vd_k) ? V
```

**Пошаговое объяснение:**

```python
import torch
import torch.nn.functional as F

def scaled_dot_product_attention(Q, K, V, mask=None):
    """
    Q: [batch, seq_len, d_k]
    K: [batch, seq_len, d_k]
    V: [batch, seq_len, d_v]
    """
    d_k = Q.size(-1)
    
    # Шаг 1: Вычисляем "сырые" attention scores
    # Q @ K^T = [batch, seq_len, d_k] @ [batch, d_k, seq_len] = [batch, seq_len, seq_len]
    scores = torch.matmul(Q, K.transpose(-2, -1))
    
    # Шаг 2: Масштабируем на vd_k
    # Без масштабирования при больших d_k dot products становятся очень большими,
    # softmax насыщается, градиенты исчезают
    scores = scores / torch.sqrt(torch.tensor(d_k, dtype=torch.float32))
    
    # Шаг 3: Применяем маску (для decoder)
    if mask is not None:
        scores = scores.masked_fill(mask == 0, float('-inf'))
    
    # Шаг 4: Softmax — преобразуем в веса (сумма = 1)
    attention_weights = F.softmax(scores, dim=-1)
    
    # Шаг 5: Взвешенная сумма значений
    output = torch.matmul(attention_weights, V)
    
    return output, attention_weights
```

**Визуализация на примере:**

```
Вход: "The cat sat"

Q (токен "sat" спрашивает):  [0.2, 0.5, 0.1, ...]
K (все токены отвечают):
  - "The": [0.1, 0.3, 0.2, ...]
  - "cat": [0.3, 0.4, 0.1, ...]
  - "sat": [0.2, 0.5, 0.1, ...]

Scores (Q @ K^T):
  - "sat" > "The": 0.2?0.1 + 0.5?0.3 + ... = 0.17
  - "sat" > "cat": 0.2?0.3 + 0.5?0.4 + ... = 0.26
  - "sat" > "sat": 0.2?0.2 + 0.5?0.5 + ... = 0.29

После softmax:
  - "sat" > "The": 0.28
  - "sat" > "cat": 0.34
  - "sat" > "sat": 0.38
```

### 3.4 Почему vd_k?

**Проблема:** При больших d_k (например, 64) dot products становятся очень большими:

```
Если q_i, k_i ~ N(0, 1), то dot product ~ N(0, d_k)
При d_k = 64: стандартное отклонение = 8
```

Большие значения > softmax даёт почти one-hot > градиенты исчезают.

**Решение:** Делим на vd_k, чтобы вернуть variance ? 1.

---

## 4. Multi-Head Attention

### 4.1 Зачем нужны несколько "голов"?

Одна голова attention может захватить только один тип связи. **Multi-head позволяет моделировать разные типы зависимостей параллельно:**

| Голова | Что может захватывать |
|--------|----------------------|
| Голова 1 | Синтаксические связи (подлежащее-сказуемое) |
| Голова 2 | Семантические связи (слова одной темы) |
| Голова 3 | Позиционные паттерны (соседние слова) |
| Голова 4 | Anaphora resolution (местоимения > существительные) |
| ... | ... |

### 4.2 Математика Multi-Head Attention

```python
class MultiHeadAttention(torch.nn.Module):
    def __init__(self, d_model=512, n_heads=8):
        super().__init__()
        self.n_heads = n_heads
        self.d_k = d_model // n_heads  # 512 / 8 = 64
        
        # Проекции для каждой головы
        self.W_Q = torch.nn.Linear(d_model, d_model)
        self.W_K = torch.nn.Linear(d_model, d_model)
        self.W_V = torch.nn.Linear(d_model, d_model)
        
        # Финальная проекция
        self.W_O = torch.nn.Linear(d_model, d_model)
    
    def forward(self, Q, K, V, mask=None):
        batch_size = Q.size(0)
        
        # 1. Линейные проекции
        Q = self.W_Q(Q)  # [batch, seq_len, d_model]
        K = self.W_K(K)
        V = self.W_V(V)
        
        # 2. Разделение на головы
        # [batch, seq_len, d_model] > [batch, n_heads, seq_len, d_k]
        Q = Q.view(batch_size, -1, self.n_heads, self.d_k).transpose(1, 2)
        K = K.view(batch_size, -1, self.n_heads, self.d_k).transpose(1, 2)
        V = V.view(batch_size, -1, self.n_heads, self.d_k).transpose(1, 2)
        
        # 3. Attention для каждой головы параллельно
        attn_output, attn_weights = scaled_dot_product_attention(Q, K, V, mask)
        
        # 4. Конкатенация голов
        # [batch, n_heads, seq_len, d_k] > [batch, seq_len, d_model]
        attn_output = attn_output.transpose(1, 2).contiguous()
        attn_output = attn_output.view(batch_size, -1, self.n_heads * self.d_k)
        
        # 5. Финальная проекция
        output = self.W_O(attn_output)
        
        return output, attn_weights
```

### 4.3 Визуализация Multi-Head

```
Вход X [seq_len, d_model=512]
         v
    -----+----¬
    v    v    v   ... (8 голов)
  [Q?] [Q?] [Q?]
  [K?] [K?] [K?]
  [V?] [V?] [V?]
    v    v    v
[Attn?][Attn?][Attn?] ... [Attn?]
 [64]   [64]   [64]        [64]
    v    v    v             v
    L----+----+--------------
              v
         Concat [512]
              v
           W_O [512]
              v
         Output [512]
```

---

## 5. Positional Encoding

### 5.1 Проблема: Transformer не знает позицию

В отличие от RNN, где позиция неявно кодируется порядком обработки, Transformer обрабатывает все токены параллельно. **Без дополнительной информации "cat sat" и "sat cat" были бы идентичны.**

### 5.2 Решение: Sinusoidal Positional Encoding

Оригинальная статья использует синусоидальные функции:

```python
def positional_encoding(seq_len, d_model):
    """
    PE(pos, 2i)   = sin(pos / 10000^(2i/d_model))
    PE(pos, 2i+1) = cos(pos / 10000^(2i/d_model))
    """
    position = torch.arange(seq_len).unsqueeze(1)  # [seq_len, 1]
    div_term = torch.exp(torch.arange(0, d_model, 2) * (-math.log(10000.0) / d_model))
    
    pe = torch.zeros(seq_len, d_model)
    pe[:, 0::2] = torch.sin(position * div_term)  # чётные индексы
    pe[:, 1::2] = torch.cos(position * div_term)  # нечётные индексы
    
    return pe
```

### 5.3 Почему синусоиды?

1. **Уникальность:** Каждая позиция имеет уникальную комбинацию значений
2. **Относительные позиции:** PE(pos+k) можно выразить как линейную функцию PE(pos)
3. **Экстраполяция:** Работает для последовательностей длиннее, чем в обучении

```
Позиция 0:  [sin(0), cos(0), sin(0), cos(0), ...]  = [0, 1, 0, 1, ...]
Позиция 1:  [sin(1), cos(1), sin(0.001), cos(0.001), ...]
Позиция 2:  [sin(2), cos(2), sin(0.002), cos(0.002), ...]
...
```

### 5.4 Современные альтернативы

| Метод | Описание | Используется в |
|-------|----------|----------------|
| Learned Positional Embeddings | Обучаемые векторы | BERT, GPT-2 |
| RoPE (Rotary Position Embedding) | Вращение в комплексной плоскости | LLaMA, Mistral |
| ALiBi | Линейное смещение attention | BLOOM |
| Relative Position Encodings | Относительные позиции | T5 |

---

## 6. Дополнительные компоненты

### 6.1 Feed-Forward Network

После attention следует позиционно-независимая feed-forward сеть:

```python
class FeedForward(torch.nn.Module):
    def __init__(self, d_model=512, d_ff=2048, dropout=0.1):
        super().__init__()
        self.linear1 = torch.nn.Linear(d_model, d_ff)
        self.linear2 = torch.nn.Linear(d_ff, d_model)
        self.dropout = torch.nn.Dropout(dropout)
    
    def forward(self, x):
        # FFN(x) = max(0, xW? + b?)W? + b?
        x = self.linear1(x)
        x = F.relu(x)
        x = self.dropout(x)
        x = self.linear2(x)
        return x
```

**Зачем FFN?**
- Attention — линейная операция (взвешенная сумма)
- FFN добавляет нелинейность
- Увеличивает выразительность модели

### 6.2 Layer Normalization

```python
# Layer Norm нормализует по последнему измерению (features)
layer_norm = torch.nn.LayerNorm(d_model)
output = layer_norm(x)
```

**Формула:**

```
LayerNorm(x) = ? ? (x - ?) / v(?? + ?) + ?
```

Где:
- ?, ? — среднее и стандартное отклонение по features
- ?, ? — обучаемые параметры

### 6.3 Residual Connections

```python
# Вместо: output = sublayer(x)
# Используем: output = x + sublayer(x)

output = x + self.attention(x)
output = self.layer_norm(output)
```

**Зачем?**
- Улучшают обучение глубоких сетей
- Позволяют градиентам "течь" напрямую
- Skip connections помогают сохранять информацию

---

## 7. Transformer и безопасность AI

### 7.1 Архитектурные особенности > Уязвимости

| Особенность | Потенциальная уязвимость |
|-------------|-------------------------|
| **Self-attention на весь контекст** | Indirect injection: вредоносный текст в документе влияет на всё |
| **Autoregressive generation** | Каждый новый токен зависит от предыдущих > injection в начале критична |
| **Positional encoding** | Атаки на позиции: манипуляция порядком инструкций |
| **Attention weights** | Интерпретируемость > можно понять, на что модель "смотрит" |

### 7.2 SENTINEL Engines для анализа Transformer

SENTINEL включает engines для анализа внутренних состояний Transformer:

```python
from sentinel import scan  # Public API

# Анализ паттернов attention
attention_detector = AttentionPatternDetector()
result = attention_detector.analyze(
    attention_weights=model.get_attention_weights(),
    prompt=user_input
)

if result.anomalous_patterns:
    print(f"Обнаружены аномальные паттерны attention: {result.patterns}")

# Форензика скрытых состояний
forensics = HiddenStateForensics()
analysis = forensics.analyze(
    hidden_states=model.get_hidden_states(),
    expected_behavior="helpful_assistant"
)
```

### 7.3 Связь с атаками

| Атака | Эксплуатируемый компонент |
|-------|--------------------------|
| Prompt Injection | Self-attention: вредоносный текст получает высокие attention weights |
| Jailbreak | FFN: обход learned representations безопасности |
| Adversarial Suffixes | Positional encoding: специфические позиции для trigger |
| Context Hijacking | Long context attention: заполнение контекста вредоносным содержимым |

---

## 8. Практические задания

### Задание 1: Визуализация Attention

Используйте библиотеку BertViz для визуализации attention weights:

```python
from bertviz import head_view, model_view
from transformers import AutoTokenizer, AutoModel

# Загрузка модели
tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
model = AutoModel.from_pretrained("bert-base-uncased", output_attentions=True)

# Анализ предложения
sentence = "The cat sat on the mat because it was tired"
inputs = tokenizer(sentence, return_tensors="pt")
outputs = model(**inputs)

# Визуализация
tokens = tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
head_view(outputs.attentions, tokens)
```

**Вопросы для анализа:**
1. Какие головы связывают "it" с "cat"?
2. Как меняется attention от слоя к слою?
3. Есть ли головы, фокусирующиеся на синтаксисе?

<details>
<summary>?? Подсказка</summary>

Обратите внимание на головы в средних слоях (4-8). Ранние слои часто фокусируются на локальных паттернах, поздние — на более абстрактных связях.

</details>

### Задание 2: Вычисление размерностей

Для Transformer с параметрами:
- d_model = 768
- n_heads = 12
- n_layers = 12
- vocab_size = 30,000

Вычислите:

1. Размерность d_k для каждой головы
2. Количество параметров в одном Multi-Head Attention блоке
3. Общее количество параметров модели (приблизительно)

<details>
<summary>? Решение</summary>

1. **d_k = d_model / n_heads = 768 / 12 = 64**

2. **Multi-Head Attention параметры:**
   - W_Q: 768 ? 768 = 589,824
   - W_K: 768 ? 768 = 589,824
   - W_V: 768 ? 768 = 589,824
   - W_O: 768 ? 768 = 589,824
   - **Итого: 2,359,296 параметров**

3. **Общее количество:**
   - Token embeddings: 30,000 ? 768 ? 23M
   - Position embeddings: 512 ? 768 ? 0.4M
   - Per layer: ~7M (attention + FFN + norms)
   - 12 layers: 12 ? 7M ? 84M
   - **Итого: ~110M параметров** (BERT-base)

</details>

### Задание 3: Реализация Scaled Dot-Product Attention

Реализуйте функцию attention с нуля и протестируйте:

```python
import torch

def my_attention(Q, K, V, mask=None):
    """
    Реализуйте scaled dot-product attention.
    
    Args:
        Q: [batch, seq_len, d_k]
        K: [batch, seq_len, d_k]
        V: [batch, seq_len, d_v]
        mask: [seq_len, seq_len] или None
    
    Returns:
        output: [batch, seq_len, d_v]
        weights: [batch, seq_len, seq_len]
    """
    # Ваш код здесь
    pass

# Тест
Q = torch.randn(2, 4, 64)  # batch=2, seq_len=4, d_k=64
K = torch.randn(2, 4, 64)
V = torch.randn(2, 4, 64)

output, weights = my_attention(Q, K, V)
print(f"Output shape: {output.shape}")  # Должно быть [2, 4, 64]
print(f"Weights shape: {weights.shape}")  # Должно быть [2, 4, 4]
print(f"Weights sum per row: {weights.sum(dim=-1)}")  # Должно быть ~1.0
```

---

## 9. Проверочные вопросы

### Вопрос 1

Какая основная проблема RNN решается архитектурой Transformer?

- [ ] A) Недостаточное количество параметров
- [ ] B) Слишком быстрое обучение
- [x] C) Последовательная обработка и затухание градиентов
- [ ] D) Слишком простая архитектура

### Вопрос 2

Для чего используется scaling factor vd_k в механизме attention?

- [ ] A) Увеличить скорость вычислений
- [x] B) Предотвратить слишком большие значения dot product и насыщение softmax
- [ ] C) Уменьшить количество параметров
- [ ] D) Добавить нелинейность

### Вопрос 3

Что такое Multi-Head Attention?

- [ ] A) Attention с несколькими входными последовательностями
- [x] B) Параллельное применение нескольких attention механизмов с разными проекциями
- [ ] C) Attention только в первом слое
- [ ] D) Attention между encoder и decoder

### Вопрос 4

Зачем нужен positional encoding в Transformer?

- [x] A) Transformer не имеет понятия порядка токенов без дополнительной информации
- [ ] B) Для ускорения обучения
- [ ] C) Для уменьшения количества параметров
- [ ] D) Для улучшения генерации

### Вопрос 5

Какое ключевое отличие Decoder от Encoder?

- [ ] A) Decoder имеет больше слоёв
- [ ] B) Decoder использует другую активацию
- [x] C) Decoder использует masked attention, чтобы не "подглядывать" будущие токены
- [ ] D) Decoder не использует positional encoding

---

## 10. Связанные материалы

### SENTINEL Engines

| Engine | Описание | Урок |
|--------|----------|------|
| `AttentionPatternDetector` | Анализ паттернов attention для детекции аномалий | [Продвинутый Detection](../../06-Продвинутый-detection/) |
| `HiddenStateForensics` | Форензика скрытых состояний модели | [Продвинутый Detection](../../06-Продвинутый-detection/) |
| `TokenFlowAnalyzer` | Анализ потока информации между токенами | [Продвинутый Detection](../../06-Продвинутый-detection/) |

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

1. **Историю:** Проблемы RNN > революция Transformer (2017)
2. **Архитектуру:** Encoder-Decoder структура с N слоями
3. **Self-Attention:** Q, K, V проекции, scaled dot-product, softmax
4. **Multi-Head Attention:** Параллельные головы для разных типов связей
5. **Positional Encoding:** Синусоидальные функции для кодирования позиции
6. **Безопасность:** Связь архитектуры с уязвимостями и SENTINEL engines

**Ключевой вывод:** Transformer — это фундамент современных LLM. Понимание его архитектуры критически важно для понимания как возможностей, так и уязвимостей AI систем.

---

## Следующий урок

> [02. Encoder-Only модели: BERT, RoBERTa](02-encoder-only.md)

---

*AI Security Academy | Track 01: AI Fundamentals | Module 01.1: Model Types*
