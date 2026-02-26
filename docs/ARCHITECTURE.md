# Sentinel Architecture

## Overview

Sentinel is a defense-in-depth AI security platform. Each layer uses a fundamentally different detection paradigm, so a bypass for one layer doesn't help against the next.

```
                        User / LLM Application
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                         SHIELD (C11)                          │
│              AI Security DMZ — 36K+ LOC, 21 protocols         │
│         Rate limiting · Protocol validation · DDoS defense    │
└──────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                     SENTINEL-CORE (Rust)                      │
│               61 Detection Engines · <1ms latency             │
│                                                               │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │  L1: Core   │ │ L1: Gaps    │ │ L1: Output  │            │
│  │  Injection  │ │ Memory Int. │ │ Meta-Frame  │            │
│  │  Jailbreak  │ │ Tool Shadow │ │ Tool-Call   │            │
│  │  PII, Exfil │ │ Cognitive   │ │ Crescendo   │            │
│  │  Moderation │ │ Dormant     │ │             │            │
│  │  Evasion    │ │ Code Sec.   │ │             │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐   │
│  │          SENTINEL LATTICE — 7 Novel Primitives         │   │
│  │                                                         │   │
│  │  TSA   Temporal Safety Automata (LTL → O(1) monitors)  │   │
│  │  CAFL  Capability-Attenuating Flow Labels               │   │
│  │  GPS   Goal Predictability Score                        │   │
│  │  AAS   Adversarial Argumentation Safety (Dung 1995)     │   │
│  │  IRM   Intent Revelation Mechanisms                     │   │
│  │  MIRE  Model-Irrelevance Containment                    │   │
│  │  PASR  Provenance-Annotated Semantic Reduction          │   │
│  │  L2    Capability Proxy + IFC (Bell-LaPadula)           │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │   Domain    │ │    Math     │ │  Structured  │            │
│  │ Behavioral  │ │ Hyperbolic  │ │  Agentic     │            │
│  │ Compliance  │ │ Spectral    │ │  RAG         │            │
│  │ Privacy     │ │ TDA, Chaos  │ │  Sheaf       │            │
│  │ + 13 more   │ │ Info Geom.  │ │              │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
└──────────────────────────────────────────────────────────────┘
                               │
                    ┌──────────┼──────────┐
                    ▼          ▼          ▼
             ┌──────────┐ ┌────────┐ ┌────────┐
             │  BRAIN   │ │ IMMUNE │ │ STRIKE │
             │ (Python) │ │  (C)   │ │(Python)│
             │ 32 mods  │ │EDR/XDR │ │ 39K+   │
             │ gRPC API │ │ eBPF   │ │payloads│
             └──────────┘ └────────┘ └────────┘
```

## Detection Cascade

```
250,000 attacks enter the system
    │
    ├── L1  Sentinel Core (53 regex engines) ─── catches  36.0%
    │   Remaining: 160,090
    │
    ├── L2  Capability Proxy (IFC) ───────────── catches  20.3%
    │   Remaining: 109,241
    │
    ├── L3  Behavioral EDR ───────────────────── catches  10.9%
    │   Remaining: 82,090
    │
    ├── PASR  Provenance tracking ────────────── catches   2.0%
    ├── TCSA  Temporal + capabilities ────────── catches   0.8%
    ├── ASRA  Ambiguity resolution ───────────── catches   1.3%
    ├── Combinatorial layers ─────────────────── catches   6.1%
    ├── MIRE  Model containment ──────────────── contains  0.7%
    │
    RESIDUAL: ~1.5% (theoretical floor)
```

## Engine Categories (61 total)

| Category | Count | Examples |
|----------|:-----:|---------|
| Core (PatternMatcher) | 12 | injection, jailbreak, PII, exfiltration, moderation |
| Critical Gap (Feb 2026) | 5 | memory_integrity, tool_shadowing, cognitive_guard |
| Output/Multi-turn | 4 | meta_framing, output_scanner, crescendo |
| Sentinel Lattice | 8 | temporal_safety, capability_proxy, argumentation_safety, capability_flow, goal_predictability, intent_revelation, model_containment, provenance_reduction |
| Domain (analyze API) | 17 | behavioral, compliance, privacy, supply_chain |
| Math | 5 | hyperbolic, spectral, TDA, chaos, info_geometry |
| ML/Semantic | 3 | semantic, anomaly, attention |
| Structured | 3 | agentic, RAG, sheaf |
| Other | 4 | embedding, drift, operational_context_injection, lethal_trifecta |

## Component Summary

| Component | Language | LOC | Purpose |
|-----------|----------|-----|---------|
| [sentinel-core](../sentinel-core) | Rust | ~25K | 61 detection engines, 1101 tests |
| [brain](../src/brain) | Python | ~15K | gRPC backend, 32 modules |
| [shield](../shield) | C11 | 36K+ | DMZ, 21 protocols, 103 tests |
| [immune](../immune) | C | ~10K | EDR/XDR, eBPF, kernel-level |
| [micro-swarm](../micro-swarm) | Python | ~5K | ML ensemble, F1=0.997 |
| [strike](../strike) | Python | ~20K | Red team, 39K+ payloads |
| [gomcp](../gomcp) | Go | ~8K | MCP server, memory, causal graphs |

## Data Flow

```
1. Input arrives at Shield (C11 DMZ)
2. Shield validates protocol, rate limits, forwards to Brain
3. Brain calls sentinel-core (Rust via PyO3) for detection
4. sentinel-core runs all 61 engines in <1ms
5. Results aggregated: detected/risk_score/matches/categories
6. Brain applies policy: allow / block / flag for review
7. Audit trail recorded
```
