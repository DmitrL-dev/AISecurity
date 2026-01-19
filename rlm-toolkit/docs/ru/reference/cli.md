# CLI Reference

![Version](https://img.shields.io/badge/version-1.2.1-blue)

> **Интерфейс командной строки** для RLM-Toolkit

## Установка

CLI включён в RLM-Toolkit:

```bash
pip install rlm-toolkit
rlm --help
```

## Команды

### rlm run

Выполнение RLM запроса из командной строки:

```bash
# Базовый запрос
rlm run --model ollama:llama3 --query "Объясни AI"

# С контекстом из файла
rlm run --model openai:gpt-4o --context отчёт.pdf --query "Суммаризируй ключевые выводы"

# С опциями
rlm run \
  --model anthropic:claude-3 \
  --context large_document.txt \
  --query "Извлеки все даты" \
  --max-iterations 20 \
  --max-cost 5.0 \
  --output results.json
```

**Опции:**

| Опция | Описание | Default |
|-------|----------|---------|
| `--model` | provider:model | Обязательно |
| `--context` | Файл/директория | - |
| `--query` | Вопрос | Обязательно |
| `--max-iterations` | Макс итераций RLM | 50 |
| `--max-cost` | Бюджет в USD | 10.0 |
| `--output` | Выходной файл (json/txt) | stdout |

### rlm eval

Запуск бенчмарков:

```bash
# OOLONG бенчмарк
rlm eval oolong --model ollama:llama3 --dataset ./oolong_pairs.json

# Кастомный бенчмарк
rlm eval custom --model openai:gpt-4o --test-file ./my_tests.yaml

# С детальным выводом
rlm eval oolong --model ollama:llama3 --verbose --report eval_report.html
```

**Опции:**

| Опция | Описание |
|-------|----------|
| `--dataset` | Путь к тестовому датасету |
| `--verbose` | Показать результаты по каждому примеру |
| `--report` | Генерировать HTML отчёт |
| `--parallel` | Параллельный запуск тестов |

### rlm trace

Анализ трейсов сессии:

```bash
# Показать последнюю сессию
rlm trace --session latest

# Показать конкретную сессию
rlm trace --session abc123

# Экспорт трейсов
rlm trace --session latest --export traces.json

# Анализ затрат
rlm trace --session latest --costs
```

**Пример вывода:**
```
Session: abc123
Started: 2026-01-19 10:30:00
Duration: 45.2s
-----------------------
Traces: 12
  - rlm.run: 8
  - embedding: 3
  - completion: 1

Cost breakdown:
  - gpt-4o: $0.0342
  - ada-002: $0.0001
  Total: $0.0343
```

### rlm index

Индексация проекта:

```bash
# Полный индекс
rlm index /path/to/project

# Delta update
rlm index /path/to/project --delta

# Принудительная переиндексация
rlm index /path/to/project --force

# Показать статистику
rlm index /path/to/project --stats
```

### rlm repl

Интерактивный REPL:

```bash
# Запустить REPL
rlm repl --model ollama:llama3

# С памятью
rlm repl --model openai:gpt-4o --memory

# С загруженным контекстом
rlm repl --model ollama:llama3 --context ./src
```

**Команды REPL:**
```
>>> /help              # Показать справку
>>> /load file.txt     # Загрузить контекст
>>> /memory            # Показать статистику памяти
>>> /cost              # Показать затраты
>>> /export chat.json  # Экспорт разговора
>>> /quit              # Выход
```

## Примеры

### Пример 1: Pipeline анализа кода

```bash
#!/bin/bash
# analyze_codebase.sh

# Индексировать проект
rlm index ./my_project --force

# Запустить аудит безопасности
rlm run \
  --model openai:gpt-4o \
  --context ./my_project \
  --query "Найди уязвимости безопасности" \
  --output security_report.json

# Сгенерировать сводку
rlm run \
  --model ollama:llama3 \
  --context security_report.json \
  --query "Суммаризируй находки в markdown" \
  --output SECURITY_AUDIT.md
```

### Пример 2: Обработка документов

```bash
# Обработка нескольких документов
for doc in ./documents/*.pdf; do
  rlm run \
    --model ollama:llama3 \
    --context "$doc" \
    --query "Извлеки ключевые пункты как JSON" \
    --output "$(basename "$doc" .pdf).json"
done

# Объединить результаты
rlm run \
  --model openai:gpt-4o \
  --context ./documents/*.json \
  --query "Создай единую сводку" \
  --output combined_summary.md
```

### Пример 3: Интерактивное исследование

```bash
# Запустить сессию исследования с памятью
rlm repl --model openai:gpt-4o --memory

>>> /load research_papers/
Загружено 45 файлов (12.3 MB)

>>> Какие основные темы в этих статьях?
Анализирую... Найдено 5 основных тем: ...

>>> /memory
Episodes: 2
Traces: 1

>>> Углубись в тему #3
Анализ темы 3: ...

>>> /export research_session.json
Экспортировано в research_session.json

>>> /quit
```

## Конфигурация

### Переменные окружения

| Переменная | Описание |
|------------|----------|
| `OPENAI_API_KEY` | OpenAI API ключ |
| `ANTHROPIC_API_KEY` | Anthropic API ключ |
| `RLM_DEFAULT_MODEL` | Модель по умолчанию |
| `RLM_MAX_COST` | Бюджет по умолчанию |

### Конфиг файл

Создайте `~/.rlm/config.yaml`:

```yaml
default_model: ollama:llama3
max_cost: 10.0
max_iterations: 50
observability:
  enabled: true
  exporter: console
```

## Связанное

- [Быстрый старт](../quickstart.md)
- [MCP Server](../mcp-server.md)
- [Observability](observability.md)
