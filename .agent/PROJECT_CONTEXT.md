# 🧠 SENTINEL Project Context

> **Purpose:** Quick context restoration for AI assistants in new sessions.
> **Last Updated:** 2025-12-30 (Dec 30: Framework v1.0 PyPI, +8 engines = 200 total, cleanup)

---

## 📁 Project Structure

```
c:\AISecurity\                              ← FULL ENTERPRISE VERSION (root)
├── src\
│   ├── brain\                              ← Python AI Security Core
│   │   ├── engines\                        ← 200 detection engines (~3 MB)
│   │   ├── core\                           ← analyzer, config, health, audit, tenant
│   │   ├── hive\                           ← Threat Hunter, Watchdog, PQC, QRNG
│   │   ├── hybrid_search\                  ← Tree-based attack evolution agent
│   │   ├── config\                         ← jailbreaks.yaml, cognitive_signatures.yaml, YARA
│   │   ├── audit\                          ← 🆕 Prompt Audit module
│   │   ├── rules\                          ← 🆕 Visual Rule Builder
│   │   ├── graph\                          ← 🆕 Intelligence Graph
│   │   ├── workflow\                       ← 🆕 Workflow Automation
│   │   ├── api\                            ← 🆕 API Gateway module
│   │   ├── sdk\                            ← 🆕 Mobile SDK
│   │   ├── gpu\                            ← CUDA acceleration
│   │   └── main.py                         ← gRPC server (port 50051)
│   ├── gateway\                            ← Go HTTP Gateway (16 files)
│   │   ├── cmd\main.go                     ← Entry point
│   │   ├── internal\                       ← auth, brain, oauth, proxy, ratelimit, vault, websocket
│   │   └── pkg\challenge\                  ← PoW anti-DDoS (pow.go)
│   ├── dashboard\                          ← Web UI
│   └── proto\                              ← gRPC protobuf definitions
├── sentinel-community\                     ← OPEN SOURCE (200 engines)
│   ├── src/
│   │   ├── brain/engines/                  ← 200 detection engines
│   │   ├── gateway/                        ← Go HTTP Gateway
│   │   └── sentinel/                       ← 🆕 Framework SDK (PyPI: sentinel-llm-security)
│   ├── strike/                             ← AI Red Team Platform (39K+ payloads)
│   ├── docs/framework/                     ← 🆕 multi-level documentation
│   ├── docs/marketing/                     ← 🆕 X thread, Dev.to articles
│   └── _ctf_workspace/                     ← 🆕 CTF temp files (gitignored)
├── docs\                                   ← 28 documentation files
│   └── reference\engines\                  ← 11 engine category docs (130 KB)
├── tests\                                  ← 19 test directories
│   ├── unit\                               ← 12 unit test files
│   ├── integration\                        ← Integration tests
│   ├── load\                               ← Load testing
│   └── red_team\                           ← Red team attack scenarios
├── benchmarks\                             ← Performance evaluation (9 files)
│   └── injection_dataset.py                ← 59 KB attack dataset
├── deploy\
│   ├── helm\                               ← Helm charts
│   └── kubernetes\                         ← K8s manifests
├── sentinel-driver\                        ← 🆕 WFP KERNEL DRIVER
│   ├── driver\                             ← C driver source (main.c, sentinel_driver.h)
│   ├── sentinel-driver-client\             ← Rust IOCTL client
│   └── test_client\                        ← C test client
├── scripts\                                ← 11 utility scripts
├── certs\                                  ← TLS certificates
└── monitoring\                             ← Prometheus, Grafana configs
```

---

## 🔢 Statistics

| Component               | Files | Size/Lines | Notes                                               |
| ----------------------- | ----- | ---------- | --------------------------------------------------- |
| **Engines**             | 200   | ~4,500 KB  | Detection engines (no tests)                        |
| **Engine Tests**        | 23    | ~200 KB    | In engines/ dir                                     |
| **Gateway (Go)**        | 16    | ~24 MB exe | Compiled binary included                            |
| **Hive**                | 6     | ~56 KB     | quantum, pqcrypto, threat_hunter, watchdog          |
| **Hybrid Search**       | 7     | ~46 KB     | Tree-based attack agent                             |
| **Core**                | 6     | ~50 KB     | analyzer, config, health, audit                     |
| **2025 Innovations 🆕** | 10    | ~3,300 KB  | shapeshifter, tide, mirror, dna, quantum, etc.      |
| **Config**              | 9     | ~26 KB     | YAML configs + YARA rules                           |
| **YARA Rules**          | 3     | ~23 KB     | prompt_injection, advanced_attacks, data_protection |
| **Docs**                | 28    | ~500 KB    | Engine docs, API, guides                            |
| **Unit Tests**          | 155+  | ~300 KB    | All modules covered                                 |
| **Health Check**        | 95/95 | **100%**   | ✅ All engines PASSED, 0 FAILED                     |

