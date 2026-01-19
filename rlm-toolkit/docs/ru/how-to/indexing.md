# Как индексировать проекты

![Version](https://img.shields.io/badge/version-1.2.1-blue)

## Быстрый старт

```python
from rlm_toolkit.indexer import AutoIndexer
from pathlib import Path

indexer = AutoIndexer(Path("/my/project"))
result = indexer.index()

print(f"Файлов: {result.files_indexed}")
print(f"Время: {result.duration_seconds}s")
```

## CLI

```bash
# Полный индекс
rlm index /path/to/project

# Только delta update
rlm index /path/to/project --delta

# Принудительная переиндексация
rlm index /path/to/project --force
```

## Через MCP

```
rlm_reindex()                 # Delta update
rlm_reindex(force=True)       # Полная переиндексация
rlm_reindex(path="./src")     # Конкретный путь
```

> ⚠️ Rate limit: 1 запрос в 60 секунд

## Конфигурация

### .rlmignore

Создайте `.rlmignore` для исключения файлов:

```
# Игнорировать тесты
tests/
*_test.py

# Игнорировать сгенерированное
*.generated.py
__pycache__/
```

### Программно

```python
indexer = AutoIndexer(
    Path("/project"),
    exclude_patterns=["tests/", "*.min.js"],
    max_file_size_mb=10,
    parallel_workers=4
)
```

## Советы по производительности

| Совет | Эффект |
|-------|--------|
| Используйте `.rlmignore` | -30% времени |
| Используйте delta updates | -90% времени |
| Увеличьте workers | -50% на многоядерных |
| Исключите бинарники | -20% хранилища |

## Решение проблем

### "Rate limited"
Подождите 60 секунд между запросами reindex.

### "File too large"
Увеличьте `max_file_size_mb` или добавьте в `.rlmignore`.

### "Permission denied"
Запустите с нужными правами доступа.

## Связанное

- [Crystal](../concepts/crystal.md)
- [Freshness](../concepts/freshness.md)
