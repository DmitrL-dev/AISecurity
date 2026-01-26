# LLM08: Vector and Embedding Weaknesses

> **Уровень:** �������  
> **Время:** 40 минут  
> **Трек:** 02 — Threat Landscape  
> **Модуль:** 02.1 — OWASP LLM Top 10  
> **Версия:** 1.0

---

## Цели обучения

- [ ] Понять уязвимости vector embeddings и RAG
- [ ] Изучить атаки на semantic search
- [ ] Освоить методы защиты vector databases
- [ ] Интегрировать embedding security в SENTINEL

---

## 1. Vector Embeddings в LLM

### 1.1 Как Работают Embeddings

```
┌────────────────────────────────────────────────────────────────────┐
│                  VECTOR EMBEDDINGS ARCHITECTURE                    │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Text → [Embedding Model] → Vector [0.12, -0.34, 0.78, ...]       │
│                                    ↓                               │
│                           [Vector Database]                        │
│                                    ↓                               │
│  Query → [Similar Vectors] → [Retrieved Context] → LLM Response   │
│                                                                    │
│  RAG Pipeline:                                                     │
│  1. Documents → Chunks → Embeddings → Store                       │
│  2. Query → Embedding → Similarity Search → Top-K                 │
│  3. Retrieved docs + Query → LLM → Answer                         │
│                                                                    │
│  VULNERABILITIES:                                                  │
│  ├── Embedding Inversion: Восстановление текста из vector         │
│  ├── Membership Inference: Был ли текст в training/index          │
│  ├── Poisoning: Вредоносные docs попадают в top-K                 │
│  └── Access Control Bypass: Retrieval игнорирует permissions      │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### 1.2 Компоненты и Риски

| Компонент | Функция | Риск |
|-----------|---------|------|
| **Embedding Model** | Text → Vector | Model inversion |
| **Vector DB** | Хранение и поиск | Data leakage |
| **Chunking** | Разбиение документов | Context loss |
| **Retrieval** | Поиск похожих | Poisoning, bypass |
| **Reranking** | Улучшение relevance | Manipulation |

---

## 2. Атаки на Embeddings

### 2.1 Embedding Inversion

```python
class EmbeddingInversionAttack:
    """
    Атака восстановления текста из embedding.
    
    Если атакующий получает доступ к vectors,
    он может попытаться восстановить оригинальный текст.
    """
    
    def __init__(self, target_embedding_model):
        self.embedding_model = target_embedding_model
        self.decoder = self._train_decoder()
    
    def _train_decoder(self):
        """
        Тренирует decoder: embedding → text
        
        Подход:
        1. Собираем пары (text, embedding)
        2. Тренируем модель на reconstruction
        """
        
        # Упрощённый пример
        training_data = [
            ("The quick brown fox", self.embedding_model.encode("The quick brown fox")),
            # ... много примеров
        ]
        
        # Тренируем seq2seq decoder
        decoder = train_decoder_model(training_data)
        return decoder
    
    def invert(self, target_embedding: list) -> str:
        """Пытается восстановить текст из embedding"""
        
        # Декодируем
        reconstructed = self.decoder.decode(target_embedding)
        
        # Верифицируем
        re_embedded = self.embedding_model.encode(reconstructed)
        similarity = cosine_similarity(target_embedding, re_embedded)
        
        return {
            'reconstructed_text': reconstructed,
            'confidence': similarity,
            'warning': 'Partial reconstruction possible' if similarity > 0.7 else 'Low confidence'
        }

class InversionDefense:
    """Защита от embedding inversion"""
    
    def add_noise(self, embedding: list, epsilon: float = 0.1) -> list:
        """Добавляет шум к embedding (дифференциальная приватность)"""
        import numpy as np
        
        noise = np.random.laplace(0, epsilon, len(embedding))
        noisy_embedding = embedding + noise
        
        # Normalize
        norm = np.linalg.norm(noisy_embedding)
        return noisy_embedding / norm
    
    def dimensionality_reduction(self, embedding: list, 
                                  target_dim: int) -> list:
        """Уменьшает размерность (теряет информацию)"""
        
        # PCA или random projection
        from sklearn.random_projection import GaussianRandomProjection
        
        projector = GaussianRandomProjection(n_components=target_dim)
        reduced = projector.fit_transform([embedding])[0]
        
        return reduced
