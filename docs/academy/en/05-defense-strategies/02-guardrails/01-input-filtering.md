# Input Validation for LLM Security

> **Level:** Intermediate  
> **Time:** 50 minutes  
> **Track:** 05 — Defense Strategies  
> **Module:** 05.2 — Guardrails  
> **Version:** 2.0 (Production)

---

## Learning Objectives

Upon completing this lesson, you will be able to:

- [ ] Explain why input validation is critical for LLM applications
- [ ] Implement multi-layer input validation pipeline
- [ ] Apply normalization and sanitization techniques
- [ ] Detect injection patterns and encoded payloads
- [ ] Integrate input validation with SENTINEL

---

## 1. Input Validation Architecture

### 1.1 Defense Layers

```
┌────────────────────────────────────────────────────────────────────┐
│                    INPUT VALIDATION PIPELINE                       │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  RAW INPUT                                                         │
│      ↓                                                             │
│  ╔═══════════════════════════════════════════════════════════════╗ │
│  ║  LAYER 1: SIZE & FORMAT                                       ║ │
│  ║  • Max length check                                           ║ │
│  ║  • Character set validation                                   ║ │
│  ║  • Rate limiting                                              ║ │
│  ╚═══════════════════════════════════════════════════════════════╝ │
│      ↓                                                             │
│  ╔═══════════════════════════════════════════════════════════════╗ │
│  ║  LAYER 2: NORMALIZATION                                       ║ │
│  ║  • Unicode normalization (NFKC)                               ║ │
│  ║  • Homoglyph detection                                        ║ │
│  ║  • Invisible character removal                                ║ │
│  ╚═══════════════════════════════════════════════════════════════╝ │
│      ↓                                                             │
│  ╔═══════════════════════════════════════════════════════════════╗ │
│  ║  LAYER 3: PATTERN DETECTION                                   ║ │
│  ║  • Injection pattern matching                                 ║ │
│  ║  • Jailbreak signature detection                              ║ │
│  ║  • Encoded content detection                                  ║ │
│  ╚═══════════════════════════════════════════════════════════════╝ │
│      ↓                                                             │
│  ╔═══════════════════════════════════════════════════════════════╗ │
│  ║  LAYER 4: SEMANTIC ANALYSIS                                   ║ │
│  ║  • Intent classification                                      ║ │
│  ║  • Topic boundary check                                       ║ │
│  ║  • Risk scoring                                               ║ │
│  ╚═══════════════════════════════════════════════════════════════╝ │
│      ↓                                                             │
│  VALIDATED INPUT                                                   │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### 1.2 Core Classes

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum

class ValidationAction(Enum):
    ALLOW = "allow"
    FLAG = "flag"
    BLOCK = "block"

@dataclass
class ValidationResult:
    action: ValidationAction
    validated_input: str
    original_input: str
    risk_score: float
    detections: List[Dict] = field(default_factory=list)
    applied_transforms: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'action': self.action.value,
            'risk_score': self.risk_score,
            'detections': self.detections,
            'transforms': self.applied_transforms
        }
```

---

## 2. Layer 1: Size & Format Validation

```python
class SizeFormatValidator:
    """First layer: basic size and format checks."""
    
    def __init__(self, config: Dict = None):
        self.config = config or {
            'max_length': 10000,
            'min_length': 1,
            'max_lines': 500,
            'allowed_chars': None,  # None = all allowed
            'blocked_chars': ['\x00', '\x1b']  # Null, escape
        }
    
    def validate(self, text: str) -> ValidationResult:
        detections = []
        
        # Length check
        if len(text) > self.config['max_length']:
            detections.append({
                'type': 'length_exceeded',
                'value': len(text),
                'max': self.config['max_length']
            })
            return ValidationResult(
                action=ValidationAction.BLOCK,
                validated_input="",
                original_input=text,
                risk_score=1.0,
                detections=detections
            )
        
        if len(text) < self.config['min_length']:
            detections.append({'type': 'too_short'})
        
        # Line count check
        lines = text.count('\n')
        if lines > self.config['max_lines']:
            detections.append({
                'type': 'too_many_lines',
                'value': lines
            })
        
        # Blocked characters
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
            original_input=text,
            risk_score=risk,
            detections=detections
        )
```

