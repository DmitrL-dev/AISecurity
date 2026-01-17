# How-to: Настройка памяти

Рецепты настройки систем памяти в RLM-Toolkit.

## Базовая буферная память

```python
from rlm_toolkit import RLM
from rlm_toolkit.memory import BufferMemory

memory = BufferMemory(max_messages=100)
rlm = RLM.from_openai("gpt-4o", memory=memory)

response = rlm.run("Привет, я Алексей")
response = rlm.run("Как меня зовут?")  # "Вас зовут Алексей"
```

## Память с лимитом токенов

```python
from rlm_toolkit.memory import TokenBufferMemory

memory = TokenBufferMemory(
    max_tokens=4000,
    model="gpt-4o"
)
```

## Суммирующая память

```python
from rlm_toolkit.memory import SummaryMemory

memory = SummaryMemory(
    summarizer=RLM.from_openai("gpt-4o-mini"),
    max_tokens=2000
)
```

## Персистентная память (H-MEM)

```python
from rlm_toolkit.memory import HierarchicalMemory, HMEMConfig

config = HMEMConfig(
    episode_limit=100,
    consolidation_enabled=True,
    consolidation_threshold=25
)

memory = HierarchicalMemory(
    config=config,
    persist_directory="./memory"
)
```

## Защищённая память с шифрованием

```python
from rlm_toolkit.memory import SecureHierarchicalMemory

memory = SecureHierarchicalMemory(
    persist_directory="./secure_memory",
    encryption_key="your-256-bit-key",
    encryption_algorithm="AES-256-GCM",
    trust_zone="confidential"
)
```

## Очистка памяти

```python
memory.clear()
```

## Экспорт/импорт памяти

```python
# Экспорт
memory.save("./memory_backup.json")

# Импорт
memory.load("./memory_backup.json")
```

## Память с зонами доверия

```python
from rlm_toolkit.memory import SecureHierarchicalMemory, TrustZone

memory = SecureHierarchicalMemory(
    trust_zone=TrustZone(name="confidential", level=2),
    audit_enabled=True
)
```

## Связанное

- [Концепция: Память](../concepts/memory.md)
- [Туториал: Системы памяти](../tutorials/05-memory.md)
- [Туториал: H-MEM](../tutorials/07-hmem.md)
