# Strange Math Core

> **Engines:** 8  
> **Description:** Advanced mathematical methods: sheaf theory, hyperbolic geometry, TDA

---

## 1. Sheaf Coherence Engine

**File:** [sheaf_coherence.py](file:///c:/AISecurity/src/brain/engines/sheaf_coherence.py)  
**LOC:** 580  
**Theoretical Base:** Sheaf theory, Čech cohomology

### Sources

| Source                 | Description                                                                      |
| ---------------------- | -------------------------------------------------------------------------------- |
| ESSLLI 2025            | Sheaf theory for unifying syntax, semantics, statistics                          |
| Hansen & Ghrist (2019) | [Toward a Spectral Theory of Cellular Sheaves](https://arxiv.org/abs/1808.01513) |
| Curry (2014)           | [Sheaves, Cosheaves and Applications](https://arxiv.org/abs/1303.3255)           |

### Key Concept

A **sheaf** on a topological space X is a functor that:

1. Assigns to each open set U ⊆ X data F(U) ("sections")
2. For V ⊆ U defines restriction maps ρ\_{U,V}: F(U) → F(V)
3. Satisfies the gluing axiom

**NLP Application:**

- Open sets = contexts (messages, dialogue turns)
- Sections = semantic embeddings
- Restriction maps = context projections
- Gluing axiom = semantic coherence

### Implementation: Čech Cohomology (Simplified)

```python
class CechCohomology:
    def compute_h1(self, sheaf: SheafStructure) -> int:
        """
        H¹ = number of gluing axiom violations.
        NOT actual cohomology! This is a heuristic.
        """
```

> [!WARNING]  
> We use "cohomology" as a metaphor for "incoherence detection".

---

## 2. Hyperbolic Geometry Engine

**File:** [hyperbolic_geometry.py](file:///c:/AISecurity/src/brain/engines/hyperbolic_geometry.py)  
**LOC:** 672  
**Theoretical Base:** Hyperbolic geometry, Poincaré model

### Sources

| Source                | Description                                                    |
| --------------------- | -------------------------------------------------------------- |
| Nickel & Kiela (2017) | [Poincaré Embeddings](https://arxiv.org/abs/1705.08039)        |
| Ganea et al. (2018)   | [Hyperbolic Neural Networks](https://arxiv.org/abs/1805.09112) |
| MERU (2023)           | Hyperbolic vision-language models                              |

### Key Concept

Poincaré space is the unit ball Bⁿ with metric:
$$ds^2 = \frac{4 \|dx\|^2}{(1 - \|x\|^2)^2}$$

**Security Application:**

- System prompt → ball center
- User messages → periphery
- "Admin" attempt = anomalous jump to center

### Key Operations

- Möbius addition
- Geodesic distance: $d(x,y) = (2/\sqrt{c}) \arctanh(\sqrt{c} \|−x \oplus y\|)$
- Fréchet mean (hyperbolic centroid)

---

## 3. TDA Enhanced Engine

**File:** [tda_enhanced.py](file:///c:/AISecurity/src/brain/engines/tda_enhanced.py)  
**LOC:** 795  
**Theoretical Base:** Persistent homology, Topological Data Analysis

### Sources

| Source              | Description                                                                              |
| ------------------- | ---------------------------------------------------------------------------------------- |
| GUDHI               | [gudhi.inria.fr](https://gudhi.inria.fr/) — TDA library                                  |
| Carlsson (2009)     | [Topology and Data](https://www.ams.org/journals/bull/2009-46-02/S0273-0979-09-01249-X/) |
| Otter et al. (2017) | [A Roadmap for Persistent Homology](https://arxiv.org/abs/1506.08903)                    |

### Key Concept

Persistent homology tracks topological structures (components, cycles, voids) across scales:

1. Build simplicial complex (Vietoris-Rips) from point cloud
2. Increase radius ε from 0 to ∞
3. Track birth/death of topological features
4. Obtain persistence diagram

**Betti Numbers:**

- β₀ = connected components
- β₁ = "holes" (independent cycles)
- β₂ = voids

### Features: Zigzag Persistence, Attention Topology, Topological Fingerprinting

---

## 4. Information Geometry Engine

**File:** [information_geometry.py](file:///c:/AISecurity/src/brain/engines/information_geometry.py)  
**LOC:** 412  
**Theoretical Base:** Statistical manifolds, Fisher-Rao metric

### Key Formula

Fisher-Rao distance for categorical distributions:
$$d_{FR}(p, q) = 2 \arccos\left(\sum_i \sqrt{p_i q_i}\right)$$

**Security Application:**

- Text → character distribution → manifold point
- "Normal" text near baseline (English/Russian)
- Attacks (Base64, code injection) far from baseline

---

## 5. Chaos Theory Engine

**File:** [chaos_theory.py](file:///c:/AISecurity/src/brain/engines/chaos_theory.py)  
**LOC:** 323  
**Theoretical Base:** Chaos theory, Lyapunov exponent

### Key Concept

Lyapunov exponent λ measures sensitivity to initial conditions:
$$\|\delta Z(t)\| \approx e^{\lambda t} \|\delta Z_0\|$$

- λ > 0: chaotic system (fuzzing bot)
- λ < 0: stable system (normal user)
- λ ≈ 0: "edge of chaos"

### Features: Phase space analysis, regime change detection

---

## 6. Category Theory Engine

**File:** [category_theory.py](file:///c:/AISecurity/src/brain/engines/category_theory.py)  
**LOC:** 444  
**Theoretical Base:** Category theory, functors

### Key Concept

Category = objects + morphisms (arrows between objects):

- **Objects** = dialogue states (context, trust level)
- **Morphisms** = prompts (state transformations)
- **Composition** = multi-turn attacks

**Safe transformations = natural transformations.**  
**Attacks = break naturality.**

### Compositional Attack Detection

```python
# Multi-step attacks: each step benign, but composition dangerous
if accumulated_risk >= 0.7:
    return "BLOCK: Accumulated composition exceeds threshold"
```

---

## 7. Homomorphic Encryption Engine

**File:** [homomorphic_engine.py](file:///c:/AISecurity/src/brain/engines/homomorphic_engine.py)  
**LOC:** 599  
**Theoretical Base:** Fully Homomorphic Encryption (FHE)

### Key Concept

FHE allows computations on encrypted data:
$$\text{Enc}(a) \oplus \text{Enc}(b) = \text{Enc}(a + b)$$
$$\text{Enc}(a) \otimes \text{Enc}(b) = \text{Enc}(a \cdot b)$$

**Application:**

- Client encrypts prompt
- SENTINEL analyzes **without seeing plaintext**
- Returns encrypted result

> [!CAUTION]  
> This is a **SIMULATION**, not real FHE! For production, use Microsoft SEAL / OpenFHE / TenSEAL.

---

## 8. Spectral Graph Engine

**File:** [spectral_graph.py](file:///c:/AISecurity/src/brain/engines/spectral_graph.py)  
**LOC:** 400  
**Theoretical Base:** Graph Laplacian, spectral clustering

### Key Features

- Laplacian eigenvalue analysis
- Spectral gap detection
- Community detection in conversation graphs

---

## General Expert Recommendations

### For Topologists/Geometers

1. Terms like "cohomology", "Betti numbers" are **metaphors**
2. Implementations are **heuristics** inspired by theory
3. We welcome PRs with more correct formulations

### For ML Engineers

1. Embeddings: sentence-transformers / BERT (plug-and-play)
2. All engines run on CPU, GPU optional

### For Security Researchers

1. This is **defense-in-depth**, not silver bullet
2. Adversarial attacks on detectors themselves are not studied
3. Threat model: jailbreaks, not model extraction

---

## References

- [Curry (2014) — Sheaves for CS](https://arxiv.org/abs/1303.3255)
- [Hansen & Ghrist (2019)](https://arxiv.org/abs/1808.01513)
- [Nickel & Kiela (2017)](https://arxiv.org/abs/1705.08039)
- [Hyperbolic Neural Networks](https://arxiv.org/abs/1805.09112)
- [GUDHI Tutorial](https://gudhi.inria.fr/python/latest/tutorials.html)
- [Carlsson — Topology and Data](https://www.ams.org/journals/bull/2009-46-02/S0273-0979-09-01249-X/)
