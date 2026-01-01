# 🔬 SENTINEL Engine Deep-Dive Reference

> **Total Engines:** 200  
> **Total LOC Analyzed:** ~81,000  
> **Unit Tests:** 1,047+ tests  
> **Benchmark Suite:** 1,815 samples (3 HF datasets)  
> **Hybrid Detector Recall:** 85.1% | Precision: 84.4% | F1: 84.7%  
> **Coverage:** OWASP LLM Top 10 + Agentic AI Top 10 (ASI 2026)
> **Version:** Dragon v4.0 (January 2026)

---

## 🆕 What's New (December 2025)

| Feature                        | Description                              |
| ------------------------------ | ---------------------------------------- |
| **GUDHI Integration**          | Precise TDA with Rips/Alpha complex      |
| **Hyperbolic Detector**        | Poincaré ball attack detection           |
| **Voice Jailbreak**            | ASI10 phonetic obfuscation detection     |
| **α-Divergence**               | Full divergence family in Info Geometry  |
| **Attacker Fingerprinting** 🆕 | IP-less threat actor identification      |
| **Adaptive Markov** 🆕         | Test-time learning for intent prediction |
| **Huber Distance** 🆕          | Outlier-resistant similarity metrics     |
| **OpenTelemetry**              | Production observability                 |
| **Rate Limiting**              | Token bucket, adaptive limits            |
| **Health Probes**              | Kubernetes-ready liveness/readiness      |

---

## Disclaimer

> [!IMPORTANT]
> This documentation describes the **engineering adaptation** of mathematical concepts for practical LLM security tasks. We use mathematics as **inspiration**, not implementing it strictly by textbooks.
>
> Where theory diverges from implementation — it's explicitly noted.

---

## Quick Navigation

| #   | Category               | Engines | File                                                           |
| --- | ---------------------- | ------- | -------------------------------------------------------------- |
| 1   | Classic Detection      | 8       | [01-classic-detection.md](./01-classic-detection.md)           |
| 2   | NLP / LLM Guard        | 5       | [02-nlp-llm-guard.md](./02-nlp-llm-guard.md)                   |
| 3   | Strange Math Core      | 8       | [03-strange-math-core.md](./03-strange-math-core.md)           |
| 4   | Strange Math Extended  | 8       | [04-strange-math-extended.md](./04-strange-math-extended.md)   |
| 5   | VLM Protection         | 3       | [05-vlm-protection.md](./05-vlm-protection.md)                 |
| 6   | TTPs.ai Defense        | 10      | [06-ttps-ai-defense.md](./06-ttps-ai-defense.md)               |
| 7   | Advanced 2025          | 6       | [07-advanced-2025.md](./07-advanced-2025.md)                   |
| 8   | Protocol Security      | 4       | [08-protocol-security.md](./08-protocol-security.md)           |
| 9   | Proactive Engines      | 10      | [09-proactive-engines.md](./09-proactive-engines.md)           |
| 10  | Data Poisoning         | 4       | [10-data-poisoning.md](./10-data-poisoning.md)                 |
| 11  | Advanced Research      | 9       | [11-advanced-research.md](./11-advanced-research.md)           |
| 12  | Deep Learning          | 6       | [12-deep-learning.md](./12-deep-learning.md)                   |
| 13  | Meta-Judge + XAI       | 4       | [13-meta-xai.md](./13-meta-xai.md)                             |
| 14  | Adaptive Behavioral 🆕 | 2       | [14-adaptive-behavioral-en.md](./14-adaptive-behavioral-en.md) |

---

## Complete Engine Index

| #   | Engine                     | Category              | LOC |
| --- | -------------------------- | --------------------- | --- |
| 1   | Sheaf Coherence            | Strange Math Core     | 580 |
| 2   | Hyperbolic Geometry        | Strange Math Core     | 672 |
| 3   | TDA Enhanced               | Strange Math Core     | 451 |
| 4   | Information Geometry       | Strange Math Core     | 412 |
| 5   | Chaos Theory               | Strange Math Core     | 350 |
| 6   | Category Theory            | Strange Math Core     | 444 |
| 7   | Homomorphic Encryption     | Strange Math Extended | 599 |
| 8   | Spectral Graph             | Strange Math Extended | 400 |
| 9   | Injection Engine           | Classic Detection     | 350 |
| 10  | Meta-Judge                 | Meta-XAI              | 450 |
| 86  | Attacker Fingerprinting 🆕 | Adaptive Behavioral   | 650 |
| 87  | Adaptive Markov 🆕         | Adaptive Behavioral   | 140 |
| ... | ...                        | ...                   | ... |

_Full index in individual category files_

---

## General Expert Recommendations

### If You're a Topologist/Geometer

1. We use terms ("cohomology", "Betti numbers") as **metaphors**
2. Implementations are **heuristics** inspired by theory
3. We welcome PRs with more correct formulations

### If You're an ML Engineer

1. ✅ **Benchmark Results:** Recall 85.1%, Precision 84.4%, F1 84.7%
2. Embeddings: sentence-transformers / BERT (plug-and-play)
3. All engines run on CPU, GPU optional

### If You're an AppSec Expert

1. This is **defense-in-depth** — many detection layers
2. Thresholds need tuning for your traffic
3. False positive rate depends on domain

---

## Archive

Full documentation in single files:

- [engines-expert-deep-dive.md](../engines-expert-deep-dive.md) (Russian)
- [engines-expert-deep-dive-en.md](../engines-expert-deep-dive-en.md) (English)
