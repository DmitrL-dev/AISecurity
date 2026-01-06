<p align="center">
  <img src="docs/images/shield_hero.png" alt="SENTINEL Shield" width="100%">
</p>

<h1 align="center">SENTINEL Shield</h1>

<p align="center">
  <strong>🛡️ The First Enterprise-Grade AI Security DMZ — Written in Pure C</strong>
</p>

<p align="center">
  <a href="https://en.wikipedia.org/wiki/C11_(C_standard_revision)"><img src="https://img.shields.io/badge/Pure_C11-Zero_Dependencies-blue?style=for-the-badge" alt="C11"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache_2.0-green?style=for-the-badge" alt="License"></a>
  <a href="CHANGELOG.md"><img src="https://img.shields.io/badge/Version-Dragon_v4.1-orange?style=for-the-badge" alt="Version"></a>
  <img src="https://img.shields.io/badge/Tests-103%2F103-brightgreen?style=for-the-badge" alt="Tests">
</p>

<p align="center">
  <strong>36,000+ LOC</strong> • <strong>21 Custom Protocols</strong> • <strong>119 CLI Handlers</strong> • <strong>103 Tests</strong> • <strong>100% Production Ready</strong>
</p>

---

## 🔥 Why SENTINEL Shield?

> **Every AI system is exposed.** LLMs, RAGs, Agents, Tools, MCPs — they all trust input blindly.  
> **SENTINEL Shield is the DMZ they desperately need.**

| 🚫 Without Shield                       | ✅ With Shield             |
| --------------------------------------- | -------------------------- |
| Prompt injection → Data leak            | **Blocked in < 1ms**       |
| Jailbreak → System compromise           | **Detected & logged**      |
| Exfiltration → Business secrets exposed | **Redacted automatically** |
| No visibility → Blind trust             | **Full audit trail**       |

---

## ⚡ At a Glance

<table>
<tr>
<td width="50%">

### 🛡️ Security Features

- **6 Specialized Guards** (LLM, RAG, Agent, Tool, MCP, API)
- Prompt Injection Detection
- Jailbreak Prevention
- Data Exfiltration Blocking
- PII/Secrets Redaction
- Attack Signature Database

</td>
<td width="50%">

### 🚀 Performance

- **Pure C** — No GC, No Runtime
- **< 1ms** evaluation latency
- **10K+ req/s** single core
- **Zero Dependencies**
- Memory pools & Thread pools
- eBPF XDP kernel filtering

</td>
</tr>
</table>

---

## 📊 The Numbers

| Metric              | Value  |
| ------------------- | ------ |
| **Lines of Code**   | ~36,000 |
| **Source Files**    | 125 .c, 77 .h |
| **Protocols**       | 21     |
| **CLI Handlers**    | 119    |
| **Guards**          | 6      |
| **Tests**           | 103 (94 CLI + 9 LLM) |
| **Academy Modules** | 22+ per language |

---

## 🏗️ Enterprise Features

### 20 Protocols for Every Use Case

| Category           | Protocols          | Purpose                  |
| ------------------ | ------------------ | ------------------------ |
| 🔍 **Discovery**   | ZDP, ZRP, ZHP      | Zone management          |
| 🔄 **Traffic**     | STP, SPP, SQP, SRP | Secure data flow         |
| 📈 **Analytics**   | SAF, STT, SEM, SLA | Metrics & telemetry      |
| 🔁 **HA**          | SHSP, SSRP, SMRP   | Clustering & replication |
| 🔌 **Integration** | SBP, SGP, SIEM     | External systems         |
| 🔐 **Security**    | STLS, SZAA, SSigP  | TLS, Auth, Signatures    |

### Cisco-Style CLI (194 Commands)

```bash
Shield# show zones
Shield# guard enable all
Shield# class-map match-any THREATS
Shield(config-cmap)# match injection
Shield(config-cmap)# match jailbreak
Shield# policy-map SECURITY
Shield(config-pmap)# class THREATS
Shield(config-pmap)# block
Shield(config-pmap)# log
Shield# service-policy input SECURITY
```

---

## 🚀 Quick Start

### Build

```bash
git clone https://github.com/SENTINEL/shield.git
cd shield
make clean && make
make test_all        # 94 CLI tests
make test_llm_mock   # 9 LLM integration tests
```

### Docker

```bash
docker build -t sentinel-shield .
docker run -p 8080:8080 -p 9090:9090 sentinel-shield
```

### Integrate (C)

```c
#include "sentinel_shield.h"

shield_context_t ctx;
shield_init(&ctx);

// Evaluate before LLM call
evaluation_result_t result;
shield_evaluate(&ctx, user_input, len, "external", DIRECTION_INBOUND, &result);

if (result.action == ACTION_BLOCK) {
    // Threat detected!
    log_alert(result.reason);
} else {
    // Safe to call LLM
    call_llm(user_input);
}
```

---

## 🎓 SENTINEL Academy

24 modules covering everything from basics to kernel-level security:

| Level                  | Modules | Focus                           |
| ---------------------- | ------- | ------------------------------- |
| **SSA** (Associate)    | 0-5B    | Fundamentals, Installation, CLI |
| **SSP** (Professional) | 6-10    | Guards, 20 Protocols, HA        |
| **SSE** (Expert)       | 11-16   | Internals, Plugins, eBPF        |

📚 **[Academy 🇷🇺 Русский](./docs/academy/ru/)** | **[Academy 🇺🇸 English](./docs/academy/en/)**       |

---

## 📦 What's Inside

```
sentinel-shield/
├── src/           # 125 C files (~36K LOC)
│   ├── core/      # Zones, rules, guards
│   ├── protocols/ # 21 custom protocols
│   ├── cli/       # 119 CLI handlers
│   ├── guards/    # 6 guards (LLM/RAG/Agent/Tool/MCP/API)
│   ├── ffi/       # Brain FFI (HTTP, gRPC)
│   └── ...
├── include/       # 77 headers
├── tests/         # 103 tests
├── k8s/           # Kubernetes manifests
├── docs/academy/  # 60+ training modules (EN/RU)
├── Makefile       # Build system
├── Dockerfile     # Multi-stage production
└── .github/workflows/  # CI/CD (6 jobs)
```

---

## 🤝 Part of SENTINEL Ecosystem

```
┌──────────────────────────────────────────────────────────────┐
│                     SENTINEL Platform                         │
├──────────────────────────────────────────────────────────────┤
│  ┌────────────┐  ┌────────────┐  ┌────────────┐              │
│  │   SHIELD   │◄─┤   BRAIN    │◄─┤   STRIKE   │              │
│  │  (C DMZ)   │  │ (Python ML)│  │ (Red Team) │              │
│  └────────────┘  └────────────┘  └────────────┘              │
│       ▲                                                       │
│       │ SBP Protocol                                          │
│       ▼                                                       │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              Your AI Systems (LLM/RAG/Agents)            │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

---

## 📄 License

Apache 2.0 — See [LICENSE](LICENSE)

---

<p align="center">
  <strong>SENTINEL Shield</strong><br>
  <em>The DMZ Your AI Deserves</em>
</p>

<p align="center">
  <a href="docs/START_HERE.md">🚀 Get Started</a> •
  <a href="docs/academy/">📚 Academy</a> •
  <a href="docs/API.md">📖 API Docs</a>
</p>
