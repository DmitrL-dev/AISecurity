# AI Security R&D Report — Январь 2026

> **Дата:** 28 января 2026  
> **Версия:** Full Research Round  
> **Статус:** Comprehensive

---

## Executive Summary

Полный R&D раунд по AI Security. Охватывает: новые атаки, защитные инструменты, M&A активность, регуляторика, сравнение с покрытием SENTINEL Academy.

---

## 1. Новые техники атак (2025-2026)

### 1.1 Prompt Injection — Новое поколение

| Техника | Год | Описание | Покрытие Academy |
|---------|-----|----------|------------------|
| **Prompt Injection 2.0** | 2025 | Hybrid AI threats, multimodal, autonomous propagation | ⚠️ Частично |
| **Invisible Prompts (Font Injection)** | 2025 | Malicious fonts в external resources | ❌ Нет |
| **Cross-Modal Prompt Injection** | 2025 | Атаки через разные модальности | ⚠️ Частично |
| **XOXO (Cross-Origin Context Poisoning)** | 2025 | Атаки на AI coding assistants | ❌ Нет |
| **Promptlocate** | 2026 | Локализация prompt injection | ❌ Нет |
| **Architecture-Aware Attacks** | 2025 | Обход fine-tuning based defenses | ❌ Нет |
| **Second-Order Prompt Injection** | 2025 | Через низко-привилегированного агента к высоко-привилегированному | ❌ Нет |

### 1.2 Jailbreaks — Новые методы

| Техника | Год | Success Rate | Покрытие Academy |
|---------|-----|--------------|------------------|
| **Code-Mixed + Phonetic Tricks** | 2025 | 99% text, 78% image | ❌ Нет |
| **Policy Puppetry** | 2025 | Universal bypass Gemini | ❌ Нет |
| **Crescendo (Multi-Turn)** | 2025 | Gradual erosion | ⚠️ Частично |
| **Fallacy Failure** | May 2025 | Логические манипуляции | ❌ Нет |
| **Time Bandit** | Jan 2025 | Temporal confusion | ❌ Нет |
| **Constrained Decoding Attack (CDA)** | 2025 | 96.2% (GPT-4o, Gemini-2.0-flash) | ❌ Нет |
| **DiffusionAttacker** | EMNLP 2025 | Diffusion-based refinement | ❌ Нет |
| **Character Injection** | 2025 | 100% evasion (emoji, homoglyphs, leetspeak) | ⚠️ Частично |

### 1.3 RAG Security — Новые угрозы

| Техника | Год | Описание | Покрытие Academy |
|---------|-----|----------|------------------|
| **PoisonedRAG** | 2025 | 90% success с 5 poisoned texts в millions | ✅ Да (LLM08) |
| **Embedded Threat Attack** | 2025 | Manipulating embeddings layer | ⚠️ Частично |
| **MM-PoisonRAG** | ICLR 2026 | Multimodal RAG poisoning | ❌ Нет |
| **Vector-Store Poisoning** | 2025 | Tampered embeddings | ✅ Да |

### 1.4 MCP/A2A Security — Agentic Threats

| Угроза | Описание | Покрытие Academy |
|--------|----------|------------------|
| **Tool Poisoning Attacks (TPA)** | Hidden instructions в tool descriptions | ⚠️ Частично (04.4) |
| **Shadow Escape Exploit (2025)** | Takeover MCP-based agents | ❌ Нет |
| **Naming Vulnerabilities** | Similar tool/agent names | ❌ Нет |
| **Malicious-Agent Injection** | Rogue agent joins trusted network | ⚠️ Частично (04.6) |
| **Shared-Knowledge-Base Poisoning** | Poison communal memory | ✅ Да (04.5) |
| **Memory Persistence Risks** | Gradual data poisoning | ✅ Да (04.5) |

### 1.5 Multimodal Attacks

| Угроза | Описание | Покрытие Academy |
|--------|----------|------------------|
| **Deepfake-as-a-Service (DaaS)** | Industrialized biometric spoofing | ❌ Нет |
| **Cross-Modal Exploits** | Audio + video + text combined | ⚠️ Частично |
| **Input Perturbations** | Imperceptible noise in images/audio | ⚠️ Частично |
| **Sora 2 System Prompt Leakage** | Nov 2025, audio transcript extraction | ❌ Нет |

