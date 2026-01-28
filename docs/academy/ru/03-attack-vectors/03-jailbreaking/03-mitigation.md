# Митигация джейлбрейков

> **Уровень:** Средний  
> **Время:** 50 минут  
> **Трек:** 03 — Векторы атак  
> **Модуль:** 03.3 — Джейлбрейкинг  
> **Версия:** 2.0

---

## Цели обучения

После этого урока вы сможете:

- [ ] Проектировать многоуровневые системы защиты от джейлбрейков
- [ ] Реализовывать обнаружение на основе паттернов и семантики
- [ ] Настраивать стратегии ответа (блокировка, пометка, санитизация)
- [ ] Применять динамическую корректировку порогов
- [ ] Интегрировать защиту от джейлбрейков в SENTINEL

---

## 1. Архитектура защиты

### 1.1 Многоуровневая защита

```
┌────────────────────────────────────────────────────────────────────┐
│                    УРОВНИ ЗАЩИТЫ ОТ ДЖЕЙЛБРЕЙКОВ                   │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ВВОД                                                              │
│      ↓                                                             │
│  ╔═══════════════════════════════════════════════════════════════╗ │
│  ║  УРОВЕНЬ 1: ПРЕДОБРАБОТКА                                     ║ │
│  ║  • Нормализация ввода                                          ║ │
│  ║  • Каноникализация Unicode                                     ║ │
│  ║  • Обнаружение гомоглифов                                      ║ │
│  ║  • Обнаружение кодирования                                     ║ │
│  ╚═══════════════════════════════════════════════════════════════╝ │
│      ↓                                                             │
│  ╔═══════════════════════════════════════════════════════════════╗ │
│  ║  УРОВЕНЬ 2: ОБНАРУЖЕНИЕ ПАТТЕРНОВ                             ║ │
│  ║  • Сигнатуры ролевой игры                                      ║ │
│  ║  • Паттерны переопределения инструкций                         ║ │
│  ║  • Инъекция разделителей                                       ║ │
│  ║  • Известные шаблоны джейлбрейков                              ║ │
│  ╚═══════════════════════════════════════════════════════════════╝ │
│      ↓                                                             │
│  ╔═══════════════════════════════════════════════════════════════╗ │
│  ║  УРОВЕНЬ 3: СЕМАНТИЧЕСКИЙ АНАЛИЗ                              ║ │
│  ║  • Классификация намерения                                     ║ │
│  ║  • Валидация границ темы                                       ║ │
│  ║  • Оценка риска                                                ║ │
│  ╚═══════════════════════════════════════════════════════════════╝ │
│      ↓                                                             │
│  ╔═══════════════════════════════════════════════════════════════╗ │
│  ║  УРОВЕНЬ 4: ПОВЕДЕНЧЕСКИЙ АНАЛИЗ                              ║ │
│  ║  • Многоходовая траектория                                     ║ │
│  ║  • История пользователя                                        ║ │
│  ║  • Контекст сессии                                             ║ │
│  ╚═══════════════════════════════════════════════════════════════╝ │
│      ↓                                                             │
│  РЕШЕНИЕ: РАЗРЕШИТЬ / ПОМЕТИТЬ / ЗАБЛОКИРОВАТЬ                     │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 2. Обнаружение на основе паттернов

### 2.1 База данных сигнатур джейлбрейков

```python
from dataclasses import dataclass
from typing import List, Dict, Pattern
import re

@dataclass
class JailbreakSignature:
    id: str
    name: str
    patterns: List[str]
    severity: float
    category: str
    description: str

