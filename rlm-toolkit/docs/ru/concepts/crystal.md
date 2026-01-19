# Архитектура C³ Crystal

![Version](https://img.shields.io/badge/version-1.2.1-blue)

> **Context Consciousness Crystal** — Семантическое сжатие для неограниченного контекста

## Обзор

C³ обеспечивает 56-кратное сжатие контекста через иерархическую экстракцию знаний.

```
ProjectCrystal
├── ModuleCrystal (пакет)
│   └── FileCrystal (файл)
│       └── Primitive (функция, класс, импорт...)
```

## Компоненты

### Примитивы
Атомарные элементы кода, извлечённые HPE (Hierarchical Primitive Extractor):

| Тип | Описание |
|-----|----------|
| `FUNCTION` | Определения функций |
| `CLASS` | Определения классов |
| `METHOD` | Методы классов |
| `IMPORT` | Импорты |
| `CONSTANT` | Константы модуля |
| `DOCSTRING` | Строки документации |

```python
from rlm_toolkit.crystal import HPEExtractor, PrimitiveType

extractor = HPEExtractor()
primitives = extractor.extract_from_source(source_code)

for p in primitives:
    print(f"{p.ptype}: {p.name} (строка {p.source_line})")
```

### FileCrystal
Представление одного файла:

```python
from rlm_toolkit.crystal import FileCrystal

crystal = extractor.extract_from_file("module.py", content)
print(f"Примитивов: {len(crystal.primitives)}")
print(f"Сжатие: {crystal.compression_ratio}x")
```

### CrystalIndexer
Быстрый поиск по всем примитивам:

```python
from rlm_toolkit.crystal import CrystalIndexer

indexer = CrystalIndexer()
indexer.index_file(crystal)

results = indexer.search("authentication", top_k=5)
```

### SafeCrystal
Обёртка с защитой целостности (детекция подмены):

```python
from rlm_toolkit.crystal import wrap_crystal

safe = wrap_crystal(crystal, secret_key=b"...")
assert safe.verify()  # Проверка целостности
```

## Интеграция

### MCP Server
C³ используется инструментом `rlm_analyze`:

```
rlm_analyze(goal="summarize")      # Использует HPE
rlm_analyze(goal="find_bugs")      # Сканирует примитивы
rlm_analyze(goal="security_audit") # Обнаружение паттернов
```

### Метрики (v1.2.1)

| Метрика | SENTINEL Codebase |
|---------|-------------------|
| Файлов индексировано | 1,967 |
| Call relations | 17,095 |
| Символов | 2,359 |
| Сжатие | 56x |

## Связанное

- [Freshness Monitoring](freshness.md)
- [Storage](storage.md)
- [MCP Server](../mcp-server.md)
