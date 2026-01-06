<p align="center">
  <img src="./docs/images/sentinel_hero.png" alt="🐉 SENTINEL — AI Security Platform" width="100%">
</p>

<h1 align="center">SENTINEL — AI Security Platform</h1>

<p align="center">
  <strong>🛡️ Defense + ⚔️ Offense + 📦 Framework — Complete AI Security Suite</strong><br>
  <strong>Dragon v4.1 • January 2026</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/🧠_BRAIN-212_Engines-brightgreen?style=for-the-badge" alt="Brain">
  <img src="https://img.shields.io/badge/🛡️_SHIELD-103_Tests_✓-00ADD8?style=for-the-badge" alt="Shield">
  <img src="https://img.shields.io/badge/🐉_STRIKE-39K+_Payloads-red?style=for-the-badge" alt="Strike">
</p>

---

## ⚡ Quick Start

```bash
pip install sentinel-llm-security
```
```python
from sentinel import scan
result = scan("Ignore previous instructions")
print(result.is_safe)  # False
```

---

## 🎮 Platform Components

<table>
<tr>
<td width="25%" align="center">
<h3>🧠 BRAIN</h3>
<strong>212 Engines</strong><br>
ML + Rules + Strange Math™
</td>
<td width="25%" align="center">
<h3>🛡️ SHIELD</h3>
<strong>Pure C DMZ</strong><br>
36K LOC • 103 Tests • 100% Ready
</td>
<td width="25%" align="center">
<h3>🐉 STRIKE</h3>
<strong>Red Team</strong><br>
39K+ Payloads • HYDRA
</td>
<td width="25%" align="center">
<h3>📦 SDK</h3>
<strong>Python</strong><br>
pip install • FastAPI
</td>
</tr>
</table>

<table>
<tr>
<td width="20%" align="center" valign="top">
<h3><a href="#-brain--detection-engines">🧠 BRAIN</a></h3>
<strong>Detection Core</strong><br>
201 engines, ML + Rules<br>
Strange Math™
</td>
<td width="20%" align="center" valign="top">
<h3><a href="#%EF%B8%8F-shield--pure-c-dmz">🛡️ SHIELD</a></h3>
<strong>AI Security DMZ</strong><br>
Pure C, <1ms latency<br>
20 Protocols, Cisco CLI
</td>
<td width="20%" align="center" valign="top">
<h3><a href="#-strike--red-team-platform">🐉 STRIKE</a></h3>
<strong>Offensive Platform</strong><br>
39K+ payloads, HYDRA<br>
AI Attack Planner
</td>
<td width="20%" align="center" valign="top">
<h3><a href="#-framework--python-sdk">📦 FRAMEWORK</a></h3>
<strong>Python SDK</strong><br>
pip install, CLI<br>
FastAPI integration
</td>
<td width="20%" align="center" valign="top">
<h3><a href="./immune/">🦠 IMMUNE</a></h3>
<strong>EDR/XDR/MDR</strong><br>
Pure C, Kernel-level<br>
DragonFlyBSD
</td>
</tr>
</table>


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
> **Solo author of this 105K LOC platform with 212 engines. Available remote.**
> 📧 [chg@live.ru](mailto:chg@live.ru) • 💬 [@DmLabincev](https://t.me/DmLabincev)

---

## 🦠 IMMUNE — EDR/XDR/MDR Security Stack

<p align="center">
  <img src="./immune/docs/images/immune_hero.png" alt="SENTINEL IMMUNE - Kernel Security" width="100%">
</p>

> **Kernel-level security for AI infrastructure — written in Pure C.**  
> **DragonFlyBSD first. Zero Python. 6 syscall hooks.**

### 🔥 Why IMMUNE?

| 🚫 Without IMMUNE | ✅ With IMMUNE |
|-------------------|----------------|
| Userspace monitoring → Easily bypassed | **Kernel hooks → Cannot bypass** |
| Python tools → Large attack surface | **Pure C → Minimal attack surface** |
| Single endpoint → No correlation | **XDR → Cross-agent detection** |

### ⚡ At a Glance

| Metric | Value |
|--------|-------|
| **Hive Modules** | 24 |
| **Hive Binary** | 110KB |
| **Syscall Hooks** | 6 (execve, connect, bind, open, fork, setuid) |
| **Platform** | DragonFlyBSD (Linux/Windows planned) |

### 🏗️ Architecture

```
┌─────────────────────────────────────┐
│            HIVE (110KB)             │
│  sentinel | correlate | playbook   │
└─────────────────┬───────────────────┘
                  │ TCP
┌─────────────────┴───────────────────┐
│         AGENT (userspace)           │
└─────────────────┬───────────────────┘
                  │ sysctl
┌─────────────────┴───────────────────┐
│    KMOD (6 syscall hooks)           │
└─────────────────────────────────────┘
```

### 💻 Tested Output

```bash
IMMUNE: [BLOCKED] exec /tmp/test.sh (pid=3158)
IMMUNE: [BLOCKED] connect 127.0.0.1:4444 (pid=3159)
IMMUNE: [AUDIT] open /etc/master.passwd (pid=3160)
IMMUNE: [AUDIT] setuid 0->65534 (pid=3162)
```

### 🔗 Components

| Component | Role |
|-----------|------|
| `sentinel.c` | SENTINEL AI Bridge |
| `correlate.c` | XDR cross-agent correlation |
| `playbook.c` | MDR automated responses |
| `kmod` | Kernel syscall hooks |

📖 **[IMMUNE Documentation](./immune/README.md)**

---

## 🛡️ SHIELD — AI Security DMZ

> **Enterprise-grade AI security DMZ — Pure C, 100% Production Ready**

| Metric | Value |
|--------|-------|
| **Status** | ✅ 100% Production Ready |
| **Lines of Code** | 36,000+ |
| **Source Files** | 125 .c, 77 .h |
| **Tests** | 103/103 pass (94 CLI + 9 LLM) |
| **CLI Handlers** | 119 |
| **Protocols** | 21 custom |
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
  <img src="./assets/brain_engines.png" alt="SENTINEL Brain - 207 Detection Engines" width="800">
</p>

> **212 detection engines** analyzing every prompt and response in real-time.

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

📖 **[Full Engine Documentation](./docs/reference/engines-en.md)** | **[R&D Changelog](./docs/CHANGELOG.md)**

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
| **HYDRA Agents** | 9 parallel attack heads |
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
sentinel engine list                     # List 207 engines
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
| **BaseEngine** | Unified interface for all 201 engines |
| **Plugin System** | pluggy-based hooks for extensions |
| **Tiered Pipeline** | Parallel execution with early exit |
| **SARIF Output** | IDE integration for VS Code, IntelliJ |

📖 **[Framework Documentation](./docs/getting-started/README-en.md)** — from beginner to PhD

---

## 📊 Platform Statistics

| Metric | Value |
|--------|-------|
| **Brain Engines** | 212 |
| **Shield LOC** | 36,000+ |
| **Shield Tests** | 103/103 ✅ |
| **Strike Payloads** | 39,000+ |
| **Total LOC** | 105,000+ |
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

## 🤝 Contributing

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
