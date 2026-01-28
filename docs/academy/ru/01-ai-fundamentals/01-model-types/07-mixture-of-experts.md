# Mixture of Experts: Mixtral, Switch

> **Уровень:** Intermediate  
> **Время:** 40 минут  
> **Трек:** 01 — Основы AI  
> **Модуль:** 01.1 — Типы моделей

---

## Цели обучения

- [ ] Понять архитектуру Mixture of Experts (MoE)
- [ ] Объяснить sparse routing
- [ ] Сравнить dense и sparse модели
- [ ] Понять последствия для безопасности

---

## Проблема с Dense моделями

### Вычислительная сложность

Dense Transformer: **все параметры** активируются для каждого токена.

```
GPT-3: 175B параметров → 175B активаций на токен
```

**Вопрос:** Можем ли мы активировать только нужные части?

---

## Mixture of Experts (MoE)

### Ключевая идея

Вместо одного большого FFN — несколько «экспертов», из которых выбираются только некоторые:

```
Token → Router → Expert 1 (активен)
              → Expert 2 (неактивен)
              → Expert 3 (активен)
              → Expert 4 (неактивен)
              → ...
```

### Компоненты

1. **Эксперты** — независимые FFN сети
2. **Router (Gating Network)** — выбирает активных экспертов
3. **Top-K selection** — обычно k=1 или k=2

### Математика Router

```python
# Gating scores
scores = softmax(W_gate @ token_embedding)

# Top-K selection
top_k_indices = scores.topk(k=2)

# Взвешенная комбинация
output = sum(scores[i] * expert[i](token) for i in top_k_indices)
```

---

## Switch Transformer

**Google, 2021** — «Switch Transformers: Scaling to Trillion Parameter Models»

### Особенности

- Top-1 routing (один эксперт на токен)
- 1.6T параметров, но только ~100B активных
- Упрощённый routing

### Архитектура

```
Transformer Layer:
├── Attention (общий)
└── FFN → Switch Layer:
         ├── Router
         └── Expert 1...N (один выбирается)
```

---

## Mixtral 8x7B

**Mistral AI, декабрь 2023**

### Архитектура

- 8 экспертов × 7B параметров = 56B всего
- Top-2 routing → 12.9B активных параметров
- Превосходит LLaMA 2 70B при меньшей стоимости

### Сравнение

| Модель | Всего Params | Активных Params | Производительность |
|--------|--------------|-----------------|-------------------|
| LLaMA 70B | 70B | 70B | Baseline |
| Mixtral 8x7B | 56B | 12.9B | Лучше |

---

## Load Balancing

### Проблема: Expert Collapse

Без балансировки router может направлять все токены к одному эксперту.

### Решение: Auxiliary Loss

```python
# Load balancing loss
aux_loss = α * sum((fraction_i - target_fraction)²)

# Добавляется к основному loss
total_loss = main_loss + aux_loss
```

---

## Безопасность: Последствия MoE

### 1. Routing Manipulation

Атакующий может попытаться направить токены к конкретным экспертам:

```
Crafted input → Specific expert → Нежелательный output
```

### 2. Expert Specialization Exploitation

Если один эксперт «специализируется» на вредоносном контенте:

```
Jailbreak → Router → «Вредоносный» эксперт → Bypass
```

### SENTINEL Protection

```python
from sentinel import scan  # Public API

engine = MoEGuardEngine()
result = engine.analyze(
    prompt=user_input,
    routing_info=model.last_routing  # если доступно
)

if result.suspicious_routing:
    print(f"Unusual expert activation pattern detected")
```

### Engines

| Engine | Назначение |
|--------|------------|
| MoEGuardEngine | Мониторинг паттернов routing |
| ExpertActivationAnalyzer | Анализ активации экспертов |
| RoutingAnomalyDetector | Аномалии routing |

---

## Практика

### Задание: Понимание Routing

Если у вас есть доступ к Mixtral через API с routing info:

1. Отправьте несколько промптов разных типов
2. Проанализируйте какие эксперты активируются
3. Есть ли паттерны для конкретных тем?

---

## Следующий урок

→ [08. State Space Models: Mamba, S4](08-state-space.md)

---

*AI Security Academy | Трек 01: Основы AI*
