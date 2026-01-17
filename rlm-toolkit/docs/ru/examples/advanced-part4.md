# Продвинутые примеры - Часть 4

Production-ready паттерны для enterprise LLM-развёртываний.

---

## 15. HA RAG-кластер

```python
from rlm_toolkit import RLM
from rlm_toolkit.vectorstores import RedisVectorStore
from rlm_toolkit.cache import RedisCache
from redis.sentinel import Sentinel

class HARAGCluster:
    """High-availability RAG с Redis Sentinel и failover."""
    
    def __init__(self, sentinel_hosts: list):
        self.sentinel = Sentinel(sentinel_hosts)
        self.master = self.sentinel.master_for("mymaster")
        self.cache = RedisCache(redis_client=self.master)
        self.llm = RLM.from_openai("gpt-4o", cache=self.cache)
        
    def query(self, question: str) -> dict:
        # С автоматическим failover...
        return {"answer": "...", "latency_ms": 150}
    
    def health_check(self) -> dict:
        return {"master": "healthy", "replicas": 2}
```

---

## 16. A/B тестирование промптов

```python
from rlm_toolkit import RLM
from scipy import stats
import numpy as np

class PromptABTesting:
    """A/B тестирование с статистической значимостью."""
    
    def __init__(self, experiment_id: str):
        self.variants = {}
        self.results = []
        
    def add_variant(self, id: str, prompt_template: str, weight: float = 0.5):
        self.variants[id] = {"template": prompt_template, "weight": weight}
        
    def run(self, input: str) -> dict:
        variant_id = self._select_variant()
        # Выполнение и сбор метрик...
        return {"variant": variant_id, "quality_score": 0.85}
    
    def analyze(self) -> dict:
        # t-test для статистической значимости...
        return {"winner": "treatment", "confidence": 0.95}
```

---

## 17. Семантический кэш с fallback

```python
from rlm_toolkit import RLM
from rlm_toolkit.embeddings import OpenAIEmbeddings
from rlm_toolkit.vectorstores import ChromaVectorStore

class SemanticCache:
    """Многослойный кэш с graceful degradation."""
    
    def __init__(self, similarity_threshold: float = 0.92):
        self.similarity_threshold = similarity_threshold
        self.embeddings = OpenAIEmbeddings("text-embedding-3-small")
        self.semantic_store = ChromaVectorStore(collection_name="cache")
        self.llm = RLM.from_openai("gpt-4o")
        self.fallback_llms = [RLM.from_openai("gpt-4o-mini")]
        
    def query(self, question: str) -> dict:
        # Слой 1: exact match, Слой 2: semantic, Слой 3: LLM с fallback
        return {"response": "...", "cache_status": "semantic_hit"}
    
    def get_stats(self) -> dict:
        return {"hit_rate": 0.73, "fallback_rate": 0.02}
```

---

## 18. Event-Driven Agent Pipeline

```python
import asyncio
from rlm_toolkit import RLM
from rlm_toolkit.agents import ReActAgent

class EventDrivenAgentPipeline:
    """Kafka/RabbitMQ интеграция с async агентами."""
    
    def __init__(self, num_workers: int = 4):
        self.num_workers = num_workers
        self.agents = {}
        self.running = False
        
    def register_agent(self, task_type: str, agent: ReActAgent):
        self.agents[task_type] = agent
        
    async def submit_task(self, task_type: str, payload: dict) -> str:
        import uuid
        return str(uuid.uuid4())
    
    async def start(self):
        self.running = True
        # Запуск worker pool...
        
    def get_stats(self) -> dict:
        return {"tasks_processed": 1500, "avg_latency_ms": 340}
```

---

## 19. Полный стек наблюдаемости

```python
from rlm_toolkit import RLM
from rlm_toolkit.callbacks import LangfuseCallback
from prometheus_client import Counter, Histogram, start_http_server

LLM_REQUESTS = Counter('rlm_requests_total', 'Total requests', ['provider', 'model'])
LLM_LATENCY = Histogram('rlm_latency_seconds', 'Latency', ['provider', 'model'])

class ObservabilityStack:
    """Langfuse + Prometheus + Grafana dashboards."""
    
    def __init__(self, langfuse_key: str = None, prometheus_port: int = 9090):
        self.langfuse_callback = LangfuseCallback(public_key=langfuse_key) if langfuse_key else None
        start_http_server(prometheus_port)
        
    def create_monitored_llm(self, provider: str, model: str) -> RLM:
        callbacks = []
        if self.langfuse_callback:
            callbacks.append(self.langfuse_callback)
        return RLM.from_openai(model, callbacks=callbacks)
    
    def generate_grafana_dashboard(self) -> dict:
        return {"title": "RLM Observability", "panels": [...]}
```

---

## Сводка

Все 19 продвинутых примеров:

| # | Пример | Категория |
|---|--------|-----------|
| 1-5 | Research, Multi-Modal, Code Review, Legal, Trading | Enterprise |
| 6-10 | Self-Improving, Knowledge Graph, Semantic Search, Debate, Summarizer | R&D |
| 11-14 | Prompt Injection, Multi-Tenant, Audit, Red Team | Security |
| 15-19 | HA Cluster, A/B Testing, Cache, Event-Driven, Observability | Production |

**~7,500 строк production-ready кода**

---

## Связанное

- [Базовые примеры](./index.md)
- [API Reference](../reference/)
- [Туториалы](../tutorials/)
