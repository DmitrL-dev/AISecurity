# Фильтрация вывода для безопасности LLM

> **Уровень:** Средний  
> **Время:** 45 минут  
> **Трек:** 05 — Стратегии защиты  
> **Модуль:** 05.2 — Guardrails  
> **Версия:** 2.0 (Production)

---

## Цели обучения

По завершении этого урока вы сможете:

- [ ] Объяснить почему фильтрация вывода критична для LLM-приложений
- [ ] Реализовать классификацию и блокировку контента
- [ ] Детектировать PII и секреты в ответах LLM
- [ ] Создавать пайплайны санитизации ответов
- [ ] Интегрировать фильтрацию вывода с SENTINEL

---

## 1. Архитектура фильтрации вывода

```
┌────────────────────────────────────────────────────────────────────┐
│                    ПАЙПЛАЙН ФИЛЬТРАЦИИ ВЫВОДА                     │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  СЫРОЙ ВЫВОД LLM                                                   │
│      ↓                                                             │
│  ╔═══════════════════════════════════════════════════════════════╗ │
│  ║  СЛОЙ 1: КЛАССИФИКАЦИЯ КОНТЕНТА                               ║ │
│  ║  • Детекция вредного контента                                 ║ │
│  ║  • Проверка нарушений политики                                ║ │
│  ║  • Детекция успешного jailbreak                               ║ │
│  ╚═══════════════════════════════════════════════════════════════╝ │
│      ↓                                                             │
│  ╔═══════════════════════════════════════════════════════════════╗ │
│  ║  СЛОЙ 2: ДЕТЕКЦИЯ УТЕЧЕК ДАННЫХ                               ║ │
│  ║  • Детекция PII (email, телефон, SSN)                         ║ │
│  ║  • Детекция секретов (API ключи, токены)                      ║ │
│  ║  • Детекция утечки системного промпта                         ║ │
│  ╚═══════════════════════════════════════════════════════════════╝ │
│      ↓                                                             │
│  ╔═══════════════════════════════════════════════════════════════╗ │
│  ║  СЛОЙ 3: САНИТИЗАЦИЯ                                          ║ │
│  ║  • Редактирование PII                                         ║ │
│  ║  • Маскирование секретов                                      ║ │
│  ║  • Трансформация контента                                     ║ │
│  ╚═══════════════════════════════════════════════════════════════╝ │
│      ↓                                                             │
│  ОТФИЛЬТРОВАННЫЙ ВЫВОД                                             │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 2. Классификация контента

```python
from dataclasses import dataclass
from typing import Dict, List
from enum import Enum

class ContentCategory(Enum):
    SAFE = "safe"
    HARMFUL = "harmful"
    POLICY_VIOLATION = "policy_violation"
    JAILBREAK_SUCCESS = "jailbreak_success"
    DATA_LEAK = "data_leak"

class ContentClassifier:
    """Классификация вывода LLM для безопасности."""
    
    HARMFUL_PATTERNS = [
        r'how\s+to\s+(make|create|build)\s+(a\s+)?(bomb|weapon|explosive)',
        r'step.by.step\s+(guide|instructions?)\s+(to|for)\s+(hack|attack)',
    ]
    
    JAILBREAK_SUCCESS_PATTERNS = [
        r'as\s+(DAN|an?\s+unrestricted)',
        r'without\s+(any\s+)?restrictions?',
        r'ignoring\s+(my\s+)?(previous\s+)?guidelines',
        r'I\s+(can|will)\s+now\s+do\s+anything',
    ]
    
    def classify(self, text: str) -> ClassificationResult:
        # Проверка на успешный jailbreak
        for pattern in self.jailbreak_compiled:
            if pattern.search(text):
                return ClassificationResult(
                    category=ContentCategory.JAILBREAK_SUCCESS,
                    confidence=0.9,
                    details={'pattern_matched': pattern.pattern}
                )
        
        # Проверка на вредный контент
        for pattern in self.harmful_compiled:
            if pattern.search(text):
                return ClassificationResult(
                    category=ContentCategory.HARMFUL,
                    confidence=0.85,
                    details={'pattern_matched': pattern.pattern}
                )
        
        return ClassificationResult(
            category=ContentCategory.SAFE,
            confidence=0.95,
            details={}
        )
```

---

## 3. Детекция PII

```python
import re

class PIIDetector:
    """Детекция персонально идентифицируемой информации."""
    
    PATTERNS = {
        'email': {
            'pattern': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'severity': 'medium'
        },
        'phone_us': {
            'pattern': r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
            'severity': 'medium'
        },
        'ssn': {
            'pattern': r'\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b',
            'severity': 'critical'
        },
        'credit_card': {
            'pattern': r'\b(?:\d{4}[-.\s]?){3}\d{4}\b',
            'severity': 'critical'
        }
    }
    
    def detect(self, text: str) -> List[Dict]:
        detections = []
        for pii_type, data in self.PATTERNS.items():
            pattern = re.compile(data['pattern'])
            matches = pattern.findall(text)
            for match in matches:
                detections.append({
                    'type': pii_type,
                    'value': self._mask_value(match),
                    'severity': data['severity']
                })
        return detections
    
    def _mask_value(self, value: str) -> str:
        if len(value) <= 4:
            return '*' * len(value)
        return value[:2] + '*' * (len(value) - 4) + value[-2:]


