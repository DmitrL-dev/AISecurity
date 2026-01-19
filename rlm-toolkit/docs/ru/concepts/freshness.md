# Freshness Monitoring

![Version](https://img.shields.io/badge/version-1.2.1-blue)

> **TTL-based индекс свежести** для надёжного контекста

## Обзор

Freshness Monitoring обеспечивает актуальность индекса:
- Обнаружение устаревших файлов (изменённых после индексации)
- Валидация cross-reference (битые символы)
- Автоматические delta-обновления

## Конфигурация

| Настройка | Default | Описание |
|-----------|---------|----------|
| `ttl_hours` | 24 | Время жизни кристаллов |
| `auto_reindex` | true | Авто delta-update при запросе |

## API

### CrossReferenceValidator

```python
from rlm_toolkit.freshness import CrossReferenceValidator

validator = CrossReferenceValidator(crystals)

# Получить статистику валидации
stats = validator.get_validation_stats()
# {'total_symbols': 2359, 'resolved': 2341, 'unresolved': 18}

# Проверить конкретный символ
is_valid = validator.validate_reference("MyClass.method")
```

### ActualityReviewQueue

```python
from rlm_toolkit.freshness import ActualityReviewQueue

queue = ActualityReviewQueue(storage)

# Получить файлы для ревью
stale_files = queue.get_review_candidates()

# Отметить как проверенные
queue.mark_reviewed(file_path)
```

## MCP Интеграция

### rlm_validate
Проверка здоровья индекса:

```
rlm_validate()
# Returns: symbols, stale_files, health status
```

### rlm_reindex
Ручное обновление (rate-limit 1/60s):

```
rlm_reindex()            # Delta update
rlm_reindex(force=True)  # Полная переиндексация
```

## Метрики (v1.2.1)

| Метрика | SENTINEL |
|---------|----------|
| Символов индексировано | 2,359 |
| Уровень резолюции | 99.2% |
| Детекция stale | < 100ms |

## Best Practices

1. **Установите подходящий TTL** — 24h для активной разработки, 72h для стабильного
2. **Используйте delta updates** — быстрее полной переиндексации
3. **Проверяйте health регулярно** — интегрируйте `rlm_validate` в CI

## Связанное

- [Crystal](crystal.md)
- [Storage](storage.md)
- [MCP Server](../mcp-server.md)
