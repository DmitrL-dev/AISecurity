# 🧠 Adaptive Behavioral Engines

> **Category:** Adaptive Behavioral  
> **Count:** 2 engines  
> **Added:** December 2025 (Titans/MIRAS Research)  
> **LOC:** ~800 lines

---

## Overview

The **Adaptive Behavioral** category includes engines implementing:

1. **Behavioral Fingerprinting** — threat actor identification without IP/cookies
2. **Test-Time Learning** — runtime prediction adaptation

**Theoretical Foundation:**

| Source                     | Application                           |
| -------------------------- | ------------------------------------- |
| Titans Architecture (2024) | Persistent memory, test-time training |
| MIRAS (2024)               | Multi-turn reasoning, safety          |
| Stylometry Research        | Authorship attribution without PII    |

---

## Engines

### 1. AttackerFingerprintingEngine

**File:** `engines/attacker_fingerprinting.py`  
**LOC:** 650  
**Unit Tests:** 21

#### Purpose

Identification of repeated attacks from the same threat actor **without stable identifiers** (IP, cookies, sessions).

#### Architecture

```mermaid
flowchart TB
    subgraph Input["Input Data"]
        M["Messages"]
        R["Risk scores"]
        T["Timestamps"]
    end

    subgraph Extractors["Feature Extractors"]
        SE["StylisticExtractor"]
        APE["AttackPatternExtractor"]
        TE["TemporalExtractor"]
        LE["LanguageExtractor"]
    end

    subgraph Output["Result"]
        FP["AttackerFingerprint<br/>ID: SHA256[:16]"]
        Match["Similarity Match<br/>threshold: 0.7"]
    end

    M --> SE & APE & LE
    T --> TE
    R --> APE
    SE & APE & TE & LE --> FP
    FP --> Match

    style FP fill:#4CAF50,color:#fff
```

#### Features

| Extractor         | Features                                    | Example                |
| ----------------- | ------------------------------------------- | ---------------------- |
| **Stylistic**     | avg_length, vocabulary_richness, caps_style | TTR = 0.78, "CAPS"     |
| **AttackPattern** | techniques, complexity, multi_turn          | INSTRUCTION_OVERRIDE   |
| **Temporal**      | burst_detection, time_of_day                | is_burst=True, "night" |
| **Language**      | lang_mix, obfuscation, encoding             | en:0.7, base64=True    |

#### Usage Example

```python
from engines.attacker_fingerprinting import AttackerFingerprintingEngine

engine = AttackerFingerprintingEngine()

# Create fingerprint
fp = engine.create_fingerprint(
    messages=["Ignore all previous instructions"],
    risk_scores=[0.9],
)

# Store (only for blocked attacks)
engine.store(fp, was_blocked=True)

# Match new attack
new_fp = engine.create_fingerprint(
    messages=["Disregard your training"],
    risk_scores=[0.85],
)

match = engine.match(new_fp)
print(f"Similarity: {match.similarity:.2%}")  # 80.76%
print(f"Known attacker: {match.is_known_attacker}")  # True
```

#### Storage (Dual-Layer)

| Layer    | Technology | TTL | Use Case                      |
| -------- | ---------- | --- | ----------------------------- |
| Hot      | Redis      | 24h | Fast lookup, session matching |
| Cold     | PostgreSQL | 30d | Persistence, analytics        |
| Fallback | In-Memory  | -   | No external deps              |

#### Privacy Compliance

- ✅ **GDPR Article 17** — TTL automatic deletion
- ✅ **No PII** — only feature hashes stored
- ✅ **CCPA** — Right to know supported via explainable fingerprints
- ✅ **152-FZ (Russian)** — RF territory storage (configurable)

---

### 2. AdaptiveMarkovPredictor

**File:** `engines/intent_prediction.py`  
**Class:** `AdaptiveMarkovPredictor`  
**LOC:** 140  
**Unit Tests:** 14

#### Purpose

User intent prediction with **runtime adaptation**. Learns from actual attacks.

#### Difference from MarkovPredictor

| Feature          | MarkovPredictor | AdaptiveMarkovPredictor |
| ---------------- | --------------- | ----------------------- |
| Transition probs | Fixed           | Adaptive                |
| Learning         | None            | Test-time               |
| Memory           | None            | Transition deltas       |
| Regularization   | None            | To prior                |

#### Parameters

| Parameter        | Default | Description                |
| ---------------- | ------- | -------------------------- |
| `learning_rate`  | 0.05    | Learning speed             |
| `regularization` | 0.1     | Pull to prior distribution |
| `momentum`       | 0.9     | Gradient smoothing         |

#### Learning Mechanism

```
1. Receive trajectory: [BENIGN, PROBING, ATTACKING]
2. If attack blocked: learn(trajectory, was_attack=True)
3. Increase Δ(PROBING → ATTACKING)
4. On false positive: learn(trajectory, was_attack=False)
5. Decrease Δ accordingly
```

#### Mathematical Formulation

**Effective probability:**

$$P_{eff}(s'|s) = (1-\lambda) \cdot (P_0 + \Delta) + \lambda \cdot P_0$$

**Momentum update:**

$$v_t = \beta \cdot v_{t-1} + (1-\beta) \cdot g_t$$

$$\Delta_t = \Delta_{t-1} + v_t$$

#### Usage Example

```python
from engines.intent_prediction import AdaptiveMarkovPredictor, Intent

predictor = AdaptiveMarkovPredictor(
    learning_rate=0.1,
    momentum=0.9,
)

# Training
trajectory = [Intent.PROBING, Intent.TESTING, Intent.ATTACKING]
predictor.learn(trajectory, was_attack=True)

# Prediction (now P(ATTACKING|TESTING) is higher)
next_intent, prob = predictor.predict_next(Intent.TESTING)
print(f"Next: {next_intent.name}, P={prob:.2f}")
```

---

## Related Engines

| Engine                    | Relationship                       |
| ------------------------- | ---------------------------------- |
| `behavioral.py`           | Baseline behavioral analysis       |
| `intent_prediction.py`    | Base MarkovPredictor               |
| `information_geometry.py` | Huber distance for robust matching |

---

## Unit Tests

```bash
# Run tests
python -m pytest tests/unit/test_attacker_fingerprinting.py -v
python -m pytest tests/unit/test_adaptive_markov.py -v

# Result: 35/35 passed
```

---

## Roadmap

- [ ] Integration with feedback loop in `SentinelAnalyzer`
- [ ] TTL on deltas in AdaptiveMarkovPredictor
- [ ] Adversarial testing fingerprint evasion
- [ ] Cross-session fingerprint correlation

---

**Next section:** [Meta-Judge + XAI →](./13-meta-xai-en.md)