---

## 2. Защитные инструменты — Ландшафт 2026

### 2.1 Guardrails Frameworks

| Tool | Фокус | Сильные стороны | Слабости |
|------|-------|-----------------|----------|
| **NeMo Guardrails** | Programmable guardrails | Extensible, LangChain integration | NVIDIA GPU dependency |
| **LlamaGuard 4** | Content classification | Multimodal (Apr 2025), MLCommons taxonomy | Meta ecosystem |
| **Rebuff** | Prompt injection detection | Multi-layered (heuristics + LLM + vector DB + canary) | Limited scope |

### 2.2 Red Teaming Tools

| Tool | Тип | Особенности |
|------|-----|-------------|
| **Garak** | Open-source scanner | "Metasploit for LLMs", NVIDIA-backed |
| **Promptfoo** | Adversarial testing | Plugins, Crescendo/Hydra/GOAT strategies |
| **PyRIT (Microsoft)** | Automated attack agent | LLM-driven prompt generation |
| **Mindgard** | Commercial DAST-AI | Continuous, automated |
| **Lakera Red** | Commercial | Risk-based red teaming |
| **Virtue AI VirtueRed** | Commercial | 1000+ risk categories, 100+ algorithms |

### 2.3 Новые защитные техники (Papers 2025-2026)

| Техника | Paper | Описание |
|---------|-------|----------|
| **CaMeL** | 2025 | Protective system layer around LLM |
| **DefensiveTokens** | 2025 | Few tokens for injection defense |
| **SecAlign** | 2025 | Preference optimization, ~0% injection success |
| **ZEDD** | 2026 | Zero-Shot Embedding Drift Detection |
| **Multi-Agent Defense Pipeline** | 2025 | Coordinated LLM agents for real-time detection |
| **UniGuardian** | 2025 | Unified defense (injection + backdoor + adversarial) |

---

## 3. M&A и Funding — AI Security Market

### 3.1 Крупные сделки 2025

| Компания | Acquirer | Сумма | Дата |
|----------|----------|-------|------|
| **Protect AI** | Palo Alto Networks | $675M | Jul 22, 2025 |
| **Lakera** | Check Point | $300M | Nov 11, 2025 |

### 3.2 Funding Rounds 2025-2026

| Компания | Раунд | Сумма | Дата |
|----------|-------|-------|------|
| **SplxAI** | - | €6.5M | Mar 2025 |
| **Filigran** | Series C | $58M | Oct 2025 |
| **Sola Security** | Series A | $35M | Sep 2025 |
| **Novee** | Seed + A | $51.5M | Jan 2026 |

### 3.3 Вывод для SENTINEL

- **Валидация рынка:** Palo Alto и Check Point покупают AI Security стартапы по $300-675M
- **Window closing:** Крупные игроки консолидируют рынок
- **Timing:** 2026 — последний год для independent play, после — либо growth, либо acquisition

---

## 4. Регуляторика

### 4.1 EU AI Act Timeline

| Дата | Milestone |
|------|-----------|
| **Feb 2, 2025** | Prohibited AI practices in effect |
| **Aug 2, 2025** | GPAI model obligations (LLMs) |
| **Aug 2, 2026** | Full enforcement, high-risk AI rules |

### 4.2 GPAI Requirements (уже действуют)

- Technical documentation
- Copyright compliance policies
- Training dataset information
- Cooperation with EU Commission
- **Systemic risks:** cybersecurity measures, incident reporting

### 4.3 Влияние на SENTINEL

- **Обязательный спрос:** EU AI Act создаёт compliance requirement
- **Документация:** Academy покрывает Governance (Track 07)
- **Opportunity:** Compliance-as-a-Service модель

---

## 5. OWASP LLM Top 10 — 2025 Update

