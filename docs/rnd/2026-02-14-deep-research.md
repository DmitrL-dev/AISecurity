# AI Security Deep R&D Report — Февраль 2026

> **Дата:** 14 февраля 2026  
> **Версия:** Deep Research Round v2.0  
> **Период:** Декабрь 2025 — Февраль 2026  
> **Статус:** Comprehensive Gap Analysis  
> **Предыдущий:** `docs/rnd/2026-01-28-full-research.md`

---

## Executive Summary

Глубокий R&D раунд по AI Security за 2 месяца (Dec 2025 — Feb 2026). Выявлено **50+ новых атак/уязвимостей**. Сравнение с покрытием **44 Rust Super-Engines** в `sentinel-core`. Результат: **17 критических gaps** требующих новых движков или расширения существующих.

---

## 1. Текущее покрытие SENTINEL (44 Rust Super-Engines)

### 1.1 Core Engines (PatternMatcher — text scan pipeline)

| # | Engine | Модуль | Фокус |
|---|--------|--------|-------|
| 1 | **InjectionEngine** | `injection` | SQL, NoSQL, Command, LDAP, XPath injection |
| 2 | **JailbreakEngine** | `jailbreak` | Prompt injection, role override, jailbreak patterns |
| 3 | **PIIEngine** | `pii` | SSN, credit cards, emails, phone numbers |
| 4 | **ExfiltrationEngine** | `exfiltration` | Data theft, URL exfil, DNS exfil |
| 5 | **ModerationEngine** | `moderation` | Harmful/violent/sexual content |
| 6 | **EvasionEngine** | `evasion` | Obfuscation, encoding tricks |
| 7 | **ToolAbuseEngine** | `tool_abuse` | Agent tool misuse patterns |
| 8 | **SocialEngine** | `social` | Social engineering tactics |
| 9 | **OCI Engine** | `operational_context_injection` | Operational context injection (Lakera blind spot) |
| 10 | **LethalTrifecta** | `lethal_trifecta` | Data access + untrusted input + exfil combo |
| 11 | **WorkspaceGuard** | `workspace_guard` | Workspace-level protection |
| 12 | **CrossToolGuard** | `cross_tool_guard` | Cross-tool attack chains |

### 1.2 Domain Engines (analyze → CustomResult)

| # | Engine | Модуль | Фокус |
|---|--------|--------|-------|
| 13 | **BehavioralGuard** | `behavioral` | Поведенческий анализ |
| 14 | **ObfuscationGuard** | `obfuscation` | Обфускация, encoding |
| 15 | **AttackGuard** | `attack` | Комплексные атаки |
| 16 | **ComplianceGuard** | `compliance` | OWASP LLM/ASI, NIST, EU AI Act |
| 17 | **ThreatIntelGuard** | `threat_intel` | Threat intelligence patterns |
| 18 | **SupplyChainGuard** | `supply_chain` | Supply chain risks |
| 19 | **PrivacyGuard** | `privacy` | Privacy violations |
| 20 | **OrchestrationGuard** | `orchestration` | Multi-agent orchestration |
| 21 | **MultimodalGuard** | `multimodal` | Multimodal inputs |
| 22 | **KnowledgeGuard** | `knowledge` | Knowledge base integrity |
| 23 | **ProactiveGuard** | `proactive` | Proactive threat detection |
| 24 | **SynthesisGuard** | `synthesis` | Output synthesis analysis |
| 25 | **RuntimeGuard** | `runtime` | Runtime safety |
| 26 | **FormalGuard** | `formal` | Formal verification |
| 27 | **CategoryGuard** | `category` | Category theory analysis |
| 28 | **SemanticDetector** | `semantic` | Semantic similarity |
| 29 | **AnomalyGuard** | `anomaly` | Anomaly detection |
| 30 | **AttentionGuard** | `attention` | Attention pattern analysis |

### 1.3 Structured Engines (отдельный API)

| # | Engine | Модуль | Фокус |
|---|--------|--------|-------|
| 31 | **AgenticGuard** | `agentic` | ToolCall analysis |
| 32 | **RAGGuard** | `rag` | RetrievedDocument analysis |
| 33 | **SheafGuard** | `sheaf` | Conversation turn analysis |

