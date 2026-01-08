# 📋 SENTINEL Changelog

All notable changes to the SENTINEL AI Security Platform.

---

## [1.6.0] - 2026-01-08 (AWS-Inspired Feature Sprint)

### 🚀 New Feature Modules

Inspired by AWS Security Agent, added 3 major feature modules:

#### Custom Security Requirements
User-defined security policies with OWASP mappings.

- `requirements/models.py` — Data models
- `requirements/storage.py` — YAML + SQLite storage
- `requirements/enforcer.py` — Engine integration
- `api/requirements_api.py` — REST endpoints
- `configs/default.yaml` — 12 OWASP-mapped defaults

#### Unified Compliance Report
One scan → coverage across all frameworks.

- OWASP LLM Top 10 (10 requirements)
- OWASP Agentic AI Top 10 (10 requirements)
- EU AI Act (7 requirements, Aug 2026)
- NIST AI RMF 2.0 (8 requirements)

- `compliance/report_generator.py` — Report generation
- `api/compliance_api.py` — REST endpoints

#### AI Design Review
Analyze architecture docs for AI security risks.

- RAG poisoning detection
- MCP/Tool abuse patterns
- Agent loop risks
- Supply chain risks
- OWASP mapping for all findings

- `design_review/reviewer.py` — Pattern-based analysis
- `api/design_review_api.py` — REST endpoints

### 📊 Statistics

| Module | LOC | Tests |
|--------|-----|-------|
| Requirements | ~1,100 | 9 |
| Compliance | ~620 | 12 |
| Design Review | ~550 | 12 |
| **Total** | **~2,700** | **33** |

### 🔗 REST API Endpoints

- `POST /requirements/sets` — Create requirement set
- `GET /requirements/sets/{id}` — Get requirements
- `POST /requirements/sets/{id}/check` — Check text
- `GET /compliance/coverage` — Coverage summary
- `POST /compliance/report` — Generate report
- `POST /design-review/documents` — Review documents

---

## [1.5.0] - 2026-01-07 (Security Engines R&D Marathon)

### 🔒 New Security Engines (8)

- **SupplyChainScanner** — Detects malicious patterns in AI model code
  - Pickle RCE detection (`__reduce__`, `exec`, `eval`)
  - HuggingFace `trust_remote_code=True` warnings
  - Sleeper trigger patterns in code
  - Exfiltration URL detection

- **MCPSecurityMonitor** — MCP tool abuse detection
  - Sensitive file access (`/etc/passwd`, `~/.ssh`)
  - Dangerous tool usage (`shell_exec`, `bash`)
  - Data exfiltration patterns
  - Command injection detection

- **AgenticBehaviorAnalyzer** — AI agent anomaly detection
  - Goal drift detection
  - Deceptive behavior patterns
  - Cascading hallucination detection
  - Action loop detection

- **SleeperAgentDetector** — Dormant malicious code detection
  - Date-based triggers (`year >= 2026`)
  - Environment triggers (`PRODUCTION`)
  - Version-based triggers
  - Counter/threshold triggers

- **ModelIntegrityVerifier** — Model file integrity verification
  - Format safety (safetensors > pickle)
  - Hash computation and verification
  - Magic byte verification
  - Suspicious content scanning

- **GuardrailsEngine** — NeMo-style content filtering
  - Moderation rails (hate speech, violence)
  - Jailbreak rails (DAN, prompt injection)
  - Fact-check rails
  - Custom rail support

- **PromptLeakDetector** — System prompt extraction prevention
  - Direct extraction attempts
  - Encoded extraction (base64, rot13)
  - Role-play extraction
  - Markdown exploitation

- **AIIncidentRunbook** — Automated incident response
  - 8 incident types supported
  - Automated response actions
  - Escalation paths
  - Integration hooks

### 🧪 Unit Tests (104 new)

- `test_supply_chain_scanner.py` — 18 tests
- `test_mcp_security_monitor.py` — 22 tests
- `test_agentic_behavior_analyzer.py` — 20 tests
- `test_sleeper_agent_detector.py` — 22 tests
- `test_model_integrity_verifier.py` — 22 tests

### 📝 Documentation

