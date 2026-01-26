# Output Filtering для LLM Security

> **Уровень:** Средний  
> **Время:** 45 минут  
> **Трек:** 05 — Defense Strategies  
> **Модуль:** 05.2 — Guardrails  
> **Версия:** 2.0 (Production)

---

## Цели обучения

После завершения этого урока вы сможете:

- [ ] Объяснить почему output filtering критичен для LLM приложений
- [ ] Реализовать content classification и blocking
- [ ] Детектировать PII и secrets в LLM responses
- [ ] Создать response sanitization pipelines
- [ ] Интегрировать output filtering с SENTINEL

---

## 1. Архитектура Output Filtering

```
---------------------------------------------------------------------¬
¦                    OUTPUT FILTERING PIPELINE                       ¦
+--------------------------------------------------------------------+
¦                                                                    ¦
¦  RAW LLM OUTPUT                                                    ¦
¦      v                                                             ¦
¦  г===============================================================¬ ¦
¦  ¦  LAYER 1: CONTENT CLASSIFICATION                              ¦ ¦
¦  ¦  • Harmful content detection                                  ¦ ¦
¦  ¦  • Policy violation check                                     ¦ ¦
¦  ¦  • Jailbreak success detection                                ¦ ¦
¦  L===============================================================- ¦
¦      v                                                             ¦
¦  г===============================================================¬ ¦
¦  ¦  LAYER 2: DATA LEAKAGE DETECTION                              ¦ ¦
¦  ¦  • PII detection (email, phone, SSN)                          ¦ ¦
¦  ¦  • Secret detection (API keys, tokens)                        ¦ ¦
¦  ¦  • System prompt leak detection                               ¦ ¦
¦  L===============================================================- ¦
¦      v                                                             ¦
¦  г===============================================================¬ ¦
¦  ¦  LAYER 3: SANITIZATION                                        ¦ ¦
¦  ¦  • PII redaction                                              ¦ ¦
¦  ¦  • Secret masking                                             ¦ ¦
¦  ¦  • Content transformation                                     ¦ ¦
¦  L===============================================================- ¦
¦      v                                                             ¦
¦  FILTERED OUTPUT                                                   ¦
¦                                                                    ¦
L---------------------------------------------------------------------
```

---

## 2. Content Classification

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

@dataclass
class ClassificationResult:
    category: ContentCategory
    confidence: float
    details: Dict

class ContentClassifier:
    """Classify LLM output для безопасности."""
    
    HARMFUL_PATTERNS = [
        r'how\s+to\s+(make|create|build)\s+(a\s+)?(bomb|weapon|explosive)',
        r'step.by.step\s+(guide|instructions?)\s+(to|for)\s+(hack|attack)',
        r'here\s+(is|are)\s+(the\s+)?instructions?\s+to\s+(harm|kill)',
    ]
    
    JAILBREAK_SUCCESS_PATTERNS = [
        r'as\s+(DAN|an?\s+unrestricted)',
        r'without\s+(any\s+)?restrictions?',
        r'ignoring\s+(my\s+)?(previous\s+)?guidelines',
        r'breaking\s+character',
        r'I\s+(can|will)\s+now\s+do\s+anything',
    ]
    
    def __init__(self):
        import re
        self.harmful_compiled = [re.compile(p, re.I) for p in self.HARMFUL_PATTERNS]
        self.jailbreak_compiled = [re.compile(p, re.I) for p in self.JAILBREAK_SUCCESS_PATTERNS]
    
    def classify(self, text: str, prompt: str = None) -> ClassificationResult:
        # Проверка на jailbreak success
        for pattern in self.jailbreak_compiled:
            if pattern.search(text):
                return ClassificationResult(
                    category=ContentCategory.JAILBREAK_SUCCESS,
                    confidence=0.9,
                    details={'pattern_matched': pattern.pattern}
                )
        
        # Проверка на harmful content
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

## 3. PII Detection

