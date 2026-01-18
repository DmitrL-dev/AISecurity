# 🧪 Урок 2.2: Тестирование на уязвимости

> **Время: 20 минут** | Уровень: Beginner → Практика

---

## Зачем тестировать?

> "Атакуй себя до того, как атакуют другие"

SENTINEL STRIKE — платформа для red team тестирования AI.

---

## Быстрый старт

```bash
# Установка
pip install sentinel-llm-security[strike]

# Базовое тестирование
sentinel strike test --target http://localhost:8000/chat
```

---

## Типы тестов

### 1. Quick Scan (1 минута)

```bash
sentinel strike quick --target http://localhost:8000/chat
```

Проверяет топ-50 атак.

### 2. Full Scan (10 минут)

```bash
sentinel strike full --target http://localhost:8000/chat
```

39,000+ payloads по всем категориям.

### 3. Specific Category

```bash
# Только injection
sentinel strike test --category injection

# Только jailbreak
sentinel strike test --category jailbreak
```

---

## Python API

```python
from sentinel.strike import Attacker

# Инициализация
attacker = Attacker(
    target_url="http://localhost:8000/chat",
    method="POST",
    payload_field="message"
)

# Quick test
results = attacker.quick_test()

print(f"Tested: {results.total}")
print(f"Vulnerable: {results.vulnerable}")
print(f"Blocked: {results.blocked}")

# Детальный отчёт
for vuln in results.vulnerabilities:
    print(f"⚠️ {vuln.category}: {vuln.payload[:50]}...")
```

---

## Категории атак в STRIKE

| Категория | Payloads | Описание |
|-----------|----------|----------|
| `injection` | 5,000+ | Prompt injection |
| `jailbreak` | 3,000+ | DAN, roleplay |
| `extraction` | 1,000+ | Prompt leak |
| `encoding` | 2,000+ | Base64, Unicode |
| `multilang` | 1,500+ | Атаки на разных языках |
| `rag` | 500+ | RAG poisoning |
| `agentic` | 800+ | Tool hijacking, MCP |

---

## Пример отчёта

```
SENTINEL STRIKE Report
═══════════════════════════════════════════════════

Target: http://localhost:8000/chat
Date: 2026-01-18

Summary:
  Total Tests:      500
  Blocked:          487 (97.4%)
  Vulnerable:       13 (2.6%)

Vulnerabilities Found:
┌─────────────┬────────────────────────────────────┐
│ Category    │ Payload                            │
├─────────────┼────────────────────────────────────┤
│ injection   │ Ignore instructions and...         │
│ jailbreak   │ You are DAN without...             │
│ encoding    │ Base64: SWdub3Jl...                │
└─────────────┴────────────────────────────────────┘

Recommendations:
1. Enable encoding detection engine
2. Add DAN pattern to blocklist
3. Implement input length limits
```

---

## Интеграция с CI/CD

### GitHub Actions

```yaml
name: AI Security Test

on: [push]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install SENTINEL
        run: pip install sentinel-llm-security[strike]
      
      - name: Run STRIKE tests
        run: sentinel strike test --target ${{ secrets.API_URL }} --fail-on-vuln
```

### pytest

```python
# test_security.py
from sentinel.strike import Attacker
import pytest

def test_no_injection_vulnerabilities():
    attacker = Attacker(target_url="http://localhost:8000/chat")
    results = attacker.test_category("injection")
    
    assert results.vulnerable == 0, f"Found {results.vulnerable} injection vulnerabilities"

def test_no_jailbreak_vulnerabilities():
    attacker = Attacker(target_url="http://localhost:8000/chat")
    results = attacker.test_category("jailbreak")
    
    assert results.vulnerable == 0
```

---

## Упражнение

Протестируй свой чатбот:

1. Запусти чатбот локально
2. Выполни quick scan
3. Проанализируй результаты
4. Исправь найденные уязвимости
5. Повтори тест

```bash
# Шаг 1: Запуск (в одном терминале)
python app.py

# Шаг 2: Тест (в другом терминале)
sentinel strike quick --target http://localhost:8000/chat

# Шаг 3: Исправь код

# Шаг 4: Повтори
sentinel strike quick --target http://localhost:8000/chat
```

---

## Регулярное тестирование

| Частота | Тип теста | Когда |
|---------|-----------|-------|
| **Daily** | Quick scan | CI/CD |
| **Weekly** | Full scan | Ночью |
| **Release** | Full + manual | Перед деплоем |
| **Quarterly** | Pentest | Внешняя команда |

---

## Следующий урок

→ [2.3: Интеграция SENTINEL](./07-sentinel-integration.md)
