# Фильтрация выходных данных

> **Урок:** 05.2.2 — Защита выходного уровня  
> **Время:** 40 минут  
> **Требования:** Основы фильтрации входных данных

---

## Цели обучения

После завершения этого урока вы сможете:

1. Реализовать комплексную фильтрацию выходных данных
2. Детектировать вредоносный контент в ответах LLM
3. Предотвращать утечку данных и раскрытие промпта
4. Применять техники санитизации ответов

---

## Почему фильтрация выходных данных?

Фильтрация входных данных недостаточна:

| Угроза | Почему input filter не справляется |
|--------|-----------------------------------|
| **Novel атаки** | Неизвестные паттерны обходят детекцию |
| **Jailbreaks** | Успешные bypasses производят вред |
| **Галлюцинации** | Модель генерирует вредоносный контент |
| **Утечка данных** | Запоминание training data |

---

## Архитектура Output Filter

```
LLM Response → Content Analysis → Policy Check → 
            → Data Leakage Scan → Sanitization → User
```

---

## Слой 1: Классификация контента

```python
from dataclasses import dataclass
from typing import List
import re

@dataclass
class ContentFinding:
    category: str
    severity: str  # "critical", "high", "medium", "low"
    span: tuple  # (start, end)
    content: str
    action: str

class OutputContentClassifier:
    """Классификация вывода LLM на предмет вредоносного контента."""
    
    HARM_CATEGORIES = {
        "violence": [
            (r'\b(?:how to|steps to|ways to).*(?:kill|murder|attack|harm)', "high"),
            (r'\b(?:weapons?|explosives?|bombs?)\b.*\b(?:make|create|build)', "critical"),
        ],
        "illegal": [
            (r'\b(?:hack|exploit|bypass).*(?:system|security|password)', "high"),
            (r'\b(?:steal|fraud|scam).*(?:how|steps|guide)', "high"),
        ],
        "harmful_instructions": [
            (r'(?:step\s+\d+|first|then|next).*(?:dangerous|illegal|harmful)', "high"),
            (r'here\'s how.*(?:to avoid detection|without getting caught)', "critical"),
        ],
        "personal_info": [
            (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', "medium"),
            (r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', "medium"),
            (r'\b\d{3}-\d{2}-\d{4}\b', "critical"),  # SSN
        ],
    }
    
    def __init__(self):
        self.compiled_patterns = {}
        for category, patterns in self.HARM_CATEGORIES.items():
            self.compiled_patterns[category] = [
                (re.compile(p, re.IGNORECASE | re.DOTALL), sev)
                for p, sev in patterns
            ]
    
    def classify(self, response: str) -> dict:
        """Классификация контента ответа."""
        
        findings = []
        
        for category, patterns in self.compiled_patterns.items():
            for pattern, severity in patterns:
                for match in pattern.finditer(response):
                    findings.append(ContentFinding(
                        category=category,
                        severity=severity,
                        span=(match.start(), match.end()),
                        content=match.group()[:100],
                        action=self._determine_action(severity)
                    ))
        
        # Определение общего риска
        if any(f.severity == "critical" for f in findings):
            overall_risk = "critical"
            action = "block"
        elif any(f.severity == "high" for f in findings):
            overall_risk = "high"
            action = "redact"
        elif findings:
            overall_risk = "medium"
            action = "flag"
        else:
            overall_risk = "low"
            action = "allow"
        
        return {
            "findings": findings,
            "risk_level": overall_risk,
            "recommended_action": action
        }
    
    def _determine_action(self, severity: str) -> str:
        return {
            "critical": "block",
            "high": "redact",
            "medium": "flag",
            "low": "allow"
        }.get(severity, "flag")
```

---

## Слой 2: Детекция утечки данных

