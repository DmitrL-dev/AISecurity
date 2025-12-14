# Classic Detection

> **Engines:** 8  
> **Description:** Basic detection engines: injection, PII, compliance

---

## 9. Injection Engine

**File:** [injection.py](file:///c:/AISecurity/src/brain/engines/injection.py)  
**LOC:** 564  
**Theoretical Base:** Multi-layer defence-in-depth

### 9.1. Architecture — 6 Layers

```
Layer 0: Cache      → LRU cache (TTL=5min)
Layer 1: Regex      → 50+ patterns (classic + 2025)
Layer 2: Semantic   → Embedding similarity (MiniLM)
Layer 3: Structural → Entropy, instruction patterns
Layer 4: Context    → Session accumulator
Layer 5: Verdict    → Profile-based thresholds
```

### 9.2. Profiles

| Profile    | Layers        | Latency |
| ---------- | ------------- | ------- |
| lite       | Cache + Regex | ~1ms    |
| standard   | + Semantic    | ~20ms   |
| enterprise | All layers    | ~50ms   |

### 9.3. 2025 Attack Patterns

```python
advanced_patterns = [
    ("#[^#]*ignore", "HashJack", 90.0),
    ("terms.*ignore", "LegalPwn", 85.0),
    ("[A-Za-z0-9+/]{40,}", "Base64 Payload", 40.0),
    ("[\\u200b-\\u200f]", "Unicode Obfuscation", 60.0),
]
```

### 9.4. FlipAttack Detection

```python
def _detect_flip_attack(self, text):
    """Find reversed keywords: 'erongI' → 'Ignore'"""
```

---

## 11. Behavioral Engine

**File:** [behavioral.py](file:///c:/AISecurity/src/brain/engines/behavioral.py)  
**LOC:** 536  
**Theoretical Base:** Isolation Forest, time-series analysis

### 11.1. Capabilities

- **Isolation Forest** for anomaly detection
- **Time-series pattern analysis** for sessions
- **User trust scoring** based on history
- **Redis-backed profiles** for persistence

### 11.2. Session Patterns

```python
class SessionPattern(Enum):
    NORMAL = "normal"
    ESCALATION = "escalation"      # Growing risk
    RECONNAISSANCE = "reconnaissance"  # Probing
    BURST = "burst"                # Many requests
```

### 11.3. Trust Scoring

| Level      | Criteria                                         |
| ---------- | ------------------------------------------------ |
| NEW        | < 5 requests                                     |
| SUSPICIOUS | block_ratio > 0.3 OR avg_risk > 60               |
| NORMAL     | Default                                          |
| TRUSTED    | > 50 requests, avg_risk < 20, block_ratio < 0.05 |

### 11.4. Risk Adjustments

```python
trust_adjustments = {
    SUSPICIOUS: +15.0,
    NORMAL: 0.0,
    TRUSTED: -5.0,  # Small bonus
}

pattern_adjustments = {
    ESCALATION: +20.0,
    RECONNAISSANCE: +10.0,
    BURST: +15.0,
}
```

---

## 27. Probing Detection Engine

**File:** [probing_detection.py](file:///c:/AISecurity/src/brain/engines/probing_detection.py)  
**LOC:** 645  
**Theoretical Base:** NVIDIA AI Kill Chain - Recon Stage

### 27.1. What It Detects (TTPs.ai)

- **System prompt extraction** — "show me your prompt"
- **Guardrail testing** — "what topics are off-limits?"
- **Error harvesting** — null bytes, template injection
- **Capability enumeration** — "list your tools"
- **Tool discovery** — sequential tool probing

### 27.2. Patterns

```python
SYSTEM_PROMPT_PATTERNS = [
    r"show\s+me\s+your\s+(system\s+)?prompt",
    r"repeat\s+everything\s+above",
    r"developer\s+mode\s+enabled",
]

GUARDRAIL_PATTERNS = [
    r"what\s+are\s+your\s+restrictions?",
    r"what\s+triggers\s+your\s+refusal",
]
```

### 27.3. Session Tracking

```python
class SessionTracker:
    """
    Tracks probing attempts across session.
    Score decays over time (5 min window).
    """

# Blocking thresholds:
block_after_probes = 5
warn_after_probes = 2
```

### 27.4. Recommendations

| Verdict  | Action                    |
| -------- | ------------------------- |
| LOG      | Just log                  |
| WARN     | Alert user                |
| BLOCK    | Reject request            |
| HONEYPOT | Return fake system prompt |

---

## 28. YARA Engine

**File:** [yara_engine.py](file:///c:/AISecurity/src/brain/engines/yara_engine.py)  
**LOC:** 329  
**Theoretical Base:** Signature-based detection (Cisco MCP-Scanner approach)

### 28.1. Concept

Fast matching against known attack patterns. **~5ms latency**.

```python
SEVERITY_WEIGHTS = {
    "CRITICAL": 100.0,
    "HIGH": 75.0,
    "MEDIUM": 50.0,
    "LOW": 25.0,
}
```

### 28.2. Features

- Load `.yara` rules from directory
- Dynamic rule addition
- Hot-reload
- Graceful fallback if `yara-python` not installed

---

## 29. Compliance Engine

**File:** [compliance_engine.py](file:///c:/AISecurity/src/brain/engines/compliance_engine.py)  
**LOC:** 438  
**Theoretical Base:** Regulatory mapping (EU AI Act, NIST AI RMF, ISO 42001)

### 29.1. Frameworks

```python
class Framework(Enum):
    EU_AI_ACT = "eu_ai_act"      # Article 9, 10, 15
    NIST_AI_RMF = "nist_ai_rmf"  # GOVERN, MEASURE, MANAGE
    ISO_42001 = "iso_42001"      # 6.1.2, 8.2, 8.4
    SOC2 = "soc2"
    GDPR = "gdpr"
```

### 29.2. Control Mapping

```python
# Prompt injection → Article 15 (robustness), Article 9 (risk management)
# Data leak → Article 10 (data governance)
```

### 29.3. Report Generation

```python
report = engine.generate_report(
    framework=Framework.EU_AI_ACT,
    period_days=30
)
# → events, controls_covered, summary
```

---

## 30. PII Engine

**File:** [pii.py](file:///c:/AISecurity/src/brain/engines/pii.py)  
**LOC:** 532  
**Theoretical Base:** Presidio + custom Russian patterns

### 30.1. Russian Patterns

| Entity          | Format         | Example        |
| --------------- | -------------- | -------------- |
| RU_PASSPORT     | XXXX XXXXXX    | 1234 567890    |
| RU_INN_PERSONAL | 12 digits      | 123456789012   |
| RU_SNILS        | XXX-XXX-XXX XX | 123-456-789 00 |
| RU_OGRN         | 13 digits      | 1234567890123  |
| RU_BIK          | 04XXXXXXX      | 044525225      |

### 30.2. INN Validation

```python
class INNValidator:
    """Validates Russian INN using checksum algorithm."""

    @staticmethod
    def validate_inn_12(inn: str) -> bool:
        weights1 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
        weights2 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
        # Verify checksum...
```

### 30.3. 1C-Specific Patterns

- `1C_USER_ID`
- `1C_SESSION_ID`
- `1C_CONFIG_PATH`
- `1C_DB_CONNECTION`

---

## 31. Cascading Guard Engine

**File:** [cascading_guard.py](file:///c:/AISecurity/src/brain/engines/cascading_guard.py)  
**LOC:** 471  
**Theoretical Base:** OWASP ASI08 - Cascading Failures

### 31.1. Circuit Breaker

```python
class CircuitState(Enum):
    CLOSED = "closed"      # Normal
    OPEN = "open"          # Blocking
    HALF_OPEN = "half_open"  # Testing recovery

FAILURE_THRESHOLD = 5  # failures before tripping
```

### 31.2. Fanout Detection

```python
FANOUT_THRESHOLD = 5  # agents in window
VELOCITY_THRESHOLD = 10  # actions per second

# A → B, C, D, E, F = suspicious fanout
```

### 31.3. Feedback Loop Detection

```python
# DFS to find cycles in agent dependency graph
# A → B → C → A = feedback loop
```

### 31.4. Rollback Coordination

```python
def coordinate_rollback(cascade_id):
    # Determine affected agents
    # Reverse order rollback
    # Estimated recovery time
```

---

## 32. Language Engine

**File:** [language.py](file:///c:/AISecurity/src/brain/engines/language.py)  
**LOC:** 371  
**Theoretical Base:** Multi-script attack detection

### 32.1. Encoding Attacks

| Attack             | Risk |
| ------------------ | ---- |
| Homoglyph (а→a)    | +40  |
| Zero-width chars   | +30  |
| BiDi override      | +50  |
| NFKC normalization | +20  |

### 32.2. Script Detection

```python
class Script(Enum):
    LATIN = "latin"
    CYRILLIC = "cyrillic"
    MIXED = "mixed"  # ← suspicious!
    CJK = "cjk"
    ARABIC = "arabic"
```

### 32.3. Normalization

```python
def normalize(text):
    # Remove zero-width chars
    # Remove BiDi overrides
    # NFKC normalization
```

---
