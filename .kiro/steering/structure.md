# Структура проекта

## Философия организации

Компонентно-ориентированная структура: каждый компонент (BRAIN, SHIELD, STRIKE, IMMUNE) — автономный модуль со своей структурой, документацией и тестами.

## Паттерны каталогов

### Компоненты платформы
**Расположение**: `/src/sentinel/`, `/shield/`, `/immune/`, `/strike/`  
**Назначение**: Основной код компонентов  
**Пример**: `/src/sentinel/engines/` — движки детекции BRAIN

### Движки детекции
**Расположение**: `/src/sentinel/engines/`  
**Назначение**: Один движок = один файл, суффикс `_engine.py`  
**Пример**: `drift_engine.py`, `entropy_engine.py`

### Спецификации
**Расположение**: `/.kiro/specs/<feature>/`  
**Назначение**: requirements.md, design.md, tasks.md для каждой функции  
**Пример**: `/.kiro/specs/kill-switch/`

### C-модули
**Расположение**: `/shield/src/`, `/immune/hive/src/`  
**Назначение**: Источники на C, отдельные Makefile  
**Пример**: `/immune/hive/src/pattern_matcher.c`

## Соглашения об именовании

- **Python файлы**: snake_case (`drift_engine.py`)
- **C файлы**: snake_case (`pattern_matcher.c`, `web_dashboard.h`)
- **Каталоги**: kebab-case для specs, snake_case для кода
- **Классы**: PascalCase (`PatternMatcher`, `EntropyEngine`)

## Организация импортов

```python
# Python импорты
from sentinel.engines import DriftEngine  # Абсолютные
from .utils import helper                 # Относительные для внутренних
```

```c
// C включения
#include "config.h"       // Локальный проект
#include <wolfssl/ssl.h>  // Системные/библиотечные
```

## Принципы организации кода

- Каждый компонент изолирован и может собираться независимо
- Общие утилиты в `/src/sentinel/utils/` (Python) или `/common/` (C)
- Документация рядом с кодом (`docs/` в компоненте или README.md)
- Тесты зеркалят структуру кода (`tests/engines/` для `engines/`)

---
_Документируем паттерны, не деревья файлов. Новые файлы по паттерну не требуют обновления_
