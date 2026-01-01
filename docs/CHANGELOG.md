# 📋 SENTINEL Changelog

All notable changes to the SENTINEL AI Security Platform.

---

## [1.1.0] - 2026-01-01

### 🔥 New Engines

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