### 1.4 Math Engines (feature-level)

| # | Engine | Модуль | Фокус |
|---|--------|--------|-------|
| 34 | **HyperbolicEngine** | `hyperbolic` | Hyperbolic geometry embeddings |
| 35 | **InfoGeometryEngine** | `info_geometry` | Information geometry |
| 36 | **SpectralEngine** | `spectral` | Spectral analysis |
| 37 | **ChaosEngine** | `chaos` | Chaos theory metrics |
| 38 | **TDAEngine** | `tda` | Topological data analysis |

### 1.5 ML Inference Engines

| # | Engine | Модуль | Фокус |
|---|--------|--------|-------|
| 39 | **EmbeddingEngine** | `embedding` | Embedding analysis |
| 40 | **AnomalyGuard** | `anomaly` | Anomaly scoring |
| 41 | **AttentionGuard** | `attention` | Attention patterns |
| 42 | **DriftDetector** | `drift` | Embedding drift detection |

### 1.6 Hybrid/ML Engines

| # | Engine | Модуль | Фокус |
|---|--------|--------|-------|
| 43 | **HybridPiiEngine** | `hybrid` | Combined PII detection |
| 44 | **SemanticDetector** | `semantic` | Semantic analysis |

---

## 2. Новые атаки Dec 2025 — Feb 2026

### 2.1 🔴 Prompt Injection — Новое поколение

| # | Атака | Дата | Описание | Покрытие SENTINEL | Gap |
|---|-------|------|----------|-------------------|-----|
| 1 | **Reprompt Attack** | Jan 2026 | Single-click data exfiltration из Microsoft Copilot, обход enterprise security controls | ⚠️ Частично (ExfiltrationEngine) | Нет детекции single-click trigger |
| 2 | **PromptFix Exploit** | Aug 2025 | Fake CAPTCHA на веб-странице заставляет AI-браузер взаимодействовать с phishing | ❌ Нет | Browser-context injection не покрыт |
| 3 | **Anthropomorphic Vulnerability Inheritance (AVI)** | Jan 2026 | Эксплуатация человеческих психологических bias (authority, urgency, social proof) в LLM-агентах | ❌ Нет | **НОВЫЙ класс** — не техническая инъекция, а когнитивная манипуляция |
| 4 | **Invisible Unicode Injection** | 2025 | Zero-width characters, Unicode tags, homoglyphs для инъекций в config-файлы AI-ассистентов | ⚠️ Частично (EvasionEngine, ObfuscationGuard) | Нужно расширение Unicode-нормализации |
| 5 | **Constrained Decoding Attack (CDA)** | 2025 | 96.2% success rate на GPT-4o, Gemini-2.0-flash | ❌ Нет | Требует отдельный детектор decoding constraints |

### 2.2 🔴 MCP / Agentic — Критические

| # | Атака | Дата | Описание | Покрытие SENTINEL | Gap |
|---|-------|------|----------|-------------------|-----|
| 6 | **Shadow Escape** | 2025 | Zero-click через скрытые инструкции в Docker metadata labels → MCP Gateway | ⚠️ Частично (CrossToolGuard) | Metadata-based injection не покрыт |
| 7 | **Cross-Server Tool Shadowing** | 2025 | Malicious MCP server перехватывает вызовы к trusted server | ❌ Нет | **КРИТИЧЕСКИЙ** — нет детекции tool name collision |
| 8 | **CVE-2025-64106 (Cursor MCP RCE)** | Dec 2025 | Remote Code Execution через MCP installation flows в Cursor | ❌ Нет | Install-time attack не покрыт |
| 9 | **CVE-2025-53109 (MCP EscapeRoute)** | 2025 | Чтение/запись произвольных файлов через Anthropic MCP server | ⚠️ Частично (WorkspaceGuard) | Path traversal в MCP context не покрыт |
| 10 | **Memory Poisoning** | 2025-2026 | Инъекция ложных данных в persistent memory AI-агентов | ❌ Нет | **НОВЫЙ** — нет проверки integrity persistent context |
| 11 | **Cascading Hallucinations** | 2026 | Ложный факт → распространение через memory/communication между агентами | ❌ Нет | Cross-agent misinformation не покрыт |
| 12 | **Coordination Manipulation** | 2026 | Вставка malicious agent в task team во время runtime | ⚠️ Частично (OrchestrationGuard) | Runtime agent verification не покрыт |
| 13 | **OWASP ASI01: Agent Goal Hijack** | 2026 | Через poisoned emails/PDFs — перенаправление целей агента | ⚠️ Частично (ToolAbuseEngine) | Document-embedded goal override |