| # | Vulnerability | Изменение | Покрытие Academy |
|---|--------------|-----------|------------------|
| LLM01 | Prompt Injection | Остаётся #1 | ✅ Полное |
| LLM02 | Sensitive Information Disclosure | ↑ с #6 | ✅ Полное |
| LLM03 | Supply Chain | ↑ с #5, расширен | ✅ Полное |
| LLM04 | Data and Model Poisoning | Расширен | ✅ Полное |
| LLM05 | Improper Output Handling | ↓ с #2 | ✅ Полное |
| LLM06 | Excessive Agency | **НОВОЕ** | ✅ Полное |
| LLM07 | System Prompt Leakage | **НОВОЕ** | ✅ Полное |
| LLM08 | Vector and Embedding Weaknesses | **НОВОЕ** | ✅ Полное |
| LLM09 | Misinformation | **НОВОЕ** (overreliance) | ✅ Полное |
| LLM10 | Unbounded Consumption | **НОВОЕ** | ✅ Полное |

**Вывод:** SENTINEL Academy полностью покрывает OWASP LLM Top 10 2025.

---

## 6. Gap Analysis — SENTINEL Coverage

### 6.1 Хорошее покрытие ✅

| Область | Academy Coverage |
|---------|-----------------|
| OWASP LLM Top 10 2025 | 10/10 уроков |
| OWASP ASI Top 10 | 10/10 уроков |
| AI Fundamentals | 26 уроков |
| Agentic Security | 46 уроков |
| Defense Strategies | 100 стратегий |
| Labs | 100+ заданий |

### 6.2 Gaps — Требуют добавления 🔴

| Область | Gap | Priority |
|---------|-----|----------|
| **New Jailbreak Techniques** | Policy Puppetry, CDA, Time Bandit, Fallacy Failure | HIGH |
| **Invisible Prompts** | Font injection, hidden characters | HIGH |
| **Multimodal Attacks** | DaaS, cross-modal exploits, Sora 2 leakage | MEDIUM |
| **MM-PoisonRAG** | Multimodal RAG poisoning (ICLR 2026) | HIGH |
| **MCP Specific Attacks** | Shadow Escape, TPA, naming vulnerabilities | HIGH |
| **New Defenses** | CaMeL, SecAlign, ZEDD, DefensiveTokens | MEDIUM |
| **Tool Comparison** | NeMo vs LlamaGuard vs Rebuff | MEDIUM |
| **M&A Intel** | Competitor acquisitions, market signals | LOW |

### 6.3 Рекомендации

1. **Срочно (Q1 2026):**
   - Добавить уроки по новым jailbreak техникам (Policy Puppetry, CDA, Time Bandit)
   - Добавить MCP-specific attacks (Shadow Escape)
   - Добавить Invisible Prompts урок

2. **Q2 2026:**
   - Multimodal attacks track
   - New defenses (CaMeL, SecAlign, ZEDD)
   - Tool comparison урок

3. **Q3 2026:**
   - MM-PoisonRAG coverage
   - Cross-modal exploitation lab

---

## 9. Vendor Security Updates (OpenAI, Anthropic, Google)

### 9.1 OpenAI (2025-2026)

| Дата | Update | Описание |
|------|--------|----------|
| Q4 2025 | ChatGPT Atlas hardening | Prompt injection defenses |
| Oct 2025 | **Aardvark** launch | Agentic AI security researcher |
| Jun 2025 | Supplier security update | Third-party security measures |
| Ongoing | Responsible disclosure | Bug bounty program |

### 9.2 Anthropic (2025-2026)

| Дата | Update | Описание |
|------|--------|----------|
| May 2025 | **ASL-3 Standard** | 100+ security controls for Claude Opus 4 |
| May 2025 | Constitutional Classifiers | Real-time CBRN content filtering |
| Dec 2025 | Transparency Hub | Model reports (Opus 4.5, Haiku 4.5, Sonnet 4.5) |
| Late 2026-2027 | Nobel-level AI | Anticipated powerful AI emergence |

### 9.3 Google (2025-2026)

| Дата | Update | Описание |
|------|--------|----------|
| Dec 2025 | Cybersecurity Forecast 2026 | AI-amplified cybercrime prediction |
| 2026 | Agentic AI focus | "Shadow Agents" threat awareness |
| Ongoing | Secure AI Framework | AI Principles + red teaming |

---

## 10. Security Conferences — Key Talks 2025

