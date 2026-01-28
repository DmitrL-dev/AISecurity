# Интеграция SENTINEL

> **Модуль 05.3: Интеграция SENTINEL в AI-приложения**

---

## Обзор

Интеграция SENTINEL — практическое руководство по интеграции фреймворка SENTINEL в AI-приложения.

---

## Уроки

### [01. Архитектура движков](01-engine-architecture.md)
- Обзор архитектуры SENTINEL Brain
- Входные движки (PromptInjectionDetector, JailbreakClassifier)
- Основные движки (TrustBoundaryAnalyzer, ContextAnalyzer)
- Выходные движки (SafetyClassifier, HallucinationDetector)
- Оркестратор для единого конвейера

### [02. Практическая интеграция](02-practical-integration.md)
- Паттерны интеграции
- Опции конфигурации
- Лучшие практики

---

## Архитектура SENTINEL

```
Входные движки → Основные движки → Выходные движки
       ↓               ↓               ↓
              ОРКЕСТРАТОР (координирует все)
```

---

## Категории движков

| Категория | Движки | Назначение |
|-----------|--------|------------|
| **Входные** | PromptInjectionDetector, JailbreakClassifier | Защита препроцессинга |
| **Основные** | TrustBoundaryAnalyzer, ContextAnalyzer | Runtime-анализ |
| **Выходные** | SafetyClassifier, HallucinationDetector | Валидация ответов |

---

*AI Security Academy | Модуль 05.3*
