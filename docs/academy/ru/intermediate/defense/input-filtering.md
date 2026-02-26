# Валидация входных данных для безопасности LLM

> **Уровень:** Средний  
> **Время:** 50 минут  
> **Трек:** 05 — Стратегии защиты  
> **Модуль:** 05.2 — Guardrails  
> **Версия:** 2.0 (Production)

---

## Цели обучения

По завершении этого урока вы сможете:

- [ ] Объяснить почему валидация ввода критична для LLM-приложений
- [ ] Реализовать многослойный пайплайн валидации ввода
- [ ] Применять техники нормализации и санитизации
- [ ] Детектировать паттерны инъекций и закодированные пейлоады
- [ ] Интегрировать валидацию ввода с SENTINEL

---

## 1. Архитектура валидации ввода

### 1.1 Слои защиты

```
┌────────────────────────────────────────────────────────────────────┐
│                    ПАЙПЛАЙН ВАЛИДАЦИИ ВВОДА                       │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  СЫРОЙ ВВОД                                                        │
│      ↓                                                             │
│  ╔═══════════════════════════════════════════════════════════════╗ │
│  ║  СЛОЙ 1: РАЗМЕР И ФОРМАТ                                      ║ │
│  ║  • Проверка макс. длины                                       ║ │
│  ║  • Валидация набора символов                                  ║ │
│  ║  • Rate limiting                                              ║ │
│  ╚═══════════════════════════════════════════════════════════════╝ │
│      ↓                                                             │
│  ╔═══════════════════════════════════════════════════════════════╗ │
│  ║  СЛОЙ 2: НОРМАЛИЗАЦИЯ                                         ║ │
│  ║  • Unicode нормализация (NFKC)                                ║ │
│  ║  • Детекция гомоглифов                                        ║ │
│  ║  • Удаление невидимых символов                                ║ │
│  ╚═══════════════════════════════════════════════════════════════╝ │
│      ↓                                                             │
│  ╔═══════════════════════════════════════════════════════════════╗ │
│  ║  СЛОЙ 3: ДЕТЕКЦИЯ ПАТТЕРНОВ                                   ║ │
│  ║  • Паттерн-матчинг инъекций                                   ║ │
│  ║  • Детекция сигнатур jailbreak                                ║ │
│  ║  • Детекция закодированного контента                          ║ │
│  ╚═══════════════════════════════════════════════════════════════╝ │
│      ↓                                                             │
│  ╔═══════════════════════════════════════════════════════════════╗ │
│  ║  СЛОЙ 4: СЕМАНТИЧЕСКИЙ АНАЛИЗ                                 ║ │
│  ║  • Классификация интента                                      ║ │
│  ║  • Проверка границ топика                                     ║ │
│  ║  • Скоринг риска                                              ║ │
│  ╚═══════════════════════════════════════════════════════════════╝ │
│      ↓                                                             │
│  ВАЛИДИРОВАННЫЙ ВВОД                                               │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 2. Слой 1: Валидация размера и формата

```python
class SizeFormatValidator:
    """Первый слой: базовые проверки размера и формата."""
    
    def __init__(self, config: Dict = None):
        self.config = config or {
            'max_length': 10000,
            'min_length': 1,
            'max_lines': 500,
            'blocked_chars': ['\x00', '\x1b']  # Null, escape
        }
    
    def validate(self, text: str) -> ValidationResult:
        detections = []
        
        # Проверка длины
        if len(text) > self.config['max_length']:
            detections.append({
                'type': 'length_exceeded',
                'value': len(text),
                'max': self.config['max_length']
            })
            return ValidationResult(
                action=ValidationAction.BLOCK,
                risk_score=1.0,
                detections=detections
            )
        
        # Проверка количества строк
        lines = text.count('\n')
        if lines > self.config['max_lines']:
            detections.append({
                'type': 'too_many_lines',
                'value': lines
            })
        
        # Заблокированные символы
        for char in self.config['blocked_chars']:
            if char in text:
                detections.append({
                    'type': 'blocked_character',
                    'char': repr(char)
                })
                text = text.replace(char, '')
        
        risk = min(len(detections) * 0.2, 0.6)
        
        return ValidationResult(
            action=ValidationAction.FLAG if detections else ValidationAction.ALLOW,
            validated_input=text,
            risk_score=risk,
            detections=detections
        )
```

---

## 3. Слой 2: Нормализация

```python
import unicodedata
import re

class CharacterNormalizer:
    """Нормализация и очистка входного текста."""
    
    # Unicode confusables (гомоглифы)
    HOMOGLYPHS = {
        'А': 'A', 'В': 'B', 'С': 'C', 'Е': 'E', 'Н': 'H',
        'І': 'I', 'К': 'K', 'М': 'M', 'О': 'O', 'Р': 'P',
        'а': 'a', 'с': 'c', 'е': 'e', 'о': 'o', 'р': 'p',
    }
    
    # Невидимые символы
    INVISIBLE_CHARS = [
        '\u200b',  # Zero-width space
        '\u200c',  # Zero-width non-joiner
        '\u200d',  # Zero-width joiner
        '\ufeff',  # BOM
        '\u00ad',  # Soft hyphen
    ]
    
    def normalize(self, text: str) -> tuple[str, List[str]]:
        transforms = []
        result = text
        
        # NFKC нормализация
        normalized = unicodedata.normalize('NFKC', result)
        if normalized != result:
            transforms.append('nfkc_normalization')
            result = normalized
        
        # Замена гомоглифов
        replaced = self._replace_homoglyphs(result)
        if replaced != result:
            transforms.append('homoglyph_replacement')
            result = replaced
        
        # Удаление невидимых символов
        cleaned = self._remove_invisible(result)
        if cleaned != result:
            transforms.append('invisible_char_removal')
            result = cleaned
        
        return result, transforms
