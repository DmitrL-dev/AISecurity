# Input Filtering

> **Урок:** 05.2.1 - Input Layer Defense  
> **Время:** 40 минут  
> **Пререквизиты:** Basic security concepts

---

## Цели обучения

К концу этого урока вы сможете:

1. Реализовывать multi-layer input filtering
2. Детектировать injection patterns до LLM processing
3. Балансировать security с usability
4. Конфигурировать adaptive filtering pipelines

---

## Defense-in-Depth Architecture

```
User Input → Preprocessing → Pattern Detection → Semantic Analysis → 
          → Policy Check → Sanitization → Forward to LLM
```

| Layer | Function | Latency |
|-------|----------|---------|
| **Preprocessing** | Normalize, decode | <1ms |
| **Pattern Detection** | Regex, keyword | 1-5ms |
| **Semantic Analysis** | ML classifier | 10-50ms |
| **Policy Check** | Business rules | 1-2ms |
| **Sanitization** | Remove/modify | <1ms |

---

## Layer 1: Preprocessing

### Normalization

```python
import unicodedata
import re

class InputPreprocessor:
    """Normalize и prepare input для analysis."""
    
    def preprocess(self, text: str) -> dict:
        """Full preprocessing pipeline."""
        
        original = text
        
        # 1. Unicode normalization
        text = self._normalize_unicode(text)
        
        # 2. Decode encoded content
        text = self._decode_encodings(text)
        
        # 3. Remove zero-width characters
        text = self._remove_invisible(text)
        
        # 4. Normalize whitespace
        text = self._normalize_whitespace(text)
        
        # Track modifications
        modifications = self._track_changes(original, text)
        
        return {
            "original": original,
            "normalized": text,
            "modifications": modifications,
            "suspicious": len(modifications) > 3
        }
    
    def _normalize_unicode(self, text: str) -> str:
        """Normalize unicode чтобы catch homoglyph attacks."""
        # NFC normalization
        text = unicodedata.normalize('NFC', text)
        
        # Convert confusables to ASCII где возможно
        confusables = {
            'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p',  # Cyrillic
            'с': 'c', 'х': 'x', 'і': 'i', 'у': 'y',
            '０': '0', '１': '1', '２': '2',  # Fullwidth
            'Ａ': 'A', 'Ｂ': 'B',
        }
        
        for confusable, replacement in confusables.items():
            text = text.replace(confusable, replacement)
        
        return text
    
    def _remove_invisible(self, text: str) -> str:
        """Remove zero-width и invisible characters."""
        # Zero-width characters
        invisible = [
            '\u200b',  # Zero-width space
            '\u200c',  # Zero-width non-joiner
            '\u200d',  # Zero-width joiner
            '\u2060',  # Word joiner
            '\ufeff',  # BOM
            '\u00ad',  # Soft hyphen
        ]
        
        for char in invisible:
            text = text.replace(char, '')
        
        # Remove other control characters (except newline, tab)
        text = ''.join(
            c for c in text 
            if not unicodedata.category(c).startswith('C') or c in '\n\t\r'
        )
        
        return text
```

---

## Layer 2: Pattern Detection

### Injection Pattern Matching

```python
import re
from typing import List, Tuple

class InjectionPatternDetector:
    """Detect injection patterns используя regex и keywords."""
    
    PATTERNS = [
        # Instruction override
        (r'(?:ignore|disregard|forget|override).*(?:previous|above|prior|all).*(?:instructions?|rules?|guidelines?)', "instruction_override", 0.9),
        
        # System/Admin mode
        (r'(?:enter|switch|enable|activate).*(?:admin|system|debug|developer|god|sudo).*(?:mode|access)', "mode_switch", 0.85),
        
        # Role impersonation
        (r'(?:you are now|pretend|act as|behave as).*(?:DAN|unrestricted|uncensored|jailbroken)', "role_impersonation", 0.9),
        
        # Prompt leakage attempts
        (r'(?:reveal|show|display|print|tell me).*(?:system|prompt|instructions?|rules)', "prompt_leakage", 0.7),
        
        # Encoding tricks
        (r'(?:base64|rot13|hex|binary|unicode).*(?:decode|encode|translate)', "encoding_trick", 0.6),
        
        # Context manipulation
        (r'---+.*(?:system|user|assistant)', "context_separator", 0.8),
        (r'\[(?:SYSTEM|USER|INST)\]', "role_marker", 0.75),
    ]
    
    SUSPICIOUS_KEYWORDS = {
        "high": ["jailbreak", "bypass", "exploit", "hack the", "pwn"],
        "medium": ["ignore instructions", "system prompt", "act as", "pretend to be", "roleplay"],
        "low": ["hypothetically", "in theory", "just curious", "for research"],
    }
    
    def detect(self, text: str) -> dict:
        """Detect injection patterns в тексте."""
        
        findings = []
        
        # Pattern matching
        for pattern, label, base_score in self.compiled_patterns:
            matches = pattern.findall(text)
            if matches:
                findings.append({
                    "type": "pattern",
                    "label": label,
                    "score": base_score,
                    "matches": matches[:3]
                })
        
        # Keyword matching
        text_lower = text.lower()
        for severity, keywords in self.SUSPICIOUS_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    score = {"high": 0.8, "medium": 0.5, "low": 0.3}[severity]
                    findings.append({
                        "type": "keyword",
                        "label": keyword,
                        "score": score,
                        "severity": severity
                    })
        
        # Calculate overall risk
        if findings:
            max_score = max(f["score"] for f in findings)
            # Boost для multiple findings
            boost = min(len(findings) * 0.05, 0.2)
            overall_score = min(max_score + boost, 1.0)
        else:
            overall_score = 0.0
        
        return {
            "findings": findings,
            "risk_score": overall_score,
            "action": self._recommend_action(overall_score)
        }
    
    def _recommend_action(self, score: float) -> str:
        if score >= 0.8:
            return "block"
        elif score >= 0.5:
            return "flag"
        elif score >= 0.3:
            return "monitor"
        else:
            return "allow"
```