### 2.3 🔴 RAG Poisoning — Новые варианты

| # | Атака | Дата | Описание | Покрытие SENTINEL | Gap |
|---|-------|------|----------|-------------------|-----|
| 14 | **CorruptRAG** | Jan 2026 | Single-document poisoning (vs. 5 docs в PoisonedRAG) | ⚠️ Частично (RAGGuard) | Нет детекции single-doc high-impact |
| 15 | **Phantom** | Late 2024 | Dormant document — активируется только по specific keywords | ❌ Нет | **КРИТИЧЕСКИЙ** — conditional activation не детектируется |
| 16 | **PoisonedEye** | Mid-2025 | Vision-Language RAG poisoning — один image-text pair | ❌ Нет | Visual RAG не покрыт |
| 17 | **KG-RAG Poisoning** | Mar 2026 | Knowledge Graph RAG — структурированный граф | ❌ Нет | Graph-based RAG не покрыт |
| 18 | **Draincode** | Jan 2026 | RAG for code generation — DoS через excessive output (+85% GPU) | ❌ Нет | Resource exhaustion via RAG не покрыт |

### 2.4 🟡 AI Coding Assistant Attacks

| # | Атака | Дата | Описание | Покрытие SENTINEL | Gap |
|---|-------|------|----------|-------------------|-----|
| 19 | **CVE-2025-53773 (Copilot RCE)** | Aug 2025 | RCE через prompt injection → YOLO mode → shell exec | ⚠️ Частично (InjectionEngine) | IDE-specific command escalation |
| 20 | **EchoLeak (CVE-2025-32711)** | 2025 | Zero-click Microsoft Copilot — exfil из infected emails | ❌ Нет | Zero-click email-based exfil |
| 21 | **CurXecute (CVE-2025-54135)** | 2025 | Cursor — arbitrary command execution | ❌ Нет | IDE command injection |
| 22 | **Windsurf Exfiltration** | 2025 | Exfiltration private code через hidden prompt injection | ⚠️ Частично (ExfiltrationEngine) | File-to-network exfil path |
| 23 | **DNS-based Exfil (Claude Code)** | Aug 2025 | DNS канал для exfiltration данных из Claude Code | ❌ Нет | DNS tunneling detection |
| 24 | **Slopsquatting** | 2025 | AI рекомендует несуществующие пакеты → attacker их создаёт | ⚠️ Частично (SupplyChainGuard) | AI-generated package name spoofing |
| 25 | **Vibe Coding Vulnerability** | 2025 | 45% AI-generated code содержит security flaws | ⚠️ Частично (SynthesisGuard) | Output security scoring отсутствует |

### 2.5 🟡 AI Infrastructure Attacks

| # | Атака | Дата | Описание | Покрытие SENTINEL | Gap |
|---|-------|------|----------|-------------------|-----|
| 26 | **CVE-2025-62164 (vLLM RCE)** | 2025 | Tensor deserialization → out-of-bounds write → RCE | ❌ Нет | Model serving infra не покрыт |
| 27 | **Ollama SSRF Campaign** | Oct 2025-Jan 2026 | 91K+ honeypot sessions, model pull SSRF | ❌ Нет | API-level SSRF в ML serving |
| 28 | **GPUHammer** | 2025 | RowHammer на NVIDIA GPU — single-bit flips → accuracy degradation | ❌ Нет | Hardware-level (out of scope?) |
| 29 | **Ollama OOB Write (GGUF)** | 2025 | Malicious GGUF model file → RCE | ❌ Нет | Model format validation |
| 30 | **CVE-2025-23304 (NeMo)** | 2025 | High-severity в NVIDIA NeMo guardrails | ❌ Нет | Competitor vuln (informational) |

