# Jailbreak Attacks на LLM

> **Уровень:** Core  
> **Время:** 45 минут  
> **Трек:** 03 — LLM Attack Taxonomy  
> **Модуль:** 03.1 — Prompt-Level Attacks  
> **Версия:** 1.0

---

## Цели обучения

- [ ] Понять механизмы jailbreak атак
- [ ] Изучить основные техники jailbreaking
- [ ] Имплементировать детекцию jailbreak попыток
- [ ] Понять defense strategies

---

## 1. Jailbreak Overview

### 1.1 Что такое Jailbreak?

```
┌────────────────────────────────────────────────────────────────────┐
│              JAILBREAK ATTACK TAXONOMY                             │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Definition: Techniques to bypass LLM safety guardrails           │
│  Goal: Make LLM generate prohibited/harmful content               │
│                                                                    │
│  Attack Categories:                                                │
│  ├── Role-Playing: Assume alternative persona                    │
│  ├── Hypothetical: "What if" scenarios                           │
│  ├── Encoding: Obfuscate malicious intent                        │
│  ├── Multi-Turn: Gradual context manipulation                    │
│  ├── Context Overflow: Exhaust safety context                    │
│  └── Prefix Injection: Force specific output start               │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 2. Jailbreak Techniques

### 2.1 Role-Playing Attacks

```python
ROLEPLAY_PATTERNS = [
    # DAN-style
    r"pretend\s+to\s+be\s+(?:DAN|evil|unrestricted)",
    r"you\s+are\s+now\s+(?:DAN|jailbroken|unfiltered)",
    r"act\s+as\s+(?:if|though)\s+you\s+have\s+no\s+(?:rules|restrictions)",
    
    # Persona switching
    r"from\s+now\s+on\s+you(?:'re|\s+are)\s+(?:my|an?)\s+(?:evil|unethical)",
    r"respond\s+as\s+(?:a|an)\s+(?:evil|unrestricted|unfiltered)",
    
    # Developer mode
    r"developer\s+mode\s+(?:enabled|activated|on)",
    r"ignore\s+(?:your|all)\s+(?:previous|safety)\s+(?:instructions|rules)"
]

class RolePlayDetector:
    """Detects role-play jailbreak attempts"""
    
    def __init__(self):
        import re
        self.patterns = [re.compile(p, re.IGNORECASE) for p in ROLEPLAY_PATTERNS]
    
    def detect(self, text: str) -> dict:
        matches = []
        for pattern in self.patterns:
            if pattern.search(text):
                matches.append(pattern.pattern)
        
        return {
            'detected': len(matches) > 0,
            'type': 'role_play',
            'confidence': min(0.3 + 0.2 * len(matches), 1.0),
            'patterns_matched': matches
        }
```

### 2.2 Hypothetical/Fiction Framing

```python
HYPOTHETICAL_PATTERNS = [
    r"write\s+a\s+(?:story|fiction|novel)\s+(?:about|where)",
    r"in\s+a\s+hypothetical\s+(?:scenario|world|situation)",
    r"imagine\s+(?:you\s+are|that|if)",
    r"for\s+(?:educational|research|academic)\s+purposes",
    r"purely\s+(?:fictional|hypothetical|theoretical)",
    r"(?:creative|fiction)\s+writing\s+(?:exercise|project)"
]

class HypotheticalDetector:
    """Detects hypothetical framing attempts"""
    
    def __init__(self):
        import re
        self.patterns = [re.compile(p, re.IGNORECASE) for p in HYPOTHETICAL_PATTERNS]
        self.harmful_keywords = [
            'hack', 'exploit', 'weapon', 'drug', 'bomb', 
            'poison', 'attack', 'steal', 'break into'
        ]
    
    def detect(self, text: str) -> dict:
        text_lower = text.lower()
        
        has_hypothetical = any(p.search(text) for p in self.patterns)
        has_harmful = any(kw in text_lower for kw in self.harmful_keywords)
        
        if has_hypothetical and has_harmful:
            return {
                'detected': True,
                'type': 'hypothetical_harmful',
                'confidence': 0.8
            }
        elif has_hypothetical:
            return {
                'detected': True,
                'type': 'hypothetical_frame',
                'confidence': 0.4
            }
        
        return {'detected': False}
```

### 2.3 Encoding Attacks

```python
import base64
import re

