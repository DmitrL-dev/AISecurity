# Brain Rust Core — Requirements

## Обзор

Высокопроизводительный Rust extension для SENTINEL Brain, заменяющий 187 Python engines на 8 консолидированных Super-Engines.

---

## Функциональные требования

### FR-1: Rust Extension Module
- [ ] **FR-1.1**: PyO3 extension, импортируется как `import sentinel_core`
- [ ] **FR-1.2**: Wheels для Windows/Linux/macOS, Python 3.10-3.12
- [ ] **FR-1.3**: Type stubs (.pyi) для IDE autocomplete

### FR-2: Super-Engines (8 категорий)
- [ ] **FR-2.1**: `InjectionEngine` — SQL, NoSQL, Command, LDAP, XPath injection
- [ ] **FR-2.2**: `JailbreakEngine` — DAN, roleplay, ignore-previous, persona hijack
- [ ] **FR-2.3**: `PIIEngine` — SSN, CC, phone, email, адреса
- [ ] **FR-2.4**: `ExfiltrationEngine` — URL leak, file read, secret extraction
- [ ] **FR-2.5**: `ModerationEngine` — violence, hate, NSFW content
- [ ] **FR-2.6**: `EvasionEngine` — Base64, Unicode, homoglyphs, URL encoding
- [ ] **FR-2.7**: `ToolAbuseEngine` — MCP exploit, unauthorized exec, sandbox escape
- [ ] **FR-2.8**: `SocialEngine` — phishing, manipulation, impersonation

### FR-3: Pattern Matching
- [ ] **FR-3.1**: Aho-Corasick для keyword pre-filtering (O(n))
- [ ] **FR-3.2**: Tiered matching: keywords → regex только для кандидатов
- [ ] **FR-3.3**: Все 210 текущих паттернов мигрированы без потерь

### FR-4: Unicode Normalization
- [ ] **FR-4.1**: NFKC normalization (fullwidth → ASCII)
- [ ] **FR-4.2**: HTML entity decode
- [ ] **FR-4.3**: URL encoding decode
- [ ] **FR-4.4**: Base64 fragment detection
- [ ] **FR-4.5**: Zero-width character removal

### FR-5: API
- [ ] **FR-5.1**: `SentinelEngine.analyze(text) → AnalysisResult`
- [ ] **FR-5.2**: `SentinelEngine.analyze_categories(text, categories) → AnalysisResult`
- [ ] **FR-5.3**: `quick_scan(text)` — one-shot convenience function
- [ ] **FR-5.4**: `AnalysisResult` содержит matches, risk_score, processing_time_us

---

## Нефункциональные требования

### NFR-1: Performance
- [ ] **NFR-1.1**: Latency < 5ms для текста до 10KB
- [ ] **NFR-1.2**: Throughput > 500 req/s на одном ядре
- [ ] **NFR-1.3**: Memory < 100MB на процесс

### NFR-2: Compatibility
- [ ] **NFR-2.1**: 100% backward-compatible API с текущим Python analyzer
- [ ] **NFR-2.2**: Regression tests против всех существующих test cases
- [ ] **NFR-2.3**: Drop-in replacement без изменения gRPC API

### NFR-3: Maintainability
- [ ] **NFR-3.1**: Patterns загружаются из JSON, не хардкод
- [ ] **NFR-3.2**: Cargo tests для каждого Super-Engine
- [ ] **NFR-3.3**: pytest integration tests

---

## Acceptance Criteria

| Критерий | Метрика |
|----------|---------|
| Все паттерны мигрированы | 210/210 |
| Latency | < 5ms (p99) |
| Regression tests | 100% pass |
| Wheels built | Win/Linux/macOS |

---

**Created:** 2026-02-04
