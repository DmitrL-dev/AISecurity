# Системы памяти

RLM-Toolkit предоставляет комплексное управление памятью от простых буферов до продвинутых иерархических систем.

## Типы памяти

### Обзор

| Тип | Персистентность | Сложность | Применение |
|-----|-----------------|-----------|------------|
| **BufferMemory** | Сессия | Простая | Короткие разговоры |
| **SummaryMemory** | Сессия | Средняя | Длинные разговоры |
| **EntityMemory** | Сессия | Средняя | Отслеживание сущностей |
| **EpisodicMemory** | Персистентная | Средняя | Кросс-сессионная |
| **HierarchicalMemory (H-MEM)** | Персистентная | Высокая | Долгосрочное обучение |
| **SecureHierarchicalMemory** | Персистентная | Высокая | Enterprise безопасность |

## BufferMemory

Хранит сырую историю разговора.

```python
from rlm_toolkit.memory import BufferMemory

memory = BufferMemory(
    max_messages=100,      # Хранить последние 100 сообщений
    return_messages=True   # Возвращать как Message объекты
)

# Добавление сообщений
memory.add_user_message("Привет!")
memory.add_ai_message("Привет! Чем могу помочь?")

# Получение истории
history = memory.get_history()
print(history)
# [Message(role='user', content='Привет!'), 
#  Message(role='ai', content='Привет! Чем могу помочь?')]

# Использование с RLM
rlm = RLM.from_openai("gpt-4o", memory=memory)
```

### Буфер с лимитом токенов

```python
from rlm_toolkit.memory import TokenBufferMemory

memory = TokenBufferMemory(
    max_tokens=4000,           # Лимит токенов
    model="gpt-4o",            # Для токенизации
    overflow_strategy="oldest" # Удалять самые старые
)
```

## SummaryMemory

Суммирует разговор когда становится слишком длинным.

```python
from rlm_toolkit.memory import SummaryMemory

memory = SummaryMemory(
    summarizer=RLM.from_openai("gpt-4o-mini"),
    max_tokens=2000,
    summary_prompt="Кратко суммируйте этот разговор:"
)

# Автоматически суммирует при превышении max_tokens
for i in range(100):
    memory.add_user_message(f"Вопрос {i}")
    memory.add_ai_message(f"Ответ {i}")

# Получить контекст (включает резюме + последние сообщения)
context = memory.get_context()
```

## EntityMemory

Отслеживает сущности упомянутые в разговоре.

```python
from rlm_toolkit.memory import EntityMemory

memory = EntityMemory(
    entity_extractor=RLM.from_openai("gpt-4o-mini")
)

memory.add_user_message("Меня зовут Алексей и я работаю в ТехКорп")
memory.add_ai_message("Рад знакомству, Алексей! Расскажите о ТехКорп.")

# Доступ к сущностям
print(memory.entities)
# {
#   "Алексей": {"type": "person", "facts": ["работает в ТехКорп"]},
#   "ТехКорп": {"type": "organization", "facts": ["Алексей работает здесь"]}
# }

# Запрос сущности
print(memory.get_entity("Алексей"))
```

## EpisodicMemory

Персистентная память между сессиями.

```python
from rlm_toolkit.memory import EpisodicMemory

memory = EpisodicMemory(
    persist_directory="./memory",
    embedding=OpenAIEmbeddings(),
    max_episodes=1000
)

# Эпизоды сохраняются с timestamps
memory.add_episode(
    user_message="Как настроить Redis?",
    ai_response="Вот как настроить Redis...",
    metadata={"topic": "configuration"}
)

# Семантическое извлечение релевантных эпизодов
relevant = memory.retrieve(
    query="Настройка Redis",
    k=5
)
```

## HierarchicalMemory (H-MEM)

4-уровневая память с LLM-консолидацией.

