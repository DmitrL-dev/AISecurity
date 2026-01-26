# SENTINEL Engine Architecture

> **Óðîâåíü:** Ñðåäíèé  
> **Âðåìÿ:** 55 ìèíóò  
> **Òðåê:** 03 — Defense Techniques  
> **Ìîäóëü:** 03.2 — SENTINEL Integration  
> **Âåðñèÿ:** 1.0

---

## Öåëè îáó÷åíèÿ

- [ ] Ïîíÿòü àðõèòåêòóðó SENTINEL Brain
- [ ] Îïèñàòü êëþ÷åâûå engines è èõ âçàèìîäåéñòâèå
- [ ] Èíòåãðèðîâàòü engines â ïðèëîæåíèå

---

## 1. SENTINEL Architecture

### 1.1 High-Level Overview

```
---------------------------------------------------------------------¬
¦                      SENTINEL BRAIN                                 ¦
+--------------------------------------------------------------------+
¦                                                                    ¦
¦  ---------------¬  ---------------¬  ---------------¬             ¦
¦  ¦   INPUT      ¦  ¦    CORE      ¦  ¦   OUTPUT     ¦             ¦
¦  ¦   ENGINES    ¦> ¦   ENGINES    ¦> ¦   ENGINES    ¦             ¦
¦  L---------------  L---------------  L---------------             ¦
¦         ¦                 ¦                 ¦                      ¦
¦         ¡                 ¡                 ¡                      ¦
¦  ---------------------------------------------------¬             ¦
¦  ¦              ORCHESTRATOR                         ¦             ¦
¦  ¦   Coordinates engines, manages flow, logging      ¦             ¦
¦  L---------------------------------------------------             ¦
¦                                                                    ¦
L---------------------------------------------------------------------
```

### 1.2 Engine Categories

```
SENTINEL Engines:
+-- Input Engines
¦   +-- PromptInjectionDetector
¦   +-- JailbreakClassifier
¦   +-- InputSanitizer
¦   L-- EncodingDetector
+-- Core Engines
¦   +-- TrustBoundaryAnalyzer
¦   +-- ContextAnalyzer
¦   L-- SemanticRouter
L-- Output Engines
    +-- SafetyClassifier
    +-- PIIRedactor
    +-- HallucinationDetector
    L-- ConsistencyChecker
```

---

## 2. Input Engines

### 2.1 PromptInjectionDetector

```python
from sentinel import scan  # Public API

class PromptInjectionDetector:
    """
    Detects prompt injection attempts in user input
    
    Methods:
    - analyze(text) -> AnalysisResult
    - get_confidence() -> float
    - get_attack_type() -> str
    """
    
    def __init__(self, config: dict = None):
        self.patterns = self._load_patterns()
        self.ml_model = self._load_model()
    
    def analyze(self, text: str) -> dict:
        # Pattern matching
        pattern_result = self._check_patterns(text)
        
        # ML classification
        ml_result = self._ml_classify(text)
        
        # Combine signals
        confidence = self._ensemble(pattern_result, ml_result)
        
        return {
            "is_injection": confidence > 0.7,
            "confidence": confidence,
            "attack_type": self._determine_type(pattern_result, ml_result),
            "evidence": self._gather_evidence(text)
        }
```

### 2.2 JailbreakClassifier

```python
from sentinel import scan  # Public API

class JailbreakClassifier:
    """
    Classifies jailbreak attempts by type
    
    Types:
    - persona_based (DAN, Evil Confidant)
    - encoding_based (Base64, ROT13)
    - logic_based (hypothetical, academic)
    - multi_turn (gradual escalation)
    """
    
    def classify(self, text: str, history: list = None) -> dict:
        # Check for persona patterns
        persona = self._check_persona(text)
        
        # Check for encoding
        encoding = self._check_encoding(text)
        
        # Check logic patterns
        logic = self._check_logic(text)
        
        # Check multi-turn patterns
        if history:
            multi_turn = self._check_escalation(history)
        
        return {
            "jailbreak_type": self._determine_type(persona, encoding, logic),
            "confidence": max(persona, encoding, logic),
            "recommendations": self._get_recommendations()
        }
```

---

## 3. Core Engines

### 3.1 TrustBoundaryAnalyzer

