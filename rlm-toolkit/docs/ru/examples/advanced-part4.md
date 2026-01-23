# Продвинутые примеры - Часть 4

Production-ready паттерны для enterprise LLM-развёртываний.

---

## 15. High-Availability RAG-кластер

Многоузловой RAG с Redis, репликацией и автоматическим failover.

```python
from rlm_toolkit import RLM
from rlm_toolkit.vectorstores import RedisVectorStore
from rlm_toolkit.embeddings import OpenAIEmbeddings
from rlm_toolkit.loaders import PDFLoader
from rlm_toolkit.cache import RedisCache
from rlm_toolkit.callbacks import LatencyCallback, TokenCounterCallback
from pydantic import BaseModel
from typing import List, Dict, Optional
from enum import Enum
import redis
from redis.sentinel import Sentinel
import time
import json

class NodeStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

class ClusterNode(BaseModel):
    id: str
    host: str
    port: int
    role: str  # primary, replica, cache
    status: NodeStatus
    latency_ms: float
    last_check: float

class HARAGCluster:
    """
    High-availability RAG кластер с:
    1. Redis Sentinel для автоматического failover
    2. Read replicas для масштабирования
    3. Распределённый кэш
    4. Мониторинг здоровья
    5. Паттерн Circuit Breaker
    """
    
    def __init__(
        self,
        sentinel_hosts: List[tuple],
        master_name: str = "mymaster",
        min_replicas: int = 2
    ):
        # Redis Sentinel для HA
        self.sentinel = Sentinel(sentinel_hosts, socket_timeout=0.5)
        self.master_name = master_name
        
        # Получаем master и replicas
        self.master = self.sentinel.master_for(master_name)
        self.replicas = [
            self.sentinel.slave_for(master_name, socket_timeout=0.5)
            for _ in range(min_replicas)
        ]
        
        # Embeddings
        self.embeddings = OpenAIEmbeddings("text-embedding-3-large")
        
        # Vector stores (primary + replicas)
        self.primary_store = RedisVectorStore(
            redis_client=self.master,
            index_name="rag_primary"
        )
        
        self.replica_stores = [
            RedisVectorStore(redis_client=replica, index_name="rag_replica")
            for replica in self.replicas
        ]
        
        # LLM с кэшированием
        self.cache = RedisCache(redis_client=self.master, ttl=3600)
        self.llm = RLM.from_openai("gpt-4o", cache=self.cache)
        
        # Отслеживание здоровья
        self.nodes: Dict[str, ClusterNode] = {}
        self.circuit_breaker_open = False
        self.failure_count = 0
        self.failure_threshold = 5
        
        # Callbacks для мониторинга
        self.latency_cb = LatencyCallback()
        self.token_cb = TokenCounterCallback()
        
    def ingest(self, documents: List, replicate: bool = True):
        """Загрузка документов в primary и репликация."""
        
        # Запись в primary
        chunks = self.primary_store.add_documents(documents)
        
        # Репликация в read replicas
        if replicate:
            for replica_store in self.replica_stores:
                try:
                    replica_store.add_documents(documents)
                except Exception as e:
                    print(f"Предупреждение репликации: {e}")
        
        return chunks
    
    def query(
        self,
        question: str,
        k: int = 5,
        use_replica: bool = True,
        timeout: float = 5.0
    ) -> Dict:
        """Запрос с автоматическим failover."""
        
        # Проверка circuit breaker
        if self.circuit_breaker_open:
            if time.time() - self.last_failure > 30:
                self.circuit_breaker_open = False
                self.failure_count = 0
            else:
                raise CircuitBreakerOpen("Сервис временно недоступен")
        
        start_time = time.time()
        
        try:
            # Сначала пробуем replicas для масштабирования чтения
            if use_replica and self.replica_stores:
                store = self._get_healthy_replica()
            else:
                store = self.primary_store
            
            # Извлекаем документы
            docs = store.similarity_search(question, k=k)
            
            # Формируем контекст
            context = "\n\n".join([doc.page_content for doc in docs])
            
            # Сначала проверяем кэш
            cache_key = f"rag:{hash(question + context)}"
            cached = self.cache.get(cache_key)
            
            if cached:
                return {
                    "answer": cached,
                    "sources": [doc.metadata for doc in docs],
                    "cached": True,
                    "latency_ms": (time.time() - start_time) * 1000
                }
            
            # Генерируем ответ
            answer = self.llm.run(f"""
            Ответь на основе контекста:
            
            Контекст:
            {context}
            
            Вопрос: {question}
            """)
            
            # Кэшируем результат
            self.cache.set(cache_key, answer)
            
            # Сбрасываем счётчик ошибок при успехе
            self.failure_count = 0
            
            return {
                "answer": answer,
                "sources": [doc.metadata for doc in docs],
                "cached": False,
                "latency_ms": (time.time() - start_time) * 1000
            }
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.circuit_breaker_open = True
            
            # Fallback на primary если replica упала
            if use_replica:
                return self.query(question, k=k, use_replica=False)
            
            raise
    
    def _get_healthy_replica(self) -> RedisVectorStore:
        """Получить здоровую replica через round-robin с проверкой здоровья."""
        for store in self.replica_stores:
            try:
                store.redis_client.ping()
                return store
            except:
                continue
        
        # Fallback на primary
        return self.primary_store
    
    def health_check(self) -> Dict[str, NodeStatus]:
        """Проверка здоровья всех узлов."""
        results = {}
        
        # Проверяем master
        try:
            start = time.time()
            self.master.ping()
            latency = (time.time() - start) * 1000
            
            results["master"] = ClusterNode(
                id="master",
                host=str(self.master.connection_pool.connection_kwargs.get("host")),
                port=self.master.connection_pool.connection_kwargs.get("port", 6379),
                role="primary",
                status=NodeStatus.HEALTHY if latency < 100 else NodeStatus.DEGRADED,
                latency_ms=latency,
                last_check=time.time()
            )
        except:
            results["master"] = ClusterNode(
                id="master",
                host="unknown",
                port=0,
                role="primary",
                status=NodeStatus.UNHEALTHY,
                latency_ms=-1,
                last_check=time.time()
            )
        
        # Проверяем replicas
        for i, replica in enumerate(self.replicas):
            try:
                start = time.time()
                replica.ping()
                latency = (time.time() - start) * 1000
                
                results[f"replica_{i}"] = ClusterNode(
                    id=f"replica_{i}",
                    host=str(replica.connection_pool.connection_kwargs.get("host")),
                    port=replica.connection_pool.connection_kwargs.get("port", 6379),
                    role="replica",
                    status=NodeStatus.HEALTHY if latency < 100 else NodeStatus.DEGRADED,
                    latency_ms=latency,
                    last_check=time.time()
                )
            except:
                results[f"replica_{i}"] = ClusterNode(
                    id=f"replica_{i}",
                    host="unknown",
                    port=0,
                    role="replica",
                    status=NodeStatus.UNHEALTHY,
                    latency_ms=-1,
                    last_check=time.time()
                )
        
        return results
    
    def get_metrics(self) -> Dict:
        """Получить метрики кластера."""
        health = self.health_check()
        
        return {
            "nodes_total": len(health),
            "nodes_healthy": len([n for n in health.values() if n.status == NodeStatus.HEALTHY]),
            "avg_latency_ms": sum(n.latency_ms for n in health.values() if n.latency_ms > 0) / max(len(health), 1),
            "circuit_breaker": "open" if self.circuit_breaker_open else "closed",
            "failure_count": self.failure_count,
            "tokens_used": self.token_cb.total_tokens,
            "cache_hit_rate": self.cache.get_stats().get("hit_rate", 0)
        }

class CircuitBreakerOpen(Exception):
    pass

# Использование
if __name__ == "__main__":
    cluster = HARAGCluster(
        sentinel_hosts=[
            ("sentinel1.local", 26379),
            ("sentinel2.local", 26379),
            ("sentinel3.local", 26379)
        ],
        master_name="mymaster",
        min_replicas=2
    )
    
    # Загружаем документы
    docs = PDFLoader("company_docs.pdf").load()
    cluster.ingest(docs)
    
    # Запрос с HA
    result = cluster.query("Какая у нас политика отпусков?")
    print(f"Ответ: {result['answer']}")
    print(f"Латентность: {result['latency_ms']:.1f}мс")
    print(f"Из кэша: {result['cached']}")
    
    # Проверка здоровья
    health = cluster.health_check()
    for name, node in health.items():
        print(f"{name}: {node.status.value} ({node.latency_ms:.1f}мс)")
```

