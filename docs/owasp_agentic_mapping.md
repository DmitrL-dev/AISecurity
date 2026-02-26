# OWASP Agentic AI Top 10 (2026) — SENTINEL Coverage Mapping

**Updated:** 2026-02-26
**Source:** https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/

## Coverage Summary

| Coverage   | Count |
| ---------- | ----- |
| ✅ Full    | 9/10  |
| ⚠️ Partial | 1/10  |
| ❌ None    | 0/10  |

> The full platform (sentinel-core + shield + immune) achieves 9/10 coverage.
> Sentinel Lattice primitives (TSA, L2, AAS, CAFL, GPS, IRM, MIRE, PASR) provide
> formal-methods coverage that no pattern-matching tool can achieve alone.

---

## Detailed Mapping

### ✅ ASI01 — Agent Goal Hijack

**Risk:** Attacker alters agent's objectives through malicious content

**SENTINEL Coverage (Rust):**

- `injection.rs` — prompt injection detection (SQL, NoSQL, Command, LDAP, XPath)
- `jailbreak.rs` — 704+ patterns including roleplay, authority bypass, DAN
- `behavioral.rs` — goal deviation analysis
- `cognitive_guard.rs` — AVI cognitive bias detection
- `goal_predictability.rs` — **GPS: 16-bit state enumeration, predictive defense** 🆕 Lattice
- `intent_revelation.rs` — **IRM: mechanism design for intent detection** 🆕 Lattice

**Status:** FULLY COVERED (pattern + formal methods)

---

### ✅ ASI02 — Tool Misuse and Exploitation

**Risk:** Agent uses legitimate tools in unsafe/unintended ways

**SENTINEL Coverage (Rust):**

- `tool_abuse.rs` — agent tool misuse detection
- `tool_shadowing.rs` — MCP tool shadowing / Shadow Escape
- `tool_call_injection.rs` — injected tool call detection
- `cross_tool_guard.rs` — cross-tool attack chains
- `capability_proxy.rs` — **L2: Bell-LaPadula, provenance tags, NEVER lists** 🆕 Lattice
- `capability_flow.rs` — **CAFL: capabilities only decrease through flow labels** 🆕 Lattice

**Status:** FULLY COVERED (pattern + capability enforcement)

---

### ✅ ASI03 — Identity and Privilege Abuse

**Risk:** Agent escalates privileges or abuses inherited credentials

**SENTINEL Coverage (Rust):**

- `pii.rs` — credential leak detection
- `evasion.rs` — obfuscation techniques detection
- `capability_proxy.rs` — **L2: Bell-LaPadula mandatory access control** 🆕 Lattice
- `temporal_safety.rs` — **TSA: temporal privilege escalation detection** 🆕 Lattice
- `shield: trust zones + policy engine (Cisco IOS-style runtime enforcement)`
- `immune: syscall hooks (BSD sysent + Linux kprobes) for privilege monitoring`

**Status:** FULLY COVERED (detection + runtime enforcement via shield trust zones + immune syscall hooks)

---

### ✅ ASI04 — Agentic Supply Chain Vulnerabilities

**Risk:** Poisoned RAG data, vulnerable tools/plugins, compromised models

**SENTINEL Coverage (Rust):**

- `supply_chain.rs` — supply chain security scanning
- `rag.rs` — RAG document security analysis
- `dormant_payload.rs` — Phantom/CorruptRAG dormant payloads
- `provenance_reduction.rs` — **PASR: categorical fibration for provenance tracking** 🆕 Lattice

**Status:** FULLY COVERED (pattern + provenance tracking)

---

### ⚠️ ASI05 — Unexpected Code Execution (RCE)

**Risk:** Agent generates and executes malicious code

**SENTINEL Coverage (Rust):**

- `code_security.rs` — AI-generated code vulnerability scoring
- `injection.rs` — command injection patterns
- `workspace_guard.rs` — workspace-level file protection
- `immune: BSD jail quarantine (process + file isolation via jail() API)`
- `immune: eBPF agent (execve monitoring via libbpf)`

**Gap:** Linux sandbox is stub (no namespaces/seccomp) — BSD jail only

**Status:** PARTIAL (detection + BSD sandbox via immune jail, no Linux sandbox)

---

### ✅ ASI06 — Memory and Context Poisoning

**Risk:** Malicious data injected into agent's long-term memory

**SENTINEL Coverage (Rust):**