```python
class DataLeakageDetector:
    """Детекция утечки данных в выводе модели."""
    
    def __init__(self, protected_content: dict = None):
        self.protected = protected_content or {}
        self.pii_patterns = self._compile_pii_patterns()
        self.credential_patterns = self._compile_credential_patterns()
    
    def _compile_pii_patterns(self) -> dict:
        return {
            "email": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            "phone": re.compile(r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'),
            "ssn": re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
            "credit_card": re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
            "address": re.compile(r'\d+\s+[\w\s]+(?:street|st|avenue|ave|road|rd|boulevard|blvd)', re.IGNORECASE),
        }
    
    def _compile_credential_patterns(self) -> dict:
        return {
            "api_key": re.compile(r'(?:api[_-]?key|apikey)["\s:=]+([a-zA-Z0-9_-]{20,})'),
            "secret": re.compile(r'(?:secret|password|passwd|pwd)["\s:=]+([^\s"\']{8,})'),
            "token": re.compile(r'(?:token|bearer)["\s:=]+([a-zA-Z0-9_.-]{20,})'),
            "aws_access": re.compile(r'AKIA[0-9A-Z]{16}'),
            "aws_secret": re.compile(r'(?:aws[_-]?secret|secret[_-]?key)["\s:=]+([a-zA-Z0-9/+=]{40})'),
            "private_key": re.compile(r'-----BEGIN (?:RSA|EC|OPENSSH) PRIVATE KEY-----'),
        }
    
    def scan(self, response: str) -> dict:
        """Сканирование ответа на утечку данных."""
        
        findings = {
            "pii": [],
            "credentials": [],
            "protected_content": [],
            "risk_score": 0
        }
        
        # Сканирование на PII
        for pii_type, pattern in self.pii_patterns.items():
            matches = pattern.findall(response)
            if matches:
                findings["pii"].append({
                    "type": pii_type,
                    "count": len(matches),
                    "redacted": [self._redact(m) for m in matches[:3]]
                })
        
        # Сканирование на credentials
        for cred_type, pattern in self.credential_patterns.items():
            matches = pattern.findall(response)
            if matches:
                findings["credentials"].append({
                    "type": cred_type,
                    "count": len(matches),
                    "severity": "critical"
                })
        
        # Проверка защищённого контента
        for label, protected_text in self.protected.items():
            if self._fuzzy_match(response, protected_text):
                findings["protected_content"].append({
                    "label": label,
                    "severity": "critical"
                })
        
        # Расчёт risk score
        findings["risk_score"] = self._calculate_risk(findings)
        findings["requires_action"] = findings["risk_score"] > 0.3
        
        return findings
    
    def _redact(self, text: str) -> str:
        """Редактирование чувствительного контента для логирования."""
        if len(text) <= 4:
            return "****"
        return text[:2] + "****" + text[-2:]
    
    def _fuzzy_match(self, response: str, protected: str, threshold: float = 0.8) -> bool:
        """Проверка на fuzzy match защищённого контента."""
        protected_words = protected.lower().split()
        response_lower = response.lower()
        
        matched_words = sum(1 for w in protected_words if w in response_lower)
        ratio = matched_words / len(protected_words) if protected_words else 0
        
        return ratio >= threshold
    
    def _calculate_risk(self, findings: dict) -> float:
        """Расчёт общего risk score."""
        risk = 0.0
        
        # Credentials критичны
        if findings["credentials"]:
            risk = max(risk, 0.9)
        
        # Защищённый контент критичен
        if findings["protected_content"]:
            risk = max(risk, 0.95)
        
        # PII варьируется по типу
        pii_weights = {
            "ssn": 0.9, "credit_card": 0.85, 
            "email": 0.4, "phone": 0.5, "address": 0.6
        }
        for pii in findings["pii"]:
            weight = pii_weights.get(pii["type"], 0.5)
            risk = max(risk, weight)
        
        return risk
```

---

## Слой 3: Предотвращение утечки промпта

```python
class PromptLeakagePreventor:
    """Предотвращение раскрытия system prompt в ответах."""
    
    def __init__(self, system_prompt: str, protected_phrases: List[str] = None):
        self.system_prompt = system_prompt
        self.protected_phrases = protected_phrases or []
        
        # Извлечение ключевых компонентов из system prompt
        self.prompt_fingerprints = self._extract_fingerprints(system_prompt)
    
    def _extract_fingerprints(self, prompt: str) -> List[str]:
        """Извлечение характерных фраз из system prompt."""
        # Разделение на предложения
        sentences = re.split(r'[.!?]', prompt)
        
        # Взятие характерных (длинных, уникальных)
        fingerprints = []
        for s in sentences:
            s = s.strip()
            if len(s) > 30 and len(s.split()) > 5:
                fingerprints.append(s.lower())
        
        return fingerprints
    
    def check(self, response: str) -> dict:
        """Проверка ответа на утечку промпта."""
        
        findings = []
        
        # Проверка на прямое включение
        response_lower = response.lower()
        
        for fingerprint in self.prompt_fingerprints:
            if fingerprint in response_lower:
                findings.append({
                    "type": "direct_leak",
                    "fingerprint": fingerprint[:50] + "...",
                    "severity": "critical"
                })
        
        # Проверка защищённых фраз
        for phrase in self.protected_phrases:
            if phrase.lower() in response_lower:
                findings.append({
                    "type": "protected_phrase",
                    "phrase": phrase,
                    "severity": "high"
                })
        
        # Проверка на мета-обсуждение промптов
        meta_patterns = [
            r'my (?:system )?prompt (?:is|says|tells)',
            r'i was (?:instructed|told|programmed) to',
            r'my (?:initial |original )?instructions',
            r'the (?:system |developer )?prompt (?:includes|contains)',
        ]
        
        for pattern in meta_patterns:
            if re.search(pattern, response_lower):
                findings.append({
                    "type": "meta_discussion",
                    "pattern": pattern,
                    "severity": "medium"
                })
        
        return {
            "is_leaking": len(findings) > 0,
            "findings": findings,
            "action": "block" if any(f["severity"] == "critical" for f in findings) else "allow"
        }
```

