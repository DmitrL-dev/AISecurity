# Концепция безопасности

RLM-Toolkit включает функции безопасности уровня SENTINEL для enterprise AI-приложений.

## Функции безопасности

### Зоны доверия
Уровни изоляции памяти и агентов:

| Зона | Уровень | Применение |
|------|---------|------------|
| `public` | 0 | Пользовательский контент |
| `internal` | 1 | Бизнес-логика |
| `confidential` | 2 | Персональные данные |
| `secret` | 3 | Высокочувствительные |

```python
from rlm_toolkit.memory import SecureHierarchicalMemory

memory = SecureHierarchicalMemory(
    trust_zone="confidential",
    encryption_enabled=True
)
```

### Безопасное выполнение кода
CIRCLE-совместимая песочница:

```python
from rlm_toolkit.tools import SecurePythonREPL

repl = SecurePythonREPL(
    allowed_imports=["math", "json"],
    max_execution_time=5,
    enable_network=False
)
```

### Шифрование
AES-256-GCM для данных в покое:

```python
memory = SecureHierarchicalMemory(
    encryption_key="your-256-bit-key",
    encryption_algorithm="AES-256-GCM"
)
```

### Логирование аудита
Полная история операций:

```python
memory = SecureHierarchicalMemory(
    audit_enabled=True,
    audit_log_path="./audit.log"
)
```

## Безопасность агентов

Безопасная коммуникация между агентами:

```python
from rlm_toolkit.agents import SecureAgent, TrustZone

agent = SecureAgent(
    name="data_handler",
    trust_zone=TrustZone(name="confidential", level=2),
    encryption_enabled=True
)
```

## Связанное

- [Туториал: Multi-Agent](../tutorials/09-multiagent.md)
- [Туториал: H-MEM](../tutorials/07-hmem.md)
