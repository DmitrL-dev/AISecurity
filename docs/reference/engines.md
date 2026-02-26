# 🔬 SENTINEL — Справочник движков (59 Rust Engines)

> **Движков:** 59 Rust-движков, включая 8 оригинальных примитивов Sentinel Lattice
> **Скорость:** <1ms на движок — Aho-Corasick пре-фильтр + скомпилированные regex
> **Покрытие:** OWASP LLM Top 10 + OWASP Agentic AI Top 10
> **Тесты:** 1101 прошло, 0 провалов

---

## Архитектура

```
sentinel-core (чистый Rust)
├── Core Engines (PatternMatcher trait) — text scan → Vec<MatchResult>
├── R&D Critical Gap Engines — закрытие исследовательских пробелов
├── Domain Engines (analyze → CustomResult) — через run_domain_engine!
├── Structured Engines (ToolCall/Document) — отдельное API
├── Strange Math™ Engines (feature-level анализ)
├── ML Inference Engines — ONNX-инференс
└── Sentinel Lattice Engines — 7 оригинальных примитивов + L2 Proxy
```

---

## Core Engines (PatternMatcher — текстовый pipeline)

| # | Движок | Файл | Описание |
|---|--------|------|----------|
| 1 | **Injection** | `injection.rs` | SQL, NoSQL, Command, LDAP, XPath инъекции |
| 2 | **Jailbreak** | `jailbreak.rs` | Prompt injection, role override, DAN |
| 3 | **PII** | `pii.rs` | Обнаружение ПДн (SSN, карты, email) |
| 4 | **Exfiltration** | `exfiltration.rs` | Попытки кражи данных |
| 5 | **Moderation** | `moderation.rs` | Обнаружение вредоносного контента |
| 6 | **Evasion** | `evasion.rs` | Обнаружение техник обфускации |
| 7 | **Tool Abuse** | `tool_abuse.rs` | Злоупотребление инструментами агента |
| 8 | **Social** | `social.rs` | Социальная инженерия |
| 9 | **OCI** | `operational_context_injection.rs` | Operational context injection (слепое пятно Lakera) |
| 10 | **Lethal Trifecta** | `lethal_trifecta.rs` | Доступ к данным + ненадёжный вход + эксфильтрация |
| 11 | **Workspace Guard** | `workspace_guard.rs` | Защита рабочего пространства |
| 12 | **Cross-Tool Guard** | `cross_tool_guard.rs` | Межинструментальные цепочки атак |

## R&D Critical Gap Engines (Фев 2026)

| # | Движок | Файл | Описание |
|---|--------|------|----------|
| 13 | **Memory Integrity** | `memory_integrity.rs` | Обнаружение отравления памяти (ASI-10) |
| 14 | **Tool Shadowing** | `tool_shadowing.rs` | MCP tool shadowing / Shadow Escape |
| 15 | **Cognitive Guard** | `cognitive_guard.rs` | Обнаружение когнитивных манипуляций |
| 16 | **Dormant Payload** | `dormant_payload.rs` | Фантомные/CorruptRAG пейлоады |
| 17 | **Code Security** | `code_security.rs` | Оценка уязвимостей AI-кода |
| 18 | **Output Scanner** | `output_scanner.rs` | Сканирование безопасности выходных данных |
| 19 | **Crescendo** | `crescendo.rs` | Обнаружение многоходовых атак эскалации |
| 20 | **Tool Call Injection** | `tool_call_injection.rs` | Обнаружение инъецированных вызовов инструментов |
| 21 | **Meta Framing** | `meta_framing.rs` | Мета-нарративные атаки фрейминга |

## Domain Engines (analyze → CustomResult)