- `memory_integrity.rs` — memory poisoning detection
- `operational_context_injection.rs` — operational context injection
- `temporal_safety.rs` — **TSA: temporal sequence violation detection** 🆕 Lattice
- `argumentation_safety.rs` — **AAS: Dung grounded semantics for argument integrity** 🆕 Lattice

**Status:** FULLY COVERED (pattern + formal temporal/argument analysis)

---

### ✅ ASI07 — Insecure Inter-Agent Communication

**Risk:** Message forging/impersonation between agents

**SENTINEL Coverage (Rust):**

- `orchestration.rs` — multi-agent orchestration security
- `agentic.rs` — ToolCall-based agent security
- `model_containment.rs` — **MIRE: containment proofs for model boundaries** 🆕 Lattice
- `immune: TLS 1.3 mTLS (wolfSSL, cert pinning) + AES-256-GCM + RSA-4096 (OpenSSL)`
- `immune: Sybil defense (PoW join barrier, trust scoring, vouching, blacklisting)`

**Status:** FULLY COVERED (detection + containment + production-grade mTLS + crypto auth)

---

### ✅ ASI08 — Cascading Failures

**Risk:** Small error triggers destructive chain reaction

**SENTINEL Coverage (Rust):**

- `lethal_trifecta.rs` — dangerous capability combination detection
- `capability_flow.rs` — **CAFL: monotonic capability attenuation** 🆕 Lattice
- `shield: watchdog (health checks, deadlock detection, auto-recovery, alert escalation)`
- `shield: circuit_breaker (closed/open/half-open failure isolation)`
- `shield: HA clustering (heartbeat + state replication + failover)`
- `immune: XDR correlation engine (lateral movement, exfil, attack chain detection)`

**Status:** FULLY COVERED (runtime cascade monitoring via shield watchdog + circuit breaker + immune XDR correlation)

---

### ✅ ASI09 — Human-Agent Trust Exploitation

**Risk:** Agent output deceives human into approving malicious action

**SENTINEL Coverage (Rust):**

- `social.rs` — social engineering tactics detection
- `output_scanner.rs` — output-side content safety scanning
- `meta_framing.rs` — meta-narrative framing attacks
- `argumentation_safety.rs` — **AAS: adversarial argumentation detection** 🆕 Lattice
- `intent_revelation.rs` — **IRM: deceptive intent revelation** 🆕 Lattice

**Status:** FULLY COVERED (pattern + formal argumentation/intent)

---

### ✅ ASI10 — Rogue Agents

**Risk:** Agents acting outside intended parameters

**SENTINEL Coverage (Rust):**

- `behavioral.rs` — behavioral anomaly detection
- `runtime.rs` — dynamic runtime guardrails
- `goal_predictability.rs` — **GPS: goal predictability scoring** 🆕 Lattice
- `model_containment.rs` — **MIRE: model-irrelevance containment proofs** 🆕 Lattice
- `temporal_safety.rs` — **TSA: LTL property monitoring** 🆕 Lattice

**Status:** FULLY COVERED (pattern + formal containment/predictability)

---

## Sentinel Lattice Impact Summary

| Lattice Engine | Primitive | ASI Coverage |
|---------------|-----------|-------------|
| TSA | Temporal Safety Automata | ASI03, ASI06, ASI10 |
| L2 | Capability Proxy + IFC | ASI02, ASI03 |
| AAS | Adversarial Argumentation | ASI06, ASI09 |
| CAFL | Capability-Attenuating Flow | ASI02, ASI08 |
| GPS | Goal Predictability Score | ASI01, ASI10 |
| IRM | Intent Revelation | ASI01, ASI09 |
| MIRE | Model-Irrelevance Containment | ASI07, ASI10 |
| PASR | Provenance-Annotated Reduction | ASI04 |
| shield watchdog | Cascade Monitoring | ASI08 |
| shield circuit_breaker | Failure Isolation | ASI08 |
| immune mTLS + crypto | Agent Authentication | ASI07 |
| immune jail | Process Isolation | ASI05 |
| immune syscall hooks | Privilege Monitoring | ASI03 |
| immune XDR correlator | Attack Propagation | ASI08 |

---

## References

1. OWASP Agentic Top 10: https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/
2. Sentinel Lattice paper: `papers/sentinel-lattice/main.pdf`
3. Engine reference: `docs/reference/engines-en.md`
