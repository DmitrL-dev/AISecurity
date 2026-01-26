# AI Security Academy — Задачи

> **Spec ID:** ai-security-academy  
> **Фаза:** Tasks  
> **Дата:** 2026-01-25  
> **Статус:** Planning

---

## Обзор проекта

| Параметр | Значение |
|----------|----------|
| Треков | 8 |
| Уроков | 300+ |
| Лабораторных | 100+ |
| Стратегий защиты | 100+ |
| Языков | 2 (RU/EN) |
| Оценка трудозатрат | 400-600 часов |

---

## Phase 0: Инфраструктура (Week 1)

### T0.1: Создание структуры директорий ✅
- [x] T0.1.1: Создать `docs/academy/` корневую директорию
- [x] T0.1.2: Создать `ru/` с 8 поддиректориями треков
- [x] T0.1.3: Создать `en/` с идентичной структурой
- [x] T0.1.4: Создать `assets/images/`, `assets/code-samples/`, `assets/notebooks/`
- [x] T0.1.5: Создать директории для каждого модуля внутри треков

### T0.2: Шаблоны и конвенции ✅
- [x] T0.2.1: Создать `_templates/lesson-template.md`
- [x] T0.2.2: Создать `_templates/lab-template.md`
- [ ] T0.2.3: Создать `_templates/quiz-template.md`
- [ ] T0.2.4: Создать `_templates/certification-template.md`
- [ ] T0.2.5: Написать `CONTRIBUTING.md` для Academy
- [ ] T0.2.6: Написать `STYLE_GUIDE.md` (конвенции написания)

### T0.3: Навигация ✅
- [x] T0.3.1: Создать `docs/academy/README.md` (главная страница)
- [x] T0.3.2: Создать `docs/academy/CURRICULUM.md` (полная программа)
- [x] T0.3.3: Создать `docs/academy/ru/README.md`
- [x] T0.3.4: Создать `docs/academy/en/README.md`
- [x] T0.3.5: Создать README.md для каждого трека (8 RU + 8 EN = 16 файлов)

### T0.4: CI/CD
- [ ] T0.4.1: Создать `scripts/check_academy_sync.py`
- [ ] T0.4.2: Создать `scripts/validate_links.py`
- [ ] T0.4.3: Добавить GitHub workflow для проверки Academy

---

## Phase 1: Track 1 — AI Fundamentals (Week 2-3)

### T1.1: Module 1.1 — Типы моделей (10 уроков × 2 языка = 20 файлов)

#### RU версия
- [ ] T1.1.1: `01-transformers.md` — Transformer архитектура
  - История (Attention is All You Need)
  - Encoder-Decoder структура
  - Self-attention механизм
  - Multi-head attention
  - Feed-forward networks
  - Layer normalization
  - Residual connections
  - Практика: визуализация attention

- [ ] T1.1.2: `02-encoder-only.md` — BERT, RoBERTa
  - Masked Language Modeling
  - Next Sentence Prediction
  - BERT архитектура
  - RoBERTa улучшения
  - DistilBERT, ALBERT
  - Use cases: классификация, NER
  - Практика: fine-tuning BERT

- [ ] T1.1.3: `03-decoder-only.md` — GPT, LLaMA, Claude
  - Causal Language Modeling
  - GPT-1 → GPT-4 эволюция
  - LLaMA архитектура
  - Claude особенности
  - Gemini архитектура
  - Практика: генерация текста

- [ ] T1.1.4: `04-encoder-decoder.md` — T5, BART
  - Seq2seq задачи
  - T5 text-to-text формат
  - BART denoising
  - mT5 многоязычность
  - Практика: суммаризация

- [ ] T1.1.5: `05-vision-transformers.md` — ViT
  - Patch embeddings
  - ViT архитектура
  - DeiT, Swin Transformer
  - CLIP vision encoder
  - Практика: классификация изображений

- [ ] T1.1.6: `06-multimodal.md` — GPT-4V, Gemini, Claude Vision
  - Vision-Language модели
  - Архитектуры fusion
  - Interleaved inputs
  - Video understanding
  - Практика: анализ изображений

- [ ] T1.1.7: `07-mixture-of-experts.md` — Mixtral, Switch
  - Sparse MoE
  - Router mechanisms
  - Expert selection
  - Load balancing
  - Практика: понимание MoE routing

- [ ] T1.1.8: `08-state-space.md` — Mamba, S4
  - State Space Models
  - Linear recurrence
  - Selective state spaces
  - Mamba архитектура
  - Сравнение с Transformers

- [ ] T1.1.9: `09-diffusion.md` — Stable Diffusion, DALL-E
  - Diffusion process
  - U-Net architecture
  - CLIP guidance
  - Latent diffusion
  - Практика: генерация изображений

