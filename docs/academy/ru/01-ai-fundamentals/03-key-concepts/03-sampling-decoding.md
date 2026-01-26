# Sampling и Decoding

> **Уровень:** ����������  
> **Время:** 35 минут  
> **Трек:** 01 — AI Fundamentals  
> **Модуль:** 01.3 — Ключевые концепции  
> **Версия:** 1.0

---

## Цели обучения

- [ ] Понять как модели выбирают следующий токен
- [ ] Знать основные стратегии: greedy, top-k, top-p, temperature
- [ ] Понять влияние параметров на output
- [ ] Связать sampling с reproducibility и security

---

## 1. От Logits к Tokens

### 1.1 Model Output: Logits

```python
# Модель возвращает logits для каждого токена в vocabulary
logits = model(input_ids)  # [batch, seq_len, vocab_size]
                           # [1, 10, 50257] для GPT-2

# logits[-1] = scores для next token
next_logits = logits[0, -1, :]  # [50257]
```

### 1.2 Softmax → Probabilities

```python
import torch.nn.functional as F

probs = F.softmax(next_logits, dim=-1)
# probs[i] = probability токена i

# Пример:
# probs[15496] = 0.15  # "Hello"
# probs[42] = 0.08     # "the"
# probs[...] = ...
```

---

## 2. Стратегии Sampling

### 2.1 Greedy Decoding

**Идея:** Всегда выбирать токен с максимальной вероятностью.

```python
def greedy(logits):
    return logits.argmax()

# Pros: Deterministic, fast
# Cons: Скучный, повторяющийся output
```

### 2.2 Temperature

**Идея:** Контроль "остроты" распределения.

```python
def sample_with_temperature(logits, temperature=1.0):
    scaled_logits = logits / temperature
    probs = F.softmax(scaled_logits, dim=-1)
    return torch.multinomial(probs, num_samples=1)

# temperature = 0.1: Почти greedy (confident)
# temperature = 1.0: Original distribution
# temperature = 2.0: More random (creative)
```

### 2.3 Top-K Sampling

**Идея:** Выборка только из K наиболее вероятных токенов.

```python
def top_k(logits, k=50):
    values, indices = logits.topk(k)
    probs = F.softmax(values, dim=-1)
    chosen_idx = torch.multinomial(probs, num_samples=1)
    return indices[chosen_idx]
```

### 2.4 Top-P (Nucleus) Sampling

**Идея:** Выборка из минимального набора токенов с cumulative probability >= p.

```python
def top_p(logits, p=0.9):
    sorted_logits, sorted_indices = logits.sort(descending=True)
    cumulative_probs = F.softmax(sorted_logits, dim=-1).cumsum(dim=-1)
    
    # Find cutoff
    mask = cumulative_probs <= p
    mask[..., 1:] = mask[..., :-1].clone()
    mask[..., 0] = True
    
    # Zero everything after cutoff
    sorted_logits[~mask] = float('-inf')
    probs = F.softmax(sorted_logits, dim=-1)
    
    chosen_idx = torch.multinomial(probs, num_samples=1)
    return sorted_indices[chosen_idx]
```

### 2.5 Сравнение стратегий

| Стратегия | Creativity | Coherence | Use Case |
|-----------|------------|-----------|----------|
| **Greedy** | Low | High | Code, facts |
| **Temp=0.3** | Low-Med | High | Balanced |
| **Temp=1.0** | Medium | Medium | Creative |
| **Top-k=50** | Medium | Good | General |
| **Top-p=0.9** | Adaptive | Good | Recommended |

---

## 3. Практическое использование

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

model = AutoModelForCausalLM.from_pretrained("gpt2")
tokenizer = AutoTokenizer.from_pretrained("gpt2")

# Разные sampling стратегии
outputs = model.generate(
    input_ids,
    max_new_tokens=50,
    do_sample=True,        # Enable sampling
    temperature=0.7,
    top_k=50,
    top_p=0.9,
    repetition_penalty=1.1
)
```

---

## 4. Security Implications

### 4.1 Reproducibility

```python
# Проблема: random sampling не воспроизводим
torch.manual_seed(42)
output1 = model.generate(..., do_sample=True)

torch.manual_seed(42)
output2 = model.generate(..., do_sample=True)

# output1 == output2 только если seed одинаковый!
```

### 4.2 Sampling Manipulation

```python
# Temperature влияет на probability harmful outputs
# Low temp: Model follows training distribution
# High temp: Increases probability of rare tokens

# Некоторые jailbreaks эксплуатируют high temperature
```

---

## 5. Резюме

1. **Logits → Probabilities:** softmax conversion
2. **Greedy:** Deterministic, boring
3. **Temperature:** Control randomness
4. **Top-k/Top-p:** Limit vocabulary
5. **Security:** Reproducibility, manipulation

---

## Следующий урок

→ [Module README](README.md)

---

*AI Security Academy | Track 01: AI Fundamentals | Module 01.3: Key Concepts*