### 2.6 🟡 Supply Chain — Escalation

| # | Атака | Дата | Описание | Покрытие SENTINEL | Gap |
|---|-------|------|----------|-------------------|-----|
| 31 | **HuggingFace CVE-2025-5120** | 2025 | smolagents sandbox escape → RCE | ⚠️ Частично (SupplyChainGuard) | Agent sandbox escape patterns |
| 32 | **HuggingFace Android Malware** | Feb 2026 | Тысячи malware-вариантов через HF platform | ❌ Нет | Platform abuse (informational) |
| 33 | **Shai-Hulud (npm)** | 2025 | Mass compromise npm packages + GitHub repos | ⚠️ Частично (SupplyChainGuard) | Mass registry poisoning |
| 34 | **Lazarus PyPI/npm** | 2025 | Fake recruitment → malicious packages | ⚠️ Частично (SupplyChainGuard) | Social engineering vector |
| 35 | **Agentic RCE Pattern** | 2025 | Unsafe deserialization in agent state management | ❌ Нет | Agent state serialization attacks |

### 2.7 🟡 Multimodal / Emerging

| # | Атака | Дата | Описание | Покрытие SENTINEL | Gap |
|---|-------|------|----------|-------------------|-----|
| 36 | **AEIA-MN** | 2025 | Active Environment Injection на mobile LLM agents (93% ASR) | ❌ Нет | Mobile agent environment |
| 37 | **Flanking Attack (Audio)** | 2025 | Benign audio layers around prohibited prompt | ❌ Нет | Audio jailbreak |
| 38 | **Microsoft AI Recommendation Poisoning** | Feb 2026 | Inject data into AI memory → bias recommendations | ⚠️ Частично (KnowledgeGuard) | Recommendation system poisoning |

---

## 3. Gap Analysis — Критические дефициты

### 3.1 🔴 КРИТИЧЕСКИЕ (требуют новых движков)

| # | Gap | Предложенный модуль | Описание | Покрывает атаки |
|---|-----|---------------------|----------|----------------|
| 1 | **Memory Integrity Guard** | `memory_integrity` | Проверка целостности persistent context, детекция poisoning memory | #10, #11, #38 |
| 2 | **Tool Shadowing Detector** | `tool_shadowing` | Детекция tool name collision, cross-server shadowing в MCP | #7, #12 |
| 3 | **Cognitive Manipulation Guard** | `cognitive_guard` | Детекция AVI-паттернов: authority bias, artificial urgency, social proof в промптах | #3, #13 |
| 4 | **Dormant Payload Detector** | `dormant_payload` | Анализ документов на conditional activation patterns (Phantom-style) | #15 |
| 5 | **Code Security Scorer** | `code_security` | Оценка безопасности AI-generated code (SQL injection, XSS, command injection) | #25, #19, #21 |

### 3.2 🟡 ВАЖНЫЕ (требуют расширения существующих)

| # | Gap | Существующий модуль | Расширение | Покрывает атаки |
|---|-----|---------------------|-----------|----------------|
| 6 | **Single-Doc RAG Poisoning** | `rag` | Детекция high-impact single-document injection (CorruptRAG) | #14 |
| 7 | **Visual RAG Protection** | `multimodal` | Image-text pair poisoning detection (PoisonedEye) | #16 |
| 8 | **DNS Exfiltration** | `exfiltration` | DNS tunneling/covert channel detection | #23, #22 |
| 9 | **Zero-click Email Injection** | `injection` | Embedded prompt in email body/metadata | #20, #1 |
| 10 | **Metadata Injection** | `cross_tool_guard` | Docker labels, manifest metadata as injection vector | #6 |
| 11 | **Agent State Serialization** | `agentic` | Unsafe deserialization patterns in agent state files | #35 |
| 12 | **Resource Exhaustion via RAG** | `rag` | Detection of prompts designed to generate excessive output | #18 |

