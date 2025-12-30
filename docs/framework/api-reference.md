# 📖 SENTINEL API Reference

> Полный справочник всех классов, функций и методов

---

## Содержание

1. [Главные функции](#главные-функции)
2. [Core модуль](#core-модуль)
3. [Finding и Severity](#finding-и-severity)
4. [AnalysisContext](#analysiscontext)
5. [BaseEngine](#baseengine)
6. [Pipeline](#pipeline)
7. [Hooks](#hooks)

---

## Главные функции

### `scan(prompt, response=None, engines=None, **kwargs)`

Главная функция для анализа текста.

**Параметры:**

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `prompt` | `str` | *обязательный* | Текст для анализа |
| `response` | `str` | `None` | Ответ LLM (для egress-анализа) |
| `engines` | `list[str]` | `None` | Список движков (None = все) |

**Возвращает:** `EngineResult`

**Примеры:**

```python
# Простой вызов
result = scan("Hello world")

# С указанием движков
result = scan("Test", engines=["injection", "pii"])

# С ответом LLM
result = scan(
    prompt="Расскажи секрет",
    response="Я не могу раскрыть конфиденциальную информацию"
)
```

---

### `guard(engines=None, on_threat="raise")`

Декоратор для защиты функций.

**Параметры:**

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `engines` | `list[str]` | `None` | Список движков |
| `on_threat` | `str` | `"raise"` | Действие: `"raise"`, `"log"`, `"block"` |

**Примеры:**

```python
@guard()
def my_function(prompt: str) -> str:
    return ask_llm(prompt)

@guard(engines=["injection"], on_threat="log")
def another_function(prompt: str) -> str:
    # При угрозе только логирование, не блокировка
    return ask_llm(prompt)
```

---

## Core модуль

### `sentinel.core.finding`

#### `class Severity(Enum)`

Уровни критичности угроз.

| Значение | Вес | Описание |
|----------|-----|----------|
| `CRITICAL` | 1.0 | Критическая угроза, немедленное действие |
| `HIGH` | 0.8 | Высокая угроза |
| `MEDIUM` | 0.5 | Средняя угроза |
| `LOW` | 0.25 | Низкая угроза |
| `INFO` | 0.1 | Информационное сообщение |

```python
from sentinel.core.finding import Severity

# Сравнение
assert Severity.CRITICAL > Severity.HIGH
assert Severity.LOW < Severity.MEDIUM
```

#### `class Confidence(Enum)`

Уровни уверенности в обнаружении.

| Значение | Коэффициент | Описание |
|----------|-------------|----------|
| `HIGH` | 0.9 | Высокая уверенность |
| `MEDIUM` | 0.7 | Средняя уверенность |
| `LOW` | 0.3 | Низкая уверенность |

#### `class Finding`

Одно обнаружение (finding).

**Атрибуты:**

| Атрибут | Тип | Описание |
|---------|-----|----------|
| `engine` | `str` | Имя движка |
| `severity` | `Severity` | Критичность |
| `confidence` | `Confidence` | Уверенность |
| `title` | `str` | Короткое название |
| `description` | `str` | Подробное описание |
| `evidence` | `str` | Доказательство (часть текста) |
| `location` | `str` | Где найдено |
| `remediation` | `str` | Как исправить |
| `metadata` | `dict` | Дополнительные данные |
| `id` | `str` | Уникальный ID (auto) |
| `timestamp` | `datetime` | Время создания (auto) |

**Свойства:**

| Свойство | Тип | Описание |
|----------|-----|----------|
| `risk_score` | `float` | Счёт риска (0.0-1.0) |

**Методы:**

```python
finding = Finding(
    engine="injection",
    severity=Severity.HIGH,
    confidence=Confidence.HIGH,
    title="Injection detected",
    description="Found 'ignore instructions' pattern",
    evidence="Please ignore previous instructions..."
)

# Преобразования
dict_data = finding.to_dict()
json_str = finding.to_json()
sarif = finding.to_sarif()

# Создание из словаря
finding2 = Finding.from_dict(dict_data)
```

---

## AnalysisContext

Контекст анализа с полной информацией.

**Создание:**

```python
from sentinel.core.context import AnalysisContext

# Простой контекст
ctx = AnalysisContext(prompt="Hello")

# Полный контекст
ctx = AnalysisContext(
    prompt="Вопрос пользователя",
    response="Ответ LLM",
    user_id="user123",
    session_id="sess456",
    model="gpt-4",
    provider="openai",
    history=[...],  # История сообщений
    retrieved_documents=[...],  # RAG документы
    available_tools=["search", "calculator"],
)
```

**Атрибуты:**

| Атрибут | Тип | Описание |
|---------|-----|----------|
| `prompt` | `str` | Входной запрос |
| `response` | `str?` | Ответ LLM |
| `user_id` | `str?` | ID пользователя |
| `session_id` | `str?` | ID сессии |
| `request_id` | `str` | ID запроса (auto) |
| `model` | `str?` | Название модели |
| `provider` | `str?` | Провайдер (openai, anthropic) |
| `history` | `list[Message]` | История сообщений |
| `retrieved_documents` | `list[dict]` | RAG документы |
| `available_tools` | `list[str]` | Доступные инструменты |
| `tool_calls` | `list[dict]` | Вызовы инструментов |
| `metadata` | `dict` | Метаданные |

**Свойства:**

```python
ctx.has_response      # bool — есть ли ответ
ctx.is_multi_turn     # bool — многоходовая беседа?
ctx.history_length    # int — количество сообщений
ctx.full_conversation # str — вся беседа как текст
```

**Методы:**

```python
# Добавить сообщение в историю
ctx.add_to_history("user", "Привет")
ctx.add_to_history("assistant", "Здравствуйте!")

# Создать копию с ответом
ctx2 = ctx.with_response("Ответ модели")

# Сериализация
data = ctx.to_dict()
ctx = AnalysisContext.from_dict(data)

# Быстрое создание
ctx = AnalysisContext.simple("Hello")
```

---

## BaseEngine

Базовый класс для создания движков.

**Атрибуты класса:**

| Атрибут | Тип | По умолчанию | Описание |
|---------|-----|--------------|----------|
| `name` | `str` | `"base_engine"` | Уникальное имя |
| `version` | `str` | `"1.0.0"` | Версия |
| `category` | `str` | `"general"` | Категория |
| `description` | `str` | `""` | Описание |
| `supports_prompt` | `bool` | `True` | Поддержка prompt |
| `supports_response` | `bool` | `False` | Поддержка response |
| `supports_multimodal` | `bool` | `False` | Поддержка изображений |
| `tier` | `int` | `1` | Уровень (0-3) |
| `typical_latency_ms` | `float` | `10.0` | Типичная задержка |

**Методы:**

```python
class MyEngine(BaseEngine):
    name = "my_engine"
    
    def initialize(self) -> None:
        """Вызывается один раз при первом использовании."""
        self.model = load_model()
        self._initialized = True
    
    def analyze(self, context: AnalysisContext) -> EngineResult:
        """Главный метод анализа (обязательный)."""
        findings = []
        # ... логика обнаружения ...
        return self._create_result(findings)
    
    def analyze_batch(self, contexts: list) -> list:
        """Пакетный анализ (опционально)."""
        return [self.analyze(ctx) for ctx in contexts]
```

**Вспомогательные методы:**

```python
# Создать результат из списка findings
result = self._create_result(findings, execution_time_ms=5.0)

# Создать finding
finding = self._create_finding(
    severity=Severity.HIGH,
    confidence=Confidence.HIGH,
    title="Угроза",
    description="Описание",
    evidence="Доказательство"
)
```

---

## Pipeline

Конвейер выполнения движков.

**Создание:**

```python
from sentinel.core.pipeline import Pipeline, PipelineConfig

# Простое создание
pipeline = Pipeline(engines=[Engine1(), Engine2()])

# С конфигурацией
config = PipelineConfig(
    parallel=True,
    max_workers=4,
    tier0_timeout_ms=10.0,
    tier1_timeout_ms=50.0,
    tier2_timeout_ms=200.0,
    total_timeout_ms=500.0,
    early_exit_enabled=True,
    early_exit_threshold=0.9,
)
pipeline = Pipeline(engines=[...], config=config)
```

**Методы:**

```python
# Синхронный анализ
result = pipeline.analyze_sync(context)

# Асинхронный анализ
result = await pipeline.analyze(context)

# Добавить движок
pipeline.add_engine(NewEngine())
```

**PipelineResult:**

| Атрибут | Тип | Описание |
|---------|-----|----------|
| `is_safe` | `bool` | Безопасно? |
| `risk_score` | `float` | Счёт риска (0.0-1.0) |
| `findings` | `FindingCollection` | Все обнаружения |
| `engine_results` | `list` | Результаты каждого движка |
| `total_time_ms` | `float` | Общее время |
| `engines_executed` | `int` | Количество движков |
| `early_exit` | `bool` | Был ранний выход? |

---

## Hooks

Система расширений на основе pluggy.

### Доступные хуки

| Хук | Когда вызывается | Что можно делать |
|-----|------------------|------------------|
| `sentinel_configure` | При инициализации | Изменить конфиг |
| `sentinel_register_engines` | При загрузке | Добавить движки |
| `sentinel_register_rules` | При загрузке | Добавить правила |
| `sentinel_before_analysis` | До анализа | Изменить контекст |
| `sentinel_after_analysis` | После анализа | Изменить результаты |
| `sentinel_on_finding` | На каждый finding | Фильтрация/модификация |
| `sentinel_on_threat` | При угрозе | Алертинг |
| `sentinel_format_output` | При форматировании | Кастомный формат |

### Пример плагина

```python
from sentinel.hooks import hookimpl

class MyPlugin:
    @hookimpl
    def sentinel_before_analysis(self, context):
        context.prompt = context.prompt.lower()
        return context
```

---

## Константы и утилиты

### `sentinel.core.engine`

```python
from sentinel.core.engine import (
    register_engine,  # Декоратор регистрации
    get_engine,       # Получить класс по имени
    list_engines,     # Список всех имён
    get_engines_by_category,  # По категории
)
```

### `sentinel.engines`

```python
from sentinel.engines import (
    list_engines,  # Список движков
    get_engine,    # Получить движок
)
```

---

<p align="center">
  Версия API: 1.0.0
</p>