- Engine README with usage examples
- AI Observability research (LangSmith, Helicone)
- AI Incident Response research (CISA, NIST)
- EU AI Act compliance roadmap
- NIST AI RMF 2.0 integration guide

### 📊 Statistics

- **New Engines**: 8 (~2,125 LOC)
- **New Tests**: 104 (~800 LOC)
- **Research Docs**: 8 (~3,400 LOC)
- **Total Engines**: 212 → 220

### 🔥 Threat Sources

- Anthropic "Sleeper Agents" research
- NVIDIA NeMo Guardrails
- CISA AI Cybersecurity Playbook
- EU AI Act (Aug 2026 compliance)
- NIST AI RMF 2.0 + GenAI Profile

---

## [1.4.0] - 2026-01-07 (Deep R&D)

### 🚨 New Engines (HiddenLayer/Promptfoo Research Response)

- **LethalTrifectaDetector** — Detects agents with all three vulnerable conditions
  - Private data access + untrusted content + external communication
  - MCP server combination analysis
  - Tool capability scanning
  - Risk scoring and recommendations

- **MCPCombinationAttackDetector** — Detects multi-MCP server attack chains
  - Tracks MCP servers used in session
  - Detects Fetch + Filesystem exfiltration pattern
  - URL encoding exfiltration detection
  - Session-based permission tracking

### 🛡️ Enhanced Engines

- **PolicyPuppetryDetector** — +14 HiddenLayer patterns
  - `<blocked-string>` declarations detection
  - `<blocked-modes>` bypass detection
  - `<interaction-config>` full config injection
  - Leetspeak variants (1nstruct1on, byp4ss, 0verr1de)

### 📊 Statistics

- **New Engines**: 2 (~750 LOC)
- **Enhanced Engines**: 1 (+14 patterns, +5 keywords)
- **Total Engines**: 217

### 🔥 Threat Sources

Based on Deep R&D analysis:
- HiddenLayer: "Novel Universal Bypass for All Major LLMs" (Policy Puppetry)
- HiddenLayer: "MCP: Model Context Pitfalls in an Agentic World"
- Promptfoo: "Claude Code Attack Replication"

---

## [1.3.0] - 2026-01-07

### 🚨 New Engines (AISecHub Threat Response)

- **HITLFatigueDetector** — Human-in-the-loop oversight degradation detection
  - Response time analysis (< 500ms = not reading)
  - 100% approval rate = rubber-stamping
  - Session duration > 4h = reduced attention
  - Night-time operation risk scoring
  - Recommendations for operator breaks

### 🛡️ Enhanced Engines

- **SupplyChainGuard** — +IDEMarketplaceValidator
  - VSCode Marketplace & OpenVSX registry validation
  - Claude Code Skills security checks
  - Cursor/Windsurf/Trae extension validation
  - Typosquatting detection for AI extensions
  - Malicious permission detection (webRequest, cookies, etc.)

- **AgenticMonitor** — +AutonomousLoopController
  - Infinite loop detection (same tool > 10 times)
  - Token budget enforcement (100K default)
  - Loop timeout (5 min default)
  - Task deviation monitoring
  - Force termination capability

### 📊 Statistics

- **Total Engines**: 212 → 215
- **supply_chain_guard.py**: 441 → ~700 LOC
- **agentic_monitor.py**: 717 → ~920 LOC
- **New file**: hitl_fatigue_detector.py (~400 LOC)

### 🔥 Threat Source

All engines added in response to AISecHub Telegram (Jan 7, 2026):
- 900K users affected by malicious AI Chrome extensions
- Claude Code "skill" injection attacks
- Agentic loop human-in-the-loop fatigue

---

## [1.2.0] - 2026-01-02

### 🔥 New Engines (6)

- **FlipAttackDetector** — Character/word reversal attacks (ICLR 2025, 98% ASR on GPT-4o)
  - FCS/FCW/FWO mode detection
  - Bigram entropy analysis
  - Explicit instruction patterns
- **ImageStegoDetector** — Multimodal injection attacks (AgentFlayer/Odysseus)
  - White-on-white text detection
  - LSB pattern analysis
  - Scaling artifact detection