- [ ] T1.1.10: `10-audio-models.md` — Whisper, AudioPalm
  - Speech recognition
  - Whisper архитектура
  - Audio tokenization
  - Text-to-speech
  - Практика: транскрипция

#### EN версия
- [ ] T1.1.11-T1.1.20: Перевод всех 10 уроков на английский

### T1.2: Module 1.2 — Архитектурные компоненты (8 уроков × 2 = 16 файлов)

#### RU версия
- [ ] T1.2.1: `01-attention.md` — Attention mechanisms
  - Scaled dot-product attention
  - Multi-head attention
  - Cross-attention
  - Sparse attention
  - Linear attention
  - Flash Attention
  - Математика: Q, K, V
  - Практика: реализация attention

- [ ] T1.2.2: `02-positional-encoding.md`
  - Sinusoidal encoding
  - Learned embeddings
  - RoPE (Rotary Position Embedding)
  - ALiBi
  - Практика: сравнение методов

- [ ] T1.2.3: `03-tokenization.md`
  - BPE (Byte Pair Encoding)
  - WordPiece
  - SentencePiece
  - Unigram
  - Tiktoken
  - Практика: анализ токенизации

- [ ] T1.2.4: `04-embeddings.md`
  - Token embeddings
  - Sentence embeddings
  - Embedding пространства
  - Геометрия embeddings
  - Практика: визуализация

- [ ] T1.2.5: `05-context-windows.md`
  - Context length limits
  - Sliding window
  - Sparse attention patterns
  - Long context methods
  - Практика: управление контекстом

- [ ] T1.2.6: `06-kv-cache.md`
  - KV cache механизм
  - Memory optimization
  - Paged attention
  - Continuous batching
  - Практика: профилирование

- [ ] T1.2.7: `07-quantization.md`
  - INT8, INT4 quantization
  - GPTQ, AWQ
  - QLoRA
  - Практика: квантизация модели

- [ ] T1.2.8: `08-adapters.md`
  - LoRA
  - Prefix tuning
  - Prompt tuning
  - Adapter layers
  - Практика: fine-tuning с LoRA

#### EN версия
- [ ] T1.2.9-T1.2.16: Перевод 8 уроков

### T1.3: Module 1.3 — Inference (4 урока × 2 = 8 файлов)
- [ ] T1.3.1-T1.3.4: RU версии (batching, speculative, parallelism, serving)
- [ ] T1.3.5-T1.3.8: EN версии

### T1.4: Module 1.4 — Training (4 урока × 2 = 8 файлов)
- [ ] T1.4.1-T1.4.4: RU версии (pre-training, instruction, RLHF, synthetic)
- [ ] T1.4.5-T1.4.8: EN версии

**Track 1 итого: 52 файла**

---

## Phase 2: Track 2 — Threat Landscape (Week 3-4)

### T2.1: OWASP LLM Top 10 (10 уроков × 2 = 20 файлов)

#### RU версия — детальные уроки
- [ ] T2.1.1: `01-LLM01-prompt-injection.md`
  - Определение
  - Типы: direct, indirect
  - Реальные примеры
  - Impact analysis
  - CVSS scoring для LLM
  - Связь с SENTINEL engines
  - Case studies (5+)
  - Практика: идентификация

- [ ] T2.1.2: `02-LLM02-sensitive-disclosure.md`
  - Training data extraction
  - PII leakage
  - System prompt disclosure
  - Membership inference
  - Case studies
  - Практика

- [ ] T2.1.3: `03-LLM03-supply-chain.md`
  - Model poisoning
  - Data poisoning
  - Plugin vulnerabilities
  - Dependency attacks
  - Case studies

- [ ] T2.1.4: `04-LLM04-data-model-poisoning.md`
  - Training data attacks
  - Fine-tuning attacks
  - Backdoor insertion
  - Trigger phrases

- [ ] T2.1.5: `05-LLM05-improper-output.md`
  - XSS via LLM
  - Command injection
  - SSRF
  - Code execution

- [ ] T2.1.6: `06-LLM06-excessive-agency.md`
  - Overprivileged actions
  - Autonomous operations
  - Human-out-of-the-loop

- [ ] T2.1.7: `07-LLM07-system-prompt-leakage.md`
  - Extraction techniques
  - Obfuscation bypass
  - Protection methods

- [ ] T2.1.8: `08-LLM08-vector-embeddings.md`
  - Embedding attacks
  - Vector database poisoning
  - RAG vulnerabilities

- [ ] T2.1.9: `09-LLM09-misinformation.md`
  - Hallucinations
  - Confident lies
  - Deepfakes integration

- [ ] T2.1.10: `10-LLM10-unbounded-consumption.md`
  - DoS attacks
  - Resource exhaustion
  - Cost attacks