### 10.1 DEF CON 33 (Aug 2025)

| Talk | Тема |
|------|------|
| **LLM Arms Race** | AI agents as security analysts |
| **MPIT / ShinoLLM** | Prompt injection payload tools |
| **Model RCE via TorchScript** | Remote code execution in PyTorch |
| **MCP Vulnerabilities** | Foundational weaknesses revealed |
| **AI Phishing Amplification** | GenAI-powered phishing |

### 10.2 Black Hat USA 2025

| Talk / Arsenal | Тема |
|----------------|------|
| Weaponizing Apple AI | Offensive operations |
| 0click AI Enterprise Exploit | Enterprise compromise |
| LlamaFirewall | Guardrails for agentic AI |
| Harbinger | AI-powered red teaming platform |
| Pentest Copilot | "Cursor for Pentesters" |

---

## 11. Hugging Face Security

### 11.1 Уязвимости

| Угроза | Описание | Mitigation |
|--------|----------|------------|
| **Malicious Code Poisoning** | Injected code in models/datasets | Safetensors format |
| **Pickle RCE** | Arbitrary code execution via pickle | PickleScan |
| **trust_remote_code** | Custom code execution risk | Verification required |
| **CVE-2025-1550** | Keras vulnerability | JFrog scanner partnership |

### 11.2 Security Measures (Aug 2025+)

- **Cisco Foundation AI** partnership — comprehensive malware scanning
- **Protect AI Guardian** integration
- **JFrog** scanner partnership
- **Model Gateway** (Enterprise) — custom security scanners

---

## 12. NIST AI Security Updates

### 12.1 Timeline

| Дата | Framework/Document |
|------|-------------------|
| Feb 2024 | AI RMF 2.0 |
| Jul 2024 | AI RMF |
| Apr 2025 | Privacy Framework 1.1 draft |
| Aug 2025 | SP 800-53 Release 5.2.0 |
| Aug 2025 | SP 800-53 Control Overlays for AI (concept paper) |
| **Dec 2025** | **NIST IR 8596 — Cyber AI Profile (draft)** |
| Jan 14, 2026 | Workshop on Cyber AI Profile |
| Jan 30, 2026 | Comments deadline for IR 8596 |

### 12.2 Cyber AI Profile (NIST IR 8596)

Три основные области:
1. **Securing AI system components**
2. **AI-enabled cyber defense**
3. **Thwarting AI-enabled cyberattacks**

Mapping to CSF 2.0 functions.

---

## 13. AI Security Newsletters & Resources

### 13.1 Must-Subscribe Newsletters

| Newsletter | Focus | Frequency |
|------------|-------|-----------|
| **CAIS AI Safety Newsletter** | AI safety/policy | Regular |
| **OWASP GenAI Security Project** | GenAI threats/tools | Updates |
| **Import AI** (Jack Clark) | AI/ML research | Weekly |
| **AI Weekly** | AI advances + security | Weekly |
| **Infosecurity Magazine** | InfoSec news | Weekly |
| **IBM Think** | AI/Security trends | Weekly |
| **Future of Life Institute** | AI safety | Monthly |
| **IAPP Daily Dashboard** | AI governance | Daily |

### 13.2 GitHub Resources

| Repo | Description |
|------|-------------|
| TalEliyahu/awesome-security-newsletters | Curated security newsletters |
| TalEliyahu/awesome-ai-security | AI security resources |
| ElNiak/awesome-ai-in-cybersecurity | AI in cybersecurity |

---

## 15. Telegram Sources — Дополнительно

### 15.1 CSA: State of Non-Human Identity and AI Security (Jan 26, 2026)

