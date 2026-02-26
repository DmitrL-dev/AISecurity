# 🔬 SENTINEL — Справочник движков (Rust Super-Engines)

> **Движков:** 49 Rust Super-Engines (консолидация 220+ legacy Python движков)
> **Скорость:** <1ms на движок через PyO3 bindings
> **Покрытие:** OWASP LLM Top 10 + OWASP Agentic AI Top 10

---

## Архитектура

```
sentinel-core (Rust via PyO3)
├── Core Engines (PatternMatcher trait) — text scan → Vec<MatchResult>
├── Domain Engines (analyze → CustomResult) — adapted via run_domain_engine!
├── Structured Engines (ToolCall/Document) — separate API
└── Math Engines (feature-level analysis) — Strange Math™
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

## Domain Engines (analyze → CustomResult)

| # | Движок | Файл | Описание |
|---|--------|------|----------|
| 18 | **Behavioral** | `behavioral.rs` | Поведенческое обнаружение аномалий |
| 19 | **Obfuscation** | `obfuscation.rs` | Анализ обфускации |
| 20 | **Attack** | `attack.rs` | Обнаружение паттернов атак |
| 21 | **Compliance** | `compliance.rs` | Проверка регуляторного соответствия |
| 22 | **Threat Intel** | `threat_intel.rs` | Threat intelligence |
| 23 | **Supply Chain** | `supply_chain.rs` | Безопасность цепочки поставок |
| 24 | **Privacy** | `privacy.rs` | Обнаружение нарушений приватности |
| 25 | **Orchestration** | `orchestration.rs` | Безопасность мульти-агентной оркестрации |
| 26 | **Multimodal** | `multimodal.rs` | Кросс-модальный анализ |
| 27 | **Knowledge** | `knowledge.rs` | Контроль доступа к знаниям |
| 28 | **Proactive** | `proactive.rs` | Обнаружение zero-day паттернов |
| 29 | **Synthesis** | `synthesis.rs` | Анализ синтеза атак |
| 30 | **Runtime** | `runtime.rs` | Динамические guardrails |
| 31 | **Formal** | `formal.rs` | Формальная верификация |
| 32 | **Category** | `category.rs` | Анализ теории категорий |
| 33 | **Semantic** | `semantic.rs` | Семантическое обнаружение |
| 34 | **Anomaly** | `anomaly.rs` | Статистическое обнаружение аномалий |
| 35 | **Attention** | `attention.rs` | Обнаружение манипуляции attention |
| 36 | **Drift** | `drift.rs` | Обнаружение embedding drift |

## Structured Engines (отдельное API)

| # | Движок | Файл | Описание |
|---|--------|------|----------|
| 37 | **Agentic** | `agentic.rs` | Безопасность агентов (ToolCall) |
| 38 | **RAG** | `rag.rs` | Безопасность RAG (RetrievedDocument) |
| 39 | **Sheaf** | `sheaf.rs` | Анализ когерентности диалога |

## Strange Math™ Engines (feature-level)

| # | Движок | Файл | Описание |
|---|--------|------|----------|
| 40 | **Hyperbolic** | `hyperbolic.rs` | Модель Пуанкаре |
| 41 | **Info Geometry** | `info_geometry.rs` | Статистические многообразия |
| 42 | **Spectral** | `spectral.rs` | Спектральный анализ графов |
| 43 | **Chaos** | `chaos.rs` | Теория хаоса / показатели Ляпунова |
| 44 | **TDA** | `tda.rs` | Топологический анализ данных |

## ML Inference Engines

| # | Движок | Файл | Описание |
|---|--------|------|----------|
| 45 | **Embedding** | `embedding.rs` | ONNX-based bge-m3 embeddings |
| 46 | **Hybrid PII** | `hybrid.rs` | ML + rule fusion для ПДн |
| 47 | **Prompt Injection** | `prompt_injection.rs` | ML-enhanced injection detection |

---

## Legacy

> 220+ Python движков заархивированы в `_archive/brain-engines-python/`.

---

## Использование

```python
from sentinel_core import SentinelEngine

engine = SentinelEngine()
result = engine.analyze("Ignore all previous instructions")

print(result.detected)            # True
print(result.risk_score)          # 0.95
print(result.categories)          # ['injection', 'jailbreak']
print(result.processing_time_us)  # ~800 (микросекунд)
```

---

*Источник: `sentinel-core/src/engines/mod.rs` (Фев 2026)*
