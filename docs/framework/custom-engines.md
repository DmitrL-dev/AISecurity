# 🛠️ Создание собственного Engine

> Пошаговое руководство по созданию движка обнаружения

---

## Зачем свой Engine?

SENTINEL включает 200+ встроенных движков, но иногда нужно:
- Обнаруживать специфические для вашей компании паттерны
- Интегрировать собственные ML модели
- Добавить проверки бизнес-логики

---

## Быстрый старт (5 минут)

### Минимальный Engine

```python
from sentinel.core.engine import BaseEngine, EngineResult
from sentinel.core.finding import Finding, Severity, Confidence
from sentinel.core.context import AnalysisContext


class MyFirstEngine(BaseEngine):
    """Мой первый движок обнаружения."""
    
    # Обязательно: уникальное имя
    name = "my_first_engine"
    
    # Опционально: метаданные
    category = "custom"
    description = "Обнаруживает слово 'секрет'"
    
    def analyze(self, context: AnalysisContext) -> EngineResult:
        """Главный метод — здесь вся логика."""
        findings = []
        
        if "секрет" in context.prompt.lower():
            findings.append(Finding(
                engine=self.name,
                severity=Severity.MEDIUM,
                confidence=Confidence.HIGH,
                title="Найдено слово 'секрет'",
                description="Пользователь упомянул секрет",
            ))
        
        return self._create_result(findings)
```

### Использование

```python
# Создаём и используем
engine = MyFirstEngine()
ctx = AnalysisContext(prompt="Расскажи секрет")
result = engine.analyze(ctx)

print(result.is_safe)       # False
print(result.risk_score)    # 0.35
```

---

## Полный пример (Production-ready)

```python
import re
import time
from typing import List, Pattern
from sentinel.core.engine import BaseEngine, EngineResult, register_engine
from sentinel.core.finding import Finding, Severity, Confidence
from sentinel.core.context import AnalysisContext


@register_engine  # Автоматическая регистрация в реестре
class CompanySecretDetector(BaseEngine):
    """
    Обнаружение корпоративных секретов.
    
    Ищет:
    - Внутренние кодовые названия проектов
    - Номера конфиденциальных документов
    - Имена VIP клиентов
    """
    
    # === Метаданные ===
    name = "company_secret_detector"
    version = "2.1.0"
    category = "privacy"
    description = "Обнаружение корпоративных секретов"
    
    # === Возможности ===
    supports_prompt = True
    supports_response = True  # Проверяем и ответы!
    supports_multimodal = False
    
    # === Производительность ===
    tier = 1  # Средний приоритет
    typical_latency_ms = 5.0
    
    # === Паттерны (конфиденциально) ===
    PROJECT_CODENAMES = [
        r"project\s+(phoenix|titan|nebula)",
        r"(op|operation)\s+\w+\s+alpha",
    ]
    
    DOCUMENT_PATTERNS = [
        r"DOC-\d{4}-\d{6}",  # DOC-2024-123456
        r"CONF-[A-Z]{2}-\d+",  # CONF-RU-12345
    ]
    
    VIP_PATTERNS = [
        r"(vip|важный)\s+клиент",
    ]
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        self._patterns: List[Pattern] = []
        
    def initialize(self) -> None:
        """
        Ленивая инициализация.
        
        Вызывается один раз при первом analyze().
        Используйте для:
        - Компиляции regex
        - Загрузки ML моделей
        - Подключения к БД
        """
        all_patterns = (
            self.PROJECT_CODENAMES + 
            self.DOCUMENT_PATTERNS + 
            self.VIP_PATTERNS
        )
        
        self._patterns = [
            re.compile(p, re.IGNORECASE | re.UNICODE)
            for p in all_patterns
        ]
        
        self._initialized = True
        self._logger.info(f"Скомпилировано {len(self._patterns)} паттернов")
    
    def analyze(self, context: AnalysisContext) -> EngineResult:
        """
        Основной анализ.
        
        Args:
            context: Содержит prompt, response, metadata
            
        Returns:
            EngineResult с findings и risk_score
        """
        self.ensure_initialized()  # Авто-инициализация
        
        findings = []
        
        # Собираем весь текст для проверки
        texts_to_check = [
            ("prompt", context.prompt)
        ]
        if context.response:
            texts_to_check.append(("response", context.response))
        
        # Проверяем каждый текст
        for location, text in texts_to_check:
            for pattern in self._patterns:
                matches = pattern.findall(text)
                if matches:
                    findings.append(self._create_finding(
                        severity=self._get_severity(pattern),
                        confidence=Confidence.HIGH,
                        title=f"Корпоративный секрет в {location}",
                        description=f"Найден паттерн: {pattern.pattern}",
                        evidence=self._extract_evidence(text, matches[0]),
                        location=location,
                        remediation="Удалите конфиденциальную информацию",
                        metadata={
                            "pattern": pattern.pattern,
                            "matches": matches[:3],  # Первые 3
                        }
                    ))
        
        return self._create_result(findings)
    
    def _get_severity(self, pattern: Pattern) -> Severity:
        """Определяем критичность по типу паттерна."""
        pattern_str = pattern.pattern
        
        if "project" in pattern_str or "DOC-" in pattern_str:
            return Severity.HIGH
        elif "vip" in pattern_str:
            return Severity.CRITICAL
        else:
            return Severity.MEDIUM
    
    def _extract_evidence(self, text: str, match: str, context_chars: int = 50) -> str:
        """Извлекаем контекст вокруг совпадения."""
        try:
            idx = text.lower().find(match.lower())
            start = max(0, idx - context_chars)
            end = min(len(text), idx + len(match) + context_chars)
            return f"...{text[start:end]}..."
        except:
            return match
```

