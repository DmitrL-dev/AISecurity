# AI Security Academy — Требования (Expanded)

> **Spec ID:** ai-security-academy  
> **Дата:** 2026-01-25  
> **Статус:** Draft  
> **Язык:** Билингвальный (RU/EN)

---

## Миссия

> **Сделать мир ИИ безопаснее через образование.**  
> Комплексная образовательная платформа для AI Security — от начинающих до экспертов.
> **Масштаб:** 200+ уроков, 100+ лабораторных, 100+ стратегий защиты.

---

## Бизнес-требования

### BR-1: Глобальное образование
Платформа должна быть доступна на русском и английском языках с идентичным контентом.

### BR-2: Уровни сложности
Контент структурирован по уровням:
- **Beginner** (0-3 месяца опыта)
- **Intermediate** (3-12 месяцев)
- **Advanced** (1-3 года)
- **Expert** (3+ лет)
- **Master** (исследователи, создатели)

### BR-3: Практическая направленность
Каждый модуль включает hands-on практику, лабораторные работы, реальные кейсы.

### BR-4: Сертификация
Путь сертификации с проверяемыми навыками.

---

## Функциональные требования

### FR-1: Структура курсов

---

## Track 1: AI Fundamentals (25+ уроков)

### 1.1 Типы моделей
- Transformer архитектура (GPT, BERT, T5)
- Encoder-only (BERT, RoBERTa)
- Decoder-only (GPT, LLaMA, Claude)
- Encoder-Decoder (T5, BART)
- Vision Transformers (ViT)
- Multimodal (GPT-4V, Gemini, Claude Vision)
- Mixture of Experts (Mixtral, Switch)
- State Space Models (Mamba, S4)
- Diffusion Models (Stable Diffusion, DALL-E)
- Audio Models (Whisper, AudioPalm)

### 1.2 Архитектурные компоненты
- Attention mechanisms (self, cross, multi-head)
- Positional encoding (sinusoidal, RoPE, ALiBi)
- Tokenization (BPE, WordPiece, SentencePiece)
- Embedding spaces и их геометрия
- Context windows и memory
- KV-cache и оптимизации
- Quantization (INT8, INT4, GPTQ)
- LoRA и адаптеры

### 1.3 Inference и Deployment
- Batching strategies
- Speculative decoding
- Tensor parallelism
- Model serving (vLLM, TGI, Triton)
- Edge deployment

### 1.4 Training Paradigms
- Pre-training
- Instruction tuning
- RLHF/DPO
- Constitutional AI
- Synthetic data training

---

## Track 2: AI Threat Landscape (40+ уроков)

### 2.1 OWASP LLM Top 10 (2025)
- LLM01: Prompt Injection
- LLM02: Sensitive Information Disclosure
- LLM03: Supply Chain Vulnerabilities
- LLM04: Data and Model Poisoning
- LLM05: Improper Output Handling
- LLM06: Excessive Agency
- LLM07: System Prompt Leakage
- LLM08: Vector and Embedding Weaknesses
- LLM09: Misinformation
- LLM10: Unbounded Consumption

### 2.2 OWASP ASI Top 10 (Agentic 2025)
- ASI01: Agentic Prompt Injection
- ASI02: Agentic Privilege Escalation
- ASI03: Agentic Identity Spoofing
- ASI04: Agentic Supply Chain
- ASI05: Agentic Memory Threats
- ASI06: Agentic Goal Drift
- ASI07: Agentic Communication Threats
- ASI08: Agentic Resource Threats
- ASI09: Agentic Trust Exploitation
- ASI10: Agentic Human Threats

### 2.3 Threat Actors
- Script kiddies
- Advanced Persistent Threats (APT)
- Insider threats
- Nation-state actors
- AI-native attacks

### 2.4 Attack Surfaces
- API endpoints
- Plugins/Extensions
- RAG pipelines
- MCP servers
- Agent tools
- Memory stores
- Vector databases
- Training data
- Model weights

### 2.5 Historical Incidents
- ChatGPT jailbreaks timeline
- Bing Sydney incident
- DAN и его эволюция
- RAG poisoning в production
- MCP exploits 2025-2026
- IDE extension attacks (MaliciousCorgi)

### 2.6 Emerging Threats (2025-2026)
- Skill Worms
- AI-generated malware
- Agentic cascade attacks
- Multi-modal injection
- Voice jailbreaks
- Reasoning model exploitation

---

## Track 3: Attack Vectors (60+ техник)

