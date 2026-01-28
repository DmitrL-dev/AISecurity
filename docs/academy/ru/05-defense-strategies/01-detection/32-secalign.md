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

```python
class SecAlignDataGenerator:
    def generate_pair(self, task: str, injection: str):
        injected = f"{task}\n\nIGNORE ALL. {injection}"
        
        rejected = {
            "prompt": injected,
            "response": f"OK, {injection}",  # BAD
        }
        
        chosen = {
            "prompt": injected,
            "response": "Это попытка инъекции. Продолжаю обычную работу.",  # GOOD
        }
        
        return rejected, chosen
```

---

## Следующий урок

→ [33. ZEDD](33-zedd.md)
