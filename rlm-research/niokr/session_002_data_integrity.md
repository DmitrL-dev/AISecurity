# НИОКР Session 2: Data Integrity & Safety
## Галлюцинации, порча данных, казусы

**Дата:** 2026-01-19 08:08  
**Инициатор:** Главный инженер (критический вопрос)  
**Статус:** 🔴 URGENT

---

## ⚠️ Проблема

C³ Session 1 доказала **эффективность**, но НЕ **надёжность**:
- Что если primitive extraction ошибётся?
- Что если связи в графе неверны?
- Что если модель "придумает" несуществующие примитивы?

---

## 🔬 Анализ Failure Modes

### FM-1: Extraction Hallucinations

**Сценарий:** HPE извлекает несуществующую сущность

```
Текст: "Компания заработала около 2 миллиардов"
HPE извлёк: Entity("2 миллиарда", type=MONEY, exact=True)
                                           ^^^^ ОШИБКА!
Было "около", не точное значение
```

**Решение: Confidence Scoring**
```python
class Primitive:
    value: str
    confidence: float  # 0.0 - 1.0
    source_span: Tuple[int, int]  # Позиция в оригинале
    qualifiers: List[str]  # ["approximately", "unclear", "estimated"]
```

---

### FM-2: Relation Hallucinations

**Сценарий:** Связь, которой нет в тексте

```
Текст: "Джон работает в Google. Мария работает в Microsoft."
Граф: Джон --[colleague_of]--> Мария  ← ОШИБКА! Они в разных компаниях
```

**Решение: Evidence-Based Relations**
```python
class Edge:
    source: int
    target: int
    relation: str
    evidence: str  # Цитата из текста, подтверждающая связь
    confidence: float
```

---

### FM-3: Temporal Corruption

**Сценарий:** Неверная временная привязка

```
Текст: "В 2020 году CEO был Джон. Сейчас CEO — Мария."
TKG: (Мария, CEO, valid_from=2020)  ← ОШИБКА! Должно быть valid_from=now
```

**Решение: Explicit Time Extraction**
```python
def extract_time(sentence: str, reference_date: datetime) -> TimeSpan:
    if "сейчас" in sentence or "в настоящее время" in sentence:
        return TimeSpan(start=reference_date, end=None)
    # Explicit date extraction...
```

---

### FM-4: Data Loss

**Сценарий:** Важная информация не попала в примитивы

```
Текст: "Дедлайн — в следующий понедельник, НО ТОЛЬКО если клиент подтвердит."
HPE извлёк: Date("следующий понедельник")
Потеряно: условие "если клиент подтвердит"  ← КРИТИЧЕСКАЯ ПОТЕРЯ
```

**Решение: Conditional Primitives**
```python
class ConditionalPrimitive:
    main_value: Primitive
    condition: Optional[str]
    condition_status: Literal["unverified", "verified", "failed"]
```

---

### FM-5: Query Mismatch

**Сценарий:** Правильный примитив есть, но query не находит

```
Кристалл содержит: Entity("директор по технологиям", "Michael Park")
Query: "Кто CTO?"
Результат: Not found  ← ОШИБКА! CTO = директор по технологиям
```

**Решение: Synonym Normalization**
```python
SYNONYMS = {
    "cto": ["cto", "chief technology officer", "директор по технологиям", "техдиректор"],
    # ...
}

def normalize_query(q: str) -> Set[str]:
    tokens = tokenize(q)
    expanded = set(tokens)
    for token in tokens:
        for key, synonyms in SYNONYMS.items():
            if token in synonyms:
                expanded.update(synonyms)
    return expanded
```

---

## 🛡️ Safety Mechanisms

### S-1: Source Traceability

**Каждый примитив хранит ссылку на оригинал:**

```python
class Primitive:
    value: str
    source_text: str       # Оригинальное предложение
    source_offset: int     # Позиция в документе
    extraction_method: str # "regex" | "ner" | "llm"
```

**Пользователь всегда может проверить:**
```python
def verify(primitive: Primitive, original_doc: str) -> bool:
    return primitive.source_text in original_doc
```

---

### S-2: Confidence Thresholds

**Не использовать ненадёжные данные:**

```python
class CrystalConfig:
    min_extraction_confidence: float = 0.7
    min_relation_confidence: float = 0.8
    warn_below_confidence: float = 0.9

def query(self, q: str) -> QueryResult:
    results = self._raw_query(q)
    
    for r in results:
        if r.confidence < self.config.min_extraction_confidence:
            continue  # Skip low-confidence
        if r.confidence < self.config.warn_below_confidence:
            r.add_warning("Low confidence extraction")
    
    return results
```