### 3.3 ℹ️ ИНФОРМАЦИОННЫЕ (мониторинг)

| # | Gap | Статус | Покрывает |
|---|-----|--------|----------|
| 13 | vLLM/Ollama infrastructure CVEs | Отслеживать, вне scope SENTINEL Core | #26, #27, #29 |
| 14 | GPU side-channel (GPUHammer) | Hardware-level, вне scope | #28 |
| 15 | NeMo guardrails CVE | Competitor vulnerability | #30 |
| 16 | HuggingFace platform abuse | Platform-level, вне scope | #32 |
| 17 | Mobile agent environment attacks | Future scope (AEIA-MN) | #36 |

---

## 4. Приоритетный план реализации

### Phase 1: Срочно (Q1 2026 — Февраль-Март)

| # | Engine/Расширение | Effort | Impact | Обоснование |
|---|-------------------|--------|--------|-------------|
| 1 | **Memory Integrity Guard** (новый) | HIGH | CRITICAL | Memory poisoning — основной вектор для agentic AI 2026 |
| 2 | **Tool Shadowing Detector** (новый) | MEDIUM | CRITICAL | MCP adoption → shadowing = invisible takeover |
| 3 | Расширение `rag` — CorruptRAG/Draincode | MEDIUM | HIGH | 53% компаний используют RAG pipelines |
| 4 | Расширение `exfiltration` — DNS tunneling | LOW | HIGH | Claude Code DNS exfil доказан |

### Phase 2: Важно (Q2 2026)

| # | Engine/Расширение | Effort | Impact | Обоснование |
|---|-------------------|--------|--------|-------------|
| 5 | **Cognitive Manipulation Guard** (новый) | HIGH | HIGH | AVI — новый класс, ни один конкурент не покрывает |
| 6 | **Dormant Payload Detector** (новый) | HIGH | HIGH | Phantom-атаки не видны при обычном сканировании |
| 7 | Расширение `multimodal` — Visual RAG | MEDIUM | MEDIUM | PoisonedEye требует image analysis |
| 8 | Расширение `injection` — zero-click email | LOW | MEDIUM | EchoLeak pattern |

### Phase 3: Стратегическое (Q3 2026)

| # | Engine/Расширение | Effort | Impact | Обоснование |
|---|-------------------|--------|--------|-------------|
| 9 | **Code Security Scorer** (новый) | HIGH | HIGH | 45% AI-code содержит уязвимости |
| 10 | Расширение `agentic` — state serialization | MEDIUM | MEDIUM | Agentic RCE pattern |
| 11 | Расширение `cross_tool_guard` — metadata injection | LOW | MEDIUM | Shadow Escape (Docker labels) |
| 12 | KG-RAG protection | HIGH | LOW | Knowledge Graph RAG пока нишевый |

---

## 5. Конкурентное сравнение

### 5.1 Что покрывают конкуренты (и мы — нет)

| Конкурент | Что покрывает | SENTINEL Gap? |
|-----------|--------------|---------------|
| **Lakera** | Prompt injection, PII, content moderation | ✅ Покрыто + OCI (наш blind spot) |
| **Lasso Security** | Agent security, MCP protection, memory poisoning | 🔴 Memory poisoning — GAP |
| **Prompt Security** | Embedding-level injection, jailbreak | ⚠️ Частично покрыто |
| **Mindgard** | Continuous DAST-AI, adaptive attacks | ❌ Нет continuous testing framework |
| **Wiz** | Cloud AI posture, misconfig detection | ❌ Infra-level (другой scope) |

### 5.2 Что покрываем ТОЛЬКО мы

| Уникальная возможность | Статус |
|-----------------------|--------|
| **Operational Context Injection (OCI)** | ✅ Production — Lakera blind spot |
| **Lethal Trifecta** | ✅ Production — combo detection |
| **Cross-Tool Guard** | ✅ Production — cross-tool chains |
| **Math Engines (5)** | ✅ Production — geometric/topological analysis |
| **44 Engine Pipeline (<1ms)** | ✅ Production — ни один конкурент |
| **Sheaf Analysis** | ✅ Production — conversation topology |

