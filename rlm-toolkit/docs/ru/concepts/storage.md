# Архитектура Storage

![Version](https://img.shields.io/badge/version-1.2.1-blue)

> **SQLite-based persistence** для кристаллов, метрик и сессионных данных

## Обзор

RLM-Toolkit использует SQLite для персистентного хранения:
- Crystal index (примитивы, связи)
- Статистика сессий (экономия токенов)
- Метаданные (TTL, freshness)

## Расположение

```
.rlm/
├── rlm.db              # SQLite база данных
├── crystals/           # Сериализованные кристаллы
├── memory/             # H-MEM данные
├── cache/              # Кэш запросов
└── .encryption_key     # AES ключ (автогенерация)
```

> ⚠️ `.rlm/` исключён из git через `.gitignore`

## API

### get_storage()

```python
from rlm_toolkit.storage import get_storage
from pathlib import Path

storage = get_storage(Path("/project"))

# Сохранить кристалл
storage.save_crystal(file_path, crystal_data)

# Загрузить все
all_crystals = storage.load_all()

# Получить статистику
stats = storage.get_stats()
# {'total_crystals': 1967, 'total_tokens': 586700000, 'db_size_mb': 12.5}
```

### Метаданные

```python
# Get/set метаданные
storage.set_metadata("ttl_hours", 24)
ttl = storage.get_metadata("ttl_hours")

# Статистика сессии
storage.set_metadata("session_stats", {
    "queries": 42,
    "tokens_saved": 1000000
})
```

### Запросы Freshness

```python
# Получить изменённые файлы (нужна переиндексация)
modified = storage.get_modified_files(Path("/project"))

# Получить устаревшие кристаллы
stale = storage.get_stale_crystals(ttl_hours=24)
```

## Схема

### Таблица crystals
| Колонка | Тип | Описание |
|---------|-----|----------|
| path | TEXT | Путь к файлу (primary key) |
| crystal | BLOB | Сериализованный кристалл |
| hash | TEXT | Хеш контента |
| indexed_at | TIMESTAMP | Время индексации |

### Таблица metadata
| Колонка | Тип | Описание |
|---------|-----|----------|
| key | TEXT | Ключ метаданных |
| value | TEXT | JSON значение |

## Производительность

| Метрика | Значение |
|---------|----------|
| Индекс 1967 файлов | < 30s |
| Латентность запроса | < 10ms |
| Размер БД (SENTINEL) | 12.5 MB |

## Связанное

- [Crystal](crystal.md)
- [Freshness Monitoring](freshness.md)
