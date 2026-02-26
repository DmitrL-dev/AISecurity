# Jailbreak Attacks on LLMs

> **Level:** Core  
> **Time:** 45 minutes  
> **Track:** 03 — LLM Attack Taxonomy  
> **Module:** 03.1 — Prompt-Level Attacks  
> **Version:** 1.0

---

## Learning Objectives

- [ ] Understand jailbreak attack mechanisms
- [ ] Study main jailbreaking techniques
- [ ] Implement jailbreak attempt detection
- [ ] Understand defense strategies

---

## 1. Jailbreak Overview

```
┌────────────────────────────────────────────────────────────────────┐
│              JAILBREAK ATTACK TAXONOMY                             │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Definition: Techniques to bypass LLM safety guardrails           │
│  Goal: Make LLM generate prohibited/harmful content               │
│                                                                    │
│  Categories:                                                       │
│  ├── Role-Playing: Assume alternative persona                    │
│  ├── Hypothetical: "What if" scenarios                           │
│  ├── Encoding: Obfuscate malicious intent                        │
│  ├── Multi-Turn: Gradual context manipulation                    │
│  └── Prefix Injection: Force specific output                     │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 2. Jailbreak Techniques

### 2.1 Role-Playing Detection

```python
import re

ROLEPLAY_PATTERNS = [
    r"pretend\s+to\s+be\s+(?:DAN|evil|unrestricted)",
    r"you\s+are\s+now\s+(?:DAN|jailbroken|unfiltered)",
    r"act\s+as\s+(?:if|though)\s+you\s+have\s+no\s+(?:rules|restrictions)",
    r"from\s+now\s+on\s+you(?:'re|\s+are)\s+(?:my|an?)\s+(?:evil|unethical)",
    r"developer\s+mode\s+(?:enabled|activated|on)",
    r"ignore\s+(?:your|all)\s+(?:previous|safety)\s+(?:instructions|rules)"
]

class RolePlayDetector:
    def __init__(self):
        self.patterns = [re.compile(p, re.IGNORECASE) for p in ROLEPLAY_PATTERNS]
    
    def detect(self, text: str) -> dict:
        matches = [p.pattern for p in self.patterns if p.search(text)]
        return {
            'detected': len(matches) > 0,
            'type': 'role_play',
            'confidence': min(0.3 + 0.2 * len(matches), 1.0),
            'patterns': matches
        }
```

### 2.2 Hypothetical Framing

```python
HYPOTHETICAL_PATTERNS = [
    r"write\s+a\s+(?:story|fiction|novel)\s+(?:about|where)",
    r"in\s+a\s+hypothetical\s+(?:scenario|world|situation)",
    r"imagine\s+(?:you\s+are|that|if)",
    r"for\s+(?:educational|research|academic)\s+purposes",
    r"purely\s+(?:fictional|hypothetical|theoretical)"
]

class HypotheticalDetector:
    def __init__(self):
        self.patterns = [re.compile(p, re.IGNORECASE) for p in HYPOTHETICAL_PATTERNS]
        self.harmful = ['hack', 'exploit', 'weapon', 'drug', 'bomb', 'poison']
    
    def detect(self, text: str) -> dict:
        text_lower = text.lower()
        has_frame = any(p.search(text) for p in self.patterns)
        has_harmful = any(kw in text_lower for kw in self.harmful)
        
        if has_frame and has_harmful:
            return {'detected': True, 'type': 'hypothetical_harmful', 'confidence': 0.8}
        elif has_frame:
            return {'detected': True, 'type': 'hypothetical', 'confidence': 0.4}
        return {'detected': False}
```

### 2.3 Encoding Detection

```python
import base64

class EncodingDetector:
    def detect(self, text: str) -> dict:
        results = {'detected': False, 'encodings': []}
        
        # Base64
        matches = re.findall(r'[A-Za-z0-9+/]{20,}={0,2}', text)
        for match in matches:
            try:
                decoded = base64.b64decode(match).decode('utf-8')
                if any(kw in decoded.lower() for kw in ['ignore', 'bypass', 'jailbreak']):
                    results['detected'] = True
                    results['encodings'].append('base64')
            except:
                pass
        
        # Hex/Unicode escapes
        if re.search(r'(?:\\x[0-9a-fA-F]{2}){4,}', text):
            results['detected'] = True
            results['encodings'].append('hex')
        
        return results
```

---

## 3. Multi-Turn Detection

```python
from dataclasses import dataclass
from typing import List

