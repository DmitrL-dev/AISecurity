# How-to: Кэширование

Рецепты кэширования ответов LLM и эмбеддингов.

## Кэширование ответов LLM

```python
from rlm_toolkit import RLM
from rlm_toolkit.cache import InMemoryCache

cache = InMemoryCache()
rlm = RLM.from_openai("gpt-4o", cache=cache)

# Первый вызов - API запрос
response1 = rlm.run("Что такое Python?")

# Второй вызов - из кэша (мгновенно)
response2 = rlm.run("Что такое Python?")
```

## Redis кэш

```python
from rlm_toolkit.cache import RedisCache

cache = RedisCache(
    host="localhost",
    port=6379,
    ttl=3600  # 1 час TTL
)

rlm = RLM.from_openai("gpt-4o", cache=cache)
```

## SQLite кэш

```python
from rlm_toolkit.cache import SQLiteCache

cache = SQLiteCache(
    database_path="./cache.db",
    ttl=86400  # 24 часа
)

rlm = RLM.from_openai("gpt-4o", cache=cache)
```

## Дисковый кэш

```python
from rlm_toolkit.cache import DiskCache

cache = DiskCache(
    cache_dir="./llm_cache",
    max_size_gb=10
)
```

## Кэширование эмбеддингов

```python
from rlm_toolkit.embeddings import OpenAIEmbeddings, CachedEmbeddings

base_embeddings = OpenAIEmbeddings("text-embedding-3-small")

cached = CachedEmbeddings(
    embeddings=base_embeddings,
    cache_dir="./embedding_cache"
)

# Первый вызов - вычисление эмбеддинга
vector1 = cached.embed_query("Привет")

# Второй вызов - из кэша
vector2 = cached.embed_query("Привет")
```

## Семантический кэш

```python
from rlm_toolkit.cache import SemanticCache
from rlm_toolkit.embeddings import OpenAIEmbeddings

# Кэширует похожие запросы, не только точные совпадения
cache = SemanticCache(
    embeddings=OpenAIEmbeddings(),
    similarity_threshold=0.95
)

rlm = RLM.from_openai("gpt-4o", cache=cache)

# Эти запросы могут попасть в одну запись кэша:
rlm.run("Что такое Python?")
rlm.run("Что есть Python?")  # Достаточно похоже
```

## Отключение кэша

```python
# Отключение для конкретного вызова
response = rlm.run("Нужен свежий ответ", use_cache=False)

# Глобальное отключение
rlm = RLM.from_openai("gpt-4o", cache=None)
```

## Очистка кэша

```python
cache.clear()

# Удаление конкретного ключа
cache.delete("Что такое Python?")
```

## Статистика кэша

```python
print(f"Попаданий в кэш: {cache.hits}")
print(f"Промахов кэша: {cache.misses}")
print(f"Hit rate: {cache.hit_rate:.2%}")
```

## Пользовательский кэш

```python
from rlm_toolkit.cache import BaseCache

class MyCache(BaseCache):
    def get(self, key: str) -> str | None:
        # Ваша логика извлечения
        pass
    
    def set(self, key: str, value: str, ttl: int = None):
        # Ваша логика сохранения
        pass
    
    def delete(self, key: str):
        pass
    
    def clear(self):
        pass
```

## Связанное

- [How-to: Провайдеры](./providers.md)
- [How-to: Эмбеддинги](./embeddings.md)