---

## Жизненный цикл Engine

```
┌─────────────────────────────────────────────────────┐
│                   Жизненный цикл                     │
├─────────────────────────────────────────────────────┤
│                                                     │
│  1. __init__()          ← Создание экземпляра       │
│         │                 (БЕЗ тяжёлых операций!)   │
│         ▼                                           │
│  2. initialize()        ← Первый вызов analyze()    │
│         │                 (загрузка моделей)        │
│         ▼                                           │
│  3. analyze() ─────────►  Повторяется N раз         │
│         │               ◄─────────────────          │
│         ▼                                           │
│  4. Конец жизни         ← GC / shutdown             │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## Tier System

| Tier | Время | Примеры | Когда использовать |
|------|-------|---------|-------------------|
| 0 | <10ms | Regex, YARA | Простые паттерны |
| 1 | ~50ms | NLP, Heuristics | Большинство случаев |
| 2 | ~200ms | ML модели | Сложная логика |
| 3 | >500ms | LLM calls | Только критичные |

```python
class FastEngine(BaseEngine):
    tier = 0  # Выполняется первым
    
class MLEngine(BaseEngine):
    tier = 2  # Выполняется после tier 0 и 1
```

---

## Советы и лучшие практики

### ✅ Делайте

```python
# 1. Используйте ленивую инициализацию
def initialize(self):
    self.model = load_heavy_model()  # Только при первом вызове

# 2. Возвращайте evidence
findings.append(Finding(
    evidence=context.prompt[start:end],  # Конкретное место
    ...
))

# 3. Логируйте
self._logger.info(f"Проанализировано за {time_ms}ms")

# 4. Обрабатывайте ошибки
try:
    result = risky_operation()
except Exception as e:
    self._logger.error(f"Ошибка: {e}")
    return self._create_result([])  # Fail open
```

### ❌ Не делайте

```python
# 1. Не загружайте модели в __init__
def __init__(self):
    self.model = load_model()  # ❌ Замедляет импорт

# 2. Не блокируйте надолго
def analyze(self):
    time.sleep(10)  # ❌ Блокирует pipeline

# 3. Не игнорируйте timeout
def analyze(self):
    for _ in range(10**9):  # ❌ Бесконечный цикл
        pass

# 4. Не храните состояние между вызовами
def analyze(self):
    self.counter += 1  # ❌ Не потокобезопасно
```

---

## Тестирование

```python
import pytest
from my_engine import CompanySecretDetector
from sentinel.core.context import AnalysisContext


class TestCompanySecretDetector:
    
    @pytest.fixture
    def engine(self):
        return CompanySecretDetector()
    
    def test_safe_prompt(self, engine):
        ctx = AnalysisContext(prompt="Привет, как дела?")
        result = engine.analyze(ctx)
        
        assert result.is_safe
        assert result.risk_score == 0.0
    
    def test_project_codename(self, engine):
        ctx = AnalysisContext(prompt="Статус Project Phoenix?")
        result = engine.analyze(ctx)
        
        assert not result.is_safe
        assert result.findings.count == 1
        assert result.findings.findings[0].severity == Severity.HIGH
    
    def test_document_pattern(self, engine):
        ctx = AnalysisContext(prompt="Открой DOC-2024-123456")
        result = engine.analyze(ctx)
        
        assert not result.is_safe
        assert "DOC-" in result.findings.findings[0].evidence
```

---

## Регистрация и использование

### Способ 1: Декоратор (рекомендуется)

```python
@register_engine
class MyEngine(BaseEngine):
    name = "my_engine"
    ...
```

### Способ 2: Через plugin

```python
# sentinel_plugins.py
class MyPlugin:
    def sentinel_register_engines(self):
        return [MyEngine, AnotherEngine]
```

### Способ 3: Вручную

```python
from sentinel.core.engine import register_engine

register_engine(MyEngine)
```

---

<p align="center">
  <strong>Создавайте движки, защищайте ИИ! 🛡️</strong>
</p>