---

## 16. Фреймворк A/B-тестирования промптов

Сравнение вариаций промптов со статистической строгостью.

```python
from rlm_toolkit import RLM
from rlm_toolkit.callbacks import TokenCounterCallback
from pydantic import BaseModel
from typing import List, Dict, Optional, Callable
from scipy import stats
import numpy as np
from dataclasses import dataclass
import json
import random
from datetime import datetime

class PromptVariant(BaseModel):
    id: str
    name: str
    prompt_template: str
    weight: float = 0.5  # Распределение трафика

class ExperimentResult(BaseModel):
    variant_id: str
    input: str
    output: str
    latency_ms: float
    tokens_used: int
    quality_score: Optional[float]
    user_feedback: Optional[int]  # 1-5
    timestamp: datetime

class ExperimentAnalysis(BaseModel):
    experiment_id: str
    variants: List[str]
    sample_sizes: Dict[str, int]
    metrics: Dict[str, Dict[str, float]]
    winner: Optional[str]
    confidence: float
    recommendation: str

class PromptABTesting:
    """
    Фреймворк A/B-тестирования для оптимизации промптов:
    1. Разделение трафика
    2. Сбор метрик (латентность, качество, отзывы)
    3. Тестирование статистической значимости
    4. Автоматическое определение победителя
    5. Постепенный rollout
    """
    
    def __init__(self, experiment_id: str):
        self.experiment_id = experiment_id
        self.variants: Dict[str, PromptVariant] = {}
        self.results: List[ExperimentResult] = []
        
        # LLM для каждого варианта
        self.llms: Dict[str, RLM] = {}
        
        # Оценщик качества
        self.evaluator = RLM.from_openai("gpt-4o-mini")
        self.evaluator.set_system_prompt("""
        Оцени качество ответа по шкале от 1 до 10.
        Учитывай:
        - Точность
        - Полноту
        - Ясность
        - Релевантность
        
        Верни только число.
        """)
        
    def add_variant(
        self,
        id: str,
        name: str,
        prompt_template: str,
        llm: RLM,
        weight: float = 0.5
    ):
        """Добавить вариант промпта в эксперимент."""
        self.variants[id] = PromptVariant(
            id=id,
            name=name,
            prompt_template=prompt_template,
            weight=weight
        )
        self.llms[id] = llm
        
    def run(self, input: str, user_id: Optional[str] = None) -> Dict:
        """Запустить эксперимент и вернуть результат выбранного варианта."""
        
        # Выбор варианта (детерминированный если есть user_id)
        if user_id:
            variant_id = self._deterministic_assignment(user_id)
        else:
            variant_id = self._weighted_random_assignment()
        
        variant = self.variants[variant_id]
        llm = self.llms[variant_id]
        
        # Форматируем промпт
        full_prompt = variant.prompt_template.format(input=input)
        
        # Выполнение с замером времени
        import time
        start = time.time()
        
        token_cb = TokenCounterCallback()
        llm.callbacks = [token_cb]
        
        output = llm.run(full_prompt)
        
        latency = (time.time() - start) * 1000
        
        # Автоматическая оценка качества
        quality_score = self._evaluate_quality(input, output)
        
        # Записываем результат
        result = ExperimentResult(
            variant_id=variant_id,
            input=input,
            output=output,
            latency_ms=latency,
            tokens_used=token_cb.total_tokens,
            quality_score=quality_score,
            user_feedback=None,
            timestamp=datetime.now()
        )
        self.results.append(result)
        
        return {
            "variant": variant_id,
            "output": output,
            "latency_ms": latency,
            "quality_score": quality_score
        }
    
    def record_feedback(self, result_index: int, feedback: int):
        """Записать отзыв пользователя о результате."""
        if 0 <= result_index < len(self.results):
            self.results[result_index].user_feedback = feedback
    
    def analyze(self, min_samples: int = 30) -> ExperimentAnalysis:
        """Анализ результатов эксперимента со статистической значимостью."""
        
        # Группировка по вариантам
        by_variant: Dict[str, List[ExperimentResult]] = {}
        for result in self.results:
            if result.variant_id not in by_variant:
                by_variant[result.variant_id] = []
            by_variant[result.variant_id].append(result)
        
        # Расчёт метрик по вариантам
        metrics = {}
        for variant_id, results in by_variant.items():
            if len(results) < min_samples:
                continue
                
            latencies = [r.latency_ms for r in results]
            qualities = [r.quality_score for r in results if r.quality_score]
            feedbacks = [r.user_feedback for r in results if r.user_feedback]
            tokens = [r.tokens_used for r in results]
            
            metrics[variant_id] = {
                "n": len(results),
                "latency_mean": np.mean(latencies),
                "latency_std": np.std(latencies),
                "quality_mean": np.mean(qualities) if qualities else 0,
                "quality_std": np.std(qualities) if qualities else 0,
                "feedback_mean": np.mean(feedbacks) if feedbacks else 0,
                "tokens_mean": np.mean(tokens),
                "cost_per_request": np.mean(tokens) * 0.00001  # Приблизительно
            }
        
        # Тестирование статистической значимости
        variant_ids = list(metrics.keys())
        winner = None
        confidence = 0.0
        
        if len(variant_ids) >= 2:
            # Сравнение оценок качества
            v1, v2 = variant_ids[0], variant_ids[1]
            q1 = [r.quality_score for r in by_variant[v1] if r.quality_score]
            q2 = [r.quality_score for r in by_variant[v2] if r.quality_score]
            
            if q1 and q2:
                t_stat, p_value = stats.ttest_ind(q1, q2)
                confidence = 1 - p_value
                
                if p_value < 0.05:  # 95% уверенность
                    winner = v1 if np.mean(q1) > np.mean(q2) else v2
        
        # Формирование рекомендации
        recommendation = self._generate_recommendation(metrics, winner, confidence)
        
        return ExperimentAnalysis(
            experiment_id=self.experiment_id,
            variants=variant_ids,
            sample_sizes={v: len(by_variant.get(v, [])) for v in variant_ids},
            metrics=metrics,
            winner=winner,
            confidence=confidence,
            recommendation=recommendation
        )
    
    def _deterministic_assignment(self, user_id: str) -> str:
        """Детерминированное назначение пользователя на вариант."""
        hash_val = hash(f"{self.experiment_id}:{user_id}") % 100
        
        cumulative = 0
        for variant_id, variant in self.variants.items():
            cumulative += variant.weight * 100
            if hash_val < cumulative:
                return variant_id
        
        return list(self.variants.keys())[-1]
    
    def _weighted_random_assignment(self) -> str:
        """Случайное назначение на основе весов."""
        variants = list(self.variants.values())
        weights = [v.weight for v in variants]
        return random.choices([v.id for v in variants], weights=weights)[0]
    
    def _evaluate_quality(self, input: str, output: str) -> float:
        """Автоматическая оценка качества ответа."""
        try:
            score = self.evaluator.run(f"""
            Ввод: {input[:200]}
            Ответ: {output[:500]}
            
            Оценка качества 1-10:
            """)
            return float(score.strip()) / 10
        except:
            return 0.5
    
    def _generate_recommendation(
        self, 
        metrics: Dict, 
        winner: Optional[str], 
        confidence: float
    ) -> str:
        """Генерация рекомендации на основе анализа."""
        if not winner:
            return "Нет статистически значимого победителя. Продолжайте эксперимент."
        
        if confidence > 0.95:
            return f"Сильная рекомендация: Деплой варианта '{winner}' (уверенность: {confidence:.1%})"
        elif confidence > 0.90:
            return f"Умеренная рекомендация: Рассмотрите деплой '{winner}' (уверенность: {confidence:.1%})"
        else:
            return f"Слабый сигнал для '{winner}'. Нужно больше данных (уверенность: {confidence:.1%})"
    
    def export_results(self, path: str):
        """Экспорт результатов для внешнего анализа."""
        data = [r.dict() for r in self.results]
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

# Использование
if __name__ == "__main__":
    # Создаём эксперимент
    experiment = PromptABTesting("prompt_optimization_v1")
    
    # Добавляем варианты
    llm = RLM.from_openai("gpt-4o")
    
    experiment.add_variant(
        id="control",
        name="Оригинальный промпт",
        prompt_template="Ответь на вопрос: {input}",
        llm=llm,
        weight=0.5
    )
    
    experiment.add_variant(
        id="treatment",
        name="Детальный промпт",
        prompt_template="""
        Ты полезный ассистент. Ответь на следующий вопрос:
        - Будь кратким, но полным
        - Используй примеры, если полезно
        - Структурируй ответ чётко
        
        Вопрос: {input}
        """,
        llm=llm,
        weight=0.5
    )
    
    # Запускаем эксперимент
    test_questions = [
        "Что такое машинное обучение?",
        "Как работают нейронные сети?",
        "Объясни backpropagation",
    ] * 20  # 60 образцов
    
    for question in test_questions:
        result = experiment.run(question)
        print(f"Вариант: {result['variant']}, Качество: {result['quality_score']:.2f}")
    
    # Анализ
    analysis = experiment.analyze()
    print(f"\n{'='*50}")
    print(f"Эксперимент: {analysis.experiment_id}")
    print(f"Победитель: {analysis.winner}")
    print(f"Уверенность: {analysis.confidence:.1%}")
    print(f"Рекомендация: {analysis.recommendation}")
```