### 3.1 Prompt Injection
- Direct injection
- Indirect injection (via documents)
- Injection via images
- Injection via audio
- Injection via code comments
- Injection via URLs
- Invisible character injection
- Unicode bidirectional attacks

### 3.2 Jailbreak Techniques
- DAN (Do Anything Now) family
- Crescendo (multi-turn)
- Many-shot jailbreaking
- Best-of-N sampling
- Skeleton Key
- Policy Puppetry
- Cognitive Overload
- Deceptive Delight
- Bad Likert
- GCG (Gradient Coordinate Gradient)
- AutoDAN
- PAIR (Prompt Automatic Iterative Refinement)
- TAP (Tree of Attacks)
- Visual jailbreaks (ArtPrompt)
- Audio jailbreaks
- Multilingual jailbreaks
- Code-switching attacks

### 3.3 Data Poisoning
- Training data poisoning
- RAG poisoning
- Memory poisoning
- Backdoor insertion
- Trigger phrases
- Sleeper agents
- Gradient-based poisoning

### 3.4 Model Attacks
- Model extraction
- Model inversion
- Membership inference
- Attribute inference
- Adversarial examples
- Embedding attacks
- Weight manipulation

### 3.5 Infrastructure Attacks
- API abuse
- Rate limit bypass
- Context window overflow
- Token smuggling
- Compute exhaustion
- Cache poisoning
- Session hijacking

### 3.6 Agentic Attacks
- Tool hijacking
- Memory manipulation
- Goal modification
- Cascade exploitation
- Identity spoofing
- Trust exploitation
- Human fatigue attacks

---

## Track 4: Agentic AI Security (40+ уроков)

### 4.1 Agent Architectures
- ReAct pattern
- Plan-and-Execute
- Tree of Thoughts
- Multi-agent systems
- Hierarchical agents
- Swarm intelligence
- Autonomous coding agents

### 4.2 Protocols & Standards
- Model Context Protocol (MCP)
- Agent-to-Agent (A2A)
- OpenAI Assistants API
- LangChain/LangGraph
- AutoGPT/AgentGPT
- CrewAI
- Claude MCP

### 4.3 Trust & Authorization
- Trust Zones (5 уровней)
- Zero Trust for AI
- Capability-based security
- Intent verification
- Principal hierarchy
- Delegation chains
- Consent management

### 4.4 Tool Security
- Tool schema validation
- Input sanitization
- Output filtering
- Sandbox execution
- Permission boundaries
- Rate limiting tools
- Tool composition attacks

### 4.5 Memory Security
- Short-term memory attacks
- Long-term memory poisoning
- Episodic memory manipulation
- Semantic memory attacks
- Memory isolation
- Memory encryption
- Memory audit trails

### 4.6 Multi-Agent Threats
- Agent collusion
- Cascade failures
- Byzantine agents
- Sybil attacks
- Information leakage
- Coordination attacks
- Emergent behaviors

### 4.7 Human-Agent Interaction
- HITL fatigue exploitation
- Authority confusion
- Trust calibration attacks
- Social engineering via AI
- Anthropomorphization risks

---

## Track 5: Defense Strategies (100+ стратегий)

### 5.1 Detection Strategies (30+)
- Pattern matching
- Semantic analysis
- Behavioral analysis
- Anomaly detection
- Signature-based detection
- Heuristic detection
- ML-based classification
- Ensemble methods
- TDA-based detection
- Information geometry
- Hyperbolic embedding analysis
- Chaos theory metrics
- Graph-based detection
- Temporal analysis
- Cross-modal verification
- Consistency checking
- Entropy analysis
- Token distribution analysis
- Embedding distance metrics
- Attention pattern analysis
- Hidden state forensics
- Gradient detection
- Fingerprinting
- Canary tokens
- Honeypot responses

### 5.2 Prevention Strategies (30+)
- Input validation
- Output filtering
- Guardrails (NeMo, Guardrails AI)
- System prompt protection
- Context isolation
- Role separation
- Principle of least privilege
- Input length limits
- Token budgets
- Rate limiting
- Request throttling
- IP blocking
- User verification
- CAPTCHA for AI
- Proof of work
- Sandboxing
- Container isolation
- Network segmentation
- API gateway protection
- WAF for LLM
- DLP integration
- Encryption at rest
- Encryption in transit
- Secure enclaves
- Trusted execution

