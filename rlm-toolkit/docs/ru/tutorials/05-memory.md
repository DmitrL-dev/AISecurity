# Туториал 5: Системы памяти

Глубокое погружение в системы памяти RLM-Toolkit для создания AI-приложений, которые помнят.

## Обзор типов памяти

| Тип | Применение | Персистентность | Лучше всего для |
|-----|------------|-----------------|-----------------|
| **BufferMemory** | Простой чат | Сессия | Базовые чат-боты |
| **EpisodicMemory** | Отслеживание сущностей | Сессия | Служба поддержки |
| **HierarchicalMemory** | Сложные приложения | Между сессиями | Продвинутые ассистенты |
| **SecureHierarchicalMemory** | Чувствительные данные | Шифрование | Enterprise |

## BufferMemory

Простой буфер разговора:

```python
from rlm_toolkit import RLM
from rlm_toolkit.memory import BufferMemory

# Создаём буферную память
memory = BufferMemory(
    max_messages=100,       # Хранить последние 100 сообщений
    return_messages=True    # Возвращать как объекты сообщений
)

rlm = RLM.from_openai("gpt-4o", memory=memory)

# Сообщения сохраняются
rlm.run("Привет, я Алиса")
rlm.run("Я работаю в TechCorp")

# Доступ к памяти
for msg in memory.get_messages():
    print(f"{msg.role}: {msg.content}")
```

### Опции BufferMemory

```python
# Буфер с ограничением по токенам
memory = BufferMemory(
    max_tokens=4000,  # Ограничение по токенам вместо сообщений
    model="gpt-4o"    # Для подсчёта токенов
)

# Суммирующий буфер - суммирует старые сообщения
memory = BufferMemory(
    max_messages=20,
    summarize_after=10,     # Суммировать когда больше 10 сообщений
    summary_llm=provider    # LLM для суммирования
)
```

## EpisodicMemory

Хранит информацию как пары сущность-факт:

```python
from rlm_toolkit.memory import EpisodicMemory

memory = EpisodicMemory()
rlm = RLM.from_openai("gpt-4o", memory=memory)

# Сохраняем факты о сущностях
rlm.run("Ивану 30 лет, он работает в Google")
rlm.run("Мария — жена Ивана. Она врач.")
rlm.run("Они живут в Санкт-Петербурге")

# Память хранит:
# Сущность: Иван -> возраст: 30, работодатель: Google
# Сущность: Мария -> отношение: жена Ивана, профессия: врач
# Сущность: Иван, Мария -> место: Санкт-Петербург

# Запрос конкретных сущностей
result = rlm.run("Где работает Иван?")
# Использует поиск по сущностям для быстрого извлечения
```

### Ручной доступ к сущностям

```python
# Получить все сущности
entities = memory.get_entities()
print(entities)  # ['Иван', 'Мария']

# Получить факты о сущности
facts = memory.get_entity_facts("Иван")
print(facts)  # {'возраст': '30', 'работодатель': 'Google'}

# Добавить факты вручную
memory.add_fact("Иван", "хобби", "теннис")
```

## HierarchicalMemory (H-MEM)

4-уровневая память с LLM-консолидацией:

```python
from rlm_toolkit.memory import HierarchicalMemory

memory = HierarchicalMemory(
    # Уровень 0: Эпизоды (сырые сообщения)
    episode_limit=100,
    
    # Уровень 1: Трейсы (группировка по темам)
    trace_limit=50,
    
    # Уровень 2: Категории (суммированные концепции)
    category_limit=20,
    
    # Уровень 3: Домен (мета-знания)
    domain_limit=10,
    
    # Настройки консолидации
    consolidation_enabled=True,
    consolidation_threshold=20,  # Консолидация после 20 эпизодов
    consolidation_llm=None       # Использует основной LLM если не указан
)

rlm = RLM.from_openai("gpt-4o", memory=memory)
```

### Объяснение уровней памяти

```
┌─────────────────────────────────────────────────────────────────┐
│                    Архитектура H-MEM                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Уровень 0: Эпизод    "Пользователь сказал: меня зовут Алекс"   │
│      ↓ консолидация                                             │
│  Уровень 1: Трейс     "Пользователь: Алекс, профессия: инженер" │
│      ↓ консолидация                                             │
│  Уровень 2: Категория "Профиль и предпочтения пользователя"     │
│      ↓ консолидация                                             │
│  Уровень 3: Домен     "Технический пользователь, интересуется AI"│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Персистентность

```python
# Сохранение на диск
memory = HierarchicalMemory(
    persist_directory="./memory_store",
    auto_save=True,         # Сохранять после каждого обновления
    save_interval=60        # Или сохранять каждые 60 секунд
)

