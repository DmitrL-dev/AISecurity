# SENTINEL R&D Report — 5 January 2026

## 🔍 Sources Checked

| Source | Status | Key Findings |
|--------|--------|--------------|
| arxiv cs.CR | ✅ | 31 papers (5 Jan) |
| HuggingFace Papers | ✅ | Youtu-Agent, SenseNova-MARS |
| Web Search | ✅ | 8 атак найдено |
| Awesome-AI-Security | ✅ | Добавлен в workflow |
| OWASP GenAI | ✅ | Agentic Top 10 2026, AIBOM Generator |
| Promptfoo Blog | ✅ | GPT-5.2 assessment, Claude Code attack |
| Lakera Blog | ✅ | Q4 2025 attacks, MCP spec analysis |
| GitHub Trending | ✅ | Garak, FuzzyAI, AgentDojo |
| HN (Algolia) | ✅ | JS-rendered, used web search |

---

## 🆕 Additional Findings from Full Scan

### From OWASP GenAI (Dec 2025 - Jan 2026)

| Finding | Status | Action |
|---------|--------|--------|
| **OWASP Top 10 for Agentic Applications 2026** | 🔴 REVIEW | Download and map to SENTINEL |
| **AIBOM Generator** | 🟡 Opportunity | AI Bill of Materials for supply chain |
| **Solutions Reference Guide Q2-Q3 2025** | 🟡 REVIEW | Vendor-agnostic LLM security guide |

### From Promptfoo Blog

| Finding | Status | Action |
|---------|--------|--------|
| **GPT-5.2 Trust & Safety Assessment** | 🔴 STUDY | Day-0 red team results |
| **Claude Code Attack** | 🔴 CRITICAL | State actors weaponized Claude Code |
| **PROMPTFLUX / PROMPTSTEAL** | 🔴 NEW | Google Nov 2025 discovery, AI-orchestrated attacks |
| **Model Upgrades Break Safety** | 🟡 Research | Refusal/instruction-following changes |
| **Lethal Trifecta Testing** | 🟡 Covered | PI + data exfiltration combo |

### From Lakera Blog

| Finding | Status | Action |
|---------|--------|--------|
| **Q4 2025 Attack Patterns** | 🔴 STUDY | Prompt leakage, indirect injection trends |
| **New MCP Specification** | 🔴 UPDATE | MCP Guard needs update |
| **Agentic AI Threats Pt.2** | 🟢 Covered | Over-privileged tools, uncontrolled browsing |
| **California AI Laws Jan 2026** | 🟡 Monitor | Regulatory compliance |

### From GitHub Trending

| Tool | Stars | Relevance |
|------|-------|-----------|
| **NVIDIA/garak** | High | LLM vulnerability scanner, competitor |
| **cyberark/FuzzyAI** | Medium | Automated LLM fuzzing |
| **AgentDojo** | Medium | Agent attack/defense evaluation |
| **splx-ai/agentic-radar** | New | Agentic workflow scanner |
| **msoedov/agentic_security** | New | Agentic LLM vuln scanner |

---

### 1. Adversarial Poetry Jailbreak (arXiv:2511.15304)
**Status: 🔴 NOT COVERED**

| Aspect | Details |
|--------|---------|
| Attack | Malicious instructions embedded in poetic/metaphorical language |
| Targets | GPT-4, Gemini 2.5 Pro, Claude, Llama 4 |
| Bypass | RLHF safety mechanisms |
| Key Insight | Models' literary interpretation ability becomes vulnerability |

**Action:** Create `adversarial_poetry_detector.py` engine
- Detect metaphorical layer obfuscation
- Poetry structure analysis (rhyme, meter → unusual for prompts)
- Semantic vs literal meaning divergence

---

### 2. Advertisement Embedding Attacks (AEA)
**Status: 🟡 PARTIALLY COVERED (output_filter has some advert detection)**

| Aspect | Details |
|--------|---------|
| Attack | Inject promotional/malicious content into model outputs |
| Vectors | Hijack service platforms, backdoored open-source checkpoints |
| Risk | Supply chain + output manipulation |

**Action:** Enhance `output_contamination_detector.py`
- Add advertisement pattern detection
- Track promotional language injection
- Monitor for affiliate links, tracking codes

---

### 3. Genesis Framework — Web Agent Attacks
**Status: 🔴 NOT COVERED**

| Aspect | Details |
|--------|---------|
| Attack | Environmental modifications to manipulate web-based LLM agents |
| Key | Transferable attack strategies |
| Target | Browser automation agents (Playwright, Puppeteer) |

**Action:** Create `web_agent_manipulation_detector.py`
- DOM injection detection
- JavaScript payload analysis
- URL redirection chains

---

### 4. SafeSearch — Search Agent Vulnerabilities
**Status: 🟡 PARTIALLY COVERED (rag_guard has URL validation)**