---

## 17. Семантический кэш с Fallback

Интеллектуальное кэширование с graceful degradation.

```python
from rlm_toolkit import RLM
from rlm_toolkit.embeddings import OpenAIEmbeddings
from rlm_toolkit.vectorstores import ChromaVectorStore
from rlm_toolkit.cache import RedisCache
from typing import Optional, Dict, Tuple
import hashlib
import time
import json

class CacheEntry:
    def __init__(self, query: str, response: str, embedding: list, timestamp: float):
        self.query = query
        self.response = response
        self.embedding = embedding
        self.timestamp = timestamp
        self.hits = 0

class SemanticCache:
    """
    Многослойный семантический кэш:
    1. Exact match кэш (быстрый, Redis)
    2. Семантический similarity кэш (векторный поиск)
    3. LLM fallback с заполнением кэша
    4. TTL-based expiration
    5. Graceful degradation при сбоях
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        similarity_threshold: float = 0.92,
        cache_ttl: int = 3600,
        max_semantic_entries: int = 10000
    ):
        self.similarity_threshold = similarity_threshold
        self.cache_ttl = cache_ttl
        
        # Слой 1: Exact match кэш (Redis)
        self.exact_cache = RedisCache(
            host="localhost",
            port=6379,
            ttl=cache_ttl
        )
        
        # Слой 2: Семантический кэш (Vector store)
        self.embeddings = OpenAIEmbeddings("text-embedding-3-small")
        self.semantic_store = ChromaVectorStore(
            collection_name="semantic_cache",
            embedding_function=self.embeddings
        )
        
        # Слой 3: LLM fallback
        self.llm = RLM.from_openai("gpt-4o")
        
        # Fallback LLM для degradation
        self.fallback_llms = [
            RLM.from_openai("gpt-4o-mini"),
            RLM.from_ollama("llama3")
        ]
        
        # Статистика
        self.stats = {
            "exact_hits": 0,
            "semantic_hits": 0,
            "llm_calls": 0,
            "fallback_calls": 0,
            "failures": 0
        }
        
    def query(self, question: str, bypass_cache: bool = False) -> Dict:
        """Запрос с многослойным кэшированием."""
        
        start_time = time.time()
        cache_status = "miss"
        
        if not bypass_cache:
            # Слой 1: Exact match
            exact_result = self._check_exact_cache(question)
            if exact_result:
                self.stats["exact_hits"] += 1
                return {
                    "response": exact_result,
                    "cache_status": "exact_hit",
                    "latency_ms": (time.time() - start_time) * 1000
                }
            
            # Слой 2: Семантическое сходство
            semantic_result = self._check_semantic_cache(question)
            if semantic_result:
                self.stats["semantic_hits"] += 1
                return {
                    "response": semantic_result[0],
                    "cache_status": f"semantic_hit (similarity: {semantic_result[1]:.2f})",
                    "latency_ms": (time.time() - start_time) * 1000
                }
        
        # Слой 3: LLM с fallback
        response, fallback_used = self._call_llm_with_fallback(question)
        
        if fallback_used:
            self.stats["fallback_calls"] += 1
            cache_status = "fallback"
        else:
            self.stats["llm_calls"] += 1
            cache_status = "llm"
        
        # Заполняем кэши
        if response:
            self._populate_caches(question, response)
        
        return {
            "response": response,
            "cache_status": cache_status,
            "latency_ms": (time.time() - start_time) * 1000
        }
    
    def _check_exact_cache(self, question: str) -> Optional[str]:
        """Проверка exact match кэша."""
        cache_key = self._hash_query(question)
        try:
            cached = self.exact_cache.get(cache_key)
            return cached
        except:
            return None
    
    def _check_semantic_cache(self, question: str) -> Optional[Tuple[str, float]]:
        """Проверка семантического similarity кэша."""
        try:
            results = self.semantic_store.similarity_search_with_score(
                question,
                k=1
            )
            
            if results:
                doc, score = results[0]
                similarity = 1 - score  # Конвертируем расстояние в similarity
                
                if similarity >= self.similarity_threshold:
                    # Возвращаем кэшированный ответ из metadata
                    return (doc.metadata.get("response"), similarity)
        except Exception as e:
            print(f"Ошибка семантического кэша: {e}")
        
        return None
    
    def _call_llm_with_fallback(self, question: str) -> Tuple[str, bool]:
        """Вызов LLM с graceful fallback."""
        
        # Пробуем основной LLM
        try:
            response = self.llm.run(question)
            return (response, False)
        except Exception as e:
            print(f"Основной LLM упал: {e}")
        
        # Пробуем fallback LLM
        for fallback in self.fallback_llms:
            try:
                response = fallback.run(question)
                return (response, True)
            except:
                continue
        
        # Все упали
        self.stats["failures"] += 1
        return ("Извините, я временно не могу ответить. Попробуйте позже.", True)
    
    def _populate_caches(self, question: str, response: str):
        """Заполнение всех слоёв кэша."""
        
        # Exact cache
        cache_key = self._hash_query(question)
        try:
            self.exact_cache.set(cache_key, response)
        except:
            pass
        
        # Semantic cache
        try:
            self.semantic_store.add_texts(
                [question],
                metadatas=[{
                    "response": response,
                    "timestamp": time.time()
                }]
            )
        except:
            pass
    
    def _hash_query(self, query: str) -> str:
        """Создание консистентного хеша для запроса."""
        normalized = query.lower().strip()
        return hashlib.sha256(normalized.encode()).hexdigest()
    
    def invalidate(self, pattern: Optional[str] = None):
        """Инвалидация записей кэша."""
        if pattern:
            # Pattern-based инвалидация (только exact cache)
            # Redis SCAN с паттерном
            pass
        else:
            # Очистка всего
            pass
    
    def get_stats(self) -> Dict:
        """Получить статистику кэша."""
        total = sum(self.stats.values())
        
        return {
            **self.stats,
            "total_requests": total,
            "exact_hit_rate": self.stats["exact_hits"] / max(total, 1),
            "semantic_hit_rate": self.stats["semantic_hits"] / max(total, 1),
            "overall_hit_rate": (self.stats["exact_hits"] + self.stats["semantic_hits"]) / max(total, 1),
            "fallback_rate": self.stats["fallback_calls"] / max(total, 1),
            "failure_rate": self.stats["failures"] / max(total, 1)
        }
    
    def warm_cache(self, common_queries: list):
        """Предзаполнение кэша частыми запросами."""
        for query in common_queries:
            self.query(query, bypass_cache=True)

# Использование
if __name__ == "__main__":
    cache = SemanticCache(
        similarity_threshold=0.90,
        cache_ttl=3600
    )
    
    # Первый запрос - cache miss
    result = cache.query("Что такое машинное обучение?")
    print(f"Статус: {result['cache_status']}, Латентность: {result['latency_ms']:.1f}мс")
    
    # Тот же запрос - exact hit
    result = cache.query("Что такое машинное обучение?")
    print(f"Статус: {result['cache_status']}, Латентность: {result['latency_ms']:.1f}мс")
    
    # Похожий запрос - semantic hit
    result = cache.query("Объясни мне машинное обучение")
    print(f"Статус: {result['cache_status']}, Латентность: {result['latency_ms']:.1f}мс")
    
    # Статистика
    stats = cache.get_stats()
    print(f"\nОбщий hit rate: {stats['overall_hit_rate']:.1%}")
```

