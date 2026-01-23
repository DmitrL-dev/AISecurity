# Туториал 14: Memory Bridge v2.1

> **Цель**: Освоить кросс-сессионную персистентность с enterprise-масштабом управления памятью

## Чему вы научитесь

- Zero-config обнаружение проекта с Auto-Mode
- Архитектура Hierarchical Memory (L0-L3)
- Семантическая маршрутизация для 56x компрессии токенов
- Git hooks для автоматического извлечения фактов
- Каузальные рассуждения для отслеживания решений

## Предварительные требования

- Пройден [Туториал 10: MCP Server](10-mcp-server.md)
- Установлен VS Code Extension v2.1.0
- Python 3.10+ с установленным `rlm-toolkit`

---

## Шаг 1: Cold Start с Project Discovery

Memory Bridge v2.1 может проанализировать ваш проект за доли секунды:

```python
from rlm_toolkit.memory_bridge.mcp_tools_v2 import rlm_discover_project

# Авто-определение типа проекта, стека и структуры
result = rlm_discover_project(project_root="./my-project")

print(f"Тип: {result['project_type']}")  # → Python MCP Server
print(f"Файлов: {result['python_files']}")  # → 150
print(f"LOC: {result['total_loc']}")        # → 15,000
print(f"Домены: {result['domains']}")       # → ['api', 'auth', 'database']
```

**Производительность**: 0.04 секунды для 79K LOC проекта.

---

## Шаг 2: Понимание иерархии L0-L3

Memory Bridge организует факты в 4 уровня:

```
L0: PROJECT   → Высокий уровень: "FastAPI проект с JWT auth"
L1: DOMAIN    → Доменные области: "Auth использует bcrypt + JWT"
L2: MODULE    → По файлам: "user.py обрабатывает регистрацию"
L3: CODE      → Уровень функций: "validate_token() проверяет expiry"
```

### Добавление фактов разных уровней

```python
from rlm_toolkit.memory_bridge.mcp_tools_v2 import rlm_add_hierarchical_fact

# L0 - Обзор проекта
rlm_add_hierarchical_fact(
    content="Микросервисная архитектура с 5 сервисами",
    level=0,  # L0_PROJECT
)

# L1 - Доменное знание
rlm_add_hierarchical_fact(
    content="Auth сервис использует OAuth2 с refresh токенами",
    level=1,  # L1_DOMAIN
    domain="auth"
)

# L2 - Модуль-специфичное
rlm_add_hierarchical_fact(
    content="token_service.py обрабатывает генерацию и валидацию JWT",
    level=2,  # L2_MODULE
    domain="auth",
    module="token_service"
)

# L3 - Уровень кода с референсом на строки
rlm_add_hierarchical_fact(
    content="generate_token() создаёт JWT с 24ч expiry",
    level=3,  # L3_CODE
    domain="auth",
    module="token_service",
    code_ref="token_service.py:45-67"
)
```

---

## Шаг 3: Enterprise Context запросы

`rlm_enterprise_context` — ваш основной инструмент для интеллектуальных запросов:

```python
from rlm_toolkit.memory_bridge.mcp_tools_v2 import rlm_enterprise_context

result = rlm_enterprise_context(
    query="Как работает аутентификация?",
    max_tokens=3000,
    include_causal=True
)

print(result["context"])
# → Семантическая маршрутизация загружает только auth-related факты
# → L0 обзор + L1 auth domain + релевантные L2/L3

print(result["token_count"])  # → 850 (vs 15,000 без routing)
print(result["compression"])  # → 17.6x экономия для этого запроса
```

**Ключевая особенность**: Только **релевантные** факты загружаются на основе семантического сходства.

---

## Шаг 4: Установка Git Hooks для авто-извлечения

Автоматически извлекайте факты из каждого коммита:

```python
from rlm_toolkit.memory_bridge.mcp_tools_v2 import rlm_install_git_hooks

result = rlm_install_git_hooks(hook_type="post-commit")
print(result["message"])  # → "Installed post-commit hook"
```

### Что извлекается

| Тип изменения | Пример факта |
|---------------|--------------|
| Новый класс | "Added class `UserService` in user_service" |
| Новая функция | "Implemented function `validate_token` in auth" |
| Major рефакторинг | "Major refactoring of database (150 lines changed)" |

### Тестирование hook

```bash
git add my_file.py
git commit -m "Add new feature"
# Вывод: Extracted 4 facts, auto-approved 4
```

---

## Шаг 5: Каузальные рассуждения

Отслеживайте ПОЧЕМУ были приняты решения:

