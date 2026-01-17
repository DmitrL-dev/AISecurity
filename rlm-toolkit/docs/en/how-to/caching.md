# How-to: Caching

Recipes for caching LLM responses and embeddings.

## LLM Response Caching

```python
from rlm_toolkit import RLM
from rlm_toolkit.cache import InMemoryCache

cache = InMemoryCache()
rlm = RLM.from_openai("gpt-4o", cache=cache)

# First call - API request
response1 = rlm.run("What is Python?")

# Second call - from cache (instant)
response2 = rlm.run("What is Python?")
```

## Redis Cache

```python
from rlm_toolkit.cache import RedisCache

cache = RedisCache(
    host="localhost",
    port=6379,
    ttl=3600  # 1 hour TTL
)

rlm = RLM.from_openai("gpt-4o", cache=cache)
```

## SQLite Cache

```python
from rlm_toolkit.cache import SQLiteCache

cache = SQLiteCache(
    database_path="./cache.db",
    ttl=86400  # 24 hours
)

rlm = RLM.from_openai("gpt-4o", cache=cache)
```

## Disk Cache

```python
from rlm_toolkit.cache import DiskCache

cache = DiskCache(
    cache_dir="./llm_cache",
    max_size_gb=10
)
```

## Embedding Cache

```python
from rlm_toolkit.embeddings import OpenAIEmbeddings, CachedEmbeddings

base_embeddings = OpenAIEmbeddings("text-embedding-3-small")

cached = CachedEmbeddings(
    embeddings=base_embeddings,
    cache_dir="./embedding_cache"
)

# First call - computes embedding
vector1 = cached.embed_query("Hello")

# Second call - from cache
vector2 = cached.embed_query("Hello")
```

## Semantic Cache

```python
from rlm_toolkit.cache import SemanticCache
from rlm_toolkit.embeddings import OpenAIEmbeddings

# Cache similar queries, not just exact matches
cache = SemanticCache(
    embeddings=OpenAIEmbeddings(),
    similarity_threshold=0.95
)

rlm = RLM.from_openai("gpt-4o", cache=cache)

# These might hit the same cache entry:
rlm.run("What is Python?")
rlm.run("What's Python?")  # Similar enough
```

## Disable Cache

```python
# Per-call disable
response = rlm.run("Fresh response needed", use_cache=False)

# Global disable
rlm = RLM.from_openai("gpt-4o", cache=None)
```

## Clear Cache

```python
cache.clear()

# Clear specific key
cache.delete("What is Python?")
```

## Cache Statistics

```python
print(f"Cache hits: {cache.hits}")
print(f"Cache misses: {cache.misses}")
print(f"Hit rate: {cache.hit_rate:.2%}")
```

## Custom Cache

```python
from rlm_toolkit.cache import BaseCache

class MyCache(BaseCache):
    def get(self, key: str) -> str | None:
        # Your retrieval logic
        pass
    
    def set(self, key: str, value: str, ttl: int = None):
        # Your storage logic
        pass
    
    def delete(self, key: str):
        pass
    
    def clear(self):
        pass
```

## Related

- [How-to: Providers](./providers.md)
- [How-to: Embeddings](./embeddings.md)