---

## 3. Layer 2: Normalization

```python
import unicodedata
import re

class CharacterNormalizer:
    """Normalize and clean input text."""
    
    # Unicode confusables (homoglyphs)
    HOMOGLYPHS = {
        'А': 'A', 'В': 'B', 'С': 'C', 'Е': 'E', 'Н': 'H',
        'І': 'I', 'К': 'K', 'М': 'M', 'О': 'O', 'Р': 'P',
        'Т': 'T', 'Х': 'X', 'а': 'a', 'с': 'c', 'е': 'e',
        'о': 'o', 'р': 'p', 'х': 'x', 'у': 'y',
        'ⅰ': 'i', 'ⅱ': 'ii', 'Ⅰ': 'I', 'ℐ': 'I',
        '𝐈': 'I', '𝐢': 'i', '𝑖': 'i', '𝒊': 'i',
        '℮': 'e', 'ℯ': 'e', 'ⓔ': 'e',
    }
    
    # Invisible characters
    INVISIBLE_CHARS = [
        '\u200b',  # Zero-width space
        '\u200c',  # Zero-width non-joiner
        '\u200d',  # Zero-width joiner
        '\ufeff',  # BOM
        '\u00ad',  # Soft hyphen
        '\u2060',  # Word joiner
    ]
    
    def normalize(self, text: str) -> tuple[str, List[str]]:
        transforms = []
        result = text
        
        # NFKC normalization
        normalized = unicodedata.normalize('NFKC', result)
        if normalized != result:
            transforms.append('nfkc_normalization')
            result = normalized
        
        # Homoglyph replacement
        replaced = self._replace_homoglyphs(result)
        if replaced != result:
            transforms.append('homoglyph_replacement')
            result = replaced
        
        # Remove invisible characters
        cleaned = self._remove_invisible(result)
        if cleaned != result:
            transforms.append('invisible_char_removal')
            result = cleaned
        
        # Collapse whitespace
        collapsed = re.sub(r'\s+', ' ', result).strip()
        if collapsed != result:
            transforms.append('whitespace_collapse')
            result = collapsed
        
        return result, transforms
    
    def _replace_homoglyphs(self, text: str) -> str:
        for homo, latin in self.HOMOGLYPHS.items():
            text = text.replace(homo, latin)
        return text
    
    def _remove_invisible(self, text: str) -> str:
        for char in self.INVISIBLE_CHARS:
            text = text.replace(char, '')
        return text
    
    def detect_homoglyphs(self, text: str) -> List[Dict]:
        detections = []
        for char in text:
            if char in self.HOMOGLYPHS:
                detections.append({
                    'type': 'homoglyph',
                    'char': char,
                    'replacement': self.HOMOGLYPHS[char],
                    'position': text.index(char)
                })
        return detections
```

---

## 4. Layer 3: Pattern Detection