```python
from rlm_toolkit.memory_bridge.mcp_tools_v2 import (
    rlm_record_causal_decision,
    rlm_get_causal_chain
)

# Записать решение
rlm_record_causal_decision(
    decision="Использовать PostgreSQL вместо MongoDB",
    reasons=["Требуется ACID compliance", "Экспертиза команды"],
    consequences=["Нужны скрипты миграции", "Управление схемой"],
    constraints=["Must support transactions"],
    alternatives=["MySQL", "MongoDB"]
)

# Позже, запросить reasoning
chain = rlm_get_causal_chain(query="выбор базы данных")
print(chain["decisions"][0]["reasons"])
# → ["Требуется ACID compliance", "Экспертиза команды"]
```

---

## Шаг 6: Health Check и мониторинг

Мониторьте вашу систему памяти:

```python
from rlm_toolkit.memory_bridge.mcp_tools_v2 import rlm_health_check

health = rlm_health_check()

print(health["status"])  # → "healthy"
print(health["components"]["store"]["facts_count"])  # → 150
print(health["components"]["router"]["embeddings_enabled"])  # → True
```

### VS Code Dashboard

Откройте RLM-Toolkit dashboard чтобы увидеть:
- Общее количество фактов
- Распределение L0-L3
- Здоровье Store и Router
- Обнаруженные домены

---

## Шаг 7: TTL и жизненный цикл фактов

Установите срок действия для временных фактов:

```python
from rlm_toolkit.memory_bridge.mcp_tools_v2 import (
    rlm_add_hierarchical_fact,
    rlm_get_stale_facts
)

# Добавить факт с TTL
fact = rlm_add_hierarchical_fact(
    content="Цель Sprint 42: реализовать payment gateway",
    level=1,
    ttl_days=14  # Истекает через 2 недели
)

# Проверить stale факты
stale = rlm_get_stale_facts()
for fact in stale["facts"]:
    print(f"Устарел: {fact['content']}")
```

---

## Полный пример: Настройка проекта

```python
"""Полная настройка Memory Bridge v2.1 для нового проекта."""

from rlm_toolkit.memory_bridge.mcp_tools_v2 import (
    rlm_discover_project,
    rlm_install_git_hooks,
    rlm_enterprise_context,
    rlm_health_check,
)

# 1. Обнаружить проект (cold start)
discovery = rlm_discover_project()
print(f"Обнаружено {discovery['python_files']} файлов, {len(discovery['domains'])} доменов")

# 2. Установить git hooks
rlm_install_git_hooks(hook_type="post-commit")
print("Git hooks установлены - факты будут авто-извлекаться на коммитах")

# 3. Проверить health
health = rlm_health_check()
assert health["status"] == "healthy"
print(f"Memory Bridge healthy: {health['components']['store']['facts_count']} фактов")

# 4. Запросить с enterprise context
context = rlm_enterprise_context(
    query="Опиши архитектуру проекта",
    max_tokens=2000
)
print(f"Контекст загружен: {context['token_count']} токенов")

# Готов к разработке!
```

---

## Упражнения

1. **Setup**: Запустите `rlm_discover_project` на вашем проекте
2. **Иерархия**: Добавьте 3 факта разных уровней (L0, L1, L2)
3. **Hooks**: Установите git hook и сделайте коммит с новой Python функцией
4. **Causal**: Запишите design decision с reasons и alternatives
5. **Query**: Используйте `rlm_enterprise_context` чтобы спросить о проекте

---

## Следующие шаги

- [Документация Memory Bridge](../../memory-bridge.md) — Глубокое погружение
- [API Reference](../../api_reference.md) — Все 18 MCP инструментов
- [Туториал 7: H-MEM](07-hmem.md) — Основы иерархической памяти
- [Туториал 10: MCP Server](10-mcp-server.md) — IDE интеграция

---

## Итоги

| Функция | Инструмент | Назначение |
|---------|------------|------------|
| Cold Start | `rlm_discover_project` | Быстрый анализ проекта |
| Добавить факты | `rlm_add_hierarchical_fact` | L0-L3 хранение знаний |
| Запрос | `rlm_enterprise_context` | Семантическая загрузка контекста |
| Авто-извлечение | `rlm_install_git_hooks` | Извлечение на коммитах |
| Решения | `rlm_record_causal_decision` | Отслеживание reasoning |
| Мониторинг | `rlm_health_check` | Здоровье системы |

**Ключевой вывод**: Memory Bridge v2.1 обеспечивает zero-friction enterprise память с 56x компрессией токенов, позволяя LLM работать с неограниченным контекстом проекта.