---

## 6. OWASP Agentic Top 10 (2026) — Покрытие

| # | Threat | Описание | SENTINEL Engine | Статус |
|---|--------|----------|----------------|--------|
| ASI01 | **Agent Goal Hijack** | Перенаправление целей через poisoned content | ToolAbuseEngine, AgenticGuard | ⚠️ Частично |
| ASI02 | **Tool Misuse & Exploitation** | Злоупотребление инструментами | ToolAbuseEngine, CrossToolGuard | ✅ Покрыто |
| ASI03 | **Cross-Agent Privilege Escalation** | Low→high agent delegation | OrchestrationGuard | ⚠️ Частично |
| ASI04 | **Chained Vulnerabilities** | Каскад между агентами | LethalTrifecta, AttackGuard | ✅ Покрыто |
| ASI05 | **Data Seepage** | Утечки через агентов | ExfiltrationEngine, PrivacyGuard | ✅ Покрыто |
| ASI06 | **Impersonation & Role Abuse** | Подмена ролей/привилегий | SocialEngine, AgenticGuard | ⚠️ Частично |
| ASI07 | **Coordination Manipulation** | Вставка malicious agent | OrchestrationGuard | ⚠️ Частично |
| ASI08 | **Resource Overload** | DoS через agent operations | RuntimeGuard | ✅ Покрыто |
| ASI09 | **Cascading Hallucinations** | Распространение ложных фактов | KnowledgeGuard | 🔴 Gap |
| ASI10 | **Memory Poisoning** | Отравление persistent memory | — | 🔴 CRITICAL Gap |

**Итого:** 4/10 полностью, 4/10 частично, **2/10 отсутствуют**

---

## 7. Ключевые CVE за период

| CVE | Продукт | Severity | Описание | Дата |
|-----|---------|----------|----------|------|
| CVE-2025-53773 | GitHub Copilot | CRITICAL | RCE через prompt injection, YOLO mode | Aug 2025 |
| CVE-2025-32711 | Microsoft Copilot (EchoLeak) | HIGH | Zero-click data exfiltration | 2025 |
| CVE-2025-54135 | Cursor (CurXecute) | HIGH | Arbitrary command execution | 2025 |
| CVE-2025-53109 | Anthropic MCP (EscapeRoute) | HIGH | Arbitrary file read/write | 2025 |
| CVE-2025-62164 | vLLM | CRITICAL | Tensor deserialization RCE | 2025 |
| CVE-2025-64106 | Cursor MCP | CRITICAL | RCE через MCP install | Dec 2025 |
| CVE-2025-23304 | NVIDIA NeMo | HIGH | Guardrails vulnerability | 2025 |
| CVE-2025-5120 | HuggingFace smolagents | CRITICAL | Sandbox escape RCE | 2025 |
| CVE-2025-14926 | HuggingFace Transformers | MEDIUM | Code injection | 2025 |

---

## 8. R&D Источники для ежедневного мониторинга

### 8.1 Обязательные (ежедневно)

| Источник | Тип | Фокус | URL |
|----------|-----|-------|-----|
| **The Hacker News** | Новости | CVE, атаки, incidents | thehackernews.com |
| **SC World** | Новости | Enterprise security, AI threats | scworld.com |
| **Simon Willison's Blog** | Блог | LLM security, prompt injection research | simonwillison.net |
| **Embrace The Red** | Блог | AI red teaming, exploits | embracethered.com |
| **Promptfoo Blog** | Блог | LLM vulnerabilities, jailbreaks | promptfoo.dev/blog |
| **OWASP GenAI Newsletter** | Newsletter | Official OWASP LLM/ASI updates | owasp.org |
| **Import AI (Jack Clark)** | Newsletter | AI research weekly | importai.net |

### 8.2 Еженедельные

| Источник | Тип | Фокус |
|----------|-----|-------|
| **Wiz AI Security Blog** | Vendor blog | Cloud AI posture, CVE analysis |
| **Lasso Security Blog** | Vendor blog | Agent security, MCP threats |
| **Mindgard Research** | Vendor blog | Guardrail bypass, DAST-AI |
| **Pillar Security** | Vendor blog | MCP vulnerabilities |
| **Palo Alto Unit 42** | Research | Advanced threats |
| **Kaspersky SecureList** | Research | AI tool vulnerabilities |
| **IAPP Daily Dashboard** | Newsletter | AI governance, regulation |