---

## 18. Event-Driven Agent Pipeline

Интеграция Kafka/RabbitMQ с асинхронной обработкой агентами.

```python
from rlm_toolkit import RLM
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import Tool
from pydantic import BaseModel
from typing import List, Dict, Optional, Callable
import asyncio
import json
from datetime import datetime
from enum import Enum

# Симуляция очереди сообщений (используйте реальный Kafka/RabbitMQ в production)
class MessageQueue:
    def __init__(self):
        self.queues: Dict[str, asyncio.Queue] = {}
        
    def get_queue(self, name: str) -> asyncio.Queue:
        if name not in self.queues:
            self.queues[name] = asyncio.Queue()
        return self.queues[name]
    
    async def publish(self, queue: str, message: dict):
        await self.get_queue(queue).put(message)
    
    async def consume(self, queue: str):
        return await self.get_queue(queue).get()

class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Task(BaseModel):
    id: str
    type: str
    payload: dict
    status: TaskStatus
    result: Optional[dict]
    created_at: datetime
    completed_at: Optional[datetime]
    retries: int = 0

class EventDrivenAgentPipeline:
    """
    Event-driven пайплайн агентов с:
    1. Интеграцией очереди сообщений (Kafka/RabbitMQ)
    2. Асинхронной обработкой задач
    3. Управлением пулом воркеров
    4. Dead letter queue
    5. Логикой повторных попыток
    """
    
    def __init__(self, num_workers: int = 4, max_retries: int = 3):
        self.mq = MessageQueue()
        self.num_workers = num_workers
        self.max_retries = max_retries
        
        # Реестр задач
        self.tasks: Dict[str, Task] = {}
        
        # Пул агентов
        self.agents: Dict[str, ReActAgent] = {}
        
        # Очереди
        self.input_queue = "tasks.input"
        self.output_queue = "tasks.output"
        self.dlq = "tasks.dlq"
        
        # Обработчики
        self.handlers: Dict[str, Callable] = {}
        
        # Флаг работы
        self.running = False
        
    def register_agent(self, task_type: str, agent: ReActAgent):
        """Регистрация агента для типа задачи."""
        self.agents[task_type] = agent
    
    def register_handler(self, task_type: str, handler: Callable):
        """Регистрация функции-обработчика для типа задачи."""
        self.handlers[task_type] = handler
    
    async def submit_task(self, task_type: str, payload: dict) -> str:
        """Отправка задачи в пайплайн."""
        import uuid
        
        task_id = str(uuid.uuid4())
        
        task = Task(
            id=task_id,
            type=task_type,
            payload=payload,
            status=TaskStatus.PENDING,
            result=None,
            created_at=datetime.now()
        )
        
        self.tasks[task_id] = task
        
        await self.mq.publish(self.input_queue, task.dict())
        
        return task_id
    
    async def get_result(self, task_id: str, timeout: float = 30.0) -> Optional[Task]:
        """Ожидание результата задачи."""
        start = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start < timeout:
            task = self.tasks.get(task_id)
            if task and task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                return task
            await asyncio.sleep(0.1)
        
        return None
    
    async def _worker(self, worker_id: int):
        """Корутина воркера."""
        print(f"Воркер {worker_id} запущен")
        
        while self.running:
            try:
                # Получаем задачу из очереди
                message = await asyncio.wait_for(
                    self.mq.consume(self.input_queue),
                    timeout=1.0
                )
                
                task = Task(**message)
                self.tasks[task.id] = task
                task.status = TaskStatus.PROCESSING
                
                print(f"Воркер {worker_id}: Обработка задачи {task.id} ({task.type})")
                
                try:
                    result = await self._process_task(task)
                    
                    task.status = TaskStatus.COMPLETED
                    task.result = result
                    task.completed_at = datetime.now()
                    
                    await self.mq.publish(self.output_queue, task.dict())
                    
                except Exception as e:
                    print(f"Воркер {worker_id}: Задача {task.id} упала: {e}")
                    
                    task.retries += 1
                    
                    if task.retries < self.max_retries:
                        # Повторная попытка
                        task.status = TaskStatus.PENDING
                        await self.mq.publish(self.input_queue, task.dict())
                    else:
                        # Отправляем в DLQ
                        task.status = TaskStatus.FAILED
                        task.result = {"error": str(e)}
                        await self.mq.publish(self.dlq, task.dict())
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Ошибка воркера {worker_id}: {e}")
        
        print(f"Воркер {worker_id} остановлен")
    
    async def _process_task(self, task: Task) -> dict:
        """Обработка задачи зарегистрированным агентом или обработчиком."""
        
        # Проверяем агента
        if task.type in self.agents:
            agent = self.agents[task.type]
            
            prompt = task.payload.get("prompt", json.dumps(task.payload))
            result = agent.run(prompt)
            
            return {"response": result}
        
        # Проверяем обработчик
        if task.type in self.handlers:
            handler = self.handlers[task.type]
            
            if asyncio.iscoroutinefunction(handler):
                result = await handler(task.payload)
            else:
                result = handler(task.payload)
            
            return result
        
        raise ValueError(f"Нет агента или обработчика для типа задачи: {task.type}")
    
    async def start(self):
        """Запуск пайплайна."""
        self.running = True
        
        workers = [
            asyncio.create_task(self._worker(i))
            for i in range(self.num_workers)
        ]
        
        print(f"Пайплайн запущен с {self.num_workers} воркерами")
        
        try:
            await asyncio.gather(*workers)
        except asyncio.CancelledError:
            pass
    
    async def stop(self):
        """Остановка пайплайна."""
        self.running = False
        await asyncio.sleep(1)  # Даём воркерам завершиться
    
    def get_stats(self) -> dict:
        """Получить статистику пайплайна."""
        tasks = list(self.tasks.values())
        
        return {
            "total_tasks": len(tasks),
            "pending": len([t for t in tasks if t.status == TaskStatus.PENDING]),
            "processing": len([t for t in tasks if t.status == TaskStatus.PROCESSING]),
            "completed": len([t for t in tasks if t.status == TaskStatus.COMPLETED]),
            "failed": len([t for t in tasks if t.status == TaskStatus.FAILED]),
            "avg_latency_ms": self._calculate_avg_latency(tasks)
        }
    
    def _calculate_avg_latency(self, tasks: List[Task]) -> float:
        completed = [t for t in tasks if t.completed_at]
        if not completed:
            return 0
        
        latencies = [
            (t.completed_at - t.created_at).total_seconds() * 1000
            for t in completed
        ]
        return sum(latencies) / len(latencies)

# Использование
async def main():
    pipeline = EventDrivenAgentPipeline(num_workers=4)
    
    # Регистрируем агентов
    qa_agent = ReActAgent.from_openai(
        "gpt-4o",
        tools=[],
        system_prompt="Отвечай на вопросы точно и кратко."
    )
    pipeline.register_agent("qa", qa_agent)
    
    # Регистрируем кастомный обработчик
    async def summarize_handler(payload: dict) -> dict:
        llm = RLM.from_openai("gpt-4o-mini")
        text = payload.get("text", "")
        summary = llm.run(f"Суммаризируй: {text[:1000]}")
        return {"summary": summary}
    
    pipeline.register_handler("summarize", summarize_handler)
    
    # Запускаем пайплайн в фоне
    pipeline_task = asyncio.create_task(pipeline.start())
    
    # Отправляем задачи
    task1_id = await pipeline.submit_task("qa", {"prompt": "Что такое Python?"})
    task2_id = await pipeline.submit_task("summarize", {"text": "Длинный текст здесь..."})
    
    # Ждём результатов
    result1 = await pipeline.get_result(task1_id)
    result2 = await pipeline.get_result(task2_id)
    
    print(f"Задача 1: {result1.result if result1 else 'Таймаут'}")
    print(f"Задача 2: {result2.result if result2 else 'Таймаут'}")
    
    # Статистика
    print(f"Статистика: {pipeline.get_stats()}")
    
    # Очистка
    await pipeline.stop()
    pipeline_task.cancel()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 19. Полный стек наблюдаемости

Комплексный мониторинг с Langfuse, Prometheus и Grafana dashboards.

```python
from rlm_toolkit import RLM
from rlm_toolkit.callbacks import BaseCallback, LangfuseCallback
from prometheus_client import Counter, Histogram, Gauge, start_http_server
from pydantic import BaseModel
from typing import Dict, List, Optional
import time
import json
import logging

