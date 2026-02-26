<div align="center">

<br>

# S E N T I N E L

**Open-source AI security platform with 7 novel security primitives**

<br>

[![Engines](https://img.shields.io/badge/engines-61-0d1117?style=for-the-badge&labelColor=161b22)](./sentinel-core)
[![Patterns](https://img.shields.io/badge/patterns-810+-0d1117?style=for-the-badge&labelColor=161b22)](./sentinel-core)
[![Tests](https://img.shields.io/badge/tests-1101-0d1117?style=for-the-badge&labelColor=161b22)](./sentinel-core)
[![Payloads](https://img.shields.io/badge/payloads-39K+-0d1117?style=for-the-badge&labelColor=161b22)](./strike)
[![Latency](https://img.shields.io/badge/latency-<1ms-0d1117?style=for-the-badge&labelColor=161b22)](./micro-swarm)
[![Detection](https://img.shields.io/badge/detection-98.5%25-0d1117?style=for-the-badge&labelColor=161b22)](./papers/sentinel-lattice)

<br>

![Rust](https://img.shields.io/badge/Rust-000?style=flat&logo=rust&logoColor=fff)
![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=fff)
![C](https://img.shields.io/badge/C11-00599C?style=flat&logo=c&logoColor=fff)
![Go](https://img.shields.io/badge/Go-00ADD8?style=flat&logo=go&logoColor=fff)
![License](https://img.shields.io/badge/license-see%20LICENSE-blue?style=flat)

</div>

<br>

## The Problem

Every AI system deployed today faces the same fundamental challenge: **the model cannot distinguish legitimate instructions from adversarial ones.** A prompt injection attack looks identical to normal input. A jailbreak uses the same natural language as a help request. A data exfiltration chain can consist entirely of individually-legitimate tool calls.

Current defenses rely on ML classifiers that share the same blindness as the models they protect. Sentinel takes a different approach: **deterministic, mathematically-grounded defense** that doesn't depend on another AI to detect what AI can't see.

**61 Rust detection engines.** Sub-millisecond latency. 98.5% detection across 250,000 simulated attacks spanning 15 categories. 7 novel security primitives derived from 19 scientific domains — from formal verification to mechanism design to immunology.

<br>

## Quick Start

```bash
git clone https://github.com/DmitrL-dev/AISecurity.git
cd AISecurity
docker-compose up -d
```

<br>

## How It Works

Sentinel operates as a **defense-in-depth cascade**. Each layer catches what the previous one missed, and each layer uses a fundamentally different detection paradigm — so a bypass for one layer doesn't help against the next.

```
250,000 attacks enter the system
    |
    +-- L1  Sentinel Core (regex engines) ---- catches  36.0%   ← deterministic pattern matching
    |   Remaining: 160,090
    |
    +-- L2  Capability Proxy (IFC) ----------- catches  20.3%   ← structural: data CAN'T flow wrong
    |   Remaining: 109,241
    |
    +-- L3  Behavioral EDR ------------------- catches  10.9%   ← runtime anomaly detection
    |   Remaining: 82,090
    |
    +-- PASR  Provenance tracking ------------ catches   2.0%   ← unforgeable provenance certificates
    +-- TCSA  Temporal chains + capabilities -- catches   0.8%   ← LTL safety automata
    +-- ASRA  Ambiguity resolution ----------- catches   1.3%   ← argumentation + mechanism design
    +-- Combinatorial layers (A+B+G) --------- catches   6.1%   ← impossibility proofs
    +-- MIRE  Model containment -------------- contains  0.7%   ← don't detect, CONTAIN
    |
    RESIDUAL: ~1.5% (~3,750 attacks — theoretical floor)
```

The key insight: **each layer uses a different scientific paradigm**, so they don't share failure modes. Pattern matching, information flow control, temporal logic, argumentation theory, mechanism design, and containment are mathematically independent approaches.

<br>

## Platform Components

### Defense

> **[sentinel-core](./sentinel-core)** `Rust` — 61 deterministic detection engines, 810+ regex patterns, 1101 tests. Sub-millisecond per-query latency. Covers OWASP LLM Top 10, CSA MCP TTPs, GenAI Attacks Matrix, and all 7 Sentinel Lattice primitives.

> **[brain](./src/brain)** `Python` — AI Security Backend. gRPC API with 32 modules: analyzer, audit, compliance, graph, hive, GPU inference, rules engine, SDK.

> **[shield](./shield)** `C11` — AI Security DMZ. 36,000+ LOC pure C11, 21 protocols, 119 CLI handlers, 103 tests. Zero external dependencies.

> **[immune](./immune)** `C` — EDR/XDR for AI infrastructure. Kernel-level endpoint protection, TLS/mTLS, Bloom filters, eBPF hooks.

> **[micro-swarm](./micro-swarm)** `Python` — Lightweight ML ensemble. <1ms inference, F1=0.997. Complements deterministic engines with statistical detection.

> **[sentinel-sdk](./sentinel-sdk)** `Python` — Integration SDK. &ensp;|&ensp; **[sentinel CLI](./src/sentinel)** `Python` — CLI framework wrapping sentinel-core.

### Offense

> **[strike](./strike)** `Python` — AI Red Team Platform. 39,000+ attack payloads across 15 categories. Autonomous adversarial testing against your own defenses.

### Infrastructure

> **[gomcp](./gomcp)** `Go` — MCP server with hierarchical memory, cognitive state, causal reasoning graphs.
>
> **[devkit](./devkit)** — Agent-first development toolkit. &ensp;|&ensp; **[patterns](./patterns)** `YAML` — Detection pattern databases (CJK jailbreaks, Pipelock taxonomy). &ensp;|&ensp; **[signatures](./signatures)** `JSON` — Signature databases (jailbreaks EN/RU, PII, keywords).

<br>

## The Sentinel Lattice — 7 Novel Security Primitives

These aren't incremental improvements. Each primitive addresses a **mathematically proven limitation** of existing approaches. 51 cross-domain searches on grep.app confirmed: **zero prior implementations exist** for any of these.

| Primitive | Source Domain | The Problem | How It Solves It |
|:--|:--|:--|:--|
| **TSA** | Runtime Verification (Havelund & Rosu) | Individual tool calls are legitimate, but the *chain* is malicious. Current guards only check pairs. | LTL safety properties compiled to O(1) monitor automata. Checks arbitrary-length chains in constant time. |
| **CAFL** | Information Flow Control | LLM can perform ANY information transformation — taint tracking breaks because the model is a black box. | Worst-case assumption: if tainted data enters LLM, ALL output is tainted. Capabilities only DECREASE through chains. Sound by construction. |
| **GPS** | Predictive Analytics | Attacks are detected only AFTER the damage is done. | Enumerates the 16-bit abstract state space (65,536 states). Computes what fraction of continuations lead to danger. GPS > 0.7 = early warning BEFORE the attack arrives. |
| **AAS** | Argumentation Theory (Dung 1995) | "How do I mix bleach and ammonia?" — chemistry student or attacker? Same text, same semantics. No classifier can distinguish them. | Constructs explicit argumentation frameworks. Computes grounded extension via fixed-point iteration. Context-conditioned attacks tip the decision. Fully auditable for EU AI Act. |
| **IRM** | Mechanism Design (Economics) | Text alone cannot reveal intent — the fundamental impossibility of semantic identity. | Designs interactions where malicious users' *behavior* reveals intent. Screening, costly signaling, sequential revelation — even when text is identical, choices differ. |
| **MIRE** | Cryptography (Goldwasser-Kim 2022) | Backdoor detection is mathematically impossible (proven). All detection has a fundamental ceiling. | Paradigm shift: don't detect — **contain**. Output envelope, canary probes, spectral watchdog, capability sandbox. The backdoor activates but achieves nothing. |
| **PASR** | Category Theory + Cryptography | Semantic transduction destroys tokens. L2 taint tags die with them. Provenance and semantics are architecturally incompatible. | Two-channel output: lossy semantic intent + HMAC-signed provenance certificate. Provenance is a property of *derivations*, not tokens. A categorical fibration. |

> 23-page academic paper (USENIX format): [`papers/sentinel-lattice`](./papers/sentinel-lattice)
>
> Full architecture & R&D notes: [`docs/rnd`](./docs/rnd)

<br>

## Scientific Foundations

The 7 primitives draw from 19 scientific domains. This isn't decoration — each domain contributes a specific mathematical tool that solves a specific security problem:

| Domain | Contribution to Sentinel |
|:--|:--|
| **Runtime Verification** | LTL temporal logic → monitor automata for tool-call chains (TSA) |
| **Information Flow Control** | Bell-LaPadula lattice → data can only flow UP, never down (L2) |
| **Argumentation Theory** | Dung's grounded semantics → auditable dual-use decisions (AAS) |
| **Mechanism Design** | Screening & costly signaling → intent revealed through behavior (IRM) |
| **Category Theory** | Provenance lifting functor → fibration preserving taint through lossy transforms (PASR) |
| **Cryptography** | Goldwasser-Kim impossibility → containment paradigm shift (MIRE) |
| **Control Theory** | Lyapunov stability → conversation trajectories provably bounded |
| **Immunology** | Negative selection → anomaly detectors that don't need attack signatures |
| **Neuroscience** | Lateral inhibition → competing interpretations suppress adversarial readings |
| **Formal Linguistics** | Chomsky hierarchy → injection syntactically impossible at grammar level |
| **Information Theory** | Shannon capacity → channel narrowed below minimum attack payload |
| **Speech Act Theory** | Illocutionary force → detects COMMAND(override) hidden in any prompt |
| **Distributed Systems** | BFT consensus → N≥3f+1 diverse models agree on safety |

<br>

---

<details>
<summary><b>На русском</b></summary>

<br>

### Проблема

Каждая развёрнутая сегодня AI-система сталкивается с одной и той же фундаментальной проблемой: модель не может отличить легитимные инструкции от враждебных. Prompt-инъекция выглядит идентично нормальному вводу. Jailbreak использует тот же естественный язык, что и обычный запрос о помощи. Цепочка эксфильтрации данных может состоять из полностью легитимных вызовов инструментов.

Существующие защиты полагаются на ML-классификаторы, разделяющие ту же слепоту, что и защищаемые модели. Sentinel использует другой подход: **детерминированная, математически обоснованная защита**, не зависящая от другого ИИ для обнаружения того, что ИИ не может увидеть.

### Платформа

**Защита:** [`sentinel-core`](./sentinel-core) (Rust — 61 движок, 810+ паттернов, 1101 тест) · [`brain`](./src/brain) (Python — gRPC API, 32 модуля) · [`shield`](./shield) (C11 — DMZ, 36 000+ LOC) · [`immune`](./immune) (C — EDR/XDR) · [`micro-swarm`](./micro-swarm) (Python — F1=0.997) · [`sentinel-sdk`](./sentinel-sdk) · [`CLI`](./src/sentinel)

**Наступление:** [`strike`](./strike) — 39 000+ атакующих полезных нагрузок, автономное тестирование.

**Инфраструктура:** [`gomcp`](./gomcp) (Go — MCP-сервер) · [`devkit`](./devkit) · [`patterns`](./patterns) (YAML) · [`signatures`](./signatures) (JSON)

### Решётка Sentinel — 7 изобретённых примитивов

| Примитив | Из какой области | Какую проблему решает |
|:--|:--|:--|
| **TSA** | Runtime Verification | Каждый вызов инструмента легитимен, но цепочка — атака. TSA компилирует LTL-формулы в автоматы O(1). |
| **CAFL** | Information Flow Control | LLM — чёрный ящик, тейнт-трекинг ломается. CAFL: если тейнтованные данные вошли в LLM — весь выход тейнтован. Capabilities только убывают. |
| **GPS** | Prediktive Analytics | Атаки обнаруживаются после ущерба. GPS перечисляет 65 536 абстрактных состояний и считает долю опасных продолжений. GPS > 0.7 = раннее предупреждение. |
| **AAS** | Теория аргументации (Dung 1995) | «Как смешать отбеливатель и аммиак?» — студент или злоумышленник? Один текст, одна семантика. AAS строит аргументационный фреймворк и вычисляет обоснованное расширение. |
| **IRM** | Mechanism Design (экономика) | Текст не может раскрыть намерение — фундаментальная невозможность. IRM проектирует взаимодействия, где *поведение* раскрывает намерение. |
| **MIRE** | Криптография (Goldwasser-Kim 2022) | Обнаружение бэкдоров математически невозможно (доказано). MIRE: не обнаруживай — **содержи**. Бэкдор активируется, но ничего не достигает. |
| **PASR** | Теория категорий | Семантическая трансдукция уничтожает токены, тейнт-теги умирают с ними. PASR: двухканальный выход — семантика + HMAC-подписанный сертификат провенанса. |

Статья: [`papers/sentinel-lattice`](./papers/sentinel-lattice) · Архитектура: [`docs/rnd`](./docs/rnd)

Обнаружение: **98.5%** на 250 000 атак, 15 категорий. 51 поиск по grep.app: **0 существующих реализаций** любого из 7 примитивов.

</details>

---

<br>

<div align="center">

[License](./LICENSE) &ensp;·&ensp; [Security](./SECURITY.md) &ensp;·&ensp; [Quick Start](./QUICKSTART.md)

</div>