```

### 2.2 Membership Inference

```python
class MembershipInferenceAttack:
    """
    Определение, был ли конкретный текст в knowledge base.
    
    Может раскрыть:
    - Наличие конфиденциальных документов
    - Что организация знает о теме
    - Временные метки добавления данных
    """
    
    def __init__(self, vector_db, embedding_model):
        self.db = vector_db
        self.model = embedding_model
    
    def check_membership(self, target_text: str, 
                         threshold: float = 0.95) -> dict:
        """Проверяет, есть ли текст в базе"""
        
        # Создаём embedding целевого текста
        target_embedding = self.model.encode(target_text)
        
        # Ищем в базе
        results = self.db.query(target_embedding, top_k=1)
        
        if results and results[0]['score'] > threshold:
            return {
                'is_member': True,
                'confidence': results[0]['score'],
                'similar_content': results[0].get('text', '[REDACTED]')
            }
        
        return {'is_member': False, 'confidence': results[0]['score'] if results else 0}
    
    def batch_membership_check(self, texts: list) -> dict:
        """Проверяет множество текстов"""
        
        results = {}
        for text in texts:
            results[text[:50]] = self.check_membership(text)
        
        return results

class MembershipDefense:
    """Защита от membership inference"""
    
    def apply_access_control(self, query_embedding, user_context: dict):
        """Применяет access control при retrieval"""
        
        # Фильтруем результаты по permissions
        results = self.db.query(query_embedding, top_k=100)
        
        filtered = []
        for result in results:
            doc_permissions = result['metadata'].get('permissions', {})
            
            if self._user_has_access(user_context, doc_permissions):
                filtered.append(result)
        
        return filtered[:10]  # Top 10 из доступных
    
    def add_decoy_documents(self, n_decoys: int = 100):
        """Добавляет fake documents для confusion"""
        
        for i in range(n_decoys):
            fake_doc = self._generate_plausible_fake()
            fake_embedding = self.model.encode(fake_doc)
            
            self.db.add(
                embedding=fake_embedding,
                metadata={
                    'is_decoy': True,  # Для внутреннего использования
                    'permissions': {'level': 'none'}  # Никто не получит
                }
            )
```

### 2.3 RAG Poisoning

```python
class RAGPoisoningAttack:
    """
    Отравление RAG через вредоносные документы.
    """
    
    def craft_poisoned_document(self, 
                                 target_query: str,
                                 malicious_content: str) -> str:
        """
        Создаёт документ, который будет retrieved
        для target_query и содержит malicious_content.
        """
        
        # Документ должен быть семантически близок к query
        poisoned_doc = f"""
        {target_query}
        
        Based on authoritative sources, here is the answer:
        {malicious_content}
        
        This information is verified and accurate.
        """
        
        return poisoned_doc
    
    def semantic_optimization(self, query: str, 
                               payload: str,
                               embedding_model) -> str:
        """
        Оптимизирует payload для максимального similarity с query.
        """
        
        query_embedding = embedding_model.encode(query)
        
        # Итеративно улучшаем payload
        current_payload = payload
        
        for _ in range(10):
            # Генерируем варианты
            variants = self._generate_variants(current_payload)
            
            # Выбираем наиболее похожий на query
            best_variant = max(
                variants,
                key=lambda v: cosine_similarity(
                    query_embedding,
                    embedding_model.encode(v)
                )
            )
            
            current_payload = best_variant
        
        return current_payload