```python
class InjectionPatternDetector:
    """Detect injection and jailbreak patterns."""
    
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
                r'roleplay\s+as',
            ],
            'severity': 0.6
        },
        'system_prompt_extraction': {
            'patterns': [
                r'(show|reveal|display|tell)\s+(me\s+)?(your|the)\s+(system\s+)?prompt',
                r'what\s+(are|is)\s+your\s+(instructions?|rules?)',
                r'repeat\s+(everything|all)\s+(above|before)',
            ],
            'severity': 0.7
        },
        'delimiter_injection': {
            'patterns': [
                r'\[/?SYSTEM\]',
                r'\[/?ADMIN\]',
                r'<\|im_(start|end)\|>',
                r'###\s*(SYSTEM|ADMIN|INSTRUCTIONS?)',
            ],
            'severity': 0.9
        }
    }
    
    def __init__(self):
        self.compiled = {}
        for category, data in self.PATTERNS.items():
            self.compiled[category] = [
                (re.compile(p, re.I), data['severity'])
                for p in data['patterns']
            ]
    
    def detect(self, text: str) -> List[Dict]:
        detections = []
        
        for category, patterns in self.compiled.items():
            for pattern, severity in patterns:
                matches = pattern.findall(text)
                if matches:
                    detections.append({
                        'type': 'injection_pattern',
                        'category': category,
                        'matches': matches[:3],
                        'severity': severity
                    })
        
        return detections


class EncodedContentDetector:
    """Detect base64, hex, and other encoded content."""
    
    def detect(self, text: str) -> List[Dict]:
        detections = []
        
        # Base64 detection
        b64_pattern = r'[A-Za-z0-9+/]{20,}={0,2}'
        b64_matches = re.findall(b64_pattern, text)
        for match in b64_matches:
            if self._is_valid_base64(match):
                detections.append({
                    'type': 'base64_content',
                    'sample': match[:30] + '...',
                    'length': len(match)
                })
        
        # Hex detection
        hex_pattern = r'(?:0x)?[0-9a-fA-F]{20,}'
        hex_matches = re.findall(hex_pattern, text)
        for match in hex_matches:
            detections.append({
                'type': 'hex_content',
                'sample': match[:30] + '...',
                'length': len(match)
            })
        
        # URL encoding
        if re.search(r'%[0-9a-fA-F]{2}', text):
            detections.append({'type': 'url_encoded_content'})
        
        return detections
    
    def _is_valid_base64(self, s: str) -> bool:
        import base64
        try:
            base64.b64decode(s)
            return len(s) % 4 == 0
        except:
            return False
```

---

## 5. SENTINEL Integration

```python
class SENTINELInputValidator:
    """SENTINEL module for comprehensive input validation."""
    
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
        
        # Layer 1: Size & Format
        size_result = self.size_validator.validate(current_text)
        if size_result.action == ValidationAction.BLOCK:
            return size_result
        
        all_detections.extend(size_result.detections)
        current_text = size_result.validated_input
        
        # Layer 2: Normalization
        normalized, transforms = self.normalizer.normalize(current_text)
        all_transforms.extend(transforms)
        
        homoglyphs = self.normalizer.detect_homoglyphs(text)
        if homoglyphs:
            all_detections.extend(homoglyphs)
            max_severity = max(max_severity, 0.4)
        
        current_text = normalized
        
        # Layer 3: Pattern Detection
        injection_detections = self.injection_detector.detect(current_text)
        all_detections.extend(injection_detections)
        
        for det in injection_detections:
            max_severity = max(max_severity, det.get('severity', 0.5))
        
        # Layer 3b: Encoding Detection
        encoding_detections = self.encoding_detector.detect(current_text)
        all_detections.extend(encoding_detections)
        
        if encoding_detections:
            max_severity = max(max_severity, 0.5)
        
        # Calculate risk score
        risk_score = min(max_severity + len(all_detections) * 0.05, 1.0)
        
        # Determine action
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

## 6. Summary

### Validation Layers

| Layer | Purpose | Techniques |
|-------|---------|------------|
| **Size/Format** | Basic limits | Length, charset, rate |
| **Normalization** | Canonicalization | NFKC, homoglyphs, invisible |
| **Pattern** | Attack detection | Regex, signatures |
| **Semantic** | Intent analysis | Classification, scoring |

### Quick Checklist

```
□ Set max input length (recommended: 10,000 chars)
□ Apply NFKC normalization
□ Detect homoglyphs and invisible characters
□ Match injection patterns
□ Detect encoded payloads
□ Calculate risk score
□ Log all detections
```

---

## Next Lesson

→ [Output Filtering](02-output-filtering.md)

---

*AI Security Academy | Track 05: Defense Strategies | Guardrails*
