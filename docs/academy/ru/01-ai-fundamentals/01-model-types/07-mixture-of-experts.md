# Mixture of Экспертs: Mixtral, Switch

> **Уровень:** Средний  
> **Время:** 40 минут  
> **Трек:** 01 — AI Fundamentals  
> **Модуль:** 01.1 — Типы моделей

---

## Цели обучения

- [ ] Понять архитектуру Mixture of Экспертs (MoE)
- [ ] Объяснить sparse routing
- [ ] Сравнить dense и sparse модели
- [ ] Понять security implications

---

## Проблема Dense моделей

### Вычислительная сложность

Dense Transformer: **все параметры** активируются для каждого токена.

```
GPT-3: 175B параметров > 175B активаций на токен
```

**Вопрос:** Можно ли активировать только нужные части?

---

## Mixture of Экспертs (MoE)

### Ключевая идея

Вместо одной большой FFN — несколько "экспертов", из которых выбираются только некоторые:

```
Token > Router > Эксперт 1 (активен)
              > Эксперт 2 (неактивен)
              > Эксперт 3 (активен)
              > Эксперт 4 (неактивен)
              > ...
```

### Компоненты

1. **Экспертs** — независимые FFN сети
2. **Router (Gating Network)** — выбирает активных экспертов
3. **Top-K selection** — обычно k=1 или k=2

### Математика Router

```python
# Gating scores
scores = softmax(W_gate @ token_embedding)

# Top-K selection
top_k_indices = scores.topk(k=2)

# Взвешенная комбинация
output = sum(scores[i] * Эксперт[i](token) for i in top_k_indices)
```

---

## Switch Transformer

**Google, 2021** — "Switch Transformers: Scaling to Trillion Parameter Models"

### Особенности

- Top-1 routing (один эксперт на токен)
- 1.6T параметров, но только ~100B активных
- Упрощённый routing

### Архитектура

```
Transformer Layer:
+-- Attention (shared)
L-- FFN > Switch Layer:
         +-- Router
         L-- Эксперт 1...N (выбирается один)
```

---

## Mixtral 8x7B

**Mistral AI, декабрь 2023**

### Архитектура

- 8 экспертов ? 7B параметров = 56B всего
- Top-2 routing > 12.9B активных параметров
- Превосходит LLaMA 2 70B при меньшей стоимости

### Сравнение

| Модель | Всего Params | Активных Params | Performance |
|--------|--------------|-----------------|-------------|
| LLaMA 70B | 70B | 70B | Baseline |
| Mixtral 8x7B | 56B | 12.9B | Better |

---

## Load Balancing

### Проблема: Эксперт Collapse

Без балансировки router может направлять все токены к одному эксперту.

### Решение: Auxiliary Loss

```python
# Load balancing loss
aux_loss = ? * sum((fraction_i - target_fraction)?)

# Добавляется к main loss
total_loss = main_loss + aux_loss
```

---

## Security: MoE Implications

### 1. Routing Manipulation

Атакующий может попытаться направить токены к специфическим экспертам:

```
Crafted input > Specific Эксперт > Unwanted output
```

### 2. Эксперт Specialization Exploitation

Если один эксперт "специализируется" на harmful content:

```
Jailbreak > Router > "Harmful" Эксперт > Bypass
```

### SENTINEL Protection

```python
from sentinel import scan  # Public API

engine = MoEGuardEngine()
result = engine.analyze(
    prompt=user_input,
    routing_info=model.last_routing  # if available
)

if result.suspicious_routing:
    print(f"Unusual Эксперт activation pattern detected")
```

### Engines

| Engine | Назначение |
|--------|------------|
| MoEGuardEngine | Мониторинг routing patterns |
| ЭкспертActivationAnalyzer | Анализ активации экспертов |
| RoutingAnomalyDetector | Аномалии routing |

---

## Практика

### Задание: Понимание Routing

Если есть доступ к Mixtral через API с routing info:

1. Отправьте несколько промптов разных типов
2. Проанализируйте какие эксперты активируются
3. Есть ли паттерны для определённых тем?

---

## Следующий урок

> [08. State Space Models: Mamba, S4](08-state-space.md)

---

*AI Security Academy | Track 01: AI Fundamentals*