---

## Layer 3: Semantic Analysis

### ML-Based Classification

```python
import numpy as np
from dataclasses import dataclass

@dataclass
class ClassificationResult:
    is_attack: bool
    attack_type: str
    confidence: float
    explanation: str

class SemanticInjectionClassifier:
    """ML-based semantic analysis для injection detection."""
    
    def __init__(self, model_path: str = None):
        self.model = self._load_model(model_path)
        self.threshold = 0.7
    
    def classify(self, text: str) -> ClassificationResult:
        """Classify text как attack или benign."""
        
        # Get embedding
        embedding = self._get_embedding(text)
        
        # Run classifier
        prediction = self.model.predict(embedding.reshape(1, -1))
        probabilities = self.model.predict_proba(embedding.reshape(1, -1))[0]
        
        # Get attack type если predicted как attack
        is_attack = prediction[0] == 1 and max(probabilities) > self.threshold
        
        if is_attack:
            attack_type = self._determine_attack_type(text, embedding)
            explanation = self._generate_explanation(text, attack_type)
        else:
            attack_type = None
            explanation = "No attack detected"
        
        return ClassificationResult(
            is_attack=is_attack,
            attack_type=attack_type,
            confidence=max(probabilities),
            explanation=explanation
        )
```

---

## Layer 4: Policy Engine

```python
from dataclasses import dataclass
from typing import List, Callable

@dataclass
class PolicyRule:
    name: str
    condition: Callable[[dict], bool]
    action: str  # "allow", "block", "modify", "flag"
    priority: int
    message: str

class PolicyEngine:
    """Apply business rules к input analysis results."""
    
    def __init__(self):
        self.rules: List[PolicyRule] = []
        self._load_default_rules()
    
    def _load_default_rules(self):
        """Load default policy rules."""
        
        self.rules = [
            # Critical patterns always block
            PolicyRule(
                name="block_critical_injection",
                condition=lambda r: r.get("pattern_score", 0) >= 0.9,
                action="block",
                priority=100,
                message="Critical injection pattern detected"
            ),
            
            # High semantic confidence blocks
            PolicyRule(
                name="block_semantic_attack",
                condition=lambda r: (
                    r.get("semantic_is_attack", False) and 
                    r.get("semantic_confidence", 0) >= 0.85
                ),
                action="block",
                priority=90,
                message="High-confidence attack detected"
            ),
        ]
    
    def evaluate(self, analysis_result: dict) -> dict:
        """Evaluate all policies против analysis result."""
        
        # Sort by priority (highest first)
        sorted_rules = sorted(self.rules, key=lambda r: -r.priority)
        
        triggered_rules = []
        final_action = "allow"
        
        for rule in sorted_rules:
            if rule.condition(analysis_result):
                triggered_rules.append(rule)
                
                # Take most restrictive action
                if rule.action == "block":
                    final_action = "block"
                    break
                elif rule.action == "flag" and final_action == "allow":
                    final_action = "flag"
        
        return {
            "action": final_action,
            "triggered_rules": [r.name for r in triggered_rules],
            "messages": [r.message for r in triggered_rules]
        }
```

---

## Интеграция с SENTINEL

```python
from sentinel import configure, InputGuard

configure(
    input_filtering=True,
    preprocessing=True,
    pattern_detection=True,
    semantic_analysis=True
)

input_guard = InputGuard(
    block_threshold=0.8,
    flag_threshold=0.5,
    enable_semantic=True
)

@input_guard.protect
def process_user_input(text: str):
    # Автоматически filtered
    return llm.generate(text)
```

---

## Ключевые выводы

1. **Layer defenses** — No single check catches everything
2. **Preprocess first** — Decode tricks before analysis
3. **Combine approaches** — Patterns + semantics
4. **Policy flexibility** — Business rules for final decision
5. **Monitor and adapt** — Learn from bypasses

---

*AI Security Academy | Урок 05.2.1*