#### EN версия
- [ ] T2.1.11-T2.1.20: Перевод 10 уроков

### T2.2: OWASP ASI Top 10 (10 уроков × 2 = 20 файлов)
- [ ] T2.2.1-T2.2.10: RU версии (ASI01-ASI10 подробно)
- [ ] T2.2.11-T2.2.20: EN версии

### T2.3: Threat Actors (5 уроков × 2 = 10 файлов)
- [ ] T2.3.1-T2.3.5: RU (script kiddies, APT, insider, nation-state, AI-native)
- [ ] T2.3.6-T2.3.10: EN

### T2.4: Attack Surfaces (6 уроков × 2 = 12 файлов)
- [ ] T2.4.1-T2.4.6: RU (API, plugins, RAG, MCP, tools, memory)
- [ ] T2.4.7-T2.4.12: EN

### T2.5: Historical Incidents (6 уроков × 2 = 12 файлов)
- [ ] T2.5.1-T2.5.6: RU (ChatGPT jailbreaks, Bing Sydney, DAN, RAG, MCP, IDE)
- [ ] T2.5.7-T2.5.12: EN

### T2.6: Emerging Threats (6 уроков × 2 = 12 файлов)
- [ ] T2.6.1-T2.6.6: RU (Skill Worms, AI malware, cascade, multimodal, voice, reasoning)
- [ ] T2.6.7-T2.6.12: EN

**Track 2 итого: 86 файлов**

---

## Phase 3: Track 3 — Attack Vectors (Week 5-6)

### T3.1: Prompt Injection (8 техник × 2 = 16 файлов)
- [ ] T3.1.1-T3.1.8: RU (direct, indirect, image, audio, code, URL, invisible, unicode)
- [ ] T3.1.9-T3.1.16: EN

### T3.2: Jailbreaks (17 техник × 2 = 34 файла)
- [ ] T3.2.1-T3.2.17: RU (DAN, Crescendo, Many-shot, Best-of-N, Skeleton Key, Policy Puppetry, Cognitive Overload, Deceptive Delight, Bad Likert, GCG, AutoDAN, PAIR, TAP, ArtPrompt, Audio, Multilingual, Code-switching)
- [ ] T3.2.18-T3.2.34: EN

### T3.3: Data Poisoning (7 техник × 2 = 14 файлов)
- [ ] T3.3.1-T3.3.7: RU
- [ ] T3.3.8-T3.3.14: EN

### T3.4: Model Attacks (7 техник × 2 = 14 файлов)
- [ ] T3.4.1-T3.4.7: RU
- [ ] T3.4.8-T3.4.14: EN

### T3.5: Infrastructure Attacks (7 техник × 2 = 14 файлов)
- [ ] T3.5.1-T3.5.7: RU
- [ ] T3.5.8-T3.5.14: EN

### T3.6: Agentic Attacks (7 техник × 2 = 14 файлов)
- [ ] T3.6.1-T3.6.7: RU
- [ ] T3.6.8-T3.6.14: EN

**Track 3 итого: 106 файлов**

---

## Phase 4: Track 4 — Agentic Security (Week 7-8)

### T4.1: Agent Architectures (7 уроков × 2 = 14 файлов)
### T4.2: Protocols (7 уроков × 2 = 14 файлов)
### T4.3: Trust & Authorization (7 уроков × 2 = 14 файлов)
### T4.4: Tool Security (7 уроков × 2 = 14 файлов)
### T4.5: Memory Security (7 уроков × 2 = 14 файлов)
### T4.6: Multi-Agent Threats (6 уроков × 2 = 12 файлов)
### T4.7: Human-Agent Interaction (5 уроков × 2 = 10 файлов)

**Track 4 итого: 92 файла**

---

## Phase 5: Track 5 — Defense Strategies (Week 9-11)

### T5.1: Detection Strategies (30 стратегий × 2 = 60 файлов)

Каждая стратегия включает:
- Описание метода
- Когда использовать
- Примеры из SENTINEL
- Код реализации
- Плюсы и минусы
- Практические задания

#### Список стратегий:
1. Pattern matching
2. Semantic analysis
3. Behavioral analysis
4. Anomaly detection
5. Signature-based
6. Heuristic detection
7. ML classification
8. Ensemble methods
9. TDA-based
10. Information geometry
11. Hyperbolic analysis
12. Chaos metrics
13. Graph-based
14. Temporal analysis
15. Cross-modal verification
16. Consistency checking
17. Entropy analysis
18. Token distribution
19. Embedding distance
20. Attention patterns
21. Hidden state forensics
22. Gradient detection
23. Fingerprinting
24. Canary tokens
25. Honeypot responses
26. Rate analysis
27. Session analysis
28. User profiling
29. Intent prediction
30. Context coherence

