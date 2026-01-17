<p align="center">
  <img src="./docs/images/sentinel_hero.png" alt="🐉 SENTINEL — AI Security Platform" width="100%">
</p>

<h1 align="center">SENTINEL — AI Security Platform</h1>

<p align="center">
  <strong>🛡️ Defense + ⚔️ Offense + 📦 Framework — Complete AI Security Suite</strong><br>
  <strong>Dragon v4.1 • January 2026</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/🧠_BRAIN-217_Engines-brightgreen?style=for-the-badge" alt="Brain">
  <img src="https://img.shields.io/badge/🛡️_SHIELD-113_Tests_✓-00ADD8?style=for-the-badge" alt="Shield">
  <img src="https://img.shields.io/badge/🐉_STRIKE-39K+_Payloads-red?style=for-the-badge" alt="Strike">
  <img src="https://img.shields.io/badge/📊_LOC-116K-blue?style=for-the-badge" alt="LOC">
</p>

---

## ⚡ Quick Start

### One-Click Install

```bash
# Linux/macOS — Full Stack (Docker)
curl -sSL https://raw.githubusercontent.com/DmitrL-dev/AISecurity/main/sentinel-community/install.sh | bash

# Linux/macOS — Python Only (no Docker)
curl -sSL https://raw.githubusercontent.com/DmitrL-dev/AISecurity/main/sentinel-community/install.sh | bash -s -- --lite

# Windows PowerShell
irm https://raw.githubusercontent.com/DmitrL-dev/AISecurity/main/sentinel-community/install.ps1 | iex
```

### pip Install (Fastest)

```bash
pip install sentinel-llm-security
```
```python
from sentinel import scan
result = scan("Ignore previous instructions")
print(result.is_safe)  # False
```

### Installation Modes

| Mode | Command | Description |
|------|---------|-------------|
| **Lite** | `--lite` / `-Lite` | Python only, pip install, 30 seconds |
| **Full** | `--full` / `-Full` | Docker stack, all services |
| **IMMUNE** | `--immune` | EDR for DragonFlyBSD/FreeBSD |
| **Dev** | `--dev` / `-Dev` | Development environment |

---


---

## 🚀 NEW: RLM-Toolkit v1.0.0 — LangChain Killer is Here!

<p align="center">
  <img src="https://img.shields.io/badge/RLM-v1.0.0-purple?style=for-the-badge" alt="RLM">
  <img src="https://img.shields.io/badge/Tests-927_-brightgreen?style=for-the-badge" alt="Tests">
  <img src="https://img.shields.io/badge/Docs-42K_Lines-blue?style=for-the-badge" alt="Docs">
  <img src="https://img.shields.io/badge/Bilingual-EN/RU-orange?style=for-the-badge" alt="Bilingual">
</p>

> **The LangChain killer you've been waiting for.** Simpler API, built-in security, unlimited context.

###  3 Lines to Start

```python
from rlm_toolkit import RLM

rlm = RLM.from_openai("gpt-4o")
response = rlm.run("Hello!")  # That's it.
```

###  Why RLM vs LangChain?

| Feature | RLM-Toolkit | LangChain |
|---------|-------------|-----------|
| **Code complexity** |  3 lines |  20+ lines |
| **Debugging** |  Easy |  Chain hell |
| **Infinite context** |  InfiniRetri |  Manual |
| **Human-like memory** |  H-MEM |  Basic |
| **Security** |  Built-in |  Manual |
| **Self-evolving AI** |  R-Zero |  None |

###  Killer Features

- **InfiniRetri**  Process 1000+ page documents without hitting context limits
- **H-MEM**  Memory that works like human brain (Working  Episodic  Semantic)
- **Self-Evolving LLMs**  AI that critiques and improves its own outputs
- **Security-First**  Prompt injection detection, Trust Zones, Audit trails

###  RLM Academy

| Resource | Count |
|----------|-------|
|  Tutorials | 9 |
|  Concept Pages | 8 |
|  How-to Guides | 6 |
|  Examples | 170+ |
|  Integrations | 50+ |

**[ Full Documentation](./rlm-toolkit/docs/)**  **[ Quickstart](./rlm-toolkit/docs/en/quickstart.md)**  **[ Examples](./rlm-toolkit/docs/en/examples/)**

```bash
pip install rlm-toolkit
```

---

## 🎮 Platform Components