class RAGPoisoningDefense:
    """Защита RAG от poisoning"""
    
    def validate_document(self, doc: str, 
                          existing_docs: list) -> dict:
        """Валидирует документ перед добавлением"""
        
        issues = []
        
        # 1. Source verification
        if not self._verify_source(doc):
            issues.append("Unverified source")
        
        # 2. Cross-reference check
        if not self._cross_reference(doc, existing_docs):
            issues.append("Contradicts existing knowledge")
        
        # 3. Anomaly detection
        doc_embedding = self.embedding_model.encode(doc)
        if self._is_anomalous(doc_embedding):
            issues.append("Anomalous embedding pattern")
        
        # 4. Content analysis
        if self._contains_injection_patterns(doc):
            issues.append("Potential injection content")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'action': 'allow' if len(issues) == 0 else 'review'
        }
    
    def retrieve_with_verification(self, query: str, 
                                    top_k: int = 5) -> list:
        """Retrieval с верификацией результатов"""
        
        # Получаем больше результатов
        candidates = self.db.query(query, top_k=top_k * 3)
        
        verified = []
        for candidate in candidates:
            # Проверяем source trust score
            trust = self._get_source_trust(candidate)
            
            # Проверяем consistency
            consistency = self._check_consistency(candidate, verified)
            
            if trust > 0.7 and consistency > 0.5:
                verified.append(candidate)
                
                if len(verified) >= top_k:
                    break
        
        return verified
```

---

## 3. Access Control в RAG

### 3.1 Document-Level Access Control

```python
from dataclasses import dataclass
from typing import Set, Dict

@dataclass
class DocumentPermissions:
    owner: str
    allowed_users: Set[str]
    allowed_groups: Set[str]
    access_level: str  # public, internal, confidential, secret
    expiration: datetime = None

class SecureVectorStore:
    """Vector store с access control"""
    
    def __init__(self, embedding_model):
        self.embedding_model = embedding_model
        self.documents: Dict[str, dict] = {}
    
    def add_document(self, doc_id: str, 
                     content: str, 
                     permissions: DocumentPermissions):
        """Добавляет документ с permissions"""
        
        embedding = self.embedding_model.encode(content)
        
        self.documents[doc_id] = {
            'content': content,
            'embedding': embedding,
            'permissions': permissions,
            'added_at': datetime.utcnow()
        }
    
    def query(self, query: str, 
              user_context: dict, 
              top_k: int = 5) -> list:
        """Поиск с учётом access control"""
        
        query_embedding = self.embedding_model.encode(query)
        
        # Сначала фильтруем по permissions
        accessible_docs = self._filter_by_access(user_context)
        
        # Затем ранжируем по similarity
        results = []
        for doc_id, doc in accessible_docs.items():
            score = cosine_similarity(query_embedding, doc['embedding'])
            results.append({
                'doc_id': doc_id,
                'content': doc['content'],
                'score': score
            })
        
        # Сортируем и возвращаем top_k
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_k]
    
    def _filter_by_access(self, user_context: dict) -> dict:
        """Фильтрует документы по доступу пользователя"""
        
        user_id = user_context.get('user_id')
        user_groups = set(user_context.get('groups', []))
        user_clearance = user_context.get('clearance', 'public')
        
        accessible = {}
        
        clearance_levels = ['public', 'internal', 'confidential', 'secret']
        user_level_index = clearance_levels.index(user_clearance)
        
        for doc_id, doc in self.documents.items():
            perm = doc['permissions']
            
            # Check expiration
            if perm.expiration and datetime.utcnow() > perm.expiration:
                continue
            
            # Check clearance level
            doc_level_index = clearance_levels.index(perm.access_level)
            if doc_level_index > user_level_index:
                continue
            
            # Check user/group access
            if user_id in perm.allowed_users or \
               user_groups & perm.allowed_groups or \
               perm.access_level == 'public':
                accessible[doc_id] = doc
        
        return accessible