# Позже, загрузка с диска
memory2 = HierarchicalMemory(
    persist_directory="./memory_store"
)
# Автоматически загружает существующую память
```

### Память между сессиями

```python
# Сессия 1
memory = HierarchicalMemory(persist_directory="./user_123_memory")
rlm = RLM.from_openai("gpt-4o", memory=memory)
rlm.run("Я предпочитаю тёмную тему и программирование на Python")
# Память сохраняется автоматически

# Сессия 2 (дни спустя)
memory = HierarchicalMemory(persist_directory="./user_123_memory")
rlm = RLM.from_openai("gpt-4o", memory=memory)
result = rlm.run("Какие мои предпочтения?")
# Помнит: тёмная тема, Python
```

## SecureHierarchicalMemory

Шифрованная память с зонами доверия:

```python
from rlm_toolkit.memory import SecureHierarchicalMemory

memory = SecureHierarchicalMemory(
    # Шифрование
    encryption_key="your-32-byte-encryption-key-here",
    encryption_algorithm="AES-256-GCM",
    
    # Зоны доверия
    trust_zone="confidential",  # public, internal, confidential, secret
    
    # Аудит
    audit_enabled=True,
    audit_log_path="./memory_audit.log",
    
    # Персистентность
    persist_directory="./secure_memory"
)

rlm = RLM.from_openai("gpt-4o", memory=memory)
```

### Зоны доверия

```python
# Определение доступа по зонам доверия
from rlm_toolkit.memory import TrustZone

zones = {
    "public": TrustZone(
        name="public",
        access_level=0,
        can_share=True
    ),
    "internal": TrustZone(
        name="internal",
        access_level=1,
        can_share=False
    ),
    "confidential": TrustZone(
        name="confidential",
        access_level=2,
        requires_encryption=True
    ),
    "secret": TrustZone(
        name="secret",
        access_level=3,
        requires_encryption=True,
        audit_required=True
    )
}

memory = SecureHierarchicalMemory(
    trust_zones=zones,
    default_zone="internal"
)
```

## Интеграция памяти

### С RAG

```python
from rlm_toolkit import RLM
from rlm_toolkit.memory import HierarchicalMemory
from rlm_toolkit.vectorstores import ChromaVectorStore

# Память для контекста разговора
memory = HierarchicalMemory()

# Векторное хранилище для извлечения документов
vectorstore = ChromaVectorStore.from_documents(docs, embeddings)

# Комбинируем оба
rlm = RLM.from_openai(
    "gpt-4o",
    memory=memory,
    retriever=vectorstore.as_retriever()
)
```

### С агентами

```python
from rlm_toolkit import RLM
from rlm_toolkit.memory import HierarchicalMemory
from rlm_toolkit.tools import Calculator, WebSearch

memory = HierarchicalMemory(
    persist_directory="./agent_memory"
)

rlm = RLM.from_openai(
    "gpt-4o",
    memory=memory,
    tools=[Calculator(), WebSearch()]
)

# Память сохраняется при использовании инструментов
rlm.run("Посчитай 15% от 200")
rlm.run("Теперь найди эту сумму в долларах")  # Помнит: 30
```

## Лучшие практики

!!! tip "Выбирайте правильную память"
    - Простой чат-бот: `BufferMemory`
    - CRM/Служба поддержки: `EpisodicMemory`
    - Персональный ассистент: `HierarchicalMemory`
    - Enterprise: `SecureHierarchicalMemory`

!!! tip "Лимиты памяти"
    Устанавливайте подходящие лимиты для избежания переполнения контекста:
    ```python
    memory = HierarchicalMemory(
        episode_limit=100,
        context_token_limit=4000
    )
    ```

!!! tip "Консолидация"
    Включайте консолидацию для долгоживущих приложений:
    ```python
    memory = HierarchicalMemory(
        consolidation_enabled=True,
        consolidation_threshold=20
    )
    ```

!!! warning "Приватность"
    Для чувствительных данных всегда используйте `SecureHierarchicalMemory` с шифрованием.

## Следующие шаги

- [Туториал 6: InfiniRetri](06-infiniretri.md)
- [Концепция: Архитектура H-MEM](../concepts/hmem.md)
- [Концепция: Системы памяти](../concepts/memory.md)