```python
from rlm_toolkit.memory import HierarchicalMemory, HMEMConfig

config = HMEMConfig(
    episode_limit=100,
    trace_limit=50,
    category_limit=20,
    domain_limit=10,
    consolidation_enabled=True,
    consolidation_threshold=25
)

memory = HierarchicalMemory(
    config=config,
    persist_directory="./hmem",
    consolidator=RLM.from_openai("gpt-4o-mini")
)

# Добавление воспоминаний
memory.add_episode(user="Я Python разработчик", ai="Отлично!")
memory.add_episode(user="Использую PyTorch для ML", ai="PyTorch отличный!")

# После 25+ эпизодов, консолидация запускается:
# Episode → Trace → Category → Domain
# "Python разработчик, использует PyTorch" → "ML engineer профиль"
```

### Уровни H-MEM

```
┌─────────────────────────────────────────────────────────────────┐
│                    Архитектура H-MEM                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Уровень 3: Домен                                                │
│  └── "Технический пользователь, ML фокус, Python эксперт"       │
│           ↑                                                      │
│  Уровень 2: Категория                                            │
│  └── "Предпочтения: детальные объяснения, примеры кода"         │
│           ↑                                                      │
│  Уровень 1: Трейс                                                │
│  └── {user: "Алексей", skills: ["Python", "PyTorch"]}           │
│           ↑                                                      │
│  Уровень 0: Эпизод                                               │
│  └── "User: Я программирую на Python уже 5 лет"                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## SecureHierarchicalMemory

H-MEM с шифрованием и зонами доверия.

```python
from rlm_toolkit.memory import SecureHierarchicalMemory, TrustZone

memory = SecureHierarchicalMemory(
    persist_directory="./secure_memory",
    encryption_key="your-256-bit-key",
    encryption_algorithm="AES-256-GCM",
    trust_zone=TrustZone(name="confidential", level=2),
    audit_enabled=True,
    audit_log_path="./audit.log"
)

# Все данные зашифрованы at rest
memory.add_episode(user="Мой ИНН 123456789012", ai="Записал.")

# Аудит трейл
# 2024-01-15T10:30:00Z ADD_EPISODE user=admin zone=confidential
```

### Зоны доверия

| Зона | Уровень | Описание |
|------|---------|----------|
| `public` | 0 | Нечувствительные данные |
| `internal` | 1 | Внутренние бизнес-данные |
| `confidential` | 2 | Персональные/чувствительные данные |
| `secret` | 3 | Высокоограниченные данные |

## Память с RLM

```python
from rlm_toolkit import RLM
from rlm_toolkit.memory import HierarchicalMemory

memory = HierarchicalMemory(persist_directory="./memory")
rlm = RLM.from_openai("gpt-4o", memory=memory)

# Память автоматически заполняется
response = rlm.run("Привет, я Алексей, Python разработчик")
response = rlm.run("Какой ML фреймворк использовать?")
# AI помнит что пользователь Python разработчик
```

## Пользовательская память

```python
from rlm_toolkit.memory import BaseMemory

class RedisMemory(BaseMemory):
    def __init__(self, redis_url: str):
        self.redis = Redis.from_url(redis_url)
    
    def add_message(self, role: str, content: str):
        self.redis.lpush("messages", f"{role}:{content}")
    
    def get_history(self) -> list:
        return self.redis.lrange("messages", 0, -1)
    
    def clear(self):
        self.redis.delete("messages")
```

## Лучшие практики

!!! tip "Выбор памяти"
    - **Простые чат-боты**: BufferMemory
    - **Длинные разговоры**: SummaryMemory
    - **Фокус на сущностях**: EntityMemory
    - **Кросс-сессионная**: EpisodicMemory
    - **Долгосрочное обучение**: HierarchicalMemory

!!! tip "Управление токенами"
    Используйте TokenBufferMemory для предотвращения переполнения контекста:
    ```python
    memory = TokenBufferMemory(max_tokens=4000)
    ```

!!! tip "Персистентность"
    Всегда устанавливайте persist_directory для продакшна:
    ```python
    memory = HierarchicalMemory(persist_directory="./memory")
    ```

## Связанное

- [Туториал: Системы памяти](../tutorials/05-memory.md)
- [Туториал: H-MEM](../tutorials/07-hmem.md)
- [Концепция: H-MEM](./hmem.md)
- [Концепция: Безопасность](./security.md)