class EncodingDetector:
    """Detects encoding-based obfuscation"""
    
    def detect(self, text: str) -> dict:
        results = {
            'detected': False,
            'encodings': []
        }
        
        # Base64 detection
        base64_pattern = r'[A-Za-z0-9+/]{20,}={0,2}'
        b64_matches = re.findall(base64_pattern, text)
        
        for match in b64_matches:
            try:
                decoded = base64.b64decode(match).decode('utf-8')
                if self._is_suspicious(decoded):
                    results['detected'] = True
                    results['encodings'].append({
                        'type': 'base64',
                        'decoded_preview': decoded[:50]
                    })
            except:
                pass
        
        # Hex encoding
        hex_pattern = r'(?:\\x[0-9a-fA-F]{2}){4,}'
        if re.search(hex_pattern, text):
            results['detected'] = True
            results['encodings'].append({'type': 'hex_escape'})
        
        # Unicode escapes
        unicode_pattern = r'(?:\\u[0-9a-fA-F]{4}){4,}'
        if re.search(unicode_pattern, text):
            results['detected'] = True
            results['encodings'].append({'type': 'unicode_escape'})
        
        return results
    
    def _is_suspicious(self, text: str) -> bool:
        keywords = ['ignore', 'bypass', 'override', 'jailbreak', 'hack']
        return any(kw in text.lower() for kw in keywords)
```

---

## 3. Multi-Turn Jailbreaks

### 3.1 Crescendo Attacks

```python
from dataclasses import dataclass
from typing import List

@dataclass
class ConversationTurn:
    role: str
    content: str
    is_suspicious: bool = False

class MultiTurnDetector:
    """Detects multi-turn jailbreak attempts"""
    
    def __init__(self):
        self.escalation_indicators = [
            ('benign', 'slightly_suspicious', 'suspicious', 'harmful'),
        ]
        self.context_manipulation_keywords = [
            'remember earlier', 'as we discussed', 'you agreed',
            'continue from', 'based on our previous'
        ]
    
    def analyze_conversation(self, turns: List[ConversationTurn]) -> dict:
        if len(turns) < 3:
            return {'detected': False}
        
        # Track suspicion levels
        levels = []
        for turn in turns:
            if turn.role == 'user':
                level = self._assess_suspicion(turn.content)
                levels.append(level)
        
        # Detect escalation pattern
        if self._is_escalating(levels):
            return {
                'detected': True,
                'type': 'crescendo',
                'confidence': 0.7,
                'pattern': 'gradual_escalation'
            }
        
        # Detect context manipulation
        recent_text = ' '.join(t.content for t in turns[-3:] if t.role == 'user')
        for keyword in self.context_manipulation_keywords:
            if keyword in recent_text.lower():
                return {
                    'detected': True,
                    'type': 'context_manipulation',
                    'confidence': 0.6
                }
        
        return {'detected': False}
    
    def _assess_suspicion(self, text: str) -> int:
        """0=benign, 1=slightly, 2=suspicious, 3=harmful"""
        text_lower = text.lower()
        
        harmful = ['hack', 'exploit', 'weapon', 'illegal']
        suspicious = ['bypass', 'ignore rules', 'pretend']
        slightly = ['hypothetically', 'imagine', 'creative']
        
        if any(w in text_lower for w in harmful):
            return 3
        if any(w in text_lower for w in suspicious):
            return 2
        if any(w in text_lower for w in slightly):
            return 1
        return 0
    
    def _is_escalating(self, levels: List[int]) -> bool:
        if len(levels) < 3:
            return False
        
        # Check if trend is upward
        increases = sum(1 for i in range(1, len(levels)) if levels[i] > levels[i-1])
        return increases >= len(levels) // 2 and levels[-1] >= 2
```

---

## 4. Jailbreak Detection Engine

```python
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class JailbreakResult:
    detected: bool
    attack_type: str
    confidence: float
    details: Dict