class JailbreakSignatureDB:
    """База данных известных сигнатур джейлбрейков."""
    
    SIGNATURES = [
        JailbreakSignature(
            id='JB001',
            name='DAN Атака',
            patterns=[
                r'\bDAN\b.*do\s+anything\s+now',
                r'pretend.*DAN',
                r'you\s+are\s+now\s+DAN',
            ],
            severity=0.9,
            category='roleplay',
            description='Атака персоной Do Anything Now'
        ),
        JailbreakSignature(
            id='JB002',
            name='Переопределение инструкций',
            patterns=[
                r'ignore\s+(all\s+)?(previous|above)\s+instructions?',
                r'disregard\s+(your\s+)?rules?',
                r'forget\s+everything\s+(above|before)',
            ],
            severity=0.85,
            category='override',
            description='Прямая попытка переопределения инструкций'
        ),
        JailbreakSignature(
            id='JB003',
            name='Режим разработчика',
            patterns=[
                r'developer\s+mode\s+(enabled|activated|on)',
                r'enter\s+debug\s+mode',
                r'maintenance\s+mode\s+override',
            ],
            severity=0.8,
            category='authority',
            description='Фейковая активация режима разработчика/отладки'
        ),
        JailbreakSignature(
            id='JB004',
            name='Извлечение системного промпта',
            patterns=[
                r'(show|reveal|tell)\s+me\s+(your\s+)?system\s+prompt',
                r'what\s+(are|is)\s+your\s+(initial\s+)?instructions?',
                r'repeat\s+(all|everything)\s+(above|before)',
            ],
            severity=0.75,
            category='extraction',
            description='Попытка извлечь системный промпт'
        ),
        JailbreakSignature(
            id='JB005',
            name='Инъекция разделителей',
            patterns=[
                r'\[/?SYSTEM\]',
                r'<\|im_(start|end)\|>',
                r'###\s*(SYSTEM|ADMIN)',
                r'```\s*system',
            ],
            severity=0.9,
            category='injection',
            description='Попытка инъекции разделителей/формата'
        ),
        JailbreakSignature(
            id='JB006',
            name='Гипотетическая рамка',
            patterns=[
                r'hypothetically\s+(speaking)?',
                r"for\s+(a|my)\s+(novel|story|book|class)",
                r'in\s+a\s+fictional\s+scenario',
                r'purely\s+for\s+(educational|research)\s+purposes?',
            ],
            severity=0.6,
            category='framing',
            description='Гипотетическая/вымышленная рамка для обхода безопасности'
        ),
    ]
    
    def __init__(self):
        self.compiled_signatures = []
        for sig in self.SIGNATURES:
            compiled = [
                (re.compile(p, re.I), sig) 
                for p in sig.patterns
            ]
            self.compiled_signatures.extend(compiled)
    
    def match(self, text: str) -> List[Dict]:
        matches = []
        
        for pattern, sig in self.compiled_signatures:
            if pattern.search(text):
                matches.append({
                    'signature_id': sig.id,
                    'name': sig.name,
                    'category': sig.category,
                    'severity': sig.severity,
                    'pattern': pattern.pattern
                })
        
        # Дедупликация по ID сигнатуры
        seen = set()
        unique_matches = []
        for m in matches:
            if m['signature_id'] not in seen:
                seen.add(m['signature_id'])
                unique_matches.append(m)
        
        return unique_matches
```

---

## 3. Семантический анализ

### 3.1 Классификация намерения

```python
from enum import Enum

class JailbreakIntent(Enum):
    BENIGN = "benign"
    ROLEPLAY = "roleplay"
    EXTRACTION = "extraction"
    OVERRIDE = "override"
    HARMFUL_REQUEST = "harmful_request"

