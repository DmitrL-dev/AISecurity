# AI Security Platform Comparison

> Sentinel vs leading LLM security solutions (February 2026)

## Overview

| Feature | **Sentinel** | Lakera Guard | LLM Guard | Prompt Armor | NeMo Guardrails |
|---------|:------------:|:------------:|:---------:|:------------:|:---------------:|
| **Detection Engines** | **61 Rust** | ~10 | 4 | Unknown | ~5 |
| **Regex Patterns** | **810+** | Unknown | ~50 | Unknown | ~30 |
| **Tests** | **1101** | Unknown | ~100 | Unknown | Unknown |
| **Attack Payloads** | **39K+** | 0 | 0 | 0 | 0 |
| **Open Source** | **Yes** | No (SaaS) | Yes | No | Yes |
| **Self-Hosted** | **Yes** | No | Yes | No | Yes |
| **Latency** | **<1ms** | ~100ms | ~30ms | Unknown | ~50ms |
| **Novel Primitives** | **7** | 0 | 0 | 0 | 0 |
| **Formal Guarantees** | **Yes (LTL)** | No | No | No | No |

## Detection Capabilities

| Capability | Sentinel | Lakera | LLM Guard | NeMo |
|------------|:--------:|:------:|:---------:|:----:|
| Prompt Injection | 12 engines | 1 | 1 | 1 |
| Jailbreak | 39K patterns | Yes | Yes | Yes |
| PII Detection | Yes | Yes | Yes | No |
| Tool Abuse / MCP | 4 engines | No | No | No |
| Data Exfiltration | Yes | No | No | No |
| Social Engineering | Yes | No | No | No |
| Memory Poisoning | Yes | No | No | No |
| Multi-turn Escalation | Yes (crescendo) | No | No | No |
| RAG Poisoning | Yes | No | No | No |

## What Only Sentinel Has

| Capability | What It Does | Why Nobody Else Has It |
|------------|-------------|----------------------|
| **Temporal Safety Automata** | LTL safety properties on tool-call chains | Adapted from runtime verification — never applied to LLMs before |
| **Capability Proxy (IFC)** | Bell-LaPadula lattice for data flow | Structural defense, not detection — architecturally different approach |
| **Adversarial Argumentation** | Dung's grounded semantics for dual-use | First application of formal argumentation to AI safety |
| **Intent Revelation** | Mechanism design reveals intent via behavior | Economics applied to security — new paradigm |
| **Model Containment** | Goldwasser-Kim: don't detect, contain | Paradigm shift from detection to containment |
| **Provenance Tracking** | HMAC-signed provenance through lossy transforms | Category theory applied to taint tracking |
| **Goal Predictability** | Enumerates 65K states, predicts danger | Predictive defense — catches attacks before they arrive |
| **Offensive Testing** | 39K+ real attack payloads | Integrated red team — test your own defenses |
| **C11 DMZ** | 36K+ LOC pure C security gateway | Hardware-level performance, zero dependencies |
| **EDR/XDR** | Kernel-level AI infrastructure protection | eBPF hooks, Bloom filters — enterprise-grade |

## Architecture Comparison

| Aspect | Sentinel | ML-based solutions |
|--------|----------|-------------------|
| **Approach** | Deterministic regex + novel primitives | ML classifiers |
| **Failure mode** | Predictable, auditable | Opaque, unpredictable |
| **Bypass difficulty** | Each layer uses different paradigm | Single paradigm = single bypass |
| **Explainability** | Every match has engine + pattern + confidence | Black box score |
| **EU AI Act** | Full audit trail | Partial |
| **Cost** | Self-hosted, open source | SaaS pricing |

## Detection Rate Comparison

Based on 250,000 simulated attacks across 15 categories:

| Metric | Sentinel | Typical ML Guard |
|--------|:--------:|:----------------:|
| Overall detection | **98.5%** | ~85-90% |
| Direct injection | >99.99% | ~95% |
| Indirect injection | >99.97% | ~80% |
| Multi-turn crescendo | 99.3% | ~60% |
| Novel/zero-day | 96.2% | ~50% |
| False positive rate | ~1.5% | ~3-5% |

---

*Comparison based on publicly available information as of February 2026. We welcome corrections.*
