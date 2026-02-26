# Jailbreak Mitigation

> **Level:** Intermediate  
> **Time:** 50 minutes  
> **Track:** 03 — Attack Vectors  
> **Module:** 03.3 — Jailbreaking  
> **Version:** 2.0 (Production)

---

## Learning Objectives

Upon completing this lesson, you will be able to:

- [ ] Design multi-layer jailbreak defense systems
- [ ] Implement pattern-based and semantic detection
- [ ] Configure response strategies (block, flag, sanitize)
- [ ] Apply dynamic threshold adjustment
- [ ] Integrate jailbreak protection into SENTINEL

---

## 1. Defense Architecture

### 1.1 Multi-Layer Defense

```
┌────────────────────────────────────────────────────────────────────┐
│                    JAILBREAK DEFENSE LAYERS                        │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  INPUT                                                             │
│      ↓                                                             │
│  ╔═══════════════════════════════════════════════════════════════╗ │
│  ║  LAYER 1: PRE-PROCESSING                                     ║ │
│  ║  • Input normalization                                        ║ │
│  ║  • Unicode canonicalization                                   ║ │
│  ║  • Homoglyph detection                                        ║ │
│  ║  • Encoding detection                                         ║ │
│  ╚═══════════════════════════════════════════════════════════════╝ │
│      ↓                                                             │
│  ╔═══════════════════════════════════════════════════════════════╗ │
│  ║  LAYER 2: PATTERN DETECTION                                   ║ │
│  ║  • Roleplay signatures                                        ║ │
│  ║  • Instruction override patterns                              ║ │
│  ║  • Delimiter injection                                        ║ │
│  ║  • Known jailbreak templates                                  ║ │
│  ╚═══════════════════════════════════════════════════════════════╝ │
│      ↓                                                             │
│  ╔═══════════════════════════════════════════════════════════════╗ │
│  ║  LAYER 3: SEMANTIC ANALYSIS                                   ║ │
│  ║  • Intent classification                                      ║ │
│  ║  • Topic boundary validation                                  ║ │
│  ║  • Risk scoring                                               ║ │
│  ╚═══════════════════════════════════════════════════════════════╝ │
│      ↓                                                             │
│  ╔═══════════════════════════════════════════════════════════════╗ │
│  ║  LAYER 4: BEHAVIORAL ANALYSIS                                 ║ │
│  ║  • Multi-turn trajectory                                      ║ │
│  ║  • User history                                               ║ │
│  ║  • Session context                                            ║ │
│  ╚═══════════════════════════════════════════════════════════════╝ │
│      ↓                                                             │
│  DECISION: ALLOW / FLAG / BLOCK                                    │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 2. Pattern-Based Detection

### 2.1 Jailbreak Signature Database

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
    """Database of known jailbreak signatures."""
    
    SIGNATURES = [
        JailbreakSignature(
            id='JB001',
            name='DAN Attack',
            patterns=[
                r'\bDAN\b.*do\s+anything\s+now',
                r'pretend.*DAN',
                r'you\s+are\s+now\s+DAN',
            ],
            severity=0.9,
            category='roleplay',
            description='Do Anything Now persona attack'
        ),
        JailbreakSignature(
            id='JB002',
            name='Instruction Override',
            patterns=[
                r'ignore\s+(all\s+)?(previous|above)\s+instructions?',
                r'disregard\s+(your\s+)?rules?',
                r'forget\s+everything\s+(above|before)',
            ],
            severity=0.85,
            category='override',
            description='Direct instruction override attempt'
        ),
        JailbreakSignature(
            id='JB003',
            name='Developer Mode',
            patterns=[
                r'developer\s+mode\s+(enabled|activated|on)',
                r'enter\s+debug\s+mode',
                r'maintenance\s+mode\s+override',
            ],
            severity=0.8,
            category='authority',
            description='Fake developer/debug mode activation'
        ),
        JailbreakSignature(
            id='JB004',
            name='System Prompt Extraction',
            patterns=[
                r'(show|reveal|tell)\s+me\s+(your\s+)?system\s+prompt',
                r'what\s+(are|is)\s+your\s+(initial\s+)?instructions?',
                r'repeat\s+(all|everything)\s+(above|before)',
            ],
            severity=0.75,
            category='extraction',
            description='Attempt to extract system prompt'
        ),
        JailbreakSignature(
            id='JB005',
            name='Delimiter Injection',
            patterns=[
                r'\[/?SYSTEM\]',
                r'<\|im_(start|end)\|>',
                r'###\s*(SYSTEM|ADMIN)',
                r'```\s*system',
            ],
            severity=0.9,
            category='injection',
            description='Delimiter/format injection attempt'
        ),
        JailbreakSignature(
            id='JB006',
            name='Hypothetical Framing',
            patterns=[
                r'hypothetically\s+(speaking)?',
                r"for\s+(a|my)\s+(novel|story|book|class)",
                r'in\s+a\s+fictional\s+scenario',
                r'purely\s+for\s+(educational|research)\s+purposes?',
            ],
            severity=0.6,
            category='framing',
            description='Hypothetical/fictional framing to bypass safety'
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
        
        # Deduplicate by signature ID
        seen = set()
        unique_matches = []
        for m in matches:
            if m['signature_id'] not in seen:
                seen.add(m['signature_id'])
                unique_matches.append(m)
        
        return unique_matches
```

---

## 3. Semantic Analysis

### 3.1 Intent Classification

```python
from enum import Enum

class JailbreakIntent(Enum):
    BENIGN = "benign"
    ROLEPLAY = "roleplay"
    EXTRACTION = "extraction"
    OVERRIDE = "override"
    HARMFUL_REQUEST = "harmful_request"

class IntentClassifier:
    """Classify user intent for jailbreak detection."""
    
    # Keywords associated with different intents
    INTENT_KEYWORDS = {
        JailbreakIntent.ROLEPLAY: [
            'pretend', 'roleplay', 'act as', 'imagine', 'persona',
            'character', 'you are now'
        ],
        JailbreakIntent.EXTRACTION: [
            'system prompt', 'instructions', 'rules', 'reveal',
            'show me', 'what were you told'
        ],
        JailbreakIntent.OVERRIDE: [
            'ignore', 'disregard', 'forget', 'override', 'bypass',
            'disable', 'turn off'
        ],
        JailbreakIntent.HARMFUL_REQUEST: [
            'bomb', 'weapon', 'hack', 'kill', 'attack', 'illegal',
            'drugs', 'exploit', 'malware'
        ]
    }
    
    def classify(self, text: str) -> Dict:
        text_lower = text.lower()
        scores = {intent: 0.0 for intent in JailbreakIntent}
        
        for intent, keywords in self.INTENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    scores[intent] += 0.2
        
        # Normalize and find max
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

## 4. Response Strategies

### 4.1 Action Types

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
    """Configure response strategies based on severity."""
    
    def __init__(self, config: Dict = None):
        config = config or {}
        self.block_threshold = config.get('block_threshold', 0.8)
        self.flag_threshold = config.get('flag_threshold', 0.5)
        self.warn_threshold = config.get('warn_threshold', 0.3)
    
    def determine_action(self, risk_score: float, 
                         detections: List[Dict]) -> MitigationResponse:
        
        # Critical patterns always block
        critical_categories = {'injection', 'override'}
        has_critical = any(
            d.get('category') in critical_categories 
            for d in detections
        )
        
        if has_critical and risk_score > 0.6:
            return MitigationResponse(
                action=MitigationAction.BLOCK,
                warning_message="Request blocked for security reasons."
            )
        
        if risk_score >= self.block_threshold:
            return MitigationResponse(
                action=MitigationAction.BLOCK,
                warning_message="I cannot process this request."
            )
        
        if risk_score >= self.flag_threshold:
            return MitigationResponse(
                action=MitigationAction.FLAG,
                warning_message="This request has been flagged for review."
            )
        
        if risk_score >= self.warn_threshold:
            return MitigationResponse(
                action=MitigationAction.WARN,
                warning_message="Please ensure your request follows guidelines."
            )
        
        return MitigationResponse(action=MitigationAction.ALLOW)
```

---

## 5. SENTINEL Integration

```python
class SENTINELJailbreakGuard:
    """SENTINEL module for comprehensive jailbreak protection."""
    
    def __init__(self, config: Dict = None):
        config = config or {}
        
        self.signature_db = JailbreakSignatureDB()
        self.intent_classifier = IntentClassifier()
        self.response_strategy = ResponseStrategy(config)
        
        # Threshold configuration
        self.thresholds = {
            'pattern_weight': 0.4,
            'intent_weight': 0.3,
            'context_weight': 0.3
        }
    
    def analyze(self, text: str, context: Dict = None) -> Dict:
        """Analyze input for jailbreak attempts."""
        
        context = context or {}
        
        # Layer 1: Pattern matching
        pattern_matches = self.signature_db.match(text)
        pattern_score = self._calculate_pattern_score(pattern_matches)
        
        # Layer 2: Intent classification
        intent_result = self.intent_classifier.classify(text)
        intent_score = self._calculate_intent_score(intent_result)
        
        # Layer 3: Context analysis
        context_score = self._analyze_context(context)
        
        # Combined risk score
        risk_score = (
            pattern_score * self.thresholds['pattern_weight'] +
            intent_score * self.thresholds['intent_weight'] +
            context_score * self.thresholds['context_weight']
        )
        
        # Determine response
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
        """Analyze session context for risk indicators."""
        
        risk = 0.0
        
        # Previous jailbreak attempts in session
        previous_attempts = context.get('jailbreak_attempts', 0)
        if previous_attempts > 0:
            risk += min(previous_attempts * 0.2, 0.5)
        
        # Conversation trajectory
        if context.get('escalating', False):
            risk += 0.3
        
        return min(risk, 1.0)
```

---

## 6. Dynamic Threshold Adjustment

```python
class AdaptiveThresholdManager:
    """Dynamically adjust thresholds based on threat landscape."""
    
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
        
        # Cleanup old entries
        cutoff = datetime.utcnow() - timedelta(hours=1)
        self.attack_history = [
            a for a in self.attack_history if a['timestamp'] > cutoff
        ]
        
        self._adjust_threshold()
    
    def _adjust_threshold(self):
        if len(self.attack_history) < 5:
            return
        
        # Calculate attack rate
        attack_count = len(self.attack_history)
        
        # Increase sensitivity during attack surge
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

## 7. Summary

### Defense Layers

| Layer | Technique | Purpose |
|-------|-----------|---------|
| **Preprocessing** | Normalization | Canonicalize input |
| **Pattern** | Signature matching | Known attacks |
| **Semantic** | Intent classification | Unknown attacks |
| **Behavioral** | Trajectory analysis | Multi-turn attacks |

### Quick Checklist

```
□ Implement signature database
□ Add intent classification
□ Configure response strategies
□ Set appropriate thresholds
□ Enable dynamic adjustment
□ Log all detections
□ Monitor false positive rate
```

---

## Next Track

→ [Track 04: Prompt-Level Attacks](../04-prompt-level/README.md)

---

*AI Security Academy | Track 03: Attack Vectors | Jailbreaking*