class IntentClassifier:
    """Классификация намерения пользователя для обнаружения джейлбрейков."""
    
    # Ключевые слова, связанные с разными намерениями
    INTENT_KEYWORDS = {
        JailbreakIntent.ROLEPLAY: [
            'pretend', 'roleplay', 'act as', 'imagine', 'persona',
            'character', 'you are now', 'притворись', 'играй роль'
        ],
        JailbreakIntent.EXTRACTION: [
            'system prompt', 'instructions', 'rules', 'reveal',
            'show me', 'what were you told', 'системный промпт'
        ],
        JailbreakIntent.OVERRIDE: [
            'ignore', 'disregard', 'forget', 'override', 'bypass',
            'disable', 'turn off', 'игнорируй', 'забудь'
        ],
        JailbreakIntent.HARMFUL_REQUEST: [
            'bomb', 'weapon', 'hack', 'kill', 'attack', 'illegal',
            'drugs', 'exploit', 'malware', 'бомба', 'взлом'
        ]
    }
    
    def classify(self, text: str) -> Dict:
        text_lower = text.lower()
        scores = {intent: 0.0 for intent in JailbreakIntent}
        
        for intent, keywords in self.INTENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    scores[intent] += 0.2
        
        # Нормализация и поиск максимума
        max_score = max(scores.values())
        
        if max_score < 0.1:
            primary_intent = JailbreakIntent.BENIGN
        else:
            primary_intent = max(scores, key=scores.get)
        
        return {
            'primary_intent': primary_intent.value,
            'confidence': min(max_score, 1.0),
            'all_scores': {k.value: v for k, v in scores.items()}
        }
```

---

## 4. Стратегии ответа

### 4.1 Типы действий

```python
from enum import Enum
from dataclasses import dataclass

class MitigationAction(Enum):
    ALLOW = "allow"
    FLAG = "flag"
    SANITIZE = "sanitize"
    WARN = "warn"
    BLOCK = "block"

@dataclass
class MitigationResponse:
    action: MitigationAction
    modified_input: str = None
    warning_message: str = None
    log_event: bool = True
    
class ResponseStrategy:
    """Настройка стратегий ответа на основе серьёзности."""
    
    def __init__(self, config: Dict = None):
        config = config or {}
        self.block_threshold = config.get('block_threshold', 0.8)
        self.flag_threshold = config.get('flag_threshold', 0.5)
        self.warn_threshold = config.get('warn_threshold', 0.3)
    
    def determine_action(self, risk_score: float, 
                         detections: List[Dict]) -> MitigationResponse:
        
        # Критические паттерны всегда блокируют
        critical_categories = {'injection', 'override'}
        has_critical = any(
            d.get('category') in critical_categories 
            for d in detections
        )
        
        if has_critical and risk_score > 0.6:
            return MitigationResponse(
                action=MitigationAction.BLOCK,
                warning_message="Запрос заблокирован по соображениям безопасности."
            )
        
        if risk_score >= self.block_threshold:
            return MitigationResponse(
                action=MitigationAction.BLOCK,
                warning_message="Я не могу обработать этот запрос."
            )
        
        if risk_score >= self.flag_threshold:
            return MitigationResponse(
                action=MitigationAction.FLAG,
                warning_message="Этот запрос помечен для проверки."
            )
        
        if risk_score >= self.warn_threshold:
            return MitigationResponse(
                action=MitigationAction.WARN,
                warning_message="Пожалуйста, убедитесь, что ваш запрос соответствует правилам."
            )
        
        return MitigationResponse(action=MitigationAction.ALLOW)
