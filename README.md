<p align="center">
  <img src="./docs/images/sentinel_hero.png" alt=" SENTINEL - AI Security Platform" width="100%">
</p>

<h1 align="center">SENTINEL - AI Security Platform</h1>

<p align="center">
  <strong> Defense +  Offense +  Framework - Complete AI Security Suite</strong><br>
  <strong>Dragon v4.1 * January 2026</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/_BRAIN-217_Engines-brightgreen?style=for-the-badge" alt="Brain">
  <img src="https://img.shields.io/badge/_SHIELD-113_Tests_-00ADD8?style=for-the-badge" alt="Shield">
  <img src="https://img.shields.io/badge/_STRIKE-39K+_Payloads-red?style=for-the-badge" alt="Strike">
  <img src="https://img.shields.io/badge/_LOC-116K-blue?style=for-the-badge" alt="LOC">
</p>

<p align="center">
  <a href="https://github.com/DmitrL-dev/AISecurity/actions"><img src="https://img.shields.io/github/actions/workflow/status/DmitrL-dev/AISecurity/ci.yml?branch=main&label=CI&style=flat-square" alt="CI"></a>
  <a href="https://pypi.org/project/sentinel-llm-security/"><img src="https://img.shields.io/pypi/v/sentinel-llm-security?style=flat-square&label=PyPI" alt="PyPI"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/License-Apache_2.0-blue?style=flat-square" alt="License"></a>
  <a href="./docs/academy/beginners/en/"><img src="https://img.shields.io/badge/Academy-48_Lessons-orange?style=flat-square" alt="Academy"></a>
</p>

---

