# RLM MCP Server v1.1 — Tasks

## 🎯 Цель: 6.5/10 → 9/10

---

## NIOKR Tracking (Live)

| Учёный | v1.0 | Current | Target | Блокер |
|--------|------|---------|--------|--------|
| Dr. Crystal | 7 | 7 | 9 | spaCy NER |
| Dr. Primitive | 7 | 7 | 9 | spaCy NER |
| Dr. Safe | 6 | 6 | 8 | Confidence algo |
| Dr. Retri | **5** | **5** | 9 | **Embeddings** |
| Dr. Memory | 8 | 8 | 9 | SQLite |
| Dr. Security | 7 | 7 | 9 | **AES-256** |
| Dr. Quantum | 6 | 6 | 8 | **Benchmarks** |
| **AVERAGE** | **6.5** | **6.5** | **9** | |

---

## P0: Critical (Week 1)

### T1: Embedding-Based Retrieval
- [ ] T1.1: Создать `rlm_toolkit/retrieval/embeddings.py`
- [ ] T1.2: EmbeddingRetriever с sentence-transformers
- [ ] T1.3: Интеграция с CrystalIndexer
- [ ] T1.4: Tests: `tests/retrieval/test_embeddings.py`
- [ ] T1.5: **NIOKR: Dr. Retri review → 8/10**

### T2: AES-256-GCM Encryption
- [ ] T2.1: Создать `rlm_toolkit/memory/crypto.py`
- [ ] T2.2: Заменить XOR в secure.py на AES-256-GCM
- [ ] T2.3: Migration script для существующих данных
- [ ] T2.4: Tests: `tests/memory/test_crypto.py`
- [ ] T2.5: **NIOKR: Dr. Security review → 9/10**

---

## P1: High (Week 2)

### T3: spaCy NER Integration
- [ ] T3.1: Update HPEExtractor с опциональным spaCy
- [ ] T3.2: Entity extraction (PERSON, ORG, FUNCTION)
- [ ] T3.3: Fallback на regex если spaCy недоступен
- [ ] T3.4: Tests: update `test_crystal.py`
- [ ] T3.5: **NIOKR: Dr. Crystal + Dr. Primitive review → 9/10**

### T4: Performance Benchmarks
- [ ] T4.1: Создать `benchmarks/` директорию
- [ ] T4.2: Benchmark indexing (10K files)
- [ ] T4.3: Benchmark retrieval latency
- [ ] T4.4: Benchmark memory usage
- [ ] T4.5: Document results in `docs/benchmarks.md`
- [ ] T4.6: **NIOKR: Dr. Quantum review → 8/10**

---

## P2: Medium (Week 3)

### T5: Rate Limiter Integration
- [ ] T5.1: Интеграция RateLimiter в server.py
- [ ] T5.2: Per-tool limits
- [ ] T5.3: Декоратор для async tools

### T6: SQLite Persistence (Optional)
- [ ] T6.1: `rlm_toolkit/storage/sqlite.py`
- [ ] T6.2: Migration JSON → SQLite
- [ ] T6.3: **NIOKR: Dr. Memory review → 9/10**

---

## Council Review Checkpoints

| Checkpoint | Tasks | Expected Score |
|------------|-------|----------------|
| Week 1 End | T1, T2 | **7.4/10** |
| Week 2 End | T3, T4 | **8.4/10** |
| Week 3 End | T5, T6 | **9.0/10** |

---

## Acceptance Criteria

- [ ] Все P0 tasks done
- [ ] Overall score ≥ 8.5/10
- [ ] Все 10 учёных ≥ 7/10
- [ ] No учёных ≤ 5/10

---

*Last updated: 2026-01-19*
