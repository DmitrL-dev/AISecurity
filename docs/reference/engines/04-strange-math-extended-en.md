# Strange Math Extended

> **Engines:** 18  
> **Description:** Extended mathematical engines: causal models, gradients, formal verification

---

## 34. Gradient Detection Engine

**File:** [gradient_detection.py](file:///c:/AISecurity/src/brain/engines/gradient_detection.py)  
**LOC:** 293  
**Theoretical Base:** Adversarial gradient analysis

### Anomaly Types

```python
class GradientAnomalyType(Enum):
    HIGH_NORM = "high_norm"
    HIGH_VARIANCE = "high_variance"
    SPARSE_GRADIENTS = "sparse_gradients"
    GRADIENT_MASKING = "gradient_masking"
    PERTURBATION_PATTERN = "perturbation_pattern"
```

### Detection: Cyrillic lookalikes, zero-width chars, fullwidth chars, combining diacritical marks, repeated chars

---

## 35. Geometric Kernel (TDA)

**File:** [geometric.py](file:///c:/AISecurity/src/brain/engines/geometric.py)  
**LOC:** 451  
**Theoretical Base:** Persistent homology (H0, H1, H2)

### Layers

1. **Embedding** — sentence-transformers
2. **Homology** — ripser persistent homology
3. **Landscape** — Persistence landscapes
4. **Adaptive** — Dynamic thresholds (μ + 2σ)
5. **Anomaly** — Multi-signal fusion

### Betti Numbers

- β₀: Connected components
- β₁: Loops/cycles
- β₂: Voids/cavities

---

## 36. Formal Verification Engine

**File:** [formal_verification.py](file:///c:/AISecurity/src/brain/engines/formal_verification.py)  
**LOC:** 522  
**Theoretical Base:** Certified robustness (IBP, CROWN)

### Verification Methods

- Interval Bound Propagation (IBP)
- CROWN / BETA-CROWN
- MILP
- Abstract Interpretation

---

## 45. Causal Attack Model

**File:** [causal_attack_model.py](file:///c:/AISecurity/src/brain/engines/causal_attack_model.py)  
**LOC:** 695  
**Theoretical Base:** Causal inference for security

> "Model **WHY** attacks work, not just WHAT they look like."

### Causal Mechanisms

- Instruction-data confusion
- Role boundary ambiguity
- Context window limits
- Trust inheritance
- Encoding blindness

---

## 48. Adversarial Resistance Module

**File:** [adversarial_resistance.py](file:///c:/AISecurity/src/brain/engines/adversarial_resistance.py)  
**LOC:** 294  
**Theoretical Base:** Defense against algorithm-aware attackers

### Features

- **Randomized Thresholds** — Attacker can't optimize for exact value
- **Secret Salts** — Primary + rotating salt with HMAC
- **Timing-Safe Checks** — All calls take ~50ms

---

## 49. APE Signatures Database

**File:** [ape_signatures.py](file:///c:/AISecurity/src/brain/engines/ape_signatures.py)  
**LOC:** 371  
**Theoretical Base:** HiddenLayer APE Taxonomy

### Tactics

- Context Manipulation
- Instruction Override
- Role Playing
- Payload Encoding
- Refusal Suppression
- Multi-Turn Attack

---

## 53. Threat Landscape Modeler

**File:** [threat_landscape_modeler.py](file:///c:/AISecurity/src/brain/engines/threat_landscape_modeler.py)  
**LOC:** 373  
**Theoretical Base:** Attack surface mapping

> "Find unexploited attack surface **before** attackers do."

### Surface Types: Input Channel, Trust Boundary, State Storage, External Integration

---

## 74–85. Additional Engines

| #   | Engine                     | LOC | Key Feature             |
| --- | -------------------------- | --- | ----------------------- |
| 74  | Cross-Modal Consistency    | 482 | CLIP-style alignment    |
| 75  | Adversarial Image Detector | 610 | FFT analysis            |
| 76  | Math Oracle                | 807 | DeepSeek integration    |
| 77  | Institutional AI           | 421 | Separation of powers    |
| 78  | Hyperbolic Geometry        | 672 | Poincaré ball model     |
| 79  | Information Theory         | 277 | Shannon entropy, KL     |
| 81  | Homomorphic Encryption     | 599 | GPU-accelerated FHE     |
| 82  | Formal Invariants          | 424 | Mathematical guarantees |
| 83  | Information Geometry       | 412 | Fisher-Rao metric       |
| 84  | Differential Geometry      | 300 | Curvature analysis      |
| 85  | Category Theory            | 444 | Morphisms, naturality   |

---

## General Expert Recommendations

### For Topologists/Geometers

- Terms like "cohomology", "Betti numbers" are **metaphors**
- Implementations are **heuristics** inspired by theory

### For ML Engineers

- Embeddings: sentence-transformers / BERT (plug-and-play)
- All engines run on CPU, GPU optional

### For Security Researchers

- This is **defense-in-depth**, not silver bullet
- Adversarial attacks on the detectors themselves are not studied

---

## References

- [Curry (2014) — Sheaves for CS](https://arxiv.org/abs/1303.3255)
- [Nickel & Kiela (2017) — Poincaré Embeddings](https://arxiv.org/abs/1705.08039)
- [GUDHI Tutorial](https://gudhi.inria.fr/python/latest/tutorials.html)
- [Amari & Nagaoka — Methods of Information Geometry](https://www.ams.org/books/mmono/191/)
- [Microsoft SEAL](https://github.com/microsoft/SEAL)
