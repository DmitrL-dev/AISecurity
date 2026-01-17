# Туториал 7: Иерархическая память (H-MEM)

Создавайте AI-системы с человекоподобной памятью на основе 4-уровневой архитектуры.

## Что такое H-MEM?

H-MEM — революционная система памяти, которая:

- **4 уровня памяти**: Эпизод → Трейс → Категория → Домен
- **LLM-консолидация**: Автоматическое суммирование по уровням
- **Персистентность между сессиями**: Помнит между разговорами
- **Интеграция безопасности**: Зоны доверия и шифрование

## Архитектура H-MEM

```
┌─────────────────────────────────────────────────────────────────┐
│                    4-уровневая архитектура H-MEM                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Уровень 0: Эпизод    │ Сырые сообщения, высокая детализация    │
│  └── "User: Меня зовут Алекс, я инженер в Google"               │
│           ↓ консолидация (каждые N эпизодов)                    │
│                                                                  │
│  Уровень 1: Трейс     │ Группировка по теме/сущности            │
│  └── {entity: "Алекс", facts: [инженер, Google, ...]}           │
│           ↓ консолидация (каждые N трейсов)                     │
│                                                                  │
│  Уровень 2: Категория │ Суммированные концепции                 │
│  └── "Пользователь — технический специалист в big tech"         │
│           ↓ консолидация (каждые N категорий)                   │
│                                                                  │
│  Уровень 3: Домен     │ Мета-знания / профиль пользователя      │
│  └── "Технический пользователь, предпочитает детальные объяснения"│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Предварительные требования

```bash
pip install rlm-toolkit[all]
export OPENAI_API_KEY=your-key
```

## Шаг 1: Базовый H-MEM

```python
from rlm_toolkit import RLM
from rlm_toolkit.memory import HierarchicalMemory

# Создаём H-MEM
memory = HierarchicalMemory()

rlm = RLM.from_openai("gpt-4o", memory=memory)

# Ведём разговор
rlm.run("Привет, я Сара. Работаю дата-сайентистом в Netflix.")
rlm.run("Специализируюсь на рекомендательных системах.")
rlm.run("Предпочитаю Python и TensorFlow.")

# Запрашиваем накопленные знания
result = rlm.run("Что ты знаешь обо мне?")
print(result.final_answer)
# "Вы Сара, дата-сайентист в Netflix, специализируетесь на
#  рекомендательных системах. Предпочитаете Python и TensorFlow."
```

## Шаг 2: Конфигурация консолидации

```python
from rlm_toolkit.memory import HierarchicalMemory, HMEMConfig

config = HMEMConfig(
    # Лимиты уровней до консолидации
    episode_limit=50,     # Консолидировать эпизоды после 50
    trace_limit=20,       # Консолидировать трейсы после 20
    category_limit=10,
    domain_limit=5,
    
    # Настройки консолидации
    consolidation_enabled=True,
    consolidation_threshold=20,   # Триггер на 20 эпизодах
    consolidation_llm=None,       # Использовать основной LLM
    
    # Лимиты контекста
    max_context_tokens=4000,      # Максимум токенов в промпте
)

memory = HierarchicalMemory(config=config)
```

## Шаг 3: Ручная инспекция уровней

```python
from rlm_toolkit.memory import HierarchicalMemory

memory = HierarchicalMemory()
rlm = RLM.from_openai("gpt-4o", memory=memory)

# После некоторого разговора...

# Инспектируем каждый уровень
print("Уровень эпизодов:")
for episode in memory.get_episodes(limit=5):
    print(f"  {episode.content[:100]}...")

print("\nУровень трейсов:")
for trace in memory.get_traces():
    print(f"  {trace.topic}: {trace.summary}")

print("\nУровень категорий:")
for category in memory.get_categories():
    print(f"  {category.name}: {category.description}")

print("\nУровень домена:")
domain = memory.get_domain()
print(f"  {domain.profile}")
```

## Шаг 4: Персистентность

```python
from rlm_toolkit.memory import HierarchicalMemory

# Сессия 1: Создание и сохранение
memory = HierarchicalMemory(
    persist_directory="./user_memories/user_123",
    auto_save=True
)

rlm = RLM.from_openai("gpt-4o", memory=memory)
rlm.run("Запомни, что я люблю походы и фотографию")
# Автоматически сохранено

# Сессия 2: Загрузка и продолжение
memory2 = HierarchicalMemory(
    persist_directory="./user_memories/user_123"
)

rlm2 = RLM.from_openai("gpt-4o", memory=memory2)
result = rlm2.run("Какие мои хобби?")
# "Ваши хобби включают походы и фотографию!"
```

## Шаг 5: Безопасный H-MEM с зонами доверия

```python
from rlm_toolkit.memory import SecureHierarchicalMemory

memory = SecureHierarchicalMemory(
    # Шифрование
    encryption_key="your-256-bit-key-here",
    
    # Зона доверия
    trust_zone="confidential",  # public, internal, confidential, secret
    
    # Аудит
    audit_enabled=True,
    audit_log_path="./memory_audit.log",
    
    persist_directory="./secure_memory"
)

rlm = RLM.from_openai("gpt-4o", memory=memory)

# Чувствительные данные шифруются в хранилище
rlm.run("Мой ИНН 123-456-789")  # Зашифровано в хранилище
```

## Шаг 6: Совместная память между агентами

```python
from rlm_toolkit.memory import HierarchicalMemory, SharedMemoryPool