---

### S-3: Original Context Fallback

**Если сомнение — вернуться к оригиналу:**

```python
def safe_query(self, q: str) -> str:
    crystal_result = self.crystal.query(q)
    
    if crystal_result.confidence < 0.8:
        # Fallback to original text search
        return self.naive_search(self.original_text, q)
    
    return crystal_result.answer
```

---

### S-4: Verification Pipeline

**Автоматическая проверка перед ответом:**

```python
class VerifiedCrystal:
    def query(self, q: str) -> VerifiedResult:
        result = self.crystal.query(q)
        
        # Step 1: Check primitive exists in original
        if not self._verify_source(result.primitive):
            return VerifiedResult(
                answer=None,
                error="Cannot verify in original text",
                fallback=self.naive_search(q)
            )
        
        # Step 2: Check relation evidence
        if result.via_relation:
            if not self._verify_relation(result.relation):
                return VerifiedResult(
                    answer=result.answer,
                    warning="Relation not directly evidenced",
                    confidence=0.6
                )
        
        # Step 3: Check temporal validity
        if result.primitive.has_time:
            if not self._verify_temporal(result.primitive, self.query_time):
                return VerifiedResult(
                    answer=result.answer,
                    warning="May be outdated",
                    temporal_note=f"Last verified: {result.primitive.time}"
                )
        
        return VerifiedResult(answer=result.answer, confidence=0.95)
```

---

### S-5: Audit Log

**Логировать все операции:**

```python
class AuditedCrystal:
    def __init__(self):
        self.audit_log = []
    
    def add_primitive(self, prim: Primitive):
        self.crystal.add(prim)
        self.audit_log.append({
            "action": "add_primitive",
            "value": prim.value,
            "source": prim.source_text,
            "confidence": prim.confidence,
            "timestamp": now(),
        })
    
    def query(self, q: str) -> str:
        result = self.crystal.query(q)
        self.audit_log.append({
            "action": "query",
            "query": q,
            "result": result.answer,
            "confidence": result.confidence,
            "primitives_used": [p.id for p in result.primitives],
            "timestamp": now(),
        })
        return result
```

---

## 📊 Failure Mode Matrix

| Mode | Probability | Impact | Mitigation | Residual Risk |
|------|-------------|--------|------------|---------------|
| FM-1 Extraction | Medium | High | Confidence scoring | Low |
| FM-2 Relations | Medium | High | Evidence-based | Low |
| FM-3 Temporal | Low | Medium | Explicit extraction | Low |
| FM-4 Data Loss | Medium | Critical | Conditional prims | Medium |
| FM-5 Query Miss | High | Medium | Synonyms | Low |

---

## 🧪 Test Suite for Safety

```python
class SafetyTests:
    
    def test_no_hallucination(self):
        """Crystal should not return data not in source."""
        crystal = ContextCrystal().build("The CEO is John.")
        result = crystal.query("Who is the CTO?")
        assert "not found" in result.lower() or result.confidence < 0.5
    
    def test_source_traceability(self):
        """Every primitive must trace to source."""
        crystal = ContextCrystal().build(doc)
        for prim in crystal.primitives:
            assert prim.source_text in doc
            assert prim.source_offset >= 0
    
    def test_temporal_correctness(self):
        """Time-sensitive queries must respect time."""
        crystal = ContextCrystal().build(
            "In 2020 CEO was John. In 2024 CEO became Maria."
        )
        result = crystal.query("Who is CEO?", time=datetime(2022, 1, 1))
        assert "John" in result.answer
        
        result = crystal.query("Who is CEO?", time=datetime(2025, 1, 1))
        assert "Maria" in result.answer
    
    def test_low_confidence_warning(self):
        """Low confidence results must warn user."""
        crystal = ContextCrystal().build("Revenue was approximately $2B")
        result = crystal.query("What is the exact revenue?")
        assert result.has_warning
        assert "approximate" in result.warning.lower()
```

---

## 🎯 Conclusion Session 2

**Проблема признана. Решения предложены:**

1. ✅ Confidence scoring на всех уровнях
2. ✅ Source traceability — каждый примитив → оригинал
3. ✅ Fallback to original — при сомнениях
4. ✅ Verification pipeline — проверка перед ответом
5. ✅ Audit log — полная история операций
6. ✅ Safety test suite — автоматические проверки

**Следующий шаг:** Интегрировать safety mechanisms в PoC v5.

---

*"Надёжность важнее скорости. Лучше честное 'не знаю', чем ложный ответ."*