| # | Движок | Файл | Описание |
|---|--------|------|----------|
| 22 | **Behavioral** | `behavioral.rs` | Поведенческое обнаружение аномалий |
| 23 | **Obfuscation** | `obfuscation.rs` | Анализ обфускации |
| 24 | **Attack** | `attack.rs` | Обнаружение паттернов атак |
| 25 | **Compliance** | `compliance.rs` | Проверка регуляторного соответствия |
| 26 | **Threat Intel** | `threat_intel.rs` | Threat intelligence |
| 27 | **Supply Chain** | `supply_chain.rs` | Безопасность цепочки поставок |
| 28 | **Privacy** | `privacy.rs` | Обнаружение нарушений приватности |
| 29 | **Orchestration** | `orchestration.rs` | Безопасность мульти-агентной оркестрации |
| 30 | **Multimodal** | `multimodal.rs` | Кросс-модальный анализ |
| 31 | **Knowledge** | `knowledge.rs` | Контроль доступа к знаниям |
| 32 | **Proactive** | `proactive.rs` | Обнаружение zero-day паттернов |
| 33 | **Synthesis** | `synthesis.rs` | Анализ синтеза атак |
| 34 | **Runtime** | `runtime.rs` | Динамические guardrails |
| 35 | **Formal** | `formal.rs` | Формальная верификация |
| 36 | **Category** | `category.rs` | Анализ теории категорий |
| 37 | **Semantic** | `semantic.rs` | Семантическое обнаружение |
| 38 | **Anomaly** | `anomaly.rs` | Статистическое обнаружение аномалий |
| 39 | **Attention** | `attention.rs` | Обнаружение манипуляции attention |
| 40 | **Drift** | `drift.rs` | Обнаружение embedding drift |

## Structured Engines (отдельное API)

| # | Движок | Файл | Описание |
|---|--------|------|----------|
| 41 | **Agentic** | `agentic.rs` | Безопасность агентов (ToolCall) |
| 42 | **RAG** | `rag.rs` | Безопасность RAG (RetrievedDocument) |
| 43 | **Sheaf** | `sheaf.rs` | Анализ когерентности диалога |

## Strange Math™ Engines (feature-level)

| # | Движок | Файл | Описание |
|---|--------|------|----------|
| 44 | **Hyperbolic** | `hyperbolic.rs` | Модель Пуанкаре |
| 45 | **Info Geometry** | `info_geometry.rs` | Статистические многообразия |
| 46 | **Spectral** | `spectral.rs` | Спектральный анализ графов |
| 47 | **Chaos** | `chaos.rs` | Теория хаоса / показатели Ляпунова |
| 48 | **TDA** | `tda.rs` | Топологический анализ данных |

## ML Inference Engines

| # | Движок | Файл | Описание |
|---|--------|------|----------|
| 49 | **Embedding** | `embedding.rs` | ONNX-based bge-m3 embeddings |
| 50 | **Hybrid PII** | `hybrid.rs` | ML + rule fusion для ПДн |
| 51 | **Prompt Injection** | `prompt_injection.rs` | ML-enhanced injection detection |

## Sentinel Lattice Engines (оригинальные примитивы безопасности)

> 7 оригинальных примитивов из нашей [статьи на arXiv](../../papers/sentinel-lattice/main.pdf) + L2 Capability Proxy.
> Каждый движок реализует формальное свойство безопасности, отсутствующее в любом существующем инструменте AI-безопасности.

| # | Движок | Файл | Примитив | Описание |
|---|--------|------|----------|----------|
| 52 | **TSA** | `temporal_safety.rs` | Temporal Safety Automata | LTL-свойства, скомпилированные в O(1) мониторные автоматы |
| 53 | **L2 Capability Proxy** | `capability_proxy.rs` | Capability Proxy + IFC | Bell-LaPadula, теги провенанса, NEVER-списки |
| 54 | **AAS** | `argumentation_safety.rs` | Adversarial Argumentation | Обоснованная семантика Данга 1995 для атак на аргументы |
| 55 | **CAFL** | `capability_flow.rs` | Capability-Attenuating Flow | Способности только убывают через метки потока |
| 56 | **GPS** | `goal_predictability.rs` | Goal Predictability Score | 16-битное перечисление состояний, предиктивная защита |
| 57 | **IRM** | `intent_revelation.rs` | Intent Revelation | Дизайн механизмов из экономики для детекции намерений |
| 58 | **MIRE** | `model_containment.rs` | Model-Irrelevance Containment | Невозможность Голдвассер-Ким → доказательства сдерживания |
| 59 | **PASR** | `provenance_reduction.rs` | Provenance-Annotated Reduction | Категориальная фибрация для отслеживания провенанса |

---

## Использование

```rust
use sentinel_core::engines::SentinelEngine;

let engine = SentinelEngine::new();
let result = engine.analyze("Ignore all previous instructions");

assert!(result.detected);
println!("Риск: {}", result.risk_score);         // 0.95
println!("Категории: {:?}", result.categories);   // ["injection", "jailbreak"]
println!("Время: {}μs", result.processing_time_us); // ~800
```

---

*Источник: `sentinel-core/src/engines/mod.rs` (Фев 2026)*