# Создаём общий пул памяти
pool = SharedMemoryPool(
    trust_level="internal",
    sync_interval=30  # Синхронизация каждые 30 секунд
)

# Агент 1: Служба поддержки клиентов
agent1_memory = HierarchicalMemory(
    agent_id="customer_service",
    shared_pool=pool,
    share_levels=[2, 3]  # Делимся только Category и Domain
)

# Агент 2: Техническая поддержка
agent2_memory = HierarchicalMemory(
    agent_id="tech_support",
    shared_pool=pool,
    share_levels=[2, 3]
)

# Оба агента делятся высокоуровневыми знаниями о пользователе
# Но сохраняют детали разговоров приватными
```

## Шаг 7: Пользовательская консолидация

```python
from rlm_toolkit.memory import HierarchicalMemory, ConsolidationStrategy

# Пользовательские промпты консолидации
class CustomConsolidator(ConsolidationStrategy):
    def consolidate_episodes_to_trace(self, episodes):
        """Пользовательская логика консолидации эпизодов."""
        prompt = f"""Проанализируй эти эпизоды разговора и извлеки:
        1. Ключевые сущности
        2. Важные факты
        3. Предпочтения пользователя
        
        Эпизоды:
        {episodes}
        
        Вывод в формате JSON."""
        
        return self.llm.generate(prompt)
    
    def consolidate_traces_to_category(self, traces):
        """Пользовательская консолидация трейсов."""
        # Ваша логика здесь
        pass

memory = HierarchicalMemory(
    consolidation_strategy=CustomConsolidator()
)
```

## Полное приложение: Персональный ассистент

```python
# personal_assistant.py
from rlm_toolkit import RLM
from rlm_toolkit.memory import HierarchicalMemory, HMEMConfig
from rlm_toolkit.tools import Calculator, WebSearch, DateTimeTool
import os

class PersonalAssistant:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.memory_path = f"./memories/{user_id}"
        
        # Настраиваем H-MEM
        config = HMEMConfig(
            episode_limit=100,
            consolidation_enabled=True,
            consolidation_threshold=25
        )
        
        self.memory = HierarchicalMemory(
            config=config,
            persist_directory=self.memory_path,
            auto_save=True
        )
        
        # Создаём RLM с памятью и инструментами
        self.rlm = RLM.from_openai(
            "gpt-4o",
            memory=self.memory,
            tools=[Calculator(), WebSearch(), DateTimeTool()],
            system_prompt=self._create_system_prompt()
        )
    
    def _create_system_prompt(self):
        """Генерируем системный промпт с профилем пользователя."""
        domain = self.memory.get_domain()
        
        base = """Ты полезный персональный ассистент.
Ты помнишь все предыдущие разговоры с пользователем.
Используй знания о пользователе для персонализации ответов."""
        
        if domain and domain.profile:
            base += f"\n\nПрофиль пользователя:\n{domain.profile}"
        
        return base
    
    def chat(self, message: str) -> str:
        """Обработка сообщения чата."""
        result = self.rlm.run(message)
        return result.final_answer
    
    def get_memory_stats(self) -> dict:
        """Получение статистики памяти."""
        return {
            "episodes": len(self.memory.get_episodes()),
            "traces": len(self.memory.get_traces()),
            "categories": len(self.memory.get_categories()),
            "has_domain": self.memory.get_domain() is not None
        }
    
    def forget(self, topic: str = None):
        """Выборочное забывание информации."""
        if topic:
            self.memory.forget_topic(topic)
        else:
            self.memory.clear()

def main():
    import sys
    user_id = sys.argv[1] if len(sys.argv) > 1 else "default"
    
    print(f"🧠 Персональный ассистент для {user_id}")
    print("   Команды: 'стат', 'забыть', 'выход'\n")
    
    assistant = PersonalAssistant(user_id)
    
    while True:
        user_input = input("Вы: ").strip()
        
        if not user_input:
            continue
        
        if user_input in ['выход', 'quit']:
            break
        
        if user_input in ['стат', 'stats']:
            stats = assistant.get_memory_stats()
            print(f"📊 Память: {stats}")
            continue
        
        if user_input.startswith('забыть'):
            topic = user_input[6:].strip() or None
            assistant.forget(topic)
            print("🧹 Память очищена")
            continue
        
        response = assistant.chat(user_input)
        print(f"Ассистент: {response}\n")

if __name__ == "__main__":
    main()
```

## Лучшие практики

!!! tip "Порог консолидации"
    Устанавливайте в зависимости от частоты разговоров:
    - Высокая частота: 50-100 эпизодов
    - Низкая частота: 10-20 эпизодов

!!! tip "Зоны доверия"
    Используйте подходящие зоны:
    - `public`: Нечувствительное, можно делиться
    - `internal`: Бизнес-данные
    - `confidential`: Персональная информация
    - `secret`: Высокочувствительные данные

!!! tip "Очистка памяти"
    Реализуйте периодическую очистку:
    ```python
    memory.cleanup_old_episodes(days=30)
    ```

!!! warning "Хранилище"
    H-MEM растёт со временем. Следите за дисковым пространством и реализуйте стратегии архивации.

## Следующие шаги

- [Туториал 8: Self-Evolving](08-self-evolving.md)
- [Концепция: Архитектура H-MEM](../concepts/hmem.md)
- [Концепция: Безопасность](../concepts/security.md)
