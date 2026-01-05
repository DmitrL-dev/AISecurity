---
description: Daily R&D research sources for LLM/AI security
---

# Daily R&D Sources for SENTINEL

// turbo-all

## ⏰ MANDATORY: Daily R&D Schedule

**Минимум 2 часа в день** на чистый R&D без имплементации:

- Изучение новых атак и техник
- Анализ arxiv papers
- Мониторинг конкурентов
- Обновление backlog

---

## 🔥 DEEP RESEARCH MODE (NEW - Dec 2025)

> **Урок из EvilAres/Colang сессии:** Поверхностный R&D ≠ Глубокий анализ

### Когда активировать Deep Mode:

- Найден репозиторий с 10+ звёздами по профильной теме
- Paper с новой архитектурой/атакой
- Конкурент выпустил major update
- Обнаружен источник с expertise уровня (EvilAres, Trail of Bits, NVIDIA)

### Deep Research Protocol:

```
┌─────────────────────────────────────────────────────────────┐
│                   DEEP RESEARCH PROTOCOL                     │
├─────────────────────────────────────────────────────────────┤
│ 1. CLONE & AUDIT                                            │
│    - git clone                                               │
│    - Проверка на backdoors (да, всегда!)                    │
│    - Размер, структура, активность                          │
│                                                             │
│ 2. ARCHITECTURE STUDY                                        │
│    - Главные модули и их связи                              │
│    - Ключевые классы/функции                                │
│    - Паттерны проектирования                                │
│                                                             │
│ 3. SCIENTIFIC FOUNDATIONS                                    │
│    - Какая теория/paper за этим стоит?                      │
│    - Математические основы (если есть)                       │
│    - Цитирования и референсы                                │
│                                                             │
│ 4. SOURCE CODE DIVE                                         │
│    - Grammar/AST если DSL                                    │
│    - Core algorithms                                         │
│    - Data structures                                         │
│                                                             │
│ 5. SENTINEL ADAPTATION                                       │
│    - Что можно взять?                                        │
│    - Как адаптировать под наш контекст?                     │
│    - Engine design                                           │
│                                                             │
│ 6. ARTIFACT CREATION                                         │
│    - Markdown с полным анализом                              │
│    - Примеры кода                                            │
│    - Рекомендации по интеграции                             │
└─────────────────────────────────────────────────────────────┘
```

### Примеры Deep Research:

| Source                   | Deep Dive Result                                      |
| ------------------------ | ----------------------------------------------------- |
| fickling (Trail of Bits) | PickleSecurityEngine, ML_ALLOWLIST, 8 severity levels |
| Claude Code AU2          | ContextCompressionEngine, 8-segment architecture      |
| NeMo-Guardrails Colang   | SentinelRuleEngine, Lark grammar, event-driven flows  |

### Что НЕ является Deep Research:

❌ Прочитать README и двигаться дальше  
❌ Скопировать код без понимания  
❌ Поверхностный обзор features  
❌ Только pip install без изучения исходников

---

## Primary Sources (Daily Check)

1. **Arxiv (cs.CR, cs.CL, cs.LG)**

   ```
   https://arxiv.org/list/cs.CR/recent  # Cryptography and Security
   https://arxiv.org/list/cs.CL/recent  # Computation and Language
   https://arxiv.org/list/cs.LG/recent  # Machine Learning
   ```

   Search: `LLM jailbreak`, `prompt injection`, `adversarial attack LLM`

2. **TTPs.ai** - AI Agents Attack Matrix

   ```
   https://ttps.ai/
   ```

   Check for new techniques added

3. **OWASP LLM Top 10**

   ```
   https://owasp.org/www-project-top-10-for-large-language-model-applications/
   https://genai.owasp.org/
   ```

4. **HuggingFace Papers**

   ```
   https://huggingface.co/papers
   ```

   Filter: security, jailbreak, adversarial

5. **Hacker News**
   ```
   https://news.ycombinator.com/newest
   https://hn.algolia.com/?q=llm+security
   https://hn.algolia.com/?q=prompt+injection
   ```
   Sections: Show HN, Ask HN, search by security/llm topics

