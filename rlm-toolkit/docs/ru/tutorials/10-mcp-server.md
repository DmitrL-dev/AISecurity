# Туториал 10: MCP Server — Полное руководство

![Version](https://img.shields.io/badge/version-1.2.1-blue)

> Полное руководство по RLM-Toolkit MCP Server с VS Code Extension

## Что вы изучите

- Установка и настройка MCP Server
- Использование всех 10 MCP инструментов
- Настройка VS Code Extension
- Отслеживание экономии токенов

## Требования

```bash
pip install rlm-toolkit[mcp]
```

## Часть 1: Настройка MCP Server

### 1.1 Проверка установки

```bash
python -c "from rlm_toolkit.mcp import RLMServer; print('OK')"
```

### 1.2 Конфигурация IDE

**Antigravity / Cursor / Claude Desktop:**

Создайте `mcp_config.json`:
```json
{
  "mcpServers": {
    "rlm-toolkit": {
      "command": "python",
      "args": ["-m", "rlm_toolkit.mcp.server"]
    }
  }
}
```

### 1.3 Запуск сервера

Сервер запускается автоматически при подключении IDE.

---

## Часть 2: Все 10 MCP инструментов

### Инструменты контекста

```python
# Загрузить проект в контекст
rlm_load_context(path="./src", name="my_project")

# Поиск в контексте
rlm_query(question="где аутентификация?", context_name="my_project")

# Список контекстов
rlm_list_contexts()
```

### Инструменты анализа

```python
# Глубокий анализ через C³
rlm_analyze(goal="summarize")       # Суммаризация структуры
rlm_analyze(goal="find_bugs")       # Поиск багов
rlm_analyze(goal="security_audit")  # Аудит безопасности
rlm_analyze(goal="explain")         # Объяснение кода
```

### Инструменты памяти

```python
# H-MEM операции
rlm_memory(action="store", content="Важная информация")
rlm_memory(action="recall", topic="аутентификация")
rlm_memory(action="forget", topic="устаревшее")
rlm_memory(action="consolidate")
rlm_memory(action="stats")
```

### Инструменты управления

```python
# Статус сервера
rlm_status()

# Статистика сессии (экономия токенов)
rlm_session_stats()
rlm_session_stats(reset=True)

# Переиндексация (rate limit: 1/60s)
rlm_reindex()
rlm_reindex(force=True)

# Валидация здоровья индекса
rlm_validate()

# Настройки
rlm_settings(action="get")
rlm_settings(action="set", key="ttl_hours", value="48")
```

---

## Часть 3: VS Code Extension

### 3.1 Установка расширения

1. Откройте VS Code
2. Extensions → Поиск "RLM-Toolkit"
3. Install → Reload

Или установите VSIX:
```bash
code --install-extension rlm-toolkit-1.2.1.vsix
```

### 3.2 Sidebar Dashboard

Нажмите на иконку RLM в Activity Bar:

| Панель | Описание |
|--------|----------|
| **Status** | Здоровье сервера, количество кристаллов |
| **Session Stats** | Запросы, сохранённые токены, % экономии |
| **Quick Actions** | Reindex, Validate, Reset |

### 3.3 Первое использование

1. Откройте папку проекта
2. Нажмите "Initialize" в sidebar
3. Дождитесь индексации (< 30s для 2000 файлов)
4. Начинайте запросы!

---

## Часть 4: Экономия токенов

### Просмотр статистики в реальном времени

```python
stats = rlm_session_stats()
print(f"Запросов: {stats['session']['queries']}")
print(f"Сохранено: {stats['session']['tokens_saved']}")
print(f"Экономия: {stats['session']['savings_percent']}%")
```

### Пример метрик (SENTINEL)

| Метрика | Значение |
|---------|----------|
| Файлов индексировано | 1,967 |
| Raw context | 586.7M токенов |
| Сжато | 10.5M токенов |
| **Экономия** | **98.2%** |
| **Сжатие** | **56x** |

---

## Часть 5: Безопасность

### Шифрование (по умолчанию: ВКЛ)

```bash
# Отключить (только dev)
export RLM_SECURE_MEMORY=false
```

### Rate Limiting

`rlm_reindex` ограничен 1 запросом в 60 секунд.

### Защищённые файлы

`.rlm/.encryption_key` авто-исключён из git.

---

## Решение проблем

| Проблема | Решение |
|----------|---------|
| "MCP not available" | `pip install mcp` |
| "Rate limited" | Подождите 60 секунд |
| "Context not found" | Сначала загрузите контекст |
| Extension не показывается | Перезапустите VS Code |

---

## Следующие шаги

- [Архитектура Crystal](../concepts/crystal.md)
- [Freshness Monitoring](../concepts/freshness.md)
- [Безопасность](../concepts/security.md)