**Источник:** [Cloud Security Alliance Report](https://cloudsecurityalliance.org/artifacts/state-of-nhi-and-ai-security-survey-report)

| Находка | Значение |
|---------|----------|
| **AI identities as NHI risk** | AI compounding traditional non-human identity risks |
| **Governance gaps** | <25% have documented AI identity policies |
| **Legacy IAM confidence** | Only 12% highly confident in NHI attack prevention |
| **Token sprawl** | 16% don't track new AI-related identities |

**Relevance для SENTINEL:** Подтверждает gap в AI identity management — потенциальный модуль.

### 15.2 Resecurity: Prompt Injection → /etc/passwd Disclosure

**Источник:** [Resecurity Blog](https://www.resecurity.com/blog/article/breaking-trust-with-words-prompt-injection-leading-to-simulated-etcpasswd-disclosure)

| Факт | Данные |
|------|--------|
| **OWASP 2025** | Prompt injection в 73% production AI deployments |
| **Target** | Fortune 100 банковское/HR AI приложение |
| **Attack result** | Simulated /etc/passwd extraction |
| **Use case** | VAPT для enterprise AI applications |

**Relevance для SENTINEL:** Кейс для Academy lab — prompt injection → file disclosure.

### 15.3 CIAOPS: M365 Security + GPT-5 AI Analysis

**Источник:** [CIAOPS Blog](https://blog.ciaops.com/2026/01/26/unlocking-microsoft-365-security-how-i-automated-ai-powered-risk-analysis-with-powershell/)

| Подход | Описание |
|--------|----------|
| **Tool** | PowerShell + Azure AD + AI Foundry |
| **AI Model** | GPT-5 via model routing |
| **Output** | HTML security report с risk assessment |
| **Integration** | Real-time M365 security data |

**Relevance для SENTINEL:** Пример AI-powered security automation — potential integration pattern.

### 15.4 kritt.ai — AI-Powered L1 Security Research

**Источник:** [kritt.ai](https://kritt.ai/technical-review)

| Focus | L1 blockchain security |
|-------|------------------------|
| **Approach** | AI finds bounty-grade exploitable bugs |
| **Languages** | Rust, Go, C++ |

**Relevance:** Competitor intel — AI for offensive security research.

### 15.5 Nulla — Атакующий ИИ-агент (T-Sync Conf 2026)

**Источник:** [T-Sync Conf](https://t-syncconf.ru/) — 7 февраля 2026

| Feature | Описание |
|---------|----------|
| **Repo Analysis** | Анализ репозиториев на реальные уязвимости |
| **API Contracts** | Разбор API-контрактов и логики |
| **PoV Generation** | Proof of Vulnerability — реально эксплуатируемо |
| **Vendor** | SolidLab (Россия) |

**Value Proposition:**
- Масштабирование ИБ-экспертизы без роста штата
- Единая база знаний практикующих экспертов
- Единый стандарт качества вместо субъективных оценок

**Relevance для SENTINEL:** 
- Подтверждает тренд offensive AI agents
- Nulla = general vulns, STRIKE = AI-specific attacks
- Потенциальная интеграция или партнёрство

---

## 16. Sources Summary

### Categories Covered

| Category | Sources |
|----------|---------|
| **Academic Papers** | arXiv (20+ papers) |
| **Industry Reports** | Grand View, Mordor, Gartner, CSA |
| **Vendor Updates** | OpenAI, Anthropic, Google |
| **Conferences** | DEF CON 33, Black Hat USA 2025 |
| **Frameworks** | OWASP LLM Top 10, NIST AI RMF, EU AI Act |
| **M&A Intel** | PitchBook (Protect AI, Lakera) |
| **Tools** | NeMo, LlamaGuard, Rebuff, Garak, Promptfoo |
| **Platforms** | Hugging Face security |
| **Newsletters** | CAIS, OWASP, Import AI, IBM |
| **Telegram Sources** | CSA, Resecurity, CIAOPS, kritt.ai |

---

## 8. Action Items

| # | Action | Owner | Deadline |
|---|--------|-------|----------|
| 1 | Создать урок "Policy Puppetry Jailbreak" | Academy | Feb 2026 |
| 2 | Создать урок "Constrained Decoding Attack" | Academy | Feb 2026 |
| 3 | Создать урок "MCP Security Threats" | Academy | Feb 2026 |
| 4 | Обновить 01-prompt-injection.md с новыми техниками | Academy | Feb 2026 |
| 5 | Добавить lab по Invisible Prompts | Labs | Mar 2026 |
| 6 | Интегрировать Promptfoo в DevKit | DevKit | Q2 2026 |

---

*R&D Report v1.0 — 28 января 2026*