> [!IMPORTANT]
> ### Open to Work - AI Security Engineer
> **Solo author of this 116K LOC platform with 217 Engines. Available remote.**
>  [chg@live.ru](mailto:chg@live.ru) *  [@DmLabincev](https://t.me/DmLabincev)

---

<h2 align="center">🎓 New to AI Security?</h2>

<details open>
<summary><h3>🇺🇸 English</h3></summary>

| I want to... | Go to... |
|--------------|----------|
| **Understand the basics** | [What is Prompt Injection?](./docs/academy/beginners/en/01-prompt-injection.md) |
| **Scan my first prompt** | [Quickstart (10 min)](./docs/academy/beginners/en/00-quickstart.md) |
| **Learn OWASP LLM Top 10** | [OWASP Lesson](./docs/academy/beginners/en/03-owasp-llm-top10.md) |
| **Protect my chatbot** | [Protection Guide](./docs/academy/beginners/en/05-protecting-chatbot.md) |

📚 **[Beginner](./docs/academy/beginners/en/)** (11) · 📈 **[Mid-Level](./docs/academy/mid-level/en/)** (16) · 🎓 **[Expert](./docs/academy/expert/en/)** (21)

</details>

<details>
<summary><h3>🇷🇺 Русский</h3></summary>

| Хочу... | Перейти... |
|---------|------------|
| **Понять основы** | [Что такое Prompt Injection?](./docs/academy/beginners/ru/01-prompt-injection.md) |
| **Первый промпт** | [Быстрый старт](./docs/academy/beginners/ru/00-quickstart.md) |
| **OWASP LLM Top 10** | [Урок OWASP](./docs/academy/beginners/ru/03-owasp-llm-top10.md) |
| **Защитить чатбота** | [Руководство](./docs/academy/beginners/ru/05-protecting-chatbot.md) |

📚 **[Начинающий](./docs/academy/beginners/ru/)** (11) · 📈 **[Средний](./docs/academy/mid-level/ru/)** (16) · 🎓 **[Эксперт](./docs/academy/expert/ru/)** (21)

</details>

🔒 **[Security](./SECURITY.md)** · 🏗️ **[Architecture](./docs/ARCHITECTURE.md)** · 📋 **[Changelog](./docs/CHANGELOG.md)**

---

##  Platform Components

| Component | Description | Docs |
|-----------|-------------|------|
|  **[BRAIN](#-brain---detection-engines)** | Detection Core - 217 Engines, ML + Rules, Strange Math™ | [Details](#-brain---detection-engines) |
|  **[SHIELD](#%EF%B8%8F-shield---ai-security-dmz)** | AI Security DMZ - Pure C, <1ms latency, 22 Protocols | [Details](#%EF%B8%8F-shield---ai-security-dmz) |
|  **[STRIKE](#-strike---red-team-platform)** | Offensive Platform - 39K+ payloads, HYDRA | [Details](#-strike---red-team-platform) |
|  **[FRAMEWORK](#-framework---python-sdk)** | Python SDK - pip install, CLI, FastAPI | [Details](#-framework---python-sdk) |
|  **[IMMUNE](#-immune---edrxdrmdr-security-stack)** | EDR/XDR/MDR - Pure C, Kernel-level | [Details](#-immune---edrxdrmdr-security-stack) |
|  **[RLM-Toolkit](#-rlm-toolkit-v121---secure-langchain-alternative)** | Secure LangChain Replacement | [Details](#-rlm-toolkit-v121---secure-langchain-alternative) |
|  **[SuperClaude Shield](#-superclaudeshield---ai-coding-assistant-protection)** | AI Coding Assistant Protection | [Details](#-superclaudeshield---ai-coding-assistant-protection) |

---

<details>
<summary><h2> Quick Start / Быстрый старт</h2></summary>

### pip Install (Fastest / Самый быстрый)

```bash
pip install sentinel-llm-security
```

```python
from sentinel import scan
result = scan("Ignore previous instructions")
print(result.is_safe)  # False
```

---

### One-Click Install / Установка одной командой

```bash
# Linux/macOS - Full Stack (Docker)
curl -sSL https://raw.githubusercontent.com/DmitrL-dev/AISecurity/main/sentinel-community/install.sh | bash

# Linux/macOS - Python Only (no Docker)
curl -sSL https://raw.githubusercontent.com/DmitrL-dev/AISecurity/main/sentinel-community/install.sh | bash -s -- --lite

# Windows PowerShell
irm https://raw.githubusercontent.com/DmitrL-dev/AISecurity/main/sentinel-community/install.ps1 | iex
```

### Installation Modes / Режимы установки

| Mode | Command | Description |
|------|---------|-------------|
| **Lite** | `--lite` / `-Lite` | Python only, pip install, 30 seconds |
| **Full** | `--full` / `-Full` | Docker stack, all services |
| **IMMUNE** | `--immune` | EDR for DragonFlyBSD/FreeBSD |
| **Dev** | `--dev` / `-Dev` | Development environment |

---

### RLM-Toolkit

```bash
pip install rlm-toolkit
```

### From Source / Из исходников

```bash
git clone https://github.com/DmitrL-dev/AISecurity.git
cd AISecurity/sentinel-community
pip install -e ".[dev]"
```

### Docker (Production)

```bash
curl -sSL https://raw.githubusercontent.com/DmitrL-dev/AISecurity/main/install.sh | bash
```

### pip Options

```bash
pip install sentinel-llm-security           # Core
pip install sentinel-llm-security[cli]      # + CLI
pip install sentinel-llm-security[full]     # Everything
pip install sentinel-llm-security[strike]   # Red Team tools
```

</details>

---

<details>
<summary><h3> Free Threat Signatures CDN</h3></summary>

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
-  Updated daily via GitHub Actions
-  Free for commercial & non-commercial use
-  Community contributions welcome (PRs to `signatures/`)

</details>

---

<details>
<summary><h2> RLM-Toolkit v1.2.1 — Secure LangChain Alternative</h2></summary>

<p align="center">
  <img src="https://img.shields.io/badge/RLM-v1.2.1_PRODUCTION-blueviolet?style=for-the-badge" alt="RLM">
  <img src="https://img.shields.io/badge/Tests-1030_PASS-success?style=for-the-badge" alt="Tests">
  <img src="https://img.shields.io/badge/Docs-156_Files-blue?style=for-the-badge" alt="Docs">
  <img src="https://img.shields.io/badge/EN%2FRU-100%25-orange?style=for-the-badge" alt="Bilingual">
  <img src="https://img.shields.io/badge/NIOKR-10%2F10-gold?style=for-the-badge" alt="NIOKR">
</p>

<p align="center">
  <a href="https://pepy.tech/project/rlm-toolkit"><img src="https://static.pepy.tech/badge/rlm-toolkit" alt="Downloads"></a>
  <a href="https://pepy.tech/project/rlm-toolkit"><img src="https://static.pepy.tech/badge/rlm-toolkit/month" alt="Monthly"></a>
  <a href="https://pypi.org/project/rlm-toolkit/"><img src="https://img.shields.io/pypi/v/rlm-toolkit?label=PyPI" alt="PyPI"></a>
</p>

### v1.2.1 Highlights

| Feature | Description |
|---------|-------------|
| **Security** | AES-256-GCM encryption, rate limiting, no XOR fallback |
| **Documentation** | 78 EN + 78 RU = 156 files (10/10 NIOKR) |
| **Tutorials** | 13 step-by-step guides incl. DSPy, Observability, Callbacks |
| **Modules** | 25 fully documented: C³ Crystal, H-MEM, InfiniRetri, MCP Server |

### Why Switch from LangChain?

| Pain Point | LangChain | RLM-Toolkit |
|------------|-----------|-------------|
| **Verbosity** | 20+ lines for basic RAG | 3-5 lines |
| **Debugging** | Chain abstraction hell | Clear stack traces |
| **Context limits** | Manual chunking nightmare | InfiniRetri (unlimited) |
| **Memory** | Simple buffer | H-MEM (brain-like) |
| **Self-improvement** | None | R-Zero auto-optimization |
| **Security** | Add-on afterthought | Built-in from day 1 |

### The Code Speaks For Itself

```python
from rlm_toolkit import RLM

rlm = RLM.from_openai("gpt-4o")
response = rlm.run("Hello!")  # Done.
```

That's it. No chains. No callbacks. No AbstractBaseFactoryManagerInterface.

### Exclusive Features

| Feature | Who Benefits | Description |
|---------|--------------|-------------|
| **InfiniRetri** | 👷 DevOps | Read 1000+ page documents without hitting token limits |
| **H-MEM** | 🔬 Researchers | 4-level hierarchical memory - works like human brain |
| **C³ Crystal** | 🔬 Researchers | 56x context compression (98.2% savings) |
| **MCP Server** | 🛠️ IDE Users | 10-tool integration for VS Code/Antigravity |
| **R-Zero** | 🔬 Researchers | Challenger-Solver architecture auto-improves outputs |
| **Security Suite** | 👶 Everyone | Prompt injection detection, Trust Zones, Full audit trail |

### Documentation

**13 Tutorials** - From "Hello World" to production multi-agent systems  
**170+ Examples** - Battle-tested patterns ready to copy-paste  
**50+ Integrations** - OpenAI, Anthropic, Ollama, all vector stores

<p align="center">
  <a href="./rlm-toolkit/docs/en/quickstart.md"><strong>[Quickstart]</strong></a> |
  <a href="./rlm-toolkit/docs/en/examples/"><strong>[Examples]</strong></a> |
  <a href="./rlm-toolkit/docs/"><strong>[Full Docs]</strong></a> |
  <a href="./rlm-toolkit/docs/en/certification/checklist.md"><strong>[Certification]</strong></a>
</p>

</details>

---

<details>
<summary><h2> BRAIN - Detection Engines</h2></summary>

<p align="center">
  <img src="./assets/brain_engines.png" alt="SENTINEL Brain - 217 detection engines" width="800">
</p>

> **217 detection engines** analyzing every prompt and response in real-time.

### Key Capabilities

| Category | Engines | Protection |
|----------|---------|------------|
|  **Injection** | 30+ | Prompt injection, jailbreak, Policy Puppetry |
|  **Agentic** | 25+ | RAG poisoning, tool hijacking, memory attacks |
|  **Mathematical** | 15+ | TDA, Sheaf Coherence, Chaos Theory |
|  **Privacy** | 10+ | PII detection, data leakage prevention |
|  **Supply Chain** | 5+ | Pickle security, serialization attacks |

>  **MCP/A2A Protocol Security** - SENTINEL protects agentic AI communication protocols.

### Strange Math™ - What Makes Us Different

```
┌─────────────────────────────────────────────────────────────┐
│  Standard Approach          vs    SENTINEL Strange Math™   │
├─────────────────────────────────────────────────────────────┤
│  * Keyword matching              * Topological Data Analysis│
│  * Regex patterns                * Sheaf Coherence Theory   │
│  * Simple ML classifiers         * Hyperbolic Geometry      │
│  * Static rules                  * Optimal Transport        │
│                                  * Chaos Theory             │
└─────────────────────────────────────────────────────────────┘
```

### Benchmarks

| Engine Category | Precision | Recall | F1 | P50 | P99 |
|-----------------|-----------|--------|----|----|-----|
| **Injection** (Tier 1) | 97% | 94% | 95.5% | 3ms | 12ms |
| **Jailbreak** (Tier 2) | 95% | 91% | 93% | 8ms | 25ms |
| **RAG Poisoning** | 92% | 89% | 90.5% | 15ms | 45ms |
| **TDA Analyzer** (Tier 3) | 89% | 96% | 92.4% | 45ms | 120ms |
| **Combined Pipeline** | 94% | 93% | 93.5% | 18ms | 85ms |

> Tested on SENTINEL Strike payloads + internal validation set. P50/P99 = latency percentiles.

📖 **[Full Engine Documentation](./docs/reference/engines-en.md)** | **[R&D Changelog](./docs/CHANGELOG.md)**

</details>

---

<details>
<summary><h2>️ SHIELD - AI Security DMZ</h2></summary>

> **Enterprise-grade AI security DMZ - Pure C, 100% Production Ready**

| Metric | Value |
|--------|-------|
| **Status** |  100% Production Ready |
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

-  **Brain FFI** - HTTP + gRPC clients for AI analysis
-  **TLS/OpenSSL** - Secure communications
-  **Kubernetes** - 5 production manifests
-  **CI/CD** - GitHub Actions (6 jobs, Valgrind, ASAN)
-  **Docker** - Multi-stage production build

 **[Shield Docs](./shield/README.md)** | **[K8s YAMLs](./shield/k8s/)** | **[Academy 🇷🇺](./shield/docs/academy/ru/)** | **[Academy 🇺🇸](./shield/docs/academy/en/)**

</details>

---

<details>
<summary><h2> STRIKE - Red Team Platform</h2></summary>

<p align="center">
  <img src="./assets/strike_hydra.png" alt="HYDRA 9-Head Attack System" width="800">
</p>

> **Test your AI before attackers do.** 39,000+ payloads, HYDRA parallel attacks.

### Attack Capabilities

| Feature | Value |
|---------|-------|
| **Payloads** | 39,000+ (84 categories) |
| **HYDRA Agents** | 10 parallel attack heads |
| **Crucible CTF** | 82/82 challenges  |
| **Jailbreak Vendors** | 33+ tested |

### Use Cases

| Who | What Strike Does |
|-----|------------------|
|  **Red Teams** | Full AI application penetration testing |
|  **Bug Bounty** | Automated AI vulnerability discovery |
|  **Enterprise** | Pre-deployment security validation |
|  **Researchers** | Attack methodology development |

 **[Strike Documentation](./strike/README.md)** | **[Colab Demo](https://colab.research.google.com/github/DmitrL-dev/AISecurity/blob/main/SENTINEL_Strike_Demo.ipynb)**

</details>

---

<details>
<summary><h2> FRAMEWORK - Python SDK</h2></summary>

<p align="center">
  <img src="./assets/framework_sdk.png" alt="SENTINEL Python SDK" width="800">
</p>

> **The pytest of AI Security** - Embed SENTINEL directly in your code.

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

### Framework Features

| Feature | Description |
|---------|-------------|
| **BaseEngine** | Unified interface for all 217 Engines |
| **Plugin System** | pluggy-based hooks for extensions |
| **Tiered Pipeline** | Parallel execution with early exit |
| **SARIF Output** | IDE integration for VS Code, IntelliJ |

 **[Framework Documentation](./docs/getting-started/README-en.md)**

</details>

---

<details>
<summary><h2> IMMUNE - EDR/XDR/MDR Security Stack</h2></summary>

<p align="center">
  <img src="./immune/docs/images/immune_hero.png" alt="SENTINEL IMMUNE - Kernel Security" width="100%">
</p>

> **Kernel-level security for AI infrastructure - written in Pure C.**  
> **DragonFlyBSD + Linux eBPF. Production Hardened.**

### Status

| Phase | Module | Status |
|-------|--------|--------|
| **1.1** | TLS 1.3 mTLS (wolfSSL) |  |
| **1.2** | ReDoS Protection |  |
| **2.1** | Bloom Filter (MurmurHash3) |  |
| **2.2** | SENTINEL Bridge (Brain API) |  |
| **3.1** | Kill Switch (Shamir 3-of-5) |  |
| **3.2** | Sybil Defense (PoW + Trust) |  |
| **3.3** | RCU Buffer (lock-free) |  |
| **4.1** | Linux eBPF Port |  |
| **4.2** | Web Dashboard (htmx) |  |

**Total: ~9,000 LOC, 11 specs, 42 unit tests**

### At a Glance

| Metric | Value |
|--------|-------|
| **Hive Modules** | 34 |
| **Syscall Hooks** | 6 (execve, connect, bind, open, fork, setuid) |
| **Platform** | DragonFlyBSD, FreeBSD, Linux eBPF |
| **Security** | TLS 1.3, mTLS, Certificate Pinning |

 **[IMMUNE Documentation](./immune/README.md)**

</details>

---

<details>
<summary><h2> SuperClaudeShield - AI Coding Assistant Protection</h2></summary>

> **Security wrapper for AI coding assistants and IDE extensions.**

### Supported Platforms

| Framework | IDE | Status |
|-----------|-----|--------|
| SuperClaude | Claude Code |  |
| SuperGemini | Gemini Code |  |
| SuperQwen | Qwen |  |
| SuperCodex | Codex |  |
| Cursor | VS Code fork |  |
| Windsurf | Codeium IDE |  |
| Continue | Extension |  |
| Cody | Sourcegraph |  |

### Quick Start

```bash
pip install -e ./superclaudeshield
```

```python
from superclaudeshield import Shield, ShieldMode

shield = Shield(mode=ShieldMode.STRICT)
result = shield.validate_command("/research", {"query": "AI news"})
```

### Protection

| Threat | Detection |
|--------|-----------|
|  Command Injection | Shell, path traversal |
|  Prompt Injection | Policy puppetry |
|  Agent Hijacking | STAC detection |
|  MCP Abuse | SSRF, 8 servers |

 **[SuperClaude Shield Docs](./superclaudeshield/README.md)** | Tests: 27/27

</details>

---

##  Statistics & Links

| Metric | Value |
|--------|-------|
| **Brain Engines** | 217 |
| **Shield LOC** | 36,000+ |
| **Shield Tests** | 103/103  |
| **Strike Payloads** | 39,000+ |
| **Total LOC** | 116,000+ |
| **OWASP LLM Top 10** | 10/10  |
| **OWASP Agentic AI** | 10/10  |

📋 **[Full Changelog](./docs/CHANGELOG.md)** | 📖 **[Engine Reference](./docs/reference/engines-en.md)**

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](./docs/CONTRIBUTING.md).

---

##  Contact

| Channel | Link |
|---------|------|
|  **Email** | [chg@live.ru](mailto:chg@live.ru) |
|  **Telegram** | [@DmLabincev](https://t.me/DmLabincev) |
|  **GitHub** | [DmitrL-dev](https://github.com/DmitrL-dev) |

---

<p align="center">
  <strong>SENTINEL - Protect your AI. Attack with confidence.</strong><br>
  Made with  by DmitrL
</p>
