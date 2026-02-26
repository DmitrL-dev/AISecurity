# SecAlign Defense

> **Трек:** 05 — Стратегии защиты  
> **Урок:** 32  
> **Уровень:** Эксперт

---

## Обзор

SecAlign — техника **preference optimization**, обучающая LLM распознавать и отклонять prompt injection. Достигает **~0% успеха инъекций**.

---

## Теория

```
Traditional: Input → [External Filter] → LLM → Output
SecAlign:    Input → LLM (с SecAlign) → Safe Output
```

### Результаты

| Метрика | До SecAlign | После |
|---------|-------------|-------|
| Успех инъекций | 40-60% | ~0% |
| Helpfulness | 100% | 98.5% |

---

## Практика

```rust
struct SecAlignDataGenerator;

impl SecAlignDataGenerator {
    fn generate_pair(
        &self,
        task: &str,
        injection: &str,
    ) -> (TrainingPair, TrainingPair) {
        let injected = format!("{}\n\nIGNORE ALL. {}", task, injection);

        let rejected = TrainingPair {
            prompt: injected.clone(),
            response: format!("OK, {}", injection), // BAD
        };

        let chosen = TrainingPair {
            prompt: injected,
            response: "Это попытка инъекции. Продолжаю обычную работу.".to_string(), // GOOD
        };

        (rejected, chosen)
    }
}
```

---

## Следующий урок

→ [33. ZEDD](33-zedd.md)