---

## 🎯 Engine Categories (170 Total)

| Category                 | Count | Key Engines                                                                                                                                                                                                |
| ------------------------ | ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Classic Detection        | 8     | injection, yara, behavioral, pii, streaming, cascading                                                                                                                                                     |
| NLP / LLM Guard          | 5     | language, prompt_guard, qwen_guard, knowledge, hallucination                                                                                                                                               |
| Strange Math Core        | 9     | tda, sheaf, hyperbolic (2), information_geometry, spectral, math_oracle, morse, optimal_transport                                                                                                          |
| Strange Math Extended    | 8     | category, chaos, differential, geometric, statistical, info_theory, laplacian, firewall                                                                                                                    |
| VLM Protection           | 3     | visual_content, cross_modal, adversarial_image                                                                                                                                                             |
| TTPs.ai Defense          | 10    | rag_guard, probing, session_memory, tool_security, c2, staging, agentic, ape, cognitive, context_poisoning                                                                                                 |
| Advanced 2025            | 6     | attack_2025, adversarial_resistance, multi_agent, institutional, reward_hacking, collusion                                                                                                                 |
| Protocol Security        | 4     | mcp_a2a, model_context_protocol, agent_card, nhi_identity                                                                                                                                                  |
| Proactive                | 10    | synthesizer, hunter, causal, immunity, zero_day, evolution, landscape, compiler, self_play, proactive_defense                                                                                              |
| Data Poisoning           | 4     | bootstrap, temporal, multi_tenant, synthetic_memory                                                                                                                                                        |
| Advanced Research        | 9     | honeypot, canary, intent, kill_chain, runtime, formal_invariants, gradient, compliance, verification                                                                                                       |
| Deep Learning            | 6     | activation, hidden_state, homomorphic, fingerprinting, learning, intelligence                                                                                                                              |
| Meta & XAI               | 2     | meta_judge (32KB), xai                                                                                                                                                                                     |
| Adaptive Behavioral 🆕   | 2     | attacker_fingerprinting, adaptive_markov (Titans/MIRAS)                                                                                                                                                    |
| Research Inventions 🆕   | 32    | Sprint 1-11: 32 engines from R&D inventions with 363 unit tests                                                                                                                                            |
| Supply Chain Security 🆕 | 3     | pickle_security, context_compression, task_complexity (fickling + Claude Code AU2)                                                                                                                         |
| Rule Engine 🆕           | 1     | rule_dsl (NeMo-Guardrails Colang-inspired declarative rules)                                                                                                                                               |
| Dec 30 Deep R&D 🆕       | 8     | serialization_security, tool_hijacker_detector, echo_chamber_detector, rag_poisoning_detector, identity_privilege_detector, memory_poisoning_detector, dark_pattern_detector, polymorphic_prompt_assembler |

---

## 🔧 Key Configuration Files

### `src/brain/config/jailbreaks.yaml` (334 lines)

- 100+ jailbreak patterns with taxonomy
- Attack classes: LLM01-LLM10, AGENT_COLLUSION, MEMORY_POISONING
- Complexity levels: trivial → zero_day
- Multi-language (en, ru, fr, de, ja, zh)

### `src/brain/config/cognitive_signatures.yaml` (207 lines)

- Core identity definition
- Defensive behaviors (refusal, honesty, transparency)
- Kill chain stage recognition (NVIDIA AI Kill Chain)
- Response templates
- EU AI Act Article 13 audit config

### `src/brain/config/yara_rules/` (3 files, 23 KB)

- `prompt_injection.yara` — 11 KB
- `advanced_attacks.yara` — 6 KB
- `data_protection.yara` — 5 KB

