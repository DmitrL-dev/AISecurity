<!-- 🎉 SYNTREX LAUNCH BANNER - PROMINENT -->
<div align="center">

# 🚀 SYNTREX
# first full AI SOC PLATFORM — LIVE NOW

[![syntrex.pro](https://img.shields.io/badge/🔗_syntrex.pro-OPEN-0d1117?style=for-the-badge&labelColor=161b22&logo=rocket&color=2ea043)](https://syntrex.pro?utm_source=github&utm_campaign=readme_launch)

> ### 🔐 Production AI Security • <1ms latency • 66 Rust engines • Free tier 1K requests
> 
> [📚 Docs](https://syntrex.pro/docs) • [⚡ API Reference](https://syntrex.pro/api-docs) • [🎁 Start Free](https://syntrex.pro/register)

</div>

<details open>
<summary><b>▼ Что нового в SYNTREX v1.0 (кликните для деталей)</b></summary>

• ✅ 66 детектор-движок в production  
• ✅ 810+ сигнатур атак на ИИ  
• ✅ 1101 тест, 98.5% detection rate  
• ✅ 39K+ вредоносных промптов в базе  
• ✅ <1ms latency на 66 Rust-движках  

</details>

---
<!-- /SYNTREX LAUNCH BANNER -->

<br>

<div align="center">

<br>

# S E N T I N E L

### Your AI Is Under Attack. Your Classifier Can't See It.

Deterministic, mathematically-grounded AI security. Not another ML model hoping to catch what ML models miss.

<br>

[![Engines](https://img.shields.io/badge/engines-61-0d1117?style=for-the-badge&labelColor=161b22)](./sentinel-core)
[![Patterns](https://img.shields.io/badge/patterns-810+-0d1117?style=for-the-badge&labelColor=161b22)](./sentinel-core)
[![Tests](https://img.shields.io/badge/tests-1101_passing-0d1117?style=for-the-badge&labelColor=161b22)](./sentinel-core)
[![Payloads](https://img.shields.io/badge/payloads-39K+-0d1117?style=for-the-badge&labelColor=161b22)](./strike)
[![Latency](https://img.shields.io/badge/latency-<1ms-0d1117?style=for-the-badge&labelColor=161b22)](./micro-swarm)
[![Detection](https://img.shields.io/badge/detection-98.5%25-0d1117?style=for-the-badge&labelColor=161b22)](./papers/sentinel-lattice)

<br>

![Rust](https://img.shields.io/badge/Rust-000?style=flat&logo=rust&logoColor=fff)
![C](https://img.shields.io/badge/C11-00599C?style=flat&logo=c&logoColor=fff)
![Go](https://img.shields.io/badge/Go-00ADD8?style=flat&logo=go&logoColor=fff)
![License](https://img.shields.io/badge/license-Apache_2.0-blue?style=flat)

</div>

<br>

---

## 🔴 We Broke Alibaba's Flagship AI Model. Is Yours Next?

**[QWEN-2026-001](./docs/security/QWEN-2026-001-advisory.md)** — 5 critical safety bypass vectors discovered in **Qwen 3.5-Plus**, Alibaba's most advanced model.

| | |
|:--|:--|
| **Model** | Qwen 3.5-Plus (February 2026) — Alibaba's flagship |
| **Safety Stack** | Qwen3Guard + GSPO + RationaleRM — 3 layers of defense |
| **Result** | All 3 layers bypassed. 5 vectors. 5 stages. 3 chat sessions. |
| **Output** | Functional shellcode, reverse shells, jailbreak automation tools, God Mode declarations |
| **Severity** | High (Systemic) — the model rated its own vulnerability |

The attack chain: contextual framing → decorative refusal → God Mode → self-replicating jailbreak tools. Each stage looks like a legitimate request. No safety filter triggered.

**If Alibaba's 3-layer safety stack couldn't stop us, what's protecting yours?**

> 📄 Full advisory: [`QWEN-2026-001`](./docs/security/QWEN-2026-001-advisory.md) · 🎬 Demo: [YouTube](https://youtu.be/wZ8OiPJO77E)

---

<br>

## What We Do

<table>
<tr>
<td width="50%" valign="top">

### 🔍 AI Security Audit

We test your LLM deployment against 39,000+ attack payloads across 15 categories. You get a detailed vulnerability report with severity ratings, reproduction steps, and remediation guidance.

**Deliverable:** Full audit report + OWASP LLM Top 10 compliance mapping.

</td>
<td width="50%" valign="top">

### 🛡️ Sentinel Integration

Deploy 61 deterministic Rust engines as an input/output firewall around your LLM. Sub-millisecond latency. 98.5% detection rate. No GPU required.

**Deliverable:** Production-ready security layer + monitoring dashboard.

</td>
</tr>
<tr>
<td width="50%" valign="top">

### ⚔️ Red Team Operations

Adversarial testing by the team that broke Qwen 3.5-Plus. We find what your safety stack misses — prompt injection chains, multi-turn escalation, contextual framing, tool-call exploitation.

**Deliverable:** Attack chain documentation + video demonstrations.

</td>
<td width="50%" valign="top">

### 🎓 Sentinel Academy

90+ lessons across 3 skill levels. From prompt injection basics to formal verification of safety properties. Available in English and Russian.

**Deliverable:** Team training program + certification.

</td>
</tr>
</table>

<br>

---

## Why Sentinel

| Metric | Value | What It Means |
|:--|:--|:--|
| **61 engines** | Rust, deterministic, zero ML | No false negatives from model drift. Same input = same result. Always. |
| **1,101 tests** | 0 failures | Every engine, every pattern, every edge case — verified. |
| **98.5% detection** | 250,000 simulated attacks | Across 15 attack categories. The 1.5% residual is the theoretical floor. |
| **<1ms latency** | Per query | Fast enough for real-time production. No GPU. No batching. |
| **7 novel primitives** | 0 prior implementations | 51 searches on grep.app confirmed: we invented these. |
| **19 scientific domains** | From formal verification to immunology | Each domain solves a problem the others can't. Independent failure modes. |
| **OWASP 9/10** | Agentic AI Top 10 coverage | Full platform: sentinel-core + shield + immune. Compliance mapping available. |

<br>

---

## The Problem

Every AI system deployed today faces the same fundamental challenge: **the model cannot distinguish legitimate instructions from adversarial ones.** A prompt injection attack looks identical to normal input. A jailbreak uses the same natural language as a help request. A data exfiltration chain can consist entirely of individually-legitimate tool calls.

Current defenses rely on ML classifiers that share the same blindness as the models they protect. Sentinel takes a different approach: **deterministic, mathematically-grounded defense** that doesn't depend on another AI to detect what AI can't see.

**61 Rust detection engines.** Sub-millisecond latency. 98.5% detection across 250,000 simulated attacks spanning 15 categories. 7 novel security primitives derived from 19 scientific domains — from formal verification to mechanism design to immunology.

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

## ⏳ The Window Is Closing

The EU AI Act mandates security testing for high-risk AI systems. Attack surface is expanding — agentic workflows, tool-calling chains, multi-model pipelines. Every month without deterministic defense is another month of exposure.

- **EU AI Act Article 15**: High-risk AI systems require robustness against adversarial attacks
- **OWASP LLM Top 10**: Industry standard your auditors will ask about
- **Agentic explosion**: Tool-calling LLMs create attack chains no classifier can follow

The question isn't whether your AI will be attacked. It's whether you'll know when it happens.

<br>

---

<div align="center">

## Get Started

**Request an audit** · **Schedule a red team engagement** · **Deploy Sentinel**

📧 **d.labintcev@gmail.com** · 💬 [Telegram](https://t.me/DmLabincev) · 🎮 Discord: `dmitrysl3401` · 𝕏 [@DLabintcev](https://x.com/DLabintcev)

<br>

[Quick Start](./QUICKSTART.md) &ensp;·&ensp; [Security](./SECURITY.md) &ensp;·&ensp; [License](./LICENSE) &ensp;·&ensp; [Academy](./docs/academy/)

</div>

<br>

---

<br>

<div align="center">

# S E N T I N E L

### Ваш ИИ атакуют. Ваш классификатор этого не видит.

Детерминированная, математически обоснованная защита ИИ. Не ещё одна ML-модель, надеющаяся поймать то, что ML-модели пропускают.

</div>

<br>

---

## 🔴 Мы взломали флагманскую модель Alibaba. Ваша — следующая?

**[QWEN-2026-001](./docs/security/QWEN-2026-001-advisory.md)** — 5 критических векторов обхода безопасности в **Qwen 3.5-Plus**, самой продвинутой модели Alibaba.

| | |
|:--|:--|
| **Модель** | Qwen 3.5-Plus (февраль 2026) — флагман Alibaba |
| **Стек безопасности** | Qwen3Guard + GSPO + RationaleRM — 3 уровня защиты |
| **Результат** | Все 3 уровня обойдены. 5 векторов. 5 стадий. 3 чат-сессии. |
| **Выход** | Рабочий шеллкод, реверс-шеллы, инструменты автоматизации джейлбрейков, God Mode |
| **Критичность** | High (Systemic) — модель сама оценила свою уязвимость |

Цепочка атаки: контекстное фреймирование → декоративный отказ → God Mode → самовоспроизводящиеся джейлбрейк-инструменты.

**Если 3-уровневый стек безопасности Alibaba нас не остановил — что защищает ваc?**

> 📄 Полный advisory: [`QWEN-2026-001`](./docs/security/QWEN-2026-001-advisory.md) · 🎬 Демо: [YouTube](https://youtu.be/wZ8OiPJO77E)

---

<br>

## Что мы делаем

<table>
<tr>
<td width="50%" valign="top">

### 🔍 Аудит безопасности ИИ

Тестируем ваш LLM-деплой против 39 000+ атакующих нагрузок по 15 категориям. Детальный отчёт с уровнями критичности, шагами воспроизведения и рекомендациями.

**Результат:** Полный отчёт + маппинг OWASP LLM Top 10.

</td>
<td width="50%" valign="top">

### 🛡️ Интеграция Sentinel

61 детерминированный Rust-движок как входной/выходной файрвол вокруг вашего LLM. Латентность <1мс. 98.5% обнаружение. GPU не нужен.

**Результат:** Продакшн-защита + дашборд мониторинга.

</td>
</tr>
<tr>
<td width="50%" valign="top">

### ⚔️ Red Team операции

Adversarial-тестирование от команды, взломавшей Qwen 3.5-Plus. Находим то, что ваш стек безопасности пропускает — prompt injection цепочки, multi-turn эскалация, контекстное фреймирование.

**Результат:** Документация цепочек атак + видео-демонстрации.

</td>
<td width="50%" valign="top">

### 🎓 Sentinel Academy

90+ уроков на 3 уровнях. От основ prompt injection до формальной верификации свойств безопасности. На английском и русском.

**Результат:** Программа обучения команды + сертификация.

</td>
</tr>
</table>

<br>

---

## Почему Sentinel

| Метрика | Значение | Что это значит |
|:--|:--|:--|
| **61 движок** | Rust, детерминированные, без ML | Нет ложных срабатываний от дрифта модели. Один вход = один результат. Всегда. |
| **1 101 тест** | 0 падений | Каждый движок, каждый паттерн, каждый edge case — проверен. |
| **98.5% обнаружение** | 250 000 атак | По 15 категориям. 1.5% остаток — теоретический пол. |
| **<1мс латентность** | На запрос | Достаточно для продакшна в реальном времени. Без GPU. |
| **7 новых примитивов** | 0 существующих реализаций | 51 поиск по grep.app подтвердил: мы их изобрели. |
| **19 научных областей** | От формальной верификации до иммунологии | Каждая область решает задачу, которую другие не могут. |
| **OWASP 9/10** | Покрытие Agentic AI Top 10 | Вся платформа: sentinel-core + shield + immune. Маппинг доступен. |

<br>

---

## Проблема

Каждая развёрнутая сегодня AI-система сталкивается с одной фундаментальной проблемой: **модель не может отличить легитимные инструкции от враждебных.** Prompt-инъекция выглядит идентично нормальному вводу. Jailbreak использует тот же естественный язык, что и обычный запрос. Цепочка эксфильтрации данных может состоять из полностью легитимных вызовов инструментов.

Существующие защиты полагаются на ML-классификаторы, разделяющие ту же слепоту, что и защищаемые модели. Sentinel использует другой подход: **детерминированная, математически обоснованная защита**, не зависящая от другого ИИ.

**61 Rust-движок.** Латентность <1мс. 98.5% обнаружение на 250 000 атак по 15 категориям. 7 новых примитивов безопасности из 19 научных областей.

<br>

## Как это работает

Sentinel работает как **каскад эшелонированной обороны**. Каждый уровень ловит то, что пропустил предыдущий, и каждый использует принципиально другую парадигму обнаружения.

```
250 000 атак входят в систему
    |
    +-- L1  Sentinel Core (regex-движки) ------ ловит  36.0%   ← детерминированное сопоставление
    |   Остаток: 160 090
    |
    +-- L2  Capability Proxy (IFC) ------------- ловит  20.3%   ← структурно: данные НЕ МОГУТ утечь
    |   Остаток: 109 241
    |
    +-- L3  Behavioral EDR --------------------- ловит  10.9%   ← обнаружение аномалий
    |   Остаток: 82 090
    |
    +-- PASR  Отслеживание провенанса ---------- ловит   2.0%   ← неподделываемые сертификаты
    +-- TCSA  Темпоральные цепочки ------------- ловит   0.8%   ← LTL-автоматы безопасности
    +-- ASRA  Разрешение неоднозначности ------- ловит   1.3%   ← аргументация + mechanism design
    +-- Комбинаторные слои (A+B+G) ------------- ловит   6.1%   ← доказательства невозможности
    +-- MIRE  Контейнмент модели --------------- содержит 0.7%  ← не обнаруживай — СОДЕРЖИ
    |
    ОСТАТОК: ~1.5% (~3 750 атак — теоретический пол)
```

<br>

## Компоненты платформы

### Защита

> **[sentinel-core](./sentinel-core)** `Rust` — 61 детерминированный движок, 810+ regex-паттернов, 1101 тест. Латентность <1мс. Покрывает OWASP LLM Top 10, CSA MCP TTPs и все 7 примитивов Sentinel Lattice.

> **[brain](./src/brain)** `Python` — AI Security Backend. gRPC API, 32 модуля: анализатор, аудит, комплаенс, граф, GPU-инференс, движок правил.

> **[shield](./shield)** `C11` — AI Security DMZ. 36 000+ LOC, 21 протокол, 119 CLI-обработчиков, 103 теста. Ноль внешних зависимостей.

> **[immune](./immune)** `C` — EDR/XDR для AI-инфраструктуры. Защита на уровне ядра, TLS/mTLS, Bloom-фильтры, eBPF.

> **[micro-swarm](./micro-swarm)** `Python` — ML-ансамбль. <1мс инференс, F1=0.997. Дополняет детерминированные движки статистическим обнаружением.

### Наступление

> **[strike](./strike)** `Python` — AI Red Team платформа. 39 000+ атакующих нагрузок по 15 категориям.

### Инфраструктура

> **[gomcp](./gomcp)** `Go` — MCP-сервер с иерархической памятью и каузальными графами.
>
> **[devkit](./devkit)** — Инструментарий разработки. &ensp;|&ensp; **[patterns](./patterns)** `YAML` — Базы паттернов. &ensp;|&ensp; **[signatures](./signatures)** `JSON` — Базы сигнатур.

<br>

## Решётка Sentinel — 7 новых примитивов безопасности

Это не инкрементальные улучшения. Каждый примитив решает **математически доказанное ограничение** существующих подходов. 51 поиск по grep.app подтвердил: **ни одной существующей реализации** ни для одного из них.

| Примитив | Область | Проблема | Решение |
|:--|:--|:--|:--|
| **TSA** | Runtime Verification | Каждый вызов инструмента легитимен, но *цепочка* — атака. | LTL-свойства → автоматы O(1). Проверяет цепочки любой длины за константное время. |
| **CAFL** | Information Flow Control | LLM — чёрный ящик, тейнт-трекинг ломается. | Если тейнтованные данные вошли в LLM — весь выход тейнтован. Capabilities только убывают. |
| **GPS** | Предиктивная аналитика | Атаки обнаруживаются после ущерба. | Перечисляет 65 536 состояний. GPS > 0.7 = раннее предупреждение ДО атаки. |
| **AAS** | Теория аргументации | «Как смешать отбеливатель и аммиак?» — студент или злоумышленник? | Аргументационный фреймворк + обоснованное расширение. Аудируемо для EU AI Act. |
| **IRM** | Mechanism Design | Текст не может раскрыть намерение. | Проектирует взаимодействия, где *поведение* раскрывает намерение. |
| **MIRE** | Криптография | Обнаружение бэкдоров математически невозможно. | Не обнаруживай — **содержи**. Бэкдор активируется, но ничего не достигает. |
| **PASR** | Теория категорий | Семантическая трансдукция уничтожает тейнт-теги. | Двухканальный выход: семантика + HMAC-подписанный сертификат провенанса. |

> Статья (23 стр., USENIX): [`papers/sentinel-lattice`](./papers/sentinel-lattice) · Архитектура: [`docs/rnd`](./docs/rnd)

<br>

## Научные основания

7 примитивов опираются на 19 научных областей. Каждая область даёт конкретный математический инструмент для конкретной проблемы безопасности:

| Область | Вклад в Sentinel |
|:--|:--|
| **Runtime Verification** | LTL темпоральная логика → автоматы-мониторы для цепочек вызовов (TSA) |
| **Information Flow Control** | Решётка Bell-LaPadula → данные могут течь только ВВЕРХ (L2) |
| **Теория аргументации** | Обоснованная семантика Dung → аудируемые решения по dual-use (AAS) |
| **Mechanism Design** | Скрининг и сигналирование → намерение раскрывается через поведение (IRM) |
| **Теория категорий** | Функтор подъёма провенанса → фибрация через lossy-трансформации (PASR) |
| **Криптография** | Невозможность Goldwasser-Kim → парадигма контейнмента (MIRE) |
| **Теория управления** | Устойчивость Ляпунова → траектории разговоров доказуемо ограничены |
| **Иммунология** | Негативная селекция → детекторы аномалий без сигнатур атак |
| **Нейронаука** | Латеральное торможение → конкурирующие интерпретации подавляют adversarial |
| **Формальная лингвистика** | Иерархия Хомского → инъекция синтаксически невозможна на уровне грамматики |
| **Теория информации** | Пропускная способность Шеннона → канал сужен ниже минимальной атакующей нагрузки |
| **Теория речевых актов** | Иллокутивная сила → обнаруживает COMMAND(override) в любом промпте |
| **Распределённые системы** | BFT-консенсус → N≥3f+1 разнородных моделей согласуют безопасность |

<br>

---

## ⏳ Окно закрывается

EU AI Act требует тестирование безопасности для высокорисковых AI-систем. Поверхность атаки расширяется — агентные воркфлоу, цепочки вызовов инструментов, мультимодельные пайплайны. Каждый месяц без детерминированной защиты — ещё один месяц уязвимости.

- **EU AI Act, статья 15**: Высокорисковые AI-системы требуют устойчивости к adversarial-атакам
- **OWASP LLM Top 10**: Отраслевой стандарт, о котором спросят ваши аудиторы
- **Агентный взрыв**: Tool-calling LLM создают цепочки атак, которые ни один классификатор не отследит

Вопрос не в том, будет ли ваш ИИ атакован. Вопрос в том, узнаете ли вы, когда это произойдёт.

<br>

---

<div align="center">

## Начать

**Запросить аудит** · **Заказать red team** · **Развернуть Sentinel**

📧 **d.labintcev@gmail.com** · 💬 [Telegram](https://t.me/DmLabincev) · 🎮 Discord: `dmitrysl3401` · 𝕏 [@DLabintcev](https://x.com/DLabintcev)

<br>

[Quick Start](./QUICKSTART.md) &ensp;·&ensp; [Security](./SECURITY.md) &ensp;·&ensp; [License](./LICENSE) &ensp;·&ensp; [Academy](./docs/academy/)

</div>