```python
import re
from typing import Tuple

class PIIDetector:
    """Detect Personally Identifiable Information."""
    
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
        },
        'ip_address': {
            'pattern': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
            'severity': 'low'
        }
    }
    
    def __init__(self):
        self.compiled = {
            name: (re.compile(data['pattern']), data['severity'])
            for name, data in self.PATTERNS.items()
        }
    
    def detect(self, text: str) -> List[Dict]:
        detections = []
        for pii_type, (pattern, severity) in self.compiled.items():
            matches = pattern.findall(text)
            for match in matches:
                detections.append({
                    'type': pii_type,
                    'value': self._mask_value(match),
                    'severity': severity
                })
        return detections
    
    def _mask_value(self, value: str) -> str:
        if len(value) <= 4:
            return '*' * len(value)
        return value[:2] + '*' * (len(value) - 4) + value[-2:]


class SecretsDetector:
    """Detect API keys, tokens, and credentials."""
    
    PATTERNS = {
        'api_key_generic': r'(?:api[_-]?key|apikey)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]{20,})',
        'aws_access_key': r'\b(AKIA[0-9A-Z]{16})\b',
        'aws_secret_key': r'(?:aws_secret|secret_key)["\']?\s*[:=]\s*["\']?([A-Za-z0-9/+=]{40})',
        'github_token': r'\b(ghp_[a-zA-Z0-9]{36})\b',
        'jwt': r'\b(eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+)\b',
        'openai_key': r'\b(sk-[a-zA-Z0-9]{48})\b',
        'password_assignment': r'(?:password|passwd|pwd)["\']?\s*[:=]\s*["\']?([^\s"\']    {8,})',
    }
    
    def __init__(self):
        self.compiled = {
            name: re.compile(pattern, re.I)
            for name, pattern in self.PATTERNS.items()
        }
    
    def detect(self, text: str) -> List[Dict]:
        detections = []
        for secret_type, pattern in self.compiled.items():
            matches = pattern.findall(text)
            for match in matches:
                detections.append({
                    'type': secret_type,
                    'masked': match[:4] + '****' + match[-4:] if len(match) > 8 else '****',
                    'severity': 'critical'
                })
        return detections
```

---

## 4. Response Sanitizer

```python
class ResponseSanitizer:
    """Sanitize LLM responses путём редактирования sensitive data."""
    
    def __init__(self, config: Dict = None):
        self.pii_detector = PIIDetector()
        self.secrets_detector = SecretsDetector()
        
        self.redaction_templates = {
            'email': '[EMAIL REDACTED]',
            'phone_us': '[PHONE REDACTED]',
            'ssn': '[SSN REDACTED]',
            'credit_card': '[CREDIT CARD REDACTED]',
            'api_key_generic': '[API KEY REDACTED]',
            'aws_access_key': '[AWS KEY REDACTED]',
            'jwt': '[TOKEN REDACTED]',
            'openai_key': '[API KEY REDACTED]',
            'password_assignment': '[PASSWORD REDACTED]',
        }
    
    def sanitize(self, text: str) -> Tuple[str, List[Dict]]:
        all_detections = []
        result = text
        
        # Detect and redact PII
        pii_detections = self.pii_detector.detect(result)
        for det in pii_detections:
            pii_type = det['type']
            pattern = self.pii_detector.compiled[pii_type][0]
            replacement = self.redaction_templates.get(pii_type, '[REDACTED]')
            result = pattern.sub(replacement, result)
        
        all_detections.extend(pii_detections)
        
        # Detect and redact secrets
        secret_detections = self.secrets_detector.detect(result)
        for det in secret_detections:
            secret_type = det['type']
            pattern = self.secrets_detector.compiled[secret_type]
            replacement = self.redaction_templates.get(secret_type, '[SECRET REDACTED]')
            result = pattern.sub(replacement, result)
        
        all_detections.extend(secret_detections)
        
        return result, all_detections
```

---

## 5. SENTINEL Integration

```python
from enum import Enum

class FilterAction(Enum):
    ALLOW = "allow"
    SANITIZE = "sanitize"
    BLOCK = "block"

@dataclass
class FilterResult:
    action: FilterAction
    original_output: str
    filtered_output: str
    detections: List[Dict]
    risk_score: float

class SENTINELOutputFilter:
    """SENTINEL модуль для comprehensive output filtering."""
    
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
        
        # Step 1: Content classification
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
        
        # Step 2: Sanitization
        sanitized, sanitize_detections = self.sanitizer.sanitize(response)
        detections.extend(sanitize_detections)
        
        # Check for critical data
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
        
        # Calculate risk
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

## 6. Резюме

### Категории фильтрации

| Категория | Действие | Severity |
|-----------|----------|----------|
| Safe | Allow | None |
| PII | Sanitize/Block | Medium-Critical |
| Secrets | Block | Critical |
| Harmful | Block | Critical |
| Jailbreak Success | Block | Critical |

### Quick Checklist

```
? Classify content для harmful/policy violations
? Detect jailbreak success patterns
? Scan для PII (email, phone, SSN, credit cards)
? Detect secrets (API keys, tokens, passwords)
? Redact или block sensitive content
? Log все filtering decisions
? Calculate risk score
```

---

## Следующий урок

> [Guardrails Frameworks](03-guardrails-frameworks.md)

---

*AI Security Academy | Track 05: Defense Strategies | Guardrails*