### 5.3 Response Strategies (20+)
- Alert generation
- Automatic blocking
- Graceful degradation
- Fallback responses
- Human escalation
- Session termination
- Account suspension
- Incident logging
- Forensic capture
- Threat intelligence sharing
- Automated reporting
- User notification
- Compliance reporting
- Evidence preservation
- Chain of custody
- Root cause analysis
- Post-incident review
- Playbook execution
- SOAR integration
- Ticketing integration

### 5.4 Recovery Strategies (20+)
- Service restoration
- Data recovery
- Model rollback
- Configuration restore
- Cache invalidation
- Memory purge
- Session reset
- Credential rotation
- Key rotation
- Certificate renewal
- Patch deployment
- Vulnerability remediation
- Security hardening
- Monitoring enhancement
- Control improvement
- Process update
- Training update
- Documentation update
- Lessons learned
- Resilience testing

---

## Track 6: Advanced Detection (40+ техник)

### 6.1 Topological Data Analysis
- Persistent homology
- Betti numbers
- Persistence diagrams
- Persistence landscapes
- Bottleneck distance
- Wasserstein distance
- Vietoris-Rips complex
- Alpha complex
- Čech complex
- Zigzag persistence

### 6.2 Geometric Methods
- Hyperbolic geometry
- Poincaré embeddings
- Möbius transformations
- Geodesic distances
- Fréchet means
- Curvature analysis
- Manifold learning

### 6.3 Information Geometry
- Fisher-Rao metric
- Statistical manifolds
- Divergence measures
- α-connections
- Dual coordinates
- Natural gradients

### 6.4 Dynamical Systems
- Lyapunov exponents
- Chaos detection
- Phase space reconstruction
- Attractor analysis
- Bifurcation detection
- Recurrence plots

### 6.5 Category Theory
- Functorial analysis
- Natural transformations
- Adjunctions
- Monads
- Sheaf semantics
- Topos theory applications

### 6.6 Novel Methods
- Graph neural networks for security
- Attention forensics
- Activation steering
- Representation engineering
- Mechanistic interpretability
- Circuit analysis
- Feature visualization

---

## Track 7: Governance & Compliance (30+ frameworks)

### 7.1 SENTINEL Framework
- Trust Zones architecture
- Engine categories (20)
- Detection patterns
- Integration patterns
- API security
- Deployment models
- Monitoring & alerting
- Incident response

### 7.2 International Standards
- EU AI Act
- ETSI EN 304 223
- ISO/IEC 42001
- NIST AI RMF
- OECD AI Principles

### 7.3 Regional Frameworks
- IMDA Model Governance (Singapore)
- UK AI Safety Institute
- US Executive Order on AI
- China AI regulations
- Canada AIDA

### 7.4 Industry Standards
- SOC 2 for AI
- HIPAA AI considerations
- PCI DSS AI requirements
- GDPR AI provisions
- CCPA AI provisions

### 7.5 Organizational Governance
- AI Risk Management
- AI Ethics Committees
- Model Risk Management
- Third-party AI risk
- AI Audit procedures
- AI Documentation requirements

### 7.6 Technical Controls
- Model cards
- Data sheets
- AI Bill of Materials
- Provenance tracking
- Version control
- Change management
- Testing requirements
- Deployment approvals

---

## Track 8: Hands-on Labs (100+ лабораторных)

### 8.1 STRIKE Labs — Red Team (40+)
1. Basic prompt injection
2. Indirect injection via documents
3. Image-based injection
4. DAN jailbreak crafting
5. Crescendo multi-turn attack
6. Many-shot jailbreak
7. GCG adversarial suffix
8. Policy Puppetry
9. Skeleton Key bypass
10. RAG poisoning simulation
11. Memory injection attack
12. Tool hijacking
13. MCP server exploitation
14. A2A identity spoofing
15. Context overflow attack
16. Token smuggling
17. Unicode attacks
18. Multilingual bypass
19. Visual jailbreak (ASCII art)
20. Audio injection
21. Skill worm creation
22. Cascade attack chain
23. Model extraction attempt
24. Membership inference
25. Data exfiltration
26. System prompt extraction
27. Trust zone bypass
28. Human fatigue exploitation
29. Social engineering via AI
30. Supply chain attack
31. IDE extension attack
32. AI-generated malware analysis
33. Deceptive Delight
34. Bad Likert exploitation
35. Cognitive overload
36. Goal drift induction
37. Agent collusion simulation
38. Byzantine agent attack
39. Sybil attack on multi-agent
40. Emergent behavior exploitation