# Prometheus метрики
LLM_REQUESTS = Counter(
    'rlm_requests_total',
    'Всего LLM запросов',
    ['provider', 'model', 'status']
)

LLM_LATENCY = Histogram(
    'rlm_latency_seconds',
    'Латентность LLM запросов',
    ['provider', 'model'],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

LLM_TOKENS = Counter(
    'rlm_tokens_total',
    'Всего использовано токенов',
    ['provider', 'model', 'type']
)

LLM_COST = Counter(
    'rlm_cost_usd_total',
    'Общая стоимость в USD',
    ['provider', 'model']
)

ACTIVE_SESSIONS = Gauge(
    'rlm_active_sessions',
    'Количество активных сессий'
)

ERROR_RATE = Counter(
    'rlm_errors_total',
    'Всего ошибок',
    ['provider', 'model', 'error_type']
)

class PrometheusCallback(BaseCallback):
    """Prometheus callback для метрик."""
    
    def __init__(self, provider: str, model: str):
        self.provider = provider
        self.model = model
        self.start_time = None
        
    def on_llm_start(self, prompt: str, **kwargs):
        self.start_time = time.time()
        
    def on_llm_end(self, response: str, **kwargs):
        latency = time.time() - self.start_time if self.start_time else 0
        
        LLM_REQUESTS.labels(
            provider=self.provider,
            model=self.model,
            status="success"
        ).inc()
        
        LLM_LATENCY.labels(
            provider=self.provider,
            model=self.model
        ).observe(latency)
        
        tokens = kwargs.get("tokens", {})
        if tokens:
            LLM_TOKENS.labels(
                provider=self.provider,
                model=self.model,
                type="prompt"
            ).inc(tokens.get("prompt_tokens", 0))
            
            LLM_TOKENS.labels(
                provider=self.provider,
                model=self.model,
                type="completion"
            ).inc(tokens.get("completion_tokens", 0))
        
        cost = kwargs.get("cost", 0)
        if cost:
            LLM_COST.labels(
                provider=self.provider,
                model=self.model
            ).inc(cost)
    
    def on_llm_error(self, error: Exception, **kwargs):
        LLM_REQUESTS.labels(
            provider=self.provider,
            model=self.model,
            status="error"
        ).inc()
        
        ERROR_RATE.labels(
            provider=self.provider,
            model=self.model,
            error_type=type(error).__name__
        ).inc()


class ObservabilityStack:
    """
    Полный стек наблюдаемости:
    1. Langfuse для LLM traces
    2. Prometheus метрики
    3. Структурированное логирование
    4. Генерация dashboard
    """
    
    def __init__(
        self,
        langfuse_public_key: str = None,
        langfuse_secret_key: str = None,
        prometheus_port: int = 9090
    ):
        # Langfuse трейсинг
        self.langfuse_callback = None
        if langfuse_public_key and langfuse_secret_key:
            self.langfuse_callback = LangfuseCallback(
                public_key=langfuse_public_key,
                secret_key=langfuse_secret_key
            )
        
        # Запуск Prometheus сервера
        start_http_server(prometheus_port)
        print(f"Prometheus метрики на http://localhost:{prometheus_port}")
        
        # Структурированное логирование
        logging.basicConfig(
            level=logging.INFO,
            format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": %(message)s}'
        )
        self.logger = logging.getLogger("rlm")
        
        # Отслеживание сессий
        self.sessions: Dict[str, dict] = {}
        
    def create_monitored_llm(
        self,
        provider: str,
        model: str,
        **kwargs
    ) -> RLM:
        """Создание LLM с полной наблюдаемостью."""
        
        callbacks = [
            PrometheusCallback(provider, model)
        ]
        
        if self.langfuse_callback:
            callbacks.append(self.langfuse_callback)
        
        if provider == "openai":
            llm = RLM.from_openai(model, callbacks=callbacks, **kwargs)
        elif provider == "anthropic":
            llm = RLM.from_anthropic(model, callbacks=callbacks, **kwargs)
        else:
            llm = RLM.from_openai(model, callbacks=callbacks, **kwargs)
        
        return llm
    
    def start_session(self, session_id: str, metadata: dict = None):
        """Начало мониторируемой сессии."""
        self.sessions[session_id] = {
            "start_time": time.time(),
            "metadata": metadata or {},
            "requests": 0
        }
        ACTIVE_SESSIONS.inc()
        
        self._log("session_started", {
            "session_id": session_id,
            "metadata": metadata
        })
    
    def end_session(self, session_id: str):
        """Завершение мониторируемой сессии."""
        if session_id in self.sessions:
            session = self.sessions.pop(session_id)
            ACTIVE_SESSIONS.dec()
            
            self._log("session_ended", {
                "session_id": session_id,
                "duration_seconds": time.time() - session["start_time"],
                "requests": session["requests"]
            })
    
    def _log(self, event: str, data: dict):
        """Структурированное логирование."""
        self.logger.info(json.dumps({
            "event": event,
            **data
        }))
    
    def generate_grafana_dashboard(self) -> dict:
        """Генерация JSON для Grafana dashboard."""
        return {
            "title": "RLM-Toolkit Наблюдаемость",
            "panels": [
                {
                    "title": "Request Rate",
                    "type": "graph",
                    "targets": [{
                        "expr": "rate(rlm_requests_total[5m])",
                        "legendFormat": "{{provider}}/{{model}}"
                    }]
                },
                {
                    "title": "Латентность (p50, p95, p99)",
                    "type": "graph",
                    "targets": [
                        {"expr": "histogram_quantile(0.5, rate(rlm_latency_seconds_bucket[5m]))", "legendFormat": "p50"},
                        {"expr": "histogram_quantile(0.95, rate(rlm_latency_seconds_bucket[5m]))", "legendFormat": "p95"},
                        {"expr": "histogram_quantile(0.99, rate(rlm_latency_seconds_bucket[5m]))", "legendFormat": "p99"}
                    ]
                },
                {
                    "title": "Использование токенов",
                    "type": "graph",
                    "targets": [{
                        "expr": "rate(rlm_tokens_total[5m])",
                        "legendFormat": "{{type}}"
                    }]
                },
                {
                    "title": "Стоимость за час",
                    "type": "stat",
                    "targets": [{
                        "expr": "increase(rlm_cost_usd_total[1h])"
                    }]
                },
                {
                    "title": "Error Rate",
                    "type": "graph",
                    "targets": [{
                        "expr": "rate(rlm_errors_total[5m])",
                        "legendFormat": "{{error_type}}"
                    }]
                },
                {
                    "title": "Активные сессии",
                    "type": "gauge",
                    "targets": [{
                        "expr": "rlm_active_sessions"
                    }]
                }
            ]
        }
    
    def get_health_status(self) -> dict:
        """Получить текущий статус здоровья."""
        return {
            "status": "healthy",
            "active_sessions": len(self.sessions),
            "prometheus": "running",
            "langfuse": "connected" if self.langfuse_callback else "disabled"
        }

# Использование
if __name__ == "__main__":
    # Инициализация наблюдаемости
    obs = ObservabilityStack(
        langfuse_public_key="pk-...",
        langfuse_secret_key="sk-...",
        prometheus_port=9090
    )
    
    # Создаём мониторируемый LLM
    llm = obs.create_monitored_llm("openai", "gpt-4o")
    
    # Начало сессии
    obs.start_session("user-123", {"user_id": "123", "tier": "premium"})
    
    # Делаем запросы (автоматически трекаются)
    response = llm.run("Что такое Python?")
    print(response)
    
    # Завершение сессии
    obs.end_session("user-123")
    
    # Генерируем dashboard
    dashboard = obs.generate_grafana_dashboard()
    with open("grafana_dashboard.json", "w") as f:
        json.dump(dashboard, f, indent=2)
    
    # Проверка здоровья
    print(obs.get_health_status())
```

---

## Сводка

Это завершает все 19 продвинутых примеров:

| # | Пример | Категория | Строк |
|---|--------|-----------|-------|
| 1 | Автономный исследовательский агент | Enterprise | ~300 |
| 2 | Мультимодальный RAG пайплайн | Enterprise | ~350 |
| 3 | Агент ревью кода | Enterprise | ~400 |
| 4 | Анализатор юридических документов | Enterprise | ~450 |
| 5 | Ассистент трейдинга в реальном времени | Enterprise | ~400 |
| 6 | Самоулучшающийся генератор кода | R&D | ~350 |
| 7 | Построитель графа знаний | R&D | ~400 |
| 8 | Семантический поиск по коду | R&D | ~350 |
| 9 | Система мультиагентных дебатов | R&D | ~400 |
| 10 | Рекурсивный суммаризатор документов | R&D | ~400 |
| 11 | Детектор Prompt Injection | Security | ~450 |
| 12 | Безопасный мультитенантный RAG | Security | ~400 |
| 13 | Система аудиторского следа | Security | ~450 |
| 14 | Red Team агент | Security | ~450 |
| 15 | High-Availability RAG кластер | Production | ~350 |
| 16 | Фреймворк A/B-тестирования | Production | ~400 |
| 17 | Семантический кэш с Fallback | Production | ~350 |
| 18 | Event-Driven Agent Pipeline | Production | ~400 |
| 19 | Полный стек наблюдаемости | Production | ~350 |

**Всего: ~7,500 строк production-ready кода**

---

## Связанное

- [Базовые примеры](./index.md)
- [API Reference](../reference/)
- [Туториалы](../tutorials/)
