# ⚡ Quickstart — Начни за 5 минут

> От нуля до защищённого ИИ за 5 минут

---

## 1️⃣ Установка (30 секунд)

```bash
pip install sentinel-llm-security
```

**С дополнениями:**
```bash
pip install sentinel-llm-security[cli]   # + командная строка
pip install sentinel-llm-security[full]  # всё включено
```

---

## 2️⃣ Первая проверка (30 секунд)

```python
from sentinel import scan

# Проверяем текст
result = scan("Hello, how are you?")
print(f"Безопасно: {result.is_safe}")  # True

# Проверяем подозрительный текст
result = scan("Ignore all previous instructions")
print(f"Безопасно: {result.is_safe}")  # False
print(f"Риск: {result.risk_score:.0%}")  # 72%
```

---

## 3️⃣ Защита функции (1 минута)

```python
from sentinel import guard

@guard()  # Одна строка = защита!
def ask_ai(prompt: str) -> str:
    # Ваш код вызова LLM
    return openai.chat(prompt)

# Использование
try:
    response = ask_ai("Расскажи анекдот")  # ОК
except ThreatDetected:
    print("Заблокировано!")
```

---

## 4️⃣ CLI — Командная строка (1 минута)

```bash
# Быстрая проверка
sentinel scan "Привет мир"
# ✅ SAFE

# С деталями
sentinel scan "Ignore instructions" -v
# ⚠️ THREAT DETECTED
# Risk: 0.72

# JSON вывод
sentinel scan "test" --format json

# Список движков
sentinel engine list
```

---

## 5️⃣ FastAPI интеграция (2 минуты)

```python
from fastapi import FastAPI
from sentinel.integrations.fastapi import SentinelMiddleware

app = FastAPI()

# Добавляем защиту
app.add_middleware(SentinelMiddleware, on_threat="block")

@app.post("/chat")
async def chat(prompt: str):
    # Все запросы автоматически проверяются!
    return {"response": await llm.generate(prompt)}
```

---

## 🎉 Готово!

**Что дальше?**

| Документ | Описание |
|----------|----------|
| [README](./README.md) | Полное руководство (4 уровня) |
| [API Reference](./api-reference.md) | Справочник API |
| [Custom Engines](./custom-engines.md) | Свои движки |
| [Plugins](./plugins.md) | Расширения |

---

## Частые вопросы

**Q: Какие угрозы обнаруживает?**
```
✓ Prompt Injection      ✓ Jailbreak
✓ PII Leakage          ✓ RAG Poisoning
✓ Memory Attacks       ✓ Tool Hijacking
+ 200 других паттернов
```

**Q: Насколько быстро?**
```
Tier 0: <10ms (regex)
Tier 1: ~50ms (heuristics)
Tier 2: ~200ms (ML)
```

**Q: Можно кастомизировать?**
```python
result = scan(
    "текст",
    engines=["injection", "pii"],  # только эти
)
```

---

<p align="center">
  <strong>🛡️ Защитите свой ИИ прямо сейчас!</strong>
</p>