```

---

## 5. Интеграция с SENTINEL

```python
class SENTINELJailbreakGuard:
    """Модуль SENTINEL для комплексной защиты от джейлбрейков."""
    
    def __init__(self, config: Dict = None):
        config = config or {}
        
        self.signature_db = JailbreakSignatureDB()
        self.intent_classifier = IntentClassifier()
        self.response_strategy = ResponseStrategy(config)
        
        # Конфигурация порогов
        self.thresholds = {
            'pattern_weight': 0.4,
            'intent_weight': 0.3,
            'context_weight': 0.3
        }
    
    def analyze(self, text: str, context: Dict = None) -> Dict:
        """Анализ ввода на попытки джейлбрейка."""
        
        context = context or {}
        
        # Уровень 1: Сопоставление паттернов
        pattern_matches = self.signature_db.match(text)
        pattern_score = self._calculate_pattern_score(pattern_matches)
        
        # Уровень 2: Классификация намерения
        intent_result = self.intent_classifier.classify(text)
        intent_score = self._calculate_intent_score(intent_result)
        
        # Уровень 3: Анализ контекста
        context_score = self._analyze_context(context)
        
        # Комбинированная оценка риска
        risk_score = (
            pattern_score * self.thresholds['pattern_weight'] +
            intent_score * self.thresholds['intent_weight'] +
            context_score * self.thresholds['context_weight']
        )
        
        # Определение ответа
        response = self.response_strategy.determine_action(
            risk_score, pattern_matches
        )
        
        return {
            'risk_score': risk_score,
            'pattern_matches': pattern_matches,
            'intent': intent_result,
            'action': response.action.value,
            'warning': response.warning_message,
            'should_log': response.log_event
        }
    
    def _calculate_pattern_score(self, matches: List[Dict]) -> float:
        if not matches:
            return 0.0
        
        max_severity = max(m.get('severity', 0.5) for m in matches)
        count_bonus = min(len(matches) * 0.1, 0.3)
        
        return min(max_severity + count_bonus, 1.0)
    
    def _calculate_intent_score(self, intent_result: Dict) -> float:
        intent = intent_result.get('primary_intent', 'benign')
        confidence = intent_result.get('confidence', 0.0)
        
        intent_weights = {
            'benign': 0.0,
            'roleplay': 0.3,
            'extraction': 0.5,
            'override': 0.7,
            'harmful_request': 0.8
        }
        
        base_score = intent_weights.get(intent, 0.0)
        return base_score * confidence
    
    def _analyze_context(self, context: Dict) -> float:
        """Анализ контекста сессии на индикаторы риска."""
        
        risk = 0.0
        
        # Предыдущие попытки джейлбрейка в сессии
        previous_attempts = context.get('jailbreak_attempts', 0)
        if previous_attempts > 0:
            risk += min(previous_attempts * 0.2, 0.5)
        
        # Траектория разговора
        if context.get('escalating', False):
            risk += 0.3
        
        return min(risk, 1.0)
```

---

## 6. Динамическая корректировка порогов

```python
from datetime import datetime, timedelta

class AdaptiveThresholdManager:
    """Динамическая корректировка порогов на основе ландшафта угроз."""
    
    def __init__(self, base_threshold: float = 0.7):
        self.base_threshold = base_threshold
        self.current_threshold = base_threshold
        self.attack_history = []
    
    def record_attack(self, severity: float, blocked: bool):
        self.attack_history.append({
            'severity': severity,
            'blocked': blocked,
            'timestamp': datetime.utcnow()
        })
        
        # Очистка старых записей
        cutoff = datetime.utcnow() - timedelta(hours=1)
        self.attack_history = [
            a for a in self.attack_history if a['timestamp'] > cutoff
        ]
        
        self._adjust_threshold()
    
    def _adjust_threshold(self):
        if len(self.attack_history) < 5:
            return
        
        # Расчёт частоты атак
        attack_count = len(self.attack_history)
        
        # Повышение чувствительности при всплеске атак
        if attack_count > 20:
            self.current_threshold = max(self.base_threshold - 0.2, 0.4)
        elif attack_count > 10:
            self.current_threshold = max(self.base_threshold - 0.1, 0.5)
        else:
            self.current_threshold = self.base_threshold
    
    def get_threshold(self) -> float:
        return self.current_threshold
```

---

## 7. Итоги

### Уровни защиты

| Уровень | Техника | Назначение |
|---------|---------|------------|
| **Предобработка** | Нормализация | Каноникализация ввода |
| **Паттерны** | Сопоставление сигнатур | Известные атаки |
| **Семантика** | Классификация намерения | Неизвестные атаки |
| **Поведение** | Анализ траектории | Многоходовые атаки |

### Быстрый чеклист

```
□ Реализовать базу данных сигнатур
□ Добавить классификацию намерения
□ Настроить стратегии ответа
□ Установить подходящие пороги
□ Включить динамическую корректировку
□ Логировать все обнаружения
□ Мониторить уровень ложных срабатываний
```

---

## Следующий трек

→ [Трек 04: Атаки уровня промптов](../04-prompt-level/README.md)

---

*AI Security Academy | Трек 03: Векторы атак | Джейлбрейкинг*