---

## Слой 4: Санитизация ответа

```python
class ResponseSanitizer:
    """Санитизация ответов LLM на основе findings."""
    
    def __init__(self):
        self.redaction_placeholder = "[ОТРЕДАКТИРОВАНО]"
    
    def sanitize(
        self, 
        response: str, 
        content_findings: dict,
        leakage_findings: dict,
        prompt_findings: dict
    ) -> dict:
        """Применение всей санитизации на основе findings."""
        
        sanitized = response
        modifications = []
        
        # Блокировка при критических проблемах
        critical_issues = (
            any(f.severity == "critical" for f in content_findings.get("findings", [])) or
            leakage_findings.get("risk_score", 0) > 0.9 or
            prompt_findings.get("action") == "block"
        )
        
        if critical_issues:
            return {
                "original": response,
                "sanitized": None,
                "blocked": True,
                "reason": "Обнаружена критическая проблема безопасности"
            }
        
        # Редактирование PII
        for pii in leakage_findings.get("pii", []):
            pattern = self._get_pii_pattern(pii["type"])
            sanitized = pattern.sub(self.redaction_placeholder, sanitized)
            modifications.append(f"Отредактирован {pii['type']}")
        
        # Редактирование credentials
        for cred in leakage_findings.get("credentials", []):
            pattern = self._get_credential_pattern(cred["type"])
            sanitized = pattern.sub(self.redaction_placeholder, sanitized)
            modifications.append(f"Отредактирован {cred['type']}")
        
        # Редактирование вредоносного контента
        for finding in content_findings.get("findings", []):
            if finding.action == "redact":
                start, end = finding.span
                sanitized = sanitized[:start] + self.redaction_placeholder + sanitized[end:]
                modifications.append(f"Отредактирован {finding.category}")
        
        return {
            "original": response,
            "sanitized": sanitized,
            "blocked": False,
            "modifications": modifications
        }
```

---

## Полный пайплайн

```python
class OutputFilterPipeline:
    """Полный пайплайн фильтрации выходных данных."""
    
    def __init__(self, system_prompt: str, protected_content: dict = None):
        self.content_classifier = OutputContentClassifier()
        self.leakage_detector = DataLeakageDetector(protected_content)
        self.prompt_guard = PromptLeakagePreventor(system_prompt)
        self.sanitizer = ResponseSanitizer()
    
    def filter(self, response: str) -> dict:
        """Фильтрация ответа LLM через все слои."""
        
        # Слой 1: Классификация контента
        content_result = self.content_classifier.classify(response)
        
        # Слой 2: Детекция утечки данных
        leakage_result = self.leakage_detector.scan(response)
        
        # Слой 3: Проверка утечки промпта
        prompt_result = self.prompt_guard.check(response)
        
        # Слой 4: Санитизация
        final_result = self.sanitizer.sanitize(
            response,
            content_result,
            leakage_result,
            prompt_result
        )
        
        # Компиляция полного результата
        return {
            "original": response,
            "output": final_result["sanitized"] if not final_result["blocked"] else None,
            "blocked": final_result["blocked"],
            "analysis": {
                "content": content_result,
                "leakage": leakage_result,
                "prompt": prompt_result
            },
            "modifications": final_result.get("modifications", [])
        }
```

---

## Интеграция SENTINEL

```python
from sentinel import configure, OutputGuard

configure(
    output_filtering=True,
    content_classification=True,
    data_leakage_detection=True,
    prompt_protection=True
)

output_guard = OutputGuard(
    system_prompt=system_prompt,
    protected_content={"api_key": sensitive_key},
    block_critical=True
)

@output_guard.protect
def generate_response(prompt: str):
    response = llm.generate(prompt)
    # Автоматически фильтруется перед возвратом
    return response
```

---

## Ключевые выводы

1. **Фильтруй и выходы тоже** — Input filtering недостаточна
2. **Детектируй множественные риски** — Контент, утечка, промпты
3. **Санитизируй, не только блокируй** — Сохраняй полезные ответы
4. **Защищай промпты** — Предотвращай раскрытие
5. **Логируй всё** — Для incident response

---

## Следующий урок

→ [03. Безопасность RAG](03-rag-security.md)

---

*AI Security Academy | Урок 05.2.2*
