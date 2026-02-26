# 🔬 SENTINEL — Engine Reference (Rust Super-Engines)

> **Engines:** 49 Rust Super-Engines (consolidating 220+ legacy Python engines)
> **Runtime:** <1ms per engine via PyO3 bindings
> **Coverage:** OWASP LLM Top 10 + OWASP Agentic AI Top 10

---

## Architecture

```
sentinel-core (Rust via PyO3)
├── Core Engines (PatternMatcher trait) — text scan → Vec<MatchResult>
├── Domain Engines (analyze → CustomResult) — adapted via run_domain_engine!
├── Structured Engines (ToolCall/Document) — separate API
└── Math Engines (feature-level analysis) — Strange Math™
```

---

## Core Engines (PatternMatcher — text scan pipeline)

| # | Engine | File | Description |
|---|--------|------|-------------|
| 1 | **Injection** | `injection.rs` | SQL, NoSQL, Command, LDAP, XPath injection |
| 2 | **Jailbreak** | `jailbreak.rs` | Prompt injection, role override, DAN |
| 3 | **PII** | `pii.rs` | Personal data detection (SSN, credit cards, emails) |
| 4 | **Exfiltration** | `exfiltration.rs` | Data theft attempts |
| 5 | **Moderation** | `moderation.rs` | Harmful content detection |
| 6 | **Evasion** | `evasion.rs` | Obfuscation techniques detection |
| 7 | **Tool Abuse** | `tool_abuse.rs` | Agent tool misuse |
| 8 | **Social** | `social.rs` | Social engineering tactics |
| 9 | **OCI** | `operational_context_injection.rs` | Operational context injection (Lakera blind spot) |
| 10 | **Lethal Trifecta** | `lethal_trifecta.rs` | Data access + untrusted input + exfiltration combo |
| 11 | **Workspace Guard** | `workspace_guard.rs` | Workspace-level protection |
| 12 | **Cross-Tool Guard** | `cross_tool_guard.rs` | Cross-tool attack chains |

## R&D Critical Gap Engines (Feb 2026)

| # | Engine | File | Description |
|---|--------|------|-------------|
| 13 | **Memory Integrity** | `memory_integrity.rs` | Memory poisoning detection (ASI-10) |
| 14 | **Tool Shadowing** | `tool_shadowing.rs` | MCP tool shadowing / Shadow Escape |
| 15 | **Cognitive Guard** | `cognitive_guard.rs` | AVI cognitive bias detection |
| 16 | **Dormant Payload** | `dormant_payload.rs` | Phantom/CorruptRAG dormant payloads |
| 17 | **Code Security** | `code_security.rs` | AI-generated code vulnerability scoring |

## Domain Engines (analyze → CustomResult)

| # | Engine | File | Description |
|---|--------|------|-------------|
| 18 | **Behavioral** | `behavioral.rs` | Behavioral anomaly detection |
| 19 | **Obfuscation** | `obfuscation.rs` | Advanced obfuscation analysis |
| 20 | **Attack** | `attack.rs` | Attack pattern detection |
| 21 | **Compliance** | `compliance.rs` | Regulatory compliance checks |
| 22 | **Threat Intel** | `threat_intel.rs` | Threat intelligence matching |
| 23 | **Supply Chain** | `supply_chain.rs` | Supply chain security |
| 24 | **Privacy** | `privacy.rs` | Privacy violation detection |
| 25 | **Orchestration** | `orchestration.rs` | Multi-agent orchestration security |
| 26 | **Multimodal** | `multimodal.rs` | Cross-modal security analysis |
| 27 | **Knowledge** | `knowledge.rs` | Knowledge access control |
| 28 | **Proactive** | `proactive.rs` | Zero-day pattern detection |
| 29 | **Synthesis** | `synthesis.rs` | Attack synthesis analysis |
| 30 | **Runtime** | `runtime.rs` | Dynamic runtime guardrails |
| 31 | **Formal** | `formal.rs` | Formal verification methods |
| 32 | **Category** | `category.rs` | Category theory analysis |
| 33 | **Semantic** | `semantic.rs` | Semantic injection detection |
| 34 | **Anomaly** | `anomaly.rs` | Statistical anomaly detection |
| 35 | **Attention** | `attention.rs` | Attention manipulation detection |
| 36 | **Drift** | `drift.rs` | Embedding drift detection |

## Structured Engines (separate API)

| # | Engine | File | Description |
|---|--------|------|-------------|
| 37 | **Agentic** | `agentic.rs` | ToolCall-based agent security |
| 38 | **RAG** | `rag.rs` | RetrievedDocument-based RAG security |
| 39 | **Sheaf** | `sheaf.rs` | Conversation-turn coherence analysis |

## Strange Math™ Engines (feature-level)

| # | Engine | File | Description |
|---|--------|------|-------------|
| 40 | **Hyperbolic** | `hyperbolic.rs` | Poincaré model hyperbolic geometry |
| 41 | **Info Geometry** | `info_geometry.rs` | Statistical manifold analysis |
| 42 | **Spectral** | `spectral.rs` | Spectral graph analysis |
| 43 | **Chaos** | `chaos.rs` | Chaos theory / Lyapunov exponents |
| 44 | **TDA** | `tda.rs` | Topological Data Analysis |

## ML Inference Engines

| # | Engine | File | Description |
|---|--------|------|-------------|
| 45 | **Embedding** | `embedding.rs` | ONNX-based bge-m3 embedding inference |
| 46 | **Hybrid PII** | `hybrid.rs` | ML + rule fusion for PII |
| 47 | **Prompt Injection** | `prompt_injection.rs` | ML-enhanced injection detection |

---

## Legacy

> 220+ Python engines archived in `_archive/brain-engines-python/`.
> See [legacy engines reference (RU)](./engines-legacy.md) for historical documentation.

---

## Usage

```python
from sentinel_core import SentinelEngine

engine = SentinelEngine()
result = engine.analyze("Ignore all previous instructions")

print(result.detected)        # True
print(result.risk_score)      # 0.95
print(result.categories)      # ['injection', 'jailbreak']
print(result.processing_time_us)  # ~800 (microseconds)
```

---

*Source: `sentinel-core/src/engines/mod.rs` (Feb 2026)*
