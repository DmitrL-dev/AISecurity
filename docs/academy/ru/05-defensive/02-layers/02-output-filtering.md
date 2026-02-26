# Output Filtering

> **Урок:** 05.2.2 - Output Layer Defense  
> **Время:** 40 минут  
> **Пререквизиты:** Input Filtering basics

---

## Цели обучения

К концу этого урока вы сможете:

1. Реализовывать comprehensive output filtering
2. Детектировать harmful content в LLM responses
3. Предотвращать data leakage и prompt disclosure
4. Применять response sanitization techniques

---

## Почему Output Filtering?

Input filtering недостаточен:

| Threat | Why Input Filter Fails |
|--------|----------------------|
| **Novel attacks** | Unknown patterns bypass detection |
| **Jailbreaks** | Successful bypasses produce harm |
| **Hallucinations** | Model-generated harmful content |
| **Data leakage** | Training data memorization |

---

## Output Filter Architecture

```
LLM Response → Content Analysis → Policy Check → 
            → Data Leakage Scan → Sanitization → User
```

---

## Layer 1: Content Classification

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
    """Classify LLM output для harmful content."""
    
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
    
    def classify(self, response: str) -> dict:
        """Classify response content."""
        
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
        
        # Determine overall risk
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
```

---

## Layer 2: Data Leakage Detection

```python
class DataLeakageDetector:
    """Detect data leakage в model outputs."""
    
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
        """Scan response для data leakage."""
        
        findings = {
            "pii": [],
            "credentials": [],
            "protected_content": [],
            "risk_score": 0
        }
        
        # Scan для PII
        for pii_type, pattern in self.pii_patterns.items():
            matches = pattern.findall(response)
            if matches:
                findings["pii"].append({
                    "type": pii_type,
                    "count": len(matches),
                    "redacted": [self._redact(m) for m in matches[:3]]
                })
        
        # Scan для credentials
        for cred_type, pattern in self.credential_patterns.items():
            matches = pattern.findall(response)
            if matches:
                findings["credentials"].append({
                    "type": cred_type,
                    "count": len(matches),
                    "severity": "critical"
                })
        
        # Calculate risk score
        findings["risk_score"] = self._calculate_risk(findings)
        findings["requires_action"] = findings["risk_score"] > 0.3
        
        return findings
```

---

## Layer 3: Prompt Leakage Prevention

```python
class PromptLeakagePreventor:
    """Prevent system prompt disclosure в responses."""
    
    def __init__(self, system_prompt: str, protected_phrases: List[str] = None):
        self.system_prompt = system_prompt
        self.protected_phrases = protected_phrases or []
        
        # Extract key components from system prompt
        self.prompt_fingerprints = self._extract_fingerprints(system_prompt)
    
    def check(self, response: str) -> dict:
        """Check response для prompt leakage."""
        
        findings = []
        
        # Check для direct inclusion
        response_lower = response.lower()
        
        for fingerprint in self.prompt_fingerprints:
            if fingerprint in response_lower:
                findings.append({
                    "type": "direct_leak",
                    "fingerprint": fingerprint[:50] + "...",
                    "severity": "critical"
                })
        
        # Check для meta-discussion about prompts
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

## Layer 4: Response Sanitization

```python
class ResponseSanitizer:
    """Sanitize LLM responses based on findings."""
    
    def __init__(self):
        self.redaction_placeholder = "[REDACTED]"
    
    def sanitize(
        self, 
        response: str, 
        content_findings: dict,
        leakage_findings: dict,
        prompt_findings: dict
    ) -> dict:
        """Apply all sanitization based on findings."""
        
        sanitized = response
        modifications = []
        
        # Block если critical issues
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
                "reason": "Critical security issue detected"
            }
        
        # Redact PII
        for pii in leakage_findings.get("pii", []):
            pattern = self._get_pii_pattern(pii["type"])
            sanitized = pattern.sub(self.redaction_placeholder, sanitized)
            modifications.append(f"Redacted {pii['type']}")
        
        return {
            "original": response,
            "sanitized": sanitized,
            "blocked": False,
            "modifications": modifications
        }
```

---

## Интеграция с SENTINEL

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
    # Автоматически filtered before return
    return response
```

---

## Ключевые выводы

1. **Filter outputs too** — Input filtering недостаточен
2. **Detect multiple risks** — Content, leakage, prompts
3. **Sanitize, don't just block** — Keep useful responses
4. **Protect your prompts** — Prevent disclosure
5. **Log everything** — Для incident response

---

*AI Security Academy | Урок 05.2.2*