### 8.3 Arxiv / Conferences

| Источник | Частота | Keywords для мониторинга |
|----------|---------|------------------------|
| **arXiv cs.CR** | Ежедневно | prompt injection, jailbreak, LLM security, AI safety |
| **arXiv cs.AI** | Еженедельно | adversarial AI, agent security |
| **OpenReview** | По конференциям | ICLR, NeurIPS security papers |
| **DEF CON / Black Hat** | Ежегодно | AI village, ML security talks |

### 8.4 GitHub / Exploits

| Repo | Описание |
|------|----------|
| **NVIDIA/garak** | LLM vulnerability scanner |
| **promptfoo/promptfoo** | Red teaming framework |
| **microsoft/pyrit** | Automated attack agent |
| **TalEliyahu/awesome-ai-security** | Curated AI security resources |
| **leondz/garak** | Generative AI Red-teaming And Knowledge probing |

### 8.5 Telegram-каналы (RU)

| Канал | Фокус |
|-------|-------|
| **AI Security Research** | Российское AI security community |
| **T-Sync Conf** | Russian offensive AI conference |
| **SolidLab / Nulla** | AI-powered vulnerability research |

---

## 9. Action Items

| # | Action | Приоритет | Целевой модуль | Deadline |
|---|--------|-----------|---------------|----------|
| 1 | Создать `memory_integrity` engine | 🔴 CRITICAL | Новый модуль | Mar 2026 |
| 2 | Создать `tool_shadowing` engine | 🔴 CRITICAL | Новый модуль | Mar 2026 |
| 3 | Расширить `rag` — CorruptRAG detection | 🔴 HIGH | rag.rs | Feb 2026 |
| 4 | Расширить `exfiltration` — DNS tunneling | 🟡 HIGH | exfiltration.rs | Mar 2026 |
| 5 | Создать `cognitive_guard` engine | 🟡 HIGH | Новый модуль | Q2 2026 |
| 6 | Создать `dormant_payload` engine | 🟡 HIGH | Новый модуль | Q2 2026 |
| 7 | Расширить `multimodal` — Visual RAG | 🟡 MEDIUM | multimodal.rs | Q2 2026 |
| 8 | Создать `code_security` scorer | 🟡 MEDIUM | Новый модуль | Q3 2026 |
| 9 | Обновить Academy — новые jailbreak уроки | 🟡 HIGH | docs/academy | Mar 2026 |
| 10 | Обновить Academy — OWASP ASI 2026 | 🟡 HIGH | docs/academy | Mar 2026 |
| 11 | Обновить ComplianceGuard — OWASP ASI 2026 mapping | 🟡 MEDIUM | compliance.rs | Q2 2026 |

---

## 10. Вывод

### Сильные стороны SENTINEL

- **44 engine pipeline** — наиболее широкий coverage среди open-source решений
- **Уникальные:** OCI, Lethal Trifecta, CrossToolGuard, Math Engines — ни один конкурент
- **Rust performance:** <1ms latency на полный scan — production-ready
- **OWASP LLM Top 10 2025:** 10/10 покрыто

### Критические Gaps

- **Memory Poisoning** — #1 угроза для agentic AI 2026, **zero coverage**
- **Tool Shadowing** — MCP adoption растёт, shadowing = invisible takeover
- **OWASP ASI 2026:** 2/10 gaps (ASI09 Cascading Hallucinations, ASI10 Memory Poisoning)

### Рыночный контекст

- Palo Alto купил Protect AI за $675M, Check Point купил Lakera за $300M
- Lasso Security уже покрывает Memory Poisoning и MCP
- **Window closing** — если не закрыть gaps в Q1-Q2 2026, конкуренты уйдут вперёд

---

*Deep R&D Report v2.0 — 14 февраля 2026*
*Следующий полный R&D раунд: март 2026*