class SecretsDetector:
    """Детекция API ключей, токенов и учётных данных."""
    
    PATTERNS = {
        'api_key_generic': r'(?:api[_-]?key|apikey)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]{20,})',
        'aws_access_key': r'\b(AKIA[0-9A-Z]{16})\b',
        'github_token': r'\b(ghp_[a-zA-Z0-9]{36})\b',
        'jwt': r'\b(eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+)\b',
        'openai_key': r'\b(sk-[a-zA-Z0-9]{48})\b',
    }
    
    def detect(self, text: str) -> List[Dict]:
        detections = []
        for secret_type, pattern in self.PATTERNS.items():
            matches = re.findall(pattern, text, re.I)
            for match in matches:
                detections.append({
                    'type': secret_type,
                    'masked': match[:4] + '****' + match[-4:] if len(match) > 8 else '****',
                    'severity': 'critical'
                })
        return detections
```

---

## 4. Санитизатор ответов

```python
class ResponseSanitizer:
    """Санитизация ответов LLM путём редактирования чувствительных данных."""
    
    def __init__(self):
        self.pii_detector = PIIDetector()
        self.secrets_detector = SecretsDetector()
        
        self.redaction_templates = {
            'email': '[EMAIL СКРЫТ]',
            'phone_us': '[ТЕЛЕФОН СКРЫТ]',
            'ssn': '[SSN СКРЫТ]',
            'credit_card': '[КАРТА СКРЫТА]',
            'api_key_generic': '[API КЛЮЧ СКРЫТ]',
            'aws_access_key': '[AWS КЛЮЧ СКРЫТ]',
            'jwt': '[ТОКЕН СКРЫТ]',
            'openai_key': '[API КЛЮЧ СКРЫТ]',
        }
    
    def sanitize(self, text: str) -> tuple[str, List[Dict]]:
        all_detections = []
        result = text
        
        # Детекция и редактирование PII
        pii_detections = self.pii_detector.detect(result)
        for det in pii_detections:
            pii_type = det['type']
            pattern = self.pii_detector.compiled[pii_type][0]
            replacement = self.redaction_templates.get(pii_type, '[СКРЫТО]')
            result = pattern.sub(replacement, result)
        
        all_detections.extend(pii_detections)
        
        # Детекция и редактирование секретов
        secret_detections = self.secrets_detector.detect(result)
        for det in secret_detections:
            secret_type = det['type']
            pattern = self.secrets_detector.compiled[secret_type]
            replacement = self.redaction_templates.get(secret_type, '[СЕКРЕТ СКРЫТ]')
            result = pattern.sub(replacement, result)
        
        all_detections.extend(secret_detections)
        
        return result, all_detections
```

---

## 5. Интеграция с SENTINEL

```python
from enum import Enum

class FilterAction(Enum):
    ALLOW = "allow"
    SANITIZE = "sanitize"
    BLOCK = "block"

class SENTINELOutputFilter:
    """Модуль SENTINEL для комплексной фильтрации вывода."""
    
    def __init__(self, config: Dict = None):
        config = config or {}
        
        self.classifier = ContentClassifier()
        self.sanitizer = ResponseSanitizer()
        
        self.block_categories = {
            ContentCategory.HARMFUL,
            ContentCategory.JAILBREAK_SUCCESS
        }
        
        self.block_on_critical_pii = config.get('block_on_critical_pii', True)
    
    def filter(self, prompt: str, response: str) -> FilterResult:
        detections = []
        
        # Шаг 1: Классификация контента
        classification = self.classifier.classify(response, prompt)
        
        if classification.category in self.block_categories:
            return FilterResult(
                action=FilterAction.BLOCK,
                original_output=response,
                filtered_output="",
                detections=[{
                    'type': 'content_blocked',
                    'category': classification.category.value,
                    'confidence': classification.confidence
                }],
                risk_score=1.0
            )
        
        # Шаг 2: Санитизация
        sanitized, sanitize_detections = self.sanitizer.sanitize(response)
        detections.extend(sanitize_detections)
        
        # Проверка на критичные данные
        critical_detections = [
            d for d in detections if d.get('severity') == 'critical'
        ]
        
        if critical_detections and self.block_on_critical_pii:
            return FilterResult(
                action=FilterAction.BLOCK,
                original_output=response,
                filtered_output="",
                detections=detections,
                risk_score=1.0
            )
        
        # Расчёт риска
        risk = min(len(detections) * 0.15, 0.9)
        
        if sanitized != response:
            return FilterResult(
                action=FilterAction.SANITIZE,
                original_output=response,
                filtered_output=sanitized,
                detections=detections,
                risk_score=risk
            )
        
        return FilterResult(
            action=FilterAction.ALLOW,
            original_output=response,
            filtered_output=response,
            detections=detections,
            risk_score=0.0
        )
```

---

## 6. Итоги

### Категории фильтрации

| Категория | Действие | Серьёзность |
|-----------|----------|-------------|
| Безопасный | Разрешить | Нет |
| PII | Санитизировать/Блокировать | Средняя-Критичная |
| Секреты | Блокировать | Критичная |
| Вредный | Блокировать | Критичная |
| Успешный Jailbreak | Блокировать | Критичная |

### Чек-лист

```
□ Классифицировать контент на вредный/нарушения политики
□ Детектировать паттерны успешного jailbreak
□ Сканировать на PII (email, телефон, SSN, карты)
□ Детектировать секреты (API ключи, токены, пароли)
□ Редактировать или блокировать чувствительный контент
□ Логировать все решения фильтрации
□ Рассчитать риск-скор
```

---

## Следующий урок

→ [Фреймворки Guardrails](03-guardrails-frameworks.md)

---

*AI Security Academy | Трек 05: Стратегии защиты | Guardrails*
