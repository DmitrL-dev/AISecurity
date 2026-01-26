# Output Filtering

> **Lesson:** 05.2.2 - Output Layer Defense  
> **Time:** 40 minutes  
> **Prerequisites:** Input Filtering basics

---

## Learning Objectives

By the end of this lesson, you will be able to:

1. Implement comprehensive output filtering
2. Detect harmful content in LLM responses
3. Prevent data leakage and prompt disclosure
4. Apply response sanitization techniques

---

## Why Output Filtering?

Input filtering alone is insufficient:

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
    """Classify LLM output for harmful content."""
    
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
    
    def _determine_action(self, severity: str) -> str:
        return {
            "critical": "block",
            "high": "redact",
            "medium": "flag",
            "low": "allow"
        }.get(severity, "flag")
```

---

## Layer 2: Data Leakage Detection

```python
class DataLeakageDetector:
    """Detect data leakage in model outputs."""
    
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
        """Scan response for data leakage."""
        
        findings = {
            "pii": [],
            "credentials": [],
            "protected_content": [],
            "risk_score": 0
        }
        
        # Scan for PII
        for pii_type, pattern in self.pii_patterns.items():
            matches = pattern.findall(response)
            if matches:
                findings["pii"].append({
                    "type": pii_type,
                    "count": len(matches),
                    "redacted": [self._redact(m) for m in matches[:3]]
                })
        
        # Scan for credentials
        for cred_type, pattern in self.credential_patterns.items():
            matches = pattern.findall(response)
            if matches:
                findings["credentials"].append({
                    "type": cred_type,
                    "count": len(matches),
                    "severity": "critical"
                })
        
        # Check for protected content
        for label, protected_text in self.protected.items():
            if self._fuzzy_match(response, protected_text):
                findings["protected_content"].append({
                    "label": label,
                    "severity": "critical"
                })
        
        # Calculate risk score
        findings["risk_score"] = self._calculate_risk(findings)
        findings["requires_action"] = findings["risk_score"] > 0.3
        
        return findings
    
    def _redact(self, text: str) -> str:
        """Redact sensitive content for logging."""
        if len(text) <= 4:
            return "****"
        return text[:2] + "****" + text[-2:]
    
    def _fuzzy_match(self, response: str, protected: str, threshold: float = 0.8) -> bool:
        """Check for fuzzy match of protected content."""
        from difflib import SequenceMatcher
        
        # Check substrings
        protected_words = protected.lower().split()
        response_lower = response.lower()
        
        matched_words = sum(1 for w in protected_words if w in response_lower)
        ratio = matched_words / len(protected_words) if protected_words else 0
        
        return ratio >= threshold
    
    def _calculate_risk(self, findings: dict) -> float:
        """Calculate overall risk score."""
        risk = 0.0
        
        # Credentials are critical
        if findings["credentials"]:
            risk = max(risk, 0.9)
        
        # Protected content is critical
        if findings["protected_content"]:
            risk = max(risk, 0.95)
        
        # PII varies by type
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

## Layer 3: Prompt Leakage Prevention

```python
class PromptLeakagePreventor:
    """Prevent system prompt disclosure in responses."""
    
    def __init__(self, system_prompt: str, protected_phrases: List[str] = None):
        self.system_prompt = system_prompt
        self.protected_phrases = protected_phrases or []
        
        # Extract key components from system prompt
        self.prompt_fingerprints = self._extract_fingerprints(system_prompt)
    
    def _extract_fingerprints(self, prompt: str) -> List[str]:
        """Extract distinctive phrases from system prompt."""
        # Split into sentences
        sentences = re.split(r'[.!?]', prompt)
        
        # Take distinctive ones (longer, unique phrasing)
        fingerprints = []
        for s in sentences:
            s = s.strip()
            if len(s) > 30 and len(s.split()) > 5:
                fingerprints.append(s.lower())
        
        return fingerprints
    
    def check(self, response: str) -> dict:
        """Check response for prompt leakage."""
        
        findings = []
        
        # Check for direct inclusion
        response_lower = response.lower()
        
        for fingerprint in self.prompt_fingerprints:
            if fingerprint in response_lower:
                findings.append({
                    "type": "direct_leak",
                    "fingerprint": fingerprint[:50] + "...",
                    "severity": "critical"
                })
        
        # Check protected phrases
        for phrase in self.protected_phrases:
            if phrase.lower() in response_lower:
                findings.append({
                    "type": "protected_phrase",
                    "phrase": phrase,
                    "severity": "high"
                })
        
        # Check for meta-discussion about prompts
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
        
        # Block if critical issues
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
        
        # Redact credentials
        for cred in leakage_findings.get("credentials", []):
            pattern = self._get_credential_pattern(cred["type"])
            sanitized = pattern.sub(self.redaction_placeholder, sanitized)
            modifications.append(f"Redacted {cred['type']}")
        
        # Redact harmful content spans
        for finding in content_findings.get("findings", []):
            if finding.action == "redact":
                start, end = finding.span
                sanitized = sanitized[:start] + self.redaction_placeholder + sanitized[end:]
                modifications.append(f"Redacted {finding.category}")
        
        return {
            "original": response,
            "sanitized": sanitized,
            "blocked": False,
            "modifications": modifications
        }
```

---

## Complete Pipeline

```python
class OutputFilterPipeline:
    """Complete output filtering pipeline."""
    
    def __init__(self, system_prompt: str, protected_content: dict = None):
        self.content_classifier = OutputContentClassifier()
        self.leakage_detector = DataLeakageDetector(protected_content)
        self.prompt_guard = PromptLeakagePreventor(system_prompt)
        self.sanitizer = ResponseSanitizer()
    
    def filter(self, response: str) -> dict:
        """Filter LLM response through all layers."""
        
        # Layer 1: Content classification
        content_result = self.content_classifier.classify(response)
        
        # Layer 2: Data leakage detection
        leakage_result = self.leakage_detector.scan(response)
        
        # Layer 3: Prompt leakage check
        prompt_result = self.prompt_guard.check(response)
        
        # Layer 4: Sanitization
        final_result = self.sanitizer.sanitize(
            response,
            content_result,
            leakage_result,
            prompt_result
        )
        
        # Compile full result
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

## SENTINEL Integration

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
    # Automatically filtered before return
    return response
```

---

## Key Takeaways

1. **Filter outputs too** - Input filtering is not enough
2. **Detect multiple risks** - Content, leakage, prompts
3. **Sanitize, don't just block** - Keep useful responses
4. **Protect your prompts** - Prevent disclosure
5. **Log everything** - For incident response

---

*AI Security Academy | Lesson 05.2.2*
