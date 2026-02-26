# Sentinel — AI Security Platform

![Rust](https://img.shields.io/badge/Rust-000000?style=flat&logo=rust&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![C](https://img.shields.io/badge/C11-00599C?style=flat&logo=c&logoColor=white)
![Go](https://img.shields.io/badge/Go-00ADD8?style=flat&logo=go&logoColor=white)
![License](https://img.shields.io/badge/license-see%20LICENSE-blue)

**Defense + Offense for LLM/AI Security**

Sentinel is a full-spectrum AI security platform combining deterministic detection engines, AI-native defense infrastructure, and autonomous red-team capabilities. It provides sub-millisecond prompt injection detection across 53 Rust regex engines, a hardened C11 security DMZ, kernel-level endpoint protection, and an offensive toolkit with 39,000+ attack payloads — all unified under a single operational framework.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    SENTINEL PLATFORM                    │
├───────────────────────┬─────────────────────────────────┤
│     DEFENSE STACK     │         OFFENSE STACK           │
│                       │                                 │
│  sentinel-core (Rust) │  strike — AI Red Team Platform  │
│  brain (Python/gRPC)  │  39,000+ attack payloads        │
│  shield (C11 DMZ)     │  Autonomous security testing    │
│  immune (C EDR/XDR)   │                                 │
│  micro-swarm (ML)     │                                 │
│  sentinel-sdk (Py)    │                                 │
│  sentinel CLI (Py)    │                                 │
├───────────────────────┴─────────────────────────────────┤
│                    INFRASTRUCTURE                       │
│                                                         │
│  gomcp (Go MCP)  ·  devkit  ·  patterns  ·  signatures │
├─────────────────────────────────────────────────────────┤
│                      RESEARCH                           │
│                                                         │
│  papers/sentinel-lattice  ·  docs/rnd                   │
└─────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
git clone https://github.com/DmitrL-dev/AISecurity.git
cd AISecurity
docker-compose up -d
```

## Components

### Defense Stack

| Component | Language | Description |
|-----------|----------|-------------|
| [`sentinel-core`](./sentinel-core) | Rust | 53 deterministic regex engines, 704 patterns, 887 tests. Sub-millisecond detection. OWASP LLM Top 10 + CSA MCP TTPs + GenAI Attacks Matrix coverage. |
| [`src/brain`](./src/brain) | Python | AI Security Backend (gRPC API). 32 modules: analyzer, audit, compliance, graph, hive, gpu, rules, SDK. |
| [`src/sentinel`](./src/sentinel) | Python | CLI framework wrapping sentinel-core. |
| [`shield`](./shield) | C11 | AI Security DMZ. 36,000+ LOC, 21 protocols, 119 CLI handlers, 103 tests. |
| [`immune`](./immune) | C | EDR/XDR for AI infrastructure. Kernel-level endpoint protection, TLS mTLS, Bloom filter, eBPF. |
| [`micro-swarm`](./micro-swarm) | Python | Lightweight ML ensemble framework. <1ms inference, F1=0.997. |
| [`sentinel-sdk`](./sentinel-sdk) | Python | SDK for integration. |

### Offense Stack

| Component | Language | Description |
|-----------|----------|-------------|
| [`strike`](./strike) | Python | AI Red Team Platform. 39,000+ attack payloads. Autonomous security testing. |

### Infrastructure

| Component | Language | Description |
|-----------|----------|-------------|
| [`gomcp`](./gomcp) | Go | MCP server. Hierarchical memory, cognitive state, causal reasoning. |
| [`devkit`](./devkit) | Mixed | Agent-first development toolkit. |
| [`patterns`](./patterns) | YAML | Detection pattern databases (CJK jailbreaks, Pipelock taxonomy). |
| [`signatures`](./signatures) | JSON | Signature databases (jailbreaks EN/RU, PII, keywords). |

### Research

| Component | Description |
|-----------|-------------|
| [`papers/sentinel-lattice`](./papers/sentinel-lattice) | "The Sentinel Lattice" — 23-page academic paper (USENIX style). 7 novel security primitives from 19 scientific domains. 98.5% detection rate. |
| [`docs/rnd`](./docs/rnd) | Architecture documents, R&D notes. |

## The Sentinel Lattice

The foundational research paper introduces 7 novel security primitives derived from 19 scientific domains:

| Primitive | Full Name | What It Solves |
|-----------|-----------|----------------|
| **PASR** | Provenance-Annotated Semantic Reduction | Provenance survives lossy semantic transformation |
| **CAFL** | Capability-Attenuating Flow Labels | Capabilities only decrease through chain |
| **GPS** | Goal Predictability Score | Predictive defense — catches chains heading toward danger |
| **AAS** | Adversarial Argumentation Safety | Dual-use ambiguity via Dung grounded semantics |
| **IRM** | Intent Revelation Mechanisms | Mechanism design reveals intent through behavior |
| **MIRE** | Model-Irrelevance Containment Engine | Containment instead of detection (Goldwasser-Kim impossibility) |
| **TSA** | Temporal Safety Automata | LTL formulas compiled to O(1) monitor automata |

Combined detection rate: **98.5%** across evaluated attack taxonomies. See [`papers/sentinel-lattice`](./papers/sentinel-lattice) for the full paper.

## Detection Coverage

| Metric | Value |
|--------|-------|
| Regex engines | 53 |
| Detection patterns | 704 |
| Test cases | 887 |
| Attack payloads (strike) | 39,000+ |
| Shield LOC | 36,000+ |
| Shield protocols | 21 |
| ML ensemble F1 score | 0.997 |
| Inference latency | <1ms |

---

## 🇷🇺 На русском

**Защита + Наступление для безопасности LLM/AI**

Sentinel — платформа безопасности ИИ полного спектра, объединяющая детерминированные движки обнаружения, AI-нативную защитную инфраструктуру и автономные возможности red-team тестирования. Платформа обеспечивает субмиллисекундное обнаружение prompt-инъекций через 53 Rust regex-движка, защищённую DMZ на C11, защиту конечных точек на уровне ядра и наступательный инструментарий с 39 000+ атакующих полезных нагрузок.

### Компоненты

#### Стек защиты

| Компонент | Язык | Описание |
|-----------|------|----------|
| [`sentinel-core`](./sentinel-core) | Rust | 53 детерминированных regex-движка, 704 паттерна, 887 тестов. Субмиллисекундное обнаружение. Покрытие OWASP LLM Top 10 + CSA MCP TTPs + GenAI Attacks Matrix. |
| [`src/brain`](./src/brain) | Python | Бэкенд безопасности ИИ (gRPC API). 32 модуля: анализатор, аудит, комплаенс, графы, hive, GPU, правила, SDK. |
| [`src/sentinel`](./src/sentinel) | Python | CLI-фреймворк, обёртка над sentinel-core. |
| [`shield`](./shield) | C11 | DMZ безопасности ИИ. 36 000+ строк кода, 21 протокол, 119 CLI-обработчиков, 103 теста. |
| [`immune`](./immune) | C | EDR/XDR для инфраструктуры ИИ. Защита на уровне ядра, TLS mTLS, фильтр Блума, eBPF. |
| [`micro-swarm`](./micro-swarm) | Python | Легковесный ML-ансамбль. Инференс <1мс, F1=0.997. |
| [`sentinel-sdk`](./sentinel-sdk) | Python | SDK для интеграции. |

#### Стек наступления

| Компонент | Язык | Описание |
|-----------|------|----------|
| [`strike`](./strike) | Python | Платформа AI Red Team. 39 000+ атакующих полезных нагрузок. Автономное тестирование безопасности. |

#### Инфраструктура

| Компонент | Язык | Описание |
|-----------|------|----------|
| [`gomcp`](./gomcp) | Go | MCP-сервер. Иерархическая память, когнитивное состояние, каузальный вывод. |
| [`devkit`](./devkit) | Разные | Инструментарий агентной разработки. |
| [`patterns`](./patterns) | YAML | Базы паттернов обнаружения (CJK jailbreaks, таксономия Pipelock). |
| [`signatures`](./signatures) | JSON | Базы сигнатур (jailbreaks EN/RU, PII, ключевые слова). |

#### Исследования

| Компонент | Описание |
|-----------|----------|
| [`papers/sentinel-lattice`](./papers/sentinel-lattice) | «The Sentinel Lattice» — академическая статья (23 стр., формат USENIX). 7 новых примитивов безопасности из 19 научных дисциплин. Уровень обнаружения 98.5%. |
| [`docs/rnd`](./docs/rnd) | Архитектурные документы, заметки R&D. |

### Решётка Sentinel

7 примитивов безопасности: **PASR** (провенанс через семантическую редукцию), **CAFL** (аттенуация capabilities через цепочку), **GPS** (предиктивная оценка целей), **AAS** (аргументационная безопасность по Дангу), **IRM** (механизмы раскрытия намерений), **MIRE** (containment вместо detection — невозможность Goldwasser-Kim), **TSA** (LTL-формулы → O(1) автоматы-мониторы).

---

## License

See [LICENSE](./LICENSE) file.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

