<div align="center">

<br>

# S E N T I N E L

**Full-spectrum AI security platform**

<br>

[![Engines](https://img.shields.io/badge/engines-53-0d1117?style=for-the-badge&labelColor=161b22)](./sentinel-core)
[![Patterns](https://img.shields.io/badge/patterns-704-0d1117?style=for-the-badge&labelColor=161b22)](./sentinel-core)
[![Tests](https://img.shields.io/badge/tests-887-0d1117?style=for-the-badge&labelColor=161b22)](./sentinel-core)
[![Payloads](https://img.shields.io/badge/payloads-39K+-0d1117?style=for-the-badge&labelColor=161b22)](./strike)
[![Latency](https://img.shields.io/badge/latency-<1ms-0d1117?style=for-the-badge&labelColor=161b22)](./micro-swarm)
[![F1](https://img.shields.io/badge/F1-0.997-0d1117?style=for-the-badge&labelColor=161b22)](./micro-swarm)

<br>

![Rust](https://img.shields.io/badge/Rust-000?style=flat&logo=rust&logoColor=fff)
![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=fff)
![C](https://img.shields.io/badge/C11-00599C?style=flat&logo=c&logoColor=fff)
![Go](https://img.shields.io/badge/Go-00ADD8?style=flat&logo=go&logoColor=fff)
![License](https://img.shields.io/badge/license-see%20LICENSE-blue?style=flat)

</div>

<br>

Deterministic detection engines, AI-native defense infrastructure, and autonomous red-team capabilities — unified under a single operational framework. Sub-millisecond prompt injection detection with 98.5% coverage across OWASP LLM Top 10.

<br>

## Quick Start

```bash
git clone https://github.com/DmitrL-dev/AISecurity.git
cd AISecurity
docker-compose up -d
```

<br>

## Platform

```
  DEFENSE                    OFFENSE                 RESEARCH
  ─────────────────────      ─────────────────────   ─────────────────────
  sentinel-core  ·  brain    strike                  papers/sentinel-lattice
  shield  ·  immune          39K+ attack payloads    docs/rnd
  micro-swarm  ·  sdk  ·  cli
```

<br>

## Components

### Defense

> **[sentinel-core](./sentinel-core)** `Rust` — 53 deterministic regex engines, 704 patterns, 887 tests. Sub-millisecond detection. OWASP LLM Top 10 + CSA MCP TTPs + GenAI Attacks Matrix coverage.

> **[brain](./src/brain)** `Python` — AI Security Backend via gRPC API. 32 modules: analyzer, audit, compliance, graph, hive, GPU, rules, SDK.

> **[shield](./shield)** `C11` — AI Security DMZ. 36,000+ LOC, 21 protocols, 119 CLI handlers, 103 tests.

> **[immune](./immune)** `C` — EDR/XDR for AI infrastructure. Kernel-level endpoint protection, TLS mTLS, Bloom filter, eBPF.

> **[micro-swarm](./micro-swarm)** `Python` — Lightweight ML ensemble. <1ms inference, F1=0.997.

> **[sentinel-sdk](./sentinel-sdk)** `Python` — SDK for integration. &ensp;|&ensp; **[sentinel CLI](./src/sentinel)** `Python` — CLI framework wrapping sentinel-core.

### Offense

> **[strike](./strike)** `Python` — AI Red Team Platform. 39,000+ attack payloads. Autonomous security testing.

### Infrastructure

> **[gomcp](./gomcp)** `Go` — MCP server with hierarchical memory, cognitive state, causal reasoning.
>
> **[devkit](./devkit)** — Agent-first development toolkit. &ensp;|&ensp; **[patterns](./patterns)** `YAML` — Detection pattern databases (CJK jailbreaks, Pipelock taxonomy). &ensp;|&ensp; **[signatures](./signatures)** `JSON` — Signature databases (jailbreaks EN/RU, PII, keywords).

<br>

## The Sentinel Lattice

<table>
<tr><td><b>7 novel security primitives</b> derived from <b>19 scientific domains</b></td></tr>
</table>

23-page academic paper (USENIX style). Combined detection rate: **98.5%** across evaluated attack taxonomies.

| Primitive | Name | What It Solves |
|:--|:--|:--|
| **PASR** | Provenance-Annotated Semantic Reduction | Provenance survives lossy semantic transformation |
| **CAFL** | Capability-Attenuating Flow Labels | Capabilities only decrease through chain |
| **GPS** | Goal Predictability Score | Predictive defense — catches chains heading toward danger |
| **AAS** | Adversarial Argumentation Safety | Dual-use ambiguity via Dung grounded semantics |
| **IRM** | Intent Revelation Mechanisms | Mechanism design reveals intent through behavior |
| **MIRE** | Model-Irrelevance Containment Engine | Containment instead of detection (Goldwasser-Kim impossibility) |
| **TSA** | Temporal Safety Automata | LTL formulas compiled to O(1) monitor automata |

→ Full paper: [`papers/sentinel-lattice`](./papers/sentinel-lattice) &ensp;|&ensp; R&D notes: [`docs/rnd`](./docs/rnd)

<br>

---

<details>
<summary><b>🇷🇺 На русском</b></summary>

<br>

**Sentinel** — платформа безопасности ИИ полного спектра, объединяющая детерминированные движки обнаружения, AI-нативную защитную инфраструктуру и автономные возможности red-team тестирования. Субмиллисекундное обнаружение prompt-инъекций через 53 Rust regex-движка, защищённая DMZ на C11, защита конечных точек на уровне ядра и наступательный инструментарий с 39 000+ атакующих полезных нагрузок.

**Защита:** [`sentinel-core`](./sentinel-core) (Rust — 53 движка, 704 паттерна, 887 тестов) · [`brain`](./src/brain) (Python — gRPC API, 32 модуля) · [`shield`](./shield) (C11 — DMZ, 36 000+ LOC) · [`immune`](./immune) (C — EDR/XDR) · [`micro-swarm`](./micro-swarm) (Python — F1=0.997) · [`sentinel-sdk`](./sentinel-sdk) · [`CLI`](./src/sentinel)

**Наступление:** [`strike`](./strike) — 39 000+ атакующих полезных нагрузок, автономное тестирование.

**Инфраструктура:** [`gomcp`](./gomcp) (Go) · [`devkit`](./devkit) · [`patterns`](./patterns) (YAML) · [`signatures`](./signatures) (JSON)

**Решётка Sentinel** — 7 примитивов безопасности из 19 научных дисциплин: **PASR** (провенанс через семантическую редукцию), **CAFL** (аттенуация capabilities), **GPS** (предиктивная оценка целей), **AAS** (аргументационная безопасность по Дангу), **IRM** (раскрытие намерений), **MIRE** (containment вместо detection — невозможность Goldwasser-Kim), **TSA** (LTL → O(1) автоматы). Обнаружение: **98.5%**.

</details>

---

<br>

<div align="center">

[License](./LICENSE) &ensp;·&ensp; [Contributing](./CONTRIBUTING.md)

</div>