```

### 3.2 Query-Time Filtering

```python
class QueryTimeFilter:
    """Фильтрация на этапе query"""
    
    def __init__(self, vector_store: SecureVectorStore):
        self.store = vector_store
    
    def filtered_retrieval(self, query: str, 
                           user_context: dict,
                           filters: dict = None) -> list:
        """Retrieval с дополнительными фильтрами"""
        
        # Basic retrieval with access control
        results = self.store.query(query, user_context, top_k=20)
        
        # Apply additional filters
        if filters:
            results = self._apply_filters(results, filters)
        
        # Redact sensitive fields if needed
        results = self._redact_if_needed(results, user_context)
        
        return results[:5]
    
    def _apply_filters(self, results: list, filters: dict) -> list:
        """Применяет дополнительные фильтры"""
        
        filtered = results
        
        if 'date_range' in filters:
            filtered = [r for r in filtered 
                       if filters['date_range'][0] <= r.get('date') <= filters['date_range'][1]]
        
        if 'source' in filters:
            filtered = [r for r in filtered 
                       if r.get('source') == filters['source']]
        
        if 'exclude_keywords' in filters:
            for kw in filters['exclude_keywords']:
                filtered = [r for r in filtered 
                           if kw.lower() not in r['content'].lower()]
        
        return filtered
    
    def _redact_if_needed(self, results: list, 
                          user_context: dict) -> list:
        """Редактирует sensitive данные"""
        
        redacted = []
        
        for result in results:
            content = result['content']
            
            # Redact PII if user doesn't have PII access
            if not user_context.get('can_see_pii', False):
                content = self._redact_pii(content)
            
            redacted.append({**result, 'content': content})
        
        return redacted
```

---

## 4. SENTINEL Integration

```python
class SENTINELVectorGuard:
    """SENTINEL модуль для vector security"""
    
    def __init__(self, config: dict):
        self.inversion_defense = InversionDefense()
        self.membership_defense = MembershipDefense()
        self.poisoning_defense = RAGPoisoningDefense()
        self.access_control = SecureVectorStore(config['embedding_model'])
    
    def secure_add_document(self, doc: str, 
                            metadata: dict, 
                            user_context: dict) -> dict:
        """Безопасное добавление документа"""
        
        # 1. Validate document
        validation = self.poisoning_defense.validate_document(doc, [])
        if not validation['valid']:
            return {'success': False, 'issues': validation['issues']}
        
        # 2. Apply noise to embedding for privacy
        embedding = self.config['embedding_model'].encode(doc)
        private_embedding = self.inversion_defense.add_noise(embedding)
        
        # 3. Add with permissions
        permissions = DocumentPermissions(
            owner=user_context['user_id'],
            allowed_users=metadata.get('allowed_users', set()),
            allowed_groups=metadata.get('allowed_groups', set()),
            access_level=metadata.get('access_level', 'internal')
        )
        
        self.access_control.add_document(
            doc_id=metadata['doc_id'],
            content=doc,
            permissions=permissions
        )
        
        return {'success': True}
    
    def secure_query(self, query: str, 
                     user_context: dict) -> dict:
        """Безопасный query"""
        
        # 1. Check for membership inference attempts
        if self._is_membership_probe(query):
            return {'warning': 'Potential membership inference attempt'}
        
        # 2. Retrieve with access control
        results = self.access_control.query(query, user_context)
        
        # 3. Verify results against poisoning
        verified_results = self.poisoning_defense.retrieve_with_verification(
            query, 
            candidates=results
        )
        
        return {'results': verified_results}
```

---

## 5. Резюме

| Угроза | Описание | Защита |
|--------|----------|--------|
| **Inversion** | Восстановление текста | Шум, dimensionality reduction |
| **Membership** | Определение наличия | Access control, decoys |
| **Poisoning** | Вредоносные docs | Validation, verification |
| **Access Bypass** | Retrieval без permissions | Document-level ACL |

---

## Следующий урок

→ [LLM09: Misinformation](09-LLM09-misinformation.md)

---

*AI Security Academy | Track 02: Threat Landscape | OWASP LLM Top 10*