```

---

## 4. Слой 3: Детекция паттернов

```python
class InjectionPatternDetector:
    """Детекция паттернов инъекций и jailbreak."""
    
    PATTERNS = {
        'instruction_override': {
            'patterns': [
                r'ignore\s+(all\s+)?(previous|above|prior)\s+instructions?',
                r'disregard\s+(all\s+)?(previous|your)\s+(instructions?|rules?)',
                r'forget\s+(everything|all)\s+(above|you\s+were\s+told)',
            ],
            'severity': 0.8
        },
        'role_manipulation': {
            'patterns': [
                r'you\s+are\s+now\s+(a|an|my)\s+\w+',
                r'pretend\s+(to\s+be|you\s+are)',
                r'act\s+as\s+(if\s+)?you\s+(are|were)',
            ],
            'severity': 0.6
        },
        'delimiter_injection': {
            'patterns': [
                r'\[/?SYSTEM\]',
                r'\[/?ADMIN\]',
                r'<\|im_(start|end)\|>',
            ],
            'severity': 0.9
        }
    }
    
    def detect(self, text: str) -> List[Dict]:
        detections = []
        
        for category, data in self.PATTERNS.items():
            for pattern in data['patterns']:
                if re.search(pattern, text, re.I):
                    detections.append({
                        'type': 'injection_pattern',
                        'category': category,
                        'severity': data['severity']
                    })
        
        return detections


class EncodedContentDetector:
    """Детекция base64, hex и другого закодированного контента."""
    
    def detect(self, text: str) -> List[Dict]:
        detections = []
        
        # Детекция Base64
        b64_pattern = r'[A-Za-z0-9+/]{20,}={0,2}'
        b64_matches = re.findall(b64_pattern, text)
        for match in b64_matches:
            if self._is_valid_base64(match):
                detections.append({
                    'type': 'base64_content',
                    'length': len(match)
                })
        
        # Детекция URL encoding
        if re.search(r'%[0-9a-fA-F]{2}', text):
            detections.append({'type': 'url_encoded_content'})
        
        return detections
```

---

## 5. Интеграция с SENTINEL

```python
class SENTINELInputValidator:
    """Модуль SENTINEL для комплексной валидации ввода."""
    
    def __init__(self, config: Dict = None):
        config = config or {}
        
        self.size_validator = SizeFormatValidator(config.get('size'))
        self.normalizer = CharacterNormalizer()
        self.injection_detector = InjectionPatternDetector()
        self.encoding_detector = EncodedContentDetector()
        
        self.block_threshold = config.get('block_threshold', 0.8)
        self.flag_threshold = config.get('flag_threshold', 0.4)
    
    def validate(self, text: str) -> ValidationResult:
        all_detections = []
        all_transforms = []
        current_text = text
        max_severity = 0.0
        
        # Слой 1: Размер и формат
        size_result = self.size_validator.validate(current_text)
        if size_result.action == ValidationAction.BLOCK:
            return size_result
        all_detections.extend(size_result.detections)
        current_text = size_result.validated_input
        
        # Слой 2: Нормализация
        normalized, transforms = self.normalizer.normalize(current_text)
        all_transforms.extend(transforms)
        current_text = normalized
        
        # Слой 3: Детекция паттернов
        injection_detections = self.injection_detector.detect(current_text)
        all_detections.extend(injection_detections)
        for det in injection_detections:
            max_severity = max(max_severity, det.get('severity', 0.5))
        
        # Слой 3b: Детекция кодирования
        encoding_detections = self.encoding_detector.detect(current_text)
        all_detections.extend(encoding_detections)
        
        # Расчёт риска
        risk_score = min(max_severity + len(all_detections) * 0.05, 1.0)
        
        # Определение действия
        if risk_score >= self.block_threshold:
            action = ValidationAction.BLOCK
        elif risk_score >= self.flag_threshold:
            action = ValidationAction.FLAG
        else:
            action = ValidationAction.ALLOW
        
        return ValidationResult(
            action=action,
            validated_input=current_text,
            original_input=text,
            risk_score=risk_score,
            detections=all_detections,
            applied_transforms=all_transforms
        )
```

---

## 6. Итоги

### Слои валидации

| Слой | Назначение | Техники |
|------|------------|---------|
| **Размер/Формат** | Базовые лимиты | Длина, charset, rate |
| **Нормализация** | Канонизация | NFKC, гомоглифы, невидимые |
| **Паттерны** | Детекция атак | Regex, сигнатуры |
| **Семантика** | Анализ интента | Классификация, скоринг |

### Чек-лист

```
□ Установить макс. длину ввода (рекомендуется: 10,000 символов)
□ Применить NFKC нормализацию
□ Детектировать гомоглифы и невидимые символы
□ Матчить паттерны инъекций
□ Детектировать закодированные пейлоады
□ Рассчитать риск-скор
□ Логировать все детекции
```

---

## Следующий урок

→ [Фильтрация вывода](02-output-filtering.md)

---

*AI Security Academy | Трек 05: Стратегии защиты | Guardrails*