```python
from sentinel import scan  # Public API

class TrustBoundaryAnalyzer:
    """
    Analyzes trust boundaries between system and user content
    
    Detects attempts to:
    - Modify system behavior
    - Inject system-level instructions
    - Cross privilege boundaries
    """
    
    def analyze(self, 
               system_prompt: str,
               user_input: str,
               retrieved_content: list = None) -> dict:
        
        # Check if user tries to modify system
        boundary_violation = self._check_boundary_crossing(
            system_prompt, user_input
        )
        
        # Check retrieved content for injection
        if retrieved_content:
            rag_injection = self._check_rag_content(retrieved_content)
        
        return {
            "boundary_intact": not boundary_violation,
            "violations": self._list_violations(),
            "risk_level": self._calculate_risk()
        }
```

### 3.2 ContextAnalyzer

```python
from sentinel import scan  # Public API

class ContextAnalyzer:
    """
    Analyzes context for security implications
    
    Features:
    - Context length monitoring
    - Attention dilution detection
    - System prompt integrity
    """
    
    def analyze(self,
               system_prompt: str,
               messages: list,
               max_context: int = 4096) -> dict:
        
        total_tokens = self._count_tokens(messages)
        
        # Check for attention dilution
        dilution_risk = self._check_dilution(
            system_prompt, messages, total_tokens
        )
        
        return {
            "total_tokens": total_tokens,
            "context_usage": total_tokens / max_context,
            "dilution_risk": dilution_risk,
            "recommendations": self._get_recommendations()
        }
```

---

## 4. Output Engines

### 4.1 SafetyClassifier

```python
from sentinel import scan  # Public API

class SafetyClassifier:
    """
    Classifies output safety across multiple dimensions
    
    Dimensions:
    - toxicity
    - harm
    - bias
    - misinformation
    """
    
    def classify(self, response: str) -> dict:
        dimensions = {
            "toxicity": self._check_toxicity(response),
            "harm": self._check_harm(response),
            "bias": self._check_bias(response),
            "misinformation": self._check_misinfo(response)
        }
        
        overall_safe = all(d["safe"] for d in dimensions.values())
        
        return {
            "is_safe": overall_safe,
            "dimensions": dimensions,
            "action": "allow" if overall_safe else "block"
        }
```

### 4.2 HallucinationDetector

```python
from sentinel import scan  # Public API

class HallucinationDetector:
    """
    Detects hallucinations in LLM output
    
    Methods:
    - Factual consistency check
    - Source attribution
    - Confidence calibration
    """
    
    def detect(self, 
              response: str,
              sources: list = None,
              context: str = None) -> dict:
        
        # Check factual claims
        claims = self._extract_claims(response)
        
        # Verify against sources
        if sources:
            verified = self._verify_against_sources(claims, sources)
        
        # Check internal consistency
        consistency = self._check_consistency(response, context)
        
        return {
            "hallucination_risk": 1 - consistency,
            "unverified_claims": len(claims) - len(verified),
            "recommendations": self._get_recommendations()
        }
```

---

## 5. Orchestrator

### 5.1 Engine Orchestration

```python
from sentinel.brain import Orchestrator

class SENTINELOrchestrator:
    """
    Orchestrates all engines in unified pipeline
    """
    
    def __init__(self):
        # Input engines
        self.injection_detector = PromptInjectionDetector()
        self.jailbreak_classifier = JailbreakClassifier()
        self.input_sanitizer = InputSanitizer()
        
        # Core engines
        self.boundary_analyzer = TrustBoundaryAnalyzer()
        self.context_analyzer = ContextAnalyzer()
        
        # Output engines
        self.safety_classifier = SafetyClassifier()
        self.hallucination_detector = HallucinationDetector()
    
    def process_request(self,
                       system_prompt: str,
                       user_input: str,
                       llm_fn) -> dict:
        
        # Phase 1: Input analysis
        input_result = self._process_input(user_input)
        if input_result["blocked"]:
            return {"response": input_result["fallback"]}
        
        # Phase 2: Context analysis
        context_result = self._analyze_context(system_prompt, user_input)
        
        # Phase 3: Generate response
        response = llm_fn(system_prompt, input_result["sanitized"])
        
        # Phase 4: Output analysis
        output_result = self._process_output(response)
        
        return {
            "response": output_result["final_response"],
            "metadata": {
                "input_analysis": input_result,
                "context_analysis": context_result,
                "output_analysis": output_result
            }
        }
```

---

## 6. Ðåçþìå

1. **Architecture:** Input > Core > Output engines
2. **Input engines:** Injection, jailbreak detection
3. **Core engines:** Boundary, context analysis
4. **Output engines:** Safety, hallucination
5. **Orchestrator:** Unified pipeline coordination

---

## Ñëåäóþùèé óðîê

> [02. Practical Integration](02-practical-integration.md)

---

*AI Security Academy | Track 03: Defense Techniques | Module 03.2: SENTINEL Integration*