6. **Awesome-AI-Security** (NEW - Jan 2026)
   ```
   https://github.com/TalEliyahu/Awesome-AI-Security
   ```
   
   ⚠️ **Мониторить обновления репозитория!**  
   Watch → Releases + Issues, или проверять коммиты еженедельно.
   
   **Ключевые секции для мониторинга:**
   
   | Секция | Что мониторить |
   |--------|----------------|
   | Tools → Guardrails | NeMo, LLM Guard, LlamaFirewall, CodeShield |
   | Tools → Model Scanners | ModelScan, Fickling, picklescan |
   | Tools → Agent/MCP Security | Новые тулзы для MCP |
   | Attack Matrices | MITRE ATLAS, GenAI TTPs, MCP TTPs |
   | Defense | AIDEFEND Framework |
   | Videos & Playlists | Ежемесячные плейлисты AI Security |
   | Newsletter | Adversarial AI Digest (LinkedIn) |
   | Datasets | Jailbreak, Prompt Injection datasets |
   
   **Новые конкуренты из списка:**
   - LlamaFirewall (Meta) — runtime firewall
   - CodeShield (Meta) — code security
   - ModelScan (ProtectAI) — artifact scanning
   - AIDEFEND Framework — defense mapping

## Secondary Sources (Weekly)

5. **GitHub Trending**

   ```
   https://github.com/trending?since=weekly
   ```

   Language: Python, Topics: llm, security, jailbreak

6. **Google Scholar Alerts**

   - Set alerts for: "LLM jailbreak", "prompt injection", "AI security"

7. **Security Blogs**

   - https://hiddenlayer.com/research/
   - https://www.lakera.ai/blog
   - https://promptfoo.dev/blog
   - https://www.anthropic.com/research
   - https://openai.com/research

8. **Conference Proceedings**
   - USENIX Security
   - IEEE S&P
   - ACL/EMNLP/NeurIPS (AI security tracks)

## Research Feeds (Subscribe)

9. **Reddit**

   - r/MachineLearning
   - r/LocalLLaMA
   - r/cybersecurity

10. **Twitter/X Lists**

    - @simonw (Simon Willison)
    - @JohannRehberger (prompt injection research)
    - @rez0\_\_

11. **Telegram Channels**
    - [@AISecHub](https://t.me/AISecHub) - 1.46K subs, daily AI security updates

## 🌟 Expert Sources (Deep Research Triggers)

11. **Security Researchers to Follow**

    - [@EvilAres](https://github.com/EvilAres) - 349+ repos, LLM security curation
    - [Trail of Bits](https://github.com/trailofbits) - fickling, ML security
    - [NVIDIA NeMo](https://github.com/NVIDIA/NeMo-Guardrails) - Guardrails DSL

12. **Curated Lists (Weekly Deep Dive)**
    - [Awesome-LLM4Security](https://github.com/EvilAres/Awesome-LLM4Security)
    - [Awesome-LLM-Security](https://github.com/corca-ai/awesome-llm-security)
    - [awesome-llm-hacking](https://github.com/NVISOsecurity/awesome-llm-hacking)

## Competitor Monitoring

13. **Competitor GitHub**
    - Lakera AI Guard
    - Rebuff
    - LLM Guard
    - Vigil
    - NeMo Guardrails
    - HexStrike AI
    - Cisco AI Defense
    - **LlamaFirewall (Meta)** — runtime firewall for LLM apps
    - **CodeShield (Meta)** — code security scanning
    - **ModelScan (ProtectAI)** — ML artifact security
    - **Guardrails AI** — runtime policy enforcement
    - **AIDEFEND Framework** — defense mapping to MITRE ATLAS

## Backlog Update Process

After research, update:

```
C:\Users\chg\.gemini\antigravity\knowledge\sentinel_strike_v4\artifacts\v4_backlog.md
```

Categories:

- P1 Critical (Security Gaps)
- P2 High (Enhancement)
- P3 Medium (Optimization)
- P4 Research (New findings from Deep Research)