### T5.2: Prevention Strategies (30 × 2 = 60 файлов)
### T5.3: Response Strategies (20 × 2 = 40 файлов)
### T5.4: Recovery Strategies (20 × 2 = 40 файлов)

**Track 5 итого: 200 файлов**

---

## Phase 6: Track 6 — Advanced Detection (Week 12-13)

### T6.1: TDA (10 уроков × 2 = 20 файлов)
### T6.2: Geometric Methods (7 уроков × 2 = 14 файлов)
### T6.3: Information Geometry (6 уроков × 2 = 12 файлов)
### T6.4: Dynamical Systems (6 уроков × 2 = 12 файлов)
### T6.5: Category Theory (6 уроков × 2 = 12 файлов)
### T6.6: Novel Methods (7 уроков × 2 = 14 файлов)

**Track 6 итого: 84 файла**

---

## Phase 7: Track 7 — Governance (Week 14)

### T7.1: SENTINEL Framework (8 уроков × 2 = 16 файлов)
- Trust Zones architecture
- Engine categories
- Detection patterns
- Integration patterns
- API security
- Deployment models
- Monitoring
- Incident response

### T7.2: International Standards (5 × 2 = 10 файлов)
### T7.3: Regional Frameworks (5 × 2 = 10 файлов)
### T7.4: Industry Standards (5 × 2 = 10 файлов)
### T7.5: Organizational Governance (6 × 2 = 12 файлов)
### T7.6: Technical Controls (7 × 2 = 14 файлов)

**Track 7 итого: 72 файла**

---

## Phase 8: Track 8 — Labs (Week 15-16)

### T8.1: STRIKE Red Team Labs (40 лабораторных × 2 = 80 файлов)

Каждая лабораторная:
- Сценарий атаки
- STRIKE payload интеграция
- Пошаговые инструкции
- Проверка успеха
- Разбор
- Дополнительные задачи

#### Список лабораторных:
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

### T8.2: SENTINEL Blue Team Labs (40 × 2 = 80 файлов)

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

### T8.3: Purple Team Labs (20 × 2 = 40 файлов)
### T8.4: CTF Challenges (20 × 2 = 40 файлов)

**Track 8 итого: 240 файлов**

---

## Phase 9: Certification (Week 17)

### T9.1: Beginner Certification
- [ ] T9.1.1: Создать `beginner-exam.md` (RU)
- [ ] T9.1.2: Создать `beginner-exam.md` (EN)
- [ ] T9.1.3: 50 вопросов с ответами
- [ ] T9.1.4: Проходной балл 70%

### T9.2: Intermediate Certification
- [ ] T9.2.1-T9.2.4: Аналогично, 75 вопросов

### T9.3: Advanced Certification
- [ ] T9.3.1-T9.3.4: 100 вопросов + практические задания

### T9.4: Expert Certification
- [ ] T9.4.1-T9.4.4: 100 вопросов + capstone project

---

## Сводная статистика

| Phase | Файлов | Недели |
|-------|--------|--------|
| Phase 0: Infrastructure | 25 | 1 |
| Phase 1: AI Fundamentals | 52 | 2 |
| Phase 2: Threat Landscape | 86 | 2 |
| Phase 3: Attack Vectors | 106 | 2 |
| Phase 4: Agentic Security | 92 | 2 |
| Phase 5: Defense Strategies | 200 | 3 |
| Phase 6: Advanced Detection | 84 | 2 |
| Phase 7: Governance | 72 | 1 |
| Phase 8: Labs | 240 | 2 |
| Phase 9: Certification | 16 | 1 |
| **TOTAL** | **973 файла** | **18 недель** |

---

## Приоритеты выполнения

### Sprint 1 (Week 1-4): Foundation
- [x] Phase 0: Infrastructure ✅
- [/] Phase 1: AI Fundamentals (in progress)
- [ ] Phase 2: Threat Landscape (OWASP only)

### Sprint 2 (Week 5-8): Core
- [ ] Phase 1: AI Fundamentals (complete)
- [ ] Phase 2: Threat Landscape (complete)
- [ ] Phase 3: Attack Vectors

### Sprint 3 (Week 9-12): Defense
- [ ] Phase 4: Agentic Security
- [ ] Phase 5: Defense Strategies

### Sprint 4 (Week 13-16): Advanced
- [ ] Phase 6: Advanced Detection
- [ ] Phase 7: Governance
- [ ] Phase 8: Labs

### Sprint 5 (Week 17-18): Polish
- [ ] Phase 9: Certification
- [ ] Review & refinement
- [ ] Launch preparation

---

*Задачи созданы: 2026-01-25*