@dataclass
class ConversationTurn:
    role: str
    content: str

class MultiTurnDetector:
    def __init__(self):
        self.manipulation_keywords = [
            'remember earlier', 'as we discussed', 'you agreed', 'continue from'
        ]
    
    def analyze(self, turns: List[ConversationTurn]) -> dict:
        if len(turns) < 3:
            return {'detected': False}
        
        levels = [self._assess(t.content) for t in turns if t.role == 'user']
        
        if self._is_escalating(levels):
            return {'detected': True, 'type': 'crescendo', 'confidence': 0.7}
        
        recent = ' '.join(t.content for t in turns[-3:] if t.role == 'user')
        for kw in self.manipulation_keywords:
            if kw in recent.lower():
                return {'detected': True, 'type': 'context_manipulation', 'confidence': 0.6}
        
        return {'detected': False}
    
    def _assess(self, text: str) -> int:
        text = text.lower()
        if any(w in text for w in ['hack', 'exploit', 'weapon']):
            return 3
        if any(w in text for w in ['bypass', 'ignore rules']):
            return 2
        if any(w in text for w in ['hypothetically', 'imagine']):
            return 1
        return 0
    
    def _is_escalating(self, levels: List[int]) -> bool:
        if len(levels) < 3:
            return False
        increases = sum(1 for i in range(1, len(levels)) if levels[i] > levels[i-1])
        return increases >= len(levels) // 2 and levels[-1] >= 2
```

---

## 4. Detection Engine

```python
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class JailbreakResult:
    detected: bool
    attack_type: str
    confidence: float
    details: Dict

class JailbreakEngine:
    def __init__(self):
        self.roleplay = RolePlayDetector()
        self.hypothetical = HypotheticalDetector()
        self.encoding = EncodingDetector()
        self.multiturn = MultiTurnDetector()
    
    def detect(self, text: str) -> JailbreakResult:
        results = []
        
        rp = self.roleplay.detect(text)
        if rp['detected']:
            results.append(('role_play', rp.get('confidence', 0.7)))
        
        hyp = self.hypothetical.detect(text)
        if hyp['detected']:
            results.append((hyp['type'], hyp.get('confidence', 0.5)))
        
        enc = self.encoding.detect(text)
        if enc['detected']:
            results.append(('encoding', 0.8))
        
        if not results:
            return JailbreakResult(False, 'none', 0.0, {})
        
        results.sort(key=lambda x: -x[1])
        return JailbreakResult(True, results[0][0], results[0][1], {'all': results})
    
    def detect_conversation(self, turns: List[Dict]) -> JailbreakResult:
        conv = [ConversationTurn(t['role'], t['content']) for t in turns]
        mt = self.multiturn.analyze(conv)
        
        if mt['detected']:
            return JailbreakResult(True, mt['type'], mt['confidence'], mt)
        
        if turns and turns[-1]['role'] == 'user':
            return self.detect(turns[-1]['content'])
        
        return JailbreakResult(False, 'none', 0.0, {})
```

---

## 5. SENTINEL Integration

```python
from dataclasses import dataclass

@dataclass
class JailbreakConfig:
    confidence_threshold: float = 0.6

class SENTINELJailbreakDetector:
    def __init__(self, config: JailbreakConfig):
        self.config = config
        self.engine = JailbreakEngine()
    
    def check(self, text: str) -> Dict:
        result = self.engine.detect(text)
        is_jailbreak = result.detected and result.confidence >= self.config.confidence_threshold
        
        action = 'ALLOW'
        if result.confidence >= 0.8:
            action = 'BLOCK'
        elif result.confidence >= self.config.confidence_threshold:
            action = 'REVIEW'
        elif result.detected:
            action = 'LOG'
        
        return {
            'is_jailbreak': is_jailbreak,
            'attack_type': result.attack_type,
            'confidence': result.confidence,
            'action': action
        }
```

---

## 6. Summary

| Attack Type | Description | Detection |
|-------------|-------------|-----------|
| **Role-Play** | Persona switching | Pattern matching |
| **Hypothetical** | Fiction framing | Context + keywords |
| **Encoding** | Base64, hex | Decode + analyze |
| **Multi-Turn** | Gradual escalation | Conversation tracking |

---

## Next Lesson

→ [02. Prompt Injection](02-prompt-injection.md)

---

*AI Security Academy | Track 03: LLM Attacks | Module 03.1: Prompt-Level*