class JailbreakDetectionEngine:
    """Combined jailbreak detection"""
    
    def __init__(self):
        self.roleplay = RolePlayDetector()
        self.hypothetical = HypotheticalDetector()
        self.encoding = EncodingDetector()
        self.multiturn = MultiTurnDetector()
    
    def detect_single(self, text: str) -> JailbreakResult:
        """Detect jailbreak in single message"""
        results = []
        
        # Run all detectors
        roleplay = self.roleplay.detect(text)
        if roleplay['detected']:
            results.append(('role_play', roleplay.get('confidence', 0.7)))
        
        hypothetical = self.hypothetical.detect(text)
        if hypothetical['detected']:
            results.append((hypothetical['type'], hypothetical.get('confidence', 0.5)))
        
        encoding = self.encoding.detect(text)
        if encoding['detected']:
            results.append(('encoding', 0.8))
        
        if not results:
            return JailbreakResult(False, 'none', 0.0, {})
        
        # Return highest confidence
        results.sort(key=lambda x: -x[1])
        top = results[0]
        
        return JailbreakResult(
            detected=True,
            attack_type=top[0],
            confidence=top[1],
            details={'all_detections': results}
        )
    
    def detect_conversation(self, turns: List[Dict]) -> JailbreakResult:
        """Detect multi-turn jailbreak"""
        conv_turns = [
            ConversationTurn(t['role'], t['content'])
            for t in turns
        ]
        
        multiturn = self.multiturn.analyze_conversation(conv_turns)
        if multiturn['detected']:
            return JailbreakResult(
                detected=True,
                attack_type=multiturn['type'],
                confidence=multiturn['confidence'],
                details=multiturn
            )
        
        # Also check last message individually
        if turns and turns[-1]['role'] == 'user':
            return self.detect_single(turns[-1]['content'])
        
        return JailbreakResult(False, 'none', 0.0, {})
```

---

## 5. SENTINEL Integration

```python
from dataclasses import dataclass

@dataclass
class JailbreakConfig:
    """Jailbreak detection configuration"""
    enable_roleplay: bool = True
    enable_hypothetical: bool = True
    enable_encoding: bool = True
    enable_multiturn: bool = True
    confidence_threshold: float = 0.6

class SENTINELJailbreakDetector:
    """Jailbreak detector for SENTINEL"""
    
    def __init__(self, config: JailbreakConfig):
        self.config = config
        self.engine = JailbreakDetectionEngine()
    
    def check(self, text: str) -> Dict:
        """Check single message for jailbreak"""
        result = self.engine.detect_single(text)
        
        return {
            'is_jailbreak': result.detected and result.confidence >= self.config.confidence_threshold,
            'attack_type': result.attack_type,
            'confidence': result.confidence,
            'action': self._get_action(result)
        }
    
    def check_conversation(self, turns: List[Dict]) -> Dict:
        """Check conversation for jailbreak"""
        result = self.engine.detect_conversation(turns)
        
        return {
            'is_jailbreak': result.detected and result.confidence >= self.config.confidence_threshold,
            'attack_type': result.attack_type,
            'confidence': result.confidence,
            'action': self._get_action(result)
        }
    
    def _get_action(self, result: JailbreakResult) -> str:
        if not result.detected:
            return 'ALLOW'
        if result.confidence >= 0.9:
            return 'BLOCK'
        if result.confidence >= 0.7:
            return 'BLOCK'
        if result.confidence >= self.config.confidence_threshold:
            return 'REVIEW'
        return 'LOG'
```

---

## 6. Defense Strategies

### 6.1 Layered Defense

```
┌─────────────────────────────────────────────────────────────┐
│              JAILBREAK DEFENSE LAYERS                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Layer 1: Input Filtering                                   │
│  ├── Pattern matching                                      │
│  ├── Encoding detection                                    │
│  └── Keyword blocklisting                                  │
│                                                             │
│  Layer 2: Semantic Analysis                                 │
│  ├── Intent classification                                 │
│  ├── Context analysis                                      │
│  └── Role-play detection                                   │
│                                                             │
│  Layer 3: Model-level                                       │
│  ├── Strong system prompts                                 │
│  ├── Constitutional AI                                     │
│  └── RLHF safety training                                  │
│                                                             │
│  Layer 4: Output Filtering                                  │
│  ├── Response classification                               │
│  ├── Harmful content detection                             │
│  └── PII removal                                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. Резюме

| Тип атаки | Описание | Детекция |
|-----------|----------|----------|
| **Role-Play** | Persona switching | Pattern matching |
| **Hypothetical** | Fiction framing | Context + harmful keywords |
| **Encoding** | Base64, hex, unicode | Decode + analyze |
| **Multi-Turn** | Gradual escalation | Conversation tracking |

---

## Следующий урок

→ [02. Prompt Injection](02-prompt-injection.md)

---

*AI Security Academy | Track 03: LLM Attacks | Module 03.1: Prompt-Level*