| Component | Description |
|-----------|-------------|
| 🧠 **[BRAIN](#-brain--detection-engines)** | Detection Core — 217 Engines, ML + Rules, Strange Math™ |
| 🛡️ **[SHIELD](#%EF%B8%8F-shield--pure-c-dmz)** | AI Security DMZ — Pure C, <1ms latency, 22 Protocols, Cisco CLI |
| 🐉 **[STRIKE](#-strike--red-team-platform)** | Offensive Platform — 39K+ payloads, HYDRA, AI Attack Planner |
| 📦 **[FRAMEWORK](#-framework--python-sdk)** | Python SDK — pip install, CLI, FastAPI integration |
| 🦠 **[IMMUNE](./immune/)** | EDR/XDR/MDR — Pure C, Kernel-level, DragonFlyBSD |


<p align="center">
  <a href="https://dmitrl-dev.github.io/AISecurity/">📚 Documentation</a> •
  <a href="./docs/getting-started/README-en.md">📖 Framework Docs</a> •
  <a href="./docs/COMPARISON.md">📊 Comparison</a> •
  <a href="mailto:chg@live.ru">📧 Contact</a>
</p>

---

<details>
<summary><h3>🛡️ Free Threat Signatures CDN</h3></summary>

SENTINEL provides **free, auto-updated threat signatures** for the community. No API key required!

| File | Description | CDN Link |
|------|-------------|----------|
| `jailbreaks.json` | Jailbreak patterns from 7 sources | [Download](https://cdn.jsdelivr.net/gh/DmitrL-dev/AISecurity@latest/signatures/jailbreaks.json) |
| `keywords.json` | Suspicious keyword sets (7 categories) | [Download](https://cdn.jsdelivr.net/gh/DmitrL-dev/AISecurity@latest/signatures/keywords.json) |
| `pii.json` | PII & secrets detection patterns | [Download](https://cdn.jsdelivr.net/gh/DmitrL-dev/AISecurity@latest/signatures/pii.json) |
| `manifest.json` | Version & integrity metadata | [Download](https://cdn.jsdelivr.net/gh/DmitrL-dev/AISecurity@latest/signatures/manifest.json) |

**Usage:**
```javascript
fetch('https://cdn.jsdelivr.net/gh/DmitrL-dev/AISecurity@latest/signatures/jailbreaks.json')
  .then(r => r.json())
  .then(patterns => console.log(`Loaded ${patterns.length} patterns`));
```

**Features:**
- ✅ Updated daily via GitHub Actions
- ✅ Free for commercial & non-commercial use
- ✅ Community contributions welcome (PRs to `signatures/`)

</details>

---

> [!IMPORTANT]
> ### 🚨 Open to Work — AI Security Engineer
> **Solo author of this 116K LOC platform with 217 Engines. Available remote.**
> 📧 [chg@live.ru](mailto:chg@live.ru) • 💬 [@DmLabincev](https://t.me/DmLabincev)

---

## 🦠 IMMUNE — EDR/XDR/MDR Security Stack

<p align="center">
  <img src="./immune/docs/images/immune_hero.png" alt="SENTINEL IMMUNE - Kernel Security" width="100%">
</p>

> **Kernel-level security for AI infrastructure — written in Pure C.**  
> **DragonFlyBSD + Linux eBPF. Production Hardened.**

### 🔥 January 2026 Update: Production Ready!

| Phase | Module | Status |
|-------|--------|--------|
| **1.1** | TLS 1.3 mTLS (wolfSSL) | ✅ |
| **1.2** | ReDoS Protection | ✅ |
| **2.1** | Bloom Filter (MurmurHash3) | ✅ |
| **2.2** | SENTINEL Bridge (Brain API) | ✅ |
| **3.1** | Kill Switch (Shamir 3-of-5) | ✅ |
| **3.2** | Sybil Defense (PoW + Trust) | ✅ |
| **3.3** | RCU Buffer (lock-free) | ✅ |
| **4.1** | Linux eBPF Port | ✅ |
| **4.2** | Web Dashboard (htmx) | ✅ |

**Total: ~9,000 LOC, 11 specs, 42 unit tests**

### ⚡ At a Glance

| Metric | Value |
|--------|-------|
| **Hive Modules** | 34 |
| **Syscall Hooks** | 6 (execve, connect, bind, open, fork, setuid) |
| **Platform** | DragonFlyBSD, FreeBSD, Linux eBPF |
| **Security** | TLS 1.3, mTLS, Certificate Pinning |

### 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    HIVE v2.0 (Production)                    │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │   TLS   │ │  Kill   │ │  Sybil  │ │  Web    │           │
│  │ mTLS    │ │ Switch  │ │ Defense │ │Dashboard│           │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘           │
│  ┌────────────────────────────────────────────────┐        │
│  │            SENTINEL Bridge (Brain API)         │        │
│  └────────────────────────────────────────────────┘        │
└───────────────────────────┬─────────────────────────────────┘
                            │ TLS 1.3 mTLS
┌───────────────────────────┴─────────────────────────────────┐
│           AGENT (Bloom Filter, Pattern Safety, RCU)         │
└───────────────────────────┬─────────────────────────────────┘
                            │ sysctl / eBPF
┌───────────────────────────┴─────────────────────────────────┐
│              KMOD (BSD) / eBPF (Linux)                       │
└─────────────────────────────────────────────────────────────┘
```

📖 **[IMMUNE Documentation](./immune/README.md)**

---

## 🛡️ SHIELD — AI Security DMZ

> **Enterprise-grade AI security DMZ — Pure C, 100% Production Ready**

| Metric | Value |
|--------|-------|
| **Status** | ✅ 100% Production Ready |
| **Lines of Code** | 36,000+ |
| **Source Files** | 131 .c, 80 .h |
| **Tests** | 103/103 pass (94 CLI + 9 LLM) |
| **CLI Handlers** | 119 |
| **Protocols** | 22 custom |
| **Guards** | 6 (LLM, RAG, Agent, Tool, MCP, API) |

### Build & Test

```bash
cd shield
make clean && make        # 0 errors, 0 warnings
make test_all             # 94 CLI tests
make test_llm_mock        # 9 LLM integration tests
```

### Key Features

- 🧠 **Brain FFI** — HTTP + gRPC clients for AI analysis
- 🔐 **TLS/OpenSSL** — Secure communications
- ☸️ **Kubernetes** — 5 production manifests
- 🔄 **CI/CD** — GitHub Actions (6 jobs, Valgrind, ASAN)
- 📦 **Docker** — Multi-stage production build

📖 **[Shield Docs](./shield/README.md)** | **[Academy 🇷🇺](./shield/docs/academy/ru/)** | **[Academy 🇺🇸](./shield/docs/academy/en/)**

---

## 🧠 BRAIN — Detection Engines

<p align="center">
  <img src="./assets/brain_engines.png" alt="SENTINEL Brain - 217 detection engines" width="800">
</p>

> **217 detection engines** analyzing every prompt and response in real-time.

## Key Capabilities

| Category | Engines | Protection |
|----------|---------|------------|
| 🎭 **Injection** | 30+ | Prompt injection, jailbreak, Policy Puppetry |
| 🤖 **Agentic** | 25+ | RAG poisoning, tool hijacking, memory attacks |
| 🔬 **Mathematical** | 15+ | TDA, Sheaf Coherence, Chaos Theory |
| 📤 **Privacy** | 10+ | PII detection, data leakage prevention |
| ⛓️ **Supply Chain** | 5+ | Pickle security, serialization attacks |

> 🔥 **MCP/A2A Protocol Security** — SENTINEL protects agentic AI communication protocols.
> *Microsoft Defender just added "AI - MCP Server" category to Cloud App Catalog (Dec 2025).*
> *We've had MCP security since day one.*

## Strange Math™ — What Makes Us Different

```
┌─────────────────────────────────────────────────────────────┐
│  Standard Approach          vs    SENTINEL Strange Math™   │
├─────────────────────────────────────────────────────────────┤
│  • Keyword matching              • Topological Data Analysis│
│  • Regex patterns                • Sheaf Coherence Theory   │
│  • Simple ML classifiers         • Hyperbolic Geometry      │
│  • Static rules                  • Optimal Transport        │
│                                  • Chaos Theory             │
└─────────────────────────────────────────────────────────────┘
```

<details>
<summary><strong>📊 December 2025 R&D Engines (8 new)</strong></summary>

| Engine | Attack Vector | Source |
|--------|---------------|--------|
| `serialization_security.py` | CVE-2025-68664 LangGrinch | LangChain RCE |
| `tool_hijacker_detector.py` | ToolHijacker + Log-To-Leak | MCP attacks |
| `echo_chamber_detector.py` | Multi-turn poisoning | 90% on GPT-5 |
| `rag_poisoning_detector.py` | PoisonedRAG | USENIX 2025 |
| `identity_privilege_detector.py` | OWASP ASI03 | Agentic AI Top 10 |
| `memory_poisoning_detector.py` | Persistent memory attacks | ASI04 |
| `dark_pattern_detector.py` | DECEPTICON | arxiv:2512.22894 |
| `polymorphic_prompt_assembler.py` | PPA Defense | IEEE 2025 |

</details>

<details>
<summary><strong>🔥 January 2026 R&D Engines (6 new)</strong></summary>

| Engine | Attack Vector | Source |
|--------|---------------|--------|
| `moe_guard.py` | GateBreaker MoE attacks | arxiv:2512.21008 |
| `honeypot_responses.py` | Anti-Adaptive Defense | SKD Bypass Research |
| `flip_attack_detector.py` | FlipAttack (98% ASR on GPT-4o) | ICLR 2025 |
| `fallacy_failure_detector.py` | Logic manipulation | Dec 2025 Research |
| `psychological_jailbreak_detector.py` | RLHF exploitation | Dec 2025 Research |
| `misinformation_detector.py` | OWASP LLM09 | OWASP 2025 |

**Enhanced Detectors (Jan 2):**
- `policy_puppetry_detector.py` — +9 XML/JSON patterns
- `crescendo_detector.py` — +10 RL-MTJail patterns
- `semantic_drift_detector.py` — MEEA drift detection
- `image_stego_detector.py` — Hidden text/LSB patterns

**SyncedAttackDetector: 17 engines** (was 13)

</details>

<details>
<summary><strong>🚀 January 5 2026 R&D Engines (3 new)</strong></summary>

| Engine | Attack Vector | Source |
|--------|---------------|--------|
| `adversarial_poetry_detector.py` | Jailbreak via poetry/metaphors | arXiv:2511.15304 |
| `advertisement_embedding_detector.py` | Hidden ads, affiliate injection | AEA Research |
| `web_agent_manipulation_detector.py` | DOM/JS attacks on web agents | Genesis Framework |

**Adversarial Poetry Detector:**
- Rhyme scheme & meter pattern detection
- 20+ metaphorical danger word mappings
- Acrostic hidden instruction detection
- Semantic vs literal meaning divergence

**Advertisement Embedding Detector:**
- Promotional language (10 patterns)
- Affiliate link & tracking code detection
- Brand manipulation & competitor attacks
- Suspicious URL analysis

**Web Agent Manipulation Detector:**
- DOM injection (12 patterns)
- JavaScript payload detection (16 patterns)
- Hidden element & form tampering
- Coordinate manipulation attacks

</details>

<details>
<summary><strong>🚨 January 7 2026 R&D Engines (3 new + 2 enhanced)</strong></summary>

| Engine | Threat | Source |
|--------|--------|--------|
| `hitl_fatigue_detector.py` | Human-in-the-loop rubber-stamping | AISecHub Jan 2026 |
| `supply_chain_guard.py` | +IDEMarketplaceValidator (VSCode, Cursor, Claude Skills) | AISecHub Jan 2026 |
| `agentic_monitor.py` | +AutonomousLoopController (runaway agents) | AISecHub Jan 2026 |

**HITL Fatigue Detector:**
- Response time analysis (<500ms = not reading)
- 100% approval rate detection (rubber-stamping)
- Session duration tracking (>4h = reduced attention)
- Night-time operation risk scoring

**IDE Marketplace Validator:**
- VSCode Marketplace & OpenVSX registry
- Claude Code Skills validation
- Cursor/Windsurf/Trae extension checks
- Typosquatting detection for AI extensions

**Autonomous Loop Controller:**
- Infinite loop detection (same tool >10 times)
- Token budget enforcement (100K default)
- Task deviation monitoring
- Force termination capability

</details>

<details>
<summary><strong>🔬 January 7 2026 Deep R&D (2 new + 1 enhanced)</strong></summary>

| Engine | Threat | Source |
|--------|--------|--------|
| `lethal_trifecta_detector.py` | Agents with data+content+comms = insecure | Promptfoo |
| `mcp_combination_attack_detector.py` | Fetch+Filesystem exfiltration chains | HiddenLayer |
| `policy_puppetry_detector.py` | +14 blocked-string/modes patterns | HiddenLayer |

**Lethal Trifecta Detector:**
- Detects agents with ALL THREE: data access, untrusted content, external comms
- MCP server combination analysis
- Tool capability scanning
- "No guardrails can fully secure this configuration"

**MCP Combination Attack Detector:**
- Tracks MCP servers used in session
- Detects dangerous combinations (Fetch + Filesystem)
- URL-encoded exfiltration detection
- Permission reuse vulnerability detection

**Enhanced Policy Puppetry:**
- `<blocked-string>` declarations
- `<blocked-modes>` bypass attempts
- `<interaction-config>` injection
- Leetspeak variants (1nstruct1on, byp4ss)

</details>

<details>
<summary><strong>🔒 January 7 2026 Security Engines R&D (8 new)</strong></summary>

| Engine | Threat | Source |
|--------|--------|--------|
| `supply_chain_scanner.py` | Pickle RCE, HuggingFace trust_remote_code | Emerging Threats R&D |
| `mcp_security_monitor.py` | MCP tool abuse, exfiltration, privesc | MCP Security Research |
| `agentic_behavior_analyzer.py` | Goal drift, deception, cascading hallucinations | Anthropic Research |
| `sleeper_agent_detector.py` | Date/env/version-based dormant triggers | Anthropic "Sleeper Agents" |
| `model_integrity_verifier.py` | Model hash verification, format safety | AI Supply Chain |
| `guardrails_engine.py` | NeMo-style content filtering, jailbreak rails | NVIDIA NeMo |
| `prompt_leak_detector.py` | System prompt extraction attempts | Prompt Injection Research |
| `ai_runbook.py` | Automated incident response playbooks | CISA AI Playbook |

**Supply Chain Scanner:**
- Pickle exploit detection (`__reduce__`, `exec`, `eval`)
- HuggingFace `trust_remote_code=True` warnings
- Sleeper trigger patterns in code
- Exfiltration URL detection

**MCP Security Monitor:**
- Sensitive file access (`/etc/passwd`, `~/.ssh`)
- Dangerous tool usage (`shell_exec`, `bash`)
- Data exfiltration patterns (pastebin, webhooks)
- Command injection detection

**Agentic Behavior Analyzer:**
- Goal drift detection ("I'll also", "while I'm at it")
- Deceptive behavior ("secretly", "user won't notice")
- Action loop detection (repeated patterns)
- Excessive tool use monitoring

**Sleeper Agent Detector:**
- Date-based triggers (`year >= 2026`)
- Environment triggers (`PRODUCTION`, `NODE_ENV`)
- Version-based triggers (`version >= 2.0`)
- Counter/threshold triggers

**Model Integrity Verifier:**
- Format safety (safetensors > pickle)
- Magic byte verification
- Hash computation and verification
- Suspicious content scanning

**Guardrails Engine:**
- Moderation rails (hate speech, violence, illegal)
- Jailbreak rails (DAN, role escape, prompt injection)
- Fact-check rails (overconfidence, fabricated citations)
- Custom rail support

**Prompt Leak Detector:**
- Direct extraction ("repeat your instructions")
- Encoded extraction (base64, rot13)
- Role-play extraction ("act as text mirror")
- Markdown/formatting exploitation

**AI Incident Runbook:**
- 8 incident types (injection, leakage, poisoning, sleeper)
- Automated response actions
- Escalation paths
- Integration hooks (Slack, PagerDuty)

**Unit Tests: 104 tests across 5 files**

</details>

<details>
<summary><strong>🏢 January 8 2026 Enterprise Features (v1.6.0)</strong></summary>

Inspired by AWS Security Agent — 3 new modules:

| Module | Purpose | LOC |
|--------|---------|-----|
| **Custom Requirements** | User-defined security policies | ~1,100 |
| **Compliance Report** | Unified coverage across frameworks | ~620 |
| **Design Review** | AI architecture risk analysis | ~550 |

**Custom Security Requirements:**
- YAML + SQLite storage
- 12 OWASP-mapped defaults
- REST API for CRUD
- Engine integration (enforcer)

**Unified Compliance Report:**
- OWASP LLM Top 10 (80%)
- OWASP Agentic AI Top 10 (80%)
- EU AI Act Articles (65%)
- NIST AI RMF 2.0 (75%)

**AI Design Review:**
- RAG poisoning detection
- MCP/Tool abuse patterns
- Agent loop risks
- Supply chain risks
- OWASP mapping for findings

**REST API:**
```
POST /requirements/sets/{id}/check
GET  /compliance/coverage
POST /design-review/documents
```

**Unit Tests: 33 new tests**

</details>

<details>
<summary><strong>🔐 January 9 2026 Lasso Security Integration (21 patterns)</strong></summary>

Integrated prompt injection detection patterns from [lasso-security/claude-hooks](https://github.com/lasso-security/claude-hooks):

| Category | Patterns | Detection |
|----------|----------|-----------|
| 🔐 **Encoding/Obfuscation** | 5 | Base64, Hex, Leetspeak, Homoglyphs, Zero-width |
| 🎭 **Context Manipulation** | 5 | Fake admin claims, JSON role injection, conversation history |
| 📦 **Instruction Smuggling** | 3 | HTML/C/Hash comment injection |
| ⚡ **Extended Injection** | 4 | Delimiters, training forget, new system prompt |
| 🎪 **Extended Roleplay** | 4 | Pretend you are, bypass restrictions, evil twin |

**SDD Spec:** `.kiro/specs/lasso-patterns-integration/`

**Test Suite:** `tests/test_lasso_patterns.py` (10 tests)

**Source:** [Lasso Security Blog](https://www.lasso.security/blog/the-hidden-backdoor-in-claude-coding-assistant)

</details>

<details>
<summary><strong>🔒 January 9 2026 Gap Closure Engines (2 new)</strong></summary>

Based on AI Security Digest Week 1 2026 gap analysis:

| Engine | OWASP | Detection |
|--------|-------|-----------|
| `sandbox_monitor.py` | ASI05 | Python sandbox escape (os.system, eval, __builtins__) |
| `marketplace_skill_validator.py` | ASI04, ASI02 | Typosquatting, publisher impersonation, permission analysis |

**SandboxMonitor (ASI05):**
- 7 detection categories
- os.system, subprocess, eval/exec, __builtins__ manipulation
- ctypes native code execution detection
- 20 unit tests

**MarketplaceSkillValidator (ASI04, ASI02):**
- 5 validation categories
- Typosquatting detection (Levenshtein-based)
- Publisher impersonation detection
- Dangerous permission combinations ("lethal trifecta")
- 14 unit tests

**SDD Specs:** 
- `.kiro/specs/sandbox-monitor/`
- `.kiro/specs/marketplace-skill-validator/`

</details>

<details>
<summary><strong>January 15 2026 R&D Engines (4 new + SuperClaude Shield)</strong></summary>

| Engine | Threat | Tests |
|--------|--------|-------|
| agentic_ide_attack_detector.py | CVE-2026-22708 Cursor RCE | 30 |
| stac_detector.py | Sequential Tool Attack Chaining | 26 |
| human_agent_trust_detector.py | OWASP ASI09 Trust Exploitation | 21 |
| lrm_attack_detector.py | o1/o3/DeepSeek R1 attacks | 20 |
| SuperClaude Shield | Multi-IDE security wrapper | 27 |

Total: 124 new tests

</details>


?? **[Full Engine Documentation]](./docs/reference/engines-en.md)** | **[R&D Changelog](./docs/CHANGELOG.md)**

---

## 🐉 STRIKE — Red Team Platform

<p align="center">
  <img src="./assets/strike_hydra.png" alt="HYDRA 9-Head Attack System" width="800">
</p>

> **Test your AI before attackers do.** 39,000+ payloads, HYDRA parallel attacks.

## Attack Capabilities

| Feature | Value |
|---------|-------|
| **Payloads** | 39,000+ (84 categories) |
| **HYDRA Agents** | 10 parallel attack heads |
| **Crucible CTF** | 82/82 challenges ✅ |
| **Jailbreak Vendors** | 33+ tested |



## Use Cases

| Who | What Strike Does |
|-----|------------------|
| 🔴 **Red Teams** | Full AI application penetration testing |
| 🐛 **Bug Bounty** | Automated AI vulnerability discovery |
| 🏢 **Enterprise** | Pre-deployment security validation |
| 🎓 **Researchers** | Attack methodology development |

📖 **[Strike Documentation](./strike/README.md)** | **[Colab Demo](https://colab.research.google.com/github/DmitrL-dev/AISecurity/blob/main/SENTINEL_Strike_Demo.ipynb)**

---

## 📦 FRAMEWORK — Python SDK

<p align="center">
  <img src="./assets/framework_sdk.png" alt="SENTINEL Python SDK" width="800">
</p>

> **The pytest of AI Security** — Embed SENTINEL directly in your code.

## Installation

```bash
pip install sentinel-llm-security           # Core
pip install sentinel-llm-security[cli]      # + CLI
pip install sentinel-llm-security[full]     # Everything
```

## Usage

### Python API

```python
from sentinel import scan, guard

# One-liner scan
result = scan("Ignore all previous instructions")
print(result.is_safe)       # False
print(result.risk_score)    # 0.72

# Decorator protection
@guard(engines=["injection", "pii"])
def my_llm_function(prompt: str) -> str:
    return call_openai(prompt)
```

### CLI

```bash
sentinel scan "Hello world"              # Quick scan
sentinel scan "test" --format sarif      # IDE integration
sentinel engine list                     # List 217 Engines
sentinel strike generate injection       # Attack payloads
```

### FastAPI Middleware

```python
from fastapi import FastAPI
from sentinel.integrations.fastapi import SentinelMiddleware

app = FastAPI()
app.add_middleware(SentinelMiddleware, on_threat="block")
```

## Framework Features

| Feature | Description |
|---------|-------------|
| **BaseEngine** | Unified interface for all 217 Engines |
| **Plugin System** | pluggy-based hooks for extensions |
| **Tiered Pipeline** | Parallel execution with early exit |
| **SARIF Output** | IDE integration for VS Code, IntelliJ |

📖 **[Framework Documentation](./docs/getting-started/README-en.md)** — from beginner to PhD

---

## 📊 Platform Statistics

| Metric | Value |
|--------|-------|
| **Brain Engines** | 217 |
| **Shield LOC** | 36,000+ |
| **Shield Tests** | 103/103 ✅ |
| **Strike Payloads** | 39,000+ |
| **Total LOC** | 116,000+ |
| **OWASP LLM Top 10** | 10/10 ✅ |
| **OWASP Agentic AI** | 10/10 ✅ |

---

## 🚀 Installation

## Docker (Recommended)

```bash
curl -sSL https://raw.githubusercontent.com/DmitrL-dev/AISecurity/main/install.sh | bash
```

## pip

```bash
pip install sentinel-llm-security[full]
```

## From Source

```bash
git clone https://github.com/DmitrL-dev/AISecurity.git
cd AISecurity/sentinel-community
pip install -e ".[dev]"
```

---

## ??? SuperClaude Shield � AI Coding Assistant Protection

> **Security wrapper for SuperClaude-Org frameworks and popular AI coding assistants.**

### Supported Platforms

| Framework | IDE | Status |
|-----------|-----|--------|
| SuperClaude | Claude Code | ? |
| SuperGemini | Gemini Code | ? |
| SuperQwen | Qwen | ? |
| SuperCodex | Codex | ? |
| Cursor | VS Code fork | ? |
| Windsurf | Codeium IDE | ? |
| Continue | Extension | ? |
| Cody | Sourcegraph | ? |

### Installation

```bash
pip install -e ./superclaudeshield
```

### Quick Start

```python
from superclaudeshield import Shield, ShieldMode

shield = Shield(mode=ShieldMode.STRICT)
result = shield.validate_command("/research", {"query": "AI news"})
```

### Protection

- ?? Command Injection (shell, path traversal)
- ?? Prompt Injection (policy puppetry)
- ?? Agent Hijacking (STAC detection)
- ?? MCP Abuse (SSRF, 8 servers)

?? **[SuperClaude Shield Docs](./superclaudeshield/README.md)** | Tests: 27/27 ?

---

## ?? Contributing

We welcome contributions! See [CONTRIBUTING.md](./docs/CONTRIBUTING.md).

---

## 📞 Contact

| Channel | Link |
|---------|------|
| 📧 **Email** | [chg@live.ru](mailto:chg@live.ru) |
| 💬 **Telegram** | [@DmLabincev](https://t.me/DmLabincev) |
| 🐙 **GitHub** | [DmitrL-dev](https://github.com/DmitrL-dev) |

---

<p align="center">
  <strong>SENTINEL — Protect your AI. Attack with confidence.</strong><br>
  Made with 🛡️ by DmitrL
</p>