---

## 🏗 Architecture

### Brain (Python gRPC Server)

```
main.py → SentinelBrainServicer
├── Analyze()         ← Ingress (user prompt)
├── AnalyzeOutput()   ← Egress (LLM response)
└── AnalyzeStream()   ← Real-time SSE tokens

Components:
├── SentinelAnalyzer  ← Core orchestrator
├── Watchdog          ← Self-healing health checks
├── ThreatHunter      ← Proactive threat detection (60min interval)
├── PQCrypto          ← Post-quantum signatures (Dilithium)
└── QRNG              ← Quantum RNG (hardware or simulated)
```

### Gateway (Go HTTP Server)

```
cmd/main.go → Fiber HTTP
├── internal/auth/       ← JWT + behavioral analysis
├── internal/brain/      ← gRPC client to Brain
├── internal/proxy/      ← LLM provider proxy
├── internal/ratelimit/  ← Token bucket
├── internal/vault/      ← HashiCorp Vault secrets
├── internal/websocket/  ← Real-time WebSocket hub
└── pkg/challenge/       ← PoW anti-DDoS (SHA256)
```

---

## 📊 Benchmark Stats

- **Recall:** 85.1%
- **Precision:** 84.4%
- **F1 Score:** 84.7%
- **Dataset:** 1,815 samples (3 HuggingFace datasets)
- **True Positives:** 1,026 / 1,206

---

## 🔐 Security Features

| Feature             | Implementation                 |
| ------------------- | ------------------------------ |
| Post-Quantum Crypto | Dilithium-3 (NIST ML-DSA)      |
| TLS                 | mTLS with client cert required |
| Secrets             | HashiCorp Vault                |
| Anti-DDoS           | SHA256 Proof-of-Work           |
| Audit               | EU AI Act Article 13 compliant |

---

## 📦 Community vs Enterprise

| Feature               | Community             | Enterprise           |
| --------------------- | --------------------- | -------------------- |
| **Location**          | `sentinel-community/` | `c:\AISecurity\src\` |
| **Engines**           | 19                    | 121                  |
| **Strange Math**      | 3                     | 17                   |
| **Proactive**         | 0                     | 10                   |
| **Protocol Security** | 0                     | 4                    |
| **Tests**             | 1                     | 35+                  |
| **Hive Intelligence** | No                    | Yes                  |
| **PQC/QRNG**          | No                    | Yes                  |

---

## 👤 Owner

**Dmitry Labintsev**

- Email: chg@live.ru
- Telegram: @DmLabincev
- Phone: +7-914-209-25-38

---

## ⚠️ Critical Reminders

1. **ALWAYS check `c:\AISecurity\src\`** for full enterprise code
2. `sentinel-community/` contains the open-source version with all 187 engines
3. Engine count: **187** (updated Dec 29, 2025 — +17 synced attack detectors)
4. README includes "Open to Work" notice at top
5. Strange Math is the unique competitive advantage
6. Proactive engines (attack generation) = enterprise only
7. Hive (ThreatHunter, Watchdog, PQC, QRNG) = enterprise only

---

## 🔗 Key Entry Points

| Purpose            | Path                                         |
| ------------------ | -------------------------------------------- |
| Brain gRPC Server  | `src/brain/main.py`                          |
| Core Analyzer      | `src/brain/core/analyzer.py`                 |
| Meta-Judge         | `src/brain/engines/meta_judge.py`            |
| Injection Engine   | `src/brain/engines/injection.py`             |
| Gateway Main       | `src/gateway/cmd/main.go`                    |
| Jailbreak Patterns | `src/brain/config/jailbreaks.yaml`           |
| Cognitive Config   | `src/brain/config/cognitive_signatures.yaml` |

---

## 📋 Backlog (31 декабря 2025)

### 🔴 High Priority: SENTINEL-Guard LLM

1. Скачать AprielGuard 8B с HuggingFace
2. Тест на наших 12K payloads
3. Начать сбор dataset (~16.5K примеров)
4. Setup QLoRA training на Kaggle

### 🟡 Medium Priority

- [ ] Исправить 404 URLs в updater.py (SecLists-XSS, SecLists-SQLi)
- [ ] Добавить JailbreakBench payloads (~1000)
- [ ] Добавить HarmBench payloads (~500)