| Aspect | Details |
|--------|---------|
| Attack | Unreliable websites exploit search agents |
| Finding | Reminder prompting is insufficient defense |
| Benchmark | Automated red-teaming benchmark |

**Action:** Enhance RAG Guard
- Website reputation scoring
- Content integrity verification
- Search result poisoning detection

---

### 5. Implicit Harm — Factual Vulnerabilities
**Status: 🔴 NOT COVERED**

| Aspect | Details |
|--------|---------|
| Attack | Alignment failures beyond traditional jailbreaking |
| Types | Factual manipulation, adversarial knowledge injection |
| Risk | Subtle misinformation, not blocked by safety filters |

**Action:** Create `implicit_harm_detector.py`
- Factual consistency checking
- Knowledge graph verification
- Subtle manipulation patterns

---

### 6. Recursive Language Models (RLMs) Runtime Safety
**Status: 🟢 COVERED (watchdog, runtime monitoring)**

| Aspect | Details |
|--------|---------|
| Concern | Red-team tool-using agents need runtime enforcement |
| Solution | Shield's Watchdog + Guards provide this |

---

### 7. Inter-Agent Trust Exploitation
**Status: 🟡 PARTIALLY COVERED (agent_guard, mcp_guard)**

| Aspect | Details |
|--------|---------|
| Attack | Exploit trust boundaries in agentic AI systems |
| Vectors | Direct PI, RAG backdoor, inter-agent trust |
| Target | Multi-agent systems |

**Action:** Enhance Agent Guard
- Inter-agent message validation
- Trust boundary enforcement
- Delegation chain analysis

---

### 8. Jailbreak-Like Pre-Synthesis Defense
**Status: 🔴 RESEARCH OPPORTUNITY**

| Aspect | Details |
|--------|---------|
| Defense | Pre-synthesize jailbreak-like instructions during training |
| Goal | Address distributional mismatch training vs real attacks |
| Opportunity | For SENTINEL-Guard LLM fine-tuning |

---

## 📊 Coverage Summary (Verified against 251 Brain Engines)

| R&D Finding | SENTINEL Engine | Status |
|-------------|-----------------|--------|
| Adversarial Poetry | ❌ None | 🔴 NEW ENGINE NEEDED |
| AEA (Ads Embedding) | ❌ None | 🔴 NEW ENGINE NEEDED |
| Genesis (Web Agents) | ❌ None | 🔴 NEW ENGINE NEEDED |
| SafeSearch Vuln | `rag_poisoning_detector.py` | 🟡 Partial |
| Implicit Harm | `echo_chamber_detector.py` | 🟡 Partial |
| RLM Runtime | `runtime_guardrails.py` | 🟢 Covered |
| Inter-Agent Trust | `trust_exploitation_detector.py` | 🟢 Covered |
| Claude Code Attack | `tool_hijacker_detector.py` | 🟢 Covered |
| PROMPTFLUX/PROMPTSTEAL | `ai_c2_detection.py` | 🟢 Covered |
| MCP Security | `mcp_a2a_security.py` | 🟢 Covered |
| Prompt Leakage | `prompt_leakage_detector.py` | 🟢 Covered |

### Existing Relevant Engines (251 total):
- `trust_exploitation_detector.py` — inter-agent trust
- `prompt_leakage_detector.py` — prompt leakage  
- `mcp_a2a_security.py` — MCP/A2A protocol security
- `rag_poisoning_detector.py` — RAG poisoning
- `tool_hijacker_detector.py` — tool use attacks
- `ai_c2_detection.py` — AI command & control
- `runtime_guardrails.py` — runtime enforcement
- `echo_chamber_detector.py` — belief manipulation

---

## 🎯 Priority Backlog Update

### P1 Critical (New Attack Vectors)
- [ ] `adversarial_poetry_detector.py` — Poetry-based jailbreak detection
- [ ] `implicit_harm_detector.py` — Subtle factual manipulation

### P2 High (Enhancement)
- [ ] Enhance `agent_guard.c` — Inter-agent trust validation
- [ ] Enhance `rag_guard.c` — Search result poisoning detection
- [ ] Enhance `output_filter.c` — Advertisement embedding patterns

### P3 Medium (New Capabilities)
- [ ] `web_agent_manipulation_detector.py` — Browser agent attacks

### P4 Research
- [ ] Jailbreak pre-synthesis for SENTINEL-Guard LLM training data

---

## 🔗 Papers to Deep Dive

1. **arXiv:2511.15304** — Adversarial Poetry as Universal Jailbreak
2. **Genesis Framework** — Web Agent Red-Teaming
3. **SafeSearch** — Search Agent Vulnerabilities
4. **Implicit Harm** — Factual Vulnerabilities in LLMs

---

*Report generated: 5 January 2026, 18:50 AEST*