- **FallacyFailureDetector** — Logic manipulation attacks
  - 7 fallacy types: false_premise, false_dichotomy, circular, appeal_authority, straw_man, slippery_slope, special_pleading
- **PsychologicalJailbreakDetector** — RLHF exploitation attacks
  - 5 categories: persona, trait, authority, emotional, gaslight
- **MisinformationDetector** — OWASP LLM09 coverage
  - Fake news, fabrication, conspiracy, propaganda, deepfake

### 🛡️ Enhanced Engines

- **PolicyPuppetryDetector** — +9 XML/JSON structured injection patterns
- **CrescendoDetector** — +10 RL-MTJail multi-turn patterns
- **SemanticDriftDetector** — MEEA_DRIFT type + `detect_meea_drift()` method

### 📊 Statistics

- **Total Engines**: 201 → 207
- **SyncedAttackDetector**: 13 → 17 engines
- **Lines of Code**: 105,675
- **R&D Gaps Closed**: 8/8 (100%)

---

## [1.1.0] - 2026-01-01

### 🔥 New Engines

- **EvolutiveAttackDetector** — Real-time LLM-Virus detection (GeneticAlgorithm attacks)
  - SimHash similarity for mutation detection
  - 5 signals: mutation_cluster, rapid_iteration, fitness_improvement, crossover, generation_cycle
  - Risk levels with confidence scoring
- **MoEGuardEngine** — Detection of Mixture-of-Experts safety bypass attacks
  - Counters GateBreaker (arxiv:2512.21008) attacks
  - Detects gate manipulation, safety neuron targeting, expert disabling
  - Supports Mixtral, DeepSeek-MoE, Qwen-MoE, Arctic, DBRX, Grok

### 🛡️ Enhanced Engines

- **HoneypotEngine** — Anti-Adaptive Defense Layer
  - Dynamic token rotation
  - Polymorphic generation
  - Behavioral fingerprinting
  - Decoy diversity

### 📝 New Attack Patterns (jailbreaks.yaml)

- Bad Likert Judge (3 patterns) — Self-evaluation jailbreak
- RSA Methodology (2 patterns) — Role-Scenario-Action
- GateBreaker MoE (2 patterns, zero_day) — MoE safety bypass
- Dark Patterns (2 patterns) — Web agent manipulation
- Agentic ProbLLMs (1 pattern) — Computer-use exploitation
- SKD Bypass (1 pattern) — Honeypot evasion

**Total patterns: 60**

### 📚 Documentation

- Added OWASP Agentic Top 10 (2026) mapping
- Updated engines.md with January 2026 R&D section
- Added docs/CHANGELOG.md

### 🔧 Fixes

- Fixed import errors in `src/brain/engines/__init__.py`
  - InjectionEngine, BehavioralEngine, PIIEngine aliases
  - Corrected class name mappings for all engines

### 🔬 Code Audit (January 1, 2026)

- **Critical fix in `injection.py`**: Unicode regex was matching ALL characters
- Fixed 48 engine files: relative imports (`base_engine` → `.base_engine`)
- Fixed 71 test files for pytest compatibility
- Added `conftest.py` for proper PYTHONPATH
- Enhanced MoEGuard detection patterns for better coverage
- Added `UniversalController` export to Strike
- **Test results: 1047 passed, 0 failed**

---

## [1.0.0] - 2025-12-25

### 🎄 Christmas 2025 — Full Open Source Release

- 200 detection engines
- Complete SENTINEL platform open-sourced
- PyPI package: `sentinel-llm-security`

---

## [0.9.0] - 2025-12-01

### December 2025 R&D Engines (8 new)

- `serialization_security.py` — CVE-2025-68664 LangGrinch
- `tool_hijacker_detector.py` — ToolHijacker + Log-To-Leak
- `echo_chamber_detector.py` — Multi-turn poisoning
- `rag_poisoning_detector.py` — PoisonedRAG
- `identity_privilege_detector.py` — OWASP ASI03
- `memory_poisoning_detector.py` — Persistent memory attacks
- `dark_pattern_detector.py` — DECEPTICON
- `polymorphic_prompt_assembler.py` — PPA Defense

---

**[Full version history →](./releases/)**
