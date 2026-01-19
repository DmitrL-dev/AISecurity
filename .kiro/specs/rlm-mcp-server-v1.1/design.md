# RLM MCP Server v1.1 — SDD (Software Design Document)

**Версия:** 1.1  
**Дата:** 2026-01-19  
**Статус:** DRAFT — Pending Council Review

---

## 1. Цель

Довести RLM MCP Server с честных **6.5/10** до **9/10** путём устранения критических gaps, выявленных NIOKR Council.

---

## 2. Текущие оценки NIOKR

| Учёный | v1.0 | Критический gap |
|--------|------|-----------------|
| Dr. Crystal | 7/10 | spaCy NER отсутствует |
| Dr. Safe | 6/10 | SafeCrystal слишком простой |
| Dr. Retri | **5/10** | InfiniRetri не реализован |
| Dr. Memory | 8/10 | JSON persistence неоптимален |
| Dr. Security | 7/10 | XOR вместо AES |
| Dr. Quantum | 6/10 | Нет benchmarks |
| **AVERAGE** | **6.5/10** | |

---

## 3. Приоритеты v1.1

### 🔴 P0: Critical (блокирует production)

#### 3.1 Embedding-Based Retrieval
**Ответственный:** Dr. Retri

**Текущее:** Keyword split (Jaccard similarity)  
**Требуется:** Semantic embeddings

**Решение:**
```python
# rlm_toolkit/retrieval/embeddings.py
class EmbeddingRetriever:
    def __init__(self, model: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model)
    
    def embed(self, texts: List[str]) -> np.ndarray:
        return self.model.encode(texts)
    
    def search(self, query: str, corpus: List[str], top_k: int = 5):
        query_emb = self.embed([query])
        corpus_emb = self.embed(corpus)
        scores = cosine_similarity(query_emb, corpus_emb)[0]
        return sorted(zip(corpus, scores), key=lambda x: -x[1])[:top_k]
```

**Метрика успеха:** Recall@5 > 0.8 на test set
**Оценка после:** Dr. Retri 5→8

---

#### 3.2 AES-256-GCM Encryption
**Ответственный:** Dr. Security

**Текущее:** XOR cipher (insecure)  
**Требуется:** AES-256-GCM

**Решение:**
```python
# rlm_toolkit/memory/crypto.py
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

class SecureEncryption:
    def __init__(self, key: bytes):
        self.aesgcm = AESGCM(key[:32])
    
    def encrypt(self, plaintext: bytes, nonce: bytes = None) -> bytes:
        nonce = nonce or os.urandom(12)
        return nonce + self.aesgcm.encrypt(nonce, plaintext, None)
    
    def decrypt(self, ciphertext: bytes) -> bytes:
        nonce, ct = ciphertext[:12], ciphertext[12:]
        return self.aesgcm.decrypt(nonce, ct, None)
```

**Dependency:** `pip install cryptography`
**Оценка после:** Dr. Security 7→9

---

### 🟠 P1: High (улучшает качество)

#### 3.3 spaCy NER Integration
**Ответственный:** Dr. Crystal, Dr. Primitive

**Текущее:** Regex patterns only  
**Требуется:** spaCy entity extraction

**Решение:**
```python
# rlm_toolkit/crystal/extractor.py — update
def __init__(self, use_spacy: bool = True):
    if use_spacy:
        import spacy
        self.nlp = spacy.load("en_core_web_sm")
    
def extract_entities(self, text: str) -> List[Entity]:
    doc = self.nlp(text)
    return [
        Entity(text=ent.text, label=ent.label_, start=ent.start_char)
        for ent in doc.ents
    ]
```

**Dependency:** `pip install spacy && python -m spacy download en_core_web_sm`
**Оценка после:** Dr. Crystal 7→9, Dr. Primitive 7→9

---

#### 3.4 Performance Benchmarks
**Ответственный:** Dr. Quantum

**Текущее:** Нет данных  
**Требуется:** Доказательство 10M+ токенов

**Решение:**
```python
# benchmarks/benchmark_retrieval.py
import time
from rlm_toolkit.crystal import HPEExtractor, CrystalIndexer

def benchmark_indexing(n_files: int, avg_lines: int = 500):
    """Benchmark crystal indexing."""
    extractor = HPEExtractor()
    indexer = CrystalIndexer()
    
    start = time.time()
    for i in range(n_files):
        content = generate_python_file(avg_lines)
        crystal = extractor.extract_from_file(f"/file_{i}.py", content)
        indexer.index_file(crystal)
    
    elapsed = time.time() - start
    return {
        "files": n_files,
        "time_sec": elapsed,
        "files_per_sec": n_files / elapsed,
        "memory_mb": get_memory_usage(),
    }
```

**Targets:**
| Метрика | Target |
|---------|--------|
| 10K files indexing | < 60 sec |
| Memory per 1M tokens | < 100 MB |
| Query latency | < 100 ms |

**Оценка после:** Dr. Quantum 6→8

---

### 🟡 P2: Medium (улучшает UX)

#### 3.5 Rate Limiter Integration
**Ответственный:** Dr. Security

**Текущее:** RateLimiter создан, но не используется  
**Требуется:** Интеграция в server.py

#### 3.6 SQLite Persistence
**Ответственный:** Dr. Memory

**Текущее:** JSON files  
**Требуется:** SQLite для больших объёмов

---

## 4. NIOKR Tracking Matrix

| Учёный | v1.0 | После P0 | После P1 | Target |
|--------|------|----------|----------|--------|
| Dr. Crystal | 7 | 7 | **9** | 9 |
| Dr. Primitive | - | - | **9** | 9 |
| Dr. Safe | 6 | 6 | 7 | 8 |
| Dr. Retri | **5** | **8** | 8 | 9 |
| Dr. Memory | 8 | 8 | 9 | 9 |
| Dr. Security | 7 | **9** | 9 | 9 |
| Dr. Quantum | 6 | 6 | **8** | 9 |
| **AVERAGE** | **6.5** | **7.4** | **8.4** | **9** |

---

## 5. Timeline

| Неделя | Task | Owner |
|--------|------|-------|
| 1 | P0: Embeddings | Dr. Retri |
| 1 | P0: AES-256 | Dr. Security |
| 2 | P1: spaCy NER | Dr. Crystal |
| 2 | P1: Benchmarks | Dr. Quantum |
| 3 | P2: Rate limiter | Dr. Security |
| 3 | P2: SQLite | Dr. Memory |
| 4 | Integration testing | All |

---

## 6. Dependencies

```toml
# pyproject.toml additions
[project.optional-dependencies]
full = [
    "sentence-transformers>=2.2.0",
    "cryptography>=41.0.0",
    "spacy>=3.7.0",
    "aiosqlite>=0.19.0",
]
```

---

## 7. Acceptance Criteria

- [ ] Dr. Retri ≥ 8/10 (embeddings работают)
- [ ] Dr. Security ≥ 9/10 (AES encryption)
- [ ] Dr. Crystal ≥ 8/10 (spaCy optional)
- [ ] Dr. Quantum ≥ 8/10 (benchmarks documented)
- [ ] **Overall ≥ 8.5/10**

---

*SDD v1.1 — Pending NIOKR Council Approval*