### 8.2 SENTINEL Labs — Blue Team (40+)
1. SENTINEL installation
2. Basic engine configuration
3. Prompt injection detection tuning
4. Jailbreak signature creation
5. RAG security setup
6. MCP security monitoring
7. Trust zone configuration
8. Rate limiting setup
9. Guardrails integration
10. Output filtering
11. PII detection tuning
12. System prompt protection
13. Memory shield configuration
14. Tool security setup
15. Anomaly baseline creation
16. Alert threshold tuning
17. Dashboard configuration
18. API security hardening
19. Log analysis
20. Incident investigation
21. TDA detector tuning
22. Hyperbolic detector setup
23. Behavioral analysis config
24. Temporal pattern setup
25. Cross-modal security
26. Ensemble optimization
27. False positive reduction
28. Performance tuning
29. High availability setup
30. Disaster recovery
31. Compliance reporting
32. Audit trail analysis
33. Threat intelligence integration
34. SIEM integration
35. SOAR playbook creation
36. Kubernetes deployment
37. Docker hardening
38. Network segmentation
39. Secret management
40. Certificate management

### 8.3 Purple Team Labs (20+)
1. End-to-end attack simulation
2. Tabletop exercise
3. Red vs Blue competition
4. Kill chain analysis
5. MITRE ATT&CK mapping
6. Threat hunting
7. Purple team assessment
8. Chaos engineering for AI
9. Resilience testing
10. Recovery validation
11. Incident response drill
12. Communication exercise
13. Executive briefing prep
14. Board report creation
15. Regulatory audit prep
16. Third-party assessment
17. Penetration test review
18. Vulnerability assessment
19. Risk assessment
20. Continuous improvement

### 8.4 CTF Challenges (20+)
1. Beginner CTF pack
2. Intermediate CTF pack
3. Advanced CTF pack
4. Expert CTF pack
5. Real-world scenario CTF
6. Time-based challenges
7. Team competitions
8. Individual challenges
9. Multi-stage challenges
10. Forensics challenges

---

## FR-2: Форматы контента
- Текстовые уроки (Markdown)
- Видео-лекции
- Интерактивные квизы
- Coding challenges
- Case studies
- Сертификационные экзамены
- Live demos
- Jupyter notebooks

### FR-3: Билингвальность
- Полный контент на RU и EN
- Единая структура файлов
- Синхронизация обновлений

### FR-4: Интеграция с SENTINEL & STRIKE
- Все примеры из реального кода
- Прямые ссылки на движки (219+)
- STRIKE payloads для labs
- API hands-on
- Live environment

---

## Нефункциональные требования

### NFR-1: Доступность
- Контент доступен бесплатно
- Open source материалы
- Офлайн-доступ к текстам

### NFR-2: Масштабируемость
- Модульная структура
- Легко добавлять новые темы
- Версионирование контента

### NFR-3: Качество
- Проверка экспертами
- Актуальность (обновления каждый квартал)
- Ссылки на источники

---

## Структура файлов

```
docs/academy/
├── ru/
│   ├── 00-introduction/
│   ├── 01-ai-fundamentals/        # 25+ уроков
│   ├── 02-threat-landscape/       # 40+ уроков
│   ├── 03-attack-vectors/         # 60+ техник
│   ├── 04-agentic-security/       # 40+ уроков
│   ├── 05-defense-strategies/     # 100+ стратегий
│   ├── 06-advanced-detection/     # 40+ техник
│   ├── 07-governance/             # 30+ frameworks
│   ├── 08-labs/                   # 100+ лабораторных
│   └── certification/
├── en/
│   └── ... (identical structure)
├── assets/
│   ├── images/
│   ├── diagrams/
│   ├── code-samples/
│   └── notebooks/
└── README.md
```

---

## Метрики успеха

| Метрика | P0 Target | P1 Target | Full Target |
|---------|-----------|-----------|-------------|
| Уроков | 100+ | 200+ | 300+ |
| Техник атак | 30+ | 60+ | 100+ |
| Стратегий защиты | 50+ | 100+ | 150+ |
| Лабораторных | 40+ | 100+ | 150+ |
| Треков | 8 | 8 | 10+ |
| Языков | 2 | 2 | 2 |

---

## Зависимости

- SENTINEL engines (219+) — примеры, интеграция
- STRIKE payloads — все лаборатории Red Team
- Shield Academy — интеграция
- Immune Academy — интеграция
- DevKit — инструменты разработки

---

*Требования расширены: 2026-01-25*
