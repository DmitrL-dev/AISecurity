# How-to: Настройка безопасности

Рецепты реализации функций безопасности.

## Защищённая память с шифрованием

```python
from rlm_toolkit.memory import SecureHierarchicalMemory

memory = SecureHierarchicalMemory(
    persist_directory="./secure_memory",
    encryption_key="your-256-bit-key",
    encryption_algorithm="AES-256-GCM"
)
```

## Зоны доверия

```python
from rlm_toolkit.memory import SecureHierarchicalMemory, TrustZone

memory = SecureHierarchicalMemory(
    trust_zone=TrustZone(name="confidential", level=2),
    audit_enabled=True,
    audit_log_path="./audit.log"
)
```

## Безопасное выполнение кода

```python
from rlm_toolkit.tools import SecurePythonREPL

repl = SecurePythonREPL(
    allowed_imports=["math", "json", "datetime"],
    max_execution_time=5,
    enable_network=False,
    sandbox_mode=True
)
```

## Безопасный агент

```python
from rlm_toolkit.agents import SecureAgent, TrustZone

agent = SecureAgent(
    name="data_handler",
    trust_zone=TrustZone(name="confidential", level=2),
    encryption_enabled=True,
    audit_enabled=True
)
```

## Включение логирования аудита

```python
memory = SecureHierarchicalMemory(
    audit_enabled=True,
    audit_log_path="./audit.log",
    log_format="json"
)

# Записи аудита:
# {"timestamp": "...", "action": "ADD_EPISODE", "zone": "confidential"}
```

## Валидация ввода

```python
from rlm_toolkit.tools import Tool
from pydantic import BaseModel, Field, validator

class SecureInput(BaseModel):
    query: str = Field(max_length=1000)
    
    @validator('query')
    def no_injection(cls, v):
        dangerous = ['exec', 'eval', '__import__']
        if any(d in v for d in dangerous):
            raise ValueError('Потенциально опасный ввод')
        return v

@Tool(name="secure_search", args_schema=SecureInput)
def search(query: str) -> str:
    return f"Результаты для: {query}"
```

## Rate limiting

```python
from rlm_toolkit.middleware import RateLimiter

limiter = RateLimiter(
    requests_per_minute=60,
    tokens_per_minute=100000
)

rlm = RLM.from_openai("gpt-4o", middleware=[limiter])
```

## Связанное

- [Концепция: Безопасность](../concepts/security.md)
- [Туториал: Multi-Agent](../tutorials/09-multiagent.md)
